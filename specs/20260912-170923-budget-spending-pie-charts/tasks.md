---

description: "Task list for Spending By Budget Pie Charts"
---

# Tasks: Spending By Budget Pie Charts

**Input**: Design documents from `specs/20260912-170923-budget-spending-pie-charts/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/http-api.md](./contracts/http-api.md),
[contracts/ui.md](./contracts/ui.md), [quickstart.md](./quickstart.md)

**Tests**: Test tasks ARE included. The constitution's Test Gate (Principle II,
NON-NEGOTIABLE) makes tests mandatory for new code. So does its financial-correctness
constraint, which requires numbers pinned by tests.

**Organization**: Grouped by user story. The whole feature is one milestone, **M1**.

**Commit prefix**: `Spending By Budget Pie Charts - M1.{n}` per constitution Development
Workflow step 4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

Single Python package at the repository root: `biweeklybudget/`, with tests under
`biweeklybudget/tests/` and documentation under `docs/source/`. Paths are
repository-relative.

---

## Phase 1: Setup

**Purpose**: Bring up the environment that later phases verify against. No production code.

- [X] T001 Start the MariaDB test container and export the test environment variables per `CLAUDE.md` ("Test Database Setup for Development"), then run `python dev/setup_test_db.py` and `initdb` using the main checkout's venv (worktrees have no venv). No migration is created by this feature.
- [X] T002 Establish a green baseline for FR-014. Implemented as acceptance tests rather than scratchpad captures: `TestBudgetSpendingEndpoint.test_existing_by_month_unchanged` and `test_existing_by_pay_period_unchanged` pin the exact current JSON of `GET /ajax/chart-data/budget-spending/by-month` and `.../by-pay-period`, worked out by hand from the sample data. The methods behind them are unchanged from `master`. `test_budgets.py` still runs in the full suite (T021).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The computation module that every story reads from. It changes no page.

- [X] T003 Create `biweeklybudget/budget_spending.py` with the standard AGPL v3 header. Implement `reporting_periods(today, current_pp)`, a pure function (no DB, no `dtnow()`) returning the six period dicts (`key`, `name`, `start_date`, `end_date`) in the order and with the boundaries of research R2. Month end is the first of the next month minus one day. The previous month and year roll over correctly in January.
- [X] T004 In `biweeklybudget/budget_spending.py`, implement `spending_by_budget(db_session, start_date, end_date)`. It is one aggregate query per research R1: sum `BudgetTransaction.amount` joined to `Transaction` and `Budget`, with date BETWEEN inclusive, `Budget.is_income` false, `Transaction.transfer_id IS NULL`, and `not_(Transaction.is_excluded_from_budget)`, grouped by budget id. Return `{budget_id: Decimal}` quantized to `0.01`, omitting nets of exactly zero. Also implement `budget_spending_by_period(db_session, today)`. It finds the current pay period with `BiweeklyPayPeriod.period_for_date(today, db_session)` and returns the full response structure of `contracts/http-api.md`: `budgets` sorted by name then id, carrying `omit_from_graphs`; and `periods`, each with `spending` as a list of `{budget_id, amount}`. Full docstrings that state every counting rule and why transfers are excluded.
- [X] T005 [P] Create `biweeklybudget/tests/unit/test_budget_spending.py` with the AGPL header. Unit-test `reporting_periods()` using a minimal stand-in pay period object (`start_date`, `end_date`, `previous`) so no DB is needed. Cover: a mid-month date; 1 January (previous month is December of the prior year; previous year is correct); 31 December; 29 February 2020 (February ends on the 29th); 1 March 2021 (previous month ends 28 February); the order and keys of the six periods; `start <= end` for all; each previous period ending the day before its current one starts.
- [X] T006 Create `biweeklybudget/tests/acceptance/test_budget_spending.py` (marked `acceptance`, using `refreshdb`) testing `spending_by_budget()` against the test DB. Insert, via the `testdb` session, dedicated transactions in an otherwise-empty date range (e.g. 2016-03-01..2016-03-31, before the sample data) and assert exact Decimals for each row of data-model.md's rules table: an ordinary transaction counted; a split giving each budget its share; one day before and after the range excluded; an income budget excluded; both halves of a `do_budget_transfer()` excluded; `no_budget_impact=True` excluded; a credit card payment (`credit_payment_acct_id` set) excluded; an inactive budget counted; a refund reducing the net; a net of exactly zero omitted; a negative net returned as negative. Add an SC-002 test: for the sample data's current pay period (the acceptance timestamp is 2017-07-28; `PAY_PERIOD_START_DATE` is 2017-07-21), every periodic non-income budget's amount equals `BiweeklyPayPeriod.budget_sums[id]['spent']`, where no transfer touches that budget in the period.

**Checkpoint**: `budget_spending.py` passes its unit and acceptance tests.

---

## Phase 3: User Story 1 - See where the money went, per period (Priority: P1) 🎯 MVP

**Goal**: Six donut charts with totals and tables at `/budgets/spending`.

**Independent Test**: Open the page against known data and check each chart's table and total.

- [X] T007 [US1] In `biweeklybudget/flaskapp/views/budgets.py`, add the `by-period` branch to `BudgetSpendingChartView.get()`, returning `jsonify(budget_spending_by_period(db_session, dtnow().date()))`. Update the class docstring to list all three aggregations. Leave `_by_pay_period` and `_by_month` untouched. First confirm how the app's JSON provider serializes `Decimal` (`biweeklybudget/flaskapp/jsonencoder.py` / `app.py`). If it does not produce a JSON number, convert with `float()` after quantizing, and note that in the docstring.
- [X] T008 [US1] In `biweeklybudget/flaskapp/views/budgets.py`, add `BudgetSpendingView(MethodView)`, which renders `budget-spending.html`, and register it at `/budgets/spending` (endpoint `budget_spending_view`) next to the other budget routes.
- [X] T009 [US1] Create `biweeklybudget/flaskapp/templates/budget-spending.html` extending `base.html`: Morris CSS in `extra_head_css`, the notifications include, the budget-selection panel, and six panels with exactly the element IDs of `contracts/ui.md`, in a Bootstrap row (`col-lg-4 col-md-6`). Load Raphael, Morris and `/static/js/budget_spending.js` in `extra_foot_script`, as `budgets.html` does.
- [X] T010 [US1] Create `biweeklybudget/flaskapp/static/js/budget_spending.js` with the JS AGPL header and JSDoc on every function. It fetches the by-period endpoint once. For each period it draws title and dates, total, `Morris.Donut` (`data` as `{label, value}`, `colors` from the per-budget palette of research R4, a `formatter` showing currency and percentage), the table (Budget | Amount | Percent, largest first) and the credits list, following data-model.md "Client arithmetic" (sum in integer cents). It shows `#spending-<key>-nodata` and no donut when there are no slices, and an error message if the request fails. All names are inserted with `.text()`. Reuse the currency formatting helper in `static/js/custom.js` if one exists.
- [X] T011 [US1] Create `biweeklybudget/tests/acceptance/flaskapp/views/test_budget_spending.py` (AGPL header, `acceptance`, `refreshdb` + `testflask`). Endpoint tests: the response shape exactly per `contracts/http-api.md`; six periods with the exact dates for the 2017-07-28 timestamp (pay periods 2017-07-21..2017-08-03 and 2017-07-07..2017-07-20; July, June, 2017, 2016); `budgets` sorted and including the `omit_from_graphs` flag; no income budget present; per-budget amounts equal to values computed independently from the sample data. The expected numbers are written in the test, derived by reading `biweeklybudget/tests/fixtures/sampledata.py`, not by calling the code under test. `by-pay-period` and `by-month` still match the T002 captures. Page tests: the page loads with no JS errors; each panel's title shows its dates; each table's rows and total match the endpoint's slices for the default selection; the table amounts sum to the total; a period with no spending shows the "no spending" message.

