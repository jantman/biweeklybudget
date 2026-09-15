# Quickstart: Validating the OFX / Vault / Keychain Removal

Run from the worktree root. Test commands follow `CLAUDE.md` and the project memory
notes: tox from the main checkout's venv, output redirected to a scratchpad file.

## Prerequisites

- MariaDB test container on port 13306 (see `CLAUDE.md`, "Test Database Setup"), with
  the `budgettest` and `alembicLeft` databases created by `dev/setup_test_db.py`.
- Chrome + chromedriver for acceptance and screenshots.
- Docker for the `docker` tox env.

## 1. Nothing references the removed code

```bash
git grep -n -i -E 'ofxgetter|backfill_ofx|ofxbackfiller|ofxclient|ofxapi|screenscraper|hvac|keyring|secretstorage|ofxparse|ofxhome|vault_creds_path|ofx_cat_memo|VAULT_ADDR|TOKEN_PATH|STATEMENTS_SAVE_PATH|\bVault\b' \
  -- ':!CHANGES.rst' ':!specs/' ':!biweeklybudget/tests/fixtures/premigration_db_state.sql' \
     ':!biweeklybudget/alembic/versions/'
```

Expected: no hits. The new migration file (under `alembic/versions/`, excluded
above) and `premigration_db_state.sql` mention the removed columns and are the only
permitted places. `CHANGES.rst` keeps its history and gains the removal entry.

## 2. Package install and console scripts

```bash
python3.14 -m venv /tmp/.../scratchpad/v && /tmp/.../scratchpad/v/bin/pip install -e .
/tmp/.../scratchpad/v/bin/pip show hvac keyring SecretStorage ofxhome ofxparse   # all "not found"
ls /tmp/.../scratchpad/v/bin | grep -E 'ofx'                                      # nothing
/tmp/.../scratchpad/v/bin/addtrans --help                                          # works
```

## 3. Migration round-trip and schema match

```bash
tox -e migrations > $SCRATCH/migrations.txt 2>&1
```

Expected: the new migration's `MigrationTest` passes (columns present before, absent
after, present again after downgrade; the account row's other values are unchanged
throughout), and `test_model_and_migration_schemas_are_the_same` passes.

## 4. Unit and acceptance suites

```bash
tox -e py314 > $SCRATCH/py314.txt 2>&1
tox -e acceptance > $SCRATCH/acceptance.txt 2>&1
```

Expected: all pass. In particular the Accounts acceptance tests show the modal
without the three fields and round-trip the rest; `GET /api/ofx/accounts` returns 404.

## 5. Docs, jsdoc, screenshots, Docker

```bash
tox -e docs > $SCRATCH/docs.txt 2>&1
tox -e docker > $SCRATCH/docker.txt 2>&1
tox -e screenshots > $SCRATCH/screenshots.txt 2>&1   # never concurrently with docs
```

Expected: docs build with no new warnings about missing references to the removed
modules; the Docker image builds and its script checks pass without the three OFX
commands; the `account1` Edit Account screenshot no longer shows the three fields.

## 6. Manual smoke check (optional)

With `flask rundev` against the sample data: open `/accounts`, edit an account, save;
open `/ofx`, `/reconcile`, `/` and `/plaid-update` and confirm they render as before.
Start the app with `VAULT_ADDR=http://x TOKEN_PATH=/x STATEMENTS_SAVE_PATH=/x` exported
and confirm it starts.
