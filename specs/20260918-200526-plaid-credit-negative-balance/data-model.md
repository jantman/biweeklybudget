# Phase 1 Data Model: Plaid Credit Card Balances Recorded As Negative

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-18

**No schema change.** No table, column, index or constraint is added, removed or altered,
and no Alembic migration is part of this feature. What changes is the *value* written to
two existing columns for one class of account, going forward. This document records the
entities involved, the sign convention each obeys, and which rows are affected.

## Entities

### `PlaidAccount` (`biweeklybudget/models/plaid_accounts.py`) — unchanged

| Field | Role in this feature |
|-------|----------------------|
| `account_type` | The Plaid account type: `credit`, `depository`, `investment` or `loan`. **This field alone selects the sign convention.** The biweeklybudget `Account.acct_type` does not, and must not, participate — a Plaid loan is documented as being linked to a biweeklybudget *Investment* account, so the two can legitimately disagree. |

### `Account` (`biweeklybudget/models/account.py`) — unchanged

| Field | Role in this feature |
|-------|----------------------|
| `credit_limit` | `Numeric(10, 4)`, nullable. Read-only input to the diagnostic consistency check. Skipped when `None`. |
| `negate_ofx_amounts` | Per-account setting negating downloaded **transaction** amounts. **Entirely separate from this feature** and untouched; a test pins that the two remain independent. |
| `acct_type` | Not consulted by the updater's sign decision. |

### `OFXStatement` (`biweeklybudget/models/ofx_statement.py`) — unchanged schema, changed values

| Field | Role in this feature |
|-------|----------------------|
| `ledger_bal` | **Sign changes for Plaid `credit` accounts.** Was Plaid's `balances.current` verbatim (positive = owed); becomes its negation (negative = owed). |
| `avail_bal` | Unchanged — recorded as Plaid reports it. Read-only input to the diagnostic check. |
| `ledger_bal_as_of`, `avail_bal_as_of`, `as_of`, `currency`, `type` | Unchanged. |

### `AccountBalance` (`biweeklybudget/models/account_balance.py`) — unchanged schema, changed values

| Field | Role in this feature |
|-------|----------------------|
| `ledger` | **Sign changes for Plaid `credit` accounts**, because `Account.set_balance()` is called with `ledger=stmt.ledger_bal`. This is the column the Account Balances chart plots. |
| `avail` | Unchanged. |

## The sign convention, per account type

biweeklybudget's invariant, repository-wide: **money owed is a negative balance; money
available is a positive balance.** Plaid does not share it. The updater is the single
place where the two are reconciled.

| Plaid `account_type` | What Plaid's `balances.current` means | Recorded by biweeklybudget as | Before this change | After this change |
|---|---|---|---|---|
| `depository` | Funds held (positive) | As reported | As reported | **unchanged** |
| `investment` | Value held (positive) | As reported | As reported | **unchanged** |
| `loan` | Principal owed (positive) | Negated | Negated (issue #263) | **unchanged** |
| `credit` | Amount owed (positive) | Negated | **As reported — the defect** | **Negated — the fix** |

Worked cases for a `credit` account:

| Plaid `balances.current` | Meaning | Recorded `ledger_bal` / `ledger` | Effect on Cash Position available funds |
|---|---|---|---|
| `1000.00` | $1,000 owed | `-1000.00` | $1,000 lower |
| `-50.00` | Card overpaid by $50 | `50.00` | $50 higher |
| `0` | Nothing owed | `0.00` (never `-0.00`) | No effect |

## Consumers — all unchanged, all already correct

| Consumer | How it uses the balance | Why no change is needed |
|---|---|---|
| `CashPosition.credit_balance` (`biweeklybudget/cashposition.py`) | Sums active credit accounts **with the sign in which each is recorded**; waterfall term 3, added. | Adding a negative balance subtracts what is owed, and an overpaid card's positive balance correctly adds. The comment becomes true once the recorded sign is right. |
| Unallocated-funds notification (`biweeklybudget/flaskapp/notifications.py`) | Adds the combined credit balance to available funds. | Same calculation — it reads `CashPosition`. |
| Account Balances chart (index page) | Plots `account_balances.ledger` over time. | Plots whatever is recorded. Pre-upgrade rows keep the old sign; see below. |
| Credit payoff calculations | Read the recorded balance. | Already built on the negative-means-owed convention, as for hand-entered credit accounts. |

## Existing rows

Rows written before this change keep the old sign. The affected set is:

* `account_balances.ledger` and `ofx_statements.ledger_bal`
* for accounts joined to a `plaid_accounts` row with `account_type = 'credit'`
* with `as_of` / `overall_date` before the first Plaid update after the upgrade.

Nothing corrects them automatically (see `research.md`, Decision 6). The visible symptom of
doing nothing is a credit card's line on the Account Balances chart jumping from positive
to negative at the first post-upgrade update. `docs/source/plaid.rst` documents the
corrective SQL — two `UPDATE ... SET col = -col` statements joined through `plaid_accounts`
on `account_type = 'credit'` — and the conditions for running it safely: once, after
upgrading and before the next Plaid update; running it twice undoes it; add a date
condition for accounts whose earlier balances came from somewhere other than Plaid.

## State transitions

None. Balances are appended, never transitioned; each Plaid update writes a new
`OFXStatement` and a new `AccountBalance`.
