# Contract: Account Tables On The Index Page

**Feature**: `specs/20260917-075406-balanceless-account-pages`
**Surface**: `GET /`, rendered by `biweeklybudget/flaskapp/templates/index.html`
**Date**: 2026-09-17

This is a UI contract: what the three account tables on the landing page must render for
each state an account can be in. It is the thing the acceptance tests assert, and it is
what must not drift for accounts that already work.

## Scope of listing

Unchanged by this feature: the index page lists **active accounts only**, one table per
account type. An inactive account appears on `/accounts` and nowhere here.

## Bank accounts — `#panel-bank-accounts table#table-accounts-bank`

Columns: `Account | Balance | Unreconciled | Difference`

| Account state | Account | Balance | Unreconciled | Difference |
|---|---|---|---|---|
| Balance and statement present | name, linked to `/accounts/<id>` | `$12,789.01 (14 hours ago)` | the sum | ledger − unreconciled |
| No balance recorded | name, linked | *empty* | the sum | *empty* |
| Balance row with `NULL` ledger | name, linked | *empty* | the sum | *empty* |
| Balance present, no statement | name, linked | figure, **no parentheses** | the sum | ledger − unreconciled |

## Credit cards — `#panel-credit-cards table`

Columns: `Account | Balance | Available | Avail - Unrec`

| Account state | Account | Balance | Available | Avail - Unrec |
|---|---|---|---|---|
| Balance, limit and statement present | name, linked | `-$952.06 (13 hours ago)` | limit + ledger | limit + ledger − unreconciled |
| No balance recorded | name, linked | *empty* | *empty* | *empty* |
| Balance row with `NULL` ledger | name, linked | *empty* | *empty* | *empty* |
| Balance present, no credit limit | name, linked | figure | *empty* | *empty* |

## Investment accounts — `#panel-investment table#table-accounts-investment`

Columns: `Account | Value`

| Account state | Account | Value |
|---|---|---|
| Balance and statement present | name, linked | `$10,362.91 (13 days ago)` |
| No balance recorded | name, linked | *empty* |
| Balance row with `NULL` ledger | name, linked | *empty* |

## Rules that hold across all three tables

1. **The page renders.** No combination of missing balance, missing ledger figure, missing
   credit limit, or missing statement may produce anything other than HTTP 200.
2. **Every active account gets a row**, with its name and its link intact, whatever is
   missing from it.
3. **A figure that cannot be computed renders as an empty cell** — never `$0.00`, never a
   dash, never a placeholder. An empty cell means "not known"; `$0.00` means the balance is
   zero, and the two must stay distinguishable.
4. **The balance age is shown only when a statement exists.** No statement means no
   parentheses at all, not `()`.
5. **Staleness is only ever marked on an account that has a statement.** The red
   `data_age text-danger` treatment continues to apply exactly where it does today.
6. **Nothing changes for an account that has a balance.** Every cell of every row in the
   first line of each table above is byte-for-byte what it was before this change; the
   existing assertions in `TestIndexAccounts` are the check.

## Relationship to `/accounts`

`GET /accounts` renders the same three tables plus an `Active?` column and inactive rows,
and already satisfies the equivalent of every rule above (verified in research R3). This
contract deliberately states the same rules so that the two pages cannot drift apart; the
Accounts page's own contract is
`specs/20260917-053603-show-inactive-accounts/contracts/accounts-page.md`.
