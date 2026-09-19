---

description: "Task list for Plaid Credit Card Balances Recorded As Negative (issue #354)"
---

# Tasks: Plaid Credit Card Balances Recorded As Negative

**Input**: Design documents from `specs/20260918-200526-plaid-credit-negative-balance/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/plaid-balance-signs.md](./contracts/plaid-balance-signs.md), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are **required**, not optional. Spec FR-013 mandates tests pinning the recorded sign for each case, and Constitution Principle II (NON-NEGOTIABLE) requires new code to be covered by valid tests and the full suites to pass before the feature is done.

**Organization**: Tasks are grouped by user story. Each group is one constitution milestone; commit messages use the prefix `Plaid Credit Negative Balance - M{milestone}.{task}`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are given in every task

## Path Conventions

Single Python package at the repository root: `biweeklybudget/` for source, `biweeklybudget/tests/unit/` for unit tests, `docs/source/` for documentation. Paths below are relative to the repository root, `/home/jantman/worktrees/biweeklybudget/issue-354`.

## Milestone Map

| Milestone | User Story | Delivers |
|---|---|---|
| M1 | US1 (P1) | The corrected sign and the tests that pin it — the reported defect is fixed |
| M2 | US2 (P1) | Plaid documentation, Cash Position cross-reference, changelog entry |
| M3 | US3 (P3) | The diagnostic consistency check, then the full test gate and delivery |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a green baseline so that any later failure is attributable to this change.

- [X] T001 Activate the main checkout's virtualenv (`source /home/jantman/GIT/biweeklybudget/venv/bin/activate`; this worktree has none) and run `pytest biweeklybudget/tests/unit/test_plaid_updater.py biweeklybudget/tests/unit/test_cashposition.py biweeklybudget/tests/unit/flaskapp/test_notifications.py`, redirecting output to a scratchpad file. Record that the baseline is green. `TestDoItem`'s three tests are known to fail when `test_plaid_updater.py` runs entirely alone; including the other files avoids that.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that must exist before any user story.

**None.** This feature adds no module, model, dependency, setting, schema change or migration. `biweeklybudget/plaid_updater.py` and its unit tests already exist and are the only source files that change. User Story 1 can begin immediately after Phase 1.

**Checkpoint**: Nothing to do — proceed to Phase 3.

---

## Phase 3: User Story 1 - Cash Position and the unallocated-funds notification tell the truth (Priority: P1) 🎯 MVP — Milestone M1

**Goal**: A Plaid `credit` account's balance is recorded with biweeklybudget's sign convention (negative when owed), so Cash Position and the unallocated-funds notification subtract what is owed instead of adding it. Depository balances and all transaction amounts are unaffected.

**Independent Test**: Run a Plaid update (or the mocked-updater unit tests) for a credit account reporting a positive `balances.current`, and confirm both `OFXStatement.ledger_bal` and the recorded `AccountBalance.ledger` are its negation. Per [quickstart.md](./quickstart.md) §1–§2.

### Tests for User Story 1 ⚠️

> Write these first and confirm they fail against the unfixed code, so the assertions are known to be load-bearing.

- [X] T002 [US1] In `biweeklybudget/tests/unit/test_plaid_updater.py`, update `TestStmtForAcct.test_credit` to assert the call is `call(end_dt, mock_acct, pai, txns, mock_stmt, negate_balance=True)`, and confirm `TestStmtForAcct.test_depository` still asserts a call with no `negate_balance` (the default). Leave `test_investment`, `test_loan`, `test_unknown_type` and `test_none` untouched.
- [X] T003 [US1] In `biweeklybudget/tests/unit/test_plaid_updater.py`, add to `TestUpdateBankOrCredit` a `test_negate_balance` case: `balances.current` of `'1234.5678'` with `negate_balance=True` records `stmt.ledger_bal == Decimal('-1234.57')` and calls `set_balance(ledger=Decimal('-1234.57'), ...)`, while `avail_bal` stays `Decimal('854.29')` and the two `upsert_record` transaction calls keep their existing positive amounts. Model it on the existing `test_happy_path`.
- [X] T004 [US1] In `biweeklybudget/tests/unit/test_plaid_updater.py`, add `test_negate_balance_negative` to `TestUpdateBankOrCredit`: a reported `balances.current` of `-50.00` with `negate_balance=True` records `Decimal('50.00')` — the overpaid-card case. Assert it is positive, proving the implementation negates rather than taking an absolute value.
- [X] T005 [US1] In `biweeklybudget/tests/unit/test_plaid_updater.py`, add `test_negate_balance_zero` to `TestUpdateBankOrCredit`: a reported balance of `0` with `negate_balance=True` records `Decimal('0.00')`, asserted via `str(stmt.ledger_bal) == '0.00'` or `not stmt.ledger_bal.is_signed()` — **not** by `== Decimal('0.00')`, which is `True` for `Decimal('-0.00')` and would pass even with the bug present. Mirror `TestUpdateInvestment.test_negate_balance_zero`.
- [X] T006 [US1] In `biweeklybudget/tests/unit/test_plaid_updater.py`, confirm the existing `TestUpdateBankOrCredit.test_happy_path` and `test_negate_amounts` still call `_update_bank_or_credit` without `negate_balance` and still expect the positive `Decimal('1234.57')`. These are the depository baseline and the guard that `negate_ofx_amounts` (transaction amounts) and `negate_balance` (statement balance) stay independent — FR-005, FR-006.

### Implementation for User Story 1

- [X] T007 [US1] In `biweeklybudget/plaid_updater.py`, add `negate_balance: bool = False` as the final keyword parameter of `PlaidUpdater._update_bank_or_credit()`, and give the method a docstring in the style of `_update_investment()` documenting every parameter, including that `negate_balance` is used for credit accounts because Plaid reports a credit card's balance as the positive amount owed.
- [X] T008 [US1] In `biweeklybudget/plaid_updater.py`, inside `_update_bank_or_credit()`, negate the quantized ledger balance when `negate_balance` is true, using a unary minus with the comment `# Unary minus, not "* -1", so a zero balance stays 0.00, not -0.00` to match `_update_investment()`. Assign the result to `stmt.ledger_bal` before `db_session.add(stmt)` so that both the statement and the `account.set_balance()` call below it use the negated value (FR-001 – FR-004). Leave `stmt.avail_bal` untouched (FR-007).
- [X] T009 [US1] In `biweeklybudget/plaid_updater.py`, change the `account_type == 'credit'` branch of `_stmt_for_acct()` to call `self._update_bank_or_credit(end_dt, account, plaid_acct_info, plaid_txns, stmt, negate_balance=True)`, with a comment matching the loan branch's: Plaid reports a credit card's balance as the positive amount owed; biweeklybudget records money owed as a negative balance. Reference issue #354. Leave the `depository` branch exactly as it is (FR-005).
- [X] T010 [US1] Fix the now-misleading `logger.debug('Generating statement for credit account')` in `_update_bank_or_credit()` — it fires for depository accounts too. Make it report which convention is being applied, e.g. `logger.debug('Generating statement for bank or credit account (negate_balance=%s)', negate_balance)`, matching `_update_investment()`.
- [X] T011 [US1] Run `pytest biweeklybudget/tests/unit/test_plaid_updater.py biweeklybudget/tests/unit/test_cashposition.py biweeklybudget/tests/unit/flaskapp/test_notifications.py` (output to a scratchpad file). All must pass. `test_cashposition.py` and `test_notifications.py` must be unchanged and green — a failure there means the fix landed in the wrong place.
- [X] T012 [US1] Commit M1 as `Plaid Credit Negative Balance - M1.1: Record Plaid credit balances as negative (issue #354)`.

