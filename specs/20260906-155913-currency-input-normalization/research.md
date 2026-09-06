# Phase 0 Research: Currency Value Input Normalization

**Feature**: `specs/20260906-155913-currency-input-normalization`
**Date**: 2026-09-06

## R-1: Root cause of the reported 500 Internal Server Error

**Finding**: `FormHandlerView.post()`
(`biweeklybudget/flaskapp/views/formhandlerview.py:49`) wraps `self.submit(data)` in a
`try`/`except` that turns any exception into a JSON `error_message`, but calls
`self.validate(data)` **unguarded**. `TransactionFormHandler.validate()`
(`biweeklybudget/flaskapp/views/transactions.py:280`) does
`Decimal(data['amount']) == Decimal('0')` as its first numeric check. `Decimal('1,234.56')`
raises `decimal.InvalidOperation`, which propagates out of `post()` and Flask renders a 500.

The same shape exists in six other validators, which call `float(data['amount'])`
unguarded: `accounts.py:340,343`, `budgets.py:271,274`, `payperiods.py:256`,
`scheduled.py:231`, plus `transactions.py:293,317,320` for budget-split amounts.

**Decision**: Two independent fixes, both required.
1. Normalize currency values into a canonical numeric string *before* `validate()` is
   called, so the raw user string never reaches a bare `Decimal()`/`float()`.
2. Wrap `validate()` in the same `try`/`except` that already guards `submit()`, so a
   future unguarded conversion degrades to a form error rather than a 500.

**Rationale**: (1) alone leaves the 500 class of bug one careless line away from
returning; (2) alone would turn the reported crash into an unhelpful error banner rather
than accepting the value the user typed. FR-005 requires "never an unhandled server
error", which only (2) can guarantee.

**Alternatives considered**: A Flask `errorhandler(500)` returning JSON — rejected: it
hides genuine server bugs behind a form-shaped response across the whole app, and the
constitution's financial-correctness stance argues for failing loudly everywhere except
the one path we have deliberately reasoned about.

---

## R-2: Root cause of the "bare integer rejected" defect

**Finding**: `FormHandlerView._validate_float()`
(`formhandlerview.py:120`) asserts `data[key].startswith('%s' % x)` after `x = float(...)`.
For input `123`, `x` is `123.0` and `'123'.startswith('123.0')` is `False`, so the field
is rejected with `Invalid float value: "123"`. Any whole number is rejected; `123.0` is
required. This helper guards BoM Item `unit_cost` (`projects.py:423`) and the four Fuel
Log numeric fields (`fuel.py:290-293`).

`_validate_int()` has the analogous `assert data[key] == '%d' % x`, which is correct for
integers and stays as-is.

**Decision**: Reimplement `_validate_float()` on top of the new parser; drop the
`startswith` round-trip assertion entirely.

**Rationale**: The assertion was trying to catch "`float()` silently accepted something
that isn't really this number" — `float('1e5')`, `float('nan')`, `float('  1  ')`. The new
parser rejects those cases outright and by construction, so the assertion is dead weight
that only produces false rejections.

**Alternatives considered**: Loosening the assertion to `float(data[key]) == x` — rejected
as tautological, and it would still leave `nan`/`inf` accepted.

---

## R-3: Server-side parsing library

**Decision**: Use `babel.numbers.parse_decimal(value, locale=..., strict=True)` as the
parsing core, wrapped in a project function that pre-cleans the input.

**Rationale**:
- Babel 2.18.0 is **already a direct dependency** (`requirements.txt:13`) and already
  supplies this project's currency *formatting* (`biweeklybudget/utils.py:90`
  `fmt_currency` → `babel.numbers.format_currency`). Parsing with the same library against
  the same `settings.LOCALE_NAME` makes round-tripping consistent by construction, and adds
  zero dependencies (AGPL-compatibility question does not arise).
- It returns an exact `Decimal`, satisfying FR-007 (no binary float rounding).
- `strict=True` rejects ambiguous grouping — verified empirically:

  | Input | `strict=False` | `strict=True` |
  |-------|----------------|---------------|
  | `1,234.56` | `1234.56` | `1234.56` |
  | `1,23,4.56` | `1234.56` (silently!) | rejected |
  | `10,00` | `1000` (silently!) | rejected |
  | `1,234,` | `1234` (silently!) | rejected |
  | `,123` | `123` (silently!) | rejected |

  The `strict=False` column is exactly the silent-corruption failure mode User Story 4 and
  FR-004 exist to prevent. **`strict=True` is non-negotiable here.**
- It is locale-parameterized, which is how FR-008 / SC-006 are met: the same call works for
  `de_DE` (`1.234,56` → `1234.56`) with no code change.

**Alternatives considered**:
- Hand-rolled regex — rejected: reimplements grouping validation this project would then
  own and get wrong, and hard-codes US conventions against the explicit i18n requirement.
- `locale.atof` — rejected: depends on process-global locale state, returns a float (loses
  cents), and requires the locale to be installed in the OS.
