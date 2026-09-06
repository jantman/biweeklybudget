# Interface Contracts: Special Handling of Credit Card Payments

**Feature**: `specs/20260906-174344-credit-card-payments/`
**Date**: 2026-09-06

The application exposes an HTTP interface to its own browser front-end. Three existing
contracts change and one new endpoint is added. All JSON is produced by the application's
`MagicJSONEncoder`, which renders `Decimal` as a number and `date` as an object with a
`str` key, exactly as the existing endpoints do.

---

## Changed: `POST /forms/transaction`

Handled by `TransactionFormHandler`.

### New request fields

| Field | Type | Required | Meaning |
|-------|------|----------|---------|
| `no_budget_impact` | `"true"` / `"false"` (checkbox) | No — absent means false | The user's explicit no-budget-impact choice |
| `credit_payment_acct` | account id as string, or `"None"` | No — absent or `"None"` means not a credit card payment | Credit account this transaction pays |

### New validation errors (blocking)

Returned in the existing error hash, keyed by field name:

| Condition | Field | Message |
|-----------|-------|---------|
| `credit_payment_acct` names no existing account | `credit_payment_acct` | `Account ID <id> is invalid.` |
| The named account is not of type Credit | `credit_payment_acct` | `<name> is not a credit account; only credit accounts can be paid.` |

All existing validations are unchanged. No warning from this feature blocks submission
(FR-021, FR-022).

### Behaviour

On success both fields are persisted. Clearing `credit_payment_acct` to `"None"` clears the
column, and the transaction's budget impact is then governed solely by `no_budget_impact`
(FR-014).

---

## Changed: `GET /ajax/transactions`

Handled by `TransactionsAjax`; server-side DataTables source.

Each row's `DT_RowData` gains:

| Key | Type | Meaning |
|-----|------|---------|
| `no_budget_impact` | `bool` | The effective exclusion — `is_excluded_from_budget`, not the raw column |
| `credit_payment_acct_id` | `int` or `null` | The credit account paid, if any |
| `credit_payment_acct_name` | `str` or `null` | Its name, for display |

Existing columns, ordering, and the per-column filter behaviour of `_filterhack` are
unchanged.

---

## Changed: `GET /ajax/transactions/<int:trans_id>`

Handled by `OneTransactionAjax`; drives the edit modal.

The response gains `no_budget_impact` (the raw stored column, so the checkbox reflects the
user's own choice), `credit_payment_acct_id`, `credit_payment_acct_name`, and
`is_excluded_from_budget` (the derived effective value).

---

## New: `GET /ajax/credit-payment-info`

Handled by a new `CreditPaymentInfoAjax` view registered in
`biweeklybudget/flaskapp/views/transactions.py`. Serves the modal's live attribution panel.

### Query parameters

| Parameter | Type | Required | Default | Meaning |
|-----------|------|----------|---------|---------|
| `account_id` | int | Yes | — | The credit account being paid |
| `amount` | decimal string | Yes | — | Candidate payment amount, already normalized client-side |
| `date` | `YYYY-MM-DD` | No | today | Payment date |
| `txn_id` | int | No | — | Id of the transaction being edited, excluded from prior payments (FR-019) |
| `payer_account_id` | int | No | — | Account the payment is recorded against, for the self-payment check (FR-022) |

### Response — 200

```json
{
  "account_id": 3,
  "account_name": "CreditOne",
  "amount": 500.00,
  "begin_date": {"str": "2017-01-01"},
  "periods": [
    {
      "start_date": {"str": "2017-07-21"},
      "end_date": {"str": "2017-08-03"},
      "is_closed": true,
      "outstanding": 400.00,
      "attributed": 400.00
    },
    {
      "start_date": {"str": "2017-08-04"},
      "end_date": {"str": "2017-08-17"},
      "is_closed": false,
      "outstanding": 150.00,
      "attributed": 100.00
    }
  ],
  "total_unpaid": 550.00,
  "total_attributed": 500.00,
  "excess": 0.00,
  "pays_itself": false,
  "warnings": []
}
```

`periods` is ordered oldest first and contains only pay periods with outstanding charges
inside the tracking window.

### Response — over-payment

`excess` is positive and `warnings` carries the advisory text, for example:

```json
{
  "total_unpaid": 550.00,
  "total_attributed": 550.00,
  "excess": 50.00,
  "warnings": [
    "This payment exceeds the $550.00 of unpaid charges recorded for CreditOne by $50.00. This usually means charges are missing from your records, or were recorded against the wrong account."
  ]
}
```

### Response — self-payment

`pays_itself` is `true` and `warnings` gains:

```text
This transaction is recorded against CreditOne and is also marked as a payment toward CreditOne. A payment should be recorded against the account the money came from.
```

### Errors

| Status | Condition | Body |
|--------|-----------|------|
| 400 | `account_id` missing, unparseable, or naming no account | `{"error": "..."}` |
| 400 | The account is not of type Credit | `{"error": "..."}` |
| 400 | `amount` missing or unparseable | `{"error": "..."}` |

The endpoint is read-only, has no side effects, and is safe to call on every keystroke.

---

## UI contract: the Add/Edit Transaction modal

Rendered by `transModalDivForm()` in `transactions_modal.js`.

| Element id | Control | Behaviour |
|------------|---------|-----------|
| `trans_frm_no_budget_impact` | checkbox | Unchecked by default; posts `no_budget_impact` |
| `trans_frm_credit_payment_acct` | select | Active credit accounts plus an empty "not a credit card payment" default; posts `credit_payment_acct` |
| `trans_frm_credit_payment_info` | div | Attribution table and warnings; empty and hidden while no credit account is selected |

The info div refreshes when the credit account select changes and when the amount or date
input changes, and is populated from `GET /ajax/credit-payment-info`. It never disables the
Save button.

`transactions.html` gains a `credit_acct_names_to_id` JavaScript variable alongside the
existing `acct_names_to_id`, populated server-side with active credit accounts only.
