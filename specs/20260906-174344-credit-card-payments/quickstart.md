# Quickstart / Validation Guide: Special Handling of Credit Card Payments

**Feature**: `specs/20260906-174344-credit-card-payments/`
**Date**: 2026-09-06

How to stand the feature up and confirm it behaves as specified. Scenario numbering follows
the acceptance scenarios in [spec.md](./spec.md).

---

## Prerequisites

A MariaDB container for the test database, and the project virtualenv:

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

**Order matters for the migration.** Run `initdb` to bring the database to the current head
*before* the model is edited, or Alembic autogenerate sees no difference and silently
produces an empty migration:

```bash
initdb
```

Tear down when finished:

```bash
docker stop budgettest && docker rm budgettest
```

---

## Verifying the migration (M1)

```bash
alembic -c biweeklybudget/alembic/alembic.ini upgrade head
alembic -c biweeklybudget/alembic/alembic.ini current      # expect the new revision
alembic -c biweeklybudget/alembic/alembic.ini downgrade -1
alembic -c biweeklybudget/alembic/alembic.ini upgrade head
```

Both directions must complete without error. `downgrade()` drops the foreign key constraint
`fk_transactions_credit_payment_acct_id_accounts` before dropping the column; MySQL refuses
to drop a column a constraint still references.

Confirm head matches the models, which is what catches a migration whose column definitions
have drifted from the model's:

```bash
tox -e migrations
```

**Expected**: green, and `SC-006` holds — every pay period total, budget total, and account
unreconciled sum is identical before and after the upgrade, because every existing row has
`no_budget_impact = 0` and `credit_payment_acct_id = NULL`.

---

## Running the application

```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

---

## Scenario walkthroughs

### US1 — a transaction with no budget impact

1. Open a pay period page and note the "Spent" figure and a budget's remaining amount.
2. Add a transaction dated inside that period, against that budget, with **No Budget
   Impact?** checked.
3. Reload the pay period.

**Expected**: the transaction is listed in the pay period's transaction table, marked as
excluded, and every total on the page is unchanged (US1 scenario 1). The account's
unreconciled sum on `/accounts` is unchanged (scenario 2). The transaction appears in
`/reconcile` and can be reconciled normally (scenarios 3, 5).

4. Edit the transaction and clear the checkbox.

**Expected**: the period's totals rise by the transaction amount; re-checking it returns
them (scenario 4).

### US2 — a credit card payment, cross-period

1. Record charges totalling $500 on a credit account inside pay period N.
2. Record charges totalling $300 on the same account inside pay period N+1.
3. Record a $500 payment on a bank account, dated in N+1, with **Credit Card Payment For**
   set to that credit account.

**Expected**: period N+1 shows $300 of that card's charges and is not increased by the $500
payment; period N is unchanged at $500 (US2 scenario 1). This is `SC-001`.

4. Reopen the payment for editing.

**Expected**: the modal shows both the credit account and the derived no-budget-impact state
(scenario 4).

5. Clear the credit account selection and save.

**Expected**: the transaction resumes counting against its budget in N+1 (scenario 5) — and
does so only because the checkbox was never independently set, which is FR-014.

### US2 — a credit card payment, same period

Record a $200 charge on a credit account and a $200 payment toward it in the same pay
period.

**Expected**: the period counts the $200 charge exactly once (US2 scenario 2). This is
`SC-002`.

### US3 — attribution and warnings

With $400 of unpaid charges on a card in a closed period and $150 in the currently-open
period, open the Add Transaction modal, select that card under **Credit Card Payment For**,
and type each amount in turn:

| Amount entered | Expected panel |
|----------------|----------------|
| `400` | $400 attributed to the closed period, $0 to the open one, no warning |
| `500` | $400 to the closed period, $100 to the open one, no warning |
| `600` | $550 attributed, warning that the amount exceeds recorded unpaid charges by $50.00 |

The Save button stays enabled throughout (scenario 5, FR-021). With unpaid charges spanning
three closed periods, the panel lists each period's attributed amount oldest first
(scenario 4). Reopening a saved payment computes the panel without counting that payment
against itself (scenario 6, FR-019).

Selecting the credit account as *both* the transaction's account and the account being paid
produces the self-payment warning, and still saves (FR-022).

---

## Test suites

Redirect output to a file rather than piping to `tail`, so the full output stays available:

```bash
source venv/bin/activate
SCRATCH=/tmp/claude-1000/-home-jantman-worktrees-biweeklybudget-issue-210/*/scratchpad

tox -e py314      > "$SCRATCH/unit.txt" 2>&1
tox -e migrations > "$SCRATCH/migrations.txt" 2>&1
tox -e acceptance > "$SCRATCH/acceptance.txt" 2>&1
tox -e docs       > "$SCRATCH/docs.txt" 2>&1
```

All four must pass to completion. A suite that times out has not passed: raise the pytest
timeout and the invoking timeout and run it again. Narrowing the run to a passing subset,
or reporting a timed-out run as green, is not an acceptable outcome (constitution,
Principle II).

---

## What "done" looks like

- `SC-001` / `SC-002`: cross-period and same-period payoff each count a charge exactly once,
  pinned by unit tests with explicit expected numbers.
- `SC-003`: recording a payment takes one entry; no offsetting transaction is created
  anywhere in the flow.
- `SC-004` / `SC-005`: the over-payment warning and the per-period breakdown both appear
  before save.
- `SC-006` / `SC-007`: migration up leaves every existing total unchanged; migration down
  returns the schema to the previous release's shape.
- `SC-008`: unit, acceptance, migrations, and docs suites all green.
