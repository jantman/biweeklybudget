# Phase 1 Data Model: Omit Accounts From The Account Balances Chart

**Feature**: `specs/20260919-192038-omit-accounts-from-graphs` · **Spec**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

## Changed entity: `Account`

`biweeklybudget/models/account.py`, table `accounts`. One column is added. Nothing
else about the entity changes — no relationship, no index, no constraint, no
hybrid property, no `models/__init__.py` entry (the class is already imported).

### New column

| | |
|---|---|
| **Attribute** | `omit_from_graphs` |
| **Model definition** | `Column(Boolean, default=False)` |
| **SQL type** | `BOOLEAN` (MySQL `TINYINT(1)`) |
| **Nullable** | Yes |
| **Server default** | None |
| **Python default on insert** | `False` |
| **Placed after** | `is_active` |

Declared identically to `Budget.omit_from_graphs`
(`biweeklybudget/models/budget_model.py:88`), which is the consistency issue #357
asks for and the name the maintainer chose.

### Value semantics

| Stored value | Means | Arises when |
|---|---|---|
| `False` | Charted | A new Account (Python default), or the flag explicitly cleared |
| `True` | Not charted | The user ticked **Omit from graphs?** |
| `NULL` | Charted — identical to `False` | A row that existed before the migration |

**`NULL` is not a third state.** Every read treats it as `False` (FR-004). This is
what makes the upgrade a no-op for existing installations (FR-003) without a data
migration, and it is the entire reason the SQL filter must be written as
`isnot(True)` rather than `== False` — see [research.md](./research.md) R3. The
modal's `=== true` test gives the same answer on the client side.

### What the column must never do

The flag is presentation-only. It does not participate in:

- any balance, total, projection, allocation or interest calculation;
- `Account.active_accounts()` or `Account.active_credit_accounts()`, and therefore
  no account picker;
- reconciliation, transfers, Plaid updates, or the stale-data check;
- the Accounts page's own queries, which list every Account regardless.

See the call-site table in [research.md](./research.md) R7. Exactly one call site
reads it.

## Migration

New revision in `biweeklybudget/alembic/versions/`, revising head `3f7c2a91e04b`
(`add_plaid_item_last_successful_update`). Re-verify the head at implementation
time in case another feature merges first.

```text
upgrade()    op.add_column('accounts',
                 sa.Column('omit_from_graphs', sa.Boolean(), nullable=True))
downgrade()  op.drop_column('accounts', 'omit_from_graphs')
```

The column definition matches the model exactly, as Constitution III requires:
`Column(Boolean, default=False)` carries a Python-side default only, so the DDL has
no server default and is nullable.

**Reversibility**: `downgrade()` drops the column and with it every stored flag.
That is the correct and only sensible reverse — the flag is a presentation
preference with no other record of it — and it loses no financial data. Balance
records for flagged Accounts are untouched in both directions.

## Unchanged entities

- **`AccountBalance`** — unchanged. Records belonging to flagged Accounts are
  stored, read, and skipped at render time; none is deleted (FR-012). Un-flagging
  an Account restores its full line, including history recorded while flagged.
- **`Budget`** — unchanged. Its own `omit_from_graphs` is the source of this
  pattern and keeps its current behaviour; the two flags are independent.

## Serialization

`ModelAsDict.as_dict` walks `vars(self)`, so `omit_from_graphs` appears in
`GET /ajax/account/<id>` with no code change (FR-008). `POST /forms/account`
accepts it as a JSON boolean, stored by `AccountFormHandler.submit()` next to
`is_active`. No validation is added: a checkbox has no invalid value, which is why
the Budget handler does not validate its equivalent either.
