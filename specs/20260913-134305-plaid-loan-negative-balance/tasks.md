---

description: "Task list for Plaid Loan Accounts Record Money Owed As A Negative Balance"
---

# Tasks: Plaid Loan Accounts Record Money Owed As A Negative Balance

**Input**: Design documents from `specs/20260913-134305-plaid-loan-negative-balance/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/plaid-loan-balance.md, quickstart.md

**Tests**: Included. The constitution's financial-correctness constraint requires tests
that pin the expected numbers for any change to recorded balances, and Constitution II
requires new code to be covered by valid tests.

**Organization**: Grouped by user story. US1 (loans negated) and US2 (other types
unchanged) are delivered by the same change to `plaid_updater.py` (T004). US2's tasks are
the tests that pin the non-loan paths. The whole feature is one milestone (M1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

- Code: `biweeklybudget/plaid_updater.py` (`PlaidUpdater._stmt_for_acct`, `PlaidUpdater._update_investment`)
- Unit tests: `biweeklybudget/tests/unit/test_plaid_updater.py` (classes `TestStmtForAcct`, `TestUpdateInvestment`; module aliases `pb` = `PlaidUpdater`, `pbm` = module path)
- Docs: `docs/source/plaid.rst`
- Changelog: `CHANGES.rst`

---

## Phase 1: Setup

**Purpose**: A working test environment, so the Phase 3 tests can be seen to fail and then pass.

- [X] T001 Start the MariaDB 10.4.7 test container and create the test databases per `CLAUDE.md` ("Test Database Setup for Development"). Then confirm the unmodified `biweeklybudget/tests/unit/test_plaid_updater.py` passes, with output redirected to a scratchpad file, to get a green baseline.
  - *Done 2026-09-13.* Baseline: 19 passed and 3 failed. The three `TestDoItem` tests fail with `AttributeError: Mock object has no attribute 'account'` **before any change**, because `PlaidAccount.account` is a backref that exists only once SQLAlchemy has configured the mappers, and nothing in this file alone triggers that. It is an artifact of running the file in isolation, unrelated to this feature. T009's full-suite run confirmed they pass there (960 passed, 0 failed).

---

## Phase 2: Foundational

None. No shared infrastructure, model, endpoint, or migration is needed.

---

## Phase 3: User Story 1 — A linked loan shows as money owed (Priority: P1) 🎯 MVP

**Goal**: A Plaid `loan` update records the statement balance and the account balance as the negation of Plaid's cent-rounded `balances.current`.

**Independent Test**: The US1 unit tests below pass (quickstart step 1).

### Tests for User Story 1

> Write these first and confirm they FAIL against the current code.

- [X] T002 [US1] In `biweeklybudget/tests/unit/test_plaid_updater.py`:
  - `TestStmtForAcct.test_loan`: change the expected `_update_investment` call to `call(end_dt, mock_acct, pai, mock_stmt, negate_balance=True)`. Keep the assertion that `mock_stmt.type == 'Investment'`.
  - `TestUpdateInvestment`: add `test_negate_balance`, mirroring `test_happy_path` but calling `_update_investment(end_dt, mock_acct, acct, mock_stmt, negate_balance=True)` with `current` `'1234.5678'`. Assert that `mock_stmt.ledger_bal == Decimal('-1234.57')` and that `set_balance` is called with `ledger=Decimal('-1234.57')`, `overall_date=end_dt` and `ledger_date=end_dt`.
  - `TestUpdateInvestment`: add `test_negate_balance_negative`. With `current` `-50.25` (a float, as the Plaid SDK returns), assert that the stored `ledger_bal` and the `set_balance` ledger are both `Decimal('50.25')`.
  - `TestUpdateInvestment`: add `test_negate_balance_zero`. With `current` `0` (an int), assert that `ledger_bal == Decimal('0')` **and** `str(mock_stmt.ledger_bal) == '0.00'` (no `-0.00`; research R2), and that the `set_balance` ledger is the same.

### Implementation for User Story 1

- [X] T003 [US1] Run the T002 tests and confirm they fail (unexpected `negate_balance` keyword / positive values).
- [X] T004 [US1] In `biweeklybudget/plaid_updater.py` (see plan "Design" and `contracts/plaid-loan-balance.md`):
  - `_update_investment`: add the keyword parameter `negate_balance: bool = False` and a docstring documenting all parameters. Compute the balance once as today (`Decimal(...).quantize(Decimal('.01'), rounding=ROUND_HALF_DOWN)`). If `negate_balance` is true, set `bal = -bal` (unary minus, not `* -1`; research R2), then use `bal` for both `stmt.ledger_bal` and `set_balance(ledger=...)`. Adjust the debug log to say whether the balance was negated.
  - `_stmt_for_acct` `loan` branch: replace the "For now, this should work..." comment with one explaining that Plaid reports a loan's balance as a positive amount owed and biweeklybudget stores money owed as negative (issue #263). Pass `negate_balance=True`.
  - Re-run the T002 tests; they now pass.

**Checkpoint**: US1 is fully functional and testable.

---

## Phase 4: User Story 2 — Other Plaid account types are unaffected (Priority: P1)

**Goal**: `depository`, `credit` and `investment` balances are recorded exactly as before.

**Independent Test**: The tests below pass unchanged against T004's code (quickstart step 1).

### Tests for User Story 2

- [X] T005 [US2] In `biweeklybudget/tests/unit/test_plaid_updater.py`, confirm that the existing tests still pass without modification: `TestStmtForAcct.test_investment` (expects `call(end_dt, mock_acct, pai, mock_stmt)`, i.e. no `negate_balance`), `TestUpdateInvestment.test_happy_path` (stores `1234.57`), and every `TestUpdateBankOrCredit` test. Add `TestUpdateInvestment.test_negate_balance_false_explicit`: calling with `negate_balance=False` and `current` `'1234.5678'` stores `Decimal('1234.57')` on both the statement and the `set_balance` call.

**Checkpoint**: US1 and US2 both verified.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T006 [P] In `docs/source/plaid.rst`, add a `Loan Accounts` subsection (`+++` underline, matching the file's other Usage subsections) at the end of the `Usage` section, before `Troubleshooting`, with an RST label `.. _plaid.loan_accounts:`. It should state that:
  - Plaid reports a loan's balance as a positive amount owed, and biweeklybudget records it negated (money owed is negative, like credit cards). A negative Plaid figure, where the lender owes you, is recorded as positive.
  - Only the balance is recorded for loans, not transactions.
  - Link Plaid loans to an **Investment** account: they are then shown in the Investment Accounts tables and the Account Balances chart, and not counted as budget funds. Linking one to a Bank or Cash account would count it as a budget funding source.
  - Balances recorded before this change are left positive. Include a MySQL `UPDATE` that negates `account_balances.ledger` and `ofx_statements.ledger_bal` for accounts joined to `plaid_accounts` rows with `account_type = 'loan'` (via `accounts.plaid_item_id`/`plaid_account_id` = `plaid_accounts.item_id`/`account_id`). Say to run it once, after upgrading and before the next Plaid update, and that running it again reverses it.
- [X] T007 Verify the T006 SQL against the **test** database (quickstart step 3). Insert a `plaid_items`/`plaid_accounts` loan row and link an account with positive `account_balances` and `ofx_statements` rows. Run the SQL and confirm the loan rows flip and non-loan rows don't. Run it again and confirm the original values are restored. Clean up the inserted rows.
- [X] T008 [P] Add a concise `CHANGES.rst` bullet at the top of `Unreleased`, led by the `Issue #263 <https://github.com/jantman/biweeklybudget/issues/263>`_ link: balances of accounts linked to Plaid loan accounts are now recorded as negative (money owed). Add one sub-bullet noting that previously recorded loan balances are not changed, with a reference to the Plaid docs for SQL to correct them. Do not touch `biweeklybudget/version.py`.
- [X] T009 Constitution II/IV gate: run the complete unit (`tox -e py314`) and acceptance (`tox -e acceptance`) suites to completion, plus `tox -e docs`, redirecting output to scratchpad files. All must pass. A timeout means raise the timeout and re-run, never narrow the run. Run pycodestyle/pyflakes on the changed files (max-line-length 100). Re-run known-flaky tests (reconcile drag, fuel log search) in isolation before blaming this change. Record the results in `plan.md` ("Test Gate Results").
- [X] T010 Mark all tasks complete in this file, commit (`Plaid Loan Negative Balance - M1.N: ...`), push the branch to `origin`, and open a PR against `master` that follows `.github/PULL_REQUEST_TEMPLATE.md`. The PR should put the option-1 decision, the no-history-rewrite choice (research R1, R3), and the out-of-scope Plaid credit-sign observation (R4) to the maintainer.

---

## Dependencies & Execution Order

- T001 → T002 → T003 → T004 → T005 → T009 → T010.
- T006 and T008 touch separate files and can be done any time after T004, in parallel with each other and with T005. T007 follows T006.
- US2 depends on US1 only because they share T004's implementation; its tests check that
  T004 did not move other paths.

### Parallel Opportunities

```text
After T004:  T005 (test_plaid_updater.py)  ∥  T006 (plaid.rst) → T007  ∥  T008 (CHANGES.rst)
```

## Implementation Strategy

MVP is US1 (T001–T004): the loan sign fix itself. US2 is a guard on the same change, so
the whole feature ships as one milestone (M1) in one PR, gated by T009.
