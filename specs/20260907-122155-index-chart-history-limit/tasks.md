---

description: "Task list for Index Page Account Balances Chart — History Limiting"
---

# Tasks: Index Page Account Balances Chart — History Limiting

**Input**: Design documents from `specs/20260907-122155-index-chart-history-limit/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/http-api.md](./contracts/http-api.md),
[quickstart.md](./quickstart.md)

**Tests**: Test tasks ARE included. The spec requires them (SC-007) and the constitution's
Test Gate (Principle II, NON-NEGOTIABLE) makes them mandatory, not optional.

**Organization**: Grouped by user story so each can be implemented and verified independently.

**Commit prefix**: `Index Chart History Limit - {Phase}.{Task}` per constitution
Development Workflow step 4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are given in every task

## Path Conventions

Single Python package at the repository root: `biweeklybudget/`, with tests under
`biweeklybudget/tests/` and documentation under `docs/source/`. Paths below are
repository-relative.

---

## Phase 1: Setup

**Purpose**: Bring up the environment later phases verify against. No production code.

- [X] T001 Start the MariaDB test container and export the test environment variables per `CLAUDE.md` ("Test Database Setup for Development"), then run `python dev/setup_test_db.py` and `initdb` from the activated `venv`. No migration is created by this feature; `initdb` is run only to bring the test database to current head.
- [X] T002 Establish the green baseline before touching anything: run `pytest biweeklybudget/tests/unit/` and `pytest biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`, redirecting output to scratchpad files. Any pre-existing failure must be understood now so it cannot later be confused with one this feature introduced.
- [X] T003 Record in a scratchpad file the current response of `GET /ajax/chart-data/account-balances` against the sample data (point count, `keys` list, first and last `date`). This is the before-picture that FR-013 ("small installations see no change") is checked against in T024.

**Checkpoint**: Test database reachable, existing index tests pass, baseline endpoint output captured.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The two settings and the two pure helper functions every user story depends on.
This phase changes no rendered page and is verifiable entirely by unit test.

⚠️ **MUST complete before Phase 3.**

- [X] T004 Add `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS = 365` and `ACCOUNT_BALANCE_CHART_MAX_POINTS = 300` to `biweeklybudget/settings.py`, placed with the other int settings near `FUEL_BUDGET_ID`. Each gets a `#:` docstring comment in the established style (that file's comments are the autodoc source for `docs/source/biweeklybudget.settings.rst`): state the type, the default, that `0` means all history for the days setting, and that the max-points setting is a hard ceiling applied after sampling. Add both names to the `_INT_VARS` list so the existing environment-variable override path applies. Do **not** add either to `_REQUIRED_VARS` — an existing settings module that predates this feature must keep working on the defaults.
- [X] T005 [P] Mirror both settings, with the same `#:` comments, into `biweeklybudget/settings_example.py`, alongside `FUEL_BUDGET_ID`.
- [X] T006 Add a module-level helper `parse_chart_days(raw, default)` to `biweeklybudget/flaskapp/views/index.py`, above `AcctBalanaceChartView`. It implements the parameter-resolution table in [contracts/http-api.md](./contracts/http-api.md): returns `default` for `None`, empty string, non-integer, float-like (`"1.5"`), and negative input; returns `0` for `"0"`; returns the integer for a positive integer. It must never raise. Full docstring naming FR-010 and stating that bad input deliberately falls back rather than erroring, because this endpoint has no side effects and a default chart beats a traceback.
- [X] T007 Add a module-level helper `sample_chart_rows(rows, max_points)` to `biweeklybudget/flaskapp/views/index.py`, next to `parse_chart_days`. Implements research R4: return `rows` unchanged when `len(rows) <= max_points` or `rows` is empty; otherwise stride by `n = ceil(len(rows) / max_points)`, take `rows[::n]`, and append `rows[-1]` if the stride did not land on it. Guard `max_points < 1` by treating it as 1. Full docstring stating the five invariants from [data-model.md](./data-model.md) §"Sampled series", and calling out explicitly why the last row is pinned (FR-005): the chart's right edge must agree with the account tables directly below it on the same page.
- [X] T008 [P] Create `biweeklybudget/tests/unit/flaskapp/views/test_index.py` with the standard AGPL v3 copyright header copied from an existing file in that directory. Add `TestParseChartDays` covering every row of the contract's parameter-resolution table: absent/`None`, `""`, `"0"`, `"30"`, `"-1"`, `"abc"`, `"1.5"`, and a value far larger than any stored history.
- [X] T009 [P] Add `TestSampleChartRows` to `biweeklybudget/tests/unit/flaskapp/views/test_index.py`, asserting each data-model invariant as its own test: (a) `len(result) <= max_points` across several sizes including exact multiples and awkward remainders; (b) `len(rows) <= max_points` returns the identical list, same objects in the same order; (c) `result[-1] is rows[-1]` for non-empty input, including the case where the stride would otherwise skip it; (d) order preserved and ascending; (e) `[]` returns `[]`; (f) `max_points` of 1 returns exactly one row and it is the last; (g) a 1,825-row input (five years of daily balances — the reporter's actual scale) with `max_points=300` returns ≤300 rows ending at the last row.
- [X] T010 Run `pytest biweeklybudget/tests/unit/flaskapp/views/test_index.py -v` redirected to a scratchpad file; all must pass. Then confirm the two changed files are pycodestyle- and pyflakes-clean under the `pytest.ini` exceptions.

**Checkpoint**: Settings exist with documented defaults and env-var override; both helpers are correct and fully unit-tested; no rendered page has changed. Delivers FR-002, FR-003 (mechanism), FR-004, FR-005, FR-010.

---

## Phase 3: User Story 1 — Index page loads quickly with years of history (Priority: P1) 🎯 MVP

**Goal**: `GET /ajax/chart-data/account-balances` returns a bounded, windowed, correctly
forward-filled result, and no longer issues one query per balance row.

**Independent test**: Seed several years of daily balances; the endpoint returns at most
`ACCOUNT_BALANCE_CHART_MAX_POINTS` dates for both the default window and `days=0`, ends at the
latest recorded date, and issues O(accounts) queries rather than O(rows).

### Implementation for User Story 1

- [X] T011 [US1] In `AcctBalanaceChartView.get()` in `biweeklybudget/flaskapp/views/index.py`, replace `bal.account.name` with a lookup into the `accounts` dict the method already builds (`accounts[bal.account_id]`). This removes the lazy-load that issues one `SELECT` per balance row (research R1) — the single largest cost at the reporter's scale — and changes no output. Do this as its own commit so it is reviewable in isolation.
- [X] T012 [US1] Add window resolution to `AcctBalanaceChartView.get()`: read `days` via `parse_chart_days(request.args.get('days'), settings.ACCOUNT_BALANCE_CHART_DEFAULT_DAYS)`, compute `window_start = dtnow() - timedelta(days=days)` for `days > 0` and `None` for `days == 0`, and apply `AccountBalance.overall_date >= window_start` to the main query when `window_start` is not `None`. Import `request` from `flask`, `settings` from `biweeklybudget`, and `timedelta`; `dtnow` is already imported.
- [X] T013 [US1] Add the forward-fill seed query to `AcctBalanaceChartView.get()`, per research R5 and [data-model.md](./data-model.md) §"Balance carry-over map". When `window_start` is not `None`, fetch each account's most recent `ledger` strictly before `window_start` — a query grouped by `account_id`, bounded by account count, never by history size — and use it to initialise the carry-forward state before walking the in-window dates. **This is the correctness-critical task**: without it, an account whose latest balance predates the window is plotted as absent or zero, which on a financial chart asserts that the account was emptied. Accounts with no pre-window record start as `None` and are not back-filled (spec edge case: account created part-way through the window).
- [X] T014 [US1] Replace the existing forward-fill loop in `AcctBalanaceChartView.get()` so it seeds from T013's map instead of consuming the first date row as its seed. The current code skips the first date entirely (using it only to prime `last`); with an explicit seed that hack is unnecessary and the first in-window date becomes plottable. Note this deliberate one-extra-point change in a code comment referencing research R5, so it is not later mistaken for a regression.
- [X] T015 [US1] Apply `sample_chart_rows(resdata, settings.ACCOUNT_BALANCE_CHART_MAX_POINTS)` to the assembled rows immediately before `jsonify` in `AcctBalanaceChartView.get()`. Update the class docstring to describe the `days` parameter, the point cap, and the response guarantees G1–G7 from the contract.
- [X] T016 [US1] Verify by hand against the running app that the response for the sample data is unchanged in shape (`data`, `keys`) and that `days=0` reproduces the pre-change full-history view, comparing against the baseline captured in T003.

### Tests for User Story 1

- [X] T017 [P] [US1] Add `TestAcctBalanceChartData` to `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`, hitting the endpoint directly with `requests` against `base_url` (no Selenium needed for these): default request returns the documented shape; `days=0` returns all history; `days=30` returns strictly fewer or equal dates than `days=365`; a garbage `days=abc` returns the same result as no parameter at all (FR-010).
- [X] T018 [US1] Add `TestAcctBalanceChartLargeData` to `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`. It seeds several thousand synthetic `AccountBalance` rows (≈3 years of daily balances across the sample accounts) into the **test** database via the existing fixtures, then asserts: `len(data) <= ACCOUNT_BALANCE_CHART_MAX_POINTS` for `days=365` **and** for `days=0` (G1, SC-002); the last element's `date` equals the latest seeded date (G4); and that re-seeding to double the history leaves the default view's point count unchanged (SC-003). Without this test the feature's central guarantee is untested — the sample data is far too small to exercise it, and a test that only sees small data would be exactly the "test written to pass" the constitution forbids.
- [X] T019 [US1] Add a test to `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py` for the dormant-account case (G5): seed an account whose only balance record predates the window, request the default window, and assert that account appears in `keys` and carries its pre-window value — not `0`, not `null` — on every returned date. This pins the one way a windowed chart can be quietly, financially wrong.
- [X] T020 [US1] Run the index acceptance tests (`pytest biweeklybudget/tests/acceptance/flaskapp/views/test_index.py -v`) redirected to a scratchpad file; all must pass.

**Checkpoint**: The endpoint is fast, bounded and correct at scale. The index page already
loads visibly faster with no UI change at all — this is a shippable MVP on its own. Delivers
FR-001, FR-003, FR-004, FR-005, FR-006, FR-010, FR-011, FR-013.

---

## Phase 4: User Story 2 — Operator chooses how much history to see (Priority: P2)

**Goal**: A range selector on the index page redraws the chart in place over a chosen span.

**Independent test**: With multi-year data, click each range and confirm the chart redraws to
that span without navigation, and the clicked button becomes the active one.

### Implementation for User Story 2

- [X] T021 [US2] Add the range button group to the "Account Balances" panel heading in `biweeklybudget/flaskapp/templates/index.html`: a Bootstrap 3 `btn-group btn-group-xs` with `id="account-balance-chart-ranges"`, pulled right within the heading, one `<button type="button" class="btn btn-default" data-days="N">` per row of the contract's range table (1m/30, 3m/90, 6m/180, 1y/365, 2y/730, 5y/1825, All/0). Mark the 1y button `active` for now; T027 makes that settings-driven.
- [X] T022 [US2] Restructure `biweeklybudget/flaskapp/static/js/index.js` into named, JSDoc-commented functions rather than the current anonymous IIFE body — `acctBalanceChartData(days, cb)`, `drawAcctBalanceChart(ajaxdata)`, `updateAcctBalanceChart(days)` — keeping the existing `Morris.Line` options (`pointSize`, `hideHover`, `resize`, `preUnits: CURRENCY_SYMBOL`, `continuousLine`) exactly as they are. Named functions are what `tox -e jsdoc` documents; the anonymous form produces no documentation at all today.
- [X] T023 [US2] Implement redraw-in-place in `biweeklybudget/flaskapp/static/js/index.js`: hold the `Morris.Line` instance in a module-scoped variable and, on subsequent range changes, call `setData()` on it rather than constructing a new chart (FR-008). Bind a click handler on `#account-balance-chart-ranges button` that moves the `active` class to the clicked button (FR-009) and re-fetches with that `data-days` value.
- [X] T024 [US2] Handle the empty-data case in `biweeklybudget/flaskapp/static/js/index.js` (FR-012, G7): when `ajaxdata.data` is empty, render a plain "No account balance data to display." message in the panel body in place of the chart, and make sure a later non-empty response replaces it with a real chart rather than appending beside it.

### Tests for User Story 2

- [X] T025 [P] [US2] Add `TestAcctBalanceChartRanges` to `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py` using Selenium: the button group exists with the seven expected labels in order; exactly one button has `active`; clicking "All" moves `active` to it and leaves the browser on `/` (no navigation, FR-008); clicking "1m" moves it back.
- [X] T026 [US2] Add a Selenium assertion to `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py` that `#account-balance-chart` contains a rendered `svg` after page load and still contains one after a range change — the check that `setData()` redrew rather than destroying the chart.

**Checkpoint**: Users Stories 1 AND 2 both work. The chart is fast by default and the full
history is one click away. Delivers FR-007, FR-008, FR-009, FR-012.

---

## Phase 5: User Story 3 — Operator configures the default window (Priority: P3)

**Goal**: The shipped defaults are overridable through the existing settings mechanism, and
the UI follows the configured value rather than a hardcoded one.

**Independent test**: Set both settings to non-default values, load the page, and confirm the
initial span, the active button, and the point cap all follow the configuration.

### Implementation for User Story 3

- [X] T027 [US3] Emit the configured default into the page from `biweeklybudget/flaskapp/templates/index.html` as `var ACCOUNT_BALANCE_CHART_DEFAULT_DAYS = {{ settings.ACCOUNT_BALANCE_CHART_DEFAULT_DAYS }};`, following the `var CURRENCY_SYMBOL = "{{ CURRENCY_SYM }}";` precedent in `base.html`. `context_processors.py` already injects every settings global as `settings`, so no view change is needed (research R7).
- [X] T028 [US3] Make the active button settings-driven in `biweeklybudget/flaskapp/templates/index.html`: mark the button whose `data-days` equals the configured default as `active`, replacing T021's hardcoded 1y. If the configured value matches no offered button (for example 45), mark none active — the chart is still correct, and inventing a button for an arbitrary value would misreport what is displayed.
- [X] T029 [US3] Use `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` as the initial fetch value in `biweeklybudget/flaskapp/static/js/index.js` instead of relying on the endpoint's own default, so the button state and the plotted data can never disagree.

### Tests for User Story 3

- [X] T030 [P] [US3] Add tests to `biweeklybudget/tests/unit/flaskapp/views/test_index.py` confirming both settings are present in `biweeklybudget.settings` with the documented defaults, are listed in `_INT_VARS`, and are absent from `_REQUIRED_VARS` — the upgrade-path guarantee that an installation whose settings module predates this feature keeps working (User Story 3 scenario 3).
- [X] T031 [US3] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py` that patches `ACCOUNT_BALANCE_CHART_MAX_POINTS` to a small value and asserts the endpoint honours it, demonstrating the cap is genuinely read from configuration and not a constant in disguise.

**Checkpoint**: All three user stories are independently functional. Delivers FR-002 fully.

---

## Phase 6: Documentation

**Purpose**: Constitution Principle IV — documentation ships with the change, not after it.

- [X] T032 [P] Add an "Account Balances Chart" section to `docs/source/app_usage.rst` with an `.. _app_usage.account_balance_chart:` label, describing the default window, the range selector, that sampling keeps the most recent point so the chart agrees with the account tables below it, and that dormant accounts show a flat carried-forward line rather than dropping to zero. Name both settings with `:py:const:` cross-references, as the surrounding sections do.
- [X] T033 [P] Check whether `docs/source/http_api.rst` documents `/ajax/chart-data/account-balances`. It currently does not; add a short entry for it under the existing GET-endpoint pattern, covering the `days` parameter, the response shape, and the point cap. External scripts are exactly who that page is for, and the default-window change is the one behaviour an existing caller would notice.
- [X] T034 Run `tox -e jsdoc` to regenerate JavaScript documentation. The named functions from T022 will produce a new `docs/source/jsdoc.index.rst` and a new line in `docs/source/jsdoc.rst`; commit both, per the release checklist's requirement that regenerated docs are committed.

**Checkpoint**: Every documentation surface this change touches is updated.

---

## Phase 7: Full Verification

**Purpose**: Constitution Principle II. A narrowed run is not a pass, and a timed-out run is
not a pass.

- [ ] T035 Run `tox -e py314` to completion, output redirected to a scratchpad file. All must pass.
- [ ] T036 Run `tox -e acceptance` to completion — the whole suite, not a `-k` selection — output redirected to a scratchpad file. All must pass. If it times out, raise both the pytest timeout and the invoking tool's timeout and re-run until it completes.
- [ ] T037 [P] Run `tox -e docs` to completion; it must build with no errors, including the autodoc for the new settings and the new view helpers.
- [ ] T038 [P] Run `tox -e migrations` to completion. This feature changes no schema; the run is the check that this is still true.
- [ ] T039 Walk the manual checks in [quickstart.md](./quickstart.md) §3 and §4 against a running `flask rundev`, in particular verifying by eye that a dormant account holds a flat line rather than dropping to zero (§3 step 5), and that the environment-variable overrides in §4 take effect.

**Checkpoint**: Every suite the constitution requires has run to completion and passed.

---

## Phase 8: Release Bookkeeping & Delivery

**Purpose**: Constitution Principle VI, and this session's delivery obligation.

- [ ] T040 Bump `VERSION` in `biweeklybudget/version.py` from `1.9.0` to `1.10.0` — a new backwards-compatible user-visible capability plus new settings.
- [ ] T041 Add the `1.10.0` entry to `CHANGES.rst` in the established per-issue format, citing `Issue #279`. It must state: that the dominant cost was an N+1 lazy load rather than the data volume the issue named; the windowing and sampling rules including why the last point is pinned; the pre-window seed query and the dormant-account correctness problem it solves; the two new settings and their defaults; and that #215's chart-library migration was deliberately not folded in, with the constitution's stack constraint as the reason.
- [ ] T042 Record the outcome of each phase in this file, ticking the boxes, so the spec artifacts reflect what was actually built (constitution Development Workflow step 5c).
- [ ] T043 Commit, push the branch `robot-army/issue-279-fix-index-page-chart-when-lots-of-data` to `origin`, and open a pull request describing the change, the Constitution Check result, the deliberate deferral of #215, the one behaviour change existing endpoint callers will see (no `days` parameter now means the default window, with `days=0` restoring the old response), and the recorded Principle I deviation on milestone approval.
- [ ] T044 Monitor the pull request's CI jobs to completion, then use `/answer-reviews` to respond to review feedback, repeating until Claude's review reports "No issues found" and Copilot's, if present, recommends approval.

---

## Dependencies & Execution Order

```text
Phase 1 (Setup)
   ↓
Phase 2 (Foundational: settings + helpers)   ← blocks everything
   ↓
Phase 3 (US1, P1: server-side window/sample/N+1)   ← MVP; independently shippable
   ↓
Phase 4 (US2, P2: range selector UI)   ← needs US1's `days` parameter to exist
   ↓
Phase 5 (US3, P3: settings-driven default in the UI)   ← needs US2's button group
   ↓
Phase 6 (Documentation)
   ↓
Phase 7 (Full verification)
   ↓
Phase 8 (Release bookkeeping & delivery)
```

### User Story Dependencies

- **US1 (P1)**: depends only on Phase 2. Fully shippable alone — the index page gets fast
  and bounded with no visible UI change.
- **US2 (P2)**: depends on US1, because the range buttons have nothing to call until the
  `days` parameter exists. Independently *testable* once US1 is in.
- **US3 (P3)**: depends on US2, because "the configured default is the active button" needs
  buttons. The server half of configurability lands in Phase 2 and is exercised by US1.

This chain is genuine rather than incidental: the stories are layers of one control path, and
pretending they are parallel would produce untestable half-states.

### Parallel Execution Opportunities

- T005 (settings_example) runs alongside T004's helper work.
- T008 and T009 (the two unit test classes) are independent of each other.
- T017 and T025 touch different test classes in the same file — sequence them to avoid edit
  conflicts even though they are logically independent.
- T032 and T033 (two different `.rst` files) are genuinely parallel.
- T037 and T038 (`docs`, `migrations`) can run concurrently with each other, but not with
  T036, which needs the browser and the database to itself.

---

## Implementation Strategy

### MVP scope

**Phases 1–3 (T001–T020).** This alone closes the performance half of issue #279: the page
loads quickly, the payload is bounded, and the chart is legible at a one-year default. It
changes no UI and could be shipped by itself.

### Incremental delivery

1. Phases 1–2 → settings and helpers, fully unit-tested, nothing user-visible.
2. Phase 3 → **MVP**: fast, bounded, correct endpoint. Validate, then continue.
3. Phase 4 → the "zoom out" the issue asks for.
4. Phase 5 → configurable default reflected in the UI.
5. Phases 6–8 → documentation, full suites, version, changelog, PR.

### Notes

- Commit after each task or logical group, prefixed `Index Chart History Limit - {Phase}.{Task}`.
- T011 (the N+1 fix) is deliberately its own commit: it is a one-line change with an outsized
  effect and belongs in the history where a reviewer can see it on its own.
- T013 and T019 are the correctness core. Everything else is performance and presentation;
  those two are the difference between a windowed chart that is right and one that quietly
  misreports a dormant account's balance as zero.
