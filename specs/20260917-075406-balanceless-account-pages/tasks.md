---

description: "Task list for the balance-less account pages fix (GitHub issue #334)"
---

# Tasks: Balance-less Accounts Must Not Break The Landing Pages

**Input**: Design documents from `specs/20260917-075406-balanceless-account-pages/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/index-page-tables.md](./contracts/index-page-tables.md)

**Tests**: Required, not optional. FR-010 asks for acceptance coverage of a state nothing
exercises today, and Constitution Principle II requires new code to be covered by valid
tests rather than tests written to pass. Every test below is written and **seen to fail**
before the template is changed.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Flask application in a single package at the repository root:
`biweeklybudget/flaskapp/templates/` for templates,
`biweeklybudget/tests/acceptance/flaskapp/views/` for the acceptance tests of a page.

## A note on story independence

The three user stories in the spec are one defect seen from three angles, not three
separable deliverables, and the task list says so rather than pretending otherwise:

- **US1** (index page renders) needs the template change. It is the whole fix.
- **US2** (Accounts page renders) needs **no** production change — research R3 verified by
  reproduction that it already works — so its tasks are test-only, and they pass from the
  first run. They are still worth having: nothing currently holds that behaviour.
- **US3** (a balance row with a `NULL` ledger) is closed by the same guard US1 installs, by
  the deliberate choice of guard shape (research R5). Its task is the test that proves it.

They land in the same two files, so the parallel opportunities are real but small, and are
marked honestly below rather than inflated.

---

## Phase 1: Setup

**Purpose**: A disposable database to run anything against.

- [x] T001 Start the throwaway MariaDB and create the test databases per the Prerequisites
  in `specs/20260917-075406-balanceless-account-pages/quickstart.md` (container
  `budgettest334` on port 13306, then `python dev/setup_test_db.py`)
- [x] T002 Reproduce the defect from `quickstart.md` and confirm `/` returns 500 while
  `/accounts` returns 200 for an active balance-less account *(done during research; the
  results are recorded in `research.md` R1)*

**Checkpoint**: The failure is reproducible on demand, so a fix can be proven rather than
assumed.

---

## Phase 2: Foundational

**Purpose**: None. There is no shared scaffolding to build — no new module, model,
migration, dependency, or route. The work begins directly at User Story 1.

---

## Phase 3: User Story 1 - Add an account and keep using the application (Priority: P1) 🎯 MVP

**Goal**: `GET /` renders successfully when any active account it lists has no recorded
balance, showing that account with blank value cells and leaving every other account's
figures untouched.

**Independent Test**: Add an active bank, credit and investment account with no balance,
request `/`, and get HTTP 200 with the three new rows present and blank-celled.

### Tests for User Story 1 ⚠️ Write first, and see them fail

- [X] T003 [US1] Add a `TestIndexMissingData` class to
  `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`, modelled on
  `TestAccountsMissingData` in `test_accounts.py:2060` — `class_refresh_db`, `refreshdb`,
  `testflask`, `incremental` — whose first test adds three **active** accounts with no
  balance (`BankNoData`/Bank, `CreditNoData`/Credit, `InvestmentNoData`/Investment) via the
  `testdb` fixture
- [X] T004 [US1] In that class, assert `requests.get(base_url + '/')` returns 200, in
  `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`
- [X] T005 [US1] In that class, assert the exact row text for each of the three index
  tables — `['BankNoData', '', '$0.00', '']` in `#table-accounts-bank`,
  `['CreditNoData', '', '', '']` in `#panel-credit-cards table`, and
  `['InvestmentNoData', '']` in `#table-accounts-investment` — in
  `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`. Exact text, not just a
  status code, is what pins FR-003 (blank, never a fabricated `$0.00`) and FR-005 (no bare
  `()` where the balance age would go)
- [X] T006 [US1] Run the new class against the **unfixed** template and record the failure
  in the scratchpad: `tox -e acceptance -- -k "TestIndexMissingData"`, output redirected to
  a file per `CLAUDE.md`. It must fail with `UndefinedError: 'None' has no attribute
  'ledger'`. A pass here means the test is not testing anything

### Implementation for User Story 1

- [X] T007 [US1] Guard the bank table in
  `biweeklybudget/flaskapp/templates/index.html` (rows near lines 136-148): add
  `{% set ledger = acct.balance.ledger if acct.balance else None %}` inside the row loop,
  print the balance as `{{ ledger|dollars }}`, wrap the balance-age span in
  `{% if acct.ofx_statement %}`, and guard the "Difference" cell with
  `{% if ledger is not none %}` — matching `accounts.html:56-68` cell for cell
