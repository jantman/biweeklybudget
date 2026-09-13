# Research: Plaid Update Check All / Uncheck All

The Technical Context had no NEEDS CLARIFICATION items. These notes record the choices
the issue left open.

## R1. Where the links go

- **Decision**: One line, `Check All | Uncheck All`, inside the "Plaid Update
  Transactions" panel's form, directly above the item table.
- **Rationale**: That panel holds the only checkboxes on the page. Above the table they
  are seen before the operator starts working down the list, and they stay close to the
  checkboxes they act on.
- **Alternatives considered**: In the "Update Transactions?" column header (cramped, and
  mixes controls into a header cell); beside the Update Transactions button (below the
  list, so the operator scrolls past every item first).

## R2. Link style

- **Decision**: `<a href="javascript:plaidSetAllItems(true|false);">`, separated by ` | `.
- **Rationale**: Matches existing page-action links such as "make trans. | skip" in
  `payperiod.html` and the `javascript:` modal links throughout the templates. It does
  not change the URL or scroll the page, as `href="#"` would.
- **Alternatives considered**: `href="#"` with `onclick` returning false (used in
  `credit-payoffs.html`; works, but two attributes and easy to get wrong); buttons (the
  issue asks for links, and buttons inside the form default to `type="submit"`).

## R3. How the checkboxes are changed

- **Decision**: `$('#table-update-plaid input.account-checkbox').prop('checked', checked)`
  inside a function that returns nothing.
- **Rationale**: jQuery is already used by the page's inline script. Setting the
  `checked` *property* changes what the form submits; the `checked` *attribute* only
  sets the default. The function must return `undefined` because a `javascript:` URL
  whose expression evaluates to a value replaces the page with that value.
- **Alternatives considered**: Triggering `click()` on each box (toggles instead of
  setting, so "Check All" would uncheck already-checked items).

## R4. Server side

- **Decision**: No change.
- **Rationale**: `PlaidUpdate.post()` in `biweeklybudget/flaskapp/views/plaid.py` builds
  `item_ids` from the posted `item_*` form keys, and browsers do not post unchecked
  checkboxes. Whatever is checked at submit time is exactly what is updated (spec FR-005).

## R5. Documentation and generated docs

- **Decision**: Update step 2 of "Updating Transactions via UI" in
  `docs/source/plaid.rst`. No jsdoc or screenshot changes.
- **Rationale**: The function is inline in the template, and `docs/make_jsdoc.py` only
  documents files in `static/js/`. `docs/make_screenshots.py` has no Plaid Update
  screenshot.

## Noted, out of scope

The Update Transactions button has `onclick="getPlaidTransactions()"`, but no such
function exists. The resulting ReferenceError does not stop the form submitting, so
behaviour is unaffected. This feature leaves it alone (spec FR-006); it could be removed
separately.
