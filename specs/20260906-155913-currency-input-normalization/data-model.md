# Phase 1 Data Model: Currency Value Input Normalization

**Feature**: `specs/20260906-155913-currency-input-normalization`

This feature introduces **no database entities and no schema change**. `biweeklybudget/models/`
is untouched, so no Alembic migration is required (constitution III). What follows are the
in-memory value shapes the feature introduces, and the authoritative inventory of the
fields it governs.

## Value shapes

### Raw currency input

The string as submitted, straight from `request.get_json()` or `request.form`.

| Property | Value |
|----------|-------|
| Type | `str` (never trusted to be numeric) |
| Source | Browser form field, or any HTTP client posting to a `/forms/*` endpoint |
| Lifetime | Replaced in-place inside `data` by the canonical form before `validate()` runs |
| Blank | `''` or whitespace-only is **not** an error at the normalization layer; it is passed through untouched so each field's existing blank semantics still apply |

### Canonical currency value

| Property | Value |
|----------|-------|
| Type | `decimal.Decimal` (exact; never `float`) |
| String form | `str(Decimal)` — plain digits, optional `-`, optional `.` fraction. No grouping separators, no currency symbol, no whitespace. |
| Precision | Whatever the input carried. Normalization neither rounds nor pads: `1.23456` stays `1.23456`, `123` stays `123`. Rounding, where it happens, remains the responsibility of the model column, exactly as today. |
| Guarantee | `parse_currency(str(parse_currency(x))) == parse_currency(x)` for every accepted `x` |

Storing the canonical **string** back into `data` (rather than the `Decimal`) is what lets
every existing `Decimal(data['amount'])` and `float(data['amount'])` call downstream keep
working with no edit.

### Parse failure

| Property | Value |
|----------|-------|
| Type | `CurrencyParseError`, a subclass of `ValueError` |
| Raised for | Unparseable text, ambiguous grouping, empty-after-cleaning input, non-`str` input |
| Never | Returns a partial parse, a guessed value, `0`, or `None` in the Python API (FR-004) |
| Browser counterpart | JS `parse_currency()` returns `null` — JS has no exception idiom here, and every call site is a truthiness check |

### Locale conventions

Not a stored object — a set of lookups performed per call, so a settings change takes
effect with no code change (FR-008, SC-006).

| Convention | Server source | Browser source |
|------------|---------------|----------------|
| Decimal separator | `babel` CLDR data for `settings.LOCALE_NAME` | `Intl.NumberFormat(LOCALE_NAME).formatToParts()` |
| Group separator | `Locale.parse(LOCALE_NAME).number_symbols['latn']['group']` | `Intl.NumberFormat(LOCALE_NAME).formatToParts()` |
| Currency symbol | `get_currency_symbol(settings.CURRENCY_CODE, settings.LOCALE_NAME)` | `CURRENCY_SYMBOL` global from `base.html` |
| Grouping validity | `parse_decimal(..., strict=True)` | Mirrored check in `custom.js` |

## Field inventory

The authoritative expansion of **FR-009**. Each row becomes one `currency_fields` /
`decimal_fields` entry, and each form gets acceptance coverage.

### Currency fields (`currency_fields`)

| Form / page | Handler | Field name(s) | Notes |
|-------------|---------|---------------|-------|
| Transaction modal | `TransactionFormHandler` (`transactions.py:256`) | `amount`, `sales_tax` | Site of the reported 500 |
| Transaction modal — budget splits | `TransactionFormHandler` | values of the `budgets` dict | Nested; needs the hook override |
| Scheduled Transaction modal | `SchedTransFormHandler` (`scheduled.py:211`) | `amount`, `sales_tax` | |
| Pay period → convert scheduled txn | `SchedToTransFormHandler` (`payperiods.py:231`) | `amount`, `sales_tax` | |
| Pay period → skip scheduled txn | `SkipSchedTransFormHandler` (`payperiods.py:302`) | `amount` | |
| Budget modal | `BudgetFormHandler` (`budgets.py:168`) | `starting_balance`, `current_balance` | Blank is meaningful — one or the other is required depending on `is_periodic` |
| Budget transfer modal | `BudgetTxfrFormHandler` (`budgets.py:243`) | `amount` | |
| Account modal | `AccountFormHandler` (`accounts.py:165`) | `credit_limit`, `apr`, `prime_rate_margin` | All three optional/blank-allowed. `apr` and `prime_rate_margin` are rates, not money, but are entered in the same shape and validated by `_validate_decimal` today; the existing ">1 means percent, divide by 100" logic in `submit()` is unchanged |
| Account transfer modal | `AccountTxfrFormHandler` (`accounts.py:312`) | `amount` | |
| Fuel Log modal | `FuelLogFormHandler` (`fuel.py:263`) | `cost_per_gallon`, `total_cost` | |
| BoM Item modal | `BoMItemFormHandler` (`projects.py:400`) | `unit_cost` | |
| Credit payoff — OFX interest | `AccountOfxFormHandler` (`credit_payoffs.py:243`) | `interest_amt` | `validate()` is currently a bare `pass` |
| Credit payoff — settings | `PayoffSettingsFormHandler` (`credit_payoffs.py:171`) | `amount` within each `increases[]` / `onetimes[]` entry | Plain `MethodView`, not a `FormHandlerView`. Normalized before the JSON blob is stored, because `_payment_settings_dict()` re-parses it while *rendering the page* — a bad stored value breaks the whole credit-payoff page |

### Non-currency decimal fields (`decimal_fields`)

Same parser, "number" rather than "amount" error wording (research R-8).

| Form | Handler | Field name(s) | Why in scope |
|------|---------|---------------|--------------|
| Fuel Log modal | `FuelLogFormHandler` (`fuel.py:263`) | `gallons`, `reported_mpg` | Validated by the same `_validate_float` whose assertion rejects bare integers; entering `10` gallons fails today |

### Explicitly out of scope

- **Integer fields** — `quantity`, `odometer_miles`, `reported_miles`, `level_before`,
  `level_after`, and all record IDs. `_validate_int`'s round-trip assertion is correct for
  integers and stays as-is.
- **Display formatting** — `fmt_currency` on both sides is already correct and unchanged.
- **Read paths** — OFX/Plaid import, reconciliation, and payoff arithmetic consume values
  that are already `Decimal`s from the database; they never see a user-typed string.

## Validation rules

Derived from FR-003 (accept) and FR-004 (reject); the full verified matrix is in
[research.md](./research.md) R-4.

**Accepted** (locale `en_US`): bare integers; decimals; `,` grouping; space grouping
(including NBSP and other Unicode spaces); leading or trailing currency symbol or ISO
code, with or without an intervening space; leading `+` or `-`; parentheses for negative;
any combination of the above; surrounding whitespace.

**Rejected**: anything non-numeric; multiple decimal separators; invalid grouping
(`10,00`, `1,23,4.56`, `1,234,`, `,123`); space-separated digit runs that are not valid
groups (`1 2 3`); trailing signs (`5-`); empty or symbol-only input; non-string input.

**Invariants**:
- Rejection is always distinguishable from success — never a guessed value (FR-004).
- Accepted input is never rejected by a later step: normalization runs *before*
  `validate()`, and produces a string that every downstream `Decimal()`/`float()` accepts.
- Nothing valid today becomes invalid (FR-010).
