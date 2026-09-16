---

description: "Task list for Duplicate Name Validation on Account and Budget Forms"
---

# Tasks: Duplicate Name Validation on Account and Budget Forms

**Input**: Design documents from `specs/20260916-183529-duplicate-name-validation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/form-endpoints.md](./contracts/form-endpoints.md), [quickstart.md](./quickstart.md)

**Tests**: Included, and not optional here — spec FR-010 requires acceptance coverage, and Constitution Principle II requires new code to be covered by valid tests.

**Organization**: Phases are the four milestones from [plan.md](./plan.md). Each is one commit, prefixed `Duplicate Name Validation - M.T` per Constitution Development Workflow step 4. Story labels ([US1]–[US4]) map tasks back to the spec's user stories.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: The spec user story the task serves; omitted for cross-cutting tasks
- Paths are repository-relative from `/home/jantman/worktrees/biweeklybudget/issue-275`

---

## Phase M1: Observe the current behaviour (US4, P3) ⚠️ GATE

**Goal**: Record what a duplicate account-name submission actually does on current code, in a real browser, before any fix is written. Satisfies FR-009 and spec User Story 4.

**Why this is first**: The original 1.1.1 report says the failure was *silent*. Reading the code says it produces a `Server Error:` banner. If the report is right, a field-level validation message would be equally invisible and the whole scope is wrong. This milestone settles it with an observation instead of an assumption.

**Independent Test**: Drive the running app in a browser, submit `BankOne` as a new account name, and record exactly what the user sees.

- [X] T001 Start the MariaDB test container and initialise the test database per the Prerequisites in [quickstart.md](./quickstart.md) (`docker run ... mariadb:10.4.7`, export the `MYSQL_*`/`DB_CONNSTRING`/`SETTINGS_MODULE` variables, `python dev/setup_test_db.py`, `initdb`)
- [X] T002 Load the acceptance fixture data so the accounts named in [quickstart.md](./quickstart.md) exist, then start the app with `FLASK_APP=biweeklybudget.flaskapp.app:app flask rundev`
- [X] T003 [US4] In a real browser, open `/accounts`, use **Add Account** to submit the name `BankOne` (already taken), and capture what is rendered: the exact banner or field text, which element it lands in, and whether the modal stays open
- [X] T004 [US4] Confirm against the database that no account was created by the rejected submission, and capture the server-side log line `FormHandlerView.post()` emits
- [X] T005 [US4] Add an "Observed behaviour before the fix" section to [spec.md](./spec.md) recording T003 and T004 verbatim — the message text, where it appears, and whether the original "silent" report reproduces
- [X] T006 [US4] **Decision gate**: if T003 showed *no* feedback at all, stop. Record the finding in [spec.md](./spec.md) as a Principle V departure, commit that record, and seek guidance before writing any fix. Otherwise, proceed to M2.

**Checkpoint**: The pre-fix behaviour is written into the spec and committed. SC-005 satisfied.

---

## Phase M2: The duplicate-name check (serves US1, US2, US3)

**Goal**: One helper on `FormHandlerView`, called from both form handlers, with unit tests pinning the semantics [research.md](./research.md) R2 settled.

**Why one helper**: See [research.md](./research.md) R1. The case and trim rules get decided once rather than in two places that can drift.

### Implementation

- [ ] T007 Add `_validate_unique_name(self, cls, data, errors, noun, key='name')` to `biweeklybudget/flaskapp/views/formhandlerview.py`: query `cls` for `func.lower(cls.name) == data[key].strip().lower()` and `cls.id != record_id`, where `record_id` is `int(data['id'])` when `data` has a non-blank `'id'` else `0`; on a hit append one message naming `noun`, the conflicting record's name and its ID to `errors[key]`; return `errors`. Import `func` from `sqlalchemy`. Return unchanged when `data[key].strip()` is empty, so a blank name keeps its single "Name cannot be empty" message (spec Edge Cases)
- [ ] T008 Give T007 a docstring in the file's existing style, stating why the comparison is trimmed and case-insensitive and citing GitHub issue #275 — this feeds the `docs` API build (Constitution Principle IV)
- [ ] T009 [P] Call `self._validate_unique_name(Account, data, errors, 'Account')` from `AccountFormHandler.validate()` in `biweeklybudget/flaskapp/views/accounts.py`, placed after the existing empty-name check and before the `have_errors` return, so a duplicate name is reported alongside any other field errors (FR-008)
- [ ] T010 [P] Call `self._validate_unique_name(Budget, data, errors, 'Budget')` from `BudgetFormHandler.validate()` in `biweeklybudget/flaskapp/views/budgets.py`, in the equivalent position. Note `BudgetFormHandler.validate()` currently returns `None` unless `have_errors`; make it also return `errors` when any field list is non-empty, matching how `AccountFormHandler.validate()` already ends, or the new message will be silently dropped
- [X] T011 Verify empirically that the check's verdict matches the database's: against the running test DB, confirm whether the `utf8mb4` collation in use treats `BankOne` and `bankone` as colliding, and record the answer in [research.md](./research.md) R2. The `func.lower()` design is correct either way (R2), but the note should state what was measured rather than what was expected

### Unit tests

- [ ] T012 [P] In `biweeklybudget/tests/unit/flaskapp/views/test_formhandlerview.py`, test `_validate_unique_name` rejects a name held by a different record (US1)
- [ ] T013 [P] In the same file, test it accepts a name held only by the record being edited, i.e. `data['id']` matches the conflicting row (US2, FR-002/FR-004)
- [ ] T014 [P] In the same file, test the comparison is applied to the *trimmed* submitted name, so `"  BankOne  "` is rejected against a stored `"BankOne"` (FR-007)
- [ ] T015 [P] In the same file, test the comparison is case-insensitive, so `"bankone"` is rejected against a stored `"BankOne"` (FR-007)
- [ ] T016 [P] In the same file, test a blank name adds no duplicate-name message, leaving only the caller's existing "Name cannot be empty" (spec Edge Cases)
- [ ] T017 Run `tox -e py314` to completion and confirm the unit suite passes and the diff is `pycodestyle`/`pyflakes` clean per `pytest.ini`

**Checkpoint**: The check exists and its semantics are pinned by tests. FR-001 through FR-008 implemented.

---

## Phase M3: Acceptance coverage and documentation

**Goal**: Prove the behaviour end to end through the real forms, on every path FR-010 names, and document the rule.

**Independent Test**: Each story below is verifiable on its own through its own form, per the scenarios in [quickstart.md](./quickstart.md).

### User Story 1 + 2 — Accounts (P1)

- [ ] T018 [US1] In `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py`, add a browser test that opens the Add Account modal, submits an existing account name, and asserts a `formfeedback` element carries the duplicate-name message and that no `Server Error:` banner is present — following the assertion pattern already in `test_04_no_date_error`
- [ ] T019 [US1] In the same file, add a `requests.post` test against `/forms/account` asserting the exact JSON `{"success": false, "errors": {"name": [...], ...}}` shape from [contracts/form-endpoints.md](./contracts/form-endpoints.md) — following `test_05_no_date_error_requests`
- [ ] T020 [US1] In the same file, assert the rejected submission created no account, and that correcting the name and resubmitting succeeds (spec US1 scenario 3, SC-002)
- [ ] T021 [US2] In the same file, add a test that renaming an existing account onto another account's name is rejected and changes neither account
- [ ] T022 [US2] In the same file, add a test that saving an existing account with its name unchanged still succeeds (FR-002, SC-003) — the regression this check could most easily introduce

### User Story 3 — Budgets (P2)

- [ ] T023 [P] [US3] In `biweeklybudget/tests/acceptance/flaskapp/views/test_budgets.py`, add a browser test for submitting an existing budget name through the Add Budget modal, asserting the field-level message
- [ ] T024 [P] [US3] In the same file, add a `requests.post` test against `/forms/budget` asserting the JSON error shape
- [ ] T025 [P] [US3] In the same file, add tests for renaming a budget onto another budget's name (rejected) and for saving a budget with its name unchanged (succeeds)

### Documentation

- [ ] T026 [P] Document the uniqueness rule and its field-level message in the appropriate page under `docs/source/` — locate the page that describes the account and budget forms and add a sentence there rather than creating a new page
- [ ] T027 Run the new acceptance tests (`tox -e acceptance -- -k 'accounts or budgets'`) and `tox -e docs`, redirecting output to the scratchpad per `CLAUDE.md` rather than piping to `tail`

**Checkpoint**: FR-010 satisfied on every named path. Documentation current (Principle IV).

---

## Phase M4: Close the test gate and open the PR

**Goal**: Everything green, changelog written, branch pushed, PR open and passing CI.

- [ ] T028 Re-check `git diff` against `biweeklybudget/models/` to confirm the Principle III claim held — no model file touched, therefore no Alembic revision and no `migrations` run required. If the diff contradicts this, the plan's Constitution Check is wrong and a migration is owed before proceeding
- [ ] T029 Run the **complete** unit suite (`tox -e py314`) to completion, output to the scratchpad. A timeout is not a pass: raise both the pytest timeout and the tool timeout and re-run until it completes
- [ ] T030 Run the **complete** acceptance suite (`tox -e acceptance`) to completion, output to the scratchpad, under the same no-narrowing and no-timeout rules. Re-run any of the known-flaky tests (reconcile drag/unignore, fuel-log search, Plaid "Uncheck All") in isolation before attributing a failure to this change
- [ ] T031 Run `tox -e docs` and confirm it builds without errors
- [ ] T032 Add one concise bullet to `CHANGES.rst` under the `Unreleased` heading, led by the issue #275 link, in the format of the existing entries. Do **not** touch `biweeklybudget/version.py` and do not create a tag (Principle VI)
- [ ] T033 Update [spec.md](./spec.md) and this file to record milestone completion, then commit M3 and M4 with the `Duplicate Name Validation - M.T` prefix
- [ ] T034 Push the branch with `git push -u origin HEAD:refs/heads/robot-army/issue-275-silent-failure-on-duplicate-account-name` — a bare `git push` would target `master`, which this branch tracks
- [ ] T035 Open a pull request describing the problem, the M1 observation, the design decision from [research.md](./research.md) R2, and the test coverage; then monitor CI to completion and address any review feedback until Claude reports "No issues found" and Copilot, if present, recommends approval

**Checkpoint**: Feature complete per Constitution Development Workflow step 6.

---

## Dependencies & Execution Order

### Phase dependencies

- **M1** blocks everything. It is a gate, not a formality: T006 can stop the feature.
- **M2** depends on M1 clearing. T007 blocks T009, T010 and all of T012–T016.
- **M3** depends on M2. The account tasks (T018–T022) and budget tasks (T023–T025) are independent of each other.
- **M4** depends on M2 and M3 both being complete.

### Within M2

- T007 (the helper) before T008 (its docstring), T009/T010 (its callers), and T012–T016 (its tests)
- T009 and T010 touch different files and are parallel
- T012–T016 all touch `test_formhandlerview.py` — written together in one pass, listed [P] because they are independent in content, not because they should be edited concurrently
- T011 needs a running database, which M1's T001 already provides

### Within M3

- T018–T022 are sequential: all touch `test_accounts.py`, and T020's "correct it and resubmit" builds on T018's state if placed in an incremental class
- T023–T025 touch `test_budgets.py` and are parallel with the account tasks
- T026 touches `docs/source/` and is parallel with all test tasks

### Parallel opportunities

```bash
# After T007 lands, the two call sites are independent:
Task: "Call _validate_unique_name from AccountFormHandler.validate() in biweeklybudget/flaskapp/views/accounts.py"
Task: "Call _validate_unique_name from BudgetFormHandler.validate() in biweeklybudget/flaskapp/views/budgets.py"