**Checkpoint**: The reported defect is fixed and pinned by tests. Cash Position and the unallocated-funds notification now subtract what is owed on a Plaid-sourced credit card.

---

## Phase 4: User Story 2 - An operator upgrading knows what happens to years of existing balances (Priority: P1) — Milestone M2

**Goal**: The documentation states the credit sign convention, says plainly that pre-upgrade rows keep the old sign and what that looks like on the Account Balances chart, and gives corrective SQL with the conditions for running it safely.

**Independent Test**: Read `docs/source/plaid.rst` — the convention, the untouched-rows statement and the SQL with its three warnings are all present — and build the docs successfully. Per [quickstart.md](./quickstart.md) §5–§6.

### Implementation for User Story 2

- [X] T013 [P] [US2] In `docs/source/plaid.rst`, add a `Credit Card Accounts` section with a `.. _plaid.credit_accounts:` label, at the same `+++` heading level as `Loan Accounts` and immediately before it, under `Usage`. State that Plaid reports a credit card's `balances.current` as the positive amount owed and that biweeklybudget records it negated; give the worked example of a card owing $1,000 recorded as -$1,000.00; state that an overpaid card or a statement credit (a negative Plaid balance) is recorded as positive and counts as funds available; note that only the balance sign differs, and transaction amounts and the available balance are recorded as Plaid reports them. Model the prose on the existing `Loan Accounts` section (FR-009).
- [X] T014 [P] [US2] In that same section of `docs/source/plaid.rst`, document the historical data: balances recorded before this change keep their old sign and are not corrected automatically, so an account's line on the Account Balances chart jumps from positive to negative at its first update after upgrading. Give the corrective SQL — two `UPDATE ... SET col = -col` statements against `account_balances.ledger` and `ofx_statements.ledger_bal`, joined to `plaid_accounts` on `account_type = 'credit'`, mirroring the loan section's statements — and the three warnings: run it **once**, after upgrading and *before* the next Plaid update; running it a second time undoes it; add a condition on `account_balances.overall_date` / `ofx_statements.as_of` if some of an account's balances came from somewhere other than Plaid (FR-010, FR-011).
- [X] T015 [P] [US2] In `docs/source/app_usage.rst`, in the Cash Position section where the sign discussion explains "Credit balances are added, not subtracted", add a sentence cross-referencing `:ref:`plaid.credit_accounts`` so a reader wondering how a Plaid-sourced credit balance acquires that sign is pointed at the answer. Do not otherwise alter the existing explanation, which is correct.
- [X] T016 [P] [US2] In `CHANGES.rst`, create an `Unreleased` heading directly beneath the `Changelog` title (there is none today; `2.0.0 (2026-09-20)` is currently the top section) and add one concise entry led by a link to issue #354: balances for credit cards linked through Plaid are now recorded as negative, so Cash Position and the unallocated-funds notification subtract what is owed instead of adding it. Add at most a couple of short sub-bullets: that the figures were previously overstated by twice the balance owed, and that balances recorded before the upgrade keep their old sign with corrective SQL in the Plaid documentation. Do **not** touch `biweeklybudget/version.py`, and create no tag (Constitution Principle VI; FR-012).
- [X] T017 [US2] Run `tox -e docs` (output to a scratchpad file). It must build without errors. Never run `tox -e docs` during or alongside a `screenshots` run — it deletes the PNGs. If `linkcheck` fails on a transient timeout, re-run it.
- [X] T018 [US2] Commit M2 as `Plaid Credit Negative Balance - M2.1: Document the credit balance convention and correct historical rows (issue #354)`.

