# Quickstart: validating Plaid Update Check All / Uncheck All

## Automated

The acceptance tests drive the page in a browser against the test database (never a
real one). From a checkout with the project's tox:

```bash
tox -e acceptance -- biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py \
  > /path/to/scratchpad/acceptance-plaid.txt 2>&1
```

Expected: every `TestPlaidUpdateView` test passes, including the new ones for
[the contract](contracts/plaid-update-ui.md):

- **Uncheck All** leaves every item checkbox unchecked and the URL unchanged.
- **Check All** after partial unchecking leaves every item checkbox checked.
- After **Uncheck All** plus checking one item, the form would submit only that item.

Then run the complete unit and acceptance suites (Constitution II) and `tox -e docs`.

## Manual

1. Start the app against a database with at least two Plaid Items
   (`flask rundev`, see `CLAUDE.md`) and open `/plaid-update`.
2. All items in "Plaid Update Transactions" are checked. Click **Uncheck All**: all
   clear, and the page neither reloads nor scrolls.
3. Check one item and click **Check All**: all are checked again.
4. Click **Uncheck All**, check one item, click **Update Transactions**: the results page
   lists only that item.
