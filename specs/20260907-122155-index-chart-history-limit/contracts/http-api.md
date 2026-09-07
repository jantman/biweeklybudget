# Contract: `GET /ajax/chart-data/account-balances`

**Feature**: `specs/20260907-122155-index-chart-history-limit`
**View**: `biweeklybudget.flaskapp.views.index.AcctBalanaceChartView`
**Status of change**: backward-compatible extension — one new optional query parameter; the
response shape is unchanged.

## Request

```
GET /ajax/chart-data/account-balances[?days=<int>]
```

### Query parameters

| Name | Type | Required | Default | Meaning |
|------|------|----------|---------|---------|
| `days` | integer | No | `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` (ships as `365`) | Number of days of history to return, counting back from now. `0` means all recorded history. |

### Parameter resolution rules

| Input | Resolves to |
|-------|-------------|
| absent | the configured default |
| `0` | all recorded history, no lower date bound |
| positive integer | that many days back from now |
| negative integer | the configured default |
| non-numeric (`"abc"`, `""`, `"1.5"`) | the configured default |
| repeated (`?days=30&days=90`) | first value, per Flask's `request.args.get` |

Bad input never produces a `4xx` or a traceback. A chart endpoint with no side effects is
better served by showing the default view than by refusing to answer (FR-010).

**Existing callers that send no `days` parameter continue to work**, but now receive the
default window rather than all history. This is the intended behaviour change of the
feature, and is stated here because it is the one way in which the contract is not purely
additive. `days=0` restores the old response exactly, modulo sampling.

## Response

`200 OK`, `Content-Type: application/json`. Shape unchanged from the current
implementation:

```json
{
  "data": [
    {"date": "2025-09-08", "BankOne": 12789.01, "CreditOne": -952.06},
    {"date": "2025-09-15", "BankOne": 12500.00, "CreditOne": -960.12}
  ],
  "keys": ["BankOne", "CreditOne"]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `data` | array of objects | One object per sampled date, ascending by `date`. Each has a `date` key (`YYYY-MM-DD`) plus one key per account name. |
| `keys` | array of strings | Account names, sorted. The Morris `ykeys`/`labels`. Every account is listed, active or not — unchanged from today. |

### Response guarantees

- **G1**: `len(data) <= ACCOUNT_BALANCE_CHART_MAX_POINTS`, for every request, at every
  history size, including `days=0`. (FR-003, SC-002)
- **G2**: `data` is ascending by `date`, with no duplicate dates.
- **G3**: When the window contains at most `ACCOUNT_BALANCE_CHART_MAX_POINTS` distinct
  dates, every one of them appears — no sampling is applied. (FR-013)
- **G4**: When `data` is non-empty, its last element is the latest balance date within the
  window. Sampling never drops the most recent point. (FR-005)
- **G5**: Every account in `keys` has a value on every element of `data` except where it
  has no known balance at or before that date, in which case the value is `null`. An
  account with no in-window record but a record before the window carries that earlier
  value forward and is never rendered as `0`. (FR-011)
- **G6**: A `ledger` stored as `NULL` is reported as `0.0`, unchanged from today.
- **G7**: With no balance records at all, the response is
  `{"data": [], "keys": [...]}` with HTTP `200` — not an error. (FR-012)

### Errors

None specific to this endpoint. It performs no writes and has no failure mode of its own
beyond a database outage, which surfaces as the application's ordinary `500`.

## Client contract (`biweeklybudget/flaskapp/static/js/index.js`)

- On page load, fetch with no `days` parameter and draw a `Morris.Line` into
  `#account-balance-chart`.
- The range control is a Bootstrap 3 `btn-group` inside the "Account Balances" panel
  heading, `id="account-balance-chart-ranges"`, one `<button>` per offered range carrying
  `data-days`. The button matching the configured default carries the `active` class on
  load (FR-009).

  | Label | `data-days` |
  |-------|-------------|
  | 1m | 30 |
  | 3m | 90 |
  | 6m | 180 |
  | 1y | 365 |
  | 2y | 730 |
  | 5y | 1825 |
  | All | 0 |

- Clicking a button re-fetches with that `days` value, moves `active` to the clicked
  button, and calls `setData()` on the existing chart instance — no page navigation and no
  chart re-instantiation (FR-008).
- An empty `data` array renders a plain "No account balance data to display." message in
  the panel body in place of the chart (FR-012, G7).
- `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` reaches the page as a JavaScript variable emitted by
  `index.html` from the `settings` template context, following the `CURRENCY_SYMBOL`
  precedent in `base.html`.
