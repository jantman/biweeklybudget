# Contract: `biweeklybudget.utils.parse_currency`

The single server-side authority for turning a user-supplied currency string into a
number. Sibling of the existing `biweeklybudget.utils.fmt_currency`.

## Signature

```python
def parse_currency(value):
    """
    :param value: the user-supplied string to parse
    :type value: str
    :return: the exact decimal value of ``value``
    :rtype: decimal.Decimal
    :raises: CurrencyParseError if ``value`` cannot be unambiguously interpreted
    """
```

```python
class CurrencyParseError(ValueError):
    """Raised when a string cannot be interpreted as a currency amount."""
```

`CurrencyParseError` subclasses `ValueError` so that callers which already catch
`ValueError` (or bare `Exception`) keep working.

## Guarantees

| # | Guarantee |
|---|-----------|
| C1 | Returns `decimal.Decimal`, never `float`. No binary floating point is used at any point. (FR-007) |
| C2 | Raises `CurrencyParseError` for every input it cannot unambiguously interpret. It never returns a guessed value, a partial parse, `0`, or `None`. (FR-004) |
| C3 | Locale behavior comes from `settings.LOCALE_NAME` and `settings.CURRENCY_CODE` at call time. No separator or symbol is hard-coded. (FR-008) |
| C4 | Idempotent through its own output: `parse_currency(str(parse_currency(x))) == parse_currency(x)` for all accepted `x`. |
| C5 | Preserves the precision given. `1.23456` → `Decimal('1.23456')`; `123` → `Decimal('123')`. No rounding, no padding to 2 places. |
| C6 | Total: for any input, it either returns a `Decimal` or raises `CurrencyParseError`. It raises no other exception type, including for `None`, numbers, or other non-string input. |

## Algorithm

Implements research R-4. Order matters.

1. Reject non-`str` input with `CurrencyParseError`.
2. Replace Unicode space variants (`U+00A0`, `U+2007`, `U+2009`, `U+202F`, tab) with ASCII
   space; strip.
3. If wrapped in `(` … `)`, strip them and record a negation.
4. **Loop until the string stops changing**: strip a leading/trailing currency symbol, a
   leading/trailing ISO currency code, or a leading `+`/`-` sign (a `-` toggles the
   negation), stripping whitespace after each removal.
   *The loop is required*: a single pass fails `-$1,234.56`, because taking the sign first
   leaves `$1,234.56`, which Babel rejects.
5. If the string is now empty, raise `CurrencyParseError`.
6. Replace remaining internal ASCII spaces with the locale's group separator.
   *Not* "delete all spaces" — that would read `1 2 3` as `123`. Rewriting to the group
   separator lets step 7's grouping validation reject it.
7. `babel.numbers.parse_decimal(s, locale=settings.LOCALE_NAME, strict=True)`.
   `strict=True` is **required**: without it Babel silently reads `10,00` as `1000` and
   `1,234,` as `1234`.
8. Apply the recorded negation; return.

Any exception from Babel is re-raised as `CurrencyParseError` with the original value in
the message.

## Behavior matrix (locale `en_US`, currency `USD`)

All rows verified against a working prototype during Phase 0.

| Input | Result | | Input | Result |
|-------|--------|-|-------|--------|
| `'123'` | `Decimal('123')` | | `'1 2 3'` | raises |
| `'123.45'` | `Decimal('123.45')` | | `'1,23,4.56'` | raises |
| `'1,234.56'` | `Decimal('1234.56')` | | `'10,00'` | raises |
| `'1 234.56'` | `Decimal('1234.56')` | | `'1,234,'` | raises |
| `'1 234.56'` | `Decimal('1234.56')` | | `',123'` | raises |
| `'$1,234.56'` | `Decimal('1234.56')` | | `'1.2.3'` | raises |
| `'$ 1,234.56'` | `Decimal('1234.56')` | | `'abc'` | raises |
| `'1,234.56 $'` | `Decimal('1234.56')` | | `''` | raises |
| `'-1,234.56'` | `Decimal('-1234.56')` | | `'   '` | raises |
| `'-$1,234.56'` | `Decimal('-1234.56')` | | `'$'` | raises |
| `'(1,234.56)'` | `Decimal('-1234.56')` | | `'5-'` | raises |
| `'($1,234.56)'` | `Decimal('-1234.56')` | | `'-(5)'` | raises |
| `'+123'` | `Decimal('123')` | | `None` | raises |
| `'  1234.56  '` | `Decimal('1234.56')` | | `123` (int) | raises |
| `'1.23456'` | `Decimal('1.23456')` | | `'1e5'` | raises |
| `'0'` | `Decimal('0')` | | `'nan'` | raises |
| `'-0.00'` | `Decimal('0.00')` | | `'inf'` | raises |

`-0.00` yielding `Decimal('0.00')` is deliberate: it compares equal to `Decimal('0')`, so
existing "amount cannot be zero" checks keep firing.

## Locale independence

With `LOCALE_NAME='de_DE'`, `CURRENCY_CODE='EUR'` (verified in prototype):

| Input | Result |
|-------|--------|
| `'1.234,56'` | `Decimal('1234.56')` |
| `'1 234,56'` | `Decimal('1234.56')` |
| `'1234,56'` | `Decimal('1234.56')` |
| `'1,234.56'` | raises |

No call site changes. This is the evidence for SC-006.
