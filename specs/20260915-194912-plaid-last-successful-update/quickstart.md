# Quickstart: validating the Plaid Item last-successful-update time

## Automated

All commands run from the worktree root with the MariaDB test container from `CLAUDE.md`
running, and with tox invoked from the main checkout's venv (see project memory on tox in
worktrees).

Targeted:

```bash
# the extraction helper
tox -e py314 -- biweeklybudget/tests/unit/test_utils.py -k plaid_last_successful_update
# the two writers
tox -e py314 -- biweeklybudget/tests/unit/test_plaid_updater.py -k TestDoItem
tox -e py314 -- biweeklybudget/tests/unit/flaskapp/views/test_plaid.py -k TestPlaidUpdateItemInfo
# the rendered table, both the value and the placeholder
tox -e acceptance -- -k "TestPlaidUpdateView and test_4_table"
```

Note: `TestDoItem`'s tests fail when `test_plaid_updater.py` is run entirely on its own (a
backref is not yet configured); run the file with the rest of the suite, or accept that
those three failures are pre-existing and unrelated.

The Test Gate for this feature (Constitution II, and III for the schema change):

```bash
tox -e py314          # unit
tox -e acceptance     # acceptance
tox -e migrations     # migration head matches the models, both directions
tox -e docs           # documentation builds clean
tox -e docker         # schema change ships in the image
```

Redirect each run's output to a file rather than piping to `tail`, per `CLAUDE.md`.

### Migration, both directions

```bash
alembic -c biweeklybudget/alembic/alembic.ini upgrade head
alembic -c biweeklybudget/alembic/alembic.ini downgrade -1
alembic -c biweeklybudget/alembic/alembic.ini upgrade head
```

Expected: the column appears, disappears, and reappears, with the Plaid Item rows intact
throughout. Confirm directly:

```bash
mysql -h 127.0.0.1 -P 13306 -u root -pdbroot budgettest \
  -e 'DESCRIBE plaid_items; SELECT item_id, last_updated, last_successful_update FROM plaid_items;'
```

## Manual, against a running instance

With the app running and at least one Plaid Item linked (see `docs/source/plaid.rst`):

1. Open `/plaid-update`. The **Plaid Items** panel's table now has a **Last Successful
   Update** column between **Last Polled** and **Update**.

2. Before any update has run since the upgrade, every row reads `unknown` in that column —
   not a blank cell.

3. Click **Update Item Information from Plaid**. The page reloads; each Item for which Plaid
   reports a time now shows it, relative ("2 hours ago"). No transaction download was needed.

4. Run a transaction update (check some Items, **Update Transactions**), then return to
   `/plaid-update`. The updated Items' **Last Polled** reads `now` while **Last Successful
   Update** shows Plaid's own, generally older, time — which is the whole point of the
   feature: the two answer different questions.

5. Link a brand-new Item that Plaid has not yet refreshed, or use a sandbox Item in
   `ITEM_LOGIN_REQUIRED`. Its row shows `unknown` and the update still reports success for
   everything else — the missing time is not an error.

## Screenshots

The `plaid-update` screenshot shows this table and therefore changes:

```bash
tox -e screenshots
```

Then commit `docs/source/plaid-update.png` and `docs/source/plaid-update_sm.png`.

**Do not run `tox -e docs` in the same invocation as `screenshots`, or after it before the
PNGs are committed** — the `docs` environment deletes the generated PNGs.
