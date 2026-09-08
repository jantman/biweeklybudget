# Phase 0 Research: Correct the Unallocated-Funds Notification

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-07

This feature touches financial arithmetic that the constitution singles out as
"the reason the project exists", so every fact the implementation leans on was
checked against the working tree rather than assumed. Each finding below records
what was checked and where.

---

## R1: Sign convention for credit account balances

**Decision**: Add each active credit account's recorded ledger balance to the
funds-available figure *with its own sign*. Do not negate it, do not take its
absolute value, and do not branch on the sign.

**Rationale**: Credit account ledger balances are stored negative when money is
owed. Three independent confirmations:

1. `biweeklybudget/interest.py:118` and `:121` wrap `acct.balance.ledger` in
   `abs()` when constructing a billing period's start and end balances for a
   credit account. The `abs()` is only necessary because the stored value is
   negative.
2. `biweeklybudget/flaskapp/views/credit_payoffs.py:98` does the same
   (`fmt_currency(abs(acct.balance.ledger))`) when rendering the amount owed.
3. The sample data fixtures give the two credit accounts
   `ledger_bal=Decimal('-952.06')` (CreditOne, latest of three statements) and
   `ledger_bal=Decimal('-5498.65')` (CreditTwo), while every bank and investment
   account in the same fixtures carries a positive balance.

Because owed money is already negative, `funding_balance + credit_balance` *is*
the subtraction the spec asks for. This also gives the positive-balance
(overpaid card / statement credit) edge case the right answer for free, which
is exactly why the spec phrased FR-001 sign-neutrally.

**Alternatives considered**:

- *Compute `abs()` of each credit balance and subtract it.* Rejected: it gets the
  overpaid-card case backwards, subtracting money the person actually has. It
  also duplicates a sign assumption in a fourth place instead of relying on the
  one the data already carries.
- *Normalise the stored sign for credit accounts.* Rejected outright — it is a
  data migration affecting `interest.py`, `credit_payoffs.py`, the payoff
  calculators and every recorded balance, for no benefit to this feature. The
  spec explicitly puts changes to how balances are recorded out of scope.

---

## R2: Which accounts count as credit accounts

**Decision**: Use the existing `Account.active_credit_accounts(db)` static
(`biweeklybudget/models/account.py:307-322`).

**Rationale**: It returns exactly `acct_type == AcctType.Credit AND
is_active == True`, which is the set FR-002 requires. It was introduced by the
#210 work to answer "what may a transaction be a payment toward", and that is
the same population: the accounts whose balances the person will have to settle
with cash. Reusing it means the notification cannot drift out of step with the
credit-payment feature, and it satisfies the spec's assumption that no new
notion of which accounts count is introduced.

**Alternatives considered**: A fresh query inside `notifications.py` filtering on
`AcctType.Credit`. Rejected: it would be a second definition of the same set,
free to diverge.

---

## R3: Missing balances

**Decision**: Skip credit accounts whose `balance` is `None`, or whose
`balance.ledger` is `None`, contributing zero.

**Rationale**: `Account.balance` is a property that returns the most recent
`AccountBalance` row or `None` when the account has never had one
(`models/account.py:295-305`). `AccountBalance.ledger` is a nullable column.
The existing `budget_account_sum()` already guards `if acct.balance is not None`
but does **not** guard `balance.ledger is None`; `index.py:293` shows the
`ledger is None` case is real and is handled there by treating it as zero.

FR-003 requires an account with no recorded balance to contribute zero *and not
prevent the notification from being produced*, so the new code guards both. The
existing `budget_account_sum()` is left as it is — tightening it is a
behavioural change to a figure this feature is not correcting, and a `None`
ledger on a funding account would raise there today rather than silently
mis-sum, so it is not a latent wrong-number bug.

**Alternatives considered**: Summing in SQL with `func.sum` and `coalesce`.
Rejected: `Account.balance` is "latest row per account", which is a
correlated-subquery/window shape in SQL that the rest of this module does not
use. The existing methods all iterate in Python, and the account count is tiny.
Matching the surrounding idiom is worth more than the query here.

---

## R4: Is defect #2 (pseudo-transactions) still present?

**Decision**: No. It is already fixed on `master`. Scope it as regression
coverage exercised through the notification, and add no new exclusion logic.

**Rationale**: Verified in the working tree:

- `Transaction.no_budget_impact` exists as a real column
  (`models/transaction.py:159`).
- `Transaction.is_excluded_from_budget` (`models/transaction.py:227-249`)
  returns true for a `no_budget_impact` transaction *or* one that is a payment
  toward a credit account.
- `Account.unreconciled_sum` (`models/account.py:343-364`) iterates
  `self.unreconciled` and `continue`s on `t.is_excluded_from_budget`.
- Its docstring already cites issues #210 and #319, and deliberately notes that
  `Account.unreconciled` itself is *not* filtered, so the reconcile view still
  lists these transactions — which is what FR-010 requires.

`NotificationsController.budget_account_unreconciled()` sums
`acct.unreconciled_sum` over the funding accounts, so it inherits the exclusion
with no change. The issue's fallback suggestion — matching reconcile notes
against the string `pseudo-trans` — must **not** be implemented; it is the
workaround the explicit flag replaced, and adding it now would give two
disagreeing definitions of "no cash impact".

