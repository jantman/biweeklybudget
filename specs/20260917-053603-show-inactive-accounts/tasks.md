---

description: "Task list for: Show Inactive Accounts So They Can Be Re-Activated"
---

# Tasks: Show Inactive Accounts So They Can Be Re-Activated

**Input**: Design documents from `specs/20260917-053603-show-inactive-accounts/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/accounts-page.md](./contracts/accounts-page.md), [quickstart.md](./quickstart.md)

**Tests**: Test tasks ARE included and are not optional here. Constitution Principle II
(NON-NEGOTIABLE) requires new code to be covered by valid tests and the full suites to pass
before the feature is declared done.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task serves (US1, US2)
- Every task names its exact file path

## Milestone mapping

Phases here are the constitution's milestones. Commit messages MUST be prefixed
`Show Inactive Accounts - M{milestone}.{task}` (Development Workflow step 4), e.g.
`Show Inactive Accounts - M1.2`. **Human approval is required to advance between milestones**
(Principle I).

| Phase | Milestone | Delivers | Stories |
|-------|-----------|----------|---------|
| 1 | — (no commits) | Working test database and tox environments | — |
| 2 | **M1** | Inactive accounts listed, marked, and re-activatable | US1, US2 |
| 3 | **M2** | Robustness on the rows M1 exposes | — (edge cases) |
| 4 | **M3** | Acceptance coverage and documentation | US1, US2 |
| 5 | **M4** | Changelog, full test gate, pull request, CI | — |

## Path Conventions

Single Python package at the repository root: `biweeklybudget/`, with tests under
`biweeklybudget/tests/` and documentation under `docs/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Get the test database and tox environments working in this worktree. Produces no
commits.

- [X] T001 Start the MariaDB test container and export the test-database environment variables per `specs/20260917-053603-show-inactive-accounts/quickstart.md` ("Prerequisites"), then run `dev/setup_test_db.py` with `/home/jantman/GIT/biweeklybudget/venv/bin/python`
- [X] T002 Build the tox environments with `/home/jantman/GIT/biweeklybudget/venv/bin/tox` (this worktree has no `venv/`, and the `tox` on `PATH` is broken), then `touch .tox/acceptance/liveserver.log` — a fresh acceptance env has no log file and every `testflask` test errors in setup without it
- [X] T003 Capture the pre-change baseline: run `$TOX -e acceptance -- biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py` redirected to a scratchpad file, confirming it is green before anything is edited

**Checkpoint**: Test database up, acceptance environment usable, baseline green.

---

## Phase 2 (M1): Make inactive accounts visible, marked, and re-activatable 🎯 MVP

**Goal**: An inactive account is listed on the Accounts page, greyed with an `Active?` cell,
its name still linking to the edit modal — so "Active?" can be re-checked and saved.

**Independent Test**: Load `/accounts` against the sample data; `DisabledBank` (id 6) appears
in the Bank Accounts table as a greyed row reading `NO`, its name links to
`accountModal(6, null)`, and the modal's `Active?` checkbox is unchecked and can be checked
and saved.

**Serves**: User Story 1 (P1) and User Story 2 (P2). Both need the same two edits, so they are
delivered in one milestone rather than split across two that could not be shipped apart.

### Implementation for M1

