# Phase 0 Research: Per-Account Transaction Totals Per Pay Period

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-07

The Technical Context for this feature contains no NEEDS CLARIFICATION entries: the
language, stack, storage, testing and target platform are all fixed by the existing
project. What follows is the research that turned the specification's requirements into
the design decisions recorded in [plan.md](./plan.md).

## R1. Where the numbers come from

**Question**: What is the smallest, most reliable source for "the total of an account's
transactions in a pay period"?

**Finding**: `BiweeklyPayPeriod.transactions_list` (`biweeklybudget/biweeklypayperiod.py`)
is already the single ordered list of dicts covering both real `Transaction` rows and the
`ScheduledTransaction` occurrences projected into the period, with converted scheduled
transactions de-duplicated against the real transactions they produced. Each dict carries
`account_id`, `account_name` and `amount` (see `_trans_dict()` / `_dict_for_trans()` /
`_dict_for_sched_trans()`).

**Decision**: Compute per-account sums by iterating `self.transactions_list`, exactly as
`_make_budget_sums()` does. No new query at all.

**Rationale**: This is what makes FR-005 and SC-002 true by construction rather than by
coincidence — the table's cells and the page's Transactions table are summing literally the
same list. Any future change to what falls in a period is picked up by both at once.

**Alternatives considered**:

- *A dedicated SQL aggregate* (`SELECT account_id, SUM(actual_amount) ... GROUP BY`). Rejected:
  it would see only real `Transaction` rows, silently excluding the scheduled transactions the
  page displays, and would drift away from `transactions_list` the moment either changes. It
  also adds a database round trip, against SC-005.
- *Summing in the Jinja template*. Rejected: puts financial arithmetic where it cannot be
  unit-tested, contradicting FR-013 and the constitution's requirement that financial paths be
  pinned by tests.

## R2. Which transactions count

**Question**: Should transactions excluded from budget arithmetic (credit card payments, and
transactions flagged `no_budget_impact`) be included?

**Finding**: `_make_budget_sums()` skips any transaction whose `no_budget_impact` is true,
because counting a credit card payment would charge the same money to a budget twice (issues
#210 / #319). That reasoning is specific to *budgets*. The money in question does genuinely
leave the paying account and does genuinely arrive at the credit account; an account activity
total that omitted it would not match the account's statement.

**Decision**: Include every entry in `transactions_list`, with no `no_budget_impact` filter.

**Rationale**: The new table answers "what moved through this account", not "what did this
consume from my budgets". The page already renders excluded transactions in its Transactions
table, marked *(no budget impact)*, so including them is also what makes the table verifiable
by adding up the visible rows (FR-005).

**Consequence to document**: the per-account totals will not, in general, agree with the
budget totals above them on the same page. This is correct and must be stated in the user
documentation so it does not read as a bug.

## R3. How many pay periods

**Question**: The issue says "for each payperiod". One column, or several?

**Finding**: `PayPeriodView.get()` already renders five periods across the top in the
"Remaining Balances" table — previous, current, next, following, last — and already forces
each of their `overall_sums`, which builds each period's complete `_data` cache (transactions,
scheduled transactions, budget sums, overall sums). The per-account sums for all five periods
are therefore obtainable from data the request has already loaded.

**Decision**: Five columns, matching the "Remaining Balances" table exactly in order, labels,
suffixes, links and current-period emphasis.

**Rationale**: Satisfies both readings of the issue (the viewed period is one of the columns),
gives the period-over-period comparison that makes an account total actionable, and costs no
additional database work (SC-005).

**Alternatives considered**: A single column for the viewed period only. Rejected as a strict
subset of the above with no saving; the data for the other four periods is loaded either way.

## R4. Avoiding repeated pay period construction

**Finding**: `BiweeklyPayPeriod.next` and `.previous` construct a *new* object on every
access. The existing view writes `pp.next.next.next.overall_sums`, so the chain is rebuilt
from scratch for each of the five template arguments. Because only the terminal `.overall_sums`
triggers `_data`, exactly five periods' worth of data is computed today — but the intermediate
objects are discarded, and naively adding `pp.next.next.next.account_sums` alongside
`pp.next.next.next.overall_sums` would compute the *last* period's data a second time.

