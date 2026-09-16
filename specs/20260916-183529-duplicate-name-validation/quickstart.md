# Quickstart: Verifying Duplicate Name Validation

**Feature**: `specs/20260916-183529-duplicate-name-validation`

## Prerequisites

A MariaDB test database and the project virtualenv, per `CLAUDE.md`:

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' mariadb:10.4.7

export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306 MYSQL_USER=root MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest MYSQL_DBNAME_LEFT=alembicLeft

source venv/bin/activate
python dev/setup_test_db.py
initdb
```

## Run the application

```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

The fixture data used by the acceptance suite includes accounts `BankOne`,
`BankTwoStale`, `CreditOne`, `CreditTwo`, `InvestmentOne`, `DisabledBank`, and budgets
`Periodic1`, `Periodic2`, `Standing1`, `Standing2`, `Income`.

## Scenario 1 — duplicate account name on create (spec User Story 1)

1. Open `http://127.0.0.1:5000/accounts` and click **Add Account**.
2. Enter the name `BankOne`, pick any account type, and fill anything else you like.
3. Save.

**Expected**: a red message appears directly beneath the **Name** field saying the
name is already in use and naming the conflicting account; the Name field's group is
outlined in red. **No** `Server Error:` banner appears at the top of the modal, and
nothing in the message mentions a table, a column, a constraint, or `IntegrityError`.
The modal stays open with everything else you typed still in it.

4. Change the name to `BankThree` and save again.

**Expected**: the usual green success confirmation, and the account appears in the
bank accounts table after dismissing the modal.

## Scenario 2 — rename onto another account's name (spec User Story 2)

1. Click the existing `BankTwoStale` account to open its modal.
2. Change its name to `BankOne` and save.

**Expected**: the same field-level message. Neither account is changed.

3. Reopen `BankTwoStale`, leave the name alone, change its description, and save.

**Expected**: saves successfully — a record keeps its own name (FR-002).

## Scenario 3 — duplicate budget name (spec User Story 3)

Repeat scenarios 1 and 2 on `http://127.0.0.1:5000/budgets` with the budget
`Periodic1`, using **Add Budget** and then editing `Periodic2`.

## Scenario 4 — the endpoint directly

```bash
curl -s -X POST http://127.0.0.1:5000/forms/budget \
  -H 'Content-Type: application/json' \
  -d '{"name":"Periodic1","description":"x","is_periodic":true,
       "starting_balance":"100","current_balance":"","is_active":true,
       "is_income":false,"omit_from_graphs":false}' | python -m json.tool
```

**Expected**: `"success": false` with the message under `errors.name`, and every other
submitted field present as an empty array. See
[contracts/form-endpoints.md](./contracts/form-endpoints.md).

## Edge cases worth poking at

- `  BankOne  ` (leading/trailing spaces) — must be rejected, not silently trimmed into
  a duplicate.
- `bankone` (different case) — must be rejected; see [research.md](./research.md) R2
  for why this is correct even if the collation would permit it.
- An empty name — must give exactly one message, `Name cannot be empty`, with no
  duplicate-name message alongside it.

## Automated verification

```bash
source venv/bin/activate
tox -e py314                                   # unit suite
tox -e acceptance -- -k 'accounts or budgets'  # while iterating
tox -e acceptance                              # the full gate; must pass complete
tox -e docs
```

Per Constitution Principle II, the narrowed acceptance run is for iteration only — the
feature is not done until the complete suite runs to completion with everything
passing.

## Teardown

```bash
docker stop budgettest && docker rm budgettest
```
