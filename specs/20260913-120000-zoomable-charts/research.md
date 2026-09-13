# Research: Zoomable, Pannable Charts

Each decision below records what was chosen, why, and what else was considered. The
library versions and behaviours were checked against the packages themselves (downloaded
with `npm pack` and read), not taken from memory.

## R1 — Charting library

**Decision**: Replace Morris.js 0.5.0 (and Raphael, which only Morris uses) with
**Chart.js 4.5.1**, plus three small companions:

| Package | Version | File vendored | Size | Licence | Why |
|---------|---------|---------------|------|---------|-----|
| chart.js | 4.5.1 | `chart.umd.min.js` | 204 KB | MIT | the charts |
| chartjs-plugin-zoom | 2.2.0 | `chartjs-plugin-zoom.min.js` | 15 KB | MIT | drag/wheel zoom, pan, limits, reset |
| hammerjs | 2.0.8 | `hammer.min.js` | 20 KB | MIT | the zoom plugin's pan (and pinch) recogniser; pan does nothing without it |
| chartjs-adapter-date-fns | 3.0.0 | `chartjs-adapter-date-fns.bundle.min.js` | 50 KB | MIT (bundles date-fns, MIT) | date parsing and tick labels for the time axis |

About 290 KB in total, against 128 KB for Morris and Raphael. All MIT, which is compatible
with AGPLv3 distribution.

**Rationale**:

- Everything the spec asks for is built in or nearly so. The zoom plugin provides
  drag-select zoom, wheel zoom and pan, each with an optional modifier key, pan and zoom
  limits (`'original'`), `resetZoom()` and `isZoomedOrPanned()`. Chart.js provides
  legend-click hiding and tooltips.
- **FR-005 needs no code.** Chart.js's `DatasetController.getMinMax` (read in
  `dist/chart.js`, line 822 of 4.5.1) skips any point whose date is outside the date axis's
  set bounds when it works out the value axis's range. The zoom plugin zooms by setting
  those bounds. The value axis therefore fits the data in view. Hidden datasets are also left
  out of that calculation, which covers FR-007's rescale.
- It is a browser library fed by the existing JSON endpoints, so it keeps the existing
  jQuery + AJAX pattern (constitution: Technology constraints) and needs no endpoint changes
  (FR-016).
- It is maintained. Morris.js 0.5.0 dates from 2014 and has no zoom or pan to switch on,
  so "just setting options on them", the issue's first suggestion, is not possible.

**Alternatives considered**:

- **Bokeh** (named in the issue). A Python library: figures are built on the server and
  rendered by BokehJS in the browser. It would add a Python dependency and move chart
  construction into the views. It would also make the chart endpoints return Bokeh
  documents instead of the JSON documented in `http_api.rst` (breaking FR-016), and add
  ~1 MB of BokehJS. That is a parallel frontend stack, which the constitution rules out
  for this project. Its interaction set is no better than Chart.js + zoom for these charts.
- **Plotly.js** (MIT). Zoom, pan, reset and legend toggling are all built in. But the
  basic bundle alone is about 1 MB, wheel zoom cannot require a modifier key (so it takes
  over page scrolling), and the value axis does not refit to a zoomed date range without a
  custom `plotly_relayout` handler.
- **Apache ECharts** (Apache-2.0, AGPL-compatible). Good built-in `dataZoom`. About 1 MB,
  and its option model differs more from what the current code does.
- **Keeping Morris** and adding zoom by hand (re-slicing the data on drag). This means
  writing and maintaining our own zoom, pan and reset on a library that no longer changes.

## R2 — Where the vendored files live

**Decision**: `biweeklybudget/flaskapp/static/chartjs/`, holding the four minified files
above, each package's `LICENSE.md` renamed to say which package it belongs to, and a
`README.rst` listing each package, version and source URL, and how to update them.

**Rationale**: `static/startbootstrap-sb-admin-2/vendor/` is the unmodified theme
(`development.rst`: "It is currently not modified at all"), so new files do not belong
there. `static/` already holds other third-party directories beside it (`jquery-ui-1.12.1.custom`,
`bootstrap-datepicker`), and `MANIFEST.in` already includes everything under `static/`,
so packaging and the Docker image pick the files up unchanged. Keeping licences next
to the files matches README.rst's pointer to `biweeklybudget/flaskapp/static` for
third-party licences. Nothing is fetched from a CDN (FR-015).

## R3 — One shared line-chart module

**Decision**: A new `static/js/charts.js`, loaded after the four vendored files on the
three line-chart pages, with:

