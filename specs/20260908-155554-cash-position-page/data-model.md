# Data Model: Cash Position Page

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-08

Two kinds of entity appear here: one **persisted** (the budget/account
association, which is the only schema change) and several **computed** (the
statement the page and the banner both consume, which is never stored).

---

## Persisted

### `budget_accounts` (new table)

Records that a standing budget's money is held in a given account. Carries no
amount and no split — see [research.md](./research.md) R2 and spec FR-019.

| Column | Type | Null | Notes |
|---|---|---|---|
| `budget_id` | Integer | no | FK → `budgets.id`, `ON DELETE CASCADE` |
| `account_id` | Integer | no | FK → `accounts.id`, `ON DELETE CASCADE` |

- **Primary key**: composite `(budget_id, account_id)`. Makes the pairing
  unique for free; the same link cannot be recorded twice.
- **Engine**: `InnoDB`, matching every other table in this schema.
- **Cascades** satisfy FR-016 at the database level: deleting either side
  removes the association row, so no dangling row can outlive its referent
  and no application code has to remember to clean up.

Declared as a `sqlalchemy.Table` on `Base.metadata` in
`biweeklybudget/models/budget_account_link.py`, imported by
`biweeklybudget/models/__init__.py` so Alembic and `alembic-verify` see it
(constitution III).

**Migration**: new revision with `down_revision = 'f9df90273cdd'` (the current
head). `upgrade()` creates the table; `downgrade()` drops it. Both directions
tested in `tests/migrations/test_migration_<rev>.py`, following the shape of
`test_migration_f9df90273cdd.py`.

### `Budget` (modified)

- `accounts` — `relationship('Account', secondary=budget_accounts, backref='budgets')`.
- `_dict_properties` gains `account_ids`, a `@property` returning
  `[a.id for a in self.accounts]`.

  **Why explicitly**: `ModelAsDict.as_dict` is built from `vars(self)`, i.e.
  the instance `__dict__`. A relationship appears there only if it happens to
  have been loaded, so `GET /ajax/budget/<id>` would return account IDs
  sometimes and not others. `_dict_properties` forces it. This is the one
  design detail the Phase 1 re-check surfaced; see [plan.md](./plan.md).

### `Account` (modified)

- `budgets` — the backref from `Budget.accounts`. No column change.

**Validation rules**

- The association is optional on both sides. A standing budget with no linked
  account, and an account with no linked budget, are both valid and expected —
  they are the state of every installation immediately after the migration
  (spec Assumptions, FR-015).
- Links are only *offered* for standing budgets (`is_periodic == False`);
  periodic budgets hold no balance, so a link would mean nothing (FR-015).
  This is a UI rule, not a database constraint: an existing link is still read
  and displayed if a budget's type is later flipped, rather than silently
  disappearing.
- Links to inactive, credit, or investment accounts are permitted and are
  displayed, but only *active budget-funding* accounts contribute to the
  waterfall. A coverage group containing such an account must mark it as not
  counted rather than dropping it (spec Edge Cases).

---

## Computed

None of the following is stored. They are the return shape of
`biweeklybudget.cashposition.CashPosition`, which both the page and the
notification banner consume (FR-005). The full contract is in
[contracts/cash-position-statement.md](./contracts/cash-position-statement.md).

### `CashPosition`

Constructed from a database session and computed once per request.

| Attribute | Type | Meaning |
|---|---|---|
| `budget_account_lines` | list of `AccountLine` | active budget-funding accounts, itemized |
| `credit_account_lines` | list of `AccountLine` | active credit accounts, itemized |
| `standing_budget_lines` | list of `BudgetLine` | active standing budgets, itemized |
| `budget_account_ledger` | Decimal | sum of ledger balances (waterfall term 1, added) |
| `unreconciled` | Decimal | sum of `unreconciled_sum` (waterfall term 2, **subtracted**) |
| `credit_balance` | Decimal | sum of credit ledgers, **with their recorded sign** (term 3, added) |
| `net_liquid` | Decimal | subtotal: `budget_account_ledger - unreconciled + credit_balance` |
| `standing_total` | Decimal | sum of standing budget balances (term 4, subtracted) |
| `pay_period_allocated_unspent` | Decimal | current period `allocated - spent` (term 5, subtracted) |
| `uncommitted` | Decimal | final: `net_liquid - standing_total - pay_period_allocated_unspent` |
| `pay_period` | BiweeklyPayPeriod | the period containing today (FR-024) |
| `unlinked_accounts` | list of `AccountLine` | active budget-funding accounts with no active linked standing budget (FR-017) |
| `coverage_groups` | list of `CoverageGroup` | FR-018 |

**The identity that must hold** (FR-004), and which a test asserts directly:

```
uncommitted == (budget_account_ledger + credit_balance)
               - (standing_total + pay_period_allocated_unspent + unreconciled)
```

The right-hand side is exactly `available - bal_sum` as the existing banner
computes it. The waterfall is a reassociation of those same terms, not a new
calculation.

### `AccountLine`

| Field | Type | Meaning |
|---|---|---|
| `account` | Account | the account |
| `ledger` | Decimal or None | raw ledger balance; `None` means no balance recorded |
| `unreconciled` | Decimal | `Account.unreconciled_sum` |
| `projected` | Decimal or None | `ledger - unreconciled`, or `None` when `ledger` is `None` |
| `as_of` | datetime or None | when the balance was recorded (FR-024) |
| `counted` | bool | whether this line contributes to the waterfall |

`ledger` is `None` when `account.balance` is `None` **or**
`account.balance.ledger` is `None`. Such a line contributes `Decimal('0')` to
every total and renders as "no balance recorded" (FR-023) — never as `$0.00`,
because "no data" and "zero dollars" mean very different things here.

### `BudgetLine`

| Field | Type | Meaning |
|---|---|---|
| `budget` | Budget | the standing budget |
| `current_balance` | Decimal | its balance, `Decimal('0')` if `None` |

### `CoverageGroup`

One connected component of the bipartite budget↔account graph
([research.md](./research.md) R3).

| Field | Type | Meaning |
|---|---|---|
| `accounts` | list of `AccountLine` | every account in the component |
| `budgets` | list of `BudgetLine` | every standing budget in the component |
| `account_total` | Decimal | sum over `accounts` that are `counted` |
| `budget_total` | Decimal | sum over `budgets` |
| `delta` | Decimal | `account_total - budget_total` |
| `is_balanced` | bool | `delta == 0` |
| `is_simple` | bool | exactly one account — the delta is then a true per-account delta |

`is_simple` is what lets the template say "this budget mirrors this account,
and it is off by $X" in the common case, while the general case says only
"these accounts and these budgets, together, are off by $X" (FR-019).

Groups with no budgets are **not** emitted as coverage groups; those accounts
are reported through `unlinked_accounts` instead (FR-017), so each account
appears in exactly one place.

**State transitions**: none. Every computed entity is derived fresh per
request from the current database state; nothing here has a lifecycle.