**Decision**: Bind the five period objects to local names once in `PayPeriodView.get()` and
read both `overall_sums` and `account_sums` from those bindings.

**Rationale**: Required for SC-005 (no extra round trips). The values passed to the template
are identical to those passed today, so FR-014 holds.

## R5. Shape of the returned data

**Decision**: `BiweeklyPayPeriod.account_sums` returns
`{account_id: {'name': str, 'total': Decimal}}` — one entry per account with at least one
transaction in the period.

**Rationale**: Carrying the name makes the property self-describing and directly assertable in
a unit test without a second query or a `Session`, which is what FR-013 asks for. Keying by id
lets the template build the `/accounts/<id>` link required by FR-010. Omitting accounts with no
activity, rather than emitting zeros for every account in the database, keeps the property
honest about what it observed; the *view* is the right place to decide that a row present in one
period must show a zero in another (FR-006), because only the view knows which periods are on
screen.

**Alternatives considered**: `{account_id: Decimal}` with names resolved by the view from the
`Account` query it already makes. Rejected: it makes the property untestable in isolation and
couples the numbers to a query the view happens to perform for an unrelated reason.

## R6. Rendering conventions

**Findings from the existing page** (`biweeklybudget/flaskapp/templates/payperiod.html`):

- Negative amounts use the `reddollars` filter with `|safe`, which wraps negatives in
  `<span class="text-danger">`; positives use `dollars`. The existing "Remaining Balances" row
  uses `reddollars`.
- The current period's column is marked with Bootstrap's `class="info"` on both the `th` and
  the `td`.
- Non-current period headers are `<a href="/payperiod/YYYY-MM-DD">` links carrying the same
  `(prev.)` / `(next)` suffix produced by `PayPeriodView.suffix_for_period()`.
- Tables are plain Bootstrap `table table-bordered` inside `div.table-responsive` inside a
  `div.panel`, each with a distinct `id` that the acceptance tests key off.

**Decision**: Follow all four conventions; give the new table `id="pp-acct-table"`. Reuse the
existing suffix and date values already passed to the template rather than recomputing them.

**Rationale**: Constitution's Technology & Security Constraints require new UI to follow the
existing Bootstrap/DataTables patterns rather than introduce a parallel style. A distinct `id`
is what makes the table addressable from acceptance tests.

## R7. Placement on the page

**Decision**: Below the existing "Remaining Balances" panel and the four summary tiles, in its
own full-width row, above the row holding the budget tables and the Transactions table.

**Rationale**: It is period-level context, like the tiles above it, rather than a breakdown of
one budget. Full width keeps five money columns plus an account name legible without horizontal
scrolling (spec edge case: very many accounts). Placing it in a new row of its own means no
existing markup moves, which is the cheapest way to satisfy FR-014 for the tests that locate
elements by id.

## R8. Test surface

**Findings**:

- `biweeklybudget/tests/unit/test_biweeklypayperiod.py::TestData::test_initial` asserts the
  *exact* dict `_data` returns. Adding an `account_sums` key requires updating that assertion —
  an expected, mechanical change, not a regression.
- Acceptance tests locate tables by `id` and compare `innerHTML` row by row via
  `AcceptanceHelper.tbody2elemlist()`. `TestCurrentPayPeriod` (test_payperiods.py) already
  builds a fixture period with transactions against accounts 1, 2 and 3, which is exactly the
  shape this table needs.
- No acceptance test on this page selects tables positionally, so inserting a new panel cannot
  displace an existing assertion.

**Decision**: Add unit tests for `_make_account_sums()` covering the sums themselves (including
scheduled transactions, split-budget transactions, and no-budget-impact transactions) and a
trivial property test for `account_sums` matching the style of `TestBudgetSums`; add acceptance
tests asserting the rendered table's contents, headers and links.

## R9. Schema and migrations

**Decision**: None required. No model changes, therefore no Alembic migration, therefore
constitution principle III does not engage.
