# Quickstart: Validating "Delete a Plaid Item"

**Feature**: [spec.md](./spec.md) | **Contracts**: [contracts/plaid-delete-item.md](./contracts/plaid-delete-item.md)

How to run this feature's gate and how to see it work by hand. Environment details that apply
to every feature in this repository are in `CLAUDE.md`; only what differs is repeated here.

## Prerequisites

A MariaDB test container and the two test databases:

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' mariadb:10.4.7

export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306 MYSQL_USER=root MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest MYSQL_DBNAME_LEFT=alembicLeft

python dev/setup_test_db.py
```

In a git worktree there is no local `venv`; use the main checkout's tox
(`/home/jantman/GIT/biweeklybudget/venv/bin/tox`). A freshly built acceptance environment also
needs `touch .tox/acceptance/liveserver.log` before its first run.

## The gate

```bash
tox -e py314        # unit + pycodestyle + pyflakes
tox -e acceptance   # Selenium; shares the test DB with py314, so run them in sequence
tox -e docs         # must build clean
```

`tox -e migrations` and `tox -e docker` are **not** required by this change on the schema
grounds the constitution names — there is no model change and no Alembic revision
(see [data-model.md](./data-model.md)). `docker` is still run because the change touches
packaged templates and static JS.

`tox -e plaid` needs real Plaid sandbox credentials (`PLAID_CLIENT_ID`, `PLAID_SECRET`,
`PLAID_ENV`, `PLAID_COUNTRY_CODES`). It is run by CI with the repository's secrets; without
credentials it cannot run locally and its absence is reported rather than papered over.

Known-flaky tests in this repository (reconcile drag/unignore, fuel-log search, Plaid
"Uncheck All", docs linkcheck) are re-run in isolation before any failure is blamed on this
change.

## Scenario 1 — The Delete affordance and the confirmation (US1, FR-001/003/004)

Against the acceptance fixture data, which has `PlaidItem1` (accounts `Acct1`, `Acct2`,
`Acct4`; two of them linked to Accounts) and `PlaidItem2` (account `Acct3`, linked to
`InvestmentOne`):

1. Load `/plaid-update`.
2. The **Plaid Items** table's last column is `Delete` for every row.
3. Click `Delete` on `PlaidItem2`'s row.
4. **Expect**: a modal naming Item `PlaidItem2` and institution `Inst2`, listing
   `InvestmentOne (<id>)` as the Account that will be unlinked, saying the Item will also be
   removed at Plaid, and saying the action cannot be undone. Its primary button reads `Delete`.
5. Dismiss it with `Close`.
6. **Expect**: no request was made (check the browser console / network panel), and the table
   is unchanged.

Covered by `tests/acceptance/flaskapp/views/test_plaid.py`.

## Scenario 2 — The endpoint's behaviour (US1/US2/US3/US4, FR-005 through FR-014)

Run the view's unit tests, which drive every branch of
[C1](./contracts/plaid-delete-item.md#c1--post-ajaxplaiddelete_item) and
[C2](./contracts/plaid-delete-item.md#c2--plaid-failure-classification) with `plaid_client`,
`db_session` and the models patched at module level:

```bash
tox -e py314 -- biweeklybudget/tests/unit/flaskapp/views/test_plaid.py
```

The assertions that matter most are the **exact ordered** `db_session.mock_calls` list — it is
what pins the mutation order (unlink → delete accounts → delete item → single commit) that the
whole safety argument rests on — and the assertion that on a non-recoverable `ApiException`
that list is empty.

## Scenario 3 — End to end against Plaid's sandbox (US2, FR-005/FR-008)

With Plaid sandbox credentials set:

```bash
tox -e plaid
```

`tests/acceptance/test_plaidlink.py` links a real sandbox Item, updates transactions against
it, and now deletes it at the end of the incremental run, then asserts the Plaid tables are
empty and the previously linked Accounts survive unlinked.

This class is `xfail`ed when `CI == 'true'` (Plaid's Link iframe does not work in headless
Chrome), so it is local-only signal. Its value is that it is the only place the real
`item_remove` call is exercised.

## Scenario 4 — By hand, against a real installation

Only if you want to watch it happen. Use a **separate** MariaDB container — an acceptance run
drops and reloads the test database — and set `PYTHONPATH` to the worktree so the app serves
the worktree's templates and JS rather than the installed copy:

```bash
PYTHONPATH=$(pwd) FLASK_APP=biweeklybudget.flaskapp.app:app \
  .tox/acceptance/bin/flask rundev
```

Then link a sandbox Item, link an Account to one of its Plaid Accounts, note that Account's
transactions and balance, delete the Item, and confirm:

- the Item and its Plaid Accounts are gone from `/plaid-update`;
- the Account still exists with the same transactions, balance and reconciliations;
- the Account's edit modal shows `none` for Plaid Account, and every remaining Item's accounts
  are still selectable for it;
- a transaction update for any remaining Item still succeeds.

## Documentation

```bash
tox -e jsdoc        # regenerates docs/source/jsdoc.plaid_prod.rst for the new JS functions
tox -e screenshots  # regenerates the Plaid Update PNGs, whose table gains a column
tox -e docs         # AFTER the above; never concurrently with screenshots
```

Two traps, both previously hit in this repository:

- `tox -e jsdoc` needs jsdoc **4.0.4** on `PATH`; the system 3.6.3 deletes every committed
  `docs/source/jsdoc.*.rst` and then fails, which breaks the `docs` build. Install it into a
  scratch prefix and prepend `node_modules/.bin`. Recover with
  `git checkout -- $(git ls-files -d docs/source/)`.
- `docs/source/screenshots.rst` is **generated** by `docs/make_screenshots.py`; edit the Plaid
  Update entry's `description` there, not the `.rst`. `make_screenshots.py` deletes every
  `docs/source/*.png` at start, so never run `docs` while it is running, and commit only the
  PNGs this change actually alters.
