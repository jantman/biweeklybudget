# Contract: Unallocated-Funds Notification Content

**Feature**: [spec.md](../spec.md) | **Plan**: [plan.md](../plan.md) | **Date**: 2026-09-07

`NotificationsController.get_notifications()` returns an ordered list of dicts,
each with keys `classes` and `content`. `content` is raw HTML rendered inside
`#notifications-row` by the base template, via the `notifications` context
processor (`flaskapp/context_processors.py:53`). This file is the contract the
unit and acceptance tests assert against.

Only the funds-comparison notification changes. The stale-accounts notification
and the unreconciled-OFXTransactions notification are unchanged in content,
classes and ordering.

## Ordering

Unchanged: stale accounts (if any), then the funds comparison (if any), then
unreconciled OFX transactions (if any).

## The funds-comparison notification

Let:

- `A` = funds available = `budget_account_sum() + credit_account_sum()`
- `C` = funds committed = `standing_budgets_sum() + pp_sum() + budget_account_unreconciled()`

| Condition | Emitted |
|---|---|
| `A < C` | one dict, `classes` = `alert alert-danger` |
| `A > C` | one dict, `classes` = `alert alert-info` |
| `A == C` | nothing |

The `classes` values and the three-way behaviour are unchanged from before this
feature.

### `content`

`{VERB}` is `is less than` for the danger case and `is more than` for the info
case. Everything else is identical between the two.

```html
Combined balance of all <a href="/accounts">budget-funding accounts</a> less
<a href="/accounts">credit account balances</a> ({A}) {VERB} all allocated funds
total of {C} ({S} <a href="/budgets">standing budgets</a>; {P} <a
href="/pay_period_for">current pay period allocated but unspent</a>; {U} <a
href="/reconcile">unreconciled</a>)!
```

Where, each formatted with `biweeklybudget.utils.fmt_currency`:

| Token | Quantity |
|---|---|
| `{A}` | funds available, after credit balances are applied |
| `{C}` | funds committed total |
| `{S}` | `standing_budgets_sum()` |
| `{P}` | `pp_sum()` — allocated minus spent for the current pay period |
| `{U}` | `budget_account_unreconciled()` |

### Links, in document order

| # | `href` | Link text |
|---|---|---|
| 0 | `/accounts` | `budget-funding accounts` |
| 1 | `/accounts` | `credit account balances` |
| 2 | `/budgets` | `standing budgets` |
| 3 | `/pay_period_for` | `current pay period allocated but unspent` |
| 4 | `/reconcile` | `unreconciled` |

Five links, where there were four. The acceptance tests index links
positionally, so this ordering is part of the contract.

## What changed, and why each change is required

| Before | After | Requirement |
|---|---|---|
| Reported figure was `budget_account_sum()` alone | Reports funds available, net of credit balances | FR-001 |
| No mention of credit accounts | `less <a href="/accounts">credit account balances</a>` names the deduction | FR-007 |
| `current pay period remaining`, linked to `/pay_period_for` | `current pay period allocated but unspent`, same link | FR-006, FR-008 |
| Four links | Five links | FR-007 |

`{P}` is the same number as before; only its name changes. The pay period view's
own "remaining" figure (`income − budgets_total`) is a different quantity and is
not touched — that view is correct as it stands.

## Formatting

All five figures go through `fmt_currency`, so they honour the configured locale
and currency symbol, and negative values are rendered the way negative currency
is rendered everywhere else in the application (FR-011). `{A}` in particular may
legitimately be negative when credit balances exceed funding balances.

Zero figures are rendered, not suppressed, so the parenthesised breakdown always
visibly accounts for `{C}`.

## Non-contract

The following are explicitly *not* promised and may change without this being a
breaking change: whitespace and line wrapping within the HTML string, and the
order in which the controller computes the underlying figures. Nothing outside
the template and this feature's tests consumes this string; there is no stored
data, API response or export that depends on its wording.
