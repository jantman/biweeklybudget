# Contract: `/plaid-update` status codes

Endpoint: `GET` or `POST /plaid-update`. Parameters are unchanged (`item_ids`, optional
`num_days`); see `docs/source/plaid.rst`.

| Request | Outcome | Status | Body |
|---------|---------|--------|------|
| GET, no `item_ids` | update form | 200 | form HTML (unchanged) |
| POST, no `item_ids` (query or form) | rejected | 400 | `{"success": false, "message": "Missing parameter: item_ids"}` (unchanged) |
| GET/POST with `item_ids`, every Item succeeds | update ran | **200** | results in the requested format (unchanged) |
| GET/POST with `item_ids`, no Items to update | update ran | **200** | empty results (unchanged) |
| GET/POST with `item_ids`, one or more Items fail | update ran, incomplete | **500** | full results in the requested format, including every failed Item's error (unchanged) |

The result formats, chosen by the `Accept` header, are all unchanged:

- `text/plain`: one line per Item, then `TOTAL: N updated, N added, N account(s) failed`.
- `application/json`: a list of `{"item_id", "success", "exception", "statement_ids", "added", "updated"}`.
- anything else: the HTML results page.

The status rule is identical for all three formats and for both methods.