- `lineChartCreate(elementId, ajaxdata, opts)`: builds the controls and canvas inside the
  existing chart `<div>`, converts the endpoint response to datasets, and returns the
  Chart.js instance. `opts.currency` selects currency formatting. `opts.dateFormat` is the
  tooltip date format: `yyyy-MM-dd`, or `yyyy-MM` for the monthly chart.
- `lineChartSetData(chart, ajaxdata)`: replaces the datasets in place, resets the zoom and
  refreshes the reset control. Used by the Index range buttons and the Fuel Log refresh.
- The shared colour palette, `CHART_COLORS`.

`index.js`, `budget_charts.js` and `fuel_charts.js` call these instead of `Morris.Line`.

**Rationale**: FR-001 requires all five charts to behave the same. One module is how that
stays true. It is also where each behaviour is written and documented (jsdoc) once, rather
than five times.

## R4 — Interaction mapping

**Decision**:

| Action | Input | Plugin setting |
|--------|-------|----------------|
| Zoom to a range | plain left-drag | `zoom.drag.enabled: true`, `zoom.mode: 'x'` |
| Zoom in/out | Ctrl + wheel/touchpad scroll | `zoom.wheel.enabled: true, modifierKey: 'ctrl'` |
| Pan | Ctrl + left-drag | `pan.enabled: true, modifierKey: 'ctrl', mode: 'x'` |
| Pinch zoom (touch) | pinch | `zoom.pinch.enabled: true` (enabled because it is free; not tested) |
| Limits | never past the data, never narrower than the widest gap | `limits.x: {min: 'original', max: 'original', minRange: <widest gap>}` |

**Rationale**, from the plugin source (`dist/chartjs-plugin-zoom.js` 2.2.0):

- `wheelPreconditions` returns before `preventDefault()` when the wheel modifier is not held.
  Without Ctrl, the page scrolls normally (FR-003). With Ctrl, the plugin's non-passive
  listener prevents the browser's own Ctrl+wheel page zoom.
- `mouseDown` rejects drag-zoom whenever the pan modifier is held. So plain drag is zoom
  and Ctrl+drag is pan, with no conflict, and both actions share one key to remember.
- `mouseDown` ignores presses inside the legend, so legend clicks never start a drag-zoom.
- Mode `'x'` zooms and pans dates only (spec Assumptions). The value axis follows by R1.
- Shift was rejected as the modifier: several browsers turn Shift+wheel into a horizontal
  scroll with `deltaY` of 0, which the plugin reads as "zoom in" every time.

`minRange` is the widest gap between consecutive dates, in milliseconds, across all
series. Any window at least that wide contains a point (spec Edge Cases, data-model
Limits). For a single date there is no gap and no zooming.

## R5 — Reset control and hint

**Decision**: `lineChartCreate` puts a controls row above each canvas with a hint in muted
text, "Drag to zoom · Ctrl+drag to pan · Ctrl+scroll to zoom in/out", and a Bootstrap
`btn-xs` "Reset zoom" button with the ID `<elementId>-reset`. The button is `disabled`
unless `chart.isZoomedOrPanned()` is true. It is re-evaluated from the plugin's
`onZoomComplete` and `onPanComplete` callbacks, and after a reset or new data.

**Rationale**: FR-006 and FR-008. A visible button is easier to find than a double-click
gesture. It is disabled rather than hidden so the row's layout does not jump.

## R6 — Converting the endpoint response

**Decision**: One dataset per `keys` entry. Its points are `{x: row.date, y: row[key]}` for
each row where `row[key]` is present and not `null`. `spanGaps: true` joins across
dates missing in between, as Morris's `continuousLine` did. The x axis is `type: 'time'`.
Date strings are parsed by the date-fns adapter's `parseISO`, which reads `2017-07-15` and
`2017-07` as local dates, so no point shifts a day in a time zone west of UTC. Built-in
parsing through `Date` would read a bare date as UTC midnight.

The time axis sets `minUnit` to `'day'`, or `'month'` for the monthly chart. No data is
finer than a day. Without `minUnit`, Chart.js labels hours whenever the visible range is
a day or two wide, which happens with a single day of data or when zoomed to `minRange`,
and that suggests the data has times. This was found in the T030 walk-through.

**Rationale**: data-model "Line series". A missing value is a gap, never a zero.

## R7 — Tooltips and currency

**Decision**: `interaction: {mode: 'nearest', axis: 'x', intersect: false}`, so hovering
anywhere on the plot shows every visible series with a point on the date nearest the
pointer. Every point on that date is at the same horizontal distance, so each appears;
series without a point on that date are further away and are left out. `'index'` mode is
wrong here because series with gaps have different indices for the same date. `'x'` mode
only matches points within their small hit radius, so the tooltip would flicker off
between dates.

