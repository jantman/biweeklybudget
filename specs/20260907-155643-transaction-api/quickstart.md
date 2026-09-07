# Quickstart: validating Transaction API name-or-ID lookup and `addtrans`

How to prove this feature works end to end. Everything here is a command to run and an
outcome to check; the rules being checked live in
[contracts/transaction-create.md](./contracts/transaction-create.md) and
[contracts/addtrans-cli.md](./contracts/addtrans-cli.md), and the resolution rules in
[data-model.md](./data-model.md).

## Prerequisites

A test database container and the environment described in `CLAUDE.md`:

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

## 1. Automated suites

The authoritative check. Redirect output to the scratchpad rather than piping to
`tail`/`head`, per `CLAUDE.md`.

```bash
source venv/bin/activate

# Unit tests, including the resolution helper and the addtrans script
tox -e py314 > /tmp/unit.txt 2>&1

# Acceptance tests, which are where the endpoint's behaviour is pinned
tox -e acceptance > /tmp/acceptance.txt 2>&1

# setup.py gains a console script, so packaging is in scope
tox -e docker > /tmp/docker.txt 2>&1

# Documentation must build clean
tox -e docs > /tmp/docs.txt 2>&1
```

Narrower runs while iterating:

```bash
pytest biweeklybudget/tests/unit/models/test_utils.py
pytest biweeklybudget/tests/unit/test_addtrans.py
tox -e acceptance -- -k 'name_or_id' > /tmp/acc-subset.txt 2>&1
```

A narrowed run is for iterating only. Constitution II requires the complete suites to pass
before the feature is called done.

## 2. Manual end-to-end check

Start the app against the test database:

```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

In another shell (same environment), note an Account name and an active Budget name from
`http://127.0.0.1:8080/transactions`, then:

**The endpoint accepts names.** Expect `{"success": true, ..., "trans_id": N}`:

```bash
curl -s -X POST http://127.0.0.1:8080/forms/transaction \
  -H 'Content-Type: application/json' \
  -d '{"date":"2026-09-07","amount":"12.34","description":"quickstart by name",
       "account":"<ACCOUNT NAME>","notes":"","budgets":{"<BUDGET NAME>":"12.34"}}'
```

**An unknown name is refused.** Expect `success: false` and an error quoting the value,
and no new row in the transactions list:

```bash
curl -s -X POST http://127.0.0.1:8080/forms/transaction \
  -H 'Content-Type: application/json' \
  -d '{"date":"2026-09-07","amount":"12.34","description":"should fail",
       "account":"No Such Account","notes":"","budgets":{"<BUDGET NAME>":"12.34"}}'
```

**IDs still work.** Post the same transaction using numeric IDs; it must behave exactly as
it did before this change. The web UI's own Add Transaction modal is the other half of
this check — use it once and confirm nothing about it has changed.

**The script works.** Expect `Created Transaction N` and exit status 0:

```bash
addtrans '<ACCOUNT NAME>' 12.34 'quickstart via addtrans' -b '<BUDGET NAME>'
echo "exit=$?"
```

**The script reports failure properly.** Expect a per-field error line and exit status 1:

```bash
addtrans '<ACCOUNT NAME>' 12.34 'should fail' -b 'No Such Budget'
echo "exit=$?"
```

**The script fails cleanly with no server.** Stop the Flask app, then expect one readable
line naming the URL — no traceback — and exit status 1:

```bash
addtrans '<ACCOUNT NAME>' 12.34 'no server' -b '<BUDGET NAME>'
echo "exit=$?"
```

**`--dry-run` posts nothing.** Expect the JSON payload printed and exit 0.

## 3. Documentation check

- `docs/source/http_api.rst` describes name-or-ID for `account`, `budgets` keys and
  `credit_payment_acct`, states the digits-first rule and the `(income)` caveat, and shows
  a names-only `curl` example.
- `docs/source/getting_started.rst` lists `addtrans` among the command line entrypoints.
- `docs/source/biweeklybudget.addtrans.rst` exists and is in the `biweeklybudget.rst`
  toctree.
- `CHANGES.rst` has a 1.11.0 entry and `biweeklybudget/version.py` says `1.11.0`.

## Cleanup

```bash
docker stop budgettest && docker rm budgettest
```
