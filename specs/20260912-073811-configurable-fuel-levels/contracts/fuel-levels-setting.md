# Contract: `FUEL_LEVELS` setting

## Settings module

```python
FUEL_LEVELS = [
    ('E', 0),
    ('1/4', 25),
    ('1/2', 50),
    ('3/4', 75),
    ('F', 100),
]
```

Any sequence of 2-item lists or tuples is accepted; it is normalised to a list of
`(label, percentage)` tuples. Default when unset:

```python
[('0/10', 0), ('1/10', 10), ('2/10', 20), ('3/10', 30), ('4/10', 40), ('5/10', 50),
 ('6/10', 60), ('7/10', 70), ('8/10', 80), ('9/10', 90), ('10/10', 100)]
```

## Environment variable (overrides the settings module)

```text
FUEL_LEVELS=E:0,1/4:25,1/2:50,3/4:75,F:100
```

- Entries are separated by `,`. Each entry is `label:percentage`, split on its last `:`.
- Whitespace around labels and percentages is ignored.
- The percentage must be digits only.
- Labels given this way cannot contain `,`.

## Validation (either source)

At import, `biweeklybudget.settings` exits with
`SystemExit('ERROR: FUEL_LEVELS setting is invalid: <reason>')` if any of these hold:

| Condition | Example |
|-----------|---------|
| fewer than two levels | `F:100` |
| an entry is not a label/percentage pair | `E:0,1/2` (env); `[('E', 0, 1), …]` (module) |
| empty label | `:0,F:100` |
| percentage not an integer | `E:zero,F:100`; `('E', 0.5)`; `('E', True)` |
| percentage outside 0–100 | `E:0,F:150` |
| duplicated label | `E:0,E:50,F:100` |
| duplicated percentage | `E:0,1/2:50,half:50,F:100` |

## Fuel page (`GET /fuel`)

The page defines a JavaScript global holding the validated list as JSON arrays:

```javascript
var FUEL_LEVELS = [["E", 0], ["1/4", 25], ["1/2", 50], ["3/4", 75], ["F", 100]];
```

The Add Fuel Fill modal's `fuel_frm_level_before` and `fuel_frm_level_after` selects each
have one `<option value="{percentage}">{label}</option>` per entry, in list order, with the
label shown as literal text. `level_before` preselects the lowest percentage and
`level_after` the highest.

## Unchanged

- `POST /forms/fuel`: `level_before` and `level_after` are still integers, and are not
  checked against `FUEL_LEVELS`.
- The fuel log table and the fuel charts.
