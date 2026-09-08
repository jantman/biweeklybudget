# Contract: The Cash Position Statement

**Feature**: [../spec.md](../spec.md) | **Module**: `biweeklybudget/cashposition.py`

This is the single calculation FR-005 requires. Two consumers depend on it:
`CashPositionView` (the page) and `NotificationsController` (the banner). It
is the contract that makes FR-004 — page and banner always agreeing — a
property of the code rather than of two implementations happening to match.

## Construction

```python
CashPosition(sess)          # sess defaults to biweeklybudget.db.db_session
```

Computed eagerly on construction, from the state of the database at that
moment. Not cached across requests, not refreshed after construction.

## Inputs, exactly

The set of records considered is identical to the banner's today (FR-006).
Widening or narrowing it is out of scope for this feature.

| Term | Source | Filter |
|---|---|---|
| Budget-funding accounts | `Account` | `is_budget_source` and `is_active` |
| Credit accounts | `Account.active_credit_accounts(sess)` | `acct_type == Credit` and `is_active` |
| Unreconciled | `Account.unreconciled_sum` | over the budget-funding accounts above |
| Standing budgets | `Budget` | `is_periodic == False` and `is_active` |
| Pay period | `BiweeklyPayPeriod.period_for_date(dtnow(), sess)` | the period containing today |

`Account.unreconciled_sum` already excludes transactions marked
`no_budget_impact` and payments toward credit accounts (issues #210, #319).
It is used as-is; the statement does **not** apply a second filter, because a
second definition of "no cash impact" that could drift from the first is
exactly what #320's changelog says not to build.

## The waterfall, in order

| # | Term | Attribute | Op | Running |
|---|---|---|---|---|
| 1 | Budget-funding account balances | `budget_account_ledger` | `+` | |
| 2 | Adjustment for unreconciled transactions | `unreconciled` | `−` | |
| 3 | Credit account balances | `credit_balance` | `+` | **`net_liquid`** |
| 4 | Standing budget balances | `standing_total` | `−` | |
| 5 | Current pay period allocated but unspent | `pay_period_allocated_unspent` | `−` | **`uncommitted`** |

## Sign rules — normative

These are the rules a plausible-looking implementation gets wrong, and each
has a test that fails if it is broken.

1. **Credit balances are added with their recorded sign.** Money owed is
   stored negative, so adding reduces the total. A credit account carrying a
   *positive* balance — overpaid, or holding a statement credit larger than
   its balance — really does hold spendable money and MUST increase
   `net_liquid`. Do not negate; do not take an absolute value. This is the
   substance of issue #320.
2. **The unreconciled term is subtracted.** Unreconciled spending is entered
   positive, so `ledger − unreconciled` is the projected balance. This is why
   term 2 is the same operation as "ledger net of unreconciled" in the
   per-account itemization (FR-008).
3. **A standing budget with a negative balance raises `uncommitted`**, by
   subtracting a negative. No special case.
4. **`net_liquid` and `uncommitted` may be negative.** Both are legitimate
   states. Never clamp, never `abs()`.
5. **An account with no recorded balance contributes `Decimal('0')`** and is
   marked `counted = False`. It never contributes `None` and never raises.

## The invariant

```python
assert cp.uncommitted == (
    (cp.budget_account_ledger + cp.credit_balance)
    - (cp.standing_total + cp.pay_period_allocated_unspent + cp.unreconciled)
)
```

The right-hand side is `available - bal_sum` as `notifications.py` computes it
today. A test asserts this directly, over a matrix of scenarios in which each
term takes a zero, positive and negative value.

## Diagnostics

- `unlinked_accounts` — active budget-funding accounts to which no *active*
  standing budget is linked (FR-017). An account linked only to inactive
  budgets counts as unlinked, because an inactive budget allocates nothing.
- `coverage_groups` — connected components of the bipartite graph over
  `budget_accounts`, restricted to active standing budgets. A component with
  no budgets is not emitted; its accounts appear in `unlinked_accounts`
  instead, so every account appears in exactly one place.

Group construction is a pure function of the association pairs and is
unit-tested independently of the database.

## Compatibility with `NotificationsController`

These six static methods keep their names, signatures, return types and
docstring meaning. They become delegations.

| Method | Returns |
|---|---|
| `budget_account_sum(sess=None)` | `budget_account_ledger` |
| `credit_account_sum(sess=None)` | `credit_balance` |
| `budget_account_unreconciled(sess=None)` | `unreconciled` |
| `standing_budgets_sum(sess=None)` | `standing_total` |
| `pp_sum(sess=None)` | `pay_period_allocated_unspent` |
| `num_unreconciled_ofx(sess=None)` | unchanged — not part of the statement |

`standing_budgets_sum` currently returns the integer `0` rather than a
`Decimal` when there are no standing budgets. The delegation returns
`Decimal('0')`. `0 == Decimal('0')` is `True`, so existing assertions hold;
this is noted so the change is deliberate and not a surprise in review.

The banner's rendered text is unchanged (FR-025); it gains one link to
`/cash-position` and nothing else.
