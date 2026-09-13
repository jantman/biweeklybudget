# Data Model: Zoomable, Pannable Charts

No stored data changes. No table, column, model or migration is added or altered, and
the chart data endpoints keep their current responses (FR-016). Everything below exists
only in the browser, for as long as a page is open.

## Chart data (input, unchanged)

Each of the five line charts is fed by an existing endpoint that returns:

```json
{
  "keys": ["Series A", "Series B"],
  "data": [
    {"date": "2017-07-15", "Series A": 123.45, "Series B": 10.0},
    {"date": "2017-07-26", "Series A": 130.00}
  ]
}
```

| Endpoint | Page / chart | `date` format | Series (`keys`) |
|----------|--------------|---------------|-----------------|
| `/ajax/chart-data/account-balances?days=N` | Index / Account Balances | `YYYY-MM-DD` | account names |
| `/ajax/chart-data/budget-spending/by-pay-period` | Budgets / Per Pay Period | `YYYY-MM-DD` (pay period start) | budget names |
| `/ajax/chart-data/budget-spending/by-month` | Budgets / Per Calendar Month | `YYYY-MM` | budget names |
| `/ajax/chart-data/fuel-economy` | Fuel Log / Fuel Economy | `YYYY-MM-DD` | vehicle names |
| `/ajax/chart-data/fuel-prices` | Fuel Log / Fuel Prices | `YYYY-MM-DD` | fixed: `["price"]` |

A row may lack a key: that series has no value on that date (a gap, not a zero).

The donut charts' input, `/ajax/chart-data/budget-spending/by-period`, is also unchanged.

## Line series (derived, in the browser)

One per entry in `keys`, built from the rows above.

| Field | Meaning |
|-------|---------|
| label | the key: account, budget or vehicle name, shown as literal text |
| points | `(date, value)` for every row that has the key, in date order; rows without it contribute no point, so the line joins the dates either side of a gap |
| colour | fixed per series index on the chart; used by the line, its legend entry and its tooltip entry |
| hidden | whether the operator has hidden it from the legend; starts `false` |

**Rules**

- A value of `null`, or a missing key, is a gap and never plotted as zero.
- Dates are parsed as local calendar dates, so a point lands on the day in its `date`
  whatever the browser's time zone.

## Chart view (state, in the browser)

One per line chart on the open page (spec Key Entities).

| Field | Meaning | Initial value |
|-------|---------|---------------|
| visible date range | first and last date on the date axis | the full range of the data |
| hidden series | series hidden by legend clicks | none |
| zoomed | whether the visible date range differs from the full range | `false` |

**Derived**

- **Value axis range**: spans the values of the visible (not hidden) series whose points
  fall inside the visible date range, plus the axis's normal padding (FR-005, FR-007).
- **Reset control enabled**: exactly when `zoomed` is `true` (FR-006).

**Limits**

- The visible date range never extends past the first or last date of the data (FR-004).
- The visible date range is never narrower than the widest gap between consecutive dates
  in the data. Any window at least that wide contains a data point, so the chart never
  zooms into a stretch with nothing to show (spec Edge Cases).

**Transitions**

| Event | Effect |
|-------|--------|
| page load | full range, no hidden series |
| drag-select | visible range becomes the selection, clamped to the limits |
| modifier + wheel | visible range narrows or widens around the pointer, clamped |
| modifier + drag (pan) | visible range shifts, keeping its width, clamped at the data's ends |
| reset control | visible range returns to the full range; hidden series unchanged |
| legend click | toggles the series' `hidden`; visible range unchanged |
| new data loaded (range button, fuel fill added) | chart redrawn from the new data at its full range; the view resets |
| window resize | chart redrawn at its panel's width; the view is kept |
| page reload | back to the initial values; nothing is saved (FR-010) |
