---

description: "Task list for Transaction API — Name-or-ID Lookup and Console Script"
---

# Tasks: Transaction API — Name-or-ID Lookup and Console Script

**Input**: Design documents from `specs/20260907-155643-transaction-api/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: **Required, not optional.** Constitution II (The Test Gate, NON-NEGOTIABLE) states that new code MUST be covered by valid tests and that no feature is complete while any test fails. Test tasks below are therefore mandatory, not illustrative.

**Organization**: Grouped by user story so each is independently implementable and testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: `[US1]` / `[US2]`, mapping to the user stories in [spec.md](./spec.md)
- Every task names the exact file it touches

## Path Conventions

Existing repository layout, per plan.md. Package code under `biweeklybudget/`, tests under
`biweeklybudget/tests/{unit,acceptance}/`, documentation under `docs/source/`.

## Milestone mapping

Constitution I requires human approval to advance between milestones, and Development
Workflow step 4 requires commit messages prefixed `{Feature Name} - {Milestone}.{Task}`.
The prefix for this feature is **`Transaction API - M{n}.{t}`**, mapped as:

| Phase | Milestone | Commit prefix |
|-------|-----------|---------------|
| Phase 1 (Setup) | — (no commit; environment only) | — |
| Phase 2 (Foundational) | **M1** — resolution helper | `Transaction API - M1.{t}` |
| Phase 3 (US1) | **M2** — endpoint accepts names | `Transaction API - M2.{t}` |
| Phase 4 (US2) | **M3** — `addtrans` script | `Transaction API - M3.{t}` |
| Phase 5 (Polish, docs/version) | **M4** — documentation and release metadata | `Transaction API - M4.{t}` |
| Phase 6 (Verification) | **M5** — full suites, PR, review | `Transaction API - M5.{t}` |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Working environment. No production code is written or changed in this phase, and nothing here is committed.

- [X] T001 Start the MariaDB test container and export the test-database environment described in `CLAUDE.md` and in [quickstart.md](./quickstart.md) (`docker run ... --name budgettest`, `DB_CONNSTRING`, `SETTINGS_MODULE`, `MYSQL_*`), then run `python dev/setup_test_db.py` from the activated `venv`
- [X] T002 Confirm the baseline is green before changing anything: run `tox -e py314` from the activated `venv`, redirecting output to a scratchpad file per `CLAUDE.md`, and record any pre-existing failures so they are not later mistaken for regressions

**Checkpoint**: Test database reachable, baseline unit suite result known.

---

## Phase 2: Foundational — Milestone M1: the resolution helper (Blocking Prerequisites)

**Purpose**: The single lookup function both user stories depend on. Implements rules R1–R4 of [data-model.md](./data-model.md).

**⚠️ CRITICAL**: US1 cannot begin until T004 is complete. US2 depends on US1.

- [X] T003 [P] Write failing unit tests for the resolution helper in `biweeklybudget/tests/unit/models/test_utils.py`, in a new `TestResolveByNameOrId` class using mocked query objects in the style of the existing tests in that file. Cover: digits-only value hits by primary key (R2); non-digit value hits by name (R3); a digits-only value that misses by ID then hits by name (R3 fallback, the "budget named 2024" case); leading/trailing whitespace is stripped (R1); matching is case-insensitive; a value matching nothing returns `None` (R4); `None`, `''` and `'   '` return `None` without querying; a non-string value such as the integer `5` is coerced and resolved
- [X] T004 Implement `resolve_by_name_or_id(db_sess, cls, value)` in `biweeklybudget/models/utils.py`, following rules R1–R4 of [data-model.md](./data-model.md). Return the model instance or `None`. Use `db_sess.query(cls).get(int(value))` for the ID path and `db_sess.query(cls).filter(func.lower(cls.name) == value.lower()).one_or_none()` for the name path — `func.lower()` explicitly rather than relying on the database collation, per decision D4 in [research.md](./research.md). Include a full docstring in the project's `:param:`/`:type:`/`:return:`/`:rtype:` style, noting that the caller is responsible for reporting a `None` result as a validation error
- [X] T005 Run `pytest biweeklybudget/tests/unit/models/test_utils.py` and confirm the new tests pass; confirm the file is pycodestyle- and pyflakes-clean under the exceptions in `pytest.ini`

**Checkpoint**: Helper implemented and unit-tested. Commit as `Transaction API - M1.1` … `M1.3`. Foundation ready.

---

## Phase 3: User Story 1 — Create a Transaction by Account and Budget name (Priority: P1) 🎯 MVP

**Goal**: `POST /forms/transaction` accepts Accounts and Budgets by name as well as by ID, with every existing validation rule intact and every existing ID-based caller — the web UI included — unaffected.

**Independent Test**: POST a Transaction whose `account` is an account name and whose `budgets` key is a budget name; confirm the Transaction is created against the right records. Delivers the whole "usable from a script" value on its own, with no console script present.

**Contract**: [contracts/transaction-create.md](./contracts/transaction-create.md)

### Tests for User Story 1

> Write these first and confirm they fail before T011.

- [X] T006 [P] [US1] Add acceptance tests for successful name-based creation to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py`, following the existing pattern of POSTing to `base_url + '/forms/transaction'`. Cover: `account` by name; a `budgets` key by name; `credit_payment_acct` by name resolving to a credit account; a request mixing an ID account with a name budget; a name given with different case and surrounding whitespace. Each asserts `success: true` and then queries the database to confirm the Transaction's `account_id`, `budget_transactions` and `credit_payment_acct_id` point at the intended records
- [X] T007 [P] [US1] Add acceptance tests for name-resolution failures to the same file: an unresolvable `account` name, an unresolvable `budgets` key, and an unresolvable `credit_payment_acct` name. Each asserts HTTP 200 with `success: false`, an `errors` entry on the right field quoting the offending value, and — critically — that the Transaction count in the database is unchanged
- [X] T008 [P] [US1] Add acceptance tests to the same file for the rules that must survive resolution: a new Transaction naming an **inactive** budget by name is rejected with the same message as by ID; a `credit_payment_acct` naming a **non-credit** account by name is rejected as "not a credit account"; a `budgets` mapping whose keys are `"<id>"` and `"<that budget's name>"` is rejected for duplicate reference (rule R7, the one genuinely new error condition)
- [X] T009 [P] [US1] Add an acceptance test to the same file pinning the digits-first precedence of rule R2/R3: create a Budget whose *name* is the decimal string of a different, existing Budget's ID, then confirm that supplying that string resolves to the Budget with that **ID**, not the one with that name
- [X] T010 [US1] Run the existing transaction acceptance tests unchanged (`tox -e acceptance -- -k transactions`, output redirected to a scratchpad file) to establish that the ID-only behaviour they pin is green before the handler is touched

