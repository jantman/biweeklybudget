# Research: Plaid Update Reports Failure In Its Status Code

## R1 — Which non-200 status

**Decision**: HTTP 500 Internal Server Error when one or more Items fail.

**Rationale**: The issue asks for "non-200". The consumers that motivate it (`curl
--fail`, cron wrappers, monitoring checks) treat any 4xx/5xx as failure, so the code only
has to be an error code that honestly describes the situation. A failed Item means the
server could not complete the requested work, and nothing is wrong with the request, which
rules out 4xx. 500 is the generic code for that, and it's accurate whatever the cause:
`PlaidUpdater._do_item()` catches *every* exception, whether an expired Plaid login, a
Plaid API error, or a local database error.

**Alternatives considered**:

- **207 Multi-Status**: made for per-item results, but it is a 2xx. `curl --fail` and most
  monitors would still report success, which defeats the issue.
- **502 Bad Gateway**: says the fault is upstream. Often true here (Plaid), but not
  always, since local errors are caught the same way.
- **Different codes for partial vs. total failure**: adds a distinction no identified
  caller needs. The body already reports exactly which Items failed.

## R2 — Which response formats get the status

**Decision**: All three (plain text, JSON, browser HTML), from one status computed before
the format branch.

**Rationale**: The issue names the endpoint, not a format. Browsers render a 500 page's
body normally, so the interactive results page looks the same, and one rule is easier
to document and test than per-format rules.

**Alternatives considered**: API formats only (text/JSON), leaving HTML at 200. Rejected
because it makes the status depend on the `Accept` header for no user benefit.

## R3 — Effect on existing tests

- **Unit** (`tests/unit/flaskapp/views/test_plaid.py::TestPlaidUpdate`): the existing
  `_update` tests assert `res == <body>`. With a tuple return they must assert
  `res == (<body>, <status>)`. `test_update_template` and the two `test_update_plain*`
  tests contain a failed result (→ 500). `test_update_json` is all-successful (→ 200).
  The `get`/`post` tests mock `_update` and pass its return value through, so they are
  unaffected.
- **Acceptance**: the helper (`tests/acceptance_helpers.py`) never inspects HTTP status,
  and Selenium cannot observe it. `test_plaidlink.py::test_17_try_update_transactions_expect_error`
  drives a failing update through the browser form and asserts the rendered table, which
  is unchanged. That class is also marked `plaid` (it runs only in the `plaid` tox
  environment, which needs sandbox credentials) and is `xfail` only when `CI == 'true'`,
  because the Plaid Link flow fails in headless Chrome.
- **Unit test for `PlaidUpdater`** (`tests/unit/test_plaid_updater.py`): unaffected; the
  updater doesn't change.

## R4 — Flask tuple returns

Flask 3.1 accepts `(body, status)` from a view, where the body is a `str`, a `Response`
(as returned by `jsonify`), or template output. The status is applied to the response it
would have built anyway, so the body and content type don't change. No need for
`make_response`.
