# Quickstart: Validating the Corrected Unallocated-Funds Notification

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/notification-content.md](./contracts/notification-content.md)

How to run and prove this feature works end to end. Details of *what* the banner
must say live in the contract; details of *where each number comes from* live in
[data-model.md](./data-model.md). This file is the run guide.

## Prerequisites

A MySQL/MariaDB instance is required — the unit suite does not run without one.
Per `CLAUDE.md`:

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot \
  --env MYSQL_ROOT_HOST='%' \
  mariadb:10.4.7

export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=13306
export MYSQL_USER=root
export MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest
export MYSQL_DBNAME_LEFT=alembicLeft
export MYSQL_DBNAME_RIGHT=alembicRight

source venv/bin/activate
python dev/setup_test_db.py
```

> **Test data safety** (Constitution): the acceptance suite drops and reloads the
> database. Point it only at this throwaway container, never at a real database.

Acceptance tests additionally need a Chrome driver.

## Running the suites

Redirect output to the scratchpad rather than piping to `tail`/`head`, so the full
output stays available:

```bash
source venv/bin/activate

# Unit
tox -e py314 > /tmp/.../unit.txt 2>&1

# Acceptance
tox -e acceptance > /tmp/.../acceptance.txt 2>&1

# Docs (principle IV) and migrations (principle III — must stay green with no
# migration added, proving no schema drift)
tox -e docs > /tmp/.../docs.txt 2>&1
tox -e migrations > /tmp/.../migrations.txt 2>&1
```

The feature is not done until the **complete** unit and acceptance suites pass.
A narrowed run is not a pass, and a timed-out run is not a pass — raise the
timeout and re-run.

While iterating, the directly relevant files are:

```bash
pytest biweeklybudget/tests/unit/flaskapp/test_notifications.py
pytest biweeklybudget/tests/acceptance/flaskapp/views/test_base_template.py
```

## Scenario 1 — Credit balances reduce funds available (User Story 1)

**Setup**: budget-funding accounts holding a known combined balance; at least one
active credit account with a known amount owed (stored negative).

**Check**: the figure the banner reports as available equals funding balance
*minus* the amount owed, and the surplus/shortfall verdict follows from that
reduced figure.

**Expected**: with $3,000 in funding accounts and $1,000 owed, the banner reports
$2,000 available. If committed funds are also $2,000, **no banner is shown at
all** — where before this change a $1,000 surplus was reported. That
disappearance is the headline outcome of the feature (SC-001).

**Sign check — do not skip**: give a credit account a *positive* balance
(overpaid card). Funds available must *increase*. An implementation using
`abs()` fails here while passing every other scenario, which is exactly why this
case is called out (see [research.md](./research.md) R1).

## Scenario 2 — Inactive and balance-less accounts (FR-002, FR-003)

**Check**: mark a credit account inactive; its balance must stop being
subtracted. Add an active credit account that has never had a balance recorded;
it must contribute zero and the banner must still render rather than erroring.

## Scenario 3 — The sentence names its quantities (User Story 2)

**Check**: read the rendered banner. The pay-period figure must be described as
*current pay period allocated but unspent* and must not contain the word
"remaining". The credit deduction must appear as its own linked term. There must
be five links, in the order given in the contract, each leading to a view that
reports the quantity it is attached to.

## Scenario 4 — No-cash-impact transactions do not move the banner (User Story 3)

**Setup**: in a funding account, add an unreconciled transaction marked *No
Budget Impact*, and an unreconciled transaction designated as a payment toward an
active credit account. Note the banner's unreconciled figure and verdict before
and after.

**Expected**: both figures are unchanged — neither transaction contributes
(FR-009) — **and** both transactions still appear in the reconcile view and
remain reconcilable (FR-010). The second half matters: excluding these from the
arithmetic must never hide them from reconciliation.

This scenario is regression coverage for behaviour already delivered by the
#210/#319 work. If it fails, the bug is in that code, not in this feature.

## Scenario 5 — No credit accounts at all (SC-005)

**Check**: with no credit accounts in the database, every figure in the banner is
identical to what it was before this change. Existing users without credit
accounts must see no difference.

## Manual check in the running app

```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

Open any page. The banner sits at the top of every view, so no particular route
is needed. Confirm the sentence matches the contract and that the parenthesised
breakdown visibly sums to the stated committed total.
