# Quickstart / Validation Guide: Per-Account Transaction Totals Per Pay Period

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-07

How to run and verify this feature. See [contracts/account-sums.md](./contracts/account-sums.md)
for exactly what is guaranteed, and [data-model.md](./data-model.md) for the shape of the data.

## Prerequisites

A MariaDB test container and the environment described in `CLAUDE.md`:

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' \
  mariadb:10.4.7

export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306 MYSQL_USER=root MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest
export MYSQL_DBNAME_LEFT=alembicLeft MYSQL_DBNAME_RIGHT=alembicRight

source venv/bin/activate
python dev/setup_test_db.py
```

No `initdb` re-run and no migration are needed for this feature: it changes no schema.

## 1. Unit tests — the arithmetic

These need no database.

```bash
source venv/bin/activate
pytest biweeklybudget/tests/unit/test_biweeklypayperiod.py \
  > /tmp/claude-1000/scratchpad/unit-bwpp.txt 2>&1
```

Expected: all pass, including the new `TestAccountSums` and `TestMakeAccountSums`, and the
updated `TestData::test_initial` which now expects an `account_sums` key in `_data`.

Redirect to a file rather than piping to `tail`, per `CLAUDE.md`.

## 2. Acceptance tests — the rendered table

```bash
source venv/bin/activate
tox -e acceptance -- -k "TestCurrentPayPeriod or TestPayPeriodAccountTotals" \
  > /tmp/claude-1000/scratchpad/acc-payperiod.txt 2>&1
```

Expected: pass. The narrowed run is for iteration only — the full suite is what the
constitution's test gate requires, and is run in step 5.

**Warning**: acceptance tests drop and reload the database. Never point them at real data.

## 3. See it in a browser

```bash
source venv/bin/activate
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

Open <http://127.0.0.1:5000/payperiod/> (or a specific `/payperiod/YYYY-MM-DD`) and check, on
the "Per-Account Transaction Totals" panel:

1. **It is there**, below the four income/allocated/spent/remaining tiles and above the budget
   and transaction tables. (FR-001)
2. **Its columns match the "Remaining Balances" table** at the top of the page — same five
   dates, same order, same `(prev.)` / `(curr.)` / `(next)` suffixes, current period shaded.
   (FR-003, FR-008)
3. **Clicking a non-current date header** navigates to that pay period. (FR-009)
4. **Clicking an account name** opens that account. (FR-010)
5. **Every account listed in the Transactions table below appears as a row**, and no account
   without activity in any of the five periods does. (FR-002)
6. **Cells with no activity read `$0.00`**, not blank. (FR-006)
7. **Negative totals are red.** (FR-007)
8. **The bottom row is a Total row** whose current-period cell equals the sum of the column
   above it. (FR-011, SC-003)

## 4. Verify a cell by hand — the acceptance criterion that matters

This is SC-002, and the reason the implementation sums `transactions_list` rather than issuing
its own query.

1. Pick any account with a row in the table and note its current-period total.
2. In the Transactions table on the same page, add up the Amount of every row whose Account is
   that account — **including** any marked *(no budget impact)* and including rows shown as
   *(sched)*.
3. The two must be equal, to the cent.

Repeat for another period by clicking its column header: the cell you were reading becomes a
column of that period's page, and step 2 must again reproduce it.

Note that the per-account totals are **not** expected to equal the budget totals above them.
Budget arithmetic deliberately excludes credit card payments and no-budget-impact transactions;
account activity deliberately includes them.

## 5. Full verification, as the constitution's test gate requires

```bash
source venv/bin/activate
tox -e py314      > /tmp/claude-1000/scratchpad/tox-py314.txt 2>&1
tox -e acceptance > /tmp/claude-1000/scratchpad/tox-acceptance.txt 2>&1
tox -e docs       > /tmp/claude-1000/scratchpad/tox-docs.txt 2>&1
tox -e migrations > /tmp/claude-1000/scratchpad/tox-migrations.txt 2>&1
```

All four must run to completion and pass. A suite that times out has not passed: raise both the
pytest timeout and the invoking timeout and re-run it rather than narrowing the selection.

`migrations` is included not because this feature changes schema — it does not — but to show
that it did not disturb the environment. `docs` must build without errors, per Principle IV.

## Cleanup

```bash
docker stop budgettest && docker rm budgettest
```