- [X] T008 [US1] Guard the credit table in
  `biweeklybudget/flaskapp/templates/index.html` (rows near lines 175-188) the same way,
  guarding both "Available" and "Avail - Unrec" with
  `{% if ledger is not none and acct.credit_limit is not none %}` — matching
  `accounts.html:100-113`
- [X] T009 [US1] Guard the investment table in
  `biweeklybudget/flaskapp/templates/index.html` (rows near lines 214-221) the same way;
  it has only the balance cell and its age span — matching `accounts.html:143-155`
- [X] T010 [US1] Re-run `tox -e acceptance -- -k "TestIndexMissingData"` and confirm it now
  passes

**Checkpoint**: The issue's headline defect is fixed and proven. This is the MVP; US2 and
US3 add coverage, not capability.

---

## Phase 4: User Story 2 - The Accounts page tolerates an active balance-less account (Priority: P2)

**Goal**: Hold the Accounts page's existing correct behaviour for an **active** balance-less
account, which nothing currently exercises — the coverage added under issue #276 used
inactive accounts only.

**Independent Test**: With the same three accounts present, `/accounts` returns 200 and
shows them as active rows with blank value cells.

**Note**: No production change is expected. If these tests fail, `accounts.html` is not as
correct as research R3 found, and fixing it becomes part of this feature under FR-002.

- [X] T011 [US2] In `TestIndexMissingData` in
  `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`, assert
  `requests.get(base_url + '/accounts')` returns 200 with the same three active
  balance-less accounts present
- [X] T012 [US2] Assert in the same class that the `BankNoData` row on `/accounts` renders
  as an **active** row with blank value cells — `['yes', 'BankNoData', '', '$0.00', '']` —
  so the active path through the staleness markup is covered, not just the inactive one
  already covered by `TestAccountsMissingData`

**Checkpoint**: Both pages named in the issue are covered for the active case.

---

## Phase 5: User Story 3 - A recorded balance with no ledger figure (Priority: P3)

**Goal**: An account whose newest balance row exists but carries no ledger figure is
rendered exactly like one with no balance row at all, on both pages.

**Independent Test**: Give an active account `set_balance(ledger=None, avail=None)`, request
both pages, and get 200 with that account's balance-derived cells blank.

- [X] T013 [US3] Add an incremental test to `TestIndexMissingData` in
  `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py` that calls
  `set_balance(ledger=None, avail=None)` on one of the balance-less accounts, then asserts
  both `/` and `/accounts` return 200 and that account's row is unchanged from the
  blank-celled form asserted in T005

**Checkpoint**: Both routes to the failure are closed and covered.

---

## Phase 6: Polish, Test Gate And Close-Out

**Purpose**: Constitution Principles II, IV and VI, and the delivery the session owes.

- [X] T014 Confirm no existing expectation moved: run
  `tox -e acceptance -- -k "TestIndexAccounts or TestAccountsMainPage or TestAccountsMissingData"`
  and confirm every previously asserted cell text still matches
- [X] T015 [P] Run the complete unit suite to completion: `tox -e py314`, output redirected
  to the scratchpad. All tests pass — a narrowed run is not the gate and a timed-out run
  has not passed (Principle II)
- [X] T016 Run the complete acceptance suite to completion: `tox -e acceptance`, output
  redirected to the scratchpad. All tests pass. Any failure among the known flaky tests
  (reconcile drag/unignore, fuel log search, Plaid "Uncheck All") is re-run in isolation
  before being attributed to this change, and never waved away without that re-run
- [X] T017 [P] Build the documentation: `tox -e docs`. No source documentation change is
  expected — this feature adds no setting, command, or endpoint and changes nothing a user
  does — but the environment must build clean (Principle IV)
- [X] T018 [P] Add one concise bullet to `CHANGES.rst` under an `Unreleased` heading, led by
  the issue link, in the format of the existing entries. Do not touch
  `biweeklybudget/version.py` and do not tag (Principle VI)
- [ ] T019 Record the outcome in
  `specs/20260917-075406-balanceless-account-pages/tasks.md` and `plan.md`, and commit the
  whole milestone together with a `Balance-less Account Pages - M.T` prefixed message