# In M3, three independent files:
Task: "Account acceptance tests in biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py"
Task: "Budget acceptance tests in biweeklybudget/tests/acceptance/flaskapp/views/test_budgets.py"
Task: "Uniqueness rule paragraph in docs/source/"
```

---

## Implementation Strategy

### MVP scope

**M1 + M2 + the account half of M3 (T018–T022)** is the smallest thing that closes the reported issue: the account form, which is what #275 is about, with the message attached to the Name field and acceptance coverage on both the create and the rename path.

The budget half (T023–T025) is what keeps the application from handling the identical mistake two different ways, and is why the spec's User Story 3 exists. It is small — the helper is already written by then — so it ships in the same change rather than being deferred.

### Incremental delivery

1. M1 → the pre-fix behaviour is on the record, and the scope is confirmed rather than assumed
2. M2 → the check works and its semantics are pinned; verifiable by hand via [quickstart.md](./quickstart.md)
3. M3 → both forms covered end to end, documentation current
4. M4 → full suites green, changelog, PR

### Notes

- Commit after each milestone with the `Duplicate Name Validation - M.T` prefix
- Test output goes to the scratchpad directory, never piped to `tail`/`head`/`grep` (`CLAUDE.md`)
- `tox` runs from the main checkout's venv; there is no venv in this worktree
