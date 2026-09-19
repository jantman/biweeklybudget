# Phase 0 Research: Plaid Credit Card Balances Recorded As Negative

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-18

The Technical Context in `plan.md` contains no `NEEDS CLARIFICATION` markers: the stack,
the file, the failing behaviour and the precedent are all known from the issue and from
the repository. What follows records the decisions that shape the implementation.

---

## Decision 1: Where the negation goes

**Decision**: Add `negate_balance: bool = False` to
`PlaidUpdater._update_bank_or_credit()` and pass `negate_balance=True` from the `credit`
branch of `_stmt_for_acct()`. Apply the negation to the already-quantized `Decimal` with a
unary minus.

**Rationale**:

* `_update_bank_or_credit()` serves both `credit` and `depository` accounts. The sign rule
  differs between them, and the thing that knows which is which is `_stmt_for_acct()`,
  which already branches on `account.plaid_account.account_type`. Putting the decision at
  the call site and the mechanism in the callee keeps the account-type knowledge in the one
  place that already has it.
* `_update_investment()` already has exactly this signature and exactly this mechanism,
  added by issue #263 for loans. Two methods with the same problem should not solve it two
  different ways; a reader who has understood one has understood the other.
* Negating the quantized value rather than the raw value means the recorded number is the
  exact negation of what would have been recorded before, with no chance of a rounding
  difference between the two paths.

**Alternatives considered**:

* *Negate in `_stmt_for_acct()` before dispatch.* Rejected: `_stmt_for_acct()` does not
  compute the balance, `_update_bank_or_credit()` does. Pre-negating would mean mutating
  the Plaid response dict or threading a second balance value through, both worse.
* *A separate `_update_credit()` method.* Rejected: it would duplicate the whole
  transaction-recording body for a one-line difference.
* *Branch on `account.acct_type == AcctType.Credit` inside the updater.* Rejected: the
  sign convention is a property of what **Plaid** reports for its account type, not of how
  the user has classified the account in biweeklybudget. The two can disagree — the Plaid
  docs explicitly tell users to link a Plaid *loan* to a biweeklybudget *Investment*
  account — and keying off the biweeklybudget type would break that case.

---

## Decision 2: Negate, never `abs()`

**Decision**: Use `bal = -bal` (unary minus on the `Decimal`).

**Rationale**: A negative `balances.current` on a Plaid credit account is legitimate and
meaningful — an overpaid card, or a statement credit larger than the balance. Plaid's own
field description says so: "a negative amount indicates the lender owing the account
holder". After negation such a card records a *positive* biweeklybudget balance, which is
precisely the case the Cash Position documentation already describes as money you can
spend. `abs()`, or any "amount owed" normalization, would silently turn a credit in the
user's favour into a debt — a wrong number in the direction that costs the user money.

Unary minus rather than `* Decimal('-1')` so that a zero balance stays `Decimal('0.00')`
and does not become `Decimal('-0.00')`. `_update_investment()` carries this exact comment
from #263; the same comment is warranted here.

---

## Decision 3: The sign rule applies to every institution

**Decision**: Negate unconditionally for `account_type == 'credit'`. Do not gate on
institution, and do not attempt to infer the convention per institution.

