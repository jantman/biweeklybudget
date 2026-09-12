# Quickstart: validating the `/plaid-update` status code

## Automated

Unit tests (need the MariaDB test container described in `CLAUDE.md`):

```bash
tox -e py314 -- biweeklybudget/tests/unit/flaskapp/views/test_plaid.py -k TestPlaidUpdate
```

Expected: every `TestPlaidUpdate` test passes, including the status-code cases for each
format (failing → 500, all-successful → 200, no results → 200).

The full Test Gate (Constitution II): `tox -e py314`, `tox -e acceptance`, `tox -e docs`,
all run to completion and passing.

## Manual, against a running instance with Plaid Items

With the app at `http://127.0.0.1:8080` (see `docs/source/plaid.rst`):

1. All Items healthy:

   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' -H 'Accept: text/plain' \
     'http://127.0.0.1:8080/plaid-update?item_ids=ALL'
   ```

   Expected: `200`.

2. At least one Item failing (in the Plaid sandbox, `sandbox_item_reset_login` puts an
   Item into `ITEM_LOGIN_REQUIRED`, as `test_plaidlink.py::test_16` does):

   ```bash
   curl --fail -H 'Accept: text/plain' 'http://127.0.0.1:8080/plaid-update?item_ids=ALL'; echo "exit=$?"
   ```

   Expected: `curl` exits 22 (HTTP error). Without `--fail`, the body still shows the
   failing Item's line and `1 account(s) failed`.

3. The same with `-H 'Accept: application/json'` returns 500 and a JSON list with
   `"success": false` for the failing Item.

4. In a browser, updating with a failing Item selected still shows the results page
   listing the failure. The browser's network panel shows status 500.