### Implementation for User Story 1

- [X] T011 [US1] In `biweeklybudget/flaskapp/views/transactions.py`, add a private helper method to `TransactionFormHandler` that resolves the identifying fields and rewrites `data` in place to canonical numeric-ID strings, returning a dict of field name to error list. It must: resolve `data['account']` via `resolve_by_name_or_id(db_session, Account, ...)`, leaving the existing `'None'`/empty handling to the caller; rebuild `data['budgets']` keyed by resolved Budget ID, rejecting a mapping in which two keys resolve to the same Budget (rule R7) with `'Budget %s specified more than once.'`; resolve `data['credit_payment_acct']` only when it is not absent/`''`/`'None'`. Error strings quote the value **as supplied**, e.g. `'Account "%s" is invalid.'`
- [X] T012 [US1] Call that helper at the top of `TransactionFormHandler.validate()`, before any of the existing checks, and merge its errors into the accumulated `errors` dict — accumulating rather than returning early, so a caller sees every problem at once (rule R5). Guard the merge so a resolution failure on `budgets` does not then fall into the existing budget-sum loop with unresolved keys
- [X] T013 [US1] Simplify the now-redundant lookups downstream of resolution in `validate()`: `db_session.query(Budget).get(int(bid))` and the `credit_payment_acct` `int()` coercion can no longer fail on a value the resolver accepted. Keep the `None` guards — defence in depth costs nothing here — but make sure no code path can raise `ValueError` on a non-numeric key any more
- [X] T014 [US1] Verify `TransactionFormHandler.submit()` needs **no** change, since `validate()` has canonicalized `data` to IDs. If any path proves to reach `submit()` without canonicalization, fix the canonicalization rather than adding parsing to `submit()`
- [X] T015 [US1] Add a DEBUG-level log line recording each resolution that took the name path, so an operator debugging a script can see what a name resolved to. Use the module's existing `logger`
- [X] T016 [US1] Run the full acceptance suite (`tox -e acceptance`, output redirected to a scratchpad file) and confirm both the new tests and every pre-existing transaction test pass

