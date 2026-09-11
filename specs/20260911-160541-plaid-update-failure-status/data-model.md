# Data Model: Plaid Update Reports Failure In Its Status Code

No persistent data changes: no model, table, column, or migration.

## PlaidUpdateResult (existing, unchanged)

Defined in `biweeklybudget/plaid_updater.py`. One per requested Plaid Item, returned by
`PlaidUpdater.update()`.

| Field | Meaning |
|-------|---------|
| `item` | the `PlaidItem` updated |
| `success` | `True` if the Item updated without error |
| `updated` / `added` | transaction counts (0 on failure) |
| `exc` | the exception caught on failure, else `None` |
| `stmt_ids` | IDs of statements created (`None` on failure) |

## Derived value: response status

```text
status = 500  if any result has success == False
       = 200  otherwise (including when there are no results)
```

Computed per request in `PlaidUpdate._update()` and never stored.
