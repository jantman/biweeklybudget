# Contract: Stored Balance Sign By Plaid Account Type

Applies to every balance `PlaidUpdater` records (`OFXStatement.ledger_bal` and
`AccountBalance.ledger`) from Plaid's `balances.current`, after rounding to cents with
`ROUND_HALF_DOWN`.

| Plaid `account_type` | Stored ledger balance | Available balance | Changed by this feature |
|----------------------|-----------------------|-------------------|-------------------------|
| `depository` | `current` | `available`, if present | No |
| `credit` | `current` | `available`, if present | No |
| `investment` | `current` | not recorded | No |
| `loan` | **`-current`** | not recorded | **Yes** (was `current`) |
| anything else | update fails with `RuntimeError` (unknown type) | — | No |

## Examples (`loan`)

| Plaid `balances.current` | Stored ledger |
|--------------------------|---------------|
| `250000.00` | `-250000.00` |
| `1234.5678` | `-1234.57` |
| `-50.25` (lender owes holder) | `50.25` |
| `0` | `0.00` |

## Internal interface

`PlaidUpdater._update_investment(end_dt, account, plaid_acct_info, stmt, negate_balance=False)`.
When `negate_balance` is true, the stored figure is sign-reversed as above. The `loan`
branch of `_stmt_for_acct()` is the only caller that passes `True`.
