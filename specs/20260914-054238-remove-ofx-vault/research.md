# Research: Remove OFX Downloading, Vault and Keychain

No `NEEDS CLARIFICATION` items were left in the Technical Context. The questions below
were settled by reading the code and the installed package metadata.

## R1. What "OFX" is removed and what stays

- **Decision**: Remove OFX downloading and importing: `ofxgetter.py`,
  `backfill_ofx.py`, `vault.py`, `screenscraper.py`, the `ofxapi/` package, the whole
  `vendored/` tree (only `ofxclient` lives there), the `/api/ofx/accounts` and
  `/api/ofx/statement` routes (`OfxAccounts`, `OfxStatementPost` in
  `flaskapp/views/ofx.py`) and `OFXTransaction.params_from_ofxparser_transaction()`.
  Keep `OFXStatement`, `OFXTransaction`, the `/ofx` page and its AJAX routes,
  reconciliation, `ofx.js`, `Account.ofx_statement`, stale-data notifications and
  `negate_ofx_amounts`.
- **Rationale**: `plaid_updater.py` writes `OFXStatement`/`OFXTransaction` rows
  directly (it imports neither `ofxapi` nor `ofxparse`) and applies
  `account.negate_ofx_amounts`; `docs/source/plaid.rst` states that Plaid uses the same
  models and views. Removing those would remove Plaid.
- **Alternatives considered**: Renaming the OFX models/tables/page to neutral names
  ("downloaded transactions"). Rejected for this change: it needs a table-rename
  migration, URL changes and touches most of the application, with no functional gain;
  it can be its own issue.

## R2. Account columns

- **Decision**: Drop `accounts.vault_creds_path`, `accounts.ofxgetter_config_json` and
  `accounts.ofx_cat_memo_to_name` in a new migration whose `down_revision` is the
  current head `2d881fa466fe`. Downgrade re-adds them exactly as the base schema
  declared them: `ofx_cat_memo_to_name tinyint(1) NULL` (`sa.Boolean()`),
  `vault_creds_path varchar(254) NULL` (`sa.String(254)`), `ofxgetter_config_json text
  NULL` (`sa.Text()`), each positioned after the column it followed originally
  (`description`, `ofx_cat_memo_to_name`, `vault_creds_path`) to keep `SHOW CREATE
  TABLE` identical after a round-trip.
- **Rationale**: Every read of the three columns is in removed code (`ofxapi/local.py`,
  `ofxgetter.py`) or in the account form/handler that only stores them. Plaid never
  reads them. Leaving dead columns would violate FR-004 and keep them in the API.
- **Alternatives considered**: Keep the columns but hide them (rejected: dead data in
  the model, API and migrations-verify baseline). Keep `ofx_cat_memo_to_name`
  (rejected: its only consumer is `OfxApiLocal.update_statement_ofx`, which is removed).

## R3. Dependencies

Checked with `pip show` in the project venv (`Required-by`):

| Package | Only needed by | Decision |
|---|---|---|
| `hvac` | Vault client | remove |
| `keyring` | vendored ofxclient config | remove |
| `SecretStorage` | keyring backend | remove |
| `ofxhome` | vendored ofxclient CLI | remove |
| `ofxparse` | OFX parsing | remove |
| `beautifulsoup4`, `lxml` | also `wishlist`, `brow`, `prime_rate.py` | keep |
| `six` | also `python-dateutil` | keep |
| `cryptography`, `cffi`, `pycparser` | also PyMySQL `caching_sha2_password` auth | keep |
| `requests` | also `brow`, `addtrans`, `prime_rate` | keep |

`appdirs`, `asn1crypto`, `httplib2`, `python-editor` are pinned but not imported by
anything in-tree or required by another pin. They are not OFX/Vault/keychain
dependencies, so removing them is outside this issue's scope; noted for a follow-up.

## R4. Settings

- **Decision**: Delete `STATEMENTS_SAVE_PATH`, `TOKEN_PATH`, `VAULT_ADDR` from
  `settings.py` (both the `_STRING_VARS` list and the documented defaults),
  `settings_example.py` and `tests/fixtures/test_settings.py`.
- **Rationale**: `settings.py` only copies names it lists from the settings module and
  environment, so a leftover definition is simply never read — FR-003's "ignored
  without preventing startup" needs no extra code. A unit test will pin that.

## R5. Tests

- `tests/acceptance/flaskapp/views/test_ofx.py`: delete the (already
  `@pytest.mark.skip('Deprecated, will be removed')`) `TestOfxApi` class and its
  now-unused imports; the page/modal tests stay. Add a small check that
  `/api/ofx/accounts` is gone (404).
- `tests/unit/models/test_ofx_transaction.py`: remove the
  `params_from_ofxparser_transaction` tests (and the `ofxparse` import); keep any
  others.
- `tests/fixtures/CreditOne_2017-07-28_05-30-00.ofx`: delete (only `TestOfxApi` used it).
- `tests/fixtures/sampledata.py` and the tests that construct `Account(...)` with the
  removed kwargs (`test_interest.py`, `test_base_template.py`, `test_reconcile.py`,
  `test_index.py`, `test_biweeklypayperiod.py`, `test_currency_normalization.py`,
  `test_payperiods.py`): drop those kwargs/keys.
- `tests/acceptance/flaskapp/views/test_accounts.py` (74 references): remove the three
  fields from form fills and DB assertions and from expected modal field lists; keep
  every other assertion.
- `tests/docker_build.py`: drop the three OFX command checks.
- New migration test `tests/migrations/test_migration_<rev>.py` (`MigrationTest`):
  `data_setup` inserts an account with all three columns populated plus other fields;
  `verify_before` asserts the columns exist and other values are intact;
  `verify_after` asserts they are gone and other values are intact.
- `premigration_db_state.sql` is the historic base schema and is not edited.

## R6. Docs and generated docs

- Delete `docs/source/ofx.rst` and its `index.rst` toctree entry; delete the apidoc
  stubs for removed modules (`biweeklybudget.backfill_ofx.rst`,
  `biweeklybudget.ofxgetter.rst`, `biweeklybudget.ofxapi*.rst` (4),
  `biweeklybudget.screenscraper.rst`, `biweeklybudget.vault.rst`) and update
  `biweeklybudget.rst`. `sphinx-apidoc -f` regenerates but never deletes stale stubs.
- Update README, `getting_started.rst` (Vault prerequisites, "Running ofxgetter in
  Docker", entrypoint list), `concepts.rst`, `plaid.rst` (drop the `:ref:` to the
  removed page; keep the explanation that Plaid uses the "OFX" models),
  `flask_app.rst` (Vault mention), `http_api.rst` (account fields; delete the "OFX
  Statements" section), `CLAUDE.md`, and the `make_screenshots.py` OFX page
  description ("imported from OFX statements").
- Drop `biweeklybudget/vendored` from the `sphinx-apidoc` excludes in `tox.ini` and the
  `vendored/*` entries in `setup.cfg`, `pytest.ini`, `.coveragerc`; drop the
  `www.ofx.net` linkcheck ignore in `docs/source/conf.py` if nothing links there.
- Screenshots: `account1` and `account1-plaid` capture the Edit Account modal and will
  change; regenerate and commit those PNGs (maintainer preference: changed
  screenshots are committed in the PR).

## R7. Constitution

- **Decision**: PATCH amendment 2.1.1 → 2.1.2 changing the Secrets bullet to drop
  "OFX credentials live in Hashicorp Vault", committed as its own commit.
- **Rationale**: Governance requires amendments in their own change; the rule it
  states becomes false once Vault is gone. Nothing required changes, so PATCH.
