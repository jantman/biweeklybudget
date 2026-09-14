---

description: "Task list for removing OFX downloading, Vault and Keychain"
---

# Tasks: Remove OFX Downloading, Vault and Keychain

**Input**: Design documents from `specs/20260914-054238-remove-ofx-vault/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/removed-interfaces.md, quickstart.md

**Tests**: Included. The constitution (Principle II, III) requires tests for new
behaviour and a round-trip test for every migration.

**Organization**: Grouped by user story. All tasks belong to milestone **M1**; commit
prefix `Remove OFX Vault - M1.<n>`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

---

## Phase 1: Setup

**Purpose**: Test infrastructure needed by later phases

- [X] T001 Start the MariaDB test container on port 13306, export the env vars from `CLAUDE.md` ("Test Database Setup"), run `dev/setup_test_db.py`, and `touch .tox/acceptance/liveserver.log` (see memory note on tox in worktrees)

---

## Phase 2: Foundational

None. Each story below edits separate code; US2's model change and US3's form change
touch the same field names but are ordered US2 → US3.

---

## Phase 3: User Story 1 - Install and run without OFX, Vault or keychain dependencies (Priority: P1) 🎯 MVP

**Goal**: The OFX download/import stack, its console scripts, HTTP endpoints and
dependencies are gone; the app and remaining scripts work.

**Independent Test**: `pip install -e .` in a clean venv installs none of `hvac`,
`keyring`, `SecretStorage`, `ofxhome`, `ofxparse` and no `ofx*` scripts;
`GET /api/ofx/accounts` returns 404; `/ofx`, `/reconcile`, `/accounts`, `/` render.

### Tests for User Story 1

- [X] T002 [US1] Add an acceptance test class `TestOfxApiRemoved` in `biweeklybudget/tests/acceptance/flaskapp/views/test_ofx.py` asserting `requests.get(base_url + '/api/ofx/accounts').status_code == 404` and that a POST to `/api/ofx/statement` returns 404 or 405; delete the skipped `TestOfxApi` class and the imports only it used (`apiclient`, `DuplicateFileException`, `OfxParser`, `BytesIO`, `fixturedir`, etc. — verify each with pyflakes)
- [X] T003 [P] [US1] Remove the `params_from_ofxparser_transaction` tests and the `ofxparse` import from `biweeklybudget/tests/unit/models/test_ofx_transaction.py` (delete the file if nothing else remains)

### Implementation for User Story 1

- [X] T004 [US1] Delete `biweeklybudget/ofxgetter.py`, `biweeklybudget/backfill_ofx.py`, `biweeklybudget/vault.py`, `biweeklybudget/screenscraper.py`, the `biweeklybudget/ofxapi/` package, the whole `biweeklybudget/vendored/` tree, and `biweeklybudget/tests/fixtures/CreditOne_2017-07-28_05-30-00.ofx` (`git rm -r`)
- [X] T005 [US1] In `biweeklybudget/flaskapp/views/ofx.py` delete the `OfxAccounts` and `OfxStatementPost` classes, their two `app.add_url_rule` calls, and now-unused imports (`OfxApiLocal`, `DuplicateFileException`, `pickle`, `b64decode`, `request` if unused); keep `OfxView`, `OfxTransView`, `OfxTransAjax`, `OfxAjax` and their routes
- [X] T006 [US1] Delete `OFXTransaction.params_from_ofxparser_transaction()` from `biweeklybudget/models/ofx_transaction.py` and fix the `OFXStatement.acct_type` comment in `biweeklybudget/models/ofx_statement.py` that points at ofxparser
- [X] T007 [US1] Remove the `ofxgetter`, `ofxbackfiller` and `ofxclient` console scripts from `setup.py` (and `ofx` from its `keywords` only if it reads as downloading support; the app still shows OFX data, so keeping it is acceptable)
- [X] T008 [P] [US1] Remove `hvac`, `keyring`, `SecretStorage`, `ofxhome`, `ofxparse` from `requirements.txt`; keep all others (research R3)
- [X] T009 [P] [US1] Remove the `biweeklybudget/vendored/*` entries from `setup.cfg`, `pytest.ini`, `.coveragerc`, and `biweeklybudget/vendored` from the `sphinx-apidoc` exclude list in `tox.ini`
- [X] T010 [P] [US1] Remove the `ofxclient`, `ofxbackfiller` and `ofxgetter` entries from `test_cmds` in `biweeklybudget/tests/docker_build.py`; check the rest of that file for any other OFX/Vault handling
- [X] T011 [US1] `git grep` for `ofxgetter|backfill_ofx|ofxapi|screenscraper|vendored|ofxparse|ofxhome|hvac|keyring|vault` in `biweeklybudget/` (excluding alembic versions and the premigration SQL) and fix any remaining code reference outside the files handled by US2/US3

**Checkpoint**: App imports and starts; `py314` collection succeeds.

---

## Phase 4: User Story 2 - Upgrade an existing installation cleanly (Priority: P1)

**Goal**: The three OFX-only Account columns and three settings are removed; a
reversible migration drops the columns without touching other data; leftover settings
are ignored.

**Independent Test**: `tox -e migrations` passes (round-trip + schema match); a unit
test shows leftover settings are ignored.

### Tests for User Story 2

- [X] T012 [P] [US2] Add unit test(s) in `biweeklybudget/tests/unit/test_settings_removed_ofx.py` (AGPL header) that reload `biweeklybudget.settings` with `VAULT_ADDR`, `TOKEN_PATH`, `STATEMENTS_SAVE_PATH` set in the environment and in a fake settings module, and assert the reload succeeds; with the environment variables, `biweeklybudget.settings` has none of the three attributes (a settings module's public names are all copied by `settings.py`, so for that case only a clean startup is asserted; nothing reads them). Model the reload/monkeypatch approach on `biweeklybudget/tests/unit/test_settings_fuel_levels.py`
- [X] T013 [P] [US2] Add `biweeklybudget/tests/migrations/test_migration_<rev>.py` (AGPL header, `@pytest.mark.migrations`, `MigrationTest` subclass, `migration_rev = '<rev>'`): `data_setup` inserts one `accounts` row with `name`, `description`, `acct_type`, `is_active`, `negate_ofx_amounts`, `ofx_cat_memo_to_name=1`, `vault_creds_path`, `ofxgetter_config_json` set; `verify_before` asserts the three columns exist and the other values are as inserted; `verify_after` asserts the three columns are absent and the other values are unchanged

### Implementation for User Story 2

- [X] T014 [US2] Remove `STATEMENTS_SAVE_PATH`, `TOKEN_PATH`, `VAULT_ADDR` from `_STRING_VARS` and their documented defaults in `biweeklybudget/settings.py`, and from `biweeklybudget/settings_example.py` and `biweeklybudget/tests/fixtures/test_settings.py`
- [X] T015 [US2] In `biweeklybudget/models/account.py` remove the `ofx_cat_memo_to_name`, `vault_creds_path`, `ofxgetter_config_json` columns and `for_ofxgetter`, `ofxgetter_config`, `set_ofxgetter_config`; drop the `json` import (and `hybrid_property` or others) if now unused
- [X] T016 [US2] Create `biweeklybudget/alembic/versions/<rev>_remove_ofxgetter_account_fields.py` (new 12-hex revision id, `down_revision = '2d881fa466fe'`, docstring citing issue #265): `upgrade()` drops the three columns; `downgrade()` re-adds `ofx_cat_memo_to_name` `sa.Boolean()` after `description`, `vault_creds_path` `sa.String(254)` after it, `ofxgetter_config_json` `sa.Text()` after that, all `nullable=True` (see data-model.md; use `mysql_after` / `op.execute` as other migrations do if `after` is needed). Use the same `<rev>` in T013
- [X] T017 [US2] Remove the three fields from `biweeklybudget/tests/fixtures/sampledata.py` and from `Account(...)` constructions in `biweeklybudget/tests/unit/test_interest.py`, `biweeklybudget/tests/acceptance/test_biweeklypayperiod.py`, `biweeklybudget/tests/acceptance/flaskapp/views/test_base_template.py`, `test_index.py`, `test_reconcile.py`, `test_payperiods.py`, `test_currency_normalization.py` (all under `biweeklybudget/tests/acceptance/flaskapp/views/`)
- [X] T018 [US2] Run `tox -e migrations`, then `alembic upgrade head` / `downgrade -1` / `upgrade head` by hand against the test DB, and inspect `SHOW CREATE TABLE accounts` before and after the round-trip (done by the migration test, which asserts the restored columns' positions; `tox -e migrations`: 9 passed)

**Checkpoint**: `tox -e migrations` green.

---

## Phase 5: User Story 3 - Account forms show only settings that do something (Priority: P2)

**Goal**: Add/Edit Account modal and `POST /forms/account` no longer have the three
fields; all other fields round-trip.

**Independent Test**: Accounts acceptance tests pass with the three fields absent from
the modal and from DB assertions.

- [X] T019 [US3] In `biweeklybudget/flaskapp/views/accounts.py` remove the `ofxgetter_config_json` JSON validation and the three assignments in `submit()`; drop the `json` import if unused. Make sure a request that still carries the three keys is not rejected
- [X] T020 [US3] In `biweeklybudget/flaskapp/static/js/accounts_modal.js` remove the `addCheckbox('account_frm_ofx_cat_memo', …)`, `addText('account_frm_vault_creds_path', …)`, `addTextArea('account_frm_ofxgetter_config_json', …)` builder calls and the matching lines in `accountModalDivFillAndShow()`
- [X] T021 [US3] Update `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py`: remove the three fields from form fills, expected-field lists and DB assertions; drop any test whose sole purpose was the ofxgetter JSON validation; add an assertion that the modal has no `account_frm_vault_creds_path`, `account_frm_ofxgetter_config_json` or `account_frm_ofx_cat_memo` element
- [X] T022 [US3] Update the Account request-field list in `docs/source/http_api.rst` (`POST /forms/account`) to drop the three fields

**Checkpoint**: `tox -e acceptance -- -k test_accounts` green.

---

## Phase 6: User Story 4 - Documentation describes only what exists (Priority: P2)

**Goal**: No README/docs/CLAUDE.md instructions for OFX downloading, Vault, keychain or
screen scraping; Plaid presented as the transaction source.

**Independent Test**: `tox -e docs` builds; the quickstart §1 grep returns nothing.

- [X] T023 [P] [US4] `git rm docs/source/ofx.rst` and remove it from the toctree in `docs/source/index.rst`
- [X] T024 [P] [US4] `git rm` the apidoc stubs `docs/source/biweeklybudget.backfill_ofx.rst`, `biweeklybudget.ofxgetter.rst`, `biweeklybudget.ofxapi.rst`, `biweeklybudget.ofxapi.exceptions.rst`, `biweeklybudget.ofxapi.local.rst`, `biweeklybudget.ofxapi.remote.rst`, `biweeklybudget.screenscraper.rst`, `biweeklybudget.vault.rst`, and remove them from `docs/source/biweeklybudget.rst`
- [X] T025 [P] [US4] Delete the "OFX Statements" section (`POST /api/ofx/statement`, `GET /api/ofx/accounts`) from `docs/source/http_api.rst` and any links to its anchors
- [X] T026 [P] [US4] `README.rst`: drop the Vault paragraph in "Intended Audience", the Vault note under Requirements, the "OFX Direct Connect" requirement bullets, and change the Main Features bullet to Plaid-only downloading
- [X] T027 [P] [US4] `docs/source/getting_started.rst`: drop Vault from the prerequisites and the Docker/containers notes, delete "Running ofxgetter in Docker", and remove the `ofxbackfiller`/`ofxgetter` entrypoint bullets
- [X] T028 [P] [US4] `docs/source/concepts.rst` (download sources → Plaid only), `docs/source/plaid.rst` (replace the `:ref:\`ofx\`` link with plain text saying OFX downloading was removed; keep the note that Plaid uses the "OFX" models), `docs/source/flask_app.rst` (drop "everything in Vault if it's being used")
- [X] T029 [P] [US4] `docs/make_screenshots.py`: change the OFX page description "Shows transactions imported from OFX statements." to describe downloaded (Plaid) transactions; also `docs/source/screenshots.rst` if it carries the same text
- [X] T030 [P] [US4] `docs/source/conf.py`: remove the `www.ofx.net` linkcheck ignore if no doc links there any more
- [X] T031 [P] [US4] `CLAUDE.md`: remove the three OFX console scripts, the "OFX Direct Connect" transaction-source bullet, `VAULT_ADDR` from key settings, the `vendored/` tree line and "(requires Vault)"; update the Overview sentence about OFX Direct Connect

**Checkpoint**: `tox -e docs` green; quickstart §1 grep clean.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T032 Add the `Unreleased` entry at the top of `CHANGES.rst` (issue #265 link; breaking change; removed commands, `/api/ofx/*` endpoints, three settings, three Account fields/form fields, five dependencies; migration drops the columns; stay on an earlier release to keep OFX downloading) — concise per Principle VI
- [X] T033 Constitution PATCH amendment 2.1.1 → 2.1.2 in `.specify/memory/constitution.md`: Secrets bullet no longer mentions OFX/Vault; Sync Impact Report entry; `Last Amended` 2026-09-14. Commit **on its own** (`Remove OFX Vault - M1.<n>: Amend constitution …`)
- [X] T034 Lint: pycodestyle (max-line-length 100 per `setup.cfg`) and pyflakes over changed Python files in a scratch venv
- [X] T035 Run `tox -e py314` to completion; all pass (output to scratchpad) — 955 passed, 4 skipped
- [X] T036 Run `tox -e acceptance` to completion; all pass (re-run known flaky tests in isolation before blaming the change) — 882 passed, 18 skipped (23 min)
- [ ] T037 Run `tox -e migrations` and `tox -e docker` to completion; all pass
- [X] T038 Run `tox -e docs` and `tox -e jsdoc`; then, not concurrently with docs, `tox -e screenshots`; commit only the changed `docs/source/account1*.png` (and any other screenshot the change touched), reverting unrelated PNG churn — docs OK, jsdoc OK (unrelated jsdoc.*.rst reverted), screenshots OK; committed account1*.png and account1-plaid*.png only
- [X] T039 Run quickstart §1 grep and §2 clean-venv install check; mark tasks complete in this file and commit — grep clean; clean venv has none of the 5 packages or ofx* scripts

---

## Dependencies & Execution Order

- Setup (T001) → everything that runs tests.
- US1 (T002–T011) first: it removes the importers of the Account fields and settings.
- US2 (T012–T018) after US1 (`ofxapi/local.py` and `ofxgetter.py` read the fields).
- US3 (T019–T022) after T015 (model columns gone).
- US4 (T023–T031) after US1–US3 (docs describe the final state); its tasks are mutually parallel.
- Polish (T032–T039) last; T033 is its own commit; T035–T038 are the test gate.

### Parallel Opportunities

- US1: T003, T008, T009, T010 alongside T004–T007.
- US2: T012 and T013 alongside each other and T014.
- US4: T023–T031 all touch different files.

## Implementation Strategy

MVP is US1 (dependency and code removal). US2 must follow in the same PR, since US1 leaves
model fields that nothing uses. US3 and US4 finish the user-visible cleanup. One
milestone, one PR, delivered after the full test gate.
