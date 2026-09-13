# Quickstart: validating Zoomable, Pannable Charts

## Automated

Environment variables and the test database as in `CLAUDE.md` ("Test Database Setup for
Development"). From a worktree, use the main checkout's venv `tox` (see project memory).

```bash
# Chart acceptance tests only, while iterating
tox -e acceptance -- -k "Chart or chart or BudgetSpending" > $SCRATCH/acc-charts.txt 2>&1

# The Test Gate (constitution II): all of these, to completion
tox -e py314      > $SCRATCH/py314.txt 2>&1
tox -e acceptance > $SCRATCH/acceptance.txt 2>&1
tox -e migrations > $SCRATCH/migrations.txt 2>&1   # confirms no model drift
tox -e docs       > $SCRATCH/docs.txt 2>&1
tox -e jsdoc      > $SCRATCH/jsdoc.txt 2>&1        # regenerates docs/source/jsdoc.*.rst
```

Expected: everything passes. The data-endpoint tests (`TestAcctBalanceChartData`,
`TestAcctBalanceChartLargeData`, the budget-spending endpoint tests) pass unchanged,
which shows FR-016 holds.

## Manual

Start the app against the test database (`flask rundev`, `FLASK_APP` as in `CLAUDE.md`)
and, for each of `/`, `/budgets` and `/fuel`:

1. **Zoom** (US1): drag across part of a chart. Only that date range is shown, and the
   value axis spans only those values. "Reset zoom" becomes enabled. Click it: the full
   view returns and the button is disabled again.
2. **Scroll isn't hijacked** (US1-6): with the pointer over a chart, scroll the wheel. The
   page scrolls and the chart doesn't change.
3. **Wheel zoom and pan** (US2): hold Ctrl and scroll over a chart: it zooms around the
   pointer. Hold Ctrl and drag: the view slides along the dates and stops at the first and
   last dates of the data.
4. **Legend** (US3): click a series in the legend. It is struck through, its line goes and
   the value axis rescales. Click again to bring it back. Zoom, then reset: hidden series stay
   hidden. Reload: everything is shown, at full view.
5. **Unchanged behaviour** (US4): hover shows the date and currency-formatted values; on
   `/`, the range buttons reload the chart and clear any zoom; on `/fuel`, adding a fill
   redraws both charts; resizing the window refits every chart to its panel.
6. **Offline** (SC-006): in the browser's dev tools, block every host but the app; reload.
   Everything still works.
7. **Donuts** (FR-017): on `/budgets/spending`, the six donuts show the same slices,
   colours, hover text and "no spending" messages as before, and the checkboxes still
   update them all.
