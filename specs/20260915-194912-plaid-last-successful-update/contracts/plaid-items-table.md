# Contract: Plaid Items Table and the Extraction Helper

**Feature**: [spec.md](../spec.md) | **Date**: 2026-09-15

This feature exposes no new HTTP endpoint and changes no existing endpoint's request or
response shape. It changes one rendered table and adds one internal function. Both are
specified here because both are what the tests assert against.

---

## C1: UI contract — the Plaid Items table on `GET /plaid-update`

Rendered by `biweeklybudget/flaskapp/templates/plaid_form.html` into the table with
`id="table-items-plaid"`, inside the panel `id="panel-plaid-items"`.

### Columns, before and after

| # | Before | After |
|---|--------|-------|
| 1 | ID | ID |
| 2 | Name | Name |
| 3 | Institution Accounts | Institution Accounts |
| 4 | Last Polled | Last Polled |
| 5 | Update | **Last Successful Update** |
| 6 | Refresh Accounts | Update |
| 7 | — | Refresh Accounts |

The new column is inserted **immediately after "Last Polled"**, so the two timestamps are
adjacent and directly comparable (FR-006, FR-007). The action columns keep their order and
shift right.

### Cell contents

| Stored value | Rendered cell |
|--------------|---------------|
| A datetime | The same relative form the "Last Polled" column uses — `humanize.naturaltime` via the `ago` filter, e.g. `now`, `3 days ago`, `2 months ago` |
| `NULL` | The literal string `unknown` |

An empty cell is not a permitted rendering (FR-008).

### Unchanged

- The table's `id`, the panel's `id`, and the ids of every control on the page.
- The "Plaid Update Transactions" table (`id="table-update-plaid"`) and its checkboxes.
- The "Update / Fix Item" and "Refresh" links, their `onclick` handlers, and their text.
- The Plaid Update *Result* page (`plaid_result.html`) — out of scope per the spec.

### Consumer impact

`biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py::test_4_table` asserts the
table's full row text. It is a consumer of this contract and must be updated in the same
change.

---

## C2: Internal contract — `biweeklybudget.utils.plaid_last_successful_update`

```text
plaid_last_successful_update(item_get_response) -> Optional[datetime]
```

**Input**: the object returned by the Plaid client's `item_get()` — in production a
`plaid.model.item_get_response.ItemGetResponse`, in tests a plain `dict`. Only the `.get()`
protocol is relied on, which both provide.

**Output**: a timezone-aware `datetime`, or `None`.

### Behaviour

| Input shape | Returns |
|-------------|---------|
| `status.transactions.last_successful_update` is an aware datetime | That datetime, unchanged |
| …is a naive datetime | The same datetime with UTC attached |
| …is absent or `None` | `None` |
| `status.transactions` is absent, `None`, or empty | `None` |
| `status` is absent, `None`, or empty | `None` |

**Never raises** for any of the shapes above. This matters because both callers use it inside
code paths where an exception is either swallowed into a failed-update result or turned into
an HTTP 400 — a cosmetic field must not be able to fail a transaction download (FR-004).

Errors that are genuinely not this function's business — an input that does not support
`.get()` at all — are not caught and propagate.

### Callers

| Caller | Assignment |
|--------|------------|
| `PlaidUpdater._do_item` | `item.last_successful_update = plaid_last_successful_update(iteminfo)`, alongside the existing `item.last_updated = dtnow()` |
| `PlaidUpdateItemInfo.post` | `item.last_successful_update = plaid_last_successful_update(response)`, alongside the existing institution-name and -id assignments |

Both assign before the `db_session.add(item)` that already exists in that code path. Neither
adds a Plaid API call: both already hold an `item_get` response.

---

## C3: What is explicitly *not* in this contract

- `last_failed_update`, and the status of Plaid products other than transactions.
- Any history of past values — the column holds one value, replaced in place.
- Any change to the `/plaid-update` endpoint's plain-text, JSON, or HTTP-status behaviour,
  which issue #261 defined and this change does not touch.
- Any new page, menu entry, or notification.
