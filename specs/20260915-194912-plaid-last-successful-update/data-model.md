# Phase 1 Data Model: Plaid Item Last Successful Update Time

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Date**: 2026-09-15

## Entity: PlaidItem

`biweeklybudget/models/plaid_items.py` — table `plaid_items`. One row per linked financial
institution connection.

### Change

One column is added. Nothing else about the entity changes: no existing column is altered or
removed, no relationship changes, and the primary key is untouched.

| Attribute | Type | Nullable | New? | Meaning |
|-----------|------|----------|------|---------|
| `item_id` | `String(70)`, PK | no | | Plaid's Item identifier |
| `access_token` | `String(70)` | yes | | Plaid access token for this Item |
| `institution_name` | `String(100)` | yes | | Institution display name |
| `institution_id` | `String(50)` | yes | | Plaid institution identifier |
| `last_updated` | `UtcDateTime` | yes | | When **this application** last polled the Item |
| **`last_successful_update`** | **`UtcDateTime`** | **yes** | **yes** | **When *Plaid* last successfully updated this Item's transactions, as reported by Plaid** |

### Why nullable

Three distinct situations produce no value, and all are normal (FR-004, FR-010):

1. An Item that existed before this change and has not been updated since.
2. A newly linked Item that Plaid has not yet refreshed.
3. An Item Plaid has never managed to refresh, for which Plaid reports the field as absent.

No default or sentinel can represent these honestly, so the column is nullable and the UI
renders a placeholder for it (FR-008).

### Why `UtcDateTime` and not plain `DateTime`

`sqlalchemy_utc.UtcDateTime` is what `last_updated` already uses. It rejects naive datetimes
outright and normalises everything else to UTC on the way in and out, which is what FR-009
asks for: the two timestamps in the same table row must be comparable without the reader
having to reason about zones. Using the same type also keeps the new column's rendering in
the Alembic migration identical in form to the existing one, which is what the `migrations`
suite's head-versus-models check compares.

### Writes

| Writer | When | Value written |
|--------|------|---------------|
| `PlaidUpdater._do_item` | Every transaction download for the Item | The time from that download's `item_get` response, or `None` if Plaid reported none |
| `PlaidUpdateItemInfo.post` | "Update Item Information from Plaid" | The time from that refresh's `item_get` response, or `None` if Plaid reported none |

Both writers already load the `PlaidItem`, mutate it, `db_session.add()` it and commit, so the
new assignment joins existing writes rather than adding a transaction.

Neither writer is reached when the `item_get` call itself fails: `_do_item` falls into its
`except Exception` handler and never commits, and `PlaidUpdateItemInfo` returns HTTP 400 on
`ApiException` without committing. The previously stored value therefore survives a failed
attempt with no extra code (FR-005).

### Reads

| Reader | Use |
|--------|-----|
| `plaid_form.html`, Plaid Items table | Rendered relative ("3 days ago") beside "Last Polled"; `unknown` when null |

`PlaidItem` extends `ModelAsDict`, so the new column appears automatically in `as_dict()`
output wherever that is already used. That is a consequence of the model change, not a new
interface.

## No other entities change

`PlaidAccount`, `Account`, `OFXStatement` and `OFXTransaction` are untouched.
