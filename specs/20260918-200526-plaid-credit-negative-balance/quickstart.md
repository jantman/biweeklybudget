# Quickstart / Validation Guide

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-18

How to prove this feature works. Sign expectations are in
[contracts/plaid-balance-signs.md](./contracts/plaid-balance-signs.md); affected columns
are in [data-model.md](./data-model.md).

## Prerequisites

Per `CLAUDE.md`, tox is run from the main checkout's virtualenv (this is a worktree, which
has none of its own):

```bash
source /home/jantman/GIT/biweeklybudget/venv/bin/activate
cd /home/jantman/worktrees/biweeklybudget/issue-354
```

Redirect suite output to a file rather than piping it to `tail`/`head`, so the whole run
can be examined:

```bash
tox -e py314 > /path/to/scratchpad/unit.txt 2>&1
```

## 1. Targeted unit validation (fastest signal)

```bash
pytest biweeklybudget/tests/unit/test_plaid_updater.py -v
```

Expected: all pass, including the new sign cases. `TestDoItem`'s three tests are known to
fail when this file is run entirely alone (a backref is not yet configured); run the file
with the rest of the unit suite if they do.

The four sign cases that must be present and passing (FR-013):

| Case | Reported `balances.current` | Expected recorded ledger |
|---|---|---|
| Credit, amount owed | `1234.5678` | `Decimal('-1234.57')` |
| Credit, overpaid | `-50.00` | `Decimal('50.00')` |
| Credit, zero | `0` | `Decimal('0.00')`, and *not* `Decimal('-0.00')` |
| Depository | `1234.5678` | `Decimal('1234.57')` — unchanged |

Check the zero case tests the string form, not just numeric equality:
`Decimal('-0.00') == Decimal('0.00')` is `True` in Python, so an assertion on equality
alone would pass even if the bug were present. Assert on `str(...)` or on
`.is_signed()`.

## 2. Confirm nothing else moved

```bash
pytest biweeklybudget/tests/unit/test_cashposition.py \
       biweeklybudget/tests/unit/flaskapp/test_notifications.py -v
```

Expected: unchanged and passing. Neither module is modified by this feature — they already
implement the negative-means-owed convention. A failure here means the fix was put in the
wrong place.

## 3. Full test gate (Constitution Principle II — required before done)

```bash
tox -e py314      > .../unit.txt       2>&1   # full unit suite
tox -e acceptance > .../acceptance.txt 2>&1   # full acceptance suite
tox -e docs       > .../docs.txt       2>&1   # documentation build
```

All three must run to completion and pass. A suite that times out has not passed — raise
the timeout and re-run rather than narrowing the selection.

Known-flaky acceptance tests in this repository (missing-wait races, not caused by this
change): the reconcile drag/unignore tests — most often `test_36_ignore_and_unignore_ofx`
— the fuel log search tests, and the Plaid "Uncheck All" test `test_6_uncheck_all`. Re-run
a failure in isolation before attributing it to this change. The docs `linkcheck` step also
fails on transient link timeouts; re-run it.

`tox -e migrations` is **not** required: this feature makes no schema change and adds no
migration.

## 4. End-to-end check against a real Plaid credit account (optional, manual)

Only meaningful with real Plaid credentials and a linked credit card. Never point the
acceptance suite at a real database.

1. Note the Cash Position available-funds figure and the unallocated-funds banner.
2. Run a Plaid update for the item holding the credit card.
3. Confirm in the database that the new rows carry the negated sign:

   ```sql
   SELECT a.name, s.as_of, s.ledger_bal, s.avail_bal, a.credit_limit
   FROM ofx_statements s
     JOIN accounts a ON a.id = s.account_id
     JOIN plaid_accounts pa
       ON a.plaid_item_id = pa.item_id AND a.plaid_account_id = pa.account_id
   WHERE pa.account_type = 'credit'
   ORDER BY s.as_of DESC
   LIMIT 5;
   ```

   `ledger_bal` is negative for a card carrying a balance.
4. Reload Cash Position. Available funds are lower than before by the amount owed on the
   card — previously the same update moved them *up* by that amount, an error of twice the
   balance.
5. The unallocated-funds banner and the Cash Position bottom line still agree exactly; the
   acceptance suite asserts that identity, and it is unaffected by this change.

### Before upgrading: check your own institutions

The current, un-negated statements should satisfy `avail_bal ≈ credit_limit - ledger_bal`.
If they do across every card, the documented convention holds for all of your institutions
and the blanket negation is right:

```sql
SELECT a.name, s.as_of, a.credit_limit, s.ledger_bal, s.avail_bal,
       a.credit_limit - s.ledger_bal AS expected_avail
FROM ofx_statements s
  JOIN accounts a ON a.id = s.account_id
WHERE a.acct_type = 'Credit'
  AND a.credit_limit IS NOT NULL
  AND s.avail_bal IS NOT NULL
ORDER BY s.as_of DESC
LIMIT 20;
```

## 5. Historical data

Pre-upgrade rows keep the old sign and are **not** corrected automatically. The corrective
SQL, and the conditions for running it safely, live in the "Credit Card Accounts" section
of `docs/source/plaid.rst` added by this feature. Validate that section by reading it: it
must state the convention, say plainly that old rows are untouched and what that looks like
on the Account Balances chart, and warn that the SQL is run once — after upgrading, before
the next Plaid update — that running it twice undoes it, and how to scope it by date.

## 6. Documentation and changelog

```bash
tox -e docs > .../docs.txt 2>&1
```

Then confirm by eye:

* `docs/source/plaid.rst` has a "Credit Card Accounts" section, at the same heading level
  as "Loan Accounts", with a working `.. _plaid.credit_accounts:` label.
* `docs/source/app_usage.rst` cross-references it from the Cash Position sign discussion.
* `CHANGES.rst` has the entry under an `Unreleased` heading, and
  `biweeklybudget/version.py` is **unchanged**.
