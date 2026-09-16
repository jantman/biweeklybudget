# Phase 0 Research: Delete a Plaid Item

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-16

Every question this feature raised was resolved against the repository or the installed
dependencies. Nothing is left for implementation time to guess at.

---

## R1 — What does Plaid's Item-removal call look like in the installed client?

**Decision**: `client.item_remove(ItemRemoveRequest(access_token=item.access_token))`, with
`ItemRemoveRequest` imported from `plaid.models` alongside the request classes the view
already imports.

**Findings** (`plaid-python` 38.0.0, the pinned version):

- `plaid.models.ItemRemoveRequest` exists and re-exports
  `plaid.model.item_remove_request.ItemRemoveRequest`. Its fields are `access_token` (str,
  required), `client_id`, `secret`, `reason_code`, `reason_note` — the last four are optional
  and unnecessary; `client_id`/`secret` come from the configured `ApiClient`.
- `PlaidApi.item_remove` exists.
- `ItemRemoveResponse` carries exactly one field, `request_id` (str). There is nothing in the
  response to branch on: a non-exception return *is* the success signal. This matches the
  `{'request_id': 'SomeRequestId'}` output the issue documents.

**Rationale**: This is exactly what the issue's manual script does, so the feature is a
faithful automation of it rather than a reinterpretation.

**Alternatives considered**: `/item/remove` via raw HTTP — rejected; the project already uses
the generated client everywhere and `plaid_client()` centralises configuration.

---

## R2 — How is a Plaid failure surfaced, and how do we tell "already gone" from a real error?

**Decision**: catch `plaid.exceptions.ApiException`, parse `exc.body` as JSON, and treat the
`error_code` values `ITEM_NOT_FOUND` and `INVALID_ACCESS_TOKEN` as "already removed — continue
with the local deletion". Every other `ApiException`, and any JSON that cannot be parsed or
carries no recognised `error_code`, aborts the deletion.

**Findings**:

- `ApiException.__init__` sets `self.status`, `self.reason`, `self.body` (the raw response
  bytes) and `self.headers`. `__str__` renders `Status Code: N\nReason: R\n` plus headers and
  body when present.
- The existing views (`PlaidHandleLink`, `PlaidRefreshAccounts`, `PlaidUpdateItemInfo`) all use
  the same shape: `except ApiException as ex: ... jsonify({'success': False, 'message':
  f'Exception: {ex}'})` with `status_code = 400`. Their unit tests assert the exact string
  `'Exception: Status Code: 500\nReason: fooerror\n'`. This feature reuses that shape verbatim
  so the failure path looks like every other Plaid failure in the app.
- Plaid error bodies are JSON objects carrying `error_type`, `error_code`, `error_message`,
  `display_message`, `request_id`. `error_code` is the stable, documented discriminator.

**Rationale**: FR-006 exists to stop an Item becoming undeletable. The two codes chosen are
precisely the "this access token will never work again" cases:

- `ITEM_NOT_FOUND` — the Item was already removed at Plaid (a previous attempt that failed
  after the Plaid call but before the local commit, or a removal done from the Plaid
  dashboard).
- `INVALID_ACCESS_TOKEN` — the token is not valid for the configured client/environment. This
  is the everyday state of every Item left over after a `PLAID_ENV`/`PLAID_SECRET` change,
  which is the exact case `docs/source/plaid.rst`'s "Changing Plaid Environments" section
  currently answers with raw `DELETE` statements.

`INVALID_API_KEYS` is deliberately **not** in the set: that is a misconfiguration of the
installation, not a property of the Item, and it must abort so the maintainer fixes their
credentials rather than silently shedding Items.

**Alternatives considered**:

- Matching on `error_type` (`ITEM_ERROR`, `INVALID_INPUT`) — too coarse; `INVALID_INPUT` also
  covers `INVALID_API_KEYS`.
- Matching on HTTP status — Plaid returns 400 for both the recoverable and unrecoverable
  cases.
- Treating *every* failure as "delete locally anyway" — rejected outright: that reproduces the
  exact orphaned-Item hazard the feature exists to remove, and violates FR-007/FR-010.

---

## R3 — In what order must the local deletion happen, and what does the schema force?

**Decision**: Plaid removal → clear `Account.plaid_item_id`/`plaid_account_id` for every
Account pointing at the Item → delete the Item's `PlaidAccount` rows → delete the `PlaidItem`
row → one `db_session.commit()`.

**Findings**:

