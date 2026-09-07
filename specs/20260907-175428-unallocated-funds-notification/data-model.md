# Phase 1 Data Model: Correct the Unallocated-Funds Notification

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-07

## Schema changes

**None.** No file under `biweeklybudget/models/` is modified, no column is added,
altered or dropped, and no Alembic migration is created. See
[plan.md](./plan.md) Constitution Check, principle III.

This document therefore describes the *existing* model attributes the feature
reads, and the derived quantities it computes from them, so that the tasks and
tests have a single statement of where each number comes from.

## Existing model attributes consumed

| Attribute | Defined at | Type | Used for |
|---|---|---|---|
| `Account.acct_type` | `models/account.py:139` | `Enum(AcctType)` | Selecting credit accounts (`AcctType.Credit`) |
| `Account.is_active` | `models/account.py` | `Boolean` | Excluding closed accounts from both sums |
| `Account.is_budget_source` | `models/account.py:228` | derived property — true for `Bank` and `Cash` | Selecting funding accounts (existing behaviour) |
| `Account.balance` | `models/account.py:295-305` | latest `AccountBalance` or `None` | Source of each account's current balance |
| `AccountBalance.ledger` | `models/account_balance.py:64` | `Numeric(10,4)`, nullable | The balance figure itself |
| `Account.unreconciled_sum` | `models/account.py:343-364` | `Decimal` | Unreconciled term; already excludes no-cash-impact transactions |
| `Account.active_credit_accounts(db)` | `models/account.py:307-322` | query | The set of credit accounts to sum |
| `Transaction.no_budget_impact` | `models/transaction.py:159` | `Boolean`, not null, default false | Read only indirectly, via `is_excluded_from_budget` |
| `Transaction.is_excluded_from_budget` | `models/transaction.py:227-249` | derived `bool` | Exclusion rule already applied inside `unreconciled_sum` |
| `Budget.current_balance` | `models/budget_model.py` | `Numeric` | Standing budgets term (existing behaviour) |
| `BiweeklyPayPeriod.overall_sums` | `biweeklypayperiod.py` | dict with `allocated`, `spent` | Pay period term (existing behaviour) |

### Sign convention (critical)

`AccountBalance.ledger` for an account of type `Credit` is **negative when money
is owed**. Confirmed by `abs()` usage at `interest.py:118`, `interest.py:121` and
`credit_payoffs.py:98`, and by the sample data
(`CreditOne` latest `-952.06`, `CreditTwo` `-5498.65`). Bank, cash and investment
balances are positive when money is held.

Consequences the implementation depends on:

- Summing credit ledgers **with their own sign** and adding the result to the
  funding-account total performs the required subtraction.
- A credit account with a *positive* ledger (overpaid card, or a statement credit
  exceeding the balance) correctly *increases* funds available.
- Taking `abs()` anywhere in this feature's arithmetic would be a defect.

## Derived quantities

These are computed per request and stored nowhere.

### `credit_account_sum` — NEW

- **Definition**: the sum of `balance.ledger` over every account returned by
  `Account.active_credit_accounts()`, skipping any account where `balance` is
  `None` or `balance.ledger` is `None`.
- **Type**: `Decimal`, starting from `Decimal('0.0')`.
- **Sign**: negative when money is owed; zero when there are no active credit
  accounts; may be positive if cards are overpaid.
- **Requirements**: FR-001, FR-002, FR-003.

### `funds_available` — NEW (composed, not a separate method)

- **Definition**: `budget_account_sum() + credit_account_sum()`.
- **Meaning**: money the person could spend now, net of what they already owe on
  credit accounts.
- **Sign**: may be negative if credit balances exceed funding balances (FR-001,
  and an explicit edge case in the spec).
- **Replaces**: the bare `budget_account_sum()` that the banner compared and
  reported previously.

### `funds_committed` — unchanged in quantity

- **Definition**: `standing_budgets_sum() + pp_sum() + budget_account_unreconciled()`.
- **Meaning**: money already spoken for.
- **Change**: none to the arithmetic (FR-004). Only the *name* given to the
  `pp_sum()` term in the rendered sentence changes (FR-006).

## Relationships that matter here

```
Account (is_active, acct_type)
  ├── is_budget_source (Bank | Cash) ──► balance.ledger ──┐
  │                                                        ├──► funds_available
  └── AcctType.Credit ─────────────────► balance.ledger ──┘
        ▲
        └── Transaction.is_excluded_from_budget is true for payments toward
            one of these accounts, which is why such payments are already
            absent from Account.unreconciled_sum

Account.unreconciled_sum ──► budget_account_unreconciled ──┐
Budget.current_balance (standing, active) ─────────────────┼──► funds_committed
BiweeklyPayPeriod.overall_sums (allocated − spent) ────────┘
```

The one subtlety worth stating: an active credit account appears on **both** sides
of that diagram — its balance reduces funds available, and its existence is what
causes payments toward it to be excluded from the unreconciled term. Those two
effects are independent and must not be confused for double-counting. The balance
is what is owed; the exclusion prevents a payment being charged against a budget a
second time.

## Validation rules

- Every monetary accumulation uses `Decimal`, never `float`, and starts from
  `Decimal('0.0')` to match the surrounding code.
- A `None` balance or `None` ledger contributes zero and must not raise (FR-003).
- No value computed here is persisted, so there are no state transitions,
  invariants to enforce on write, or backfill concerns.
