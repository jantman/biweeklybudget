---

description: "Task list for removing the sqlalchemy-diff dependency"
---

# Tasks: Remove the sqlalchemy-diff Dependency

**Input**: Design documents from `specs/20260909-185411-remove-sqlalchemy-diff/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [quickstart.md](./quickstart.md)

**Tests**: This feature *is* test infrastructure. The suite it modifies is the test for
the change, so no separate test tasks are generated — instead, T009 requires the rebuilt
comparison to be proven non-vacuous against injected drift before it is trusted.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task serves (US1–US4 from spec.md)
- Milestone column maps tasks to the plan's M1–M4

## Path Conventions

Single Python package at the repository root: `biweeklybudget/`, with tests under
`biweeklybudget/tests/`. Paths below are repository-relative.

---

## Phase 1: Setup

Already complete in this worktree; recorded so the state is reproducible and so a fresh
session does not redo it.

- [x] T001 Build the venv at `venv/` (`python3.14 -m venv venv`; `pip install -e .`) plus the migration suite's test dependencies (alembic-verify 1.0.2, pytest, pytest-html, mock, freezegun, retrying, execnet, py, pytest-cache)
- [x] T002 Start MariaDB 10.4.7 in Docker (container `budgettest311`, port 13311) and create the test databases with `dev/setup_test_db.py`
- [x] T003 Capture the pre-change baseline by running the migrations suite unmodified — recorded in [research.md](./research.md) R9 as **8 passed in 123s**

## Phase 2: Foundational

Blocking prerequisites. Complete before any user-story phase.

- [x] T004 Establish empirically that `alembic.autogenerate.compare_metadata` reports zero differences against this schema, with and without `compare_server_default=True` — recorded in [research.md](./research.md) R4
- [x] T005 Establish empirically that it detects injected drift across all six categories tried — recorded in [research.md](./research.md) R5

---

## Phase 3 (M1): Replace the schema comparison — US1, US2

**Goal**: The migration suite verifies model/migration agreement using Alembic's own
autogenerate comparison, with no reference to `sqlalchemydiff`.

**Independent test**: `pytest -m migrations biweeklybudget/tests/migrations/test_alembic_verify.py`
passes, and fails when drift is injected.

- [x] T006 [US1] Rewrite the imports of `biweeklybudget/tests/migrations/test_alembic_verify.py`: remove `from sqlalchemydiff.comparer import Comparer`, `import json`, and `from sqlalchemy import create_engine`; add `from pprint import pformat`, `from alembic.autogenerate import compare_metadata` and `from alembic.migration import MigrationContext`; add `import biweeklybudget.models  # noqa` — importing `models.base` alone leaves `Base.metadata` empty, which was verified, so this import is load-bearing and must be commented as such
- [x] T007 [US1] Delete the local `prepare_schema_from_models()` helper from `biweeklybudget/tests/migrations/test_alembic_verify.py` — it existed only to materialise the models into the second database for a database-to-database diff
- [x] T008 [US1] Rewrite `test_model_and_migration_schemas_are_the_same` in `biweeklybudget/tests/migrations/test_alembic_verify.py` to open a connection on the migrated database, build `MigrationContext.configure(conn, opts={'compare_server_default': True})`, call `compare_metadata(context, Base.metadata)`, and assert the returned list is empty — rendering it with `pformat` in the assertion message, not `json.dumps`, since Alembic diff tuples contain live SQLAlchemy objects that will not serialise. Drop the sixteen check-constraint entries and the `alembic_version` entry from the old `ignores` list; neither is needed. Add a comment recording that Alembic autogenerate does not compare check constraints, and that the previous mechanism had every one of this schema's check constraints explicitly ignored, so nothing that was being verified stops being verified (FR-008)
- [x] T009 [US1] Prove the rebuilt comparison is not vacuous (FR-009, SC-004): temporarily add a column to a model with no matching migration, run `pytest -m migrations biweeklybudget/tests/migrations/test_alembic_verify.py`, and confirm it **fails** with `add_column` and the table and column names in the output. Revert the model change and confirm `git status` shows no model file modified
- [x] T010 [US1] [US2] Run the full migrations suite and confirm all 8 tests pass, matching the T003 baseline

**Checkpoint**: `sqlalchemydiff` is no longer imported anywhere. The suite still passes.

---

## Phase 4 (M2): Move to the supported fixtures — US3

**Goal**: The project uses only alembic-verify's non-deprecated interface, and the
migration-only fixtures live in the migration suite's own conftest.

**Independent test**: The migrations suite passes and emits no `alembicverify`
deprecation warning.

