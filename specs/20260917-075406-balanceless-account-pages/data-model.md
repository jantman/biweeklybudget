# Data Model: Balance-less Accounts Must Not Break The Landing Pages

**Feature**: `specs/20260917-075406-balanceless-account-pages`
**Date**: 2026-09-17

## Schema changes

**None.** No file under `biweeklybudget/models/` is modified, so no Alembic migration is
created and Constitution Principle III is not engaged. This is a deliberate outcome of
research R4, not an oversight: the alternative shape for the fix — an `Account` property
that reports a substitute balance — was rejected precisely because it would change the
model's meaning for every caller.

## Existing entities the change reads

These are described only as far as the rendering depends on them.

### `Account` (`biweeklybudget/models/account.py`)

| Member | Kind | What the templates rely on |
|---|---|---|
| `name`, `id` | Columns | Row label and link. Always present. |
| `acct_type` | Column (`AcctType`) | Selects which of the three tables the row appears in. |
| `is_active` | Column | The index page lists only active accounts; the Accounts page lists all. Unchanged by this feature. |
| `credit_limit` | Column, **nullable** | Used with the ledger figure for the credit table's "Available" and "Avail - Unrec". Null for a newly created credit account. |
| `balance` | Read-only property | The newest `AccountBalance` for the account, **or `None`** when none has ever been recorded. The origin of the defect. |
| `ofx_statement` | Read-only property | The newest statement, **or `None`**. Dates the displayed balance and decides staleness. |
| `is_stale` | Hybrid property | Already returns `False` when `ofx_statement` is `None`; needs no change. |
| `unreconciled_sum` | Read-only property | Independent of the balance; returns a real zero for an account with no transactions, and keeps rendering `$0.00`. |

### `AccountBalance` (`biweeklybudget/models/account_balance.py`)

| Member | Kind | What the templates rely on |
|---|---|---|
| `ledger` | Column, **nullable** | The figure every affected cell is derived from. It can be `None` on a row that exists — the second failure route (research R5). |

## The states the rendering must handle

For a single account, as seen by the two pages:

| State | `acct.balance` | `acct.balance.ledger` | What must render |
|---|---|---|---|
| Normal | an `AccountBalance` | a number | Today's figures, unchanged |
| No balance ever recorded | `None` | — | Blank balance and blank derived cells |
| Balance row with no ledger figure | an `AccountBalance` | `None` | Identical to the row above |
| Credit account, balance but no limit | an `AccountBalance` | a number | Balance shown; the two limit-derived cells blank |
| No statement | — | — | No balance-age parentheses; not flagged stale |

The template expression `{% set ledger = acct.balance.ledger if acct.balance else None %}`
maps rows two and three onto one value, after which a single `ledger is not none` test
distinguishes "display the figure" from "leave the cell blank" everywhere.

## Invariant

No substitute value is ever written or displayed in place of a missing balance. "No balance
has ever been recorded" and "the balance is $0.00" stay distinguishable in the database and
on the screen, which is the reason the absent figure renders as an empty cell rather than
as a zero.
