# Contract: `GET /ajax/credit-payment-info`

**Feature**: Credit Payment Panel Window
**Handler**: `CreditPaymentInfoAjax` in `biweeklybudget/flaskapp/views/transactions.py`
**Consumer**: `transModalCreditPaymentInfoHtml()` in
`biweeklybudget/flaskapp/static/js/transactions_modal.js`

Read-only, no side effects, called on every keystroke in the amount field. The handler
itself does not change; the response body gains one key and two keys change meaning.

## Request

Unchanged.

| Parameter | Required | Meaning |
|-----------|----------|---------|
| `account_id` | yes | the credit account being paid; 400 if missing, unknown, or not a credit account |
| `amount` | yes | the candidate payment amount; 400 if unparseable |
| `date` | no | payment date, `YYYY-MM-DD`; defaults to today, 400 if malformed |
| `txn_id` | no | the transaction being edited |
| `payer_account_id` | no | the account the payment is recorded against |

## Response — 200

```json
{
  "account_id": 2,
  "account_name": "CreditOne",
  "amount": "400.00",
  "begin_date": "2026-09-04",
  "configured_begin_date": "2018-01-06",
  "periods": [
    {
      "start_date": {"str": "2026-09-04", "...": "MagicJSONEncoder date form"},
      "end_date":   {"str": "2026-09-17", "...": "MagicJSONEncoder date form"},
      "is_closed": true,
      "outstanding": "400.00",
      "attributed": "400.00"
    }
  ],
  "rollup": {
    "count": 14,
    "start_date": {"str": "2026-01-02"},
    "end_date":   {"str": "2026-07-10"},
    "outstanding": "1380.00",
    "attributed": "400.00"
  },
  "total_unpaid": "1780.00",
  "total_attributed": "400.00",
  "excess": "0.00",
  "pays_itself": false,
  "warnings": []
}
```

### Changes to the body

| Key | Change |
|-----|--------|
| `begin_date` | **meaning changed** — now the *effective* window start, per account, not the configured setting. Never earlier than `configured_begin_date`. |
| `configured_begin_date` | **new** — the configured setting verbatim, so the panel can distinguish a derived bound from the floor. |
| `periods` | **bounded** — at most `CREDIT_PAYMENT_MAX_PERIODS` (6) entries, the most recent ones, still oldest-first. Was unbounded. |
| `rollup` | **new** — an object describing the collapsed older periods, or `null` when nothing was collapsed. |

Every other key is unchanged in name, type and meaning. `total_unpaid`,
`total_attributed` and `excess` are still computed over the whole window, not over the
rendered subset.

### Compatibility

No consumer outside `transactions_modal.js` exists. `periods` shrinking is a behaviour
change by design (spec FR-011); a client that ignored `rollup` would understate the
totals, which is exactly why `rollup` carries both summed amounts and why FR-014 requires
the rendered rows to reconcile.

## Response — 400

Unchanged: `{"error": "..."}` for a missing/invalid `account_id`, a non-credit account,
an unparseable `amount`, or a malformed `date`. The panel renders the error text as muted
prose and the transaction remains saveable.

## Rendering contract

| Response shape | Panel |
|----------------|-------|
| `periods` empty, `rollup` null | "No unpaid charges are recorded for {account_name}." plus any warnings |
| `rollup` null | table of `periods` as today, oldest first |
| `rollup` non-null | one summary row `{count} older periods ({start} – {end})`, status `rolled up`, at the **head** of the table body, then the `periods` rows |
| `rollup.attributed` non-zero | the summary row is additionally emphasised (FR-015) |
| any | a line stating the window start from `begin_date` (FR-016); the existing totals line; warnings above the table |

Element ids the acceptance tests rely on: `credit_payment_periods` (the table, existing),
`credit_payment_totals` (the totals line, existing), `credit_payment_warning_{i}`
(existing), `credit_payment_rollup` (the summary row, **new**), `credit_payment_window`
(the window line, **new**).