**Checkpoint**: An operator upgrading can determine from the documentation alone what happens to their existing credit balances and correct them in one documented step.

---

## Phase 5: User Story 3 - An institution that breaks the documented sign rule is noticeable (Priority: P3) — Milestone M3

**Goal**: A cheap, non-fatal consistency check makes a hypothetical reversed-sign institution discoverable from the update logs rather than only from a wrong total.

**Independent Test**: Feed the updater a credit account whose available balance, credit limit and current balance are consistent only with a reversed sign, and confirm a message is logged, the balance is still recorded per the documented rule, and the update succeeds.

### Tests for User Story 3 ⚠️

- [X] T019 [US3] In `biweeklybudget/tests/unit/test_plaid_updater.py`, add to `TestUpdateBankOrCredit` a test that the check **fires**: `negate_balance=True`, `account.credit_limit` set, an `available` balance matching `limit + current` far better than `limit - current` and with `err_normal > abs(current)`. Assert the log record and assert the recorded `ledger_bal` is still the plain negation — the check must not alter it. This file has no existing log-assertion idiom, so establish one: pytest's built-in `caplog` fixture, matching on the logger name and level.
- [X] T020 [US3] In `biweeklybudget/tests/unit/test_plaid_updater.py`, add a test that the check **stays quiet** for a consistent account: `available == limit - current`. Assert no such log record is emitted.
- [X] T021 [US3] In `biweeklybudget/tests/unit/test_plaid_updater.py`, add tests for each skip condition: `account.credit_limit is None`; Plaid reported no `available` balance; a reported `current` of zero; and `negate_balance=False` (a depository account, which must never be checked). Each asserts no log record and no change to the recorded values.

### Implementation for User Story 3

