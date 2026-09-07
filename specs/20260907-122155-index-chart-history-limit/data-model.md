# Phase 1 Data Model: Index Page Account Balances Chart — History Limiting

**Feature**: `specs/20260907-122155-index-chart-history-limit`
**Date**: 2026-09-07

## Schema changes

**None.** This feature changes only how existing records are queried and shaped for
display. No model in `biweeklybudget/models/` is added, removed, or altered, and therefore
**no Alembic migration is required** (constitution principle III is satisfied vacuously —
there is no model change to migrate).

The `migrations` tox environment must still pass, unchanged, as a check that this remains
true.

## Existing entities read by this feature

### `AccountBalance` (`biweeklybudget/models/account_balance.py`)

Read-only for this feature. Relevant columns:

| Column | Type | Use here |
|--------|------|----------|
| `account_id` | `Integer` FK → `accounts.id` | Groups rows into per-account series. Used **directly**, not via the `account` relationship, to avoid the N+1 load described in research R1. |
| `ledger` | `Numeric(10,4)`, nullable | The plotted value. `NULL` is rendered as `0.0`, exactly as today. |
| `overall_date` | `UtcDateTime` | The x-axis value and the column the window filter and ordering apply to. |

The `AccountBalance.account` relationship is deliberately **not** traversed in the chart
view.

### `Account` (`biweeklybudget/models/account.py`)

Read-only. Only `id` and `name` are used, loaded once into an `{id: name}` dict. All
accounts are included, active or not, matching current behaviour.

## Derived structures (in-memory only, not persisted)

### Chart window

The span of history the request covers.

| Field | Type | Rules |
|-------|------|-------|
| `days` | int | `> 0`: that many days back from now. `0`: all recorded history. Any other input (absent, non-numeric, negative) resolves to `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS`. |
| `window_start` | datetime or `None` | `now - timedelta(days=days)`, or `None` when `days == 0`. |

### Balance carry-over map (the forward-fill seed)

`{account_name: float or None}` — each account's most recent `ledger` strictly before
`window_start`, or `None` for an account with no such record.

Purpose: an account whose latest balance predates the window would otherwise be plotted as
absent or zero, which for a financial chart asserts something false. Rules:

- Populated by a query bounded by account count, never by history size.
- `None` for an account with no pre-window record — that account's line legitimately begins
  where its data begins and is not back-filled (spec edge case: account created part-way
  through the window).
- When `days == 0` there is no window start and the map is empty; every account's line
  starts at its own first record.

### Date row

One entry per distinct `overall_date` (as `YYYY-MM-DD`) within the window.

| Field | Type | Rules |
|-------|------|-------|
| `date` | `str`, `YYYY-MM-DD` | Morris `xkey`. Distinct and ascending across the series. |
| *(one key per account name)* | `float` or `None` | That account's `ledger` on that date, or its carried-forward previous value, or `None` if it has no value yet. |

Multiple `AccountBalance` rows for the same account on the same calendar date collapse to
the last one seen in ascending `overall_date` order — unchanged from current behaviour.

### Sampled series

The date rows actually returned, after the interval sampling of research R4.

Invariants, each of which is a unit test:

1. `len(sampled) <= max_points` for every input.
2. When `len(rows) <= max_points`, `sampled == rows` — identical objects, in order, nothing
   dropped and nothing added (FR-013: small installations see no change at all).
3. `sampled[-1] is rows[-1]` whenever `rows` is non-empty (FR-005: the present is always
   plotted).
4. Order is preserved and ascending.
5. Empty input yields empty output, with no error (FR-012).

Stride: `n = ceil(len(rows) / max_points)`; take `rows[::n]`; append `rows[-1]` if the
stride did not already land on it.

## Configuration entities

Two new module-level constants in `biweeklybudget/settings.py`, mirrored in
`settings_example.py`, and both added to `_INT_VARS` so the existing environment-variable
override path applies.

| Setting | Type | Default | Meaning |
|---------|------|---------|---------|
| `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` | int | `365` | Days of history the chart shows on page load. `0` means all history by default. |
| `ACCOUNT_BALANCE_CHART_MAX_POINTS` | int | `300` | Hard ceiling on dates returned for any request. |

Neither is added to `_REQUIRED_VARS`: an existing settings module that predates this
feature must keep working and pick up the defaults.

## Relationship to `BiweeklyPayPeriod` and budget math

None. This feature touches no pay-period arithmetic, budget allocation, interest, or
payoff calculation, and changes no stored value. It is a presentation change over
already-computed balances.
