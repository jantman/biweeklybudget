# Contract: Spending By Budget Per Period chart data

`GET /ajax/chart-data/budget-spending/by-period`

Handled by `BudgetSpendingChartView` with `aggregation == 'by-period'`. Takes no
parameters. Read-only.

## Response: 200, `application/json`

```json
{
  "budgets": [
    {"id": 1, "name": "Periodic1", "omit_from_graphs": false},
    {"id": 4, "name": "Standing1", "omit_from_graphs": true}
  ],
  "periods": [
    {
      "key": "current_pay_period",
      "name": "Current Pay Period",
      "start_date": "2017-07-21",
      "end_date": "2017-08-03",
      "spending": [
        {"budget_id": 1, "amount": 123.45},
        {"budget_id": 4, "amount": -10.0}
      ]
    }
  ]
}
```

- `budgets`: every non-income budget with a non-zero net in at least one period, sorted by
  `name` (ties by `id`). This list defines the checkboxes and each budget's colour index.
- `periods`: exactly six, in the order `current_pay_period`, `previous_pay_period`,
  `current_month`, `previous_month`, `current_year`, `previous_year`. Dates are
  `YYYY-MM-DD`, both inclusive.
- `spending`: one entry per budget with a non-zero net in that period, in no particular
  order. `amount` is a JSON number, the net rounded to cents. Positive means spent;
  negative means a net credit. Every `budget_id` appears in `budgets`.
- No exclusion is applied here beyond research R1. `omit_from_graphs` budgets **are**
  included, with their flag, so the page can offer to tick them back in.

## Unchanged

- `GET /ajax/chart-data/budget-spending/by-pay-period` and `.../by-month` return exactly
  what they return today.
- Any other `aggregation` value still raises, as today.