What is genuinely missing is a test tying that model behaviour to the banner.
Nothing currently asserts that an excluded transaction leaves the notification
unmoved, so the correction could regress silently. That gap is the whole of
User Story 3.

**Alternatives considered**: Treating the issue's description as authoritative
and re-implementing the exclusion. Rejected: it would duplicate working logic
and risk double-excluding.

---

## R5: How the notification reaches the page, and what asserts its text

**Decision**: Change only `NotificationsController`; no template, view or
front-end change is needed. Update the tests that pin the old sentence.

**Rationale**: `flaskapp/context_processors.py:53` injects
`NotificationsController().get_notifications()` into every template context, and
the base template renders each dict's `content` as raw HTML inside
`#notifications-row`. The sentence is built entirely inside `get_notifications()`,
so rewording it requires no template edit.

Tests that assert the exact wording and must be updated:

- `tests/unit/flaskapp/test_notifications.py` —
  `test_get_notifications_over_balance` and `test_get_notifications_under_balance`
  assert the full HTML string; all six tests in `TestNotifications` patch the
  controller's statics by name, so a new static must be added to each
  `patch.multiple` call or those tests will hit the database.
- `tests/acceptance/.../test_base_template.py` —
  `TestBudgetOverBalanceNotification.test_3_notification` (asserts the rendered
  sentence, the four link hrefs and the four link texts, positionally),
  `TestPPOverBalanceNotification.test_2_notification`, and
  `TestPPUnderBalanceNotification.test_3_notification`. The same classes'
  `test_*_confirm_pp` methods assert the individual component figures and will
  need a new assertion for the credit total.

The acceptance figures shift for a second reason: the sample data has two active
credit accounts (`CreditOne` latest ledger `-952.06`, `CreditTwo` `-5498.65`),
so funds available in those tests drops by `$6,450.71` from the current
`$12,889.24` to `$6,438.53`. Every expected string and verdict in those three
classes must be recomputed from the actual fixture data rather than hand-adjusted
— including re-checking whether each class still produces the *same* over/under
verdict it was written to demonstrate. A class named "over balance" that now
computes an under-balance would need its fixture nudged so it still tests what
its name says.

**Alternatives considered**: Keeping the old sentence and appending the credit
figure, to minimise test churn. Rejected: FR-006 requires the pay-period label to
change regardless, so the sentence is being rewritten either way, and a sentence
that says "combined balance of budget-funding accounts" while reporting a figure
that is *not* that balance would trade one mislabelling for another.

---

## R6: Wording of the corrected sentence

**Decision**: Rewrite the sentence around "funds available" and "allocated funds",
showing the credit deduction as its own linked term:

> Combined balance of all [budget-funding accounts](/accounts) less
> [credit account balances](/accounts) (**$X**) is less/more than all allocated
> funds total of **$Y** (**$A** [standing budgets](/budgets); **$B**
> [current pay period allocated but unspent](/pay_period_for); **$C**
> [unreconciled](/reconcile))!

**Rationale**: This satisfies FR-006 (no "remaining"), FR-007 (the credit
deduction is named and visible) and FR-008 (each link leads to a view reporting
that quantity — `/accounts` shows both account balances, `/budgets` shows
standing budget balances, `/reconcile` shows unreconciled transactions).

"allocated but unspent" is the phrase the issue itself proposes, and it is
literally what `pp_sum()` computes (`allocated - spent`), so the label and the
arithmetic now agree. Keeping the two-clause "is less than / is more than" shape
and the existing `alert-danger` / `alert-info` classes preserves FR-005 and the
acceptance tests' class assertions.

**Alternatives considered**:

- *Showing the credit balance as a fourth term on the committed side* (i.e.
  adding the amount owed to funds committed rather than subtracting it from
  funds available). Arithmetically identical for the verdict, but it misrepresents
  the model: money owed on a card is not an allocation, and the spec's Overview
  defines it as a reduction of what is available. Rejected on meaning, not maths.
- *Dropping the pay-period link entirely* rather than relabelling it. Rejected:
  the pay period view is still where a reader goes to understand that figure;
  only the word "remaining" was wrong.

---

## R7: Schema, migrations and packaging

**Decision**: No model change, no Alembic migration, no packaging change.

**Rationale**: Every input already exists as a model attribute or an existing
query. The feature adds one derived figure computed at request time from data
already stored. Nothing is added to `models/`, so constitution principle III
(schema changes ship with reversible migrations) is satisfied vacuously — and
the `migrations` tox environment, which verifies that head matches the models,
must still pass unchanged, which is itself the check that no schema drift crept
in. No new console script or package data, so the Docker/packaging suites are
unaffected.

---

## R8: Test strategy for the arithmetic

**Decision**: Cover the new figure at three levels — unit tests over the new
static with a mocked session, unit tests over `get_notifications()` with the
statics patched, and acceptance tests against real sample data.

**Rationale**: The constitution requires that changes to budget arithmetic ship
with tests that pin the expected numbers, and that new code be covered by valid
tests rather than tests written to pass. The three levels catch different
failures: the first catches a wrong sign or a mishandled `None`; the second
catches a wrong formula or a wrong sentence; the third catches the two of them
disagreeing, and is the only level that exercises the real
`is_excluded_from_budget` path end to end for User Story 3.

The unit tests must pin *signed* expectations — a test asserting only that the
figure "decreased" would pass for both a correct subtraction and an `abs()`-based
one, which is precisely the bug R1 guards against.