- [X] T004 [US1] In `biweeklybudget/flaskapp/views/accounts.py`, extract the body shared by `AccountsView.get()` and `OneAccountView.get()` into one module-level helper taking an optional `account_id`, and drop `Account.is_active == True` from the three account queries in it (removing all six filtered queries at lines 92-100 and 135-143) — research R2, R1; spec FR-001
- [X] T005 [P] [US2] In `biweeklybudget/flaskapp/templates/accounts.html`, add `Active?` as the first `<th>` of all three tables (bank, credit, investment) and, per row, a first `<td>` rendering `yes` or `<td style="color: #a94442;">NO</td>`, copying `biweeklybudget/flaskapp/templates/budgets.html:81,110` character-for-character — spec FR-002; contracts/accounts-page.md "Active? cell"
- [X] T006 [US2] In `biweeklybudget/flaskapp/templates/accounts.html`, render each account row as `<tr>` when active and `<tr class="inactive">` when not, in all three tables, following `budgets.html:80,109`. Do **not** add CSS — `tr.inactive` already exists at `biweeklybudget/flaskapp/static/css/custom.css:7` — spec FR-003
- [X] T007 [US1] Confirm no change is needed to `biweeklybudget/flaskapp/static/js/accounts_modal.js` or to `AccountFormHandler` in `biweeklybudget/flaskapp/views/accounts.py`: the modal already reads `is_active` into the checkbox (line 131) and `submit()` already writes it (line 281). Record the confirmation; make no edit — spec FR-004, FR-005; research R1

### Verification for M1

- [X] T008 [US1] Manually verify the round trip per `quickstart.md` ("Manual validation"): `DisabledBank` greyed and reading `NO` on `/accounts`, re-activate it from its modal, then deactivate an active account and confirm it stays listed. Remember that synthetic coordinate clicks do not fire this app's jQuery handlers — drive them with `$('#...').click()`
- [X] T009 Milestone close: run `$TOX -e py314` and `$TOX -e acceptance` sequentially to completion, redirecting each to a scratchpad file. Expect `test_accounts.py` table assertions to fail here — that is the deliberate change, fixed in M3 — and expect **nothing else** to fail. Any other failure is a defect in M1, not an assertion to update

**Checkpoint**: Issue #276 is functionally fixed. Accounts-page assertions are knowingly red
pending M3; everything else is green. **Human approval required before M2.**

---

## Phase 3 (M2): Handle what M1 makes reachable

**Goal**: The rows M1 surfaces render correctly and quietly — no permanent red on every
inactive row, and no 500 for the whole page because one account is missing a figure.

**Independent Test**: An inactive account shows its balance age in plain styling rather than
red; an account with no recorded balance, or a credit account with no credit limit, renders as
a row with blank value cells and the page still returns 200.

**Serves**: The spec's Edge Cases (FR-006, FR-007). Kept out of M1 so the defensive work is
reviewable as such rather than blurred into the visible change.

### Implementation for M2

- [X] T010 In `biweeklybudget/flaskapp/templates/accounts.html`, gate the stale-data `text-danger` class on `acct.is_active` as well as `acct.is_stale`, in all three tables. The age itself must still be shown, in plain `data_age` styling — spec FR-007; research R4
- [X] T011 In `biweeklybudget/flaskapp/templates/accounts.html`, guard every balance-derived cell so a missing value renders as an empty cell instead of raising: `Balance`/`Value` and `Difference` when `acct.balance` is `None`, and `Credit Limit`, `Available` and `Difference` when `acct.credit_limit` is `None`. Do **not** change `Account.balance` in `biweeklybudget/models/account.py` to fabricate a zero — spec FR-006; research R5; data-model.md "Nullability"

### Verification for M2

- [X] T012 Milestone close: run `$TOX -e py314` and `$TOX -e acceptance` sequentially to completion. Same expectation as T009 — only the known `test_accounts.py` table assertions fail

**Checkpoint**: Edge cases handled. **Human approval required before M3.**

---

## Phase 4 (M3): Acceptance coverage and documentation

**Goal**: The new behaviour is covered by tests that would fail without it, the tests broken by
the deliberate change are corrected, and the documentation describes what the application now
does.

**Independent Test**: `$TOX -e acceptance -- -k "TestInactiveAccounts or TestAccountsMainPage"`
passes, and `$TOX -e docs` builds clean.

### Tests for M3

