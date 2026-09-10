# Phase 0 Research: Remove the sqlalchemy-diff Dependency

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-09

All findings below were established empirically in this worktree against MariaDB
10.4.7 (the version CI uses), Python 3.14.7, SQLAlchemy 2.0.52, Alembic 1.19.2 and
alembic-verify 1.0.2. Nothing here is inferred from documentation alone.

## R1: What is the current released version of alembic-verify?

**Finding**: 1.0.2. `pip download --no-deps alembic-verify` resolves to
`alembic_verify-1.0.2-py3-none-any.whl`. The project already pins exactly this.

Its wheel metadata declares `pytest>=7.0`, `alembic>=1.8`, `sqlalchemy<3,>=1.4`, and
`sqlalchemy-utils>=0.40.0`. **`sqlalchemy-diff` is not among them.** The library's own
README states the 1.\* rewrite is "completely untied from the sqlalchemy-diff project".

**Consequence**: FR-002 is already satisfied by the current pin. The remaining work is
entirely on this project's side — `sqlalchemy-diff` survives as a *direct* dependency of
our own test code, not as a transitive dependency of alembic-verify.

## R2: Should the alembic-verify pin be removed outright?

**Decision**: No. Keep an exact pin, at the current latest version (`1.0.2`).

**Rationale**: The issue's title says "un-pin" but its body says "update alembic-verify
to the latest version", and every other test dependency in `tox.ini` carries an exact
pin (`selenium==4.48.0`, `pytest-flask==1.3.0`, `sphinx==9.1.0`, …). Removing this one
pin would make the migration suite the only environment whose dependency set can drift
between CI runs, which is at odds with how the rest of the file is maintained. Reading
"un-pin" as "stop being stuck on the old pin" satisfies the issue's intent while keeping
the file internally consistent.

**Flagged for the maintainer**: if the intent really was to drop the version constraint
entirely, that is a one-line change. It is called out in the pull request so the
decision is visible rather than silently made.

**Alternatives considered**: dropping the constraint (rejected: inconsistent with the
file, and reintroduces exactly the class of surprise breakage that led to the original
pin); using a compatible-release constraint such as `~=1.0` (rejected: same
inconsistency, and 1.\* is barely a month old with no track record to justify trusting
its patch stream unattended).

## R3: What replaces `sqlalchemydiff.comparer.Comparer`?

**Decision**: Alembic's own autogenerate comparison —
`alembic.autogenerate.compare_metadata(migration_context, Base.metadata)` against a
`MigrationContext` opened on the migrated database.

**Rationale**:

- **It adds no dependency.** Alembic is already a hard runtime requirement of the
  application (`requirements.txt` pins `alembic==1.19.2`), so the comparison costs
  nothing new. This is the point of the issue; swapping one third-party schema-diff
  library for another would satisfy its letter and miss its purpose.
- **It is the same machinery that generates migrations.** `alembic revision
  --autogenerate` is built on `compare_metadata`. Using it to *verify* migrations means
  the test asks precisely the question a maintainer cares about: "would autogenerate
  still want to write a migration here?" A non-empty diff list is, literally, the
  migration the maintainer forgot to write.
- **It removes the second database.** `compare_metadata` compares a live database
  against in-memory `MetaData`. The models no longer need to be materialised into a
  real schema, so the "right" database, its URI fixture, and the local
  `prepare_schema_from_models()` helper all become dead — FR-007.
- **It needs no exclusion list.** Measured, below.

**Alternatives considered**:

- *Keep sqlalchemy-diff.* Rejected — it is the thing the issue asks to remove.
- *Hand-rolled comparison over SQLAlchemy's `Inspector`.* Rejected — this is
  reimplementing `compare_metadata`, badly, and it would be this project's code to
  maintain and to get wrong.
- *`alembic check`.* This is the CLI wrapper around the same comparison. Rejected as the
  interface because it reports through process exit status and stdout rather than a
  structured diff list, which makes a useful assertion message harder to produce.

## R4: Does `compare_metadata` produce false positives against this schema?

**Finding: no. Zero.**

A prototype built the "left" database exactly as the suite does — empty the database,
load `premigration_db_state.sql`, run `alembic upgrade head` — and then ran
`compare_metadata` against `Base.metadata`:

| Options | Diffs reported |
|---------|----------------|
| Alembic defaults (`compare_type` on, `compare_server_default` off) | **0** |
| `compare_server_default=True` | **0** |

**Decision**: enable `compare_server_default=True`. It costs nothing here and it closes
a real gap — a migration that creates a column with the wrong server default would
otherwise pass.

Two things this settles that were open questions going in:

- **The Alembic version table is handled automatically.** Alembic's autogenerate
  excludes its own `alembic_version` table from comparison, so the explicit
  `'alembic_version'` ignore the old comparison needed is unnecessary.
