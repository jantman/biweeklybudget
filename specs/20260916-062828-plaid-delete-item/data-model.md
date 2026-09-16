# Phase 1 Data Model: Delete a Plaid Item

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md)

## Summary

**No schema change.** No column is added, removed or altered; no Alembic revision is created.
This feature only changes *rows*, and only along relationships that already exist. The
constitution's Principle III (schema changes ship with reversible migrations) is therefore not
engaged — see the Constitution Check in [plan.md](./plan.md).

What the feature needs from the data model is the deletion order that the existing constraints
force, and the guarantee that nothing outside the Plaid tables is destroyed.

## Entities involved

### `PlaidItem` — `biweeklybudget/models/plaid_items.py`

Table `plaid_items`. One row per linked institution connection.

| Column | Type | Role in this feature |
|---|---|---|
| `item_id` | `String(70)`, PK | Identifies the Item to delete; supplied by the request |
| `access_token` | `String(70)` | Passed to Plaid's Item-removal call. Never leaves the server |
| `institution_name` | `String(100)` | Shown in the confirmation |
| `institution_id` | `String(50)` | — |
| `last_updated` | `UtcDateTime` | — |
| `last_successful_update` | `UtcDateTime` | — |

Relationship: `all_accounts` → `PlaidAccount`, ordered by `account_id`. **No cascade is
configured**, so the child rows must be deleted explicitly (research R3).

**Change**: the row is deleted.

### `PlaidAccount` — `biweeklybudget/models/plaid_accounts.py`

Table `plaid_accounts`. Composite primary key `(item_id, account_id)`; `item_id` is a foreign
key into `plaid_items.item_id` with **no** `ON DELETE` action and `nullable=False`.

Relationships: `plaid_item` → `PlaidItem`; `account` (backref from `Account.plaid_account`,
`uselist=False`) → the at-most-one `Account` linked to it.

**Change**: every row with `item_id == <the Item>` is deleted.

### `Account` — `biweeklybudget/models/account.py`

Table `accounts`. Carries a composite foreign key `(plaid_item_id, plaid_account_id)` into
`plaid_accounts (item_id, account_id)`, again with no `ON DELETE` action. Both columns are
nullable; the hybrid property `plaid_configured` is true only when both are set.

**Change**: for every Account whose `plaid_item_id` equals the Item being deleted, both
`plaid_item_id` and `plaid_account_id` are set to `NULL`. **Nothing else on the Account is
written** — this is the same two-line assignment `flaskapp/views/accounts.py:286-288` already
performs when the account form's Plaid dropdown is set to "none".

### Not touched

`OFXTransaction`, `OFXStatement`, `TxnReconcile`, `Transaction`, `BudgetTransaction`, `Budget`
and every other model. Downloaded transactions and statements belong to the `Account`, not to
the Plaid Item, so they survive untouched (FR-009, User Story 3). `db_event_handlers`' flush
hooks filter on `BudgetTransaction` and ignore Plaid rows entirely (research R3), so no budget
arithmetic runs.

## Required mutation order

Forced by the foreign keys, not chosen:

```text
1. (Plaid)  item_remove(access_token)         — must precede everything below
2. UPDATE   accounts  SET plaid_item_id=NULL, plaid_account_id=NULL
            WHERE plaid_item_id = :item_id
3. DELETE   plaid_accounts WHERE item_id = :item_id
4. DELETE   plaid_items    WHERE item_id = :item_id
5. COMMIT                                      — steps 2-4 in one transaction
```

- **1 before 2-4**: the access token is the only way to reach Plaid, and step 4 destroys it
  (spec Assumptions; research R4).
- **2 before 3**: `accounts.(plaid_item_id, plaid_account_id)` references `plaid_accounts`;
  deleting a referenced `PlaidAccount` first raises a foreign key error.
- **3 before 4**: `plaid_accounts.item_id` references `plaid_items` and is `NOT NULL` and part
  of the composite primary key, so SQLAlchemy's default relationship behaviour (NULL the
  child's FK) cannot work and a direct delete of the parent fails.
- **Single commit for 2-4**: gives FR-010's all-or-nothing guarantee. If any of them raises,
  the session is rolled back and the database is exactly as it was.

This is the same order as the issue's manual procedure and as
`tests/acceptance/test_plaidlink.py:85-95`, except that the Plaid call is moved from last to
first.

## State transitions

An `Account` moves between exactly two states, in one direction per deletion:

```text
linked  (plaid_item_id IS NOT NULL AND plaid_account_id IS NOT NULL)
   │  Item deleted
   ▼
unlinked (both NULL)  ── re-linkable via the existing account form ──▶ linked
```

An unlinked Account is indistinguishable from one that was never linked: `plaid_configured` is
false, the account form's Plaid dropdown shows "none", and every remaining Plaid Account of
every remaining Item is selectable for it (FR-015, research R9).

## Invariants after a successful deletion

1. No `plaid_items` row with that `item_id`.
2. No `plaid_accounts` row with that `item_id`.
3. No `accounts` row with that `plaid_item_id`.
4. Every `accounts` row that previously carried that `plaid_item_id` still exists, with every
   other column unchanged, and with both Plaid columns `NULL`.
5. Every other `plaid_items` row, its `plaid_accounts` rows and the `accounts` rows referencing
   them are byte-for-byte unchanged (FR-011).
6. Row counts in `ofx_trans`, `ofx_statements`, `txn_reconciles`, `transactions`,
   `budget_transactions` and `budgets` are unchanged.

## Invariants after a failed deletion

All six of the above hold with "the Item" still present: nothing at all changed (FR-007,
FR-010). The only exception is the window described in research R4 — Plaid accepted the removal
but the local commit failed — which leaves the database untouched and is resolved by retrying,
because Plaid then reports the Item as not found and the retry completes locally.
