---

description: "Task list for Configurable Fuel Levels"
---

# Tasks: Configurable Fuel Levels

**Input**: Design documents from `specs/20260912-073811-configurable-fuel-levels/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/fuel-levels-setting.md, quickstart.md

**Tests**: Included. Constitution II requires new code to be covered by valid tests, and
the spec's success criteria SC-002 and SC-003 are verified by them.

**Organization**: Grouped by user story. The setting's default and the JS that builds the
selects from it are shared by every story, so they are Foundational. The whole feature is
one milestone (M1). Commit prefix: `Configurable Fuel Levels - M1.x`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

- Settings: `biweeklybudget/settings.py`
- Fuel page template: `biweeklybudget/flaskapp/templates/fuel.html`
- Fuel page JS: `biweeklybudget/flaskapp/static/js/fuel.js`
- New unit tests: `biweeklybudget/tests/unit/test_settings_fuel_levels.py`
- Acceptance tests: `biweeklybudget/tests/acceptance/flaskapp/views/test_fuel.py`
- Docs: `docs/source/app_usage.rst`, `docs/source/http_api.rst`; changelog `CHANGES.rst`

---

## Phase 1: Setup

**Purpose**: A working test environment, so the new tests can be seen to fail and then pass.

- [X] T001 Start the MariaDB test container and create the test databases per `CLAUDE.md` ("Test Database Setup for Development"), using tox from the main checkout's venv. Confirm a green baseline for the fuel acceptance tests with `tox -e acceptance -- biweeklybudget/tests/acceptance/flaskapp/views/test_fuel.py`, output redirected to the scratchpad.

---

## Phase 2: Foundational (blocks all stories)

**Purpose**: The setting exists with today's values as its default, reaches the page, and the form is built from it.

- [X] T002 Create `biweeklybudget/tests/unit/test_settings_fuel_levels.py` with the standard AGPL header (copy from an existing test module). Add `TestFuelLevelsDefault.test_default`, asserting `settings.FUEL_LEVELS == [('%d/10' % i, i * 10) for i in range(11)]`. The test settings module does not set `FUEL_LEVELS`, so this pins the default. Confirm it fails (no attribute) before T003.
- [X] T003 In `biweeklybudget/settings.py`, after `FUEL_ECO_ABBREVIATION`, add `FUEL_LEVELS = [('%d/10' % i, i * 10) for i in range(11)]` with a `#:` docstring. The docstring covers: an ordered list of `(label, percentage)` pairs offered as the Add Fuel Fill form's starting and ending fuel levels; the percentage (whole number 0–100) is what is stored; the form shows them in order and defaults to the lowest and highest percentage; the env-var syntax `label:percentage` separated by commas, split on the last colon, with no commas in labels; an example `E:0,1/4:25,1/2:50,3/4:75,F:100`; the validation rules from `contracts/fuel-levels-setting.md`; and a pointer to `:ref:`Currency Formatting and Localization <app_usage.l10n>``.
- [X] T004 [P] In `biweeklybudget/flaskapp/templates/fuel.html`, in the inline `<script>` that sets `fuel_budget_id` (~line 155), add `var FUEL_LEVELS = {{ settings.FUEL_LEVELS|tojson }};`.
- [X] T005 [P] In `biweeklybudget/flaskapp/static/js/fuel.js`:
  - Add a JSDoc-commented `fuelLevelOptions(selectedValue)` that returns an Array of `{value: pct, label: <HTML-escaped label>, selected: pct == selectedValue}` built from the global `FUEL_LEVELS` in order. Reuse an existing HTML-escape helper from `static/js` if there is one; otherwise add a small local one escaping `& < > " '`.
  - In `fuelModalDivForm()`, compute the min and max percentage in `FUEL_LEVELS`. Replace the two `addLabelToValueSelect(...)` calls for `fuel_frm_level_before`/`fuel_frm_level_after` with `addSelect(id, name, label, fuelLevelOptions(min|max))`, keeping the same ids, names and labels.
  - Done as: the existing `escapeHtml()` was only in `budgets_modal.js`, which the fuel page doesn't load. So it moved to `custom.js`, which every page loads via `base.html`, instead of being duplicated (see plan.md, Test Gate Results).

**Checkpoint**: T002 passes. With no configuration the form should look exactly as before (verified in US2).

---

## Phase 3: User Story 1 — Log a fill using my own gauge's markings (Priority: P1) 🎯 MVP

**Goal**: A configured list, from the settings module or the `FUEL_LEVELS` env var, drives both selects, in order, with the right defaults, and saving records the paired percentages.

**Independent Test**: The US1 unit and acceptance tests below pass. Manually: `quickstart.md` step 2.

### Tests for User Story 1

