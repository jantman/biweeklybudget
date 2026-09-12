# Implementation Plan: Spending By Budget Pie Charts

**Branch**: `robot-army/issue-214-spending-by-budget-charts` | **Date**: 2026-09-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/20260912-170923-budget-spending-pie-charts/spec.md`

## Summary

Add a read-only **Spending By Budget** page at `/budgets/spending`. It shows six donut
charts of net spending per budget: current and previous pay period, calendar month and
calendar year. Each chart has a table under it. Above them is a set of checkboxes, one per
budget, that removes a budget from every chart at once (GitHub issue #214).

The work splits in three:

1. **A small computation module**, `biweeklybudget/budget_spending.py`. One pure function
   works out the six reporting periods from today's date and the pay period calculation.
   One aggregate SQL query per period sums `BudgetTransaction.amount` by budget over the
   period's dates. The query excludes income budgets, transfers, and transactions that are
   excluded from budget arithmetic (`Transaction.is_excluded_from_budget`, the same
   predicate the pay period page uses).
2. **One JSON endpoint**, `GET /ajax/chart-data/budget-spending/by-period`. It is a third
   aggregation on the existing `BudgetSpendingChartView`, beside `by-pay-period` and
   `by-month`. It returns the periods, their per-budget net spending, and the budgets'
   names and `omit_from_graphs` flags. Everything is computed on the server. The browser
   only filters and adds up what it is given.
3. **The page**: a template, and one JavaScript file that draws the charts with the
   already-bundled `Morris.Donut`. The same JavaScript builds the tables and the
   checkboxes, and redraws everything in place when a checkbox changes. The page is linked
   from the navigation menu and from the existing charts on the Budgets page.

No schema change, no migration, no new setting, no new dependency.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, MariaDB/MySQL (server). jQuery, Bootstrap 3,
Morris.js 0.5.0 with Raphael (client, all already vendored). Nothing new.

**Storage**: MariaDB/MySQL. Reads the existing `transactions`, `budget_transactions` and
`budgets` tables. Writes nothing.

**Testing**: pytest. Unit tests (`tox -e py314`), Selenium acceptance tests
(`tox -e acceptance`), Alembic model-match (`tox -e migrations`, run to confirm no model
drift), Sphinx (`tox -e docs`), jsdoc (`tox -e jsdoc`).

**Target Platform**: Self-hosted Flask app on localhost, single trusted operator.

**Project Type**: Server-rendered web application with AJAX endpoints; single Python package.

**Performance Goals**: One page load issues six aggregate `GROUP BY` queries (one per
period), plus one pay period lookup and one budget lookup. The query cost does not depend
on how many transactions exist outside the year being charted. Toggling a checkbox is
client-side only and redraws six charts well under the one second SC-004 allows.

**Constraints**: The existing `by-pay-period` and `by-month` responses and the Budgets
page line charts must not change (FR-014). Amounts are summed as `Decimal` on the server,
so no floating point touches a total before it reaches the browser.

**Scale/Scope**: Tens of budgets, up to a few thousand transactions a year. One new Python
module, one view method plus one page view, one template, one JS file, two template
edits (nav, budgets), tests and docs.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v2.1.1. The gate was evaluated before
Phase 0 and again after the Phase 1 design; both passes are recorded below.*

| Principle | Assessment | Verdict |
|-----------|------------|---------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | The spec was written and validated, then this plan, then tasks, all before any code, on the feature branch `robot-army/issue-214-spending-by-budget-charts`. One feature only. The change is small enough to be a **single milestone (M1)**, so there is no boundary between milestones to cross. | ✅ PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | The full unit and acceptance suites are run to completion before the feature is declared done, and `migrations` and `docs` are run too. New logic is covered by valid tests: unit tests pin the period boundaries, including the January edge cases. Acceptance tests pin per-budget amounts against the sample data plus transactions inserted by the tests, one for every exclusion rule in FR-004. Another test checks the current pay period figures against `BiweeklyPayPeriod.budget_sums` (SC-002). Selenium tests cover the checkboxes. Code stays pycodestyle and pyflakes clean. Any timeout is raised and the suite re-run. | ✅ PASS |
| **III. Schema Changes Ship With Reversible Migrations** | `biweeklybudget/models/` is not changed and no migration is needed. `tox -e migrations` still runs, to confirm that stays true. | ✅ PASS (not applicable) |
| **IV. Documentation Is Part Of The Change** | `docs/source/app_usage.rst` gains a section explaining what is counted. `docs/source/http_api.rst` documents the new aggregation under Charts. `docs/make_screenshots.py` gains the page, and `docs/source/screenshots.rst` its entry. `tox -e jsdoc` generates `docs/source/jsdoc.budget_spending.rst`, which is committed. `tox -e docs` must build clean. `README.rst` and `CLAUDE.md` describe no page list that this changes. | ✅ PASS |
| **V. Escalate Instead Of Guessing** | The spec settled the open product questions as recorded assumptions: page placement, calendar periods, transfers, standing budgets, and an unsaved selection. Research R1–R7 settles the technical ones. None is a one-way door, and none needed a `[NEEDS CLARIFICATION]` marker. The one choice that makes a figure differ from an existing page, excluding transfers, is stated in the spec, the docs and the PR. | ✅ PASS |
| **VI. Changelog Every Change; Release Only On Request** | One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link. `version.py` is not touched, and there is no tag or release. The new Python module and the new unit test module carry the standard AGPL v3 header, and so does the new JS file, which follows the header convention of the existing JS files. | ✅ PASS |
| **Tech constraints: existing frontend stack** | jQuery, Bootstrap 3 panels and the already-vendored Morris.js (`Morris.Donut`). No new charting library. Moving charts to another library is issue #215, which stays out of scope. | ✅ PASS |
| **Tech constraints: financial correctness** | No pay-period arithmetic, allocation, interest or payoff code changes. The new sum is a new report. The rules it applies are pinned by acceptance tests with exact expected numbers: which transactions count, splits, and negative nets. So is its agreement with the pay period page's `spent` (SC-002). | ✅ PASS |
| **Tech constraints: security posture / secrets** | A read-only GET page and endpoint. No credentials. Nothing changes the localhost-only assumption. Budget names reach the page through jQuery `.text()` and Raphael SVG text, never HTML string concatenation, so a name containing `<` cannot inject markup. | ✅ PASS |
| **Tech constraints: test data safety** | Acceptance tests use the existing `refreshdb` fixture and test database only. Transactions inserted by the tests are committed there and removed by the next `refreshdb`. | ✅ PASS |

**Gate result: PASS, both before Phase 0 and after the Phase 1 design.** There are no
violations, so there is no Complexity Tracking table.

**Workflow note.** Development Workflow steps 3 and 5 require human approval of the plan
and at each milestone boundary. This session was dispatched to run the full lifecycle
through to an opened pull request. That is the dispatcher's decision to make, and it is
recorded here rather than left silently absent. The pull request is the review artifact,
and the maintainer approves at merge.

## Project Structure

### Documentation (this feature)

```text
specs/20260912-170923-budget-spending-pie-charts/
├── spec.md              # Feature specification (/speckit-specify)
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0: R1..R7
├── data-model.md        # Phase 1: derived entities, rules, invariants
├── quickstart.md        # Phase 1: validation scenarios
├── contracts/
│   ├── http-api.md      # Phase 1: GET /ajax/chart-data/budget-spending/by-period
│   └── ui.md            # Phase 1: page structure and element IDs
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
biweeklybudget/
├── budget_spending.py                       # NEW - reporting_periods(), spending_by_budget()
├── flaskapp/
│   ├── views/
│   │   └── budgets.py                       # + 'by-period' aggregation on
│   │                                        #   BudgetSpendingChartView;
│   │                                        #   + BudgetSpendingView (GET /budgets/spending)
│   ├── templates/
│   │   ├── budget-spending.html             # NEW - the page
│   │   ├── budgets.html                     # + link beside the existing charts
│   │   └── nav.html                         # + "Spending Charts" entry
│   └── static/js/
│       └── budget_spending.js               # NEW - donuts, tables, checkboxes
└── tests/
    ├── unit/
    │   └── test_budget_spending.py          # NEW - reporting_periods() boundaries
    └── acceptance/
        ├── test_budget_spending.py          # NEW - spending_by_budget() rules, SC-002
        └── flaskapp/views/
            └── test_budget_spending.py      # NEW - endpoint, page, checkboxes, links

docs/
├── make_screenshots.py                      # + budget-spending page
└── source/
    ├── app_usage.rst                        # + Spending By Budget Charts section
    ├── http_api.rst                         # + by-period chart data endpoint
    ├── screenshots.rst                      # + entry
    ├── biweeklybudget.budget_spending.rst   # NEW - autodoc stub, as for other modules
    ├── modules.rst / biweeklybudget.rst     # + toctree entry, if that is how stubs are listed
    └── jsdoc.budget_spending.rst            # generated by tox -e jsdoc, committed
CHANGES.rst                                  # + Unreleased entry
```

**Structure Decision**: Single Python package, following the existing layout. The
computation lives in a top-level module, like `cashposition.py` for the Cash Position
page, so it can be tested without Flask. The view stays thin. The endpoint joins the
existing budget-spending chart view instead of adding a second view class, so all three
spending-by-budget chart datasets are served by one class under one URL family.
