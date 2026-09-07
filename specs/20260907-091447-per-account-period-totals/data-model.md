# Phase 1 Data Model: Per-Account Transaction Totals Per Pay Period

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-07

## Persistent schema

**No change.** No table, column, index or constraint is added, altered or removed, and no
file under `biweeklybudget/models/` is touched. No Alembic migration accompanies this feature.

The feature is a new derived view over records that already exist:

| Existing entity | Attribute used | Role |
|---|---|---|
| `Account` | `id`, `name` | Identifies a row; `id` builds the `/accounts/<id>` link, `name` is the label and the row sort key. |
| `Transaction` | `account_id`, `account.name`, `actual_amount` | Contributes its amount to one cell. |
| `ScheduledTransaction` | `account_id`, `account.name`, `amount` | Contributes its amount to one cell for each occurrence the period projects, unless already converted to a `Transaction`. |
| `BiweeklyPayPeriod` | `start_date`, `end_date` | Identifies a column and bounds which transactions fall in it. |

All of the above are read through the existing `BiweeklyPayPeriod.transactions_list`, which
already resolves scheduled-transaction projection, per-period and weekly occurrence counts, and
de-duplication of scheduled transactions that have become real ones.

## Derived structure 1: `BiweeklyPayPeriod.account_sums`

The new unit of computation. One instance per pay period.

```python
{
    account_id: {          # int — Account.id
        'name': str,       # Account.name, as shown in the page's Transactions table
        'total': Decimal   # sum of transactions_list amounts for this account
    },
    ...
}
```

**Membership rule**: an `account_id` appears if and only if at least one entry of that period's
`transactions_list` carries it. Accounts with no activity in the period are absent — not present
with a zero.

**Amount rule**: `total` is the unfiltered sum of the `amount` of every entry in
`transactions_list` whose `account_id` matches. It includes:

- real `Transaction` rows and projected `ScheduledTransaction` occurrences alike;
- transactions excluded from budget arithmetic (`no_budget_impact` true, which covers credit
  card payments) — see research R2;
- every budget split of a transaction exactly once, because the amount summed is the
  transaction's own `amount`, not the per-budget split amounts.

**Sign**: unchanged from the source records. Spending is positive, income is negative, so a
`total` may be positive, negative or zero.

**Invariants** (each is an assertion in the unit tests):

1. `sum(v['total'] for v in account_sums.values())` equals the sum of `t['amount']` for every
   `t` in `transactions_list`. Nothing is dropped and nothing is counted twice.
2. Every `account_id` key appears in at least one entry of `transactions_list`, and every
   `account_id` in `transactions_list` appears as a key.
3. `account_sums[i]['name']` equals the `account_name` of the transactions summed into it.
4. The result is cached in `_data_cache` alongside `budget_sums` and `overall_sums`, and is
   discarded by `clear_cache()` with them.

**Relationship to `budget_sums`**: none. The two are deliberately different totals over
overlapping sets — `budget_sums` excludes no-budget-impact transactions, `account_sums` does
not — and they are not expected to reconcile with each other.

## Derived structure 2: the view's cross-period table model

Assembled in `PayPeriodView.get()` from the five periods' `account_sums`, and consumed by the
template. It exists so that the template performs no arithmetic and no lookups that can fail.

```python
acct_period_sums = [
    {
        'id': int,                # Account.id
        'name': str,              # Account.name
        'totals': [Decimal] * 5   # one per displayed period, in column order
    },
    ...                           # sorted by name
]

acct_period_totals = [Decimal] * 5   # column totals, in the same order
```

**Column order** is fixed and identical to the existing "Remaining Balances" table:
previous, current, next, following, last.

**Row membership**: the union of the account ids present in any of the five periods'
`account_sums`. An account absent from a given period contributes `Decimal('0.0')` in that
position (FR-006), which is where the zeros the property omits are supplied.

**Row order**: ascending by account name (FR-012), giving an ordering that is stable across
page loads and identical whichever period is being viewed.

**Name resolution**: taken from whichever period's `account_sums` entry supplies it. An
account's name is a single value on a single row, so all five agree; the first found is used.

**Column totals**: `acct_period_totals[i]` is the sum of `row['totals'][i]` over all rows
(FR-011). For the current-period column this equals that period's
`sum(v['total'] for v in account_sums.values())`, which is invariant 1 above — this is the
identity asserted by SC-003.

**Empty case**: when no account has activity in any of the five periods, `acct_period_sums` is
`[]` and `acct_period_totals` is five zeros. The table still renders, with headers and the
totals row (spec edge case 1).
