# Contract: The Cash Position Page

**Feature**: [../spec.md](../spec.md) | **URL**: `GET /cash-position`

The page is read-only: no form, no POST, no editing. It renders the statement
from [cash-position-statement.md](./cash-position-statement.md).

This contract fixes the element IDs the acceptance tests target. It is a DOM
contract, not a visual one; layout follows the existing Bootstrap 3 panel
conventions.

## Response

`200 OK`, `text/html`, extending `base.html` and including
`notifications.html` like every other page. It renders for **every** database
state, including an empty one (FR-022).

## Structure

| Element ID | Contents |
|---|---|
| `cash-position-waterfall` | the five terms and two subtotals, in the contract's order |
| `waterfall-budget-accounts` | term 1, with `data-amount` |
| `waterfall-unreconciled` | term 2 |
| `waterfall-credit` | term 3 |
| `subtotal-net-liquid` | **Net liquid position** |
| `waterfall-standing` | term 4 |
| `waterfall-payperiod` | term 5 |
| `total-uncommitted` | **Truly unallocated / uncommitted funds** |
| `table-budget-account-detail` | per-account: name, ledger, unreconciled, projected, as-of |
| `table-credit-account-detail` | per-account: name, balance, as-of |
| `table-standing-budget-detail` | per-budget: name, current balance |
| `cash-position-diagnostics` | unlinked accounts and coverage groups |
| `table-unlinked-accounts` | FR-017 |
| `coverage-group-<n>` | one per group (FR-018) |
| `diagnostics-all-clear` | shown only when there is nothing to report (FR-021) |

Each row carries `data-amount` with the raw signed decimal, so tests assert on
values rather than on formatted currency strings.

## Links (FR-012)

| From | To |
|---|---|
| term 1, term 3, and each account row | `/accounts` and `/accounts/<id>` |
| term 2 | `/reconcile` |
| term 4, and each budget row | `/budgets` and `/budgets/<id>` |
| term 5 | `/pay_period_for` |

## Rendering rules

- Amounts use the `dollars` filter; negative amounts use `reddollars`, so they
  are visually distinct (FR-007).
- An account with no recorded balance shows `no balance recorded`, not
  `$0.00`, and its row carries `data-counted="false"` (FR-023).
- Each itemized table shows its own total row, and that total equals the
  corresponding waterfall term (FR-011).
- A coverage group with one account is labelled as a per-account delta; a
  group with several says explicitly that the delta is reported for the group
  because the application records no split (FR-019).
- Accounts in a group that do not contribute to the waterfall — inactive, or
  not budget-funding — are shown marked as not counted, never dropped.
- The page states the pay period it covers and each balance's as-of date
  (FR-024).

## Navigation and banner

- `nav.html` gains `('/cash-position', 'Cash Position')` immediately after
  `('/', 'Home')`. The exact nav list assertion in
  `tests/acceptance/flaskapp/views/test_base_template.py` must be updated in
  the same change.
- The notification banner gains a `/cash-position` link and is otherwise
  unchanged (FR-025).
