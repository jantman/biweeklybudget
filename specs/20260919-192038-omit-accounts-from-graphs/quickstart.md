# Quickstart: Verifying Omit-From-Graphs For Accounts

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-19

How to prove this feature works, end to end.

Unlike issue #356, the sample data does **not** contain a ready-made case: no
Account ships flagged, deliberately (see [research.md](./research.md) R5 — flagging
one would force edits to dozens of unrelated assertions). So every manual check
below starts by flagging an Account yourself, and the value of the check is the
*before/after* comparison.

## Prerequisites

Per `CLAUDE.md`. In a worktree there is no local venv — use the main checkout's
`tox`, and export `TOXINIDIR` and `BIWEEKLYBUDGET_LOG_FILE` when running a suite
outside tox.

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' mariadb:10.4.7
export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306 MYSQL_USER=root MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest MYSQL_DBNAME_LEFT=alembicLeft
```

## 1. The automated gate

```bash
source venv/bin/activate
tox -e py314      > "$SCRATCH/unit.txt"       2>&1
tox -e acceptance > "$SCRATCH/acceptance.txt" 2>&1
tox -e migrations > "$SCRATCH/migrations.txt" 2>&1
tox -e docs       > "$SCRATCH/docs.txt"       2>&1
```

Redirect to a file rather than piping to `tail`/`grep` (CLAUDE.md), so the whole
run can be read. All must pass in full — a narrowed or timed-out run is not a pass
(Constitution II).

Targeted runs while iterating:

```bash
tox -e acceptance -- -k "TestAcctBalanceChart"
tox -e acceptance -- -k "test_accounts"
```

Known-flaky tests unrelated to this change (reconcile drag/unignore, fuel log
search, Plaid "Uncheck All") should be re-run in isolation before being blamed on
it.

## 2. The migration, both ways (User Story 4, SC-004)

The important half is the **upgrade**, because every pre-existing row gets `NULL`:

```bash
alembic -c biweeklybudget/alembic/alembic.ini current   # note the revision
alembic -c biweeklybudget/alembic/alembic.ini upgrade head
```

```sql
SELECT id, name, omit_from_graphs FROM accounts;
```

**Expect**: the column exists and every row is `NULL`. Now, *without setting
anything*:

```bash
curl -s "$BASE_URL/ajax/chart-data/account-balances" | python -m json.tool
```

**Expect**: `keys` is exactly what it was before the migration —
`["BankOne", "BankTwoStale", "CreditOne", "CreditTwo", "InvestmentOne"]`.

> This is the check that catches the one real trap in this feature. If the filter
> was written `== False` instead of `isnot(True)`, `keys` comes back **empty** here
> and every user's chart goes blank on upgrade. See [research.md](./research.md) R3.

Then reverse:

```bash
alembic -c biweeklybudget/alembic/alembic.ini downgrade -1
```

**Expect**: succeeds; the column is gone; all other Account data intact.

## 3. Setting the flag from the modal (User Story 2)

Open `/accounts`, click **InvestmentOne**.

**Expect**: an **Omit from graphs?** checkbox below **Active?**, unticked, with
wording identical to the Budget modal's.

Tick it, save, reopen the modal.

**Expect**: still ticked. `GET /ajax/account/5` reports
`"omit_from_graphs": true`.

Click **Add Account** from any panel heading.

**Expect**: the checkbox is present and unticked.

## 4. The chart (User Story 1, SC-001)

Capture before and after, and diff them — the diff is the assertion:

```bash
curl -s "$BASE_URL/ajax/chart-data/account-balances?days=0" > "$SCRATCH/before.json"
# tick "Omit from graphs?" on InvestmentOne and save
curl -s "$BASE_URL/ajax/chart-data/account-balances?days=0" > "$SCRATCH/after.json"
diff <(python -m json.tool "$SCRATCH/before.json") \
     <(python -m json.tool "$SCRATCH/after.json")
```

**Expect** the two files differ *only* by the removal of `"InvestmentOne"` from
`keys` and of its member from each `data` row. Specifically:

- the list of `date` values is identical (contract C-3 — flagging an account must
  not punch holes in the horizontal axis);
- every other account's value on every date is identical (C-2);
- the response still has exactly the keys `data` and `keys` (C-1).

Repeat for `?days=15`, `?days=365` and no parameter: absent from every window.

On the dashboard, the Account Balances chart now has one fewer line and one fewer
legend entry, and the vertical axis has rescaled to the remaining accounts — which
is the whole point of the feature.

Untick the flag and reload.

**Expect**: the line is back in full, including any history recorded while it was
flagged (FR-012).

## 5. Nothing else moved (User Story 3, SC-003)

With `InvestmentOne` still flagged, confirm it is unchanged on:

- `/accounts` — listed as normal, balance, unreconciled and difference all shown,
  no greying, no new column;
- `/cash-position`, `/` and any pay period page — every total that includes it is
  the same as with the flag cleared;
- every Account picker: Add Transaction, Account Transfer, Budget Transfer, Add
  Scheduled Transaction, Add Fuel Fill — it is still offered (it is active);
- the stale-data warning, if the account is stale, still appears.

The sharpest form of this check is to clear the flag and reload each page: only the
index chart should differ.

## 6. Edge cases worth poking

| Case | Do this | Expect |
|---|---|---|
| Every account flagged | Flag all of them | `{"data": [], "keys": []}`, status 200 — not an error |
| Inactive **and** flagged | Flag `DisabledBank` (already inactive) | Excluded once, no error, no duplicate handling |
| Date anchored only by a flagged account | Flag the account owning a date's sole balance record | That date is still returned, carrying the others' forward-filled values |
| Unknown caller | `curl` the endpoint with no knowledge of the flag | Same document, fewer series — no breakage |

## 7. Documentation

```bash
tox -e docs > "$SCRATCH/docs.txt" 2>&1
```

**Expect**: builds clean, including linkcheck. Confirm the rendered output
describes the new setting under **Account Balances Chart**, that
`POST /forms/account` lists `omit_from_graphs`, and that the chart `keys`
description no longer claims to include inactive accounts.

Regenerate the two screenshots that show the Edit Account modal and commit them:

```bash
tox -e screenshots   # never in the same run as -e docs; docs deletes the PNGs
git status --short docs/source/*.png
```

**Expect**: `account1.png`/`account1_sm.png` and
`account1-plaid.png`/`account1-plaid_sm.png` changed — and nothing else. In
particular the index-page screenshot must be unchanged, because no sample Account
is flagged.