- [X] T006 [US1] In `test_settings_fuel_levels.py`, add `TestParseFuelLevels`:
  - `E:0,1/4:25,1/2:50,3/4:75,F:100` → the five pairs in order.
  - Whitespace around labels and percentages is stripped (` E : 0 , F:100 `).
  - A label containing a colon splits on the last colon (`a:b:50` → `('a:b', 50)`).
  - A non-digit percentage (`E:x`, `E:-5`, `E:1.5`) and an entry with no colon raise `ValueError`.

  Also add `TestFuelLevelsEnvVar.test_env_var_is_used`, which runs `subprocess.run([sys.executable, '-c', 'import json; from biweeklybudget import settings; print(json.dumps(settings.FUEL_LEVELS))'], env={**os.environ, 'FUEL_LEVELS': 'E:0,1/2:50,F:100', 'DB_CONNSTRING': os.environ.get('DB_CONNSTRING', 'mysql+pymysql://u:p@127.0.0.1/x')}, capture_output=True, text=True)`. Assert return code 0 and the last stdout line parses to `[['E', 0], ['1/2', 50], ['F', 100]]`. Confirm these fail before T007.
- [X] T007 [US1] In `biweeklybudget/settings.py`, add module-level `parse_fuel_levels(value)` with a docstring, per research R3. Split on `,`; each entry is `rpartition(':')`, and an empty separator means `ValueError`. Strip both parts. The percentage must match `^\d+$`, else `ValueError` naming the offending entry. Return a list of `(label, int(pct))` tuples. After the `_DATE_VARS` env loop, add: `if 'FUEL_LEVELS' in os.environ: FUEL_LEVELS = parse_fuel_levels(os.environ['FUEL_LEVELS'])`, converting `ValueError` to `SystemExit('ERROR: FUEL_LEVELS setting is invalid: %s' % ex)`. T006 must pass.
- [X] T008 [US1] In `test_fuel.py`, append a new acceptance class `TestFuelLevelsConfigured` (same base class and `@pytest.mark.acceptance` / `usefixtures` pattern as the existing classes, checking how class-level DB refresh works so that fill IDs are predictable). Its tests:
  - `test_1_custom_levels`: load `/fuel` and run `selenium.execute_script("FUEL_LEVELS = [['E', 0], ['1/4', 25], ['1/2', 50], ['3/4', 75], ['F', 100]];")`. Open **Add Fill**. Assert both selects' `[value, text]` options are exactly `[['0','E'],['25','1/4'],['50','1/2'],['75','3/4'],['100','F']]`, with `level_before` selected `0` and `level_after` selected `100`.
  - `test_2_add_fill`: with the same override, fill the form like `test_12_fuel_add_no_trans` (add-transaction unchecked), choosing `1/4` → `F`. Save, and confirm the success message.
  - `test_3_verify_db`: the new `FuelFill` has `level_before == 25` and `level_after == 100`.
  - `test_4_numeric_and_markup_labels`: override with `[['8', 100], ['4', 50], ['<b>0</b> & E', 0]]`. Assert option order and values are `[['100','8'],['50','4'],['0','<b>0</b> & E']]`, meaning the text is literal and there is no `<b>` element in the select. Assert `level_before` selected `0` and `level_after` selected `100`.

**Checkpoint**: US1 delivered: a configured list drives the form and is stored as percentages.

---

## Phase 4: User Story 2 — Nothing changes for an operator who configures nothing (Priority: P1)

**Goal**: With no configuration, the form, recorded values and defaults are identical to before.

**Independent Test**: The existing default-list acceptance assertions pass unchanged, plus the check below.

- [X] T009 [US2] In `test_fuel.py`, leave `LEVEL_OPTS` and the `test_11_fuel_populate_modal` / `test_12` / `test_14` level assertions exactly as they are, so they guard FR-003. In `test_11_fuel_populate_modal`, after loading `/fuel`, add `assert selenium.execute_script('return FUEL_LEVELS;') == [[l, int(v)] for v, l in LEVEL_OPTS]`. This proves the server renders the default setting into the page. Run the fuel acceptance tests; all existing and new ones pass.

**Checkpoint**: US1 and US2 pass.

---

## Phase 5: User Story 3 — A mistake in the configuration is reported, not silently used (Priority: P2)

**Goal**: Any invalid list, from either source, aborts startup with an error naming `FUEL_LEVELS`.

**Independent Test**: The US3 unit tests below pass. Manually: `quickstart.md` step 3.

### Tests for User Story 3

- [X] T010 [US3] In `test_settings_fuel_levels.py`, add `TestValidateFuelLevels`:
  - Valid lists of tuples and of lists return a list of `(label, pct)` tuples with labels stripped.
  - Each of these raises `ValueError`, parametrized: fewer than two levels (0 and 1 entries); an entry that isn't a 2-item list/tuple (`('E',)`, `('E', 0, 1)`, a bare string); an empty or whitespace label; a non-str label (`None`); percentage `0.5`, `'50'`, `True`; percentage `-1` or `101`; a duplicated label; a duplicated percentage; a non-list value (`None`, `'E:0,F:100'`).
  - The boundaries 0 and 100 are accepted.

  Add `TestFuelLevelsEnvVar.test_invalid_env_var_exits`, parametrized over `E:0,F:150`, `F:100`, `E:0,E:50,F:100`, `E:x,F:100` and using the T006 subprocess helper. Assert a non-zero return code and `'FUEL_LEVELS setting is invalid'` in stderr. Confirm these fail before T011.
