---

description: "Task list for Zoomable, Pannable Charts"
---

# Tasks: Zoomable, Pannable Charts

**Input**: Design documents from `specs/20260913-120000-zoomable-charts/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/ui.md](./contracts/ui.md),
[quickstart.md](./quickstart.md)

**Tests**: Test tasks ARE included. The constitution's Test Gate (Principle II,
NON-NEGOTIABLE) makes tests mandatory for new code.

**Organization**: Grouped by user story, in two milestones. **M1** covers the line charts
(Phases 1–6). **M2** covers the donuts, Morris removal and close-out (Phases 7–8).

**Commit prefix**: `Zoomable Charts - M{milestone}.{n}` per constitution Development
Workflow step 4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1 zoom, US2 pan, US3 legend, US4
  unchanged behaviour)

## Path Conventions

Single Python package at the repository root: `biweeklybudget/`, with tests under
`biweeklybudget/tests/` and documentation under `docs/source/`. Paths are
repository-relative. `static/` means `biweeklybudget/flaskapp/static/`.

---

## Phase 1: Setup (M1)

**Purpose**: Bring up the environment that later phases verify against. No production code.

- [X] T001 Start the MariaDB test container and export the test environment variables per `CLAUDE.md` ("Test Database Setup for Development"). Then run `python dev/setup_test_db.py` and `initdb`, using the main checkout's venv (worktrees have no venv). No migration is created by this feature.
- [X] T002 *(Result, 2026-09-13, unchanged code, MariaDB 10.4.7: 79 passed, 1610 deselected.)* Run the existing chart-related acceptance tests on the unchanged code (`tox -e acceptance -- -k "Chart or chart or BudgetSpending or Fuel"`, output to a scratchpad file) to have a green baseline to compare against.

---

## Phase 2: Foundational (M1, blocking)

**Purpose**: The vendored library and the shared module that every story builds on.

- [X] T003 Create `static/chartjs/` and copy in, unmodified, from the npm packages of research R1: `chart.umd.min.js` (chart.js 4.5.1 `dist/`), `chartjs-plugin-zoom.min.js` (2.2.0 `dist/`), `hammer.min.js` (hammerjs 2.0.8), `chartjs-adapter-date-fns.bundle.min.js` (3.0.0 `dist/`). Copy each package's `LICENSE.md` as `LICENSE-<package>.md`. Write `static/chartjs/README.rst` listing each package, version, npm URL, licence, and how to update them (`npm pack <pkg>@<ver>` and copy the same files).
- [X] T004 Create `static/js/charts.js` with the JS AGPL header (copy from `static/js/budget_charts.js`) and JSDoc on every function and global. Implement per `contracts/ui.md` and research R3, R6–R9: `CHART_COLORS` (a categorical palette, extended around the hue circle beyond its length); `lineChartDatasets(ajaxdata)` (one dataset per key; points only where the row has a non-null value; `spanGaps: true`; colour per index); and `lineChartCreate(elementId, ajaxdata, opts)`, which empties `#elementId` and builds the `.chart-controls` row (hint span and `#<id>-reset` button) and a `.chart-canvas-wrap` holding `<canvas id="<id>-canvas">`, then creates a `line` chart. The chart has a `time` x axis, `responsive: true`, `maintainAspectRatio: false`, `animation: false`, `interaction: {mode: 'nearest', axis: 'x', intersect: false}` (research R7; `'x'` mode was found to match only within a point's hit radius), a bottom legend, tooltips titled in `opts.dateFormat`, and value labels and y ticks through `fmt_currency` when `opts.currency` (else `toFixed(2)`). Also implement `lineChartSetData(chart, ajaxdata)`, which replaces the datasets, recalculates limits, resets the view and refreshes the reset button. Leave zoom and pan for Phases 4–5, but structure the options so they slot in.
- [X] T005 [P] Add `.chart-controls` (small bottom margin, hint and button on one line, wrapping on narrow panels) and `.chart-canvas-wrap` (`position: relative; height: 300px;`) to `static/css/custom.css`.

