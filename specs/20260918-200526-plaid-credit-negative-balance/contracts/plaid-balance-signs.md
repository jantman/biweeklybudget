# Contract: Balance Sign Recorded By `PlaidUpdater`

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-18

This is an internal contract between `biweeklybudget.plaid_updater.PlaidUpdater` and every
consumer of a recorded account balance. It has no HTTP surface and no user-facing API
change; the Plaid update endpoints (`/plaid-update`) keep their existing request and
response shapes exactly. What is specified here is the number the updater writes.

## Invariant

> For every account, the balance biweeklybudget records is **positive when the account
> holds money the user can spend** and **negative when the user owes money**, regardless of
> the sign in which the upstream source reports it.

## Per-account-type contract

Let `C = plaid_acct_info['balances']['current']`, quantized to two decimal places with
`ROUND_HALF_DOWN`.

| `PlaidAccount.account_type` | Recorded `OFXStatement.ledger_bal` and `AccountBalance.ledger` |
|---|---|
| `depository` | `C` |
| `investment` | `C` |
| `loan` | `-C` |
| `credit` | `-C` ← **changed by this feature; was `C`** |
| anything else | `RuntimeError` (unchanged) |

`-C` is a unary minus on the quantized `Decimal`, so:

* `C = Decimal('1000.00')` → `Decimal('-1000.00')`
* `C = Decimal('-50.00')` → `Decimal('50.00')`
* `C = Decimal('0.00')` → `Decimal('0.00')`, **not** `Decimal('-0.00')`

It is never `abs(C)` and never conditional on the sign of `C`.

## Method signature

```python
def _update_bank_or_credit(
    self, end_dt: datetime, account: Account, plaid_acct_info: dict,
    plaid_txns: List[dict], stmt: OFXStatement, negate_balance: bool = False
) -> None
```

`negate_balance` is keyword-with-default, mirroring `_update_investment()`. Call sites in
`_stmt_for_acct()`:

| Branch | Call |
|---|---|
| `credit` | `self._update_bank_or_credit(end_dt, account, plaid_acct_info, plaid_txns, stmt, negate_balance=True)` |
| `depository` | `self._update_bank_or_credit(end_dt, account, plaid_acct_info, plaid_txns, stmt)` |

Both existing callers of `_update_investment()` are unchanged.

## What this contract does not cover

These are explicitly outside it and must not change:

* **Transaction amounts.** `OFXTransaction.amount` is recorded from
  `plaid_txns[*]['amount']`, negated only by the per-account `Account.negate_ofx_amounts`
  setting. `negate_balance` and `negate_ofx_amounts` are independent; setting either must
  not affect what the other governs.
* **Available balance.** `OFXStatement.avail_bal` and `AccountBalance.avail` record Plaid's
  `balances.available` as reported.
* **Every other statement field**: `as_of`, `ledger_bal_as_of`, `avail_bal_as_of`,
  `currency`, `type`, `bankid`, `acctid`, `filename`, `file_mtime`.
* **The return value of `_stmt_for_acct()`** — `(statement_id, count_new, count_updated)`
  — and therefore the JSON returned by `/plaid-update`.

## Diagnostic consistency check (non-binding)

When, and only when, `negate_balance` is true and `account.credit_limit is not None` and
the available balance is not `None` and `C != 0`:

```text
err_normal   = abs(available - (credit_limit - C))
err_reversed = abs(available - (credit_limit + C))
```

If `err_reversed < err_normal` **and** `err_normal > abs(C)`, log a warning naming the
account and the three figures.

Binding constraints on the check:

* It MUST NOT alter any recorded value. The balance is recorded as `-C` whatever the check
  concludes.
* It MUST NOT raise, and MUST NOT cause the account or item to be reported as failed.
* It MUST be skipped, silently, when any input is missing or when `C` is zero.
