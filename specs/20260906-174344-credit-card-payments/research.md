# Phase 0 Research: Special Handling of Credit Card Payments

**Feature**: `specs/20260906-174344-credit-card-payments/`
**Date**: 2026-09-06

This document records the decisions that turn the specification into an implementable
design, together with the code facts each one rests on. Every decision that the
specification left open, and every place where the existing code constrains the answer, is
recorded here rather than discovered during implementation.

---

## D-1: Stored fields on `Transaction`

**Decision**: Two new columns on `transactions`:

| Column | Type | Nullability | Default |
|--------|------|-------------|---------|
| `no_budget_impact` | `Boolean` | `nullable=False` | `False` |
| `credit_payment_acct_id` | `Integer`, `ForeignKey('accounts.id')` | `nullable=True` | `NULL` |

**Rationale**: `no_budget_impact` is the name issue #319 itself proposes, and a non-nullable
Boolean with a Python-side default is already an established pattern in this schema —
`Account.reconcile_trans` is `Column(Boolean, default=True, nullable=False)`, and
`Transaction.sales_tax` is `Column(Numeric(...), nullable=False, default=0.0)`, added to a
populated table by migration `d01774fa3ae3` with a bare `nullable=False` and no
`server_default`. Following that precedent keeps the migration and the model definitions
identical, which is what the `migrations` tox environment (alembic-verify) checks.

`credit_payment_acct_id` is nullable because "not a payment toward any credit account" is
the overwhelmingly common case and the specified default (FR-009).

**Alternatives considered**:

- *A single nullable column, with non-NULL meaning both "credit payment" and "no budget
  impact"*. Rejected: #319's non-credit-card cases — statement credits, cash-back
  redemptions, balance-reconcile adjustments — have no credit account to name, so the
  general designation must be expressible on its own.
- *An enum or a `transaction_kind` discriminator*. Rejected: it would force every existing
  transaction into a category, is a larger migration, and buys nothing the two columns do
  not.

---

## D-2: Relationship disambiguation (a correctness trap)

**Decision**: When `credit_payment_acct_id` is added, the **existing** `account`
relationship must gain an explicit `foreign_keys=[account_id]`, and the new relationship
must declare `foreign_keys=[credit_payment_acct_id]` with a distinct backref
(`credit_payments`).

**Rationale**: `transactions` will have two foreign keys to `accounts.id`. SQLAlchemy
cannot infer the join condition for either relationship in that situation and raises
`AmbiguousForeignKeysError` at mapper configuration time — which is to say, on import, for
every code path in the application. The existing relationship is:

```python
account = relationship("Account", backref="transactions", uselist=False)
```

and it must not be left as-is. `Transaction.transfer_id` is already a self-referential FK
to `transactions.id` and is handled with `remote_side=[id]`, so the codebase already has
precedent for explicitly-disambiguated relationships.

**Consequence for the plan**: this is the single most likely way to break the entire test
suite at once, so it belongs in the first milestone and is verified by importing the models
and running the unit suite before anything else is built on top.

---

## D-3: Effective exclusion is derived, not stored

**Decision**: Add a `hybrid_property` on `Transaction`:

```python
is_excluded_from_budget = no_budget_impact OR (credit_payment_acct_id IS NOT NULL)
```

with a matching SQL expression so it is usable in queries. `no_budget_impact` stores only
the user's explicit choice; the credit designation forces exclusion independently.

**Rationale**: FR-011 requires the credit designation to imply zero budget impact, and
FR-014 requires that *clearing* the credit designation restore ordinary budget impact
"unless the user has also set the Layer 1 designation explicitly, in which case that choice
stands". If the form handler instead wrote `no_budget_impact = True` whenever a credit
account was chosen, that stored `True` would be indistinguishable from a user's own choice,
and FR-014 would be unimplementable — clearing the credit account would leave the
transaction silently excluded forever. Deriving the effective answer keeps the two facts
separate and makes FR-014 fall out for free.

`actual_amount` on the same model is already a `hybrid_property` with an explicit
`.expression`, so the pattern is in place.

**Alternatives considered**: *Form handler sets the boolean.* Rejected for the reason above.

---

## D-4: Where the exclusion filter is applied — dict level, not query level

**Decision**: `BiweeklyPayPeriod._dict_for_trans()` gains a `no_budget_impact` key carrying
`t.is_excluded_from_budget`; `_dict_for_sched_trans()` sets it to `False`;
`_make_budget_sums()` skips any entry whose value is `True`. The `_transactions()` query is
**not** filtered.

**Rationale**: `transactions_list` has two consumers. `_make_budget_sums()` computes the
totals, but `payperiod.html` also iterates it directly (`{% for t in transactions %}`) to
render the pay period's transaction table. FR-005 requires excluded transactions to remain
visible in that table, and FR-007 requires them to be visually distinguished there — both of
which are impossible if the query drops them. Filtering at the query level would make the
transaction vanish from the page rather than be shown-and-not-counted, which is the opposite
of what the feature is for: the reader must be able to see *why* the listed amounts do not
sum to the reported totals.