- `Decimal(value.replace(',', ''))` — rejected: this *is* the `strict=False` column above;
  it turns `10,00` into 1000.

---

## R-4: What Babel does not handle, and the pre-clean rules

Babel's `parse_decimal` rejects the currency symbol, spaces-as-separators, and
parentheses-negatives — all three named in FR-003. A pre-clean step handles them, then
hands a Babel-parseable string to `parse_decimal(strict=True)`.

**Decision** — pre-clean, in this order:

1. Normalize all Unicode space variants (`U+00A0` NBSP, `U+2009` thin, `U+202F` narrow
   NBSP, `U+2007` figure space, tab) to ASCII space, then strip leading/trailing whitespace.
2. If the value is wrapped in `(` … `)`, remove them and record a negation.
3. Repeatedly strip a leading/trailing currency symbol (from
   `babel.numbers.get_currency_symbol(settings.CURRENCY_CODE, settings.LOCALE_NAME)`), the
   ISO code itself, and a leading `+`/`-` sign, until the string stops changing. Looping is
   required so that `-$1,234.56` works: a single pass that takes the sign first leaves
   `$1,234.56`, which Babel rejects. **This was found by prototyping — a single-pass
   implementation fails this exact case.**
4. Replace the remaining internal ASCII spaces with the locale's group separator
   (`Locale.parse(...).number_symbols['latn']['group']`), then hand to Babel.
5. An empty string at this point is an error, not zero.

**Rationale for step 4** (the non-obvious one): the naive reading of "accept spaces as
separators" is "delete all spaces", which turns `1 2 3` into `123` — a number the user
plainly did not type. Rewriting spaces *into* the locale's group separator instead means
Babel's `strict=True` grouping validation applies to space-separated input too: `1 234.56`
→ `1,234.56` → `1234.56`, while `1 2 3` → `1,2,3` → rejected. One rule, both behaviors,
and it is automatically correct for locales where space *is* the group separator.

**Verified prototype results** (locale `en_US`, currency `USD`):

| Input | Result | | Input | Result |
|-------|--------|-|-------|--------|
| `123` | `123` | | `1 2 3` | rejected |
| `123.45` | `123.45` | | `1,23,4.56` | rejected |
| `1,234.56` | `1234.56` | | `1.2.3` | rejected |
| `1 234.56` | `1234.56` | | `abc` | rejected |
| `$1,234.56` | `1234.56` | | `` (empty) | rejected |
| `$ 1,234.56` | `1234.56` | | `$` | rejected |
| `-$1,234.56` | `-1234.56` | | `1,234,` | rejected |
| `(1,234.56)` | `-1234.56` | | `5-` | rejected |
| `($1,234.56)` | `-1234.56` | | `-(5)` | rejected |
| `+123` | `123` | | `1.23456` | `1.23456` |
| `-0.00` | `0.00` | | ` 1 234.56 ` | `1234.56` |

`-0.00` parsing to `Decimal('0.00')` is correct and required: it compares equal to
`Decimal('0')`, so existing "amount cannot be zero" checks keep firing (spec edge case).

`de_DE` spot-check confirms locale independence: `1.234,56` → `1234.56`,
`1 234,56` → `1234.56`, `1,234.56` → rejected.

---

## R-5: Where server-side normalization happens ("as few places as possible")

**Finding**: There are 30+ sites that convert a form string to a number, split across
`validate()` and `submit()` in 13 form handlers. Normalizing at each site would be 30 edits
and 30 chances to miss one — the opposite of what the issue asks for.

**Decision**: Normalize **once**, in `FormHandlerView.post()`, before `validate()` runs.
`FormHandlerView` gains a `currency_fields` class attribute (a list of field names); each
handler subclass declares its own. `post()` walks that list, replaces each present,
non-blank value in `data` with its canonical string form, and collects a per-field error
for any value that will not parse — returning those errors as a normal form-validation
response without ever calling `validate()`.

**Consequences**: every existing `Decimal(data['amount'])` and `float(data['amount'])` in
both `validate()` and `submit()` keeps working unchanged, because by the time it runs the
string is already canonical. The change is one method plus one declarative line per
handler, and a reviewer can enumerate every currency field by grepping `currency_fields`
(SC-005).

**Blank values are left untouched**, so each field's existing "blank means zero" /
"blank is an error" / "blank means omit" semantics are preserved exactly (spec Assumptions).

**Two cases do not fit the flat list**, and are handled explicitly:
- `TransactionFormHandler` — budget split amounts arrive as a `budgets` dict of
  `{budget_id: amount}`. The handler overrides the normalization hook to call `super()`
  and then normalize the dict's values.
- `PayoffSettingsFormHandler` (`credit_payoffs.py:171`) is a plain `MethodView`, not a
  `FormHandlerView`, and stores its amounts as a JSON blob in `DBSetting`. It normalizes
  on the way in, so the stored blob is always canonical. This matters more than it looks:
  `_payment_settings_dict()` (`credit_payoffs.py:137,142`) calls `Decimal(i['amount'])`
  while *rendering the credit-payoff page*, so a bad stored value breaks a whole page,
  not just a form.

