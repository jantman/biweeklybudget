# Quickstart: Validating Currency Value Input Normalization

How to run and verify this feature. Details of *what* the code does are in
[contracts/](./contracts/); this file is the run guide.

## Prerequisites

A MySQL/MariaDB instance is required for the unit and acceptance suites.

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

Acceptance tests additionally need Chrome and chromedriver on `PATH`.

Cleanup: `docker stop budgettest && docker rm budgettest`

## Running the suites

Always redirect test output to a file rather than piping to `tail`/`grep`, so the full
output stays available (per `CLAUDE.md`).

```bash
source venv/bin/activate

# Unit tests, pycodestyle and pyflakes. Covers the parser and the normalization hook.
tox -e py314 > /tmp/py314.txt 2>&1

# Browser tests. Covers every form in the FR-009 inventory.
tox -e acceptance > /tmp/acceptance.txt 2>&1

# Regression checks — this feature changes no models and no packaging,
# so these must pass exactly as before.
tox -e migrations > /tmp/migrations.txt 2>&1

# Documentation must build clean (constitution IV).
tox -e docs  > /tmp/docs.txt 2>&1
tox -e jsdoc > /tmp/jsdoc.txt 2>&1   # regenerates docs/source/jsdoc.custom.rst
```

Narrower runs while iterating:

```bash
pytest biweeklybudget/tests/unit/test_utils.py -k parse_currency
tox -e acceptance -- -k "TestTransModalCurrencyNormalization" > /tmp/one.txt 2>&1
```

A suite that times out has **not** passed. Raise both the `pytest.ini` timeout and the
invoking tool's timeout and re-run to completion — do not narrow the run (constitution II).

## Manual verification in a browser

```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

Then, at <http://127.0.0.1:5000/transactions> → **Add Transaction**:

| # | Do this | Expect | Covers |
|---|---------|--------|--------|
| 1 | Amount `1,234.56`, a description, an account, a budget → Save | Saved as `$1,234.56`. **No 500 page.** | Story 1, SC-001 |
| 2 | Amount `123` → Save | Saved as `$123.00`. No "Invalid float value" error. | Story 2, SC-002 |
| 3 | Amount `$1,234.56`, then ` 1 234.56 `, then `(1,234.56)` | `1234.56`, `1234.56`, `-1234.56` | Story 3 |
| 4 | Amount `abc` → Save | Red field-level error on Amount reading `Invalid amount: "abc"`. No 500. No row created. | Story 4, SC-004 |
| 5 | Amount `1.2.3` → Save | Same as #4. | Story 4 |
| 6 | Check **Budget Split?**, Amount `1,234.56`, one allocation `1,234.56` | No "sum of budget allocations" error; Save stays enabled; saves. | Story 5 |

Then spot-check the other forms — Fuel Log (`/fuel`, Total Cost `123`), BoM Item
(`/projects`, Unit Cost `1,000`), Budget transfer, Account credit limit, Credit payoff
settings — each with a comma-separated value.

## What "done" looks like

- `tox -e py314` and `tox -e acceptance` both run to completion with zero failures.
- `tox -e migrations`, `tox -e docs`, `tox -e jsdoc` unchanged and green.
- Every row of the manual table above behaves as stated.
- `grep -rn "currency_fields\|decimal_fields" biweeklybudget/flaskapp/views/` enumerates
  every server-side currency field (SC-005); `grep -rn "parseFloat" biweeklybudget/flaskapp/static/js/`
  returns nothing in `transactions_modal.js`.
- `version.py` is `1.7.0` with a matching `CHANGES.rst` entry.