- [X] T011 [US3] In `biweeklybudget/settings.py`, add module-level `validate_fuel_levels(levels)` with a docstring implementing the rules in `contracts/fuel-levels-setting.md` (research R4). It returns a new normalised list and raises `ValueError` with a specific reason. After the env-var step from T007, and before the `_REQUIRED_VARS` check, run `FUEL_LEVELS = validate_fuel_levels(FUEL_LEVELS)`, converting `ValueError` to the same `SystemExit` message. T010 and all earlier tests must pass.

**Checkpoint**: All three stories pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T012 [P] In `docs/source/app_usage.rst`, in the Fuel Log settings list (~line 66), add a bullet for `:py:attr:`biweeklybudget.settings.FUEL_LEVELS``, which sets the fuel level choices on the Add Fuel Fill form. Adjust the following sentence, which says these settings only affect display of units, so it stays accurate.
- [X] T013 [P] In `docs/source/http_api.rst` (~line 730), change the `level_before`/`level_after` descriptions to say the value is a percentage of a full tank (0-100), normally one of the `FUEL_LEVELS` setting's percentages.
- [X] T014 [P] In `CHANGES.rst`, add one concise bullet at the top of `Unreleased`, led by the `Issue #208` link: the fuel level choices on the Add Fuel Fill form are now configurable via the new `FUEL_LEVELS` setting; the default is unchanged. Add a short sub-bullet with the env-var format example. Do not touch `biweeklybudget/version.py`.
- [X] T015 Run the Test Gate (Constitution II) to completion, redirecting output to scratchpad files:
  - `tox -e py314`, which also covers pycodestyle and pyflakes.
  - `tox -e acceptance`.
  - `tox -e docs`.

  Raise the timeouts and re-run if a suite times out, rather than narrowing it. `migrations`, `docker`, and `plaid` are not engaged and run in CI.
- [X] T016 Manually walk through `quickstart.md` steps 1–3 against `flask rundev`, or record why that wasn't possible.
- [X] T017 Record results in the spec artifacts: set `spec.md` Status to Complete, mark the tasks here done, and add a "Test Gate Results" section to `plan.md`. Commit with the prefix `Configurable Fuel Levels - M1.x`.
- [X] T018 Push the branch to `origin` and open the pull request, following `.github/PULL_REQUEST_TEMPLATE.md` and surfacing the spec's Assumptions (global list, percentages stored) for the maintainer. Then monitor CI and answer reviews until Claude's review says "No issues found" and Copilot's, if present, recommends approval.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)** blocks everything that runs tests.
- **Foundational**: T002 → T003. T004 and T005 are independent files and can be done alongside T003. All of T002–T005 block the stories.
- **US1**: T006 → T007 (unit). T008 (acceptance) depends on T004/T005 only.
- **US2**: T009 depends on T004/T005.
- **US3**: T010 → T011. T011 edits the same import-time block as T007, so it follows it.
- **Polish**: T012–T014 are different files and can run in parallel at any time after T003. T015 depends on T002–T014. T016 needs T011. T017 depends on T015/T016, and T018 on T017.

### User Story Dependencies

- US1, US2 and US3 all depend on Foundational only. US3's validation also runs on US1's env-var output, but its tests don't need US1's code.
- T006, T010 and T002 share one test file, and T008 and T009 share `test_fuel.py`, so tasks within each file are done sequentially.

### Parallel Opportunities

- T004 ∥ T005 ∥ T003.
- T012 ∥ T013 ∥ T014.
- Within T015, run the `docs` suite concurrently with the DB suites. Run `py314` and `acceptance` sequentially, since both use the test database.

---

## Parallel Example: Foundational

```bash
Task: "Add FUEL_LEVELS default + docstring in biweeklybudget/settings.py"
Task: "Expose FUEL_LEVELS global in biweeklybudget/flaskapp/templates/fuel.html"
Task: "Build level selects from FUEL_LEVELS in biweeklybudget/flaskapp/static/js/fuel.js"
```

---

## Implementation Strategy

### MVP First

T001–T008 is the MVP: a settings-module or env-var list drives the form. T009 locks in the
unchanged default, T010–T011 add safety, and T012–T018 document, verify and deliver. At
this size all of it ships together as milestone M1 in one pull request.

---

## Notes

- Unit tests need the MariaDB container (see `CLAUDE.md`). Without it, `test_plaid.py` and `test_utils.py` fail to collect.
- Never test import-time behaviour with `importlib.reload(settings)`. Other modules hold references to the module object, and a failed reload leaves it half-initialised. Use a subprocess.
- Flaky `TestDragLimitations::test_11_unreconcile` (reconcile) is a known intermittent failure. Re-run it in isolation before blaming this change.
