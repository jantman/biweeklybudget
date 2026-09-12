# Data Model: Configurable Fuel Levels

No database change. No model, column, or migration is added or altered.

## Fuel level option (setting, not stored)

One entry of `settings.FUEL_LEVELS`.

| Field | Type | Rules |
|-------|------|-------|
| label | string | Non-empty after stripping whitespace; unique within the list. Displayed literally. |
| percentage | integer | Whole number 0–100 (a `bool` is not accepted); unique within the list. |

The list:

- is ordered, and has at least two entries;
- is shown on the form in its configured order;
- defaults to `0/10`→0, `1/10`→10 … `10/10`→100.

The form's defaults are derived from the list, not configured separately. The starting
level is the entry with the lowest percentage and the ending level the entry with the
highest.

## FuelFill (existing, unchanged)

`level_before` and `level_after` stay `SmallInteger` columns holding a percentage of a full
tank. A saved value is the `percentage` of the option chosen. Existing rows are not
touched, and are displayed as percentages as before.
