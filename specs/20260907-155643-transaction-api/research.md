# Phase 0 Research: Transaction API — Name-or-ID Lookup and Console Script

No `NEEDS CLARIFICATION` markers survived the specification. What follows is the record of
the judgement calls made, each with what was rejected and why, per Constitution V.

## D1 — Extend `POST /forms/transaction` rather than add a parallel API endpoint

**Decision**: Teach the existing `TransactionFormHandler` to accept names. Do not add a
second endpoint.

**Rationale**: Issue #322 explicitly allows either ("Either the form handler needs to
resolve names, or a separate API endpoint should sit alongside it"). The existing handler
carries five non-obvious validation rules — non-empty description, non-zero amount, budget
amounts summing to the transaction amount, new transactions may not use inactive budgets
(with a distinct rule for existing ones), and only credit accounts may be paid. A parallel
endpoint either duplicates all five, and they drift the first time one is corrected, or
delegates to the same handler, at which point it is a URL alias rather than a second
endpoint. `docs/source/http_api.rst` already documents this endpoint as *the* scriptable
way to create a Transaction; adding a second would leave the docs describing two ways to
do one thing.

**Alternatives considered**:
- *New `POST /api/transaction` with its own validation*: rejected, duplicated rules.
- *New endpoint that resolves names then internally calls the form handler*: rejected as
  an alias with extra surface; the same result is reached by making the one endpoint
  accept both forms.

## D2 — Resolve inside `validate()`, rewriting `data` to canonical IDs in place

**Decision**: At the top of `TransactionFormHandler.validate()`, resolve the three
identifying fields and replace their values in `data` with numeric ID strings. `submit()`
is not modified.

**Rationale**: `FormHandlerView.post()` passes the *same* `data` dict to `validate()` and
then `submit()`, and the class already normalizes in place before validation —
`normalize_currency()` rewrites `data['amount']` from `$1,234.56` to `1234.56` for exactly
this reason. Following that established pattern means `submit()`'s `int(data['account'])`
and `db_session.query(Budget).get(int(bid))` keep working unchanged, and every rule below
the resolution point continues to operate on IDs. Backward compatibility for ID callers
then falls out of the diff — an all-digits value that hits by ID is rewritten to itself —
rather than depending on tests to notice a regression.

**Alternatives considered**:
- *Resolve in both `validate()` and `submit()`*: rejected. Two lookups of the same value
  can disagree if the database changes between them, and it doubles the code to keep
  correct.
- *Add a new overridable `normalize_references()` hook on `FormHandlerView`*: rejected for
  now. Only one handler needs it; adding a base-class hook for a single caller is surface
  without a user. If a second form handler needs it later, promoting the code is easy.
- *Resolve client-side in the console script only*: rejected outright — it would leave the
  HTTP API, which is the thing issue #322 is about, still unusable by anything but that
  one script.

## D3 — Digits-first resolution with a name fallback

**Decision**: A value whose stripped form consists only of ASCII digits is looked up as a
primary key. If, and only if, no record has that ID, the same value is then looked up as a
name. Any other value is looked up only as a name.

**Rationale**: The overwhelmingly common case is an integer ID from the web UI, and it must
stay a single indexed primary-key fetch with no ambiguity. Nothing in the schema prevents
an Account or Budget being named `"2024"`, though, and a rule of "digits are always IDs,
full stop" would make such a record permanently unreachable by name with no recourse and a
confusing error. The fallback costs one extra query only on the path that was about to
fail anyway.

**Residual ambiguity, accepted and documented**: if Budget 12 exists *and* a different
Budget is named `"12"`, the value `12` resolves to Budget 12. This is the right precedence
(IDs are the pre-existing meaning of that field) and it is stated in the API
documentation. It cannot be resolved automatically without inventing a disambiguating
syntax, which is not worth it for a case that requires deliberately naming a budget after
another budget's ID.

**Alternatives considered**:
- *Separate fields, e.g. `account_id` and `account_name`*: rejected. It changes the
  request shape for existing callers or leaves three fields where there was one, and the
  issue asks for one field accepting either.
- *A type prefix, e.g. `id:12` vs `name:12`*: rejected as ceremony imposed on every caller
  to serve a case that will most likely never occur.
- *Digits are always IDs, never names*: rejected as above.

## D4 — Case-insensitive, whitespace-stripped, exact name matching

**Decision**: Strip leading/trailing whitespace, compare case-insensitively, require the
whole name to match. `Account.name` and `Budget.name` both carry unique indexes, so at
most one record can match.