**Checkpoint**: MVP. The charts render, and their numbers are pinned.

---

## Phase 4: User Story 2 - Leave specific budgets out (Priority: P1)

**Goal**: Checkboxes that exclude budgets from all six charts at once, with the default taken from "Omit from graphs".

**Independent Test**: Untick a budget and check that it disappears from every chart with recalculated totals. Re-tick it and check that the charts are restored.

- [X] T012 [US2] In `biweeklybudget/flaskapp/static/js/budget_spending.js`, build `#panel-budget-spending-selection` from `budgets`, one `input.budget-spending-toggle` each with the `id` and `data-budget-id` of `contracts/ui.md`, ticked unless `omit_from_graphs`. On `change`, redraw all six panels from the loaded data, with no request. Colours stay tied to each budget's index in the full `budgets` list. The selection is not stored anywhere.
- [X] T013 [US2] Add to `biweeklybudget/tests/acceptance/flaskapp/views/test_budget_spending.py`: Standing1 (sample data, `omit_from_graphs=True`) starts unticked and is absent from every table. Ticking it adds it and raises the affected totals by exactly its amount. Unticking another budget removes it from all six tables, each total dropping by that budget's amount there. Re-ticking restores the original tables. Unticking every budget shows the "no spending" message in all six panels. A reload restores the default selection. A negative-net budget (insert a refund in a test) is listed under credits, not in the table or total.

