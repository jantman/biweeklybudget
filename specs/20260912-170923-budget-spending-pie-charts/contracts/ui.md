# Contract: Spending By Budget page

`GET /budgets/spending` renders `budget-spending.html`. The element IDs below are relied on
by the acceptance tests.

## Layout

```text
[notifications]
Panel "Budgets Included"                 #panel-budget-spending-selection
  one checkbox per budget                 input.budget-spending-toggle
                                            id="budget_spending_toggle_<budget id>"
                                            data-budget-id="<budget id>"
                                            label text = budget name (literal text)
Row of six panels (col-lg-4, col-md-6)   #panel-spending-<key>
  heading: "<name>" + "<start> to <end>"  #spending-<key>-title
  total                                   #spending-<key>-total   e.g. "$1,234.56"
  donut                                   #spending-<key>-chart
  "No spending in this period."           #spending-<key>-nodata  (hidden unless no slices)
  table                                   #spending-<key>-table
    tbody rows: Budget | Amount | Percent  (largest first)
  net credits                             #spending-<key>-credits (hidden if none)
    "<name>: -$10.00" per budget, labelled as net credits, not charted
```

`<key>` is the period key from the HTTP contract, e.g. `current_pay_period`.

## Behaviour

- On load: one fetch of the by-period endpoint. Checkboxes are built from `budgets`,
  ticked unless `omit_from_graphs`. All six panels are then drawn.
- On any checkbox `change`: all six panels are redrawn from the data already loaded, with
  no request.
- Currency is formatted with the page's existing `CURRENCY_SYMBOL` and `fmt_currency`
  helper, if one is available in `custom.js`. Otherwise it is formatted with the same
  conventions.
- Budget names are inserted with `.text()`, never as HTML.
- While the data is loading, the panels show nothing. If the request fails, an error
  message is shown in place of the charts.

## Links in

- `nav.html`: "Spending Charts" (`fa-pie-chart`), placed directly after "Budgets".
- `budgets.html`: a link to `/budgets/spending` in the heading row of the existing
  spending charts, with id `link-budget-spending`.
