# Quickstart: Validating The Balance-less Account Fix

**Feature**: `specs/20260917-075406-balanceless-account-pages`
**Date**: 2026-09-17

Two ways to see this working: a direct reproduction that takes about a minute and proves
the defect and the fix, and the acceptance tests that gate the change.

## Prerequisites

A throwaway MariaDB and the test settings, per `CLAUDE.md`:

```bash
docker run -d --name budgettest334 -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' mariadb:10.4.7

export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306 MYSQL_USER=root MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest MYSQL_DBNAME_LEFT=alembicLeft

source venv/bin/activate      # in a worktree, the main checkout's venv
python dev/setup_test_db.py
```

The container holds only disposable test data and is deleted at the end
(`docker rm -f budgettest334`). It must never be pointed at a real database.

## Direct reproduction

Load sample data, add an active account with no balance for each displayed type, and
request both pages through the Flask test client:

```python
# drop/create all tables, SampleDataLoader().load(), init_db()
for name, typ in [('BankNoBal', AcctType.Bank),
                  ('CreditNoBal', AcctType.Credit),
                  ('InvestNoBal', AcctType.Investment)]:
    db_session.add(Account(description=name, name=name, acct_type=typ,
                           is_active=True))
db_session.flush(); db_session.commit()

c = app.test_client()
print(c.get('/').status_code, c.get('/accounts').status_code)
```

Expected:

| | Before the fix | After the fix |
|---|---|---|
| `/` | **500** — `UndefinedError: 'None' has no attribute 'ledger'` at `index.html:147` | 200 |
| `/accounts` | 200 | 200 |

Repeat with `acct.set_balance(ledger=None, avail=None)` instead of no balance row at all
(research R5); the result must be identical in both columns.

## What the page should look like

Open `/` in a browser with such an account present. The new account has a row in its
table, carrying its name and link, with every balance-derived cell **empty** — not `$0.00`,
and with no bare `()` beside the empty balance. Every other account's figures are exactly
as before. The full statement of this is
[`contracts/index-page-tables.md`](./contracts/index-page-tables.md).

## Acceptance tests

The new class, which must fail before the template is fixed and pass after:

```bash
tox -e acceptance -- -k "TestIndexMissingData" 2>&1 > /path/to/scratchpad/new-class.txt
```

The classes that prove nothing else moved:

```bash
tox -e acceptance -- -k "TestIndexAccounts or TestAccountsMainPage or TestAccountsMissingData" \
  2>&1 > /path/to/scratchpad/regression.txt
```

Redirect to a file rather than piping to `tail`, per `CLAUDE.md`, so the whole output stays
readable.

## The gate

Per Constitution Principle II, the feature is not done until the complete unit and
acceptance suites have run to completion and passed — a narrowed run is not the gate, and a
timed-out run has not passed:

```bash
tox -e py314 2>&1 > /path/to/scratchpad/unit.txt
tox -e acceptance 2>&1 > /path/to/scratchpad/acceptance.txt
tox -e docs 2>&1 > /path/to/scratchpad/docs.txt
```

No migration is created by this change, so the `migrations` environment has nothing new to
verify; CI runs it regardless.

## Cleanup

```bash
docker rm -f budgettest334
```