- [X] T013 [US1] [US2] In `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py`, update `TestAccountsMainPage` — `test_bank_table`, `test_bank_stale_span`, `test_credit_table`, `test_investment_table` — for the deliberate change. The **only** expected movement is the added `Active?` cell on every row and the added `DisabledBank` row (sorting last in the bank table, after `BankTwoStale`). Treat any other difference as a defect — research R7
- [X] T014 [US1] In `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py`, update the three `TestAccountTransfer` bank-table assertions (around lines 1060, 1167, 1312) for the same two additions
- [X] T015 [P] [US2] Add a `TestInactiveAccounts` acceptance class to `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py` asserting the presentation contract: `DisabledBank`'s `<tr>` carries class `inactive` and active rows do not; its first cell reads `NO` and others read `yes`; its name cell is `<a href="javascript:accountModal(6, null)">DisabledBank</a>`; and its age span has class `data_age` **without** `text-danger` — spec FR-002, FR-003, FR-004, FR-007
- [X] T016 [US1] Add the end-to-end round trip to `TestInactiveAccounts` in `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py`: open `DisabledBank`'s modal, assert `Active?` is unchecked, check it, save, and assert both the page and the database show it active; then deactivate an active account through its modal and assert it remains listed as inactive — spec User Story 1, FR-005
- [X] T017 Confirm the regression invariants pass **with no edits**: `$TOX -e acceptance -- -k "test_index or CashPosition or Payperiod or CreditPayoff"`. `test_index.py:91-143` is the sharp one — the dashboard's panels share element IDs with the Accounts page but come from `index.html` and must still list active accounts only. Needing to edit any of these means the change leaked outside its scope — spec FR-009, SC-005; contracts/accounts-page.md "Invariants"

### Documentation for M3

- [X] T018 [P] Add an "Inactive Accounts" section to `docs/source/app_usage.rst`: what deactivating an account does and does not do, that inactive accounts stay listed and greyed on the Accounts page with an `Active?` column, and how to re-activate one from its edit modal — spec FR-010
- [X] T019 [P] Add a `description` to the `/accounts` entry in `docs/make_screenshots.py` (around line 262) naming the inactive-account treatment. Edit the **generator**, not `docs/source/screenshots.rst`, which is generated output and would be silently overwritten — research R8
- [X] T020 Regenerate the `/accounts` screenshots with `$TOX -e screenshots`, then commit **only** `docs/source/accounts.png`, `docs/source/accounts_sm.png` and this feature's own caption in `docs/source/screenshots.rst`. Restore everything else the run rewrites: `git checkout -- docs/source/*.png` for the rest, and `git clean -n docs/source/` before removing any untracked PNGs it added — research R8
- [X] T021 Build the documentation clean with `$TOX -e docs`, in a **separate invocation** from `screenshots` — `docs` deletes the generated PNGs, and running them together fails the linkcheck on every `screenshots.rst` image

### Verification for M3

- [X] T022 Milestone close: run `$TOX -e py314`, then `$TOX -e acceptance`, then `$TOX -e docs`, each to completion and each redirected to a scratchpad file. All three must pass with **zero** failures. Check each log for `<env>: OK` rather than trusting a trailing exit code

**Checkpoint**: Everything green, documentation built. **Human approval required before M4.**

---

## Phase 5 (M4): Changelog, test gate, pull request

**Goal**: The change is recorded, the gate is closed, and the pull request is open and green.