**Rationale**: Names are typed at a shell prompt, where stray case and trailing spaces are
routine and mean nothing. Partial, prefix or fuzzy matching is a different matter: this
endpoint moves money, and a typo that quietly lands on the nearest budget is worse in
every way than one that fails with an error. Case-insensitivity is implemented explicitly
with `func.lower()` rather than relying on the database's default collation being
case-insensitive, so the behaviour is a property of the code and is pinned by a test.

**Alternatives considered**:
- *Case-sensitive exact match*: rejected as needlessly hostile to a CLI caller.
- *Prefix or `LIKE` matching*: rejected; see above.
- *Rely on MySQL's `utf8mb4_general_ci` collation for case-insensitivity*: rejected as
  correct today but silently dependent on a setting nothing in this feature controls.

## D5 — The income-budget `(income)` display suffix is not special-cased

**Decision**: The web UI labels income budgets `Name (income)` in its select boxes. A
caller must supply the stored name, `Name`. This is documented, not accommodated.

**Rationale**: The suffix is built by the view for display (`'%s (income)' % b.name` in
`TransactionsView.get()`); it is not data. Stripping it during resolution would mean a
budget genuinely named `"Bonus (income)"` could not be addressed, and would embed a
presentation detail in a lookup function. Documenting it costs one sentence.

## D6 — Console entry point named `addtrans`, in `biweeklybudget/addtrans.py`

**Decision**: `addtrans = biweeklybudget.addtrans:main`, module at package top level.

**Rationale**: Every existing entry point in `setup.py` is lowercase with no separator —
`loaddata`, `ofxgetter`, `ofxbackfiller`, `initdb`, `wishlist2project` — and every one has
its module at package top level. A hyphenated `add-transaction` would be the only entry
point in the project that needed shell quoting rules explained.

**Alternatives considered**: `add-transaction`, `create-transaction`, `mktrans` — all
rejected against the established convention.

## D7 — The script talks HTTP, and takes its address from flag, env, then default

**Decision**: The script POSTs JSON to `{base_url}/forms/transaction` using `requests`.
The base URL comes from `-U/--url`, else the `BIWEEKLYBUDGET_URL` environment variable,
else `http://127.0.0.1:8080`.

**Rationale**: Talking to the database directly would be simpler and would prove nothing —
the entire point of the proof of concept is that the HTTP contract is usable. `requests`
is already in `requirements.txt`, so this adds no dependency. Flag-then-environment-then-
default is what every other configurable in this project does, and `http://127.0.0.1:8080`
is the address every example in `docs/source/http_api.rst` already uses. There is no
authentication to handle: the application is documented as localhost-only and the endpoint
is already unauthenticated.

**Alternatives considered**:
- *A new `settings.py` constant for the base URL*: rejected. Settings are for the server's
  own configuration; a client pointing at a server is a client-side concern, and requiring
  a settings module would make the script unusable from a machine that only has `requests`.
- *Direct database access via `db_session`*: rejected; see above.

## D8 — Amount strings are sent verbatim for the server to normalize

**Decision**: The script does not parse currency. It sends whatever the user typed and
lets `FormHandlerView.normalize_currency()` interpret it.

**Rationale**: The server already accepts `$1,234.56`, `1,234.56` and `1234.56` and has
tests pinning that (issue #323). Parsing client-side would create a second, subtly
different definition of what an amount is. The one convenience the script does add is
local rather than interpretive: with exactly one `--budget` given and no explicit split
amount, the transaction amount string is copied to that budget, because "all of it" is
unambiguous.

## Existing-code findings that shaped the above

- `FormHandlerView.post()` (`biweeklybudget/flaskapp/views/formhandlerview.py`) accepts a
  JSON body or form-encoded data, calls `normalize_currency(data)`, then `validate(data)`,
  then `submit(data)` — all on one dict, which is what makes D2 work. It returns HTTP 200
  with `{"success": false, ...}` for validation failures, so the console script must key
  off the body, not the status code.
- `TransactionFormHandler.submit()` reads `data['account']`, `data['credit_payment_acct']`
  and the keys of `data['budgets']` as integers. Canonicalizing in `validate()` is
  therefore sufficient and no change to `submit()` is needed.
- `Account.name` and `Budget.name` are both `Column(String(50), unique=True, index=True)`,
  so name lookups are indexed and cannot be ambiguous.
- `requests` is already listed in `requirements.txt`.
- Acceptance tests already POST directly to `base_url + '/forms/transaction'` in
  `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py`; the new endpoint
  tests follow that existing pattern rather than introducing a new one.
- The current version is **1.10.0**, not the 1.6.0 quoted in issue #322; the next version
  is therefore 1.11.0.
