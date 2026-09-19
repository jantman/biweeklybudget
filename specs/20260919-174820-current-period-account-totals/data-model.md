# Phase 1 Data Model: Current-Period Per-Account Transaction Totals

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-19

## Persistent model: unchanged

**No database entity is added, removed or altered by this feature.** Nothing under
`biweeklybudget/models/` is touched, no column changes type or nullability, and no
Alembic migration is produced. Constitution principle III does not engage.

The existing entities the feature reads through are:

| Entity | Role here | Changed? |
|--------|-----------|----------|
| `Account` | Supplies the id and name behind each column. | No |
| `Transaction` / `ScheduledTransaction` | The rows a period's per-account totals sum over. | No |
| `BudgetTransaction` | Irrelevant here — these totals are per *account*, and deliberately ignore the budget-impact exclusions. | No |

## Computed model: unchanged

`BiweeklyPayPeriod.account_sums` is the one computation this feature depends on, and it
is **not** modified. Its shape today, and after this change:

```python
{
    account_id: {'name': str, 'total': Decimal},
    ...
}
```

with accounts absent rather than zero when the period saw no transactions for them. Every
number the panel displays comes from here, so the amounts a user sees for the viewed
period are byte-for-byte the ones the current-period column showed before (SC-002).

## View model: this is what changes

### Before

`build_account_period_sums(periods)` produced a two-dimensional model — accounts down,
periods across:

```python
rows = [
    {'id': 1, 'name': 'BankOne', 'totals': [Decimal, Decimal, Decimal, Decimal, Decimal]},
    ...
]
column_totals = [Decimal, Decimal, Decimal, Decimal, Decimal]
```

An account appeared if it had activity in *any* of the five periods, and the `totals`
list carried an explicit `Decimal('0.0')` for each period in which it had none.

### After

`build_account_sums(period)` produces a one-dimensional model — accounts across, one
amount each:

```python
columns = [
    {'id': 1, 'name': 'BankOne', 'total': Decimal('-2215.67')},
    {'id': 3, 'name': 'CashOne', 'total': Decimal('100.00')},
]
total = Decimal('-2115.67')
```

### Entities in the view model

**Account column** — one per account with activity in the viewed period.

| Field | Type | Source | Rules |
|-------|------|--------|-------|
| `id` | `int` | `account_sums` key | Used to build `/accounts/{id}`; never displayed as a number. |
| `name` | `str` | `account_sums[id]['name']` | The sort key, ascending. Displayed as the column header's link text. |
| `total` | `Decimal` | `account_sums[id]['total']` | Sum of that account's transactions in the period. Negative for net income, and may be exactly zero without removing the column. |

**Grand total** — a single `Decimal`, the sum of the columns' `total` values, or
`Decimal('0.0')` when there are no columns.

### Derivation rules

- **DR-1**: The set of columns is the key set of the viewed period's `account_sums` —
  a straight per-period grouping, with the five-period union removed.
- **DR-2**: No zero-filling. The old model needed explicit zeros because a row spanned
  periods the account was absent from; a single-period model has no such gaps
  (see [research.md](./research.md) D3).
- **DR-3**: Ordering is by account name ascending, as before. The dimension that ordering
  applies to changes from rows to columns; the ordering itself does not.
- **DR-4**: All arithmetic stays in `Decimal`. Money never becomes a float on this path.
- **DR-5**: The model is read-only and per-request. Nothing is cached beyond the pay
  period's own existing `_data_cache`, and nothing is written back.

## State transitions

None. This is a read-only projection built fresh on each render of the pay period view.
