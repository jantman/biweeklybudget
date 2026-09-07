# Contract: Per-Account Pay Period Totals

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-07

This feature exposes no new HTTP endpoint and changes no existing one. Its two contracts are a
Python property that other code and tests may rely on, and the HTML the pay period view renders.

## 1. Python contract — `BiweeklyPayPeriod.account_sums`

**Module**: `biweeklybudget/biweeklypayperiod.py`

```python
@property
def account_sums(self) -> dict:
    """
    {account_id: {'name': str, 'total': Decimal}}
    """
```

| Aspect | Guarantee |
|---|---|
| Return type | `dict`; keys `int` (`Account.id`), values `dict` with keys `'name'` (`str`) and `'total'` (`Decimal`). |
| Membership | Exactly the account ids appearing in this period's `transactions_list`. Never a zero-valued entry for an account with no activity. |
| Value | Sum of `amount` over every `transactions_list` entry for that account, with no filtering of any kind. |
| Sign | As stored: spending positive, income negative. |
| Cost | Zero database queries of its own. Computed in one pass over `transactions_list`. |
| Caching | Stored under `_data_cache['account_sums']` when `_data` is first built; cleared by `clear_cache()`. Repeated reads return the same object. |
| Stability | Adding this key to `_data_cache` is additive. `budget_sums`, `overall_sums`, `transactions_list` and every existing key are unchanged in value and in meaning. |

**Backwards compatibility**: `_data` gains one key. The only known consumer asserting the exact
shape of that dict is `tests/unit/test_biweeklypayperiod.py::TestData::test_initial`, updated as
part of this change.

## 2. Rendered HTML contract — the pay period view

**Route**: `GET /payperiod/<YYYY-MM-DD>` (unchanged; no new route, no new query parameter, no
change to any response header or status code).

A new panel is added to the page. Nothing existing is moved, renamed, reordered or removed.

### Structure

```html
<div class="panel panel-default">
  <div class="panel-heading">Per-Account Transaction Totals</div>
  <div class="table-responsive">
    <table class="table table-bordered" id="pp-acct-table">
      <thead>
        <tr>
          <th>Account</th>
          <th><a href="/payperiod/YYYY-MM-DD">YYYY-MM-DD <em>(prev.)</em></a></th>
          <th class="info">YYYY-MM-DD <em>(curr.)</em></th>
          <th><a href="/payperiod/YYYY-MM-DD">YYYY-MM-DD <em>(next)</em></a></th>
          <th><a href="/payperiod/YYYY-MM-DD">YYYY-MM-DD <em></em></a></th>
          <th><a href="/payperiod/YYYY-MM-DD">YYYY-MM-DD <em></em></a></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><a href="/accounts/1">BankOne</a></td>
          <td>$0.00</td>
          <td class="info">$123.45</td>
          <td>$0.00</td>
          <td>$0.00</td>
          <td>$0.00</td>
        </tr>
        <!-- ... one row per account with activity, ordered by name ... -->
        <tr>
          <td><strong>Total</strong></td>
          <td>$0.00</td>
          <td class="info">$123.45</td>
          <td>$0.00</td>
          <td>$0.00</td>
          <td>$0.00</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
```

### Guarantees

| Requirement | Guarantee |
|---|---|
| FR-001 | The table is present on every successful render of this route. |
| FR-002 | One `tbody` row per account with activity in any displayed period, plus the totals row. No row for any other account. |
| FR-003 | Five period columns after the Account column, in the order previous, current, next, following, last, with the same date labels and the same `(prev.)` / `(curr.)` / `(next)` suffixes as `#pay-period-table`. |
| FR-006 | Empty account/period combinations render `$0.00`, never blank. |
| FR-007 | Negative amounts render through the `reddollars` filter, i.e. `<span class="text-danger">-$1.23</span>`, matching the rest of the page. Non-negative amounts render as `$1.23`. |
| FR-008 | The current period's `th` and every current-period `td`, including the totals row's, carry `class="info"`. |
| FR-009 | The four non-current period headers are anchors to `/payperiod/<that period's start date>`. The current period's header is plain text, as in `#pay-period-table`. |
| FR-010 | Each account cell is an anchor to `/accounts/<account id>`. |
| FR-011 | The last `tbody` row is the totals row, labelled `<strong>Total</strong>` in the Account column. |
| FR-012 | Rows appear in ascending account-name order. |
| FR-014 | The ids `pay-period-table`, `pb-table`, `sb-table`, `trans-table`, `amt-income`, `amt-allocated`, `amt-spent`, `amt-remaining`, `btn-add-txn`, `btn-budg-txfr-periodic` and `btn-budg-txfr-standing` and their contents are byte-for-byte what they were before this change. |

### Non-guarantees

- The table's totals are **not** expected to agree with the budget totals elsewhere on the
  page. They are different sums over different sets, by design (research R2).
- No JavaScript is attached to this table. It is not a DataTable, has no sorting, filtering or
  paging, and adds no script to the page.
