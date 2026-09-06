# Contract: `FormHandlerView` currency normalization

The single server-side interception point. Every `/forms/*` endpoint inherits it, so a
currency field is normalized by declaring its name — not by editing a conversion site.

## Declarations

```python
class FormHandlerView(MethodView):

    #: Names of form fields holding currency amounts. Values are normalized to
    #: canonical form before validate() runs; unparseable values become field
    #: errors and validate() is not called.
    currency_fields = []

    #: Names of form fields holding non-currency decimal numbers. Same
    #: normalization, different error wording.
    decimal_fields = []
```

Example:

```python
class TransactionFormHandler(FormHandlerView):
    currency_fields = ['amount', 'sales_tax']
```

## Flow in `post()`

```
data = request JSON or form
errors = self.normalize_currency(data)          # NEW
if errors:                                      # NEW
    return {'success': False, 'errors': errors} # NEW  -> never reaches validate()
try:                                            # NEW guard
    res = self.validate(data)
except Exception:                               # NEW guard
    log + return {'success': False, 'error_message': ...}
if res is not None:
    return {'success': False, 'errors': res}
try:
    res = self.submit(data)                     # unchanged
...
```

## `normalize_currency(data)`

```python
def normalize_currency(self, data):
    """
    Normalize every currency and decimal field named in ``currency_fields`` and
    ``decimal_fields`` to canonical string form, in place.

    :param data: submitted form data; modified in place
    :type data: dict
    :return: hash of field name to list of error strings; empty if all valid
    :rtype: dict
    """
```

| Rule | Behavior |
|------|----------|
| N1 | Fields absent from `data` are skipped, not reported. Handlers share field lists across create/edit shapes. |
| N2 | Values that are `''` or whitespace-only are **left untouched and not reported**. Each field's existing blank semantics — "means zero", "is required", "means omit" — are unchanged. |
| N3 | A parseable value is replaced in `data` with `str(parse_currency(value))`, so every downstream `Decimal(data[k])` / `float(data[k])` keeps working with no edit. |
| N4 | An unparseable value leaves `data` unchanged and appends to `errors[key]`: `Invalid amount: "<raw>"` for `currency_fields`, `Invalid number: "<raw>"` for `decimal_fields`. |
| N5 | Non-string values (e.g. a JSON number) are passed through untouched — already numeric, nothing to normalize. |
| N6 | All fields are processed; errors accumulate rather than short-circuiting, so the user sees every bad field at once. |
| N7 | The returned dict is empty when everything is valid, so `if errors:` is the test. |

## Subclass override — `TransactionFormHandler`

Budget split amounts arrive as a nested `{budget_id: amount}` dict, which a flat name list
cannot address:

```python
def normalize_currency(self, data):
    errors = super().normalize_currency(data)
    # normalize each value of data['budgets'], accumulating into errors['budgets']
    return errors
```

## Non-`FormHandlerView` case — `PayoffSettingsFormHandler`

`credit_payoffs.py:171` is a plain `MethodView` storing amounts in a JSON blob in
`DBSetting`. It calls `parse_currency` directly in `post()` and writes the canonical string
into the blob, returning `{'success': False, 'error_message': ...}` for a bad value.

This is normalize-on-write rather than normalize-on-read, and it matters:
`_payment_settings_dict()` (`credit_payoffs.py:137,142`) calls `Decimal(i['amount'])` while
**rendering the credit-payoff page**. A bad value stored there breaks an entire page, not
just a form submission.

## Rewritten validation helpers

| Helper | Before | After |
|--------|--------|-------|
| `_validate_decimal` | `Decimal(data[key])` in a bare `try` | `parse_currency(data[key])`; message `Invalid amount: "%s"` |
| `_validate_float` | `float(data[key])` **plus** `assert data[key].startswith('%s' % x)` — which is why `123` is rejected while `123.0` is accepted | `parse_currency(data[key])`; the round-trip assertion is removed entirely; message `Invalid number: "%s"` |
| `_validate_int` | `int()` plus `assert data[key] == '%d' % x` | **unchanged** — the assertion is correct for integers |

Removing the `startswith` assertion is safe: it existed to catch `float()` accepting things
that are not really the given number (`1e5`, `nan`, `inf`, padded strings), and
`parse_currency` rejects all of those by construction.

## Why `validate()` gets a `try`/`except`

`submit()` has been guarded since the beginning; `validate()` never was. That asymmetry
*is* the reported 500: `TransactionFormHandler.validate()` calls `Decimal(data['amount'])`
on line 280, and `Decimal('1,234.56')` raises `InvalidOperation` straight out to Flask.
Six other validators have the same shape with unguarded `float()`.

Normalization alone prevents today's known crashes; the guard is what makes FR-005 —
"never an unhandled server error" — a property of the code rather than of the current call
list. Both are implemented.