**Alternatives considered**:
- A custom `CurrencyField` type / WTForms-style form layer — rejected: the project has no
  form-object layer, and introducing one is a far larger change than the issue warrants
  (constitution: complexity must be justified).
- Normalizing in the browser only, submitting canonical values — rejected outright: it
  leaves every endpoint crashable by any non-browser client, and FR-005/edge cases require
  server-side handling.

---

## R-6: Client-side mirror

**Finding**: The browser converts currency strings to numbers in exactly one file:
`transactions_modal.js`, at `validateTransModalSplits()` (lines 265, 268) and
`transModalSplitBudgetChanged()` (lines 339, 343), all via `parseFloat()`. `parseFloat`
truncates at the first comma — `parseFloat('1,234.56')` is `1`. So a user entering
`1,234.56` in a split transaction is told the allocations do not sum, and Save is
disabled; the server fix alone would never be reachable in that flow (User Story 5).

**Decision**: Add `parse_currency(value)` to `biweeklybudget/flaskapp/static/js/custom.js`
as the sibling of the existing `fmt_currency(value)`, returning `null` for input it cannot
interpret. Replace all four `parseFloat` calls with it. Separators are discovered from
`Intl.NumberFormat(LOCALE_NAME).formatToParts(...)` rather than hard-coded, mirroring the
server's locale parameterization.

**Rationale for `custom.js`**: it is already loaded on every page by `base.html`, already
holds the formatting counterpart, and already receives `LOCALE_NAME` / `CURRENCY_CODE` /
`CURRENCY_SYMBOL` as globals from the template. No new file, no new `<script>` tag, and
`docs/make_jsdoc.py` auto-discovers the file so documentation regenerates for free.

**Verification**: this repository has no JavaScript unit-test harness, and introducing one
is out of scope. The JS parser is therefore verified through the Selenium acceptance tests
that the issue explicitly asks for — which is the stronger test anyway, since it exercises
the real page.

---

## R-7: Error message wording (FR-012)

**Decision**: Replace `Invalid float value: "%s"` / `Invalid Decimal value: "%s"` with
`Invalid amount: "%s"` for currency fields and `Invalid number: "%s"` for the non-currency
numeric fields (fuel gallons, reported MPG).

**Rationale**: "float" and "Decimal" are Python type names leaking into a user-facing
message. Existing acceptance tests assert on the old strings and must be updated in the
same change.

---

## R-8: Scope of non-currency numeric fields

**Finding**: Fuel Log `gallons` and `reported_mpg` are not currency, but they are validated
by the same `_validate_float` whose `startswith` assertion causes the bare-integer defect.
Entering `10` gallons is rejected today.

**Decision**: In scope for the bare-integer fix. They go through the same parser (a stray
currency symbol on a gallons field is harmless to accept) but are declared separately from
`currency_fields` so the distinction stays visible, and they get the "number" rather than
"amount" error wording.

---

## R-9: Testing approach

**Decision**:
- **Unit tests** (`biweeklybudget/tests/unit/test_utils.py`) — table-driven over the
  accept/reject matrix in R-4, plus a `de_DE` case proving locale parameterization
  (SC-006) and a `Decimal`-identity case proving no float rounding (FR-007).
- **Unit tests** for the `FormHandlerView` normalization hook, using a stub subclass:
  canonicalization, blank pass-through, error collection, and that `validate()` is not
  called when normalization fails.
- **Acceptance (browser) tests** — required by the issue and FR-011. One
  separator-formatted round trip per form covering the FR-009 inventory; plus, on the
  Transaction modal, a bare-integer case, a malformed-input case asserting a field error
  and no 500 and no new DB row, and a budget-split case exercising the client-side parser
  (User Story 5).

**Rationale**: The unit tests pin the parser's exact semantics cheaply; the browser tests
prove the wiring, which is where this feature can actually still be broken. The
constitution's Test Gate requires the full unit and acceptance suites to pass before the
feature is complete.

**Existing tests to update**: acceptance tests asserting the old `Invalid float value:` /
`Invalid Decimal value:` message text.

---

## R-10: Schema, version, and documentation obligations

- **Schema**: no model changes, so no Alembic migration (constitution III does not apply).
  The `migrations` tox env should still pass untouched.
- **Version**: `biweeklybudget/version.py` is at `1.6.2`. This adds user-visible accepted
  behavior beyond a pure bug fix, so **1.7.0** per SemVer, with a matching `CHANGES.rst`
  entry (constitution VI).
- **Docs** (constitution IV): `docs/source/app_usage.rst` has a localization section that
  documents currency *formatting*; it gains a subsection documenting accepted *input*
  formats. `biweeklybudget.utils.rst` regenerates via `sphinx-apidoc -f` in `tox -e docs`.
  `jsdoc.custom.rst` regenerates via `tox -e jsdoc`; `node` and `jsdoc` are present on this
  machine, so the regenerated file is committed rather than hand-written.

---

## Unresolved

None. No `NEEDS CLARIFICATION` items remain from Technical Context.
