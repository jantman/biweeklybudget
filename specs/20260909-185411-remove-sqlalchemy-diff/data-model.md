# Phase 1 Data Model: Remove the sqlalchemy-diff Dependency

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

This feature changes no database schema. It changes how two *descriptions* of the schema
are compared with each other, so the entities below are the test suite's own, not the
application's.

## Entities

### As-migrated schema

The live database schema produced by emptying the migration test database, loading
`biweeklybudget/tests/fixtures/premigration_db_state.sql`, and running every Alembic
revision under `biweeklybudget/alembic/versions/` up to head.

- **Materialised in**: the MySQL database named by `MYSQL_DBNAME_LEFT`.
- **Built by**: `alembicverify.util.prepare_schema_from_migrations`.
- **Carries**: Alembic's `alembic_version` bookkeeping table, which is not part of the
  models and is excluded from comparison automatically by Alembic.

### Model metadata

The schema described by the SQLAlchemy model classes under `biweeklybudget/models/`,
reachable as `biweeklybudget.models.base.Base.metadata` once `biweeklybudget.models` has
been imported so that every model class is registered.

- **Materialised in**: memory only. This is the change from the previous design, where
  it was materialised into the second (`MYSQL_DBNAME_RIGHT`) database via a local
  `prepare_schema_from_models()` helper so that a database-to-database diff could be
  taken. Both the helper and the database are removed.
- **Covers**: 18 tables — `account_balances`, `accounts`, `bom_items`,
  `budget_accounts`, `budget_transactions`, `budgets`, `fuellog`, `ofx_statements`,
  `ofx_trans`, `plaid_accounts`, `plaid_items`, `projects`, `reconcile_rules`,
  `scheduled_transactions`, `settings`, `transactions`, `txn_reconciles`, `vehicles`.

### Schema difference

The result of comparing the two above. Produced by
`alembic.autogenerate.compare_metadata(migration_context, metadata)` as a list; an empty
list means the two agree.

Each element is either a tuple or a list of tuples, whose first member names the kind of
difference. The kinds this schema can produce, all confirmed reachable in research R5:

| Kind | Meaning |
|------|---------|
| `add_table` / `remove_table` | A table exists on one side only |
| `add_column` / `remove_column` | A column exists on one side only |
| `modify_type` | Same column, different type |
| `modify_nullable` | Same column, different nullability |
| `modify_default` | Same column, different server default |
| `add_index` / `remove_index` | An index exists on one side only |
| `add_fk` / `remove_fk` | A foreign key constraint exists on one side only |

Tuple members include live SQLAlchemy `Type`, `Column`, `Table` and `Constraint`
objects, which are not JSON-serialisable. The failure message renders them with
`pprint`, not `json.dumps` as the previous implementation did.

## What is deliberately not compared

**Check constraints.** Alembic's autogenerate does not examine them, so no difference in
them will ever be reported. This is recorded as a comment in the test itself (FR-008).

It is not a reduction in what the suite actually verifies: the previous implementation
listed all sixteen of this schema's named check constraints —
`accounts.CONSTRAINT_1`–`4`, `budgets.CONSTRAINT_1`–`4`, `ofx_trans.CONSTRAINT_1`–`5`,
`reconcile_rules.CONSTRAINT_1`, `scheduled_transactions.CONSTRAINT_1` — in its `ignores`
argument, because they "don't diff correctly, likely due to creation order". They were
already switched off.

## Fixture relationships

```text
alembic_root ─────────┐
                      ├──> alembic_config  ──> (Alembic Config with absolute script_location)
alembic_db_uri ───────┘                          │
      │                                          │
      └──────────────────────────────────────────┴──> prepare_schema_from_migrations()
                                                            │
                                                            └──> as-migrated schema
```

`alembic_db_uri` resolves `MYSQL_DBNAME_LEFT` through
`biweeklybudget.tests.migrations.alembic_helpers.uri_for_db` and empties the database
before yielding, exactly as `uri_left` did.
