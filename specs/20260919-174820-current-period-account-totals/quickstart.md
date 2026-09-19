# Quickstart: Validating Current-Period Per-Account Transaction Totals

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-19

How to run and prove this change. The contracts it validates against are in
[contracts/view-model.md](./contracts/view-model.md).

## Prerequisites

A MariaDB test container, and `tox` from the main checkout's virtualenv (worktrees have
no `venv/` of their own, and the `tox` on `PATH` is broken):

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot \
  --env MYSQL_ROOT_HOST='%' \
  mariadb:10.4.7

export TOX=/home/jantman/GIT/biweeklybudget/venv/bin/tox
export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306 MYSQL_USER=root MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest MYSQL_DBNAME_LEFT=alembicLeft

/home/jantman/GIT/biweeklybudget/venv/bin/python dev/setup_test_db.py
```

On a freshly built acceptance environment, create the log file tox expects before the
first run, or every `testflask` test errors in setup:

```bash
touch .tox/acceptance/liveserver.log
```

## Run the suites

Run from the worktree root. Unit and acceptance share the test database, so run them
sequentially; `docs` can run alongside either.

```bash
# Unit suite (also applies pycodestyle and pyflakes)
$TOX -e py314 > /tmp/.../py314.txt 2>&1; echo "rc=$?"

# Acceptance suite (Selenium; drops and reloads the test database)
$TOX -e acceptance > /tmp/.../acceptance.txt 2>&1; echo "rc=$?"

# Documentation build
$TOX -e docs > /tmp/.../docs.txt 2>&1; echo "rc=$?"

# Regression check only -- this feature changes no models and adds no migration
$TOX -e migrations > /tmp/.../migrations.txt 2>&1; echo "rc=$?"
```

Redirect to a scratchpad file rather than piping to `tail`, so the whole output stays
available. When a run is backgrounded, end the command with `rc=$?; ...; exit $rc` — a
trailing `echo` masks tox's exit code — or confirm `<env>: OK` in the log.

**Expected**: every suite passes, in full. A narrowed run is not a pass
(Constitution principle II).

### Just this feature's tests, while iterating

```bash
$TOX -e py314 -- biweeklybudget/tests/unit/flaskapp/views/test_payperiods.py
$TOX -e acceptance -- -k 'TestPayPeriodAccountTotals'
```

Useful during development; it does not substitute for the full runs above.

## Validate by hand

Serve the app against a *separate* database — acceptance runs drop and reload the test
one — and set `PYTHONPATH` so the worktree's templates win over the installed copy:

```bash
PYTHONPATH=$PWD FLASK_APP=biweeklybudget.flaskapp.app:app \
  .tox/acceptance/bin/flask rundev
```

Open `/payperiod/<YYYY-MM-DD>` and check the **Per-Account Transaction Totals** panel:

| # | Check | Expects | Traces to |
|---|-------|---------|-----------|
| 1 | Count the table's rows | Exactly two: one header, one of amounts | FR-002, SC-001 |
| 2 | Read the headers | One account name per column, then `Total` | FR-002, FR-007 |
| 3 | Look for dates or period links in the table | None anywhere | FR-009, SC-004 |
| 4 | Compare an account's amount against the Transactions table below | Equal to the sum of that account's rows, including any *(no budget impact)* and card-payment rows | FR-005 |
| 5 | Add the amounts across the row | Equals the `Total` cell | FR-007, SC-003 |
| 6 | Find an account with no activity this period | It has no column | FR-003 |
| 7 | Click an account name | Opens `/accounts/<id>` | FR-008 |
| 8 | Compare the `Total` with the period's *spent* figure above | They may disagree, deliberately | FR-005, FR-012 |
| 9 | View a *different* pay period | Amounts are that period's, not today's | FR-001 |
| 10 | Check the Remaining Balances table at the top | Still five periods, untouched | FR-013 |
| 11 | Narrow the browser window | The table scrolls horizontally inside its panel; the page does not widen | FR-011, edge case |

A pay period with no transactions at all (a far-future period works) should show the
`Total` column alone, over `$0.00` — FR-010, SC-005.

## Screenshot

The committed `payperiod.png` shows the old five-column table and becomes stale.
Regenerate with `$TOX -e screenshots`, then commit only `docs/source/payperiod.png` and
`docs/source/payperiod_sm.png` — a regeneration rewrites all 49+ PNGs even where nothing
changed, and only this feature's belong in this pull request.

Two cautions: **never run `docs` while `screenshots` is running** (the script deletes
every PNG up front, so a concurrent linkcheck reports them all broken), and captions are
edited in `docs/make_screenshots.py` — `docs/source/screenshots.rst` is generated from it,
and an edit made only to the `.rst` is discarded on the next regeneration. This change
edits the caption in both, because the `.rst` is committed.

If the run is killed for memory (this host has done so), restore with
`git checkout -- docs/source/` and leave the screenshot to a later regeneration rather
than committing a half-written set.

## Cleanup

```bash
docker stop budgettest && docker rm budgettest
```
