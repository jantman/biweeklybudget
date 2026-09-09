# Feature Specification: Remove the sqlalchemy-diff Dependency

**Feature Branch**: `robot-army/issue-311-un-pin-alembic-verify-and-remove`

**Created**: 2026-09-09

**Status**: Draft

**Input**: GitHub issue [#311](https://github.com/jantman/biweeklybudget/issues/311) — "Un-pin alembic-verify and remove sqlalchemy-diff dependency"

## Context

The `migrations` test suite exists to answer two questions about every change to the
database schema:

1. Can every Alembic migration be applied from an empty database, and then rolled
   back again, without error?
2. Does the schema produced by running all migrations match the schema described by
   the SQLAlchemy models?

Historically both answers came from a pair of third-party libraries: `alembic-verify`
(for driving the migrations) and `sqlalchemy-diff` (for the schema comparison).
`alembic-verify` began life inside the `sqlalchemy-diff` project, and the two were
coupled tightly enough that this project had to pin both to specific versions to get a
working combination.

`alembic-verify` 1.0 severed that relationship: it no longer depends on
`sqlalchemy-diff` at all, and it renamed its fixtures away from the "left database /
right database" vocabulary that only existed to serve the schema-comparison use case.
This project has already moved to `alembic-verify` 1.0.2, but it still carries
`sqlalchemy-diff` as a separate direct dependency purely to perform the comparison in
question 2, and it still drives `alembic-verify` through that library's *deprecated*
fixtures.

Carrying `sqlalchemy-diff` costs the project a second dependency that must be pinned,
audited, and kept compatible with the SQLAlchemy version the application actually uses,
for the sake of one assertion in one test. Continuing to use deprecated fixtures means
the suite emits deprecation warnings today and will break outright when those fixtures
are eventually removed.

## User Scenarios & Testing *(mandatory)*

The "users" of this feature are the project's maintainers and its CI system. The
feature delivers no user-visible application behaviour.

### User Story 1 - Migration/model drift is still caught (Priority: P1)

A maintainer changes a SQLAlchemy model and writes the accompanying Alembic migration.
They run the `migrations` test suite. If the migration they wrote does not produce
exactly the schema their model describes — a wrong column type, a missing index, a
nullable mismatch, a forgotten column — the suite fails and tells them what differs.

**Why this priority**: This is the entire reason the suite exists, and the project
constitution makes it a gate on every schema change. Any replacement that cannot catch
drift makes the whole change a regression, no matter how clean the dependency list is.

**Independent Test**: Deliberately introduce a discrepancy between a model and the
migration chain (for example, add a column to a model without a migration), run the
`migrations` suite, and confirm it fails with a message that names the differing
element. Revert the discrepancy and confirm the suite passes.

**Acceptance Scenarios**:

1. **Given** a model set and a migration chain that agree, **When** the schema
   comparison test runs, **Then** it passes.
2. **Given** a model with a column that no migration creates, **When** the schema
   comparison test runs, **Then** it fails and the failure message identifies the
   table and column that differ.
3. **Given** a migration that creates a column with a different type than its model
   declares, **When** the schema comparison test runs, **Then** it fails and the
   failure message identifies the mismatch.

---

### User Story 2 - Migrations still apply and roll back cleanly (Priority: P1)

A maintainer runs the `migrations` suite and learns whether the full migration chain
upgrades from empty to head and downgrades back to empty without error, and whether
each individual migration's `upgrade()`/`downgrade()` pair round-trips.

**Why this priority**: Equal in importance to Story 1 and covered by the same suite.
The constitution requires every migration to implement and be tested in both
directions.

**Independent Test**: Run the `migrations` suite against an empty test database and
confirm the upgrade/downgrade tests and every per-migration round-trip test pass.

**Acceptance Scenarios**:

1. **Given** an empty test database, **When** the upgrade/downgrade test runs,
   **Then** all migrations apply to head, the current revision equals the head
   revision, and all migrations then roll back to nothing.
2. **Given** the existing per-migration round-trip tests, **When** the suite runs,
   **Then** every one of them passes unchanged in intent.

---

### User Story 3 - The dependency is gone and the remaining one is current (Priority: P1)

A maintainer inspects the project's declared test dependencies. `sqlalchemy-diff`
appears nowhere. `alembic-verify` is present at the current released version, and the
project uses only its supported, non-deprecated interface.

**Why this priority**: This is the explicit ask of the issue, and it is what removes
the ongoing maintenance cost.

**Independent Test**: Search the repository for every form of the name
(`sqlalchemy-diff`, `sqlalchemy_diff`, `sqlalchemydiff`) and find no declaration or
import outside of historical changelog entries. Install the test environments from a
clean state and confirm `sqlalchemy-diff` is not present in the resulting package list.

**Acceptance Scenarios**:

1. **Given** a freshly built test environment, **When** its installed packages are
   listed, **Then** `sqlalchemy-diff` does not appear.
2. **Given** the test suite runs, **When** warnings are collected, **Then** no
   deprecation warning is raised by `alembic-verify` about the fixtures this project
   uses.

---

### User Story 4 - Setup instructions match what the suite needs (Priority: P2)

A maintainer following the documented development-environment setup ends up with
exactly the databases and environment variables the suite requires — no more, no less
— and CI is configured the same way.

**Why this priority**: Lower than the correctness stories because a stale extra
environment variable is harmless in the short term, but the constitution requires
documentation to be updated in the same change, and leaving instructions to create a
database nothing uses is exactly the kind of rot that wastes the next person's time.

**Independent Test**: Follow the documented setup from scratch in a clean environment
and run the `migrations` suite to completion; it passes with no undocumented
prerequisites and no documented-but-unused ones.

**Acceptance Scenarios**:

1. **Given** the documented setup steps, **When** a maintainer follows them exactly,
   **Then** the `migrations` suite runs to completion and passes.
2. **Given** the CI workflow configuration, **When** it is compared against what the
   suite actually consumes, **Then** every environment variable it sets for the
   migration suite is one the suite uses.

### Edge Cases

- **Schema elements the previous comparison could not compare reliably.** The existing
  comparison ignored sixteen named check constraints across five tables because they
  did not diff correctly, most likely due to creation order. The replacement must
  either compare those elements correctly or be explicit about what it does not
  compare; it must not silently narrow the comparison to less than the previous
  mechanism covered without that reduction being visible and deliberate.
- **The Alembic version table.** The migrations-built database contains Alembic's own
  bookkeeping table, which the model metadata knows nothing about. The comparison must
  not report this as drift.
- **Pre-migration SQL.** The first migration in this project's chain assumes some
  pre-existing state that the suite loads before migrating. The comparison must
  continue to account for whatever that leaves behind.
- **A comparison that reports no differences because it compared nothing.** A test that
  passes vacuously is worse than no test. The comparison must be demonstrated to fail
  on a real, deliberately introduced difference.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST NOT declare, install, or import `sqlalchemy-diff` in any
  form, in any test environment or requirements declaration.
- **FR-002**: The project MUST depend on the current released version of
  `alembic-verify` at the time of implementation, in every test environment that
  declares it.
- **FR-003**: The project MUST use only `alembic-verify`'s supported, non-deprecated
  public interface. It MUST NOT rely on fixtures or helpers that library documents as
  deprecated.
- **FR-004**: The `migrations` test suite MUST continue to verify that the full
  migration chain applies from an empty database to head and then rolls back to
  nothing.
- **FR-005**: The `migrations` test suite MUST continue to verify that the schema
  produced by the migration chain matches the schema defined by the SQLAlchemy models,
  and MUST fail with a message identifying what differs when it does not.
- **FR-006**: Every existing per-migration round-trip test MUST continue to run and
  pass, testing the same migration in the same direction pair as before.
- **FR-007**: Any test-environment configuration — environment variables, databases,
  fixtures, helper functions — that becomes unused as a result of this change MUST be
  removed from the test code, the developer setup tooling, the CI workflow, and the
  documentation, in this same change.
- **FR-008**: Anything the schema comparison deliberately does not compare MUST be
  recorded in the test code with a stated reason, so a future maintainer can tell an
  intentional exclusion from an oversight.
- **FR-009**: The schema comparison MUST be demonstrated to fail on a deliberately
  introduced model/migration discrepancy before the change is considered complete.
- **FR-010**: Documentation describing the migration test environment MUST match what
  the suite actually requires after the change. This covers `docs/source/development.rst`
  and `CLAUDE.md`.
- **FR-011**: The project version MUST be incremented and `CHANGES.rst` MUST gain a
  matching entry describing the dependency removal and the replacement of the schema
  comparison mechanism.

### Key Entities

- **Migration chain**: The ordered set of Alembic revisions under
  `biweeklybudget/alembic/versions/`. Applying all of them to an empty database
  produces the "as-migrated" schema.
- **Model metadata**: The schema described by the SQLAlchemy model classes under
  `biweeklybudget/models/`. This is the authoritative intent.
- **Schema comparison**: The act of establishing that the as-migrated schema and the
  model metadata describe the same database, and reporting what differs when they do
  not.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `sqlalchemy-diff` appears zero times in the repository outside of
  historical changelog entries, and zero times in the installed package list of any
  built test environment.
- **SC-002**: The `migrations` test suite runs to completion with every test passing.
- **SC-003**: The `migrations` test suite emits zero deprecation warnings originating
  from this project's use of `alembic-verify`.
- **SC-004**: When a model/migration discrepancy is deliberately introduced, the schema
  comparison test fails, and the failure output names the differing table and element.
- **SC-005**: The unit and acceptance suites run to completion with every test passing,
  and the `docs` environment builds without errors.
- **SC-006**: A maintainer following the documented development setup can run the
  `migrations` suite successfully with no step outside the documentation and no
  documented step that turns out to be unnecessary.

## Assumptions

- **The replacement comparison should avoid adding a new third-party dependency.**
  Swapping `sqlalchemy-diff` for a different external schema-diff library would satisfy
  the letter of the issue while leaving the project in the same position. The intent is
  fewer dependencies, so the comparison should be built from libraries the project
  already requires.
- **A second ("right") database may no longer be needed.** The `MYSQL_DBNAME_RIGHT`
  database exists solely so `sqlalchemy-diff` had a second live database to inspect. If
  the replacement compares the migrated database against the model metadata directly,
  that database and its environment variable become dead weight and fall under FR-007.
  If the chosen mechanism still needs it, it stays.
- **The exclusions carried by the old comparison were workarounds for that library, not
  statements about this project's schema.** The sixteen ignored check constraints were
  ignored because `sqlalchemy-diff` could not compare them reliably. A different
  mechanism is expected to need a different — and ideally shorter — exclusion list.
- **No application behaviour changes.** This work touches test infrastructure,
  development tooling, CI configuration, and documentation only. No file under
  `biweeklybudget/models/`, `biweeklybudget/flaskapp/`, or
  `biweeklybudget/alembic/versions/` changes as part of it.
- **MySQL/MariaDB remains the only supported engine**, so the comparison only needs to
  behave correctly against it.

## Out of Scope

- Changing, adding, or removing any Alembic migration.
- Changing any SQLAlchemy model.
- Upgrading SQLAlchemy, Alembic, or any dependency other than `alembic-verify`.
- Restructuring the migration test suite beyond what removing the dependency and
  moving to the supported `alembic-verify` interface requires.