`_make_overall_sums()` needs no change at all: it derives entirely from
`self._data_cache['budget_sums']`, so excluding a transaction from the budget sums excludes
it from the overall sums automatically. That is verified by test, not assumed.

**Alternatives considered**: *Filter in `_transactions()`*. Rejected — breaks FR-005 and
FR-007 as above.

---

## D-5: `Account.unreconciled_sum` — filter the sum, not the query

**Decision**: `Account.unreconciled_sum` skips transactions where `is_excluded_from_budget`
is true. `Account.unreconciled` (the query property) and `Transaction.unreconciled()` (the
static method) are left unchanged.

**Rationale**: `Transaction.unreconciled(db)` is what `TransUnreconciledAjax` uses to
populate the reconcile view; filtering it would make excluded transactions unreconcilable,
directly contradicting FR-005. `Account.unreconciled` has exactly one consumer in the
codebase — `unreconciled_sum` — so narrowing the behaviour at the sum is both sufficient
and the smaller change.

**Recorded trade-off, deliberately accepted**: `unreconciled_sum` is displayed as
`balance.ledger - unreconciled_sum` on the accounts and index pages, which reads as "cash
in the account less what I have recorded but the bank has not yet posted". A real credit
card payment that has not yet cleared *is* committed cash, so excluding it makes that
figure optimistic for the window between recording the payment and reconciling it.

This is nevertheless what is specified: FR-004 in the spec, from #319's explicit
"are excluded from `Account.unreconciled_sum`", restated in #210's own Scope paragraph.
There is a coherent reading behind it — `unreconciled_sum` feeds
`NotificationsController.budget_account_unreconciled()`, which is a *budget allocation*
figure ("how much of my money is not yet accounted for by a budget"), and a transaction with
no budget impact is by definition not a budget allocation. Issue #320 is already open against
that notification for the related reason that it never nets out credit account balances, so
the cash-versus-allocation question is being handled there rather than here. Implemented as
specified; flagged in the pull request so the trade-off is visible to review.

---

## D-6: Attribution and warnings are computed server-side, in a reusable module

**Decision**: A new module `biweeklybudget/credit_payment.py` holds the whole calculation,
exposed as a `CreditPaymentAttribution` class. A new AJAX endpoint
`GET /ajax/credit-payment-info` in `flaskapp/views/transactions.py` serves it to the modal.
Nothing is computed in JavaScript beyond rendering the response.

**Rationale**:

- The calculation needs pay period boundaries (`BiweeklyPayPeriod`), the account's
  transactions, and the set of payments already designated toward it. All of that is
  server-side data; shipping it to the browser to be re-derived would duplicate the
  arithmetic in a second language.
- Financial arithmetic must be unit-testable with pinned numbers (constitution, Technology
  & Security Constraints). A Python module is; jQuery in a modal is not, short of Selenium.
- The spec states (Assumptions, scope boundaries) that issue #322 — detecting a closed pay
  period whose card charges have no recorded payment — is to build on this calculation
  rather than reimplement it. A standalone module is the shared foundation that promise
  requires; logic buried in a view handler is not.

**Alternatives considered**:

- *Compute in `TransactionFormHandler.validate()` and return warnings with the form
  response.* Rejected: `FormHandlerView` treats everything in its error hash as blocking,
  and FR-021 requires the warning to be advisory. It would also give feedback only on
  submit, when FR-016 requires it *while* the amount is being entered.
- *Compute client-side from data embedded in the page.* Rejected per the rationale above.

---

## D-7: The attribution algorithm, stated precisely

The specification gives the rule (FR-017: oldest charges first) but not its boundaries.
Made precise here:

Given a credit account `A`, a candidate payment amount `P`, a payment date `D`, and
optionally the id of the payment being edited:

1. **Window**. Consider only transactions dated on or after
   `settings.CREDIT_PAYMENT_BEGIN_DATE` and on or before `D`.
2. **Charges**. Group every transaction recorded against account `A` inside the window by
   the pay period its date falls in, summing `actual_amount` per period. Order the periods
   oldest first.
3. **Prior payments**. Sum `actual_amount` over every transaction inside the window whose
   `credit_payment_acct_id` is `A`, **excluding the transaction being edited** (FR-019).
4. **Consume prior payments** against the per-period charge totals, oldest period first,
   producing the outstanding charge remaining in each period.
5. **Attribute `P`** against those outstanding remainders, oldest period first, until `P` is
   exhausted. Each period receives an attributed amount; periods are labelled closed or
   currently-open by comparing against the pay period containing today's date.
6. **Excess** is `P` less the total attributed. Excess greater than zero triggers the
   over-payment warning (FR-020), stating the excess.

Bounding charges at `D` rather than considering all recorded charges is a deliberate
refinement: a payment cannot settle a charge that had not yet been made when it was paid,
and without the bound a payment entered today would be silently attributed to a
future-dated charge. Bounding prior payments the same way makes the result independent of
the order in which payments were entered.

The self-paying case (FR-022) — a transaction recorded against account `A` and also
designated as a payment toward `A` — is detected in the same module and returned as a
separate warning.

---

## D-8: The tracking start date is a new setting