*Revised during implementation:* `'nearest'` alone is not enough. It binary-searches each
dataset for the pointer position and examines only the points either side of it. When a
series has several points on the same date, as the sample data's fuel prices do (three
fills on each of two days), it returns one or two of them depending on the exact pointer
pixel. A flaky acceptance test found this. The charts therefore register a custom Chart.js
interaction mode, `date` (`chartDateInteraction()` in `charts.js`). It uses `'nearest'`
with `axis: 'x'` to find the date, then returns every visible point at exactly that x
pixel. Points on one date always compute the same pixel, so hovering always lists every
point on that date. The tooltip title is the date in
`opts.dateFormat`. Label values go through the existing `fmt_currency()` when
`opts.currency` is set (Account Balances, both Spending By Budget charts, Fuel Prices), and
through `toFixed(2)` for Fuel Economy, matching Morris's two decimals. The value axis
ticks use the same formatter.

## R8 — Legend, colours and names

**Decision**: Chart.js's built-in legend at the bottom, whose default click handler
toggles the dataset (FR-007). It wraps onto more lines as needed. Colours come from a
shared categorical palette. After the palette runs out, further colours are generated
around the hue circle, so a dozen or more series each keep a distinct colour for their
line, legend swatch and tooltip swatch.

**Rationale**: Legend, tooltip and axis text are all drawn onto the canvas with
`fillText`. No series name is ever parsed as HTML, so a name containing `<` or `&` shows
as literal text and cannot inject markup (spec Edge Cases; constitution security posture).

## R9 — Sizing and resize

**Decision**: Each canvas sits in a wrapper `<div>` with a fixed height (300 px for the
line charts) and `position: relative`. The chart uses `responsive: true,
maintainAspectRatio: false`, so Chart.js's own `ResizeObserver` redraws it to the panel's
width whenever the panel changes size (FR-013). `animation: false` makes redraws immediate.
Tests can then read the chart's state as soon as an action returns, with no timing waits.

**Rationale**: This replaces the Morris workarounds: the `resize: true` option on the
line charts, and on the Spending Charts page the "draw tables before charts" ordering and
the window-resize redraw handler (see `budget_spending.js`). Both existed only because
Morris measures its container once.

## R10 — The donut charts

**Decision**: Move the Spending Charts page's six donuts to Chart.js `doughnut` charts too,
keeping their colours, slices, hover text (`Name: $X (Y%)`), "no spending" message and
checkbox behaviour (FR-017). Then delete Morris, Raphael and `morris.css` from the tree.

**Rationale**: With the line charts on Chart.js, keeping Morris only for the donuts would
mean two charting libraries, two sets of styles and two ways of handling resizing: the
parallel stack the constitution warns against. The donut code is one short function
(`budgetSpendingDrawChart`), and Chart.js removes the workaround described in R9.
Leaving Morris in place for the donuts was rejected for that reason. The spec's FR-017
pins the donuts' behaviour, so this is a change of drawing library only.

## R11 — Testing strategy

**Decision**: Selenium acceptance tests drive the real charts with real input:
ActionChains drag, Ctrl + drag, Ctrl + wheel via Selenium 4 wheel actions, and clicks on the
reset button and on legend entries. They then read the chart's state through Chart.js's
public `Chart.getChart(canvas)`: `scales.x.min/max`, `scales.y.min/max`,
`isZoomedOrPanned()`, `isDatasetVisible(i)` and dataset data. Legend entries are clicked
at the hit boxes Chart.js reports in `chart.legend.legendItems`/`legendHitBoxes`. Existing tests that
count `svg` or `path` elements are changed to assert on the canvas and the chart's data
instead. Nothing in the tests depends on timing, because animation is off (R9).

The data-endpoint tests are unchanged and must still pass, which is the check on FR-016.

## R12 — Documentation touch points

- `docs/source/app_usage.rst`: a "Charts" section describing the controls. The Account
  Balances and Spending Charts sections link to it.
- `docs/source/development.rst` (Frontend / UI): the vendored Chart.js files and how to
  update them.
- `README.rst`: already points at `biweeklybudget/flaskapp/static` for third-party licences;
  that stays true.
- `docs/make_screenshots.py`: its Budgets pre-shot shows a Morris hover box
  (`.morris-hover`). It will show a Chart.js tooltip through
  `chart.tooltip.setActiveElements` instead.
- `tox -e jsdoc` regenerates `jsdoc.*.rst` for the changed JS files and the new `charts.js`,
  and the output is committed.
- `CHANGES.rst`: one bullet under `Unreleased`.