**Checkpoint**: `charts.js` loads without errors when included after the four vendored files.

---

## Phase 3: User Story 4 - The charts keep doing what they do now (Priority: P1, M1) 🎯 MVP

**Goal**: All five line charts drawn by Chart.js through `charts.js`, with every existing behaviour intact.

**Independent Test**: Each chart renders one canvas with the endpoint's series. The range buttons, the Fuel Log refresh, the "no data" message, currency tooltips and resize all still work.

- [X] T006 [US4] In `biweeklybudget/flaskapp/templates/index.html`, `budgets.html` and `fuel.html`, remove the Morris CSS link and the Raphael and Morris script tags. Add the four `/static/chartjs/` scripts in the order of `contracts/ui.md`, then `/static/js/charts.js`, before each page's own chart script. Leave `budget-spending.html` for M2.
- [X] T007 [P] [US4] In `static/js/index.js`, replace `Morris.Line` with `lineChartCreate('account-balance-chart', ajaxdata, {currency: true, dateFormat: 'yyyy-MM-dd'})`, and `setData` with `lineChartSetData`. Keep the request sequence guard (`acctBalanceChartSeq`) and the no-data handling. Update the JSDoc that mentions Morris.
- [X] T008 [P] [US4] In `static/js/budget_charts.js`, draw `budget-per-period-chart` (`dateFormat: 'yyyy-MM-dd'`) and `budget-per-month-chart` (`dateFormat: 'yyyy-MM'`) with `lineChartCreate`, `currency: true`.
- [X] T009 [P] [US4] In `static/js/fuel_charts.js`, draw `mpg-chart` (`currency: false`) and `fuel-price-chart` (`currency: true`) with `lineChartCreate`. Make `updateCharts()` call `lineChartSetData` on both.
- [X] T010 [US4] *(As built: the data check clicks `1m` rather than `All`, because on the sample data `All` returns the same five dates as the default `1y`, so it would not show a change.)* In `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`, change `TestAcctBalanceChartRanges`'s `svg` assertions to assert that `#account-balance-chart` contains exactly one `canvas` and that `Chart.getChart('account-balance-chart-canvas')` exists. Add a test that the chart's dataset labels equal the endpoint's `keys` and that its points match the endpoint's data, for the default range and after clicking `All`.
- [X] T011 [US4] *(As built: the resize check asserts that the chart's own container stays inside the window rather than that the whole page has no horizontal scroll. At 1100px the Fuel Log page scrolls sideways because its `#table-fuel-log` DataTable is wider than the window: checked in headless Chrome, where that table and its cells were the only elements past the right edge. This feature does not touch that table, so its width is out of scope here. Tooltips are checked on the four charts whose sample data has points; the MPG chart has none until a fill is added, which T012 does.)* Create `biweeklybudget/tests/acceptance/flaskapp/views/test_charts.py` (AGPL header, `acceptance`, `refreshdb`). Add a shared helper that loads a page, waits for jQuery to finish, and returns chart state via `execute_script` against `Chart.getChart('<id>-canvas')`. Parametrize over the five charts of `contracts/ui.md` (page, container ID, endpoint URL). Test: one canvas per container; dataset labels equal the endpoint's `keys` in order; each dataset's points are exactly the rows with that key (gaps not zero-filled); the hint text and a disabled `#<id>-reset` are present; the canvas fits its panel and the page has no horizontal scroll, before and after a `set_window_size` change (FR-013); hovering the plot shows a tooltip whose label text uses currency formatting for currency charts (read `chart.tooltip` after an ActionChains move); no JS errors in the browser log.
- [X] T012 [US4] *(As built: in `test_charts.py`, `TestFuelChartRefresh`. It asserts that each fuel chart's data equals the endpoint's after the fill and differs from before, rather than a hard-coded MPG, because the fuel-economy endpoint carries values forward and drops its first date.)* Add to `biweeklybudget/tests/acceptance/flaskapp/views/test_fuel.py` (or `test_charts.py` if test_fuel's fixtures make it simpler): after adding a fuel fill through the modal, both fuel charts' data include the new fill's date without a page reload, and each container still holds one canvas (FR-012).
- [X] T013 [US4] *(Result, 2026-09-13: first run 70 passed, 5 failed, all five test faults (see the as-built notes on T010-T012 and T020); after fixing the tests, `-k Chart` over `test_charts.py` and `test_index.py`: 75 passed. No chart code changed between the runs.)* Run the tests from T010–T012 and the T002 set. Fix anything failing.

**Checkpoint**: MVP of the library move. Everything behaves as before, on Chart.js.

---

## Phase 4: User Story 1 - Zoom into a stretch of time (Priority: P1, M1)

**Goal**: Drag-select zoom, Ctrl+wheel zoom (with plain wheel left to the page), a value axis that follows the view, and a reset button.

**Independent Test**: Drag-select a range on a multi-year chart, check the x range and the refitted y range, then reset.

- [X] T014 [US1] In `static/js/charts.js`, enable the zoom plugin per research R4: `zoom: {mode: 'x', drag: {enabled: true}, wheel: {enabled: true, modifierKey: 'ctrl'}, pinch: {enabled: true}}`, and `limits: {x: {min: 'original', max: 'original', minRange: <widest gap between consecutive dates across all series, ms>}}`. Put the widest-gap computation in its own documented function. Wire `onZoomComplete` (and later `onPanComplete`) to a function that sets `#<id>-reset`'s `disabled` from `chart.isZoomedOrPanned()`. The reset button calls `chart.resetZoom()` and then refreshes itself. `lineChartSetData` recalculates `minRange` and resets the view.
- [X] T015 [US1] Add to `test_charts.py`, parametrized over the five charts, using a sample data set wide enough to zoom (for Account Balances, click `All` first; add rows in the test if a chart's sample data has too few dates to zoom): an ActionChains drag across the middle half of the plot area leaves `scales.x.min/max` inside the dragged range and `isZoomedOrPanned()` true; `scales.y.min/max` bound only the values of points inside the new x range (compute the expected bounds from the dataset data in the test, allowing for Chart.js's nice-number padding, which never goes beyond the next tick); a second drag narrows it further; the reset button becomes enabled, and clicking it restores the original `scales.x.min/max` and disables it again (FR-006); `lineChartSetData` (a range button on `/`) returns to full view.
- [X] T016 [US1] Add wheel tests to `test_charts.py` on at least the Account Balances and Budgets per-period charts. Scroll over the chart with Selenium 4 wheel actions (`ActionChains.scroll_from_origin` with a `ScrollOrigin.from_element`) without a modifier: the page's `window.scrollY` changes and the chart's x range does not. Hold Ctrl (`key_down(Keys.CONTROL)`) and scroll up: the x range narrows. Scroll down: it widens but never past the original bounds. Zooming in repeatedly stops at `minRange`, with at least one point still in view (spec Edge Cases).

---

## Phase 5: User Story 2 - Move along a zoomed chart (Priority: P1, M1)

**Goal**: Ctrl+drag pans the date axis, stopping at the ends of the data.

**Independent Test**: Zoom, Ctrl+drag, and check that the window moved and kept its width.

- [X] T017 [US2] In `static/js/charts.js`, enable `pan: {enabled: true, mode: 'x', modifierKey: 'ctrl', onPanComplete: <reset-button refresh>}`. Confirm by test that plain drag still zooms and Ctrl+drag pans rather than zooms (the plugin's `mouseDown` rejects drag-zoom while the pan key is held; research R4).
- [X] T018 [US2] Add to `test_charts.py`, parametrized over the five charts: zoom by drag, then Ctrl+drag (ActionChains `key_down(Keys.CONTROL)`, `click_and_hold`, `move_by_offset`, `release`, `key_up`) towards later dates. Both `scales.x.min` and `max` move earlier by the same amount and the width is unchanged (within one pixel's worth of time). Panning far past the start stops with `scales.x.min` equal to the original minimum (FR-004), and the reset button is enabled.

---

## Phase 6: User Story 3 - Hide and show series (Priority: P2, M1)

**Goal**: A legend whose entries hide and show series, with the value axis refitting.

**Independent Test**: Click the largest series in the legend, check that it is hidden and the y range shrinks to the rest, then click it again.

- [X] T019 [US3] Confirm in `static/js/charts.js` that the legend is displayed, uses each dataset's colour, wraps, and uses Chart.js's default toggle handler. Clicks inside the legend must not start a drag-zoom. Nothing else should be needed (research R8). Make sure the reset handler does not re-show hidden datasets.
- [X] T020 [US3] *(As built: the hidden series is the one with the highest value, found from the data, and the test asserts the axis top drops and still fits the remaining series; an earlier version assumed InvestmentOne was the highest, which the sample data does not bear out.)* Add to `test_charts.py`, on the Account Balances and Budgets per-period charts (those with several series): clicking the legend hit box (from `chart.legend.legendHitBoxes`, converted to an offset from the canvas centre) of the series with the largest absolute value makes `isDatasetVisible(i)` false, and `scales.y.max`/`min` then bound only the remaining visible series. Clicking again restores it. Hide a series, zoom, then reset: the series stays hidden. Reload: every dataset is visible and the view is full (FR-010). Add one test with a budget named `<b>&amp;` (inserted in the test): its legend label and dataset label are the literal string, and the page contains no `<b>` element created from it.
- [X] T021 [US3] *(Results, 2026-09-13: `py314` 956 passed, 4 skipped, run with `.tox/py314/.pytest_cache` cleared so every pycodestyle/pyflakes check ran. The first full `acceptance` run was stopped after about 8 tests by the session harness because the machine was low on memory: swap was full from other processes, and nothing left behind was this session's. It did not fail. Re-run to completion: `acceptance` 869 passed, 24 skipped, 0 failed (20m10s). The skips are the known ones: 6 deprecated OFX tests in `test_ofx.py` and 18 unconditional skips in `test_reconcile.py`. Docs build: succeeded; none of its 129 warnings are in `app_usage.rst` or `development.rst`.)* Close milestone M1 per constitution Development Workflow step 5. Run the chart acceptance tests and `tox -e py314` to completion, and fix anything found. Add a "Charts" section to `docs/source/app_usage.rst` (the controls, the reset button, the legend, nothing saved, the Ctrl key) and link to it from the Account Balances Chart section. Document the vendored Chart.js files and how to update them in `docs/source/development.rst` (Frontend / UI). Mark T001–T021 done here and commit as `Zoomable Charts - M1.n`.

**Checkpoint**: M1 complete. All five line charts have the full set of interactions.

---

## Phase 7: Donuts on Chart.js, Morris removed (M2)

**Goal**: FR-017. The Spending Charts page is drawn with Chart.js and behaves as before, and Morris and Raphael leave the tree.

**Independent Test**: The existing `test_budget_spending.py` page tests pass with their SVG checks moved to canvas and chart data.

- [X] T022 In `biweeklybudget/flaskapp/templates/budget-spending.html`, replace the Morris CSS, Raphael and Morris includes with `/static/chartjs/chart.umd.min.js`. The donuts need no zoom plugin, adapter or Hammer. Keep `.spending-chart`'s height, give it `position: relative`, and drop `overflow: hidden` if it is no longer needed.
- [X] T023 *(As built: each redraw destroys the period's previous chart and empties its container before drawing, so a period with no slices is left with no canvas. With Chart.js following its container's width, the "tables before charts" ordering and the window-resize redraw were both removed; `test_charts_fit_their_panels` still guards the width.)* In `static/js/budget_spending.js`, replace `Morris.Donut` in `budgetSpendingDrawChart` with a Chart.js `doughnut`. Use `data.labels` = slice names, one dataset with `data` = amounts and `backgroundColor` = `budgetSpendingColors[budget_id]`, no legend (the table is the legend), and a tooltip label `Name: $X (Y%)` via `fmt_currency`. Keep one Chart instance per period: destroy the previous instance before redrawing on a checkbox change. With `responsive: true`, remove the window-resize redraw handler and the "tables before charts" ordering comment. Keep the ordering only if a test shows it is still needed. Update the JSDoc.
- [X] T024 *(Result, 2026-09-13: `test_budget_spending.py` 20 passed. `test_charts_and_nodata` now checks each donut's labels, amounts and colours against its table and the page's per-budget colours; new `test_toggle_redraws_one_chart_each` checks that a checkbox change leaves at most one canvas per chart and updates its slices.)* In `biweeklybudget/tests/acceptance/flaskapp/views/test_budget_spending.py`, change `test_charts_and_nodata` to read `Chart.getChart('spending-<key>-canvas')` (or the canvas inside the container) and assert that its labels, amounts and colours match the table rows and swatches, and that there is one canvas per shown chart. Change `test_charts_fit_their_panels` to measure the canvas instead of the SVG. Add a check that toggling a checkbox leaves exactly one canvas per chart and updates the chart's labels.
- [X] T025 *(Result: after deleting both directories and regenerating jsdoc, `git grep -i "morris|raphael"` outside `specs/` finds only the new CHANGES.rst entry and the `test_charts_fit_their_panels` docstring that explains the old Morris bug. Both are intended.)* Delete `static/startbootstrap-sb-admin-2/vendor/morrisjs/` and `static/startbootstrap-sb-admin-2/vendor/raphael/`. Then grep the repository, excluding `specs/`, for `morris`, `Morris` and `raphael`, and remove or update every remaining reference.
- [X] T026 [P] In `docs/make_screenshots.py`, replace the `.morris-hover` script in the Budgets pre-shot with a script that shows a tooltip on the per-period chart via `Chart.getChart('budget-per-period-chart-canvas')`, `tooltip.setActiveElements(...)` and `update()`.

---

## Phase 8: Polish, Docs & Test Gate (M2)

- [X] T027 [P] Add a concise entry under `Unreleased` at the top of `CHANGES.rst`, led by the issue #215 link, with sub-bullets for the new controls and the Morris → Chart.js replacement. Do not touch `biweeklybudget/version.py`.
- [X] T028 *(Result: `git grep -i morris|raphael` outside `specs/` found nothing to change in README.rst, CLAUDE.md or docs/source prose; only the new CHANGES.rst entry, a test docstring explaining the old bug, and generated `jsdoc.*.rst` pages regenerated by T029.)* [P] Check `README.rst`, `CLAUDE.md` and `docs/source/` for anything else that names Morris or describes chart behaviour, and update it. Mention the chart controls in the Spending Charts section of `app_usage.rst` only if something there changed.
- [X] T029 *(Results, 2026-09-13, on the final code, MariaDB 10.4.7: `py314` 956 passed, 4 skipped, `.tox/py314/.pytest_cache` cleared so no style check was skipped; full `acceptance` 876 passed, 24 skipped (the known 6 deprecated OFX and 18 unconditional reconcile skips), 0 failed; `migrations` 8 passed; `docs` build succeeded; `jsdoc` OK with jsdoc 4.0.4, with the stale unrelated `jsdoc.budgets_modal`, `jsdoc.custom` and `jsdoc.fuel` output reverted. The docs build has 140 warnings. The ones in this feature's jsdoc pages are the same two kinds master's pages already have, from `make_jsdoc.py` rendering every function name as dots: `:js:func:` references that cannot resolve (the project's convention; 15 JS files use it) and "duplicate function description" where two names share a length and last letter. They are left alone as pre-existing and out of scope, and noted in the PR. Docker: `tox -e docker` reruns the whole acceptance suite against a built image. It was not run locally, after a local acceptance run had been killed for low memory. The PR's CI `docker` job is the Docker suite run for this change, which alters packaged static files, and it must pass before merge.)* Run the Test Gate to completion with output to scratchpad files: `tox -e py314`, `tox -e acceptance`, `tox -e migrations`, `tox -e docs`, `tox -e jsdoc` (jsdoc 4.0.4; commit the regenerated `docs/source/jsdoc.*.rst`, including the new `jsdoc.charts.rst`, and add it to whatever toctree lists the others). Raise timeouts rather than narrowing any run. Re-run known-flaky tests in isolation before attributing a failure. Record the results in this file.
- [X] T030 *(Walk-through, 2026-09-13: `flask run` from the worktree against a separate MariaDB container loaded with the sample data, driven in headless Chrome with screenshots of each page. Zoom, pan, reset, the legend strike-through, the hint and currency tooltips all behaved as specified, with no browser errors apart from the app's missing favicon. Two things were found and fixed. (1) The date axis labelled times of day ("12AM, 3AM…") when the data spans a single day (the sample fuel prices) or has none (the sample MPG chart), and the monthly chart labelled days. Fixed with Chart.js `time.minUnit`: `'day'` by default, `'month'` for the monthly chart. Covered by new `test_date_axis_labels_dates_only`. (2) No test checked the donut hover text FR-017 requires. Added `test_donut_hover_text`, and confirmed `Periodic2: $222.22 (66.7%)` in the browser. (3) Re-running the tests afterwards, `test_tooltip` on the Fuel Prices chart failed, after passing once before. Chart.js's `nearest` mode returns only some of a series' points on one date (the sample data has three fuel fills on each of two days), varying with the exact pointer pixel. Fixed with a custom `date` interaction mode (`chartDateInteraction()`, research R7) that returns every visible point on the nearest date. `test_tooltip` now expects one line per point on the hovered date, and new `test_tooltip_lists_every_point_on_a_date` hovers each fuel-price date at its pixel and one and two pixels away, expecting all three prices every time. After the fixes: `test_charts.py` + `test_budget_spending.py` 69 passed.)* Manually walk `quickstart.md`'s scenarios against `flask rundev` with the test data, in a browser, and fix anything found.
- [ ] T031 Mark tasks complete, set the spec's Status to Complete, and commit everything as `Zoomable Charts - M2.n`. Push the branch to `origin` and open the pull request following `.github/PULL_REQUEST_TEMPLATE.md`. Surface for the maintainer the library choice (and why not Bokeh), the Ctrl modifier, the donuts moving too, and the ~290 KB of vendored JS. Then monitor CI and answer reviews until Claude's review says "No issues found" and Copilot's, if present, recommends approval.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US4 (Phase 3) → US1 (Phase 4) → US2 (Phase 5) → US3 (Phase 6) → M2
  (Phases 7–8).
- US4 must come first: nothing can be zoomed until the charts are on Chart.js. US1, US2 and
  US3 all edit `charts.js` and `test_charts.py`, so they run in sequence, though each is
  independently testable once done.
- T007, T008 and T009 are different files and can be done in parallel after T004–T006.
- Phase 7 depends only on T003 (the vendored Chart.js), not on the line-chart work, but it
  is scheduled after M1 so that Morris is deleted only once nothing uses it.
- T026–T028 are independent files.

## Parallel Example

```text
After T006:  T007 (index.js) || T008 (budget_charts.js) || T009 (fuel_charts.js)
Phase 2:     T004 (charts.js) || T005 (custom.css)
Phase 7/8:   T026 (make_screenshots.py) || T027 (CHANGES.rst) || T028 (docs sweep)
```

## Implementation Strategy

The MVP is US4 plus US1: the charts are on Chart.js with nothing lost, and they zoom. US2 (pan)
and US3 (legend) complete what the issue asks for ("zooming, panning, etc."). M2 removes the
second charting library and closes the feature. Both milestones ship in one pull request,
committed separately so they can be reviewed in order.
