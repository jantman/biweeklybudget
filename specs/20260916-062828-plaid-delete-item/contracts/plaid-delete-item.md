# Phase 1 Contracts: Delete a Plaid Item

**Feature**: [spec.md](./spec.md) | **Research**: [research.md](./research.md) |
**Data model**: [data-model.md](./data-model.md)

Three contracts: the HTTP endpoint (C1), the Plaid failure classification it depends on (C2),
and the UI surface on the Plaid Update page (C3).

---

## C1 — `POST /ajax/plaid/delete_item`

Served by a new `PlaidDeleteItem(MethodView)` in `biweeklybudget/flaskapp/views/plaid.py`,
registered in `set_url_rules` as `plaid_delete_item`. Modelled on `PlaidRefreshAccounts`
(`views/plaid.py:134-191`).

### Request

`Content-Type: application/json`

```json
{"item_id": "SomePlaidItemId"}
```

`item_id` is required and is the `plaid_items.item_id` primary key.

### Behaviour

In this exact order (see [data-model.md](./data-model.md) "Required mutation order"):

1. Read `item_id` from the request body. Absent or empty → **400**, nothing else happens.
2. `db_session.query(PlaidItem).get(item_id)`. `None` → **404**, nothing else happens.
3. `plaid_client().item_remove(ItemRemoveRequest(access_token=item.access_token))`.
   - Returns normally → continue.
   - Raises `ApiException` classified *recoverable* by C2 → continue.
   - Raises `ApiException` otherwise → **400**; the session is not modified.
4. For every `Account` with `plaid_item_id == item_id`: set `plaid_item_id = None` and
   `plaid_account_id = None`. No other attribute is assigned.
5. `db_session.delete(...)` each `PlaidAccount` with `item_id == item_id`.
6. `db_session.delete(item)`.
7. `db_session.commit()` — one commit covering steps 4-6.

### Responses

| Outcome | Status | Body |
|---|---|---|
| Deleted | 200 | `{"success": true, "item_id": "<id>", "accounts_unlinked": ["<Account name> (<id>)", ...]}` |
| `item_id` missing from request | 400 | `{"success": false, "message": "Missing item_id parameter."}` |
| No such Item | 404 | `{"success": false, "message": "ERROR: No Plaid Item with item_id <id>"}` |
| Plaid rejected the removal | 400 | `{"success": false, "message": "Exception: <str(ApiException)>"}` |

`accounts_unlinked` is a list of human-readable `"Name (id)"` strings, empty when no Account
was linked. It is the only part of the outcome that is not visible on the reloaded page.

### Guarantees

- **G1** — The access token is never in any response body, any log line added by this feature,
  or any rendered page (FR-014).
- **G2** — On any non-200 response, the database is exactly as it was before the request
  (FR-007, FR-010). Steps 4-6 all happen inside one transaction, and step 3's failure path runs
  before the session is touched at all.
- **G3** — Only rows belonging to this Item, and Accounts referencing it, are written
  (FR-011).
- **G4** — Repeating a request for an Item already deleted returns 404, not a 500 and not a
  partial mutation (FR-013).
- **G5** — Nothing on an unlinked Account other than its two Plaid columns is written
  (FR-009).

---

## C2 — Plaid failure classification

A helper in `views/plaid.py` (module-private) answers one question about an `ApiException`:
*is this Item already gone as far as Plaid is concerned?*

```text
recoverable(exc) -> bool
```

| Input | Result |
|---|---|
| `exc.body` is JSON with `error_code == "ITEM_NOT_FOUND"` | `True` |
| `exc.body` is JSON with `error_code == "INVALID_ACCESS_TOKEN"` | `True` |
| `exc.body` is JSON with any other `error_code` (e.g. `INVALID_API_KEYS`, `INTERNAL_SERVER_ERROR`, `RATE_LIMIT_EXCEEDED`) | `False` |
| `exc.body` is JSON with no `error_code` key | `False` |
| `exc.body` is `None` | `False` |
| `exc.body` is not valid JSON, or is not a JSON object | `False` |
| `exc.body` is `bytes` rather than `str` | decoded, then as above |

`True` means "treat the removal as having succeeded and continue with the local deletion"
(FR-006). `False` means "abort" (FR-007).

**Rationale and the reason `INVALID_API_KEYS` is excluded**: [research.md](./research.md) R2.

This helper must never raise. Every branch above is a unit test case.

---

## C3 — Plaid Update page

### C3.1 — The Plaid Items table

`templates/plaid_form.html`, table `#table-items-plaid`. Columns become:

```text
ID | Name | Institution Accounts | Last Polled | Last Successful Update | Update | Refresh Accounts | Delete
```

The new final cell renders a link whose text is exactly `Delete`, invoking the confirmation
(never the deletion) on click. It carries the Item's id, its institution name and the
already-computed `accounts[i.item_id]` string, serialised with Jinja's `|tojson` because
institution names are free text from Plaid.

Effects on existing tests: `tests/acceptance/flaskapp/views/test_plaid.py::test_4_table`
asserts exact per-row cell text and gains an eighth cell, `'Delete'`.

### C3.2 — The confirmation modal

Uses the shared `#modalDiv` already included at `plaid_form.html:87`, following the
`creditPayoffErrorModal.js` pattern (`$('#modalBody').empty()` → append → `$('#modalSaveButton').off().click(...)` →
`$('#modalLabel').text(...)` → `$("#modalDiv").modal('show')`).

Required content (FR-003):

| Element | Content |
|---|---|
| `#modalLabel` | Names the action and the Item, e.g. `Delete Plaid Item <item_id>` |
| `#modalBody` | The institution name and Item id; the Accounts that will be unlinked, or an explicit statement that none will be; that the Item will also be removed at Plaid; that the action cannot be undone |
| `#modalSaveButton` | Visible, labelled `Delete`, styled as a destructive action; posts to C1 on click |
| `#modalCloseButton` | Dismisses with no request sent (FR-004) |

**Nothing is sent to the server until `#modalSaveButton` is clicked.** Opening the modal and
dismissing it makes no HTTP request of any kind.

### C3.3 — `plaidDelete` in `static/js/plaid_prod.js`

Two functions, JSDoc'd in the file's existing style (they appear in the generated
`docs/source/jsdoc.plaid_prod.rst`):

- **`plaidDeleteConfirm(item_id, institution_name, account_names)`** — builds and shows the
  modal described in C3.2. Makes no request.
- **`plaidDelete(item_id)`** — POSTs C1 and, on success, `location.reload()` so the page
  reflects the new state (FR-012). On failure, surfaces the server's `message` to the
  maintainer without reloading, so the unchanged page is still in front of them (FR-007).
  This mirrors `plaidRefresh` (`plaid_prod.js:109-126`).

### C3.4 — What does not change

`Update / Fix Item`, `Refresh`, `Link (Add Plaid Item)`, `Update Item Information from Plaid`,
the `Check All` / `Uncheck All` links, the `#table-update-plaid` checkbox table and the
transaction update flow all behave exactly as before. No other page gains a delete affordance.
