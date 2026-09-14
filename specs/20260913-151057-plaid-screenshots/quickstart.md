# Quickstart: validating Plaid Screenshots

## Prerequisites

- A MariaDB test container and `DB_CONNSTRING` pointing at it (see `CLAUDE.md`, "Test
  Database Setup"). The screenshot run drops and reloads that database.
- Chrome and chromedriver.
- No Plaid credentials: leave `PLAID_*` unset to prove FR-005.

## 1. Generate the screenshots

```bash
tox -e screenshots
```

Expected: the run finishes successfully. `docs/source/` contains `plaid-update.png`,
`account1-plaid.png`, `plaid-update-result.png` and their `_sm.png` thumbnails, and
`docs/source/screenshots.rst` has the three sections after "OFX Transactions"
([contract](contracts/screenshots.md)).

Check each image:

- `plaid-update.png`: both sample Items in both tables.
- `account1-plaid.png`: the Plaid Account selector with `Inst1 / Acct1 (foo)` visible.
- `plaid-update-result.png`: an Inst1 row with counts and statement IDs, an Inst2 row with
  the sample error, and a Total row with "1 Failed".

Then discard the regenerated files (they are committed at release):
`git checkout -- docs/source/ && git clean -f docs/source/`.

## 2. Tests and docs

```bash
tox -e py314        # includes the result-template unit test
tox -e acceptance
tox -e docs         # plaid.rst link to the Screenshots page resolves
```
