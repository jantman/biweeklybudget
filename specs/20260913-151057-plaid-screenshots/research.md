# Research: Plaid Screenshots

## R1. Producing a Plaid Update result without Plaid

**Decision**: In `docs/make_screenshots.py`, before starting the live server, replace
`biweeklybudget.flaskapp.views.plaid.PlaidUpdater` with a stub subclass. Its `__init__`
skips creating a Plaid client. Its `update(items, days)` returns fixed
`PlaidUpdateResult`s: the first Item succeeds (updated/added counts and statement IDs),
the rest fail with an invented `ITEM_LOGIN_REQUIRED` error. `available_items()` is
inherited, so `GET /plaid-update?item_ids=ALL` renders the real view and template.

**Rationale**: pytest-flask's `LiveServer` runs the app in a `multiprocessing.Process`,
and the script sets the start method to `fork`, so a module attribute patched in the
parent before `server.start()` is what the server process uses. The real view code
(status, totals, failure count) and the real template are exercised. The stub writes
nothing to the database, so later screenshots are unaffected.

**Alternatives considered**:

- Test-only endpoint or setting in the app: adds production code that exists only for
  docs. Rejected.
- Mocking the Plaid HTTP API: much more setup (link to transactions and balances
  responses) for the same picture. Rejected.
- Rendering the template to a static file and screenshotting that: loses the real
  page chrome and view logic. Rejected.

## R2. Showing the Plaid Account selector

**Decision**: New entry for `/accounts/1` (BankOne, linked to sample Plaid Item
`PlaidItem1` / account `PlaidAcct1`) with a preshot that scrolls the modal
(`#modalDiv`, the Bootstrap 3 scroll container) to the bottom, so the Plaid Account
selector and the Save button are in view.

**Rationale**: The existing `account1` screenshot is taken with the modal at the top and
cuts off at the "Plaid Account" label. The full-page resize only grows the window to the
document height, not the modal's content height, so scrolling is needed. Scrolling to
the bottom is robust to fields being added above.

**Alternatives considered**: Changing `account1` itself: it would stop showing the top of
the modal. Rejected; the spec keeps it.

## R3. Order and names

**Decision**: Insert after "OFX Transactions", in the order a user follows (linking,
then updating): `plaid-update` ("Plaid Update"), `account1-plaid` ("Linking an Account to
Plaid"), `plaid-update-result` ("Plaid Update Result").

## R4. Result page "Statement IDs" column is always empty

**Finding**: `plaid_result.html` renders `{{ pur.stmt_id }}`, but `PlaidUpdateResult`'s
attribute is `stmt_ids`. Jinja renders the undefined attribute as an empty string, so
the column is blank for every Item. Unit tests mock `render_template`, so the template
is never rendered in tests.

**Decision**: Fix the attribute name and add a unit test that renders the real template
with results that have statement IDs. Recorded in the spec as a deviation.

**Rationale**: The new screenshot would otherwise document the bug. The fix is one token.

## R5. Committing regenerated screenshots

**Decision**: Do not commit regenerated PNGs or `screenshots.rst`. Verify with a full
local `screenshots` run and review the three new images.

**Rationale**: The constitution (Development Workflow step 7) regenerates screenshots at
release, and earlier features that added screenshots (Cash Position, Spending Charts) only
changed the generator. Regenerating here would also replace every other image and pull
in those features' not-yet-committed entries, unrelated to this change. The `plaid.rst`
link targets the Screenshots page, which exists now; the Plaid entries appear on it at
the next regeneration.

## R6. Linting the generator

`docs/make_screenshots.py` is not under the `py314` env's pytest target
(`biweeklybudget`), so `--pycodestyle --flakes` does not see it. New code in it is
checked by hand with pycodestyle (repo `setup.cfg`, max line length 100) and pyflakes;
existing warnings in untouched code are left alone.