**Decision**: Add `CREDIT_PAYMENT_BEGIN_DATE` to `biweeklybudget/settings.py`, defaulting to
`None`, listed in `_DATE_VARS` (so it is overridable by environment variable in the existing
`%Y-%m-%d` form) but **not** in `_REQUIRED_VARS`. After the required-variable check runs,
`None` is resolved to `RECONCILE_BEGIN_DATE`.

**Rationale**: FR-023 requires the setting to be configurable and to default to the existing
reconcile begin date so that no new configuration is needed to adopt the feature. Making it
required would break every existing deployment and every existing settings module on
upgrade. `settings.py` already has this exact shape for its optional dated and typed
variables, and `LOCALE_NAME` already demonstrates post-load default resolution in the same
file.

The reason the window exists at all is recorded in the spec's Assumptions: payments recorded
before this feature carry no designation, so they are not subtracted from the charge total,
and without a bound a card's apparent unpaid-charge total would drift upward without limit
and the warning would stop meaning anything.

`biweeklybudget/settings_example.py` and
`biweeklybudget/tests/fixtures/test_settings.py` gain the same variable, documented, next to
`RECONCILE_BEGIN_DATE`.

---

## D-9: Front-end approach

**Decision**: Extend the existing `FormBuilder` modal in `transactions_modal.js` — no new
frontend stack, per the constitution's Technology & Security Constraints.

- `.addCheckbox('trans_frm_no_budget_impact', 'no_budget_impact', 'No Budget Impact?', false, ...)`
  for the Layer 1 designation. `addCheckbox` already exists (`formBuilder.js:318`) and is
  used for the budget-split toggle.
- `.addLabelToValueSelect('trans_frm_credit_payment_acct', 'credit_payment_acct', 'Credit Card Payment For', credit_acct_names_to_id, 'None', true)`
  for the credit account. `addLabelToValueSelect` already exists (`formBuilder.js:258`) and
  is what the Account select uses; `addNone=true` gives the required explicit
  "not a credit card payment" default (FR-010).
- `.addHTML('<div id="trans_frm_credit_payment_info"></div>')` for the attribution panel and
  warnings, refreshed by an `onchange`/`onkeyup` handler that calls the AJAX endpoint. This
  mirrors how the budget-split feedback div (`#budget-split-feedback`) already works.

`TransactionsView` and `OneTransactionView` already pass `accts` and `budgets` to the
template; they gain a `credit_accts` mapping restricted to `AcctType.Credit` and
`is_active`, rendered into a JS variable in `transactions.html` the same way `acct_names_to_id`
is today. Restricting the list server-side is what makes FR-010 and FR-015 true by
construction rather than by client-side politeness — FR-015 is *also* enforced in
`TransactionFormHandler.validate()`, because the form is a public endpoint.

**Visual distinction (FR-007)**: the `/transactions` DataTable gains a rendered marker on the
description column driven by a new `no_budget_impact` field in the AJAX row data, and
`payperiod.html` gains an equivalent marker in its transaction table. Both follow the
existing convention in those tables of an `<em>`-wrapped parenthetical, as
`payperiod.html` already uses for `<em>(sched)</em>`.

---

## D-10: Test data lives in the tests, not in `sampledata.py`

**Decision**: New unit and acceptance tests create their own credit charges and payments
through the `testdb` fixture. `biweeklybudget/tests/fixtures/sampledata.py` is **not**
extended with new transactions.

**Rationale**: acceptance tests across the suite address fixture rows by hard-coded primary
key — `testdb.query(Transaction).get(3)`, `Budget.get(4).current_balance ==
Decimal('1284.23')`, and so on — and several assert on pay period totals computed from the
whole fixture set. Adding transactions to `sampledata.py` would shift those numbers and
break tests that have nothing to do with this feature, producing a diff in which the real
changes are invisible. `TestTransModalDoesNotShowInactiveBudgets` (test_transactions.py:791)
is the established pattern for a test class that builds its own rows in a `test_00_*`
method; new test classes follow it.

---

## D-11: Migration shape

**Decision**: One Alembic revision adding both columns and the foreign key, with a matching
`downgrade()` dropping them, plus a `biweeklybudget/tests/migrations/test_migration_<rev>.py`
following the `test_migration_d01774fa3ae3.py` pattern (`verify_before` asserts the columns
are absent, `verify_after` asserts they are present, and the harness runs the reverse
migration back through `verify_before`).

Current head is `a1b2c3d4e5f6` (`add_standing_budget_id_to_projects`); the new revision's
`down_revision` points at it.

**Sequencing note, from CLAUDE.md**: for Alembic autogenerate to see a diff, the test
database must be brought to the current head with `initdb` **before** the model is edited.
The task ordering in `tasks.md` must therefore stand the database up and run `initdb` as its
first step, before the first model change. Getting this backwards silently produces an empty
migration.

The `downgrade()` must drop the foreign key constraint before dropping
`credit_payment_acct_id`; MySQL will not drop a column that a constraint still references.
The constraint name follows the metadata naming convention declared in `models/base.py`
(`fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s`), giving
`fk_transactions_credit_payment_acct_id_accounts`.