- `PlaidItem.all_accounts` (`models/plaid_items.py:77-79`) is a plain `relationship` with **no**
  `cascade=` and no `passive_deletes`. The SQLAlchemy default (`save-update, merge`) makes a
  `delete()` of the parent try to NULL the children's `item_id` — which is both
  `nullable=False` and half of `PlaidAccount`'s composite primary key. Deleting the Item
  without first deleting its accounts therefore fails.
- `f5a002127934_plaid_models.py:39-59` creates `fk_plaid_accounts_item_id_plaid_items` and
  `fk_accounts_plaid_item_id_plaid_accounts` with **no** `ondelete` clause, so MySQL rejects
  any delete that would orphan a referencing row. `Account.__table_args__`
  (`models/account.py:96-103`) carries the composite FK into `plaid_accounts`.
- Consequently the unlink must precede the `PlaidAccount` deletes, which must precede the
  `PlaidItem` delete. This is the same order the issue's manual procedure uses and the same
  order `tests/acceptance/test_plaidlink.py:85-95` uses in raw SQL.
- Unlinking is a two-column assignment to `None`, exactly as
  `flaskapp/views/accounts.py:286-288` already does for the "none" choice in the account form.
  Nothing else on the Account is touched, which is what FR-009 requires.
- `db_event_handlers.py`'s `before_flush` deletion handler filters on
  `isinstance(obj, BudgetTransaction)` and `continue`s otherwise, so deleting Plaid rows
  triggers no budget arithmetic. Confirmed by reading the whole `session.deleted` loop.

**Rationale**: The ordering is forced by the schema, not chosen. Doing it in one session and
one commit gives FR-010's all-or-nothing guarantee for free.

**Alternatives considered**:

- Adding `cascade='all, delete-orphan'` to `PlaidItem.all_accounts` and/or `ON DELETE CASCADE`
  to the foreign keys. Rejected: it is a schema/behaviour change requiring a migration, it
  would silently change what happens on every other path that deletes a `PlaidAccount`
  (`PlaidRefreshAccounts`, `views/plaid.py:189`), and an implicit cascade through a foreign key
  into the *accounts* table is precisely the kind of action-at-a-distance that a financial
  database should not have. Explicit deletion in the one view that wants it is safer and keeps
  the feature schema-free.
