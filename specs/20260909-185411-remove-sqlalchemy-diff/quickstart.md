# Quickstart / Validation Guide: Remove the sqlalchemy-diff Dependency

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

How to set up an environment for this feature and prove it works. Every command below
runs from the repository root.

## Prerequisites

- Python 3.14
- Docker, for the MariaDB test database

## 1. Test database

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot \
  --env MYSQL_ROOT_HOST='%' \
  mariadb:10.4.7
```

## 2. Environment

Note that **`MYSQL_DBNAME_RIGHT` is no longer set** — the second database is what this
feature removes. Setting it does no harm, but nothing reads it.

```bash
export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=13306
export MYSQL_USER=root
export MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest
export MYSQL_DBNAME_LEFT=alembicLeft
export TOXINIDIR="$(pwd)"
export BIWEEKLYBUDGET_LOG_FILE=/tmp/bwb-liveserver.log
```

`TOXINIDIR` and `BIWEEKLYBUDGET_LOG_FILE` are set by tox itself; they are only needed
when running pytest directly.

## 3. Virtualenv and databases

```bash
python3.14 -m venv venv
source venv/bin/activate
pip install -e .
python dev/setup_test_db.py
```

`setup_test_db.py` should now create **two** databases (`budgettest` and the one named by
`MYSQL_DBNAME_LEFT`), not three.

## 4. Run the migration suite

```bash
tox -e migrations
```

Expected: **8 passed**. Baseline before the change was 8 passed in ~123s; expect the same
count and no longer.

To run it directly instead of through tox (having also installed the migration suite's
test dependencies):

```bash
python -m pytest -rxs -vv -m migrations biweeklybudget/tests/migrations
```

Per the project's testing convention, redirect output to a file rather than piping it
through `tail`, so the whole run stays inspectable:

```bash
tox -e migrations > /tmp/migrations-output.txt 2>&1
```

## 5. Prove `sqlalchemy-diff` is gone (SC-001)

```bash
grep -rn "sqlalchemy-diff\|sqlalchemy_diff\|sqlalchemydiff" \
  --include="*.py" --include="*.ini" --include="*.txt" --include="*.yml" \
  --include="*.rst" --include="*.md" . | grep -v "^./venv/"
```

Expected: matches only in `CHANGES.rst`, which records history and must keep its old
entries intact.

And in a freshly built tox environment:

```bash
tox -e migrations 2>&1 | grep -i sqlalchemy-diff
```

Expected: no match in the `pip freeze` output the environment prints on startup.

## 6. Prove there are no alembic-verify deprecation warnings (SC-003)

```bash
python -m pytest -rxs -W error::DeprecationWarning -m migrations \
  biweeklybudget/tests/migrations > /tmp/migrations-deprecations.txt 2>&1
```

Expected: no failure attributable to an `alembicverify` fixture. (Other libraries in the
dependency tree emit their own deprecation warnings; the one that matters is that none
originate from this project's use of alembic-verify.)

## 7. Prove the comparison is not vacuous (SC-004, FR-009)

Temporarily introduce drift between the models and the migrations, and confirm the suite
catches it. For example, add a column to a model with no corresponding migration:

```bash
# in biweeklybudget/models/account.py, add to the Account class:
#     drift_check = Column(String(30))
python -m pytest -rxs -m migrations \
  biweeklybudget/tests/migrations/test_alembic_verify.py > /tmp/drift.txt 2>&1
```

Expected: `test_model_and_migration_schemas_are_the_same` **fails**, and the failure
output contains `add_column`, `accounts` and `drift_check`.

**Revert the drift afterwards** and confirm the suite returns to green. Verify with
`git status` that no model file is left modified.

## 8. Full test gate

Required by the constitution before the feature is complete:

```bash
tox -e py314      > /tmp/unit.txt       2>&1   # unit
tox -e migrations > /tmp/migrations.txt 2>&1
tox -e docs       > /tmp/docs.txt       2>&1
tox -e acceptance > /tmp/acceptance.txt 2>&1   # needs Chrome/chromedriver
```

All must run to completion and pass. A suite that times out has not passed — raise the
timeout and re-run rather than narrowing the selection.

## Cleanup

```bash
docker stop budgettest && docker rm budgettest
```