- [X] T022 [US3] In `biweeklybudget/plaid_updater.py`, add the diagnostic check to `_update_bank_or_credit()`, guarded on `negate_balance` being true. Per [contracts/plaid-balance-signs.md](./contracts/plaid-balance-signs.md): skip silently unless `account.credit_limit is not None`, the available balance is not `None`, and the reported current balance is non-zero; then compute `err_normal = abs(available - (credit_limit - current))` and `err_reversed = abs(available - (credit_limit + current))`, and log when `err_reversed < err_normal` **and** `err_normal > abs(current)`. Use `logger.warning` (see `research.md` Decision 5 — a deliberate, recorded departure from the issue's "debug-level" suggestion), naming the account and all three figures, and say in the message that pending activity makes the relation approximate. The check must never raise and must never alter a recorded value (FR-008). Extract it to a small private helper if `_update_bank_or_credit()` would otherwise become unwieldy.
- [X] T023 [US3] Run `pytest biweeklybudget/tests/unit/test_plaid_updater.py biweeklybudget/tests/unit/test_cashposition.py biweeklybudget/tests/unit/flaskapp/test_notifications.py` again. All pass.
- [X] T024 [US3] Commit as `Plaid Credit Negative Balance - M3.1: Warn when a Plaid credit account's balances suggest a reversed sign (issue #354)`.

**Checkpoint**: All three user stories are functional. The fix, its documentation and the diagnostic are complete.

---

## Phase 6: Polish, Test Gate & Delivery — Milestone M3

**Purpose**: The Constitution Principle II gate, and delivery. No feature is complete while any test fails, and a suite that times out has not passed.

- [X] T025 Lint the changed files clean under the exceptions in `pytest.ini` / `setup.cfg` (`max-line-length = 100`): pycodestyle and pyflakes over `biweeklybudget/plaid_updater.py` and `biweeklybudget/tests/unit/test_plaid_updater.py`. A scratch virtualenv is needed for the lint tools in this worktree.
- [X] T026 Run the **full unit suite** to completion: `tox -e py314`, output redirected to a scratchpad file. Every test passes. If it times out, raise both the pytest timeout and the tool timeout and re-run — do not narrow the selection.
- [X] T027 Run the **full acceptance suite** to completion: `tox -e acceptance`, output redirected to a scratchpad file. Every test passes. `touch .tox/acceptance/liveserver.log` first if the env is fresh. Known-flaky tests (reconcile drag/unignore, especially `test_36_ignore_and_unignore_ofx`; fuel log search; Plaid `test_6_uncheck_all`) have missing-wait races unrelated to this change — re-run a failure in isolation before attributing it here.
- [X] T028 `tox -e migrations` is **not required** (no schema change, no migration) and `tox -e docker` is left to CI, which is the gate for it. Record this decision in the spec artifacts rather than skipping silently.
- [X] T029 Update `specs/20260918-200526-plaid-credit-negative-balance/tasks.md` and `plan.md` to record progress and the test-gate results (Constitution step 5c).
- [X] T030 Commit the test-gate record, push the branch with `git push -u origin HEAD:refs/heads/robot-army/issue-354-cash-position-adds-plaid-sourced-credit` — the branch's upstream is `origin/master`, so a bare `git push` would target master — and open a pull request describing the defect, the fix, the untouched areas, the historical-data decision, and the recorded WARNING-vs-DEBUG judgement call for the maintainer.
- [X] T031 Monitor CI on the pull request until every job completes, then use `/answer-reviews` to respond to review comments. Repeat until Claude's review reports "No issues found" and Copilot's review, if present, recommends approval.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: empty for this feature; blocks nothing.
- **User Story 1 (Phase 3, M1)**: after Phase 1. Depends on nothing else.
- **User Story 2 (Phase 4, M2)**: independent of US1 in principle — the documentation describes the intended behaviour either way — but sequenced after it so the docs describe code that exists.
- **User Story 3 (Phase 5, M3)**: depends on US1, because the check is guarded on the `negate_balance` parameter that T007 introduces.
- **Polish (Phase 6)**: after all three stories.

### Within User Story 1

T002–T006 (tests) before T007–T010 (implementation): the tests must be seen to fail against the unfixed code, which is the only way to know they are load-bearing. T007 before T008 and T009 (both need the parameter to exist). T011 after all of them.

### Parallel Opportunities

Genuinely limited, and that is honest rather than a gap: nearly every source task touches one of two files (`biweeklybudget/plaid_updater.py`, `biweeklybudget/tests/unit/test_plaid_updater.py`), so they are sequential.

The real parallelism is in Phase 4, where T013/T014 (`docs/source/plaid.rst`), T015 (`docs/source/app_usage.rst`) and T016 (`CHANGES.rst`) touch three different files and can be done in any order or together. T013 and T014 edit the same new section and are marked `[P]` relative to T015/T016, not to each other.

---

## Implementation Strategy

### MVP (User Story 1 / M1 only)

1. Phase 1 baseline.
2. Phase 3: tests first, then the `negate_balance` parameter, the credit call site, and the log-message fix.
3. **Stop and validate**: the plaid-updater, cashposition and notifications unit tests pass; Cash Position now subtracts what is owed.

This alone closes the reported defect and is a shippable increment.

### Incremental Delivery

1. M1 → the defect is fixed and pinned by tests.
2. M2 → an operator can understand and correct their historical data.
3. M3 → the diagnostic check, then the full test gate, push, pull request and CI.

Each milestone is committed with its constitution prefix, and each adds value without disturbing the previous one.

---

## Notes

- `[P]` means different files with no dependency between them.
- Run tox from the main checkout's virtualenv; this worktree has none, and `~/.local/bin/tox` is broken.
- Always redirect suite output to a scratchpad file rather than piping to `tail`/`head`, so the whole run can be read back (`CLAUDE.md`).
- No Alembic migration is part of this feature; see `research.md` Decision 6 and the Complexity Tracking table in `plan.md`.
- Do not touch `biweeklybudget/version.py`, and do not create a tag or release.
