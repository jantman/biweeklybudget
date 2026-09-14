# Contract: Interfaces Removed and Changed

This feature removes external interfaces rather than adding them. This file is the
authoritative list of what disappears or changes, for the changelog, the docs and the
tests.

## Console scripts (removed)

| Command | Was | After |
|---|---|---|
| `ofxgetter` | `biweeklybudget.ofxgetter:main` | not installed |
| `ofxbackfiller` | `biweeklybudget.backfill_ofx:main` | not installed |
| `ofxclient` | `biweeklybudget.vendored.ofxclient.cli:run` | not installed |

Remaining console scripts, unchanged: `addtrans`, `loaddata`, `initdb`,
`wishlist2project`, and the `flask rundev` command.

## HTTP endpoints (removed)

| Method + path | Was | After |
|---|---|---|
| `GET /api/ofx/accounts` | JSON of accounts configured for ofxgetter | 404 (no route) |
| `POST /api/ofx/statement` | Upload pickled `ofxparse.Ofx` statement | 404/405 (no route) |

Unchanged OFX-named routes (they serve Plaid data): `GET /ofx`, `GET /ajax/ofx`,
`GET /ajax/ofx/<acct_id>/<fitid>`, `GET /ofx/<acct_id>/<fitid>`, and every
`/ajax/unreconciled/ofx`, reconcile and ignore endpoint.

## HTTP endpoints (changed)

### `POST /forms/account`

Request fields **removed**: `ofx_cat_memo_to_name`, `vault_creds_path`,
`ofxgetter_config_json`. The "Invalid JSON!" validation error on
`ofxgetter_config_json` goes with it.

A client that still sends them: the three keys are ignored (the handler reads only
the fields it knows); the account is saved from the remaining fields. No new error is
introduced for extra keys.

All other request fields, validation and responses are unchanged.

### `GET /ajax/account/<id>` (and anything else serialising `Account.as_dict`)

Response keys **removed**: `ofx_cat_memo_to_name`, `vault_creds_path`,
`ofxgetter_config_json`. `negate_ofx_amounts` and all other keys are unchanged.

## Settings (removed)

`VAULT_ADDR`, `TOKEN_PATH`, `STATEMENTS_SAVE_PATH` — removed from
`biweeklybudget.settings`, `settings_example.py` and the test settings. If a
settings module or the environment still sets them, they are not read and startup
is unaffected.

## Web UI (changed)

Add/Edit Account modal: fields "OFX Cat Memo to Name" (`account_frm_ofx_cat_memo`),
"Vault Creds Path" (`account_frm_vault_creds_path`) and "OFXGetter Config (JSON)"
(`account_frm_ofxgetter_config_json`) are removed. All other fields, in their existing
order, are unchanged.

## Python API (removed)

Modules: `biweeklybudget.ofxgetter`, `biweeklybudget.backfill_ofx`,
`biweeklybudget.vault`, `biweeklybudget.screenscraper`, `biweeklybudget.ofxapi`
(and `.local`, `.remote`, `.exceptions`), `biweeklybudget.vendored` (the vendored
`ofxclient`).

Members: `Account.vault_creds_path`, `Account.ofxgetter_config_json`,
`Account.ofx_cat_memo_to_name`, `Account.for_ofxgetter`, `Account.ofxgetter_config`,
`Account.set_ofxgetter_config()`, `OFXTransaction.params_from_ofxparser_transaction()`.

A user's customization package that subclassed `ScreenScraper` or imported any of the
above stops importing; this is the intended breaking change.