**Checkpoint**: US1 complete and independently demonstrable with `curl` alone. Commit as `Transaction API - M2.1` … `M2.11`.

---

## Phase 4: User Story 2 — Create a Transaction from the command line (Priority: P2)

**Goal**: An `addtrans` console entry point that creates a Transaction through the HTTP API, taking inputs similar to the Add Transaction form and accepting names or IDs.

**Independent Test**: With the app running, invoke `addtrans <ACCOUNT> <AMOUNT> <DESCRIPTION> -b <BUDGET>` and confirm the Transaction appears with the expected values and the command prints the new ID and exits 0.

**Contract**: [contracts/addtrans-cli.md](./contracts/addtrans-cli.md)

**Depends on**: US1 (the endpoint must accept names for the script's headline use to work). The script's ID-only path would function without US1, but the story is not delivered until names work.

### Tests for User Story 2

- [ ] T017 [P] [US2] Write failing unit tests for payload construction in a new `biweeklybudget/tests/unit/test_addtrans.py`, with `requests.post` patched. Cover: positional account/amount/description map to the right JSON keys; a single `-b BUDGET` with no `=AMOUNT` allocates the full transaction amount; `-b NAME=AMOUNT` repeated produces one entry per budget; `notes` defaults to `''` and is always present in the payload (the endpoint 500s without it); `sales_tax` is omitted when not given; `-p` populates `credit_payment_acct`; `--no-budget-impact` sets the flag; `-d` is honoured and its absence yields today's date; the amount string is passed through verbatim without client-side parsing (decision D8)
- [ ] T018 [P] [US2] Write failing unit tests in the same file for URL resolution: `-U` wins; absent `-U`, the `BIWEEKLYBUDGET_URL` environment variable is used; absent both, `http://127.0.0.1:8080`; and the posted URL is the base with `/forms/transaction` appended exactly once regardless of a trailing slash on the base
- [ ] T019 [P] [US2] Write failing unit tests in the same file for outcome handling: a `success: true` body prints the transaction ID and exits 0; a `success: false` body with `errors` prints one line per field per error and exits 1; a `success: false` body with `error_message` prints it and exits 1; `requests.exceptions.ConnectionError` and `Timeout` produce a one-line message naming the URL and exit 1 with no traceback; a non-200 status and a non-JSON body each exit 1 with a readable message; `--dry-run` prints the payload, exits 0, and calls `requests.post` zero times
- [ ] T020 [P] [US2] Write a failing unit test in the same file asserting that more than one `-b` where any lacks `=AMOUNT` is a usage error (argparse exit code 2), and that zero `-b` arguments is likewise rejected

### Implementation for User Story 2

- [ ] T021 [US2] Create `biweeklybudget/addtrans.py` with the standard AGPL v3 copyright header copied verbatim from an existing module such as `biweeklybudget/wishlist2project.py` (Constitution VI). It must not import `biweeklybudget.db` or `biweeklybudget.settings` — the script is an HTTP client and must run without a settings module (decision D7)
- [ ] T022 [US2] Implement `parse_args()` in `biweeklybudget/addtrans.py` exactly as specified in [contracts/addtrans-cli.md](./contracts/addtrans-cli.md): positional `ACCOUNT`, `AMOUNT`, `DESCRIPTION`; `-b/--budget` (`action='append'`, required); `-d/--date`, `-n/--notes`, `-t/--sales-tax`, `-p/--credit-payment-acct`, `--no-budget-impact`, `-U/--url`, `--dry-run`, and `-v/--verbose` (`action='count'`) matching the pattern in `wishlist2project.py`
- [ ] T023 [US2] Implement budget-argument parsing in `biweeklybudget/addtrans.py`: split each `-b` value on the first `=`; with exactly one budget and no `=`, allocate the whole transaction amount string; with more than one, require every one to carry an amount and raise a `parser.error()` otherwise. Document in the module docstring that a budget name containing `=` must be given by ID
- [ ] T024 [US2] Implement payload construction and the POST in `biweeklybudget/addtrans.py`, sending JSON with `Content-Type: application/json` to `{base_url}/forms/transaction`. Always include `notes` (defaulting to `''`). Omit `sales_tax` and `credit_payment_acct` when not supplied
- [ ] T025 [US2] Implement response handling and exit codes in `biweeklybudget/addtrans.py` per the behaviour table in the contract. Note that `FormHandlerView` returns **HTTP 200 for validation failures**, so success must be read from the body's `success` key, never from the status code
- [ ] T026 [US2] Implement `main()` in `biweeklybudget/addtrans.py` following the `wishlist2project.py` pattern: `logging.basicConfig`, then `set_log_info`/`set_log_debug` from `biweeklybudget.cliutils` by verbosity count, then `raise SystemExit(rc)`. Wrap the request in a `try`/`except requests.exceptions.RequestException` so no transport failure reaches the user as a traceback
- [ ] T027 [US2] Add `addtrans = biweeklybudget.addtrans:main` to the `[console_scripts]` block in `setup.py`, alphabetically placed among the existing entries
- [ ] T028 [US2] Run `pytest biweeklybudget/tests/unit/test_addtrans.py`, confirm all tests pass, and confirm the new module and test file are pycodestyle- and pyflakes-clean
- [ ] T029 [US2] Reinstall the package into the venv (`pip install -e .`) and manually exercise the script against the running app per section 2 of [quickstart.md](./quickstart.md): a successful create, a validation failure, a `--dry-run`, and a run with the app stopped

**Checkpoint**: Both user stories functional. Commit as `Transaction API - M3.1` … `M3.13`.

---

## Phase 5: Milestone M4 — Documentation, version and changelog

**Purpose**: Constitution IV (documentation is part of the change) and VI (versioned, changelogged releases).

- [ ] T030 [P] Update the `POST /forms/transaction` section of `docs/source/http_api.rst`: change the `account`, `budgets` and `credit_payment_acct` field descriptions to say "ID or name"; add a short subsection stating the resolution rule (digits-first with name fallback, exact whole-string matching, case- and whitespace-insensitive), the ID-wins-over-name precedence, the `(income)` suffix caveat, and the duplicate-budget-reference error; add a names-only `curl` example beside the existing ID-based one
- [ ] T031 [P] Add `addtrans` to the "Command Line Entrypoints and Scripts" list in `docs/source/getting_started.rst`, in the same one-line style as the neighbouring entries, mentioning that it creates a Transaction through the HTTP API and takes accounts and budgets by name or ID
- [ ] T032 [P] Create `docs/source/biweeklybudget.addtrans.rst` following the exact form of `docs/source/biweeklybudget.wishlist2project.rst`, and add `biweeklybudget.addtrans` to the Submodules toctree in `docs/source/biweeklybudget.rst`, alphabetically
- [ ] T033 Bump `VERSION` in `biweeklybudget/version.py` from `1.10.0` to `1.11.0` — MINOR, a backward-compatible new capability (Constitution VI). Note that issue #322's "as of 1.6.0" is out of date
- [ ] T034 Add the `1.11.0` entry to `CHANGES.rst` in the established format: link `Issue #322`, then bullets covering what changed and why — the resolution rule and its precedence, why the existing endpoint was extended rather than a parallel one added, the in-place canonicalization that keeps `submit()` and all existing rules untouched, the new duplicate-budget-reference error as the one behaviour with no prior equivalent, the new `addtrans` entry point, and explicitly that there is no schema change, no migration and no new dependency
- [ ] T035 Run `tox -e docs` from the activated `venv`, output redirected to a scratchpad file, and confirm it builds with no errors or new warnings

**Checkpoint**: Documentation complete. Commit as `Transaction API - M4.1` … `M4.6`.

---

## Phase 6: Milestone M5 — Verification, pull request and review

**Purpose**: Constitution II (The Test Gate) and Development Workflow step 6.

- [ ] T036 Run the complete unit suite to completion: `tox -e py314`, output redirected to a scratchpad file. All tests must pass. If it times out, raise both the pytest and the tool timeout and re-run to completion — a timed-out suite has not passed
- [ ] T037 Run the complete acceptance suite to completion: `tox -e acceptance`, output redirected to a scratchpad file. All tests must pass, under the same no-timeout rule
- [ ] T038 Run `tox -e docker` to completion, output redirected to a scratchpad file. In scope because `setup.py` changed, which is a packaging change (Constitution II)
- [ ] T039 Work through [quickstart.md](./quickstart.md) section 2 end to end against a running app, including the check that the web UI's own Add Transaction modal is unchanged
- [ ] T040 Update this `tasks.md` and, if anything was learned that contradicts them, `spec.md` and `plan.md`, to record the outcome; commit everything from M4 and M5 together as the milestone close
- [ ] T041 Push `robot-army/issue-322-implement-the-transaction-http-api-and` to `origin` and open a pull request describing the change, the decisions from [research.md](./research.md), and the constitution compliance check from [plan.md](./plan.md)
- [ ] T042 Monitor the PR's CI jobs to completion and fix any failure
- [ ] T043 Run `/answer-reviews` to address review feedback, repeating until Claude's review reports "No issues found" and any Copilot review recommends approval

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies
- **Phase 2 (M1, Foundational)**: needs Phase 1 — **blocks both user stories**
- **Phase 3 (US1)**: needs Phase 2
- **Phase 4 (US2)**: needs Phase 3 — the script's headline behaviour is name-based creation
- **Phase 5 (M4, docs)**: needs Phases 3 and 4, since it documents both
- **Phase 6 (M5)**: needs everything

### User Story Dependencies

- **US1 (P1)**: depends only on the foundational helper. This is the MVP and is independently shippable — it makes the endpoint usable from `curl` and from any external script.
- **US2 (P2)**: depends on US1. Unlike the template's default assumption, these two stories are **not** parallelizable: the script exists to demonstrate the endpoint US1 delivers.

### Within Each Story

Tests are written before implementation and confirmed failing. Helper before handler;
handler before script; code before documentation.

### Parallel Opportunities

- T003 (helper tests) is `[P]` against nothing else in Phase 2 — T004 depends on it being written, not passing
- T006–T009, the four acceptance test tasks, are `[P]` with each other: independent test methods, though all in one file, so write them in one editing pass to avoid conflicting edits
- T017–T020, the four unit test tasks for the script, are `[P]` with each other, same caveat
- T030–T032, the three documentation tasks, touch four different files and are genuinely `[P]`
- The implementation tasks within each story are sequential: each builds on the last in the same file

This is a single-developer feature; the `[P]` markers indicate absence of dependency, not
a recommendation to parallelize a change this size.

---

## Parallel Example: User Story 1

```bash
# The four acceptance-test tasks are independent of one another.
# All land in biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py,
# so write them in one pass, then run them together:
tox -e acceptance -- -k 'name_or_id or by_name' > /tmp/acc-us1.txt 2>&1
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1: Setup
2. Phase 2: the resolution helper — blocks everything
3. Phase 3: the endpoint accepts names
4. **Stop and validate**: create a Transaction with `curl` using only names; confirm the
   web UI's Add Transaction modal is unchanged
5. At this point the issue's blocking complaint — "the endpoint is unusable from a script
   that only knows names" — is resolved, with or without the script

### Incremental delivery

1. Setup + Foundational → helper ready
2. US1 → endpoint usable from any HTTP client (**MVP**)
3. US2 → `addtrans` ships as the proof of concept
4. M4 → documentation, version, changelog
5. M5 → full suites, PR, CI, review

---

## Notes

- `[P]` means different files and no dependency, not a scheduling instruction
- Commit at each task or coherent group, prefixed `Transaction API - M{n}.{t}`
- Confirm each new test fails before writing the code that makes it pass
- Human approval is required to advance between milestones (Constitution I)
- Per `CLAUDE.md`, redirect test output to a scratchpad file rather than piping to
  `tail`/`head`/`grep`, so the full output stays available
- **Out of scope**, and not to be drifted into: the missed-payment detection described in
  issue #322's "Follow-on" section, and any change to how the negating offset transaction
  (#210) is calculated