- [X] T023 Add one concise bullet to `CHANGES.rst` under an `Unreleased` heading (creating that heading directly beneath the `Changelog` title if absent), led by the issue #276 link, stating the user-visible change in a sentence or two. Do **not** touch `biweeklybudget/version.py`, create a tag, or cut a release — constitution Principle VI
- [X] T024 Verify Principle III compliance by diff: confirm `git diff master... --stat` shows no change under `biweeklybudget/models/`, and therefore that no Alembic migration is required — research R9; data-model.md
- [X] T025 Close the test gate: run `$TOX -e py314` and `$TOX -e acceptance` to completion one final time on the finished tree, with everything passing. A suite that times out has not passed — raise both the pytest timeout and the tool timeout and re-run rather than narrowing the run
- [X] T026 Commit the work with `Show Inactive Accounts - M{n}.{t}` prefixes, push the branch with `git push -u origin HEAD:refs/heads/robot-army/issue-276-inability-to-re-activate-an-account` (a bare `git push` would target `master`, which this worktree's branch tracks), and open a pull request describing the change, linking issue #276, and stating Constitution compliance
- [ ] T027 Monitor the CI jobs on the pull request to completion, then run `/answer-reviews` to address every review comment. Repeat until Claude's review reports "No issues found" and Copilot's review, if present, recommends approval. Known-flaky tests (reconcile drag/unignore, fuel log search, Plaid "Uncheck All", and the docs linkcheck) are re-run before being treated as regressions

**Checkpoint**: Feature complete, pull request green and reviewed.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies; start immediately
- **Phase 2 (M1)**: depends on Phase 1. **This is the MVP** — it is what closes issue #276
- **Phase 3 (M2)**: depends on M1; it hardens rows that only M1 makes reachable
- **Phase 4 (M3)**: depends on M1 and M2 — the tests assert both milestones' behaviour, so
  writing them earlier would mean writing them twice
- **Phase 5 (M4)**: depends on all of the above

Each milestone boundary requires human approval (Principle I).

### Within Phase 2 (M1)

- T004 (view) and T005/T006 (template) touch different files and are independent of each other,
  but the feature is not observable until both are done
- T005 and T006 both edit `accounts.html`; T005 is marked `[P]` relative to T004 only. Do T005
  then T006 — or make both edits in one pass over the template
- T007 is a confirmation, not an edit, and can be done at any point in the phase
- T008 and T009 require T004-T006 complete

### Within Phase 4 (M3)

- T013, T014 and T015 all edit `test_accounts.py`; T015 is `[P]` relative to T018/T019 only
- T018 and T019 are genuinely parallel — different files, no shared state
- T020 depends on T019 (the caption must exist before regeneration writes it into the `.rst`)
- T021 must **not** overlap T020

### Parallel opportunities

This is a single-operator change across five files; parallelism is limited and mostly not worth
coordinating. The genuine pairs:

```bash
# Documentation, different files, no shared state:
Task: "T018 Add the Inactive Accounts section to docs/source/app_usage.rst"
Task: "T019 Add the /accounts description to docs/make_screenshots.py"
```

Note what is **not** parallel: `$TOX -e py314` and `$TOX -e acceptance` share the test database
and must run sequentially, and `$TOX -e docs` must never run alongside `$TOX -e screenshots`.

---

## Implementation Strategy

### MVP (Phase 2 / M1 only)

Phase 1 → Phase 2 → stop and validate. At that point issue #276 is fixed: no account can be
put into a state where the application offers no way to reach it, and the database workaround
in the issue is no longer needed. Phases 3-5 make it robust, tested, documented and merged —
all required before the feature is declared done (Principles II and IV), but none of them
change what the user can now do.

### Incremental delivery

1. Setup → environment ready
2. **M1** → inactive accounts visible and re-activatable (the fix)
3. **M2** → edge cases on the newly reachable rows
4. **M3** → coverage and documentation
5. **M4** → changelog, gate, pull request, CI

### Notes

- `[P]` means different files with no dependency, not "do these at the same time regardless"
- Commit at each logical group, prefixed `Show Inactive Accounts - M{n}.{t}`
- Redirect test output to a scratchpad file rather than piping to `tail`/`head`/`grep`, so the
  full output stays available
- Never point the acceptance suite at a real database — it drops and reloads what it is given
- No task in this list edits `biweeklybudget/models/`, `biweeklybudget/version.py`, or
  `biweeklybudget/alembic/`
