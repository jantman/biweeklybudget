# Research: Configurable Fuel Levels

All Technical Context items were known from the code; there were no NEEDS CLARIFICATION
markers. This file records the design decisions and the alternatives rejected.

## R1. Where the option list lives today

**Finding**: The eleven options exist in exactly one place, as two identical object
literals in `fuelModalDivForm()` in `biweeklybudget/flaskapp/static/js/fuel.js`, passed to
`FormBuilder.addLabelToValueSelect()` with defaults `0` (before) and `100` (after). The
server (`FuelFormHandler` in `flaskapp/views/fuel.py`) only checks that each level is an
integer. The model (`FuelFill.level_before`/`level_after`) is a `SmallInteger` documented as
a percentage 0–100. Nothing computes with the levels (no MPG or chart code reads them); the
fuel log table renders them as `N%`.

**Consequence**: The change is a new setting, a template line to expose it, and a JS change.
No model, migration, or form-handler change is needed.

## R2. Setting shape: ordered list of `(label, percentage)` pairs

**Decision**: `settings.FUEL_LEVELS`, a list of 2-item `(label, percentage)` sequences,
defaulting to `[('0/10', 0), ('1/10', 10), … ('10/10', 100)]`.

**Rationale**: A list keeps the configured order (spec FR-004) and allows any labels.
Pairing each label with a percentage keeps the stored meaning of a level unchanged
(FR-006), so old and new fills stay comparable.

**Alternatives rejected**:
- *A `dict` of label → percentage*: order is preserved in Python, but once serialised to a
  JavaScript object, integer-like keys (`"0"`, `"1"` … for a bar gauge) are re-ordered
  ahead of the others. A list of pairs has no such trap.
- *A number of divisions (e.g. `8` for eighths)*: can't express labels like `E`/`F`, or
  gauges that are not evenly divided.
- *Store the label*: see spec Assumptions; makes fills logged under different lists
  incomparable and needs a migration.

## R3. Environment variable format

**Decision**: `FUEL_LEVELS` as comma-separated `label:percentage` entries, for example
`FUEL_LEVELS="E:0,1/4:25,1/2:50,3/4:75,F:100"`. Each entry is split on its **last** colon,
so a label may itself contain a colon. Whitespace around labels and percentages is
stripped. Labels given by environment variable cannot contain commas; a settings module
can use any label.

**Rationale**: Every other setting can be given as an environment variable (spec FR-002,
`getting_started.rst`), and the Docker image is configured that way. This format is easy
to type in a Docker env file, unlike JSON with its nested quotes.

**Alternatives rejected**: JSON (awkward quoting in env files and shell); `label=percent`
(`=` in a value is confusing in `KEY=VALUE` env files).

## R4. Validation at import, failing with `SystemExit`

**Decision**: Two module-level functions in `biweeklybudget/settings.py`:
`parse_fuel_levels(value)` (env string → list of pairs) and
`validate_fuel_levels(levels)` (checks and normalises the list, whatever its source). Both
raise `ValueError` with a specific reason. At import, the module parses the env var if set,
then validates the final value, turning any `ValueError` into
`SystemExit('ERROR: FUEL_LEVELS setting is invalid: <reason>')`.

Rules (spec FR-007): at least two levels; each is a 2-item list or tuple; the label is a
non-empty string after stripping whitespace; the percentage is an `int` (not `bool`) from
0 to 100; labels are unique; percentages are unique. In the env var, the percentage must
be all digits (`\d+`), matching the strictness of the existing `_INT_VARS` parsing.

**Rationale**: Invalid `_INT_VARS`, `_DATE_VARS`, `LOCALE_NAME`, and `CURRENCY_CODE` values
already abort startup with `SystemExit('ERROR: ...')`. Validating the settings-module value
too means a typo there is caught the same way. Pure functions can be unit-tested directly;
an import-time check can be tested in a subprocess without reloading the shared module.

**Why duplicates are rejected**: two options with the same percentage would be
indistinguishable once saved; two with the same label would be indistinguishable on the
form.

## R5. Getting the list to the browser

**Decision**: `fuel.html` adds `var FUEL_LEVELS = {{ settings.FUEL_LEVELS|tojson }};` next
to the existing `fuel_budget_id` global. The `settings` context processor already exposes
every setting to templates.

**Rationale**: Only the fuel page uses it, so it goes in that page's template rather than
`base.html`. Jinja's `tojson` escapes `<`, `>`, `&` and `'`, so no label can break out of
the `<script>` block. Tuples serialise as JSON arrays.

## R6. Building the selects in `fuel.js`

**Decision**: Build an ordered array of `{value, label, selected}` from `FUEL_LEVELS` and
pass it to `FormBuilder.addSelect()`, which already takes an ordered array. The starting
select preselects the lowest percentage, the ending select the highest. Labels are
HTML-escaped before being handed to `addSelect()`, which concatenates labels into HTML
unescaped.

**Rationale**: `addLabelToValueSelect()` takes an object and would re-order integer-like
labels (R2). Escaping in `fuel.js` rather than in `addSelect()` avoids changing how every
other form in the application renders its options. Account and budget names pass through
`addSelect()` too, and changing that is out of scope.

## R7. Testing a non-default list in the browser

**Finding**: The acceptance tests' `testflask` fixture is session-scoped and forks a live
server, so patching `settings` in the test process doesn't reach it. The test settings
module must keep the default list, so the existing default-behaviour assertions keep
guarding FR-003.

**Decision**:
- Settings parsing/validation: unit tests of the two functions, plus subprocess imports of
  `biweeklybudget.settings` with `FUEL_LEVELS` set in the environment (valid → value
  parsed; invalid → non-zero exit and an error naming `FUEL_LEVELS`).
- Server → page: an acceptance test reads the `FUEL_LEVELS` global from the rendered `/fuel`
  page and checks it equals the default list.
- Page → form → database, non-default: acceptance tests replace the page's `FUEL_LEVELS`
  global via Selenium before opening the modal, then check options, order, defaults and
  literal (escaped) labels, and save a fill and check the recorded percentages.

Together these cover each link of the chain (setting → page → form → stored value) with
both default and non-default lists.
