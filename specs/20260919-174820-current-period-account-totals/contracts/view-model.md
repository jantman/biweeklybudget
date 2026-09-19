# Contract: Per-Account Totals View Model and Rendered Table

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-19

This feature exposes no HTTP API and no new endpoint. Its contracts are two: the Python
function that builds the table's view model, and the HTML the template renders from it.
Both are consumed only inside this repository — the function by one view, the markup by
the acceptance suite — but both are pinned here because the tests assert against them
exactly.

## 1. `build_account_sums(period)`

**Module**: `biweeklybudget/flaskapp/views/payperiods.py`

**Replaces**: `build_account_period_sums(periods) -> (rows, column_totals)`

### Signature

```python
def build_account_sums(period):
    """-> (columns, total)"""
```

**Parameter**

| Name | Type | Meaning |
|------|------|---------|
| `period` | `BiweeklyPayPeriod` | The single pay period being viewed. |

**Returns** a 2-tuple `(columns, total)`:

| Element | Type | Contract |
|---------|------|----------|
| `columns` | `list` of `dict` | One entry per account with at least one transaction in `period`, ordered ascending by account name. |
| `total` | `Decimal` | The sum of every entry's `total`. `Decimal('0.0')` when `columns` is empty. |

Each entry of `columns`:

| Key | Type | Contract |
|-----|------|----------|
| `id` | `int` | The account's database id, used to build its link. |
| `name` | `str` | The account's name, as reported by the period. |
| `total` | `Decimal` | The sum of that account's transactions in `period`. May be negative (income) or exactly zero. |

### Rules

- **C-1**: `columns` contains exactly the accounts present in `period.account_sums` —
  no more (no zero-filling for quiet accounts) and no fewer (an account whose
  transactions net to `Decimal('0.00')` keeps its entry).
- **C-2**: Ordering is by `name` ascending. Ties are not expected; account names are
  unique.
- **C-3**: `total` equals `sum(c['total'] for c in columns)`, exactly, in `Decimal`
  arithmetic — no float conversion anywhere on the path.
- **C-4**: The function reads `period.account_sums` and nothing else. It issues no
  queries of its own and mutates no argument.
- **C-5**: An empty period returns `([], Decimal('0.0'))` rather than raising.

### Consumed by

`PayPeriodView.get()`, which passes the results to `payperiod.html` as:

| Template variable | Value |
|-------------------|-------|
| `acct_sums` | `columns` |
| `acct_total` | `total` |

## 2. Rendered table: `#pp-acct-table`

**Template**: `biweeklybudget/flaskapp/templates/payperiod.html`

The table keeps its id, its `table table-bordered` classes, its enclosing
`div.table-responsive`, and its `div.panel.panel-default` with the heading text
`Per-Account Transaction Totals`.

### Structure

```html
<table class="table table-bordered" id="pp-acct-table">
  <thead>
    <tr>
      <!-- one per entry of acct_sums, in order -->
      <th><a href="/accounts/{id}">{name}</a></th>
      ...
      <th>Total</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <!-- one per entry of acct_sums, in the same order -->
      <td>{total|reddollars}</td>
      ...
      <td>{acct_total|reddollars}</td>
    </tr>
  </tbody>
</table>
```

### Rules

- **H-1**: Exactly one `<tr>` in `<thead>` and exactly one `<tr>` in `<tbody>`, for any
  number of accounts — including zero.
- **H-2**: `<thead>` has `len(acct_sums) + 1` cells; `<tbody>`'s row has the same count.
  The nth body cell is the nth header cell's account, and the last of each is the total.
- **H-3**: Every account header cell is an `<a href="/accounts/{id}">` around the account
  name, and nothing else.
- **H-4**: The final header cell is the literal text `Total`, not a link.
- **H-5**: Amounts are rendered through the `reddollars` filter with `|safe`, so
  negatives arrive as `<span class="text-danger">-$N,NNN.NN</span>` and non-negatives as
  `$N,NNN.NN`. This is unchanged from the five-column table.
- **H-6**: No cell anywhere in the table links to, or names, any pay period — no
  `/payperiod/` href, no date. (FR-009)
- **H-7**: No cell carries `class="info"`; the current-period emphasis is gone. (research D2)
- **H-8**: With `acct_sums` empty, the table still renders: a `<thead>` row of the single
  `Total` cell and a `<tbody>` row of the single `$0.00` cell. (FR-010)
- **H-9**: No DataTables initialisation is attached; the table's class list never gains
  `dataTable` and no `_wrapper` div appears around it.

### Example

For a period in which `BankOne` nets `-2215.67` and `CashOne` nets `100.00`:

| Header | `BankOne` | `CashOne` | `Total` |
|--------|-----------|-----------|---------|
| Amounts | `-$2,215.67` (red) | `$100.00` | `-$2,115.67` (red) |

## Compatibility

Nothing outside this repository consumes either contract. `pp-acct-table` is retained as
the table's id so existing acceptance selectors and any operator CSS keep working; the
*shape* behind that id changes, which is the point of the feature, and every test that
asserted the old shape is rewritten rather than kept passing.
