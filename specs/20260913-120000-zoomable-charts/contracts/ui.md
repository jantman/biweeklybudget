# UI Contract: Zoomable, Pannable Charts

This is what tests, the screenshot script and the templates can rely on. The data endpoints
are unchanged (FR-016). Their contract is in `docs/source/http_api.rst` and is not repeated here.

## Vendored assets

Served from `/static/chartjs/`, in this load order, on every page with a chart:

1. `chart.umd.min.js` (defines global `Chart`)
2. `chartjs-adapter-date-fns.bundle.min.js`
3. `hammer.min.js` (defines global `Hammer`; must precede the zoom plugin)
4. `chartjs-plugin-zoom.min.js` (registers itself with `Chart`)

Then `/static/js/charts.js` on the three line-chart pages. No page loads Morris,
Raphael or `morris.css`.

## Line chart containers

The existing container IDs stay as they are:

| Page | Container ID | Currency | Tooltip date format |
|------|--------------|----------|---------------------|
| `/` | `account-balance-chart` | yes | `yyyy-MM-dd` |
| `/budgets` | `budget-per-period-chart` | yes | `yyyy-MM-dd` |
| `/budgets` | `budget-per-month-chart` | yes | `yyyy-MM` |
| `/fuel` | `mpg-chart` | no (2 decimals) | `yyyy-MM-dd` |
| `/fuel` | `fuel-price-chart` | yes | `yyyy-MM-dd` |

`lineChartCreate(id, …)` fills container `#<id>` with:

```html
<div class="chart-controls">
  <span class="chart-hint text-muted">Drag to zoom · Ctrl+drag to pan · Ctrl+scroll to zoom in/out</span>
  <button type="button" id="<id>-reset" class="btn btn-default btn-xs chart-reset" disabled>Reset zoom</button>
</div>
<div class="chart-canvas-wrap">
  <canvas id="<id>-canvas"></canvas>
</div>
```

Each container holds exactly one `<canvas>`, however often its data is reloaded.

`#account-balance-chart-nodata` is unchanged. When shown, `#account-balance-chart` is hidden.

## Chart state (read by tests through `Chart.getChart('<id>-canvas')`)

| Property / call | Meaning |
|-----------------|---------|
| `data.datasets[i].label` | series name (an endpoint `keys` entry), in `keys` order |
| `data.datasets[i].data` | `[{x: 'YYYY-MM-DD' or 'YYYY-MM', y: number}, …]`, present values only |
| `scales.x.min`, `scales.x.max` | visible date range, epoch milliseconds |
| `scales.y.min`, `scales.y.max` | value axis range |
| `isZoomedOrPanned()` | `true` when zoomed or panned, i.e. not at full view |
| `isDatasetVisible(i)` | `false` once hidden from the legend |
| `resetZoom()` | same as clicking the reset control |
| `legend.legendItems`, `legend.legendHitBoxes` | legend entries and their clickable boxes, canvas pixels |

## JavaScript API (`static/js/charts.js`)

| Function | Contract |
|----------|----------|
| `lineChartCreate(elementId, ajaxdata, opts)` | Builds the markup above inside `#elementId` and returns the Chart.js instance. `ajaxdata` is an endpoint response (`{keys, data}`). `opts.currency` (bool) formats values with `fmt_currency`. `opts.dateFormat` is the tooltip date format. `opts.minUnit` (default `'day'`) is the smallest unit the date axis labels: `'month'` for the monthly chart. The axis never labels times of day. |
| `lineChartSetData(chart, ajaxdata)` | Replaces the chart's datasets with those from `ajaxdata`, recalculates the zoom limits, returns to full view and refreshes the reset control. The canvas and instance are kept. |
| `lineChartDatasets(ajaxdata)` | Pure: endpoint response → Chart.js datasets (labels, points, colours). |
| `CHART_COLORS` | The shared categorical palette. |

## Interaction

| Input on a line chart | Result |
|-----------------------|--------|
| left-drag across the plot | zoom the date axis to the dragged range |
| Ctrl + wheel | zoom the date axis in or out around the pointer |
| Ctrl + left-drag | pan the date axis |
| wheel without Ctrl | page scrolls; the chart does not change |
| click `#<id>-reset` | back to full view; hidden series stay hidden |
| click a legend entry | hide or show that series |
| hover | tooltip: the date nearest the pointer, then `name: value` for every visible point on that date (a series with several points on one date lists each), via the custom `date` interaction mode |

## Spending Charts page (donuts)

Containers `#spending-<period>-chart` keep their IDs. Each holds one `<canvas>` while it
has slices, and is hidden, with the "no spending" message shown, when it has none (as
now). `Chart.getChart` on that canvas gives `data.labels` (budget names, largest first)
and `data.datasets[0].data` (amounts) and `.backgroundColor` (each budget's colour, the
same as its checkbox swatch). Hover text is `Name: $X (Y%)`. The `data-loaded` attribute
on `#budget-spending-charts` is kept.
