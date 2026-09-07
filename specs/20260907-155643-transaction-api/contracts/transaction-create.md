# Contract: `POST /forms/transaction` (as amended)

The endpoint already exists and is documented in `docs/source/http_api.rst`. This contract
records only what this feature changes; everything not listed here is unchanged and
remains as documented there.

Handler: `biweeklybudget.flaskapp.views.transactions.TransactionFormHandler`.

## Backward compatibility

**Absolute.** The web UI posts to this endpoint. Every request that is valid today remains
valid and produces an identical result, and every request that is rejected today is still
rejected with the same message — with the single exception noted under *New error
condition* below, which cannot be triggered by any request expressible before this change.

## Changed request fields

| Field | Type | Change |
|-------|------|--------|
| `account` | string or integer | **Was**: Account ID. **Now**: Account ID *or* Account name. Required. |
| `budgets` | object | **Was**: mapping of Budget ID (string key) to decimal amount. **Now**: each key may be a Budget ID *or* a Budget name. At least one required; amounts must still sum to `amount`. |
| `credit_payment_acct` | string or integer | **Was**: Account ID of the credit account being paid, or absent/`""`/`"None"`. **Now**: Account ID *or* Account name, or absent/`""`/`"None"` for "not a credit card payment". Must still resolve to an account of type Credit. |

Unchanged fields: `id`, `description`, `amount`, `date`, `notes`, `sales_tax`,
`no_budget_impact`. `id` remains a Transaction ID only.

## Resolution rule (normative)

For each of the three fields above:

1. Coerce to string and strip surrounding whitespace. Empty or `None` means "not supplied".
2. If the result is all ASCII digits, look up by primary key; a hit ends resolution.
3. Otherwise, or if step 2 missed, look up by name — whole-string, case-insensitive.
   `Account.name` and `Budget.name` are unique, so at most one record matches.
4. No match is a validation error on that field.

Consequences a caller must know, and which the documentation states:

- **IDs win over names for digit-only values.** If Budget 12 exists and a *different*
  budget is named `"12"`, the value `12` means Budget 12.
- **Names must be exact.** No prefix, substring or fuzzy matching. Case and surrounding
  whitespace are ignored; nothing else is.
- **The `(income)` suffix is not part of a name.** The web UI displays income budgets as
  `"Bonus (income)"`; the name is `"Bonus"`.
- **IDs and names may be mixed freely** within one request, including within `budgets`.

## New error condition

If two keys of `budgets` resolve to the same Budget, the request is rejected:

```json
{
  "success": false,
  "errors": {
    "budgets": ["Budget Groceries specified more than once."]
  }
}
```

Rationale: rekeying by resolved ID would otherwise collapse the two entries and silently
drop one allocation. Unreachable before this feature, since two distinct ID keys could not
denote one Budget.

## Unresolvable reference

```json
{
  "success": false,
  "errors": {
    "account": ["Account \"No Such Bank\" is invalid."],
    "budgets": ["Budget \"No Such Budget\" is invalid."]
  }
}
```

As with all `FormHandlerView` validation failures, the HTTP status is **200** and the
outcome is carried in the body. Errors for all fields are accumulated and returned
together. Nothing is written to the database.

## Success

Unchanged from today:

```json
{
  "success": true,
  "success_message": "Successfully saved Transaction 123  in database.",
  "trans_id": 123
}
```

## Example — names only

```bash
curl -X POST http://127.0.0.1:8080/forms/transaction \
  -H 'Content-Type: application/json' \
  -d '{
        "date": "2026-09-07",
        "amount": "123.45",
        "description": "Groceries",
        "account": "CHASE",
        "notes": "",
        "budgets": {"Food": "100.00", "Household": "23.45"}
      }'
```

## Example — mixed, and a credit card payment by name

```bash
curl -X POST http://127.0.0.1:8080/forms/transaction \
  -H 'Content-Type: application/json' \
  -d '{
        "date": "2026-09-07",
        "amount": "500.00",
        "description": "CHASE payment",
        "account": "1",
        "notes": "",
        "credit_payment_acct": "CHASE",
        "budgets": {"Credit Card Payments": "500.00"}
      }'
```
