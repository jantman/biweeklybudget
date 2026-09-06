# Contract: `parse_currency(value)` in `static/js/custom.js`

The browser mirror of `biweeklybudget.utils.parse_currency`. Sibling of the existing
`fmt_currency(value)` in the same file.

## Signature

```javascript
/**
 * Parse a user-entered currency string to a Number, or null if it cannot be
 * interpreted. Mirrors biweeklybudget.utils.parse_currency() on the server.
 *
 * @param {string} value - the string to parse
 * @returns {(number|null)} the numeric value, or null if not interpretable
 */
function parse_currency(value)
```

## Guarantees

| # | Guarantee |
|---|-----------|
| J1 | Returns `null` — not `NaN`, not `0` — for anything it cannot interpret. Every call site tests for `null` explicitly. |
| J2 | Accepts every form the server accepts, and rejects every form the server rejects, for the locale in force. The server remains the authority; the client must never be *stricter*, or it would block a submission the server would have accepted. |
| J3 | Separators come from `Intl.NumberFormat(LOCALE_NAME)` and the symbol from the `CURRENCY_SYMBOL` global, both already set by `base.html`. Nothing is hard-coded. |
| J4 | Returns a JavaScript `Number`. Precision loss is acceptable here and only here: this value feeds on-screen validation feedback, never storage. The server re-parses to an exact `Decimal`. |

## Why `null` and not `NaN`

`parseFloat` returns `NaN`, and `NaN`-based comparisons silently evaluate false, which is
how the existing split-transaction check can disable Save with no visible reason. An
explicit `null` forces each call site to decide what an unparseable field means.

## Placement

`custom.js`, because:

- It already holds `fmt_currency`, the formatting counterpart — the pair stays together.
- `base.html` already loads it on every page, so no new `<script>` tag is needed.
- `LOCALE_NAME`, `CURRENCY_CODE`, and `CURRENCY_SYMBOL` are already in scope there.
- `docs/make_jsdoc.py` auto-discovers files in the JS directory, so `jsdoc.custom.rst`
  regenerates with no manual doc wiring.

## Call sites replaced

All four `parseFloat` uses in `biweeklybudget/flaskapp/static/js/transactions_modal.js`:

| Location | Current | Change |
|----------|---------|--------|
| `validateTransModalSplits()` line 265 | `parseFloat($('#trans_frm_budget_amount_' + rownum).val())` | `parse_currency(...)`; a `null` allocation makes the form report an invalid amount rather than summing `NaN` |
| `validateTransModalSplits()` line 268 | `parseFloat($('#trans_frm_amount').val())` | `parse_currency(...)`; a `null` transaction amount suppresses the mismatch message instead of showing `NaN` — the server will produce the real field error |
| `transModalSplitBudgetChanged()` line 339 | `parseFloat($('#trans_frm_amount').val())` | `parse_currency(...)`; skip the remainder auto-fill when `null` |
| `transModalSplitBudgetChanged()` line 343 | `parseFloat($('#trans_frm_budget_amount_' + rownum).val())` | `parse_currency(...)`; treat `null` as "not yet a number" and skip |

**Why this matters**: `parseFloat('1,234.56')` is `1`. Today a split transaction for
`1,234.56` reports "Sum of budget allocations (1234.5600) must equal transaction amount
(1.0000)" and disables Save, so the user cannot even reach the server. This is User
Story 5.

## Verification

This repository has no JavaScript unit-test harness, and adding one is out of scope. The
contract is verified through Selenium acceptance tests that drive the real Transaction
modal — which is the stronger check, since it exercises the actual page wiring rather
than the function in isolation.
