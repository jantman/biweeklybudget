# Quickstart: Validating "Show Inactive Accounts"

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Contract**: [contracts/accounts-page.md](./contracts/accounts-page.md)

How to prove this feature works end to end, and how to run the gates Constitution
Principle II requires. This is a validation guide — implementation belongs in `tasks.md`.

## Prerequisites

A MariaDB test database, and tox run from the main checkout's venv (worktrees have no `venv/`
and the `tox` on `PATH` is broken):

```bash
export TOX=/home/jantman/GIT/biweeklybudget/venv/bin/tox
cd /home/jantman/worktrees/biweeklybudget/issue-276

docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' mariadb:10.4.7

export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306 MYSQL_USER=root MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest MYSQL_DBNAME_LEFT=alembicLeft
/home/jantman/GIT/biweeklybudget/venv/bin/python dev/setup_test_db.py
```

A newly built acceptance env has no log file, and every `testflask` test errors in setup
without it:

```bash
touch .tox/acceptance/liveserver.log   # after the env exists; harmless to repeat
```

## Automated validation

### The gates (Principle II — all must pass, run to completion)

```bash
$TOX -e py314      > /tmp/.../unit.txt       2>&1; echo "exit $?"
$TOX -e acceptance > /tmp/.../acceptance.txt 2>&1; echo "exit $?"
$TOX -e docs       > /tmp/.../docs.txt       2>&1; echo "exit $?"
```

Redirect to a scratchpad file rather than piping to `tail`, so the full output stays readable.
Check the log for `<env>: OK` / `<env>: FAIL` — a trailing `echo` masks tox's exit code when
the command is backgrounded. Run unit and acceptance **sequentially**; they share the test
database. Never run `docs` in the same invocation as `screenshots` — `docs` deletes the
generated PNGs.

`migrations` is **not** a gate here: nothing under `biweeklybudget/models/` changes, so there
is no migration (data-model.md). `docker` is left to CI; this host kills it for low memory.

### The feature's own tests

```bash
$TOX -e acceptance -- -k "TestInactiveAccounts or TestAccountsMainPage" \
  > /tmp/.../inactive.txt 2>&1
```

New coverage in `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py`, asserting
the contract:

| Covers | Assertion |
|---|---|
| FR-001, FR-008 | `DisabledBank` appears in the bank table, ordered by name after `BankTwoStale` |
| FR-002 | every row's first cell is `yes`, or `NO` for `DisabledBank` |
| FR-003 | `DisabledBank`'s `<tr>` has class `inactive`; active rows do not |
| FR-004 | `DisabledBank`'s name cell is `<a href="javascript:accountModal(6, null)">DisabledBank</a>` |
| FR-005 | opening that modal shows `Active?` unchecked; checking it and saving sets `is_active` true in the database |
| FR-007 | `DisabledBank`'s age span has class `data_age`, **not** `data_age text-danger` |
| User Story 1 | round trip: deactivate an active account → still listed, greyed → re-activate from its modal → listed as active, and `is_active` true in the database |

Tests updated for the deliberate change (research R7) — the `Active?` cell and the
`DisabledBank` row are the **only** movement expected in these lists; anything else is a
defect, not an assertion to update:

- `test_accounts.py` `test_bank_table`, `test_bank_stale_span`, `test_credit_table`,
  `test_investment_table`
- `test_accounts.py` `TestAccountTransfer` bank-table assertions (around lines 1060, 1167, 1312)

### Regression invariants — these must pass UNMODIFIED

If any of these needs editing, the change has leaked outside its scope (spec FR-009, SC-005):

```bash
$TOX -e acceptance -- -k "test_index or CashPosition or Payperiod or CreditPayoff" \
  > /tmp/.../regress.txt 2>&1
```

`test_index.py:91-143` is the sharpest one: the dashboard's panels use the **same element
IDs** as the Accounts page but are rendered from `index.html`. They must still list active
accounts only, with no `Active?` column.

## Manual validation

```bash
export PYTHONPATH=/home/jantman/worktrees/biweeklybudget/issue-276   # serve worktree code,
export FLASK_APP=biweeklybudget.flaskapp.app:app                     # not site-packages
.tox/acceptance/bin/flask rundev
```

Point it at a **separate** MariaDB container — acceptance runs drop and reload the test DB.

1. Open `/accounts`. `DisabledBank` is listed in Bank Accounts, greyed, first cell `NO` in red.
   Every other row reads `yes`.
2. Click `DisabledBank`. The modal opens, `Active?` unchecked. Check it, Save.
3. The page reloads; `DisabledBank` is no longer grey and reads `yes`.
4. Click an active account, uncheck `Active?`, Save. It stays listed, now grey and `NO` —
   this is the bug, fixed.
5. Open `/` — the dashboard still lists active accounts only, with no `Active?` column.

Ad-hoc browser automation note: this app's buttons are bound with jQuery `.on('click')`, and
synthetic coordinate clicks do not fire them. Drive them as the user's click does —
`$('#btn_add_acct_bank').click()`, `$('#modalSaveButton').click()`.

## Documentation and screenshots

```bash
$TOX -e screenshots > /tmp/.../shots.txt 2>&1     # never alongside docs
$TOX -e docs        > /tmp/.../docs.txt  2>&1     # after screenshots finishes
```

`docs/source/screenshots.rst` is **generated** — edit the `/accounts` caption in
`docs/make_screenshots.py`, not the `.rst`. A regeneration also rewrites unrelated PNGs and
adds sections for screenshots never committed, so commit **only** `accounts.png`,
`accounts_sm.png` and this feature's own caption; restore the rest with
`git checkout -- docs/source/*.png docs/source/screenshots.rst` and `git clean -n docs/source/`.
If a run is interrupted it leaves every PNG deleted: `git checkout -- docs/source/`.

## Done

- [ ] `py314`, `acceptance` and `docs` all run to completion and pass
- [ ] New `TestInactiveAccounts` coverage passes
- [ ] Regression invariants pass with **no** edits
- [ ] Manual round trip confirmed
- [ ] `app_usage.rst` section, `/accounts` caption, regenerated screenshots, `CHANGES.rst`
      bullet under `Unreleased`; `version.py` untouched