**Rationale**: Plaid states the credit convention as a rule, not an observation. From
`plaid/model/account_balance.py` in the pinned `plaid-python==44.0.0` (generated from
Plaid's OpenAPI spec, matching the published API reference):

> The total amount of funds in or owed by the account. For `credit`-type accounts, a
> positive balance indicates the amount owed; a negative amount indicates the lender owing
> the account holder. For `loan`-type accounts, the current balance is the principal
> remaining on the loan, except in the case of student loan accounts at Sallie Mae
> (`ins_116944`). [...] Similar to `credit`-type accounts, a positive balance is
> *typically* expected, while a negative amount indicates the lender owing the account
> holder.

The `credit` sentence carries no hedge and no institution qualifier. The hedging
("typically expected") and the one named institution-specific carve-out in the whole field
belong to `loan`, which #263 already handled — and even that carve-out is about *what is
included* in the balance (principal plus outstanding interest), not about its sign. No
Plaid documentation, changelog entry or errors page describes an institution that reverses
the credit sign.

**Alternatives considered**: a per-institution or per-account override setting. Rejected as
speculative configuration for a case with no known instance; it would add a setting the
user cannot evaluate without already knowing the answer. Decision 4 gives a cheaper way to
find out if such an institution ever appears.

---

## Decision 4: Shape of the diagnostic consistency check

**Decision**: When negating (i.e. for credit accounts only), and only when the account has
a recorded credit limit and Plaid reported an available balance and the reported current
balance is non-zero, compute:

```text
err_normal   = abs(available - (limit - current))
err_reversed = abs(available - (limit + current))
```

and log when `err_reversed < err_normal` **and** `err_normal > abs(current)`. Record the
balance per the documented rule regardless; never raise.

**Rationale**: Plaid documents, for credit accounts, that "the `available` balance
typically equals the `limit` less the `current` balance, less any pending outflows plus any
pending inflows". So under the documented convention the residual `err_normal` is exactly
the net pending activity. A residual *larger than the balance itself*, which is also better
explained by the reversed hypothesis, is the signal worth reporting. The second condition
is what keeps the check quiet: without it, a card with a small balance and a large pending
inflow flags spuriously, because the two hypotheses are only `2 × current` apart and noise
dominates when `current` is small.

The relation is approximate by Plaid's own wording, which is why this is a log line and
not a validation. It must not alter a recorded value and must not make an update fail or
be reported as failed — a false positive that broke a user's Plaid update would be far
worse than the problem it looks for.

Use `account.credit_limit` (already stored, and named by the issue) rather than Plaid's
`balances.limit`. Skip silently when it is `None`, when `available` is `None`, or when
`current` is zero — in the zero case both hypotheses coincide and the comparison is
meaningless.

**Alternatives considered**:

* *Compare on every update with no margin condition.* Rejected: measurably noisy for
  small-balance cards with pending activity, and a check that cries wolf gets ignored.
* *Raise or fail the update.* Rejected explicitly by the issue and by common sense; the
  relation is approximate.
* *Auto-correct the sign when the check fires.* Rejected: it would make the recorded sign
  depend on pending-transaction noise, which is exactly the instability the negative-means-
  owed convention exists to avoid.

---

## Decision 5: Log level for the diagnostic check

**Decision**: `logger.warning`, with the account name and all three figures in the message.

**Rationale, and a recorded deviation**: the issue text suggests "a debug-level warning in
the updater rather than a hard failure". The "rather than a hard failure" half is honoured
exactly. On the level itself this plan chooses WARNING, because the condition it reports —
an institution whose balances mean the opposite of what biweeklybudget records — would
silently invert a financial figure on the Cash Position page, and a message at DEBUG would
never be seen in normal operation (Plaid API responses are already logged at DEBUG, so the
line would be buried even when debug logging is on). The margin condition in Decision 4
keeps the warning rare enough that it does not become noise.

This is a one-word change if the maintainer prefers DEBUG, so it is called out in the pull
request rather than blocking the work. Recorded here per Constitution Principle V.

---

## Decision 6: Historical rows — documented SQL, not a migration

**Decision**: Do not write an Alembic migration. Document, in the new "Credit Card
Accounts" section of `docs/source/plaid.rst`, that pre-upgrade rows keep their old sign,
what that looks like on the Account Balances chart, and SQL the operator runs once to
correct `account_balances.ledger` and `ofx_statements.ledger_bal` for Plaid credit
accounts.

**Rationale**:

* Issue #263 faced the identical situation for loan accounts and resolved it this way. The
  existing "Loan Accounts" section is the model, down to the two `UPDATE` statements and
  the warnings around them. Solving the same problem a second, different way would leave
  the project with two procedures for one class of problem.
* A migration cannot tell a balance that came from Plaid from one the account had before it
  was linked, so it would flip rows that were always correct.
* Principle III requires a tested, reversible `downgrade()`. For a data-rewriting migration
  the only possible `downgrade()` is "re-break the data", which corrupts anyone who
  corrected rows by hand in between, in both directions.
* Nothing under `biweeklybudget/models/` changes, so Principle III's trigger is not met.

The documentation must carry the same three warnings the loan section carries: run it once,
after upgrading and *before* the next Plaid update; running it a second time undoes it; add
a date condition if some of an account's balances came from somewhere other than Plaid.

**Alternatives considered**:

* *An Alembic data migration.* Rejected, above.
* *A one-off maintenance console script.* Rejected: it is the same SQL with a `setup.py`
  entry point, more code to test and document, and it diverges from the loan precedent for
  no gain.
* *Leave the historical data undiscussed.* Rejected: the issue calls this out as needing a
  decision, and a chart that flips sign mid-history with no explanation is a support
  problem.

---

## Decision 7: What is deliberately *not* changed

**Decision**: `cashposition.py`, `flaskapp/notifications.py`, the Account Balances chart,
the models, the transaction amounts, the available balance, and the per-account
`negate_ofx_amounts` setting are all untouched.

**Rationale**: each already implements the negative-means-owed convention correctly, and
each becomes correct for Plaid-sourced credit balances the moment the recorded sign is
fixed. Term 3 of the waterfall adds the credit balance "with the sign in which each is
recorded" precisely so that it needs no special case; that comment becomes true rather than
aspirational. Changing a second place would create a second convention to keep in sync.

`negate_ofx_amounts` is a separate, per-account, user-facing setting about **transaction**
amounts. It must not be conflated with the statement's ledger balance, and an account that
has it set must see no change in its transaction amounts from this work.

---

## Decision 8: Test strategy

**Decision**: Unit tests in `biweeklybudget/tests/unit/test_plaid_updater.py` only; no new
acceptance test.

**Rationale**: the behaviour is a pure function of the Plaid response and the account type,
fully exercised by the existing mocked-updater tests. `TestStmtForAcct.test_credit` asserts
the call made to `_update_bank_or_credit()` and gains `negate_balance=True`;
`TestStmtForAcct.test_depository` asserts it is not passed (or is `False`).
`TestUpdateBankOrCredit` gains cases pinning the recorded sign for a positive, a negative
and a zero reported credit balance, and keeps its existing cases as the depository
(non-negating) baseline — including `test_negate_amounts`, which is the regression guard
that `negate_ofx_amounts` and `negate_balance` stay independent.

The diagnostic check gets its own tests: fires, does not fire, and each skip condition.

The existing acceptance suite covers Cash Position and the unallocated-funds notification
against fixture data that does not come from Plaid, so it is unaffected — but it must still
be run to completion and pass before the feature is done (Principle II).
