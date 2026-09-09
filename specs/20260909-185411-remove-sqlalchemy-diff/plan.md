# Implementation Plan: Remove the sqlalchemy-diff Dependency

**Branch**: `robot-army/issue-311-un-pin-alembic-verify-and-remove` | **Date**: 2026-09-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260909-185411-remove-sqlalchemy-diff/spec.md`

## Summary

Drop `sqlalchemy-diff` from the project entirely and drive the migration test suite
through `alembic-verify`'s supported interface.

The schema-comparison assertion that was the dependency's only remaining purpose is
rebuilt on Alembic's own autogenerate comparison — `compare_metadata()` against a
`MigrationContext` opened on the migrated database, compared to `Base.metadata`.
Alembic is already a hard runtime dependency, so this removes a dependency without
adding one. Research measured the replacement at **zero false positives** against this
schema (with server-default comparison switched on, which the old mechanism did not do)
while detecting every category of injected model/migration drift, so the sixteen
check-constraint exclusions and the `alembic_version` exclusion the old comparison
carried are all dropped.

Because `compare_metadata` compares a live database against in-memory metadata, the
second ("right") database that existed solely to give `sqlalchemy-diff` something to
inspect becomes dead, and is removed along with its fixture, its CI configuration, its
setup-script provisioning and its documentation.

## Technical Context

**Language/Version**: Python 3.14 (3.14.7 in this worktree)

**Primary Dependencies**: Alembic 1.19.2, SQLAlchemy 2.0.52, alembic-verify 1.0.2,
pytest. `sqlalchemy-diff` 1.1.1 is removed.

**Storage**: MariaDB 10.4.7 (matching CI), `utf8mb4`. Two test databases today
(`MYSQL_DBNAME_LEFT`, `MYSQL_DBNAME_RIGHT`); one after this change.

**Testing**: pytest with the `migrations` marker; `tox -e migrations`. Unit, acceptance
and docs environments must also pass per the constitution's Test Gate.

**Target Platform**: Linux; developer workstation and GitHub Actions CI.

**Project Type**: Flask/SQLAlchemy web application. This change touches only its test
infrastructure, development tooling, CI configuration and documentation.

**Performance Goals**: No regression against the measured baseline of 8 tests in 123s.
Dropping the second database's schema build should if anything shorten the run.

**Constraints**: No application code, model or migration may change. MySQL/MariaDB is
the only engine that must be supported.

**Scale/Scope**: 18 model tables, 1 migration chain, 8 tests in the migrations suite;
roughly a dozen files touched across code, CI, tooling and docs.

## Constitution Check

*Constitution v1.0.0. Gate evaluated before Phase 0 and re-evaluated after Phase 1.*

| Principle | Assessment | Status |
|-----------|-----------|--------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Spec written and validated before planning; this plan precedes implementation; work stays on the feature branch `robot-army/issue-311-un-pin-alembic-verify-and-remove`. Decomposed into milestones below. | PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | The migrations suite is the *subject* of this change, so it must pass; unit, acceptance and docs suites must also pass to completion. A pre-change baseline (8 passed / 123s) was captured so a regression is distinguishable from a pre-existing failure. Timeouts are to be raised and re-run, never narrowed. All touched code stays pycodestyle/pyflakes clean. | PASS |
| **III. Schema Changes Ship With Reversible Migrations** | No model and no migration changes. The principle is not engaged — but its *enforcement mechanism* is exactly what this change rebuilds, so the bar is that the rebuilt mechanism must be at least as good at catching drift. Research R5 demonstrates it is stricter, not laxer. | PASS |
| **IV. Documentation Is Part Of The Change** | `docs/source/development.rst` and `CLAUDE.md` are updated in the same change; the `docs` environment must build clean. | PASS |
| **V. Escalate Instead Of Guessing** | Two judgement calls are made rather than guessed silently and are recorded in research with their reasoning, then surfaced in the pull request: keeping an exact version pin on `alembic-verify` (R2) and keeping the `MYSQL_DBNAME_LEFT` variable name (R7). | PASS |
| **VI. Versioned, Changelogged Releases** | Version bump plus a matching `CHANGES.rst` entry in milestone M4. No new Python files, so no new copyright headers are needed; edited files keep theirs. | PASS |
| **Tech constraints** | Python 3.14, MariaDB, no new dependency (one removed), no license question, no secrets, no change to the security posture, no financial-calculation code touched. Test data safety is unaffected — the migration suite still points only at the dedicated test database. | PASS |

**Result: no violations. The Complexity Tracking table is therefore omitted.**

Post-Phase-1 re-evaluation: the design adds no new project, module, abstraction layer or
dependency. It deletes a dependency, a database, a fixture and a helper function, and
replaces a ~25-line comparison with a shorter one. Constitution Check still PASS.

## Design

### The schema comparison

```
empty MYSQL_DBNAME_LEFT
  → load premigration_db_state.sql
  → alembic upgrade head            (via alembicverify.util.prepare_schema_from_migrations)
  → MigrationContext.configure(conn, opts={'compare_server_default': True})
  → compare_metadata(context, Base.metadata)
  → assert the diff list is empty, rendering it into the failure message if not
