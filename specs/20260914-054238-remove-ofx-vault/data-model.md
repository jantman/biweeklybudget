# Data Model: Remove OFX Downloading, Vault and Keychain

## Account (`accounts` table) — changed

Columns **removed** (declared in the base schema, `premigration_db_state.sql`):

| Column | Type | Null | Default | Previously used by |
|---|---|---|---|---|
| `ofx_cat_memo_to_name` | `tinyint(1)` / `Boolean` | yes | none (model default `False`) | `OfxApiLocal.update_statement_ofx` |
| `vault_creds_path` | `varchar(254)` / `String(254)` | yes | none | `ofxgetter`, `OfxApiLocal.get_accounts` |
| `ofxgetter_config_json` | `text` / `Text` | yes | none | `ofxgetter`, `Account.for_ofxgetter` / `ofxgetter_config` |

Model members removed with them: `Account.for_ofxgetter` (hybrid property),
`Account.ofxgetter_config` (property), `Account.set_ofxgetter_config()`.

Columns and members **kept**: everything else, notably `negate_ofx_amounts`,
`reconcile_trans`, `re_interest_charge`, `re_interest_paid`, `re_payment`,
`re_late_fee`, `re_other_fee`, `plaid_item_id`, `plaid_account_id`,
`ofx_statement`, `is_stale`.

## Migration

- New revision, `down_revision = '2d881fa466fe'` (current single head).
- `upgrade()`: `op.drop_column('accounts', ...)` for the three columns.
- `downgrade()`: `op.add_column` each back with its original type, nullable, no
  server default, positioned `after` its original neighbour
  (`ofx_cat_memo_to_name` after `description`, `vault_creds_path` after
  `ofx_cat_memo_to_name`, `ofxgetter_config_json` after `vault_creds_path`), so the
  table layout matches the pre-upgrade layout. Restored columns are NULL: the
  dropped values are not recoverable, and nothing reads them.
- State transition: pre-upgrade rows → identical rows minus three columns →
  (downgrade) identical rows with three NULL columns.

## OFXStatement / OFXTransaction — unchanged

Schema and model unchanged. `OFXTransaction.params_from_ofxparser_transaction()` (a
static helper that turned an `ofxparse` transaction into constructor kwargs) is
removed; nothing but the OFX importer called it. `OFXStatement.filename` and
`file_mtime` stay (Plaid sets `filename`; historical OFX rows keep both).
