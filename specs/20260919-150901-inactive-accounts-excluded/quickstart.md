# Quickstart: Verifying Inactive Accounts Are Excluded

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-19

How to prove this feature works, end to end. The sample data already contains what is
needed: `DisabledBank` (account id 6) is inactive and has a recorded balance, so it is
both a dropdown case and a chart case.

## Prerequisites

Per `CLAUDE.md`. In a worktree, use the main checkout's venv for `tox` (there is no venv
here), and export `TOXINIDIR` and `BIWEEKLYBUDGET_LOG_FILE` when running a suite outside
tox.

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' mariadb:10.4.7
export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
```

## 1. The automated gate

```bash
source venv/bin/activate
tox -e py314      > /path/to/scratchpad/unit.txt      2>&1
tox -e acceptance > /path/to/scratchpad/acceptance.txt 2>&1
```

Redirect to a file rather than piping to `tail` (CLAUDE.md), so the whole run can be read.
Both must pass in full — a narrowed or timed-out run is not a pass (Constitution II).

Targeted runs while iterating:

```bash
tox -e py314 -- -k "active_accounts"
tox -e acceptance -- -k "TestAcctBalanceChartData or InactiveAccount"
```

Known-flaky tests unrelated to this change (reconcile drag/unignore, fuel log search,
Plaid "Uncheck All") should be re-run in isolation before being blamed on it.

## 2. The chart (User Story 1)

```bash
curl -s "$BASE_URL/ajax/chart-data/account-balances" | python -m json.tool | head -20
```

**Expect**: `keys` is `["BankOne", "BankTwoStale", "CreditOne", "CreditTwo",
"InvestmentOne"]` — no `DisabledBank`, in `keys` or in any `data` row.

**Expect unchanged**: the date list, and every remaining account's values. The strongest
check is a before/after diff — capture the response, deactivate an account through the
Edit Account modal, capture again, and confirm the two differ only by that account's key
in `keys` and in each row (contract C-4, C-5).

On the dashboard itself, the Account Balances chart shows one fewer line and one fewer
legend entry, and nothing else moves.

## 3. The pickers (User Story 2)

Open each and read its Account select. **Expect**: `DisabledBank` absent; every active
account present.

| Where | How to open |
|---|---|
| Account Transfer, From and To | `/` → "Account Transfer"; and `/accounts` → same |
| Add Transaction | `/transactions` → "Add Transaction" |
| Budget Transfer | `/budgets` → "Budget Transfer"; and a `/payperiod/<date>` page |
| Add Scheduled Transaction | `/scheduled` → "Add Scheduled Transaction" |
| Add Fuel Fill | `/fuel` → "Log Fuel Fill" |

## 4. An existing record keeps its account (User Story 3) — the one that matters

This is the case that makes the fix safe rather than harmful.

1. On `/transactions`, add a transaction against an **active** account, e.g. `BankOne`.
2. On `/accounts`, open that account and uncheck **Active?**. Save.
3. Reopen the transaction from `/transactions`.

**Expect**: the Account select shows that now-inactive account, selected. **Expect**: the
select's other options are the remaining active accounts only — the inactive one was
re-added for this record, not restored to the list (FR-012).

4. Save with no other edit, then check the database:

```sql
SELECT id, account_id, description FROM transactions ORDER BY id DESC LIMIT 5;
```

**Expect**: `account_id` unchanged. A changed or null `account_id` here is the failure
this requirement exists to prevent.

Repeat for a ScheduledTransaction from `/scheduled`, and for the skip-scheduled flow on a
pay period page — whose Account field is *disabled* and still submitted, so it must show
the inactive account too.

## 5. What must still show inactive accounts (User Story 4)

- `/transactions` → the **Account filter** above the table still offers `DisabledBank`, and filtering by it still returns its rows.
- `/ofx` → the same filter, same expectation.
- `/accounts` → still lists `DisabledBank`, greyed, `Active? = NO` (issue #276).

A failure here means historical data has been made unreachable, which is worse than the
bug being fixed.

## 6. Documentation

```bash
tox -e docs   # must build clean
```

The dashboard `index` screenshot contains the Account Balances chart and loses the
`DisabledBank` line, so regenerate and commit it:

```bash
tox -e screenshots
git status --short docs/source/_static/
```

Never run `tox -e docs` in the same chained invocation as `screenshots` — it deletes the
generated PNGs. Commit only the screenshots this change actually altered.
