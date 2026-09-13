# Implementation Plan: Zoomable, Pannable Charts

**Branch**: `robot-army/issue-215-better-charts` | **Date**: 2026-09-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/20260913-120000-zoomable-charts/spec.md`

## Summary

Replace Morris.js with Chart.js 4.5.1 and its zoom plugin (GitHub issue #215). The five
time-series line charts gain drag-select zoom, Ctrl+wheel zoom, Ctrl+drag pan, a reset
button, a hint, and a legend whose entries hide and show series. Each chart's value axis
refits to what is in view. Morris has no zoom or pan to switch on, so the issue's "just
setting options" route is not available ([research R1](research.md)).

The work splits in two milestones:

1. **M1: Line charts.** Vendor Chart.js, the zoom plugin, Hammer.js and the date-fns
   adapter under `static/chartjs/`. Add one shared module, `static/js/charts.js`
   (`lineChartCreate`, `lineChartSetData`), that owns every interaction, so all five charts
   behave the same (FR-001). Move the Index, Budgets and Fuel Log charts onto it, keeping
   the range buttons, the Fuel Log refresh and the "no data" message. Acceptance tests drive
   real drags, wheel turns and clicks and read the resulting chart state.
2. **M2: Donuts and clean-up.** Redraw the Spending Charts page's donuts with Chart.js
   (same slices, colours, hover text and checkbox behaviour; FR-017). Then delete Morris,
   Raphael and `morris.css`, leaving one charting library in the application. Update the
   screenshot script, the docs and the changelog, and pass the Test Gate.

No schema change, no migration, no new setting, no endpoint change.

## Technical Context

**Language/Version**: Python 3.14 (unchanged); browser JavaScript in the existing ES5-style
jQuery idiom.

**Primary Dependencies**: Flask, SQLAlchemy (unchanged). Client: jQuery, Bootstrap 3, and,
new and vendored: Chart.js 4.5.1, chartjs-plugin-zoom 2.2.0, hammerjs 2.0.8,
chartjs-adapter-date-fns 3.0.0 (all MIT). Removed: Morris.js 0.5.0, Raphael.

**Storage**: None touched. The chart data endpoints are read as they are.

**Testing**: pytest + Selenium acceptance tests (`tox -e acceptance`), unit
(`tox -e py314`), `tox -e migrations`, `tox -e docs`, `tox -e jsdoc`.

**Target Platform**: Desktop browser on localhost against a self-hosted Flask app. The
Selenium suite runs headless Chrome.

**Project Type**: Server-rendered web application with AJAX endpoints; single Python package.

**Performance Goals**: Zoom, pan, reset and legend clicks respond within 0.5 s (SC-005). The
largest chart is Account Balances, capped at `ACCOUNT_BALANCE_CHART_MAX_POINTS` dates per
account. Chart.js draws thousands of canvas points in a few milliseconds, and animation is off.

**Constraints**: Works offline, with every asset served by the app (FR-015). Endpoints and
their responses are unchanged (FR-016). Page scrolling must not be taken over (FR-003).

**Scale/Scope**: 5 line charts on 3 pages plus 6 donuts on 1 page. 4 vendored files, 1 new
JS module, 4 chart JS files and 4 templates edited, tests, docs.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v2.1.1. Evaluated before Phase 0 and
again after the Phase 1 design; both passes are recorded below.*

| Principle | Assessment | Verdict |
|-----------|------------|---------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Spec written and validated, then this plan, then tasks, all before any code, on the feature branch `robot-army/issue-215-better-charts`. One feature. Two milestones, M1 (line charts) and M2 (donuts, Morris removal, close-out), so each can be reviewed on its own. | ✅ PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | Each milestone closes with the full unit and acceptance suites run to completion and passing. `migrations` and `docs` are run too. New behaviour is covered by acceptance tests that perform real input (drag, Ctrl+drag, Ctrl+wheel, legend and reset clicks) and assert on the resulting chart state, not on implementation details. There is no timing dependence, because animation is off. Existing tests that assert Morris's SVG are rewritten to assert the same facts on the canvas (one chart, fits its panel, one segment per slice). Any timeout is raised and the suite re-run. pycodestyle/pyflakes clean. | ✅ PASS |
| **III. Schema Changes Ship With Reversible Migrations** | `biweeklybudget/models/` is not changed. `tox -e migrations` is still run to confirm there is no drift. | ✅ PASS (not applicable) |
| **IV. Documentation Is Part Of The Change** | `app_usage.rst` gains a "Charts" section describing the controls. `development.rst` (Frontend / UI) documents the vendored Chart.js files and how to update them. `static/chartjs/README.rst` records versions and sources. `make_screenshots.py` loses its Morris-specific hover call. `tox -e jsdoc` output for `charts.js` and the edited JS files is committed. `tox -e docs` must build. `README.rst`'s pointer to `static/` for third-party licences stays accurate. `CLAUDE.md` names no charting library to update. | ✅ PASS |
| **V. Escalate Instead Of Guessing** | The product questions (which charts, modifier keys, no persistence, touch not required) are settled as recorded spec assumptions. The technical ones are settled with evidence from the packages' own source (R1, R4). The one notable choice, replacing the donuts' library too (R10), is recorded with its reason and pinned by FR-017's no-regression requirement. None is a one-way door: Morris could be restored from git. No `[NEEDS CLARIFICATION]` remained. | ✅ PASS |
| **VI. Changelog Every Change; Release Only On Request** | One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link. `version.py` not touched, no tag, no release. The new `charts.js` carries the AGPL header used by the other JS files. Vendored files keep their own MIT headers and licences. | ✅ PASS |
| **Tech constraints: existing frontend stack** | This replaces the charting library; it does not add a second one. Morris and Raphael are deleted in M2, so at the end there is exactly one charting library, used the same way as before: a browser library fed by the existing JSON endpoints through jQuery AJAX, inside Bootstrap panels. Bokeh was rejected specifically because it would be a parallel, server-side rendering stack (R1). | ✅ PASS |
| **Tech constraints: licence** | All four new packages are MIT (date-fns, bundled in the adapter, is MIT too). MIT is compatible with AGPLv3 distribution. Licence files ship beside the vendored files. | ✅ PASS |
| **Tech constraints: security posture / secrets** | No new endpoints, no network access, no CDN. All chart text (series names in legends and tooltips) is drawn with canvas `fillText`, never parsed as HTML, so a name with `<` cannot inject markup. The localhost-only assumption is unchanged. | ✅ PASS |
| **Tech constraints: financial correctness** | No arithmetic changes. The charts plot the same endpoint values as before, and the endpoint tests (unchanged) still pin them. | ✅ PASS |
| **Tech constraints: test data safety** | Acceptance tests use the existing `refreshdb` fixture and test database only. | ✅ PASS |

**Gate result: PASS, both before Phase 0 and after the Phase 1 design.** There are no
violations, so there is no Complexity Tracking table.

**Workflow note.** Development Workflow steps 3 and 5 require human approval of the plan
and at each milestone boundary. This session was dispatched to run the full lifecycle
through to an opened pull request. That is the dispatcher's decision to make, and it is
recorded here rather than left silently absent. The pull request is the review artifact,
and the maintainer approves at merge. Each milestone is still closed in the constitution's
order (tests, docs, spec progress, one commit), so the two can be reviewed separately in
the PR's history.

## Project Structure

### Documentation (this feature)

```text
specs/20260913-120000-zoomable-charts/
├── spec.md              # Feature specification (/speckit-specify)
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0: R1..R12
├── data-model.md        # Phase 1: chart data in, chart view state (browser only)
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   └── ui.md            # Phase 1: assets, container IDs, JS API, chart state for tests
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
biweeklybudget/
├── flaskapp/
│   ├── static/
│   │   ├── chartjs/                               # NEW (M1) - vendored, unmodified
│   │   │   ├── README.rst                         #   versions, sources, how to update
│   │   │   ├── chart.umd.min.js                   #   + LICENSE-chart.js.md
│   │   │   ├── chartjs-adapter-date-fns.bundle.min.js  # + LICENSE-chartjs-adapter-date-fns.md
│   │   │   ├── hammer.min.js                      #   + LICENSE-hammerjs.md
│   │   │   └── chartjs-plugin-zoom.min.js         #   + LICENSE-chartjs-plugin-zoom.md
│   │   ├── css/custom.css                         # + .chart-controls / .chart-canvas-wrap
│   │   ├── js/
│   │   │   ├── charts.js                          # NEW (M1) - lineChartCreate, lineChartSetData, palette
│   │   │   ├── index.js                           # M1 - Account Balances on charts.js
│   │   │   ├── budget_charts.js                   # M1 - both spending line charts
│   │   │   ├── fuel_charts.js                     # M1 - both fuel charts, updateCharts()
│   │   │   └── budget_spending.js                 # M2 - Chart.js doughnuts; resize hack removed
│   │   └── startbootstrap-sb-admin-2/vendor/
│   │       ├── morrisjs/                          # DELETED (M2)
│   │       └── raphael/                           # DELETED (M2)
│   └── templates/
│       ├── index.html, budgets.html, fuel.html    # M1 - script/css includes
│       └── budget-spending.html                   # M2 - script/css includes, chart CSS
└── tests/acceptance/flaskapp/views/
    ├── test_charts.py                             # NEW (M1) - zoom, pan, wheel, reset, legend,
    │                                              #   tooltip format, resize, one canvas, on all 5
    ├── test_index.py                              # M1 - svg assertions → canvas; range clears zoom
    ├── test_fuel.py                               # M1 - charts redraw after a fill is added
    └── test_budget_spending.py                    # M2 - path/svg assertions → chart data

docs/
├── make_screenshots.py                            # M2 - Chart.js tooltip instead of .morris-hover
└── source/
    ├── app_usage.rst                              # M1 - "Charts" section
    ├── development.rst                            # M1 - vendored Chart.js
    └── jsdoc.*.rst                                # regenerated by tox -e jsdoc, committed
CHANGES.rst                                        # M2 - Unreleased entry
```

**Structure Decision**: Single Python package, existing layout. Chart behaviour lives in
one new JS module beside the existing per-page JS files. The per-page files keep owning
*when* to load data (range buttons, fuel refresh); `charts.js` owns *how* a chart looks and
behaves. The vendored files get their own directory under `static/` because the
startbootstrap theme directory is kept unmodified.
