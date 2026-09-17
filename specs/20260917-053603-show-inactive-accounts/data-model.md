# Phase 1 Data Model: Show Inactive Accounts So They Can Be Re-Activated

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-17

## Summary

**No schema change. No Alembic migration.** Everything this feature needs is already stored.
Constitution Principle III does not engage, because nothing under `biweeklybudget/models/`
is modified.

This document records the fields the Accounts page reads, and the state transition the feature
makes reachable again.

## Entity: Account

`biweeklybudget/models/account.py`, table `accounts`. Unchanged by this feature. The fields the
Accounts page reads:

| Field / property | Type | Role on the Accounts page |
|------------------|------|---------------------------|
| `id` | Integer, PK | Target of the `accountModal(<id>, null)` link and of `/accounts/<id>` |
| `name` | String(50), unique | Row label and the link text; rows are ordered by it |
| `acct_type` | Enum(`AcctType`) | Selects which of the three tables the row appears in |
| `is_active` | Boolean, default `True` | **The field this feature surfaces.** Drives the `Active?` cell and the `tr.inactive` class |
| `credit_limit` | Numeric(10,4), **nullable** | Credit table: "Credit Limit", and a term in "Available" and "Difference" |
| `balance` | property → `AccountBalance` or **`None`** | Latest recorded balance; `balance.ledger` is the "Balance"/"Value" cell and a term in the derived cells |
| `ofx_statement` | property → `OFXStatement` or `None` | `ofx_statement.as_of` is the "(N ago)" age next to the balance |
| `is_stale` | property → bool | Whether that age is shown in red. Now additionally gated on `is_active` (FR-007) |
| `unreconciled_sum` | property → Decimal | "Unreconciled" cell, and a term in "Difference" |

### Nullability that the page must survive (FR-006)

Two of the above can be absent, and the template currently dereferences both without a guard:

- **`balance` is `None`** when no `AccountBalance` row has ever been written for the account.
  `AccountFormHandler.submit()` writes a zero balance for every account it creates
  (`views/accounts.py:298`), so this is reachable mainly for accounts loaded by `loaddata` or
  created before that line existed.
- **`credit_limit` is `NULL`** whenever a credit account is saved with the field left blank;
  `submit()` stores `None` for an empty value (`views/accounts.py:267-269`).

The display filters (`dollars`, `reddollars`, `ago`) already return `''` for `None` and for
Jinja `Undefined`. The **arithmetic** does not: `credit_limit + balance.ledger` raises when
either is absent, returning a 500 for the whole page. The template guards these cells so a
missing value costs one cell. See research R5 for why `Account.balance` is deliberately not
changed to fabricate a zero.

## State transition: active ↔ inactive

The only state change in this feature, and the one the bug made one-way:

```text
                      uncheck "Active?" in the Edit Account modal, Save
     ┌─────────────┐  ──────────────────────────────────────────────────>  ┌───────────────┐
     │  is_active  │                                                       │   is_active   │
     │    True     │  <──────────────────────────────────────────────────  │     False     │
     └─────────────┘     check "Active?" in the Edit Account modal, Save    └───────────────┘
                         ^
                         └── BEFORE this feature: unreachable through the application.
                             The account was absent from every Accounts-page table, so
                             there was no link left that opened its modal. Recovery was
                             UPDATE accounts SET is_active=1 WHERE id=<n>;
```

Both directions are written by the same line —
`account.is_active = data['is_active']` (`views/accounts.py:281`) — and read back by
`accountModalDivFillAndShow()` (`static/js/accounts_modal.js:131`). Neither changes. The
feature restores the inbound arrow by keeping the row, and therefore the link, on the page.

### What `is_active = False` continues to mean (FR-009, unchanged)

Deactivating an account still removes it from: the dashboard's account panels
(`views/index.py:91,94,97`), the cash position waterfall (`cashposition.py:233,457`, where it
is shown in coverage groups marked "inactive account"), credit payoff (`interest.py:93`,
`Account.active_credit_accounts`), and the budget-source picker (`views/budgets.py:80`). The
transfer and transaction forms continue to reject it on submit with "From Account must be
active" / "To Account must be active" (`views/accounts.py:352,369`).

The feature changes **where the account can be seen and edited**, not **what being inactive
does**.

## Test fixture

No fixture change needed. `tests/fixtures/sampledata.py:714` already defines `DisabledBank`
— id 6, `AcctType.Bank`, `is_active=False`, one `OFXStatement` and a recorded ledger balance
of `$10.00` — which is the same account the issue's workaround example names. It becomes
visible on `/accounts` the moment the filter is dropped, and serves as the inactive fixture for
the new acceptance tests.
