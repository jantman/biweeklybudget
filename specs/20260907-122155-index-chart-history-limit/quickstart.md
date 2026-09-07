# Quickstart / Validation Guide: Index Chart History Limiting

**Feature**: `specs/20260907-122155-index-chart-history-limit`

How to prove this feature works end to end. See [`contracts/http-api.md`](contracts/http-api.md)
for the endpoint contract and [`data-model.md`](data-model.md) for the invariants referenced
below.

## Prerequisites

```bash
cd /home/jantman/worktrees/biweeklybudget/issue-279
source venv/bin/activate

docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' \
  mariadb:10.4.7

export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306 MYSQL_USER=root MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest
export MYSQL_DBNAME_LEFT=alembicLeft MYSQL_DBNAME_RIGHT=alembicRight

python dev/setup_test_db.py
initdb
```

Teardown when finished: `docker stop budgettest && docker rm budgettest`

## Scenario 1 — Unit-level invariants (no database)

The sampling and parameter-parsing rules are the substance of the feature and are testable
in isolation.

```bash
pytest biweeklybudget/tests/unit/flaskapp/views/test_index.py -v
```

**Expected**: all pass, covering data-model invariants 1–5 (bound respected, small inputs
untouched, last point pinned, order preserved, empty input safe) and every `days`
resolution row in the contract's parameter table.

## Scenario 2 — The bound holds at scale (User Story 1, SC-002, SC-003)

This is the scenario the issue is about; the sample data is far too small to demonstrate it,
so the test seeds synthetic history.

```bash
pytest biweeklybudget/tests/acceptance/flaskapp/views/test_index.py -v -k Chart \
  2>&1 > /tmp/claude-1000/-home-jantman-worktrees-biweeklybudget-issue-279/108b0a90-4854-4f84-99ec-9427a905689b/scratchpad/chart-tests.txt
```

**Expected**: with several years of daily balances loaded,
`GET /ajax/chart-data/account-balances` returns at most `ACCOUNT_BALANCE_CHART_MAX_POINTS`
dates for `days=365` *and* for `days=0`, and doubling the seeded history leaves the default
view's point count unchanged.

## Scenario 3 — Manual end-to-end check in the browser

```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

Open <http://127.0.0.1:8080/> and confirm:

1. The **Account Balances** panel draws a chart, and the panel heading carries a range
   button group with **1y** marked active (the shipped default).
2. Hovering the rightmost point shows a balance matching the account tables lower on the
   same page — the sampling has not dropped the present (G4).
3. Clicking **All** redraws the chart over the full history without the page reloading, and
   `active` moves to **All**.
4. Clicking **1m** narrows it again.
5. An account that has had no balance recorded for a long time still shows a flat line at
   its last known value across the window, rather than disappearing or dropping to zero
   (G5). This is the correctness point most worth checking by eye.

## Scenario 4 — Configurability (User Story 3)

```bash
ACCOUNT_BALANCE_CHART_DEFAULT_DAYS=30 ACCOUNT_BALANCE_CHART_MAX_POINTS=20 flask rundev
```

**Expected**: the chart opens on a 30-day window with **1m** active, and no request returns
more than 20 dates. Both settings are in `_INT_VARS`, so the environment-variable override
path applies without editing a settings module.

Then unset both and restart: the chart returns to 365 days / 300 points with nothing
failing — the upgrade path for an installation whose settings module predates this feature.

## Scenario 5 — Backward compatibility of the endpoint

```bash
curl -s 'http://127.0.0.1:8080/ajax/chart-data/account-balances?days=0' | head -c 400
```

**Expected**: the same `{"data": [...], "keys": [...]}` shape as before this change. Any
external script consuming this endpoint keeps working; `days=0` reproduces the old
full-history view, subject to the point cap.

## Full gate before the feature is declared done

Constitution principle II — no narrowing to a passing subset, no timed-out run reported as
green.

```bash
tox -e py314 2>&1 > .../scratchpad/unit.txt
tox -e acceptance 2>&1 > .../scratchpad/acceptance.txt
tox -e migrations 2>&1 > .../scratchpad/migrations.txt   # must still pass; no schema change
tox -e docs 2>&1 > .../scratchpad/docs.txt
tox -e jsdoc 2>&1 > .../scratchpad/jsdoc.txt             # regenerates jsdoc.index.rst
```

All must complete and pass. `tox -e jsdoc` output is generated documentation and is
committed with the change.
