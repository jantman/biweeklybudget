# Contract: Account Balances Chart Endpoint

**Endpoint**: `GET /ajax/chart-data/account-balances`
**View**: `AcctBalanaceChartView` — `biweeklybudget/flaskapp/views/index.py`
**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-19

This endpoint is read by the dashboard chart and, per its own docstring, by external
scripts. This contract states exactly what this feature changes and — at greater length —
what it does not.

## Request

Unchanged. One optional query parameter, `days`: days of history counting back from now,
`0` meaning all recorded history, anything unparseable falling back to
`settings.ACCOUNT_BALANCE_CHART_DEFAULT_DAYS`. Never returns 4xx for a bad `days`.

## Response

Unchanged in shape:

```json
{
  "data": [ {"date": "2017-07-27", "<account name>": 1234.56, "...": 0.0} ],
  "keys": ["<account name>", "..."]
}
```

## What changes

**Only the set of accounts.** `keys` lists the **active** Accounts, sorted by name; each
row in `data` carries one entry per active Account plus `date`.

- **C-1** (FR-001): an inactive Account's name does not appear in `keys`.
- **C-2** (FR-002): an inactive Account's name does not appear as a key in any `data` row — not as a recorded value, and not as a forward-filled or pre-window seeded value.
- **C-3**: with every Account inactive, `keys` is `[]`, `data` rows carry only `date`, and the status is 200.

## What does not change

- **C-4** (FR-003): for every Account that remains, every value in every row is identical to what this endpoint returns today.
- **C-5** (FR-003): **the set of dates in `data` is identical to today's**, for every `days`. A date exists in the response because *some* `AccountBalance` row exists on it — including one belonging to an inactive Account. Such a date is still returned; its row simply carries no entry for that account, and the remaining accounts carry their forward-filled values. This is why the `AccountBalance` query is **not** narrowed to active accounts (R4): narrowing it would silently drop such a date from the chart's x-axis.
- **C-6**: `data` stays ascending by date with no duplicates; the most recent date in the window is still last.
- **C-7**: the `ACCOUNT_BALANCE_CHART_MAX_POINTS` cap, the sampling, and `days=0` returning all history are untouched.
- **C-8**: an account with no balance inside the window still carries its last value from before the window forward, rather than reading as zero — for active accounts. Inactive accounts are not seeded at all.
- **C-9** (FR-004): `AccountBalance` rows for inactive Accounts remain stored, and encountering one is not an error — it is skipped. Reactivating an Account restores its full line.
- **C-10**: a `NULL` ledger is still reported as `0.0`; with no balance records at all, `data` is empty and the status is 200.

## Implementation note

Every one of C-1, C-2 and C-3 follows from filtering the single `accounts` map that
`keys`, `datedict`, the forward-fill loop and `_balances_before()` are all derived from.
`_balances_before()` needs no change: it already skips ids absent from `accounts`
(`index.py:357-359`), so it stops seeding inactive accounts automatically. The one added
guard is in `get()`, where a balance row for an account absent from the map is skipped
rather than raising `KeyError`.

## Verification

- `keys` for the sample data is `['BankOne', 'BankTwoStale', 'CreditOne', 'CreditTwo', 'InvestmentOne']` — `'DisabledBank'` (inactive, and holding a balance record) is gone.
- The response with an account active and the response after deactivating it differ in exactly one key per row, and in `keys`; the date list and every other value are equal.