---

## Phase 5: User Story 3 - Find the charts (Priority: P2)

**Goal**: Links from the nav menu and from the Budgets page.

**Independent Test**: Follow both links and check that they arrive at `/budgets/spending`.

- [X] T014 [P] [US3] Add a "Spending Charts" entry (`fa-pie-chart`) directly after "Budgets" in `biweeklybudget/flaskapp/templates/nav.html`.
- [X] T015 [P] [US3] Add a link with id `link-budget-spending` to `/budgets/spending` beside the existing spending charts in `biweeklybudget/flaskapp/templates/budgets.html`. It goes in a panel heading, without changing the existing charts.
- [X] T016 [US3] Add to `biweeklybudget/tests/acceptance/flaskapp/views/test_budget_spending.py`: the nav link exists on the index page and leads to the page, and `#link-budget-spending` on `/budgets` leads to the page. Check whether `test_base_template.py` or any test asserts the full nav link list, and update it if so. *(That check was missed when this task was first ticked. The full acceptance run in T021 caught it: `TestBaseTemplateNavigation.test_nav_links` pins the whole sidebar list. It was fixed by adding `('/budgets/spending', 'Spending Charts')` after Budgets.)*

---

## Phase 6: Polish, Docs & Test Gate

- [X] T017 [P] Add a "Spending By Budget Charts" section to `docs/source/app_usage.rst`. Cover the six periods, exactly what is counted and excluded (and that this differs from the pay period page's "spent" for transfers), negative nets shown as credits, the checkboxes, and "Omit from graphs" as the permanent exclusion.
- [X] T018 [P] Document `GET /ajax/chart-data/budget-spending/by-period` under Charts in `docs/source/http_api.rst`, per `contracts/http-api.md`.
- [X] T019 [P] Add the page to `docs/make_screenshots.py` (path `/budgets/spending`, filename `budget-spending`) following the `cash-position` precedent. `docs/source/screenshots.rst` is generated by that script along with the images when a release is cut, so it is not edited by hand here (a hand-written entry would reference an image that does not exist yet and add a Sphinx warning). Add a Sphinx autodoc stub `docs/source/biweeklybudget.budget_spending.rst` and its toctree entry, matching how the other top-level modules are listed.
- [X] T020 [P] Add a concise entry under `Unreleased` at the top of `CHANGES.rst`, led by the issue #214 link. Do not touch `biweeklybudget/version.py`.
- [ ] T021 Run the Test Gate to completion, output to scratchpad files: `tox -e py314`, `tox -e acceptance`, `tox -e migrations`, `tox -e docs`, `tox -e jsdoc` (commit the generated `docs/source/jsdoc.budget_spending.rst`). Raise timeouts rather than narrowing any run. Re-run known-flaky tests in isolation before attributing a failure. Record the results in this file.
- [X] T022 Manually walk `quickstart.md`'s scenarios against `flask rundev` with the sample data, in a browser, and fix anything found.
- [ ] T023 Mark tasks complete, set the spec's Status to Complete, and commit everything. Push the branch to `origin` and open the pull request following `.github/PULL_REQUEST_TEMPLATE.md`, surfacing the spec's Assumptions (transfers excluded, standing budgets included, the selection not saved, donut shape) for the maintainer. Then monitor CI and answer reviews until Claude's review says "No issues found" and Copilot's, if present, recommends approval.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Phase 6.
- US2 extends the JS file that US1 creates, so it follows US1. US3's template edits (T014,
  T015) are independent of US1 and US2 and could be done at any point after Phase 2.
- T005 and T006 can run in parallel with each other once T003 and T004 exist.
- T017–T020 are independent documentation files and can be done in parallel.

## Parallel Example

```text
After T004:  T005 (unit tests) || T006 (acceptance tests of the module)
Phase 5:     T014 (nav.html)   || T015 (budgets.html)
Phase 6:     T017 || T018 || T019 || T020
```

## Implementation Strategy

MVP is US1: the charts render with pinned numbers. US2 completes what the issue asks for
(exclusion), and US3 makes the page discoverable. All three ship together as one milestone
and one pull request.