- [x] T011 [US3] Rewrite `biweeklybudget/tests/migrations/conftest.py`: replace the `alembic_config_left` / `alembic_config_right` fixtures with `alembic_root`, `alembic_db_uri` and `alembic_config`. `alembic_root` returns the absolute path to `biweeklybudget/alembic` from `TOXINIDIR`; `alembic_db_uri` resolves `MYSQL_DBNAME_LEFT` via `alembic_helpers.uri_for_db` and empties the database via `empty_db_by_uri`; `alembic_config` builds the Alembic `Config` with `alembicverify.util.make_alembic_config`. Update the docstrings to explain why this project supplies its own `alembic_config` rather than using the library's (the library resolves `script_location` relative to the working directory; this project's `alembic.ini` records a relative path)
- [x] T012 [US3] Remove the now-relocated `alembic_root`, `uri_left` and `uri_right` fixtures from `biweeklybudget/tests/conftest.py`. Before editing, confirm whether the module-level `from biweeklybudget.tests.migrations.alembic_helpers import uri_for_db, empty_db_by_uri` is still needed by anything else in that file, and remove it only if it is not — this conftest is loaded by the unit and acceptance suites, so a wrong edit here breaks far more than the migration suite
- [x] T013 [US3] Update `MigrationTest.test_migration_roundtrip` in `biweeklybudget/tests/migrations/migration_test_helpers.py` to take `(self, alembic_db_uri, alembic_config)` instead of `(self, uri_left, alembic_config_left)`, and update every use of those names in the method body
- [x] T014 [P] [US3] Re-verify by grep that none of the six `biweeklybudget/tests/migrations/test_migration_*.py` modules references a fixture by name, and change them only if that turns out to be wrong
- [x] T015 [US3] Run the migrations suite; confirm 8 passed and that no `alembicverify` DeprecationWarning appears in the warnings summary (SC-003)

**Checkpoint**: No deprecated alembic-verify surface is used, and no migration-only
fixture remains in the shared conftest.

---

## Phase 5 (M2): Delete the dead plumbing — US3, US4

**Goal**: `sqlalchemy-diff` is gone from every dependency declaration, and the second
test database it required is gone from tooling, CI and documentation.

**Independent test**: A freshly built tox environment contains no `sqlalchemy-diff`, and
a repository-wide grep finds it only in historical changelog entries.

- [x] T016 [US3] Remove the `sqlalchemy-diff==1.1.1` line from all four environments in `tox.ini` — `[testenv]`, `[testenv:acceptance]`, `[testenv:plaid]` and `[testenv:migrations]`. Leave `alembic-verify==1.0.2` in place in each; per [research.md](./research.md) R2 the exact pin is deliberate and 1.0.2 is the current latest
- [x] T017 [P] [US4] Remove `'MYSQL_DBNAME_RIGHT'` from the required-variable list in `dev/setup_test_db.py` so the script provisions two databases rather than three
- [x] T018 [P] [US4] Remove all six `MYSQL_DBNAME_RIGHT: alembicRight` entries from `.github/workflows/run-tox-suite.yml`
- [x] T019 [P] [US4] Remove the `MYSQL_DBNAME_RIGHT` export from the test-database setup instructions in `CLAUDE.md`

**Checkpoint**: Nothing installs or references `sqlalchemy-diff`; nothing sets up a
second database.

---

## Phase 6 (M3): Verify

**Goal**: Everything passes, from a clean environment, with the removed dependency
genuinely absent.

- [x] T020 Rebuild the virtualenv or explicitly `pip uninstall sqlalchemy-diff`, then run the migrations suite to completion and confirm 8 passed with the package absent. Redirect output to a file rather than piping through `tail`, per the project's testing convention
- [x] T021 [P] Run the repository-wide grep from [quickstart.md](./quickstart.md) §5 and confirm `sqlalchemy-diff` / `sqlalchemy_diff` / `sqlalchemydiff` appear only in `CHANGES.rst` history entries (SC-001)
- [x] T022 Run the unit suite (`tox -e py314`) to completion; all tests pass, and the run is pycodestyle- and pyflakes-clean under `pytest.ini`'s exceptions (Constitution II)
- [x] T023 Run the docs build (`tox -e docs`) to completion with no errors (Constitution IV)
- [x] T024 Run the acceptance suite (`tox -e acceptance`) to completion; all tests pass. A timeout is not a pass — raise the timeout and re-run rather than narrowing the selection (Constitution II). The known-flaky `TestDragLimitations::test_11_unreconcile` should be re-run in isolation before being attributed to this change

**Checkpoint**: The full Test Gate is green.

---

## Phase 7 (M4): Document and release — US4

- [x] T025 [US4] Update `docs/source/development.rst`: drop `MYSQL_DBNAME_RIGHT` from the setup export lines (~38, ~59–60) and from the environment-variable list (~154); drop the "requires *two* test databases" sentence; and rewrite the Database Migration Tests prose (~141) so it describes what the suite now does — drives the migrations with alembic-verify and compares the resulting schema against the models with Alembic's own autogenerate comparison. Describe `MYSQL_DBNAME_LEFT` as the database the migration suite builds, rather than as "the first (left)" of a pair
- [x] T026 [US4] Bump `biweeklybudget/version.py` from 1.12.0 and add the matching `CHANGES.rst` entry in the existing format, covering: `sqlalchemy-diff` removed entirely; the schema comparison rebuilt on `alembic.autogenerate.compare_metadata` with server-default comparison enabled and no exclusion list; the migration fixtures renamed to alembic-verify 1.x's supported names; and `MYSQL_DBNAME_RIGHT` no longer used. Note in the entry that check constraints are not compared by Alembic autogenerate, and that they were already excluded from the previous comparison
- [x] T027 [US4] Re-run `tox -e docs` after the documentation edits and confirm it still builds clean
- [x] T028 Record the final results in this file and in [spec.md](./spec.md) (status → Complete), then commit

