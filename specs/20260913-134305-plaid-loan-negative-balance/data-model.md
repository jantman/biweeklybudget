# Data Model: Plaid Loan Accounts Record Money Owed As A Negative Balance

No model, column, or schema changes. This feature changes only the **sign of values
written** for one kind of account.

| Entity (table) | Field | Change |
|----------------|-------|--------|
| `PlaidAccount` (`plaid_accounts`) | `account_type` | Read only. `'loan'` selects the negated path. |
| `OFXStatement` (`ofx_statements`) | `ledger_bal` | For Plaid `loan` updates: `-round(current, 0.01)`. Otherwise unchanged. |
| `AccountBalance` (`account_balances`) | `ledger` | Same value as the statement's `ledger_bal` from the same update. |
| `AccountBalance` | `avail`, `avail_date` | Not set for loans (as today). |
| `Account` (`accounts`) | `acct_type` | Unchanged; no `Loan` value. Loans are recommended to be linked to `Investment`. |

## Validation rules

- The statement `ledger_bal` and the `AccountBalance.ledger` written by one update are
  equal (FR-002).
- A zero balance is stored as `0.00`, never `-0.00` (research R2).
- Rows written before this change are not modified by the application (FR-005).