- Deleting locally first and calling Plaid afterwards (the issue's order) — rejected; see the
  spec's Context and Assumptions. It destroys the access token before it is used.

---

## R4 — What happens if Plaid succeeds but the local commit then fails?

**Decision**: Accept it, and rely on R2 to make the retry correct. No compensating action is
attempted.

**Findings**: Removal at Plaid is not reversible from this application. If the commit fails
afterwards, the Item remains in the database with an access token Plaid no longer honours. The
maintainer's natural response — click Delete again — now gets `ITEM_NOT_FOUND` from Plaid,
which R2 classifies as success, so the second attempt completes the local deletion.

**Rationale**: The one irreducible window in the whole design is self-healing on retry. Trying
to "undo" a Plaid removal would mean re-linking, which needs the maintainer's bank credentials
and cannot be done server-side.

---

## R5 — Where does the endpoint go, and what does it return?

**Decision**: a new `PlaidDeleteItem(MethodView)` in `flaskapp/views/plaid.py` serving
`POST /ajax/plaid/delete_item`, modelled directly on `PlaidRefreshAccounts`
(`views/plaid.py:134-191`).

**Findings**:

- `PlaidRefreshAccounts` is the closest sibling: a JSON `POST` taking `{'item_id': ...}`,
  looking the Item up with `db_session.query(PlaidItem).get(item_id)`, calling Plaid,
  mutating the database, committing, and returning `{'success': True}`. It is also the only
  place in the whole application that calls `db_session.delete()` outside tests.
- Routes are registered in `set_url_rules` (`views/plaid.py:450-471`), which
  `tests/unit/flaskapp/views/test_plaid.py:60-118` asserts as an exact ordered list of
  `add_url_rule` calls. That test **must** be updated; it is not optional.
- `PlaidRefreshAccounts` does not check for a missing Item — `...get(item_id)` returning `None`
  would raise `AttributeError` and produce a 500. FR-013 requires better, so the new view
  checks explicitly and returns 404.

**Response contract** (full detail in [contracts/plaid-delete-item.md](./contracts/plaid-delete-item.md)):

| Case | Status | Body |
|---|---|---|
| Deleted | 200 | `{'success': True, 'item_id': ..., 'accounts_unlinked': [...]}` |
| No `item_id` in request | 400 | `{'success': False, 'message': ...}` |
| Item not in the database | 404 | `{'success': False, 'message': ...}` |
| Plaid rejected the removal | 400 | `{'success': False, 'message': 'Exception: ...'}` |

**Rationale**: Mirroring the sibling keeps the view, its tests and its JS caller in the shape a
reader of this file already expects. `accounts_unlinked` is returned because it is the one
piece of the outcome the maintainer cannot see by looking at the reloaded page.

**Alternatives considered**: `DELETE /ajax/plaid/item/<item_id>` — more RESTful, but no other
endpoint in this application uses a non-POST verb for mutation, and the frontend helpers are
all built around `type: 'POST'`.

---

## R6 — How is the confirmation built, and where does it get the list of affected Accounts?

**Decision**: the existing Bootstrap 3 modal (`templates/modal.html`, already included by
`plaid_form.html:87`), populated entirely client-side from values Jinja renders into the
`onclick` attribute with `|tojson`. No extra AJAX round trip, no browser-native `confirm()`.

**Findings**:

- `plaid_form.html:87` already does `{% include 'modal.html' %}`, giving the page `#modalDiv`,
  `#modalLabel`, `#modalBody`, `#modalSaveButton` and `#modalCloseButton`.
- The established usage pattern (`creditPayoffErrorModal.js:56-72`, `account_transfer_modal.js`,
  `budget_transfer_modal.js`, `payperiod_modal.js`) is: `$('#modalBody').empty()`, append
  content, `$('#modalSaveButton').off()` then `.click(...)`, `$('#modalLabel').text(...)`,
  `$("#modalDiv").modal('show')`. `ofx.js:68` shows `$('#modalSaveButton').hide()` for a
  read-only modal, so the button's visibility is already managed per-modal — a delete modal
  must `.show()` it and re-label it.
- `PlaidUpdate._form` (`views/plaid.py:372-398`) already computes, per Item, both
  `plaid_accounts[item_id]` (`'Name (mask), ...'`) and `accounts[item_id]`
  (`'AcctName (id), ...'`, empty string when no Account is linked). The confirmation needs
  exactly `accounts[item_id]` and the institution name — both already in the template's scope.
- The existing row actions are rendered as `<a onclick="plaidUpdate('{{ i.item_id }}')">`, so
  passing arguments through `onclick` is the house style. `|tojson` is used rather than manual
  quoting because institution names are free text from Plaid and can contain apostrophes.

**Rationale**: A native `confirm()` cannot list the affected Accounts, reads as a browser
artefact rather than part of the application, and is awkward to drive from Selenium — which
matters, because the acceptance suite is where the confirmation's content and its Cancel path
get tested. The constitution also requires new UI to follow the existing modal pattern rather
than introduce a parallel one.

**Alternatives considered**:

- A dedicated `GET /ajax/plaid/item/<id>/delete_preview` endpoint to build the modal.
  Rejected — a second round trip for data the page already rendered.
- A per-row hidden `<div>` holding the confirmation text. Rejected — more markup, and it would
  change the acceptance suite's `tbody2textlist` assertions in a confusing way.

---

## R7 — How is this tested, given that the acceptance suite cannot call Plaid?

**Decision**: three layers, each covering what it can actually reach.

| Layer | Suite | Covers |
|---|---|---|
| View logic, every branch | `tox -e py314` unit | FR-002/004–011, 013, 014 — with `plaid_client`, `db_session` and the models patched at module level |
| Template + modal + Cancel | `tox -e acceptance` | FR-001, 003, 004, 012 — the Delete link exists, the modal names the Item and the Accounts, Cancel changes nothing |
| Real round trip to Plaid | `tox -e plaid` | FR-005, FR-008 end-to-end against Plaid's sandbox |

**Findings**:

- `tests/fixtures/test_settings.py:84-92` sets `PLAID_CLIENT_ID='plaidCID'`,
  `PLAID_SECRET='plaidSecret'`, `PLAID_ENV='Sandbox'`. So in the acceptance live server
  `plaid_client()` will *not* assert — it will build a client and make a real network call to
  Plaid's sandbox host, which then fails with `INVALID_API_KEYS`. An acceptance test that
  actually POSTs the delete endpoint would therefore depend on outbound network and on Plaid's
  availability. That is not acceptable for the acceptance suite; no existing acceptance test
  exercises any Plaid-calling endpoint, and this feature will not be the first.
- The acceptance suite *can* cover everything up to the POST: the table cell, the modal's
  content, and the Cancel path — none of which touch the server.
- `tests/unit/flaskapp/views/test_plaid.py` patches everything at module level
  (`patch.multiple(pbm, jsonify=DEFAULT, request=..., plaid_client=DEFAULT, PlaidItem=DEFAULT,
  db_session=mock_sess, ...)`) and asserts the **exact ordered** `mock_calls` list on
  `db_session` and on the mock Plaid client. The new view's DB call sequence must therefore be
  spelled out in its test — which is a feature here, because the call *order* is the safety
  property (R3).
- `TestPlaidResultTemplate` (`test_plaid.py:1366-1393`) renders a real template inside
  `app.test_request_context()` and asserts on the HTML. The same pattern gives a direct unit
  test that `plaid_form.html` renders the Delete link.
- `tests/acceptance/test_plaidlink.py` is an `@pytest.mark.incremental` class running against
  Plaid's real sandbox, currently ending at `test_19_update_transactions`. Appending delete
  steps there is the only way to prove FR-005 against Plaid. The class is `xfail`ed when
  `CI == 'true'` because the Link iframe flow does not work headless, so these steps add local
  signal and cost nothing in CI.

**Rationale**: This mirrors how the repository already splits Plaid coverage, and it puts the
strictest assertions (ordering, exact DB calls) where they can run on every push.

**Alternatives considered**: monkey-patching the Plaid client inside the acceptance live server
the way `docs/make_screenshots.py:115-142` substitutes a `ScreenshotPlaidUpdater`. Rejected —
that works because the screenshot script constructs the app itself; the `testflask` fixture
does not offer an equivalent hook, and adding one for a single test is disproportionate.

---

## R8 — Which documentation and screenshots change?

**Decision**: a new "Deleting a Plaid Item" subsection in `docs/source/plaid.rst`, a rewrite of
that file's "Changing Plaid Environments" steps 1–2, the Plaid Update screenshot regenerated,
and its caption updated in `docs/make_screenshots.py`.

**Findings**:

- `docs/source/plaid.rst` has `.. _plaid.linking:` (Linking Accounts to Plaid, lines 36-47),
  `.. _plaid.update-ui:`, `.. _plaid.update-api:`, `.. _plaid.loan_accounts:`,
  `.. _plaid.troubleshooting:` and `.. _plaid.change-env:` (lines 134-146). The new subsection
  belongs under Usage, after Linking.
- "Changing Plaid Environments" steps 1 and 2 are the raw SQL this feature replaces:
  `UPDATE accounts SET plaid_item_id=NULL, plaid_account_id=NULL;` and
  `DELETE FROM plaid_accounts; DELETE FROM plaid_items;`. They must now say to delete each Item
  through the UI, and must say to do it **before** changing `PLAID_ENV`/`PLAID_SECRET`, because
  after the switch the old tokens are invalid for the new credentials. (An Item stranded by a
  switch that has already happened is still deletable — that is exactly the `INVALID_ACCESS_TOKEN`
  case in R2 — so the SQL is no longer needed as a fallback and is removed.)
- `docs/source/screenshots.rst` is **generated** by `make_rst()` in `docs/make_screenshots.py`;
  editing the `.rst` directly is discarded on the next regeneration. The Plaid Update entry's
  `description` (around `make_screenshots.py:280`) is the thing to edit.
- The Plaid Items table gains a column, so `plaid-update.png` / `plaid-update_sm.png` change and
  must be regenerated and committed.
- `docs/source/jsdoc.plaid_prod.rst` is tracked and generated by `tox -e jsdoc` from
  `static/js/plaid_prod.js`; the new JS function adds an entry.
- The `automodule` API stubs (`biweeklybudget.flaskapp.views.plaid.rst` and friends) pick the
  new view class up automatically — no manual edit.
- No prose in `README.rst` or `CLAUDE.md` enumerates the Plaid Items table's actions, so
  nothing else needs rewriting.

**Rationale**: Constitution IV — the documentation that describes the change ships with it, and
the manual procedure this feature obsoletes must stop being the documented answer.

---

## R9 — Does anything else in the application depend on a Plaid Item existing?

**Decision**: No. Nothing beyond the files this feature already touches.

**Findings**: `grep` for `PlaidItem|PlaidAccount` across `biweeklybudget/` (excluding tests and
migrations) returns only the two model modules, `models/account.py`, `models/__init__.py`,
`plaid_updater.py`, `flaskapp/views/plaid.py` and `flaskapp/views/accounts.py`. Of these:

- `plaid_updater.py:112` selects all Items each run — a deleted Item simply is not returned
  (FR: User Story 2, scenario 4).
- `views/accounts.py:84-88,127-131` builds the account form's Plaid dropdown from all
  `PlaidAccount`s — a deleted Item's accounts vanish from the dropdown, and an unlinked
  Account defaults to the "none" choice it already supports (FR-015).
- No notification, sidebar count, chart or report references Plaid Items.

**Rationale**: Confirms the blast radius is the Plaid Update page plus the Accounts dropdown,
and that no schema change is needed (spec Assumptions).