---

## Dependencies

```text
Phase 1 (T001–T003)  ─┐
Phase 2 (T004–T005)  ─┴─> Phase 3 (T006–T010)  M1
                              │
                              v
                         Phase 4 (T011–T015)   M2  fixtures
                              │
                              v
                         Phase 5 (T016–T019)   M2  dead plumbing
                              │
                              v
                         Phase 6 (T020–T024)   M3  verify
                              │
                              v
                         Phase 7 (T025–T028)   M4  document and release
```

Within phases:

- T006 → T007 → T008 → T009 → T010 are strictly sequential; they edit one file and then
  test the result.
- T011 → T012 → T013 are sequential: the fixtures must exist under their new names in the
  migrations conftest before they are removed from the shared one, and both must be
  settled before the helper that consumes them is updated. T014 is independent [P].
- T017, T018 and T019 touch three separate files and are fully parallel [P]. T016 is
  listed first because it is the one that changes what gets installed.
- T021 is independent of the test runs and can go in parallel [P] with T020–T024.

**Story dependencies**: US1 and US2 are delivered together by Phase 3 — they are two
assertions in one file, and separating them would mean editing that file twice. US3
depends on Phase 3 only in that the `sqlalchemydiff` import must be gone before the
dependency can be dropped. US4 is independent of all of them and could be done at any
point after Phase 5.

## Parallel execution examples

Phase 5, after T016:

```text
T017 dev/setup_test_db.py
T018 .github/workflows/run-tox-suite.yml       # all three concurrently
T019 CLAUDE.md
```

Phase 6:

```text
T021 (grep)  concurrently with  T022 / T023 / T024 (the long suite runs)
```

## Implementation strategy

**MVP scope is Phase 3 alone.** After T010 the project no longer imports
`sqlalchemydiff` and the suite still passes — the substantive risk of the whole change
is retired at that point, and everything after it is renaming, deletion and prose.

**Order rationale**: the comparison is replaced *before* the dependency is dropped from
`tox.ini`, so that at no point is the suite expected to run against a dependency set that
does not match the code. Verification (Phase 6) is deliberately separated from the edits
so that a clean-environment run, with the removed package genuinely absent, is its own
gate rather than an assumption.

**Do not touch** `specs/*/quickstart.md` belonging to earlier features. Those record how
the environment looked when each of those features was built, and rewriting them would
falsify history.

---

## Results

All 28 tasks complete. Recorded 2026-09-09.

### Test Gate (Constitution II)

| Suite | Local | CI (PR #336) |
|-------|-------|--------------|
| `migrations` | 8 passed — re-run with `sqlalchemy-diff` uninstalled from the environment | pass |
| `py314` (unit) | 885 passed, 4 skipped | pass |
| `acceptance` | 793 passed, 24 skipped | pass |
| `docs` | build succeeded; `sphinx-apidoc` regenerated no changed files | pass |
| `docker` | not run locally | pass |
| `plaid` / `jsdoc` / `screenshots` / `coverage` / Snyk | not run locally | pass |

Every CI check on PR #336 passed. The `claude-review` job reported **"No issues found."**
No Copilot review was requested on the PR.

The known-flaky `TestDragLimitations::test_11_unreconcile` passed on the first run and
needed no isolated re-run.

### Success criteria

| ID | Outcome |
|----|---------|
| SC-001 | `sqlalchemy-diff` appears nowhere outside `CHANGES.rst` history and one explanatory comment in `test_alembic_verify.py`; absent from the installed package list |
| SC-002 | Migrations suite runs to completion, all passing |
| SC-003 | Zero `alembic-verify` deprecation warnings (one unrelated `datetime.utcnow()` warning from `biweeklybudget/utils.py` remains, pre-existing) |
| SC-004 | Injected `drift_check` column produced a failure naming `add_column`, `accounts` and `drift_check` |
| SC-005 | Unit and acceptance suites pass; docs build clean |
| SC-006 | Documented setup produces exactly the databases and variables the suite consumes |

### Baseline comparison

Before: 8 passed in 123s. After: 8 passed in 121s. Same test count, same result, one
fewer dependency and one fewer database.

### Judgement calls, surfaced in PR #336 for the maintainer

- `alembic-verify` keeps its exact pin at `1.0.2` (research R2)
- `MYSQL_DBNAME_LEFT` keeps its name (research R7)