- **The sixteen ignored check constraints are unnecessary.** The old comparison ignored
  `CONSTRAINT_1`…`CONSTRAINT_5` across `accounts`, `budgets`, `ofx_trans`,
  `reconcile_rules` and `scheduled_transactions` because sqlalchemy-diff could not diff
  them reliably, "likely due to creation order". `compare_metadata` does not compare
  check constraints at all, so it reports nothing about them and needs no ignore list.

  **This is the one respect in which the new comparison is narrower than the old one** —
  though only nominally, because the old one had those same constraints switched off.
  Nothing that was actually being checked stops being checked. Per FR-008 this is
  recorded as a comment in the test rather than left implicit.

## R5: Is the new comparison actually checking anything, or does it pass vacuously?

**Finding**: it detects every category of drift tried. Each row below was produced by
mutating `Base.metadata` in memory and re-running the comparison against the unmodified
migrated database:

| Injected drift | Detected | Reported as |
|----------------|----------|-------------|
| Column present in models, absent from migrations | yes | `add_column` naming the table and column |
| Column type changed (`VARCHAR(50)` → `Integer`) | yes | `modify_type` with both types |
| Column nullability changed | yes | `modify_nullable` with both values |
| Table present in migrations, absent from models | yes | `remove_table` naming the table |
| Index present in models, absent from migrations | yes | `add_index` naming the index |
| Foreign key present in migrations, absent from models | yes | `remove_fk` naming the constraint |

**Consequence**: FR-009's "demonstrated to fail on a deliberately introduced
discrepancy" is satisfiable, and the failure messages name the offending element, as
FR-005 and SC-004 require. Coverage extends beyond what the old comparison exercised —
tables, columns, types, nullability, server defaults, indexes and foreign keys.

## R6: How does this project move off alembic-verify's deprecated fixtures?

**Background**: alembic-verify 1.0 renamed its fixtures. `alembic_config_left`,
`alembic_config_right`, `new_db_left` and `new_db_right` still exist but emit
`DeprecationWarning`; the supported names are `alembic_db_uri`, `alembic_ini_location`,
`alembic_config` and `alembic_new_db`.

This project does not currently *consume* the deprecated fixtures so much as *shadow*
them: `biweeklybudget/tests/migrations/conftest.py` defines its own
`alembic_config_left` / `alembic_config_right` under the same names, because the
library's versions resolve `script_location` out of `alembic.ini` as a path relative to
the current working directory, and this project's `alembic.ini` records the relative
`script_location = biweeklybudget/alembic`.

**Decision**: keep providing the Alembic `Config` from this project's own fixture, but
under the supported name `alembic_config`, fed by a `alembic_db_uri` fixture; build it
with `alembicverify.util.make_alembic_config`, which is not deprecated and is what the
library's own fixtures use.

**Rationale**: the deprecated *names* disappear, which is what FR-003 is about, and the
suite keeps resolving the script location from an absolute path derived from
`TOXINIDIR` rather than from the working directory. Adopting the library's stock
`alembic_config` fixture instead would reintroduce exactly the cwd-relative fragility
the current conftest exists to avoid.

**`alembic_new_db` was considered and rejected.** It would create and drop a
uuid-named database per test, which would let both `MYSQL_DBNAME_*` variables disappear
entirely — attractive, but it provisions through `sqlalchemy_utils.create_database`,
whose default character set is `utf8`, not the `utf8mb4` this project's schema requires.
Working around that would mean writing a bespoke database fixture anyway, which is what
the existing `uri_for_db` / `empty_db_by_uri` helpers already are.

## R7: Should `MYSQL_DBNAME_LEFT` be renamed now that there is no "right"?

**Decision**: No. Keep the variable name.

**Rationale**: it remains in use, so FR-007 does not reach it. Renaming would touch the
same eight files again for a cosmetic gain, and — more to the point — it would silently
break every existing local development environment: a developer whose shell profile
still exports `MYSQL_DBNAME_LEFT` would get a `KeyError` at fixture setup rather than
anything that explains itself. The documentation is updated to describe it as the
database the migration suite builds, which removes the confusion at its source.

**Flagged for the maintainer** in the pull request, since it is a judgement call and the
opposite choice is defensible.

## R8: What is the blast radius in the test suite?

Established by inspection:

- `biweeklybudget/tests/conftest.py` defines `alembic_root`, `uri_left` and `uri_right`.
  This conftest is loaded by the unit and acceptance suites too, so changes here need
  care — but a grep confirms these three fixtures are consumed *only* by the migration
  tests, and the module's other uses of `uri_for_db` / `empty_db_by_uri` are independent
  of them.
- `biweeklybudget/tests/migrations/migration_test_helpers.py` — its
  `MigrationTest.test_migration_roundtrip` takes `uri_left` and `alembic_config_left` as
  parameters. This is the only consumer besides `test_alembic_verify.py`.
- The six `test_migration_*.py` modules subclass `MigrationTest` and **do not reference
  any fixture by name**, confirmed by grep. The rename does not reach them.

## R9: Baseline

The `migrations` suite was run before any change, against MariaDB 10.4.7 with the
current dependency set: **8 passed in 123s**. This is the bar the change has to hold.