```

The assertion message must render the diff list readably — an Alembic diff is a tuple
or list of tuples whose members include SQLAlchemy type and constraint objects, so it is
formatted with `pprint`/`repr` rather than `json.dumps`, which cannot serialise them.

What is compared: tables, columns, column types, nullability, server defaults, indexes
and foreign keys. What is not: check constraints, which Alembic's autogenerate does not
examine — recorded as a comment in the test per FR-008. The previous mechanism had every
check constraint in the schema explicitly ignored, so nothing that was being verified
stops being verified.

### Fixture naming

| Today | After | Lives in |
|-------|-------|----------|
| `uri_left` | `alembic_db_uri` | moves to `tests/migrations/conftest.py` |
| `uri_right` | *removed* | — |
| `alembic_root` | `alembic_root` | moves to `tests/migrations/conftest.py` |
| `alembic_config_left` | `alembic_config` | `tests/migrations/conftest.py` |
| `alembic_config_right` | *removed* | — |

`alembic_db_uri` and `alembic_config` are alembic-verify 1.\*'s supported fixture names;
this project supplies its own implementations of them, built with the non-deprecated
`alembicverify.util.make_alembic_config`, so that the Alembic script location is
resolved from an absolute `TOXINIDIR`-derived path rather than relative to the working
directory (see research R6). Moving them out of the top-level `tests/conftest.py` into
the migrations conftest keeps migration-only fixtures out of the conftest that the unit
and acceptance suites load.

### Project Structure

Documentation for this feature:

```text
specs/20260909-185411-remove-sqlalchemy-diff/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2, written by /speckit-tasks
```

Repository files this change touches:

```text
tox.ini                                             # drop sqlalchemy-diff from 4 testenvs
biweeklybudget/
├── version.py                                      # version bump
└── tests/
    ├── conftest.py                                 # remove alembic_root/uri_left/uri_right
    └── migrations/
        ├── conftest.py                             # alembic_root, alembic_db_uri, alembic_config
        ├── test_alembic_verify.py                  # new comparison; no sqlalchemydiff
        └── migration_test_helpers.py               # fixture parameter rename
dev/setup_test_db.py                                # stop creating the right-hand database
.github/workflows/run-tox-suite.yml                 # drop 6 MYSQL_DBNAME_RIGHT entries
docs/source/development.rst                         # migration-test env docs
CLAUDE.md                                           # test DB setup instructions
CHANGES.rst                                         # changelog entry
```

No file under `biweeklybudget/models/`, `biweeklybudget/flaskapp/` or
`biweeklybudget/alembic/versions/` changes.

**Structure Decision**: the existing layout is kept unchanged. This is a subtractive
change within the established test tree; no new package, module or directory is created.

### Contracts

This feature exposes no external interface — no API, CLI surface, or user-facing
behaviour changes. The `contracts/` directory is therefore not created. The nearest
thing to a contract is the set of environment variables the migration suite consumes,
which is documented in `quickstart.md` and in `docs/source/development.rst`.

## Milestones

Human approval is required at each milestone boundary (Constitution I).

- **M1 — Replace the schema comparison.** Rewrite
  `test_alembic_verify.py`'s comparison on `compare_metadata`; delete the
  `sqlalchemydiff` import, the local `prepare_schema_from_models` helper and the
  exclusion list. Prove it fails on injected drift (FR-009), then prove it passes clean.
- **M2 — Move to the supported fixtures and delete the dead plumbing.** Rename the
  fixtures, relocate them into the migrations conftest, remove `uri_right` and every
  `MYSQL_DBNAME_RIGHT` reference across `dev/setup_test_db.py` and the CI workflow, and
  drop `sqlalchemy-diff` from all four `tox.ini` environments.
- **M3 — Verify.** Run the migrations suite from a clean environment built without
  `sqlalchemy-diff`, then the unit, acceptance and docs suites, all to completion.
- **M4 — Document and release.** Update `docs/source/development.rst` and `CLAUDE.md`,
  bump `version.py`, add the `CHANGES.rst` entry, record results in the spec artifacts.

## Risks

| Risk | Mitigation |
|------|-----------|
| `compare_metadata` behaves differently under CI's MariaDB than locally. | Local verification already runs MariaDB 10.4.7, the same image CI uses. CI is the final gate before merge. |
| The comparison passes vacuously and drift stops being caught. | FR-009 makes an injected-drift demonstration a required step, not an optional check (research R5 already ran six variants). |
| Removing fixtures from the top-level `tests/conftest.py` disturbs the unit or acceptance suites. | Research R8 confirmed by grep that the three fixtures have no consumer outside the migration tests; the Test Gate runs both suites regardless. |
| Check constraints stop being compared. | They were already excluded from comparison. Documented in the test and in the changelog so the narrowing is visible rather than silent. |
