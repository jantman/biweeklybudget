# Contract: HTTP interfaces touched by this feature

**Feature**: `specs/20260919-192038-omit-accounts-from-graphs` · **Spec**: [spec.md](../spec.md)

Three existing endpoints are affected. None is added, none is removed, and no
request or response key changes its name or type. The only behavioural change is
that one endpoint returns *fewer* series.

---

## 1. `GET /ajax/chart-data/account-balances`

Handled by `AcctBalanaceChartView`. Drives the **Account Balances** chart on the
index page.

### Request — unchanged

| Parameter | Type | Meaning |
|---|---|---|
| `days` | integer, optional | Days of history, counting back from now. `0` means all history. Absent, negative, non-integer, or above 36,500 falls back to `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` (or to all history for the too-large case). Never a 4xx. |

### Response — same shape, narrower contents

```json
{
  "data": [
    {"date": "2017-07-26", "BankOne": 12345.67, "CreditOne": -876.54},
    {"date": "2017-07-27", "BankOne": 12789.01, "CreditOne": -952.06}
  ],
  "keys": ["BankOne", "CreditOne"]
}
```

| Key | Type | Contract |
|---|---|---|
| `data` | array of objects | One object per date, ascending, no duplicates. Each has `date` (`YYYY-MM-DD`) plus one key per **charted** account name. Value is that account's balance on that date, or `null` if it had no recorded balance at or before it. A `NULL` ledger reads as `0.0`. |
| `keys` | array of strings | The **charted** account names, sorted. |

### Which accounts are charted

An Account is charted if and only if **both** hold:

1. it is active (`is_active` true) — established by issue #356;
2. it is not omitted from graphs (`omit_from_graphs` is not `True`, so `False` and
   `NULL` both qualify) — established by this feature.

An Account failing either test appears in neither `keys` nor any object in `data`.
Failing both is not an error and is not handled twice (FR-013).

### Invariants that this change must preserve

These held before and must hold after; they are what the acceptance tests assert.

| # | Invariant |
|---|---|
| C-1 | The response has exactly the keys `data` and `keys`, and nothing else (FR-017). |
| C-2 | Excluding an account changes no other account's value on any date (FR-011). |
| C-3 | The **set and order of dates is unaffected by which accounts are charted**. A date whose only balance record belongs to an excluded account is still returned, carrying the other accounts' forward-filled values. |
| C-4 | Every charted account has a continuous line: with no record inside the window it carries forward its last value from before the window, rather than reading `null` (which on a balance chart would say "emptied"). |
| C-5 | `data` never holds more than `ACCOUNT_BALANCE_CHART_MAX_POINTS` dates, and the most recent date in the window is always last. |
| C-6 | Every account name present in any `data` object is also in `keys`, and vice versa. |
| C-7 | With no charted accounts at all, `data` is `[]` and `keys` is `[]`, with status 200 — not an error. |
| C-8 | Balance records for excluded accounts are read without error and never deleted (FR-012). |

### Compatibility

Narrowing only. A caller that does not know about this feature keeps working: it
receives the same document with fewer series, exactly as it already does for
accounts the user deactivates. No version, flag or parameter is added to opt out —
an account is charted or it is not, and the user decides from the modal.

---

## 2. `POST /forms/account`

Handled by `AccountFormHandler`.

### Request — one field added

| Field | Type | Required | Meaning |
|---|---|---|---|
| `omit_from_graphs` | boolean | optional | Whether to leave this Account off charts that plot accounts. Submitted by the **Omit from graphs?** checkbox. |

All existing fields are unchanged. The value is stored verbatim; there is no
validation and no value is rejected, matching the Budget form's handling of its
identical field.

### Response — unchanged

```json
{"success": true, "success_message": "Successfully saved Account 5 in database."}
```

---

## 3. `GET /ajax/account/<int:account_id>`

Handled by `AccountAjax`, serialized by `ModelAsDict.as_dict`.

**Response**: unchanged in shape; gains an `omit_from_graphs` member alongside the
Account's other fields. It is `true`, `false`, or `null` for an Account that
predates the migration, and `null` is read as `false` by every consumer (see
[data-model.md](../data-model.md)).

---

## Not part of any contract

The Accounts page, the six account pickers, the Transactions and OFX table
filters, Cash Position, pay period pages, reconciliation, transfers, the Plaid
updater and the stale-data warnings are all untouched by this feature and must
behave identically for a flagged Account (FR-014, FR-015).