- [ ] T020 Push the branch to `origin` and open a pull request describing the defect, the
  fix, the decision to render blank rather than `$0.00`, and what was verified by
  reproduction
- [ ] T021 Monitor the pull request's CI to completion, then use `/answer-reviews` to
  respond to review comments, repeating until Claude's review reports no issues found and
  Copilot's review, if present, recommends approval
- [ ] T022 Tear down the throwaway database container: `docker rm -f budgettest334`

---

## Outcome

Recorded 2026-09-17, against a `mariadb:10.4.7` container, from the worktree.

**The fix.** Nine lines of `biweeklybudget/flaskapp/templates/index.html`, in three
blocks. Each table gained one `{% set ledger = ... %}`, its balance-age span moved inside
`{% if acct.ofx_statement %}`, and its derived cells gained an `is not none` test. The
`{% if acct.is_stale %}…{% else %}…{% endif %}` pair around the age span collapsed into the
class-attribute form `accounts.html` uses; it emits byte-identical markup, which the
existing `test_bank_stale_span` assertion confirms. No Python changed.

**T006 — the test was seen red.** Against the unfixed template the new class failed at
`test_02_index_still_loads` with `assert 500 == 200`, the remaining tests cascading to
xfail on the `incremental` marker. Recorded in `t006-unfixed.txt`.

**T010 / T014 — green after the fix, nothing else moved.**
`TestIndexMissingData or TestIndexAccounts or TestAccountsMainPage or TestAccountsMissingData`:
26 passed. Every previously asserted cell text still matches, including the `$12,789.01
(14 hours ago)` balance cells whose markup was rewritten.

**The gate (Principle II).** Both suites run to completion, neither narrowed nor timed out:

| Suite | Result |
|---|---|
| `tox -e py314` | **1005 passed**, 4 skipped |
| `tox -e acceptance` | **965 passed**, 0 failed (22:58) |
| `tox -e docs` | build succeeded |

The acceptance run was clean on the first attempt — none of the known flaky tests
(reconcile drag/unignore, fuel log search, Plaid "Uncheck All") needed a re-run, so no
failure was attributed to flakiness.

**Unchanged, as planned**: no file under `biweeklybudget/models/`, so no migration
(Principle III not engaged); no `docs/source/` change and no screenshot change, and
`sphinx-apidoc` regenerated nothing that differs (Principle IV); no `version.py` change
(Principle VI).

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: complete.
- **Phase 2 (Foundational)**: empty — nothing blocks the stories.
- **Phase 3 (US1)**: the only phase with a production change. T003→T004→T005 build the test,
  T006 must fail, T007-T009 fix it, T010 must pass.
- **Phase 4 (US2)** and **Phase 5 (US3)**: both add tests to the class created in T003, so
  they follow it. US3's subject is fixed by US1's guard; US2's needs no fix at all.
- **Phase 6**: after every story, and T014 before the full suites so a local regression is
  caught in seconds rather than at the end of a long acceptance run.

### Within User Story 1

The order T006 → T007-T009 → T010 is the point of the story, not a formality: a test that
was never seen red proves nothing about the fix.

### Parallel opportunities

Genuinely small, and listed rather than padded:

- T007, T008 and T009 edit three separate table blocks in one file — do them in one pass,
  not in parallel; they are listed separately because they are three distinct reviewable
  edits, not because they can be staffed out.
- T015, T017 and T018 touch different things (unit suite, docs build, `CHANGES.rst`) and are
  marked `[P]`. T016, the acceptance suite, must not overlap another acceptance run against
  the same database.

---

## Implementation Strategy

### MVP

Phase 3 alone closes the issue: the landing page stops failing, and the blank-cell
behaviour is pinned by an exact-text assertion. Everything after it is coverage that stops
the same defect coming back through the other door.

### Incremental delivery

1. Phase 3 → the reported bug is fixed and proven → could ship.
2. Phase 4 → the Accounts page's existing behaviour is held rather than merely believed.
3. Phase 5 → the second route to the same failure is covered.
4. Phase 6 → full suites, changelog, pull request, CI, reviews.

---

## Notes

- Redirect every test run to a file in the scratchpad rather than piping to `tail` or
  `grep`, per `CLAUDE.md`, so the whole output stays available.
- Commit messages take the `Balance-less Account Pages - {Milestone}.{Task}` prefix.
- Nothing here touches `biweeklybudget/models/`, so no Alembic migration is created; if that
  changes, Principle III applies in full and a reversible migration ships in the same change.
