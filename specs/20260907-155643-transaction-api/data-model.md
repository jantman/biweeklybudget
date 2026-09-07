# Phase 1 Data Model: Transaction API — Name-or-ID Lookup

**No schema change.** No model class, table, column, index or constraint is added,
removed or altered, and no Alembic migration is required. This document describes the
existing entities as they are *addressed* by the amended endpoint, and the resolution
rules that govern that addressing.

## Entities involved

### Account (`biweeklybudget.models.account.Account`)

| Attribute | Type | Relevance |
|-----------|------|-----------|
| `id` | Integer, primary key | Accepted today as the value of `account` and `credit_payment_acct`. |
| `name` | `String(50)`, **unique**, indexed | Newly accepted as the value of those same fields. Uniqueness is what makes a name an unambiguous identifier. |
| `acct_type` | `AcctType` enum | Unchanged rule: only `AcctType.Credit` accounts may be the target of `credit_payment_acct`. Enforced after resolution, so it applies identically whether the account arrived as a name or an ID. |

### Budget (`biweeklybudget.models.budget_model.Budget`)

| Attribute | Type | Relevance |
|-----------|------|-----------|
| `id` | Integer, primary key | Accepted today as each key of the `budgets` mapping. |
| `name` | `String(50)`, **unique**, indexed | Newly accepted as those keys. |
| `is_active` | Boolean | Unchanged rule: a new Transaction may not use an inactive Budget, and an existing Transaction may not be changed onto one it does not already use. Enforced after resolution. |
| `is_income` | Boolean | Affects only the web UI's display label `"<name> (income)"`. **Not** part of the name; see resolution rules below. |

### Transaction (`biweeklybudget.models.transaction.Transaction`)

The record created or updated. Unchanged. Its `account_id`, `credit_payment_acct_id` and
its `BudgetTransaction` rows are populated from the *resolved* IDs, so the persisted data
is identical whether the request named records by ID or by name.

## Resolution rules

These apply uniformly to every identifying field on `POST /forms/transaction`.

**R1 — Normalize.** Coerce the supplied value to a string and strip leading and trailing
whitespace. An empty result, or `None`, is not a reference; it is handled by the field's
existing "absent" behaviour (an error for `account`, "not a credit card payment" for
`credit_payment_acct`).

**R2 — Digits first.** If the stripped value consists only of ASCII digits, look the record
up by primary key. If a record is found, that is the answer.

**R3 — Name fallback.** Otherwise — a non-digit value, or a digit value that matched no
primary key — look the record up by name: whole-string equality against `name`, compared
case-insensitively via `func.lower()` on both sides. Because `name` is unique, this yields
at most one record.

**R4 — Miss.** If neither step finds a record, resolution fails. The field gets a
validation error quoting the value as supplied, and no Transaction is created or modified.

**R5 — No partial application.** Resolution failures are accumulated across all fields and
returned together, exactly as the handler already accumulates its other validation errors.
The request is rejected as a whole.

**R6 — Canonicalization.** On success the submitted data is rewritten in place so that
every identifying value is the numeric ID as a string, and the `budgets` mapping is rekeyed
by numeric ID. Everything downstream — every pre-existing validation rule, and `submit()` —
therefore operates on IDs and is not modified by this feature.

**R7 — Duplicate references.** Because two distinct keys of `budgets` can resolve to the
same Budget (`"7"` and `"Groceries"`, say), rekeying could silently discard one allocation
and produce a Transaction whose budget amounts no longer sum to its amount. A `budgets`
mapping in which two keys resolve to the same Budget is therefore rejected with a
validation error naming that Budget. This is a **new** error condition with no ID-only
equivalent, because before this feature two keys could not name one record.

### Worked examples

Given Account 1 named `CHASE`, Budget 7 named `Groceries` (active), Budget 9 named `2024`:

| Supplied value | Resolves to | By which rule |
|----------------|-------------|---------------|
| `"1"` | Account 1 | R2 |
| `"CHASE"` | Account 1 | R3 |
| `"  chase "` | Account 1 | R1 then R3 |
| `"Groceries"` | Budget 7 | R3 |
| `"7"` | Budget 7 | R2 |
| `"9"` | Budget 9 | R2 (matches by ID) |
| `"2024"` | Budget 9 | R2 finds no Budget 2024, R3 matches the name |
| `"Grocery"` | *error* | R4 — exact matching only |
| `"Groceries (income)"` | *error* | R4 — the suffix is a UI label, not the name |
| `{"7": "5.00", "Groceries": "5.00"}` | *error* | R7 — both keys are Budget 7 |

## Field-by-field effect on `POST /forms/transaction`

| Field | Before | After |
|-------|--------|-------|
| `account` | Account ID | Account ID **or** name (R1–R4) |
| `budgets` keys | Budget IDs | Budget IDs **or** names (R1–R4, R7) |
| `credit_payment_acct` | Account ID, or absent/`"None"`/`""` | Account ID **or** name, or absent/`"None"`/`""` unchanged |
| `id`, `description`, `amount`, `date`, `notes`, `sales_tax`, `no_budget_impact` | — | Unchanged |

`id` is deliberately **not** given name resolution: a Transaction has no name, and the
field is a Transaction ID.
