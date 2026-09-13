# Data Model: Plaid Update Check All / Uncheck All

No persistent data changes. No model, table, column, or migration is added or changed.

The only state involved is transient and client-side: the checked/unchecked state of
each Plaid Item checkbox on the Plaid Update page.

| State | Initial value | Changed by | Persisted |
|-------|---------------|-----------|-----------|
| Item checkbox `item_<item_id>` checked | checked (unchanged) | the operator, **Check All** (→ checked), **Uncheck All** (→ unchecked) | No; a reload restores all checked |

On submit, each checked box posts `item_<item_id>=1`; unchecked boxes post nothing. The
existing `/plaid-update` POST handler turns the posted keys into the list of Items to
update (unchanged).
