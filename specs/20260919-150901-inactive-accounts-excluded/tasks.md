---

description: "Task list for: Exclude Inactive Accounts From Dropdowns And The Balances Chart"
---

# Tasks: Exclude Inactive Accounts From Dropdowns And The Balances Chart

**Input**: Design documents from `specs/20260919-150901-inactive-accounts-excluded/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: REQUIRED. Constitution Principle II (NON-NEGOTIABLE) requires that new code be
covered by valid tests and that the full unit and acceptance suites pass before the
feature is done. Test tasks below are therefore not optional.

**Organization**: Tasks are grouped by user story. Note the sequencing constraint recorded
in plan.md M2: **US2 and US3 must land in the same commit.** Narrowing a select (US2)
without re-adding an existing record's own Account (US3) would silently retarget financial
records, so US3 is not a follow-up — it is the other half of US2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US4, mapping to the user stories in spec.md

## Path Conventions

Flask web application, existing layout. Backend: `biweeklybudget/models/`,
`biweeklybudget/flaskapp/views/`, `biweeklybudget/flaskapp/templates/`. Frontend:
`biweeklybudget/flaskapp/static/js/`. Tests: `biweeklybudget/tests/unit/` and
`biweeklybudget/tests/acceptance/`.

---

## Phase 1: Setup

**Purpose**: Working test database, so any task can be verified as it is written.

- [X] T001 Start the test database container and export the test environment per `CLAUDE.md` ("Test Database Setup for Development"): `docker run -d --name budgettest -p 13306:3306 ... mariadb:10.4.7`, then `DB_CONNSTRING`, `SETTINGS_MODULE` and the `MYSQL_*` variables
- [X] T002 Confirm the suites run green before any change, redirecting output to the scratchpad per `CLAUDE.md`: `tox -e py314 > <scratchpad>/unit-baseline.txt 2>&1`. A pre-existing failure must be identified as pre-existing now, not discovered later and mistaken for a regression

**Checkpoint**: A known-good baseline exists.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The single definition of "an Account that may be chosen". Every user story
reads it, so nothing else can start until it exists.

**⚠️ CRITICAL**: T003 blocks US1, US2 and US3.

- [X] T003 Add the static method `Account.active_accounts(db)` to `biweeklybudget/models/account.py`, returning `db.query(Account).filter(Account.is_active.__eq__(True)).order_by(Account.name)`. Mirror `Account.active_credit_accounts(db)` (same file, ~line 264) exactly in placement, signature, docstring style and `:rtype: sqlalchemy.orm.query.Query` — per research.md R3
- [X] T004 [P] Add unit tests for `Account.active_accounts()` in `biweeklybudget/tests/unit/models/test_account.py` (new file; include the standard AGPL header used by the other files in that directory): returns only active Accounts, excludes inactive ones, is ordered by name, and returns a `Query` rather than a list

**Checkpoint**: Foundation ready. US1 and US2/US3 can now proceed in parallel.

---

## Phase 3: User Story 1 — A closed account leaves the balances chart (Priority: P1) 🎯 MVP

**Goal**: The Account Balances chart plots only active Accounts, with every remaining
account's data, and the returned date set, byte-identical to today's.

**Independent Test**: `GET /ajax/chart-data/account-balances` with the sample data returns
`keys` without `DisabledBank`, and the same dates and same values for every other account.

**Contract**: [contracts/account-balances-chart.md](./contracts/account-balances-chart.md)

### Implementation for User Story 1

- [X] T005 [US1] In `AcctBalanaceChartView.get()` (`biweeklybudget/flaskapp/views/index.py`, ~line 267), build `accounts` from `Account.active_accounts(db_session).all()` instead of `db_session.query(Account).all()`
- [X] T006 [US1] In the same method's balance loop (~line 292), replace `name = accounts[bal.account_id]` with a `accounts.get(...)` lookup that `continue`s when the account is absent, so a balance row belonging to an inactive Account is skipped rather than raising `KeyError`. **Leave the `AccountBalance` query unfiltered** — research.md R4 and contract C-5: narrowing it would drop any date whose only balance row belongs to an inactive Account
- [X] T007 [US1] Update the docstring of `AcctBalanaceChartView` (`views/index.py`, ~lines 230-264) to state that only active Accounts are returned and that balance records for inactive Accounts are retained but skipped. Verify `_balances_before()` needs no change — it already guards with `accounts.get(...)` / `continue` (~line 357)

### Tests for User Story 1

- [X] T008 [US1] In `TestAcctBalanceChartData` (`biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`, ~line 655), remove `'DisabledBank'` from the expected `keys` in `test_response_shape_is_unchanged`
- [X] T009 [US1] Add tests to that same class covering contract C-1/C-2/C-4/C-5: the inactive Account appears in no `data` row for any `days` value including `days=0`; the returned dates are unchanged from the documented `['2017-06-27', '2017-07-10', '2017-07-15', '2017-07-26', '2017-07-27']`; and every remaining account's values are unchanged
- [X] T010 [US1] Check `biweeklybudget/tests/acceptance/flaskapp/views/test_charts.py` for assertions that depend on the number or identity of chart series (e.g. around line 640) and update any that break

**Checkpoint**: US1 is independently complete and verifiable via the endpoint alone.

---

## Phase 4: User Stories 2 & 3 — Pickers offer only active Accounts, without losing an existing record's (Priority: P1)

**Goal**: Every Account picker that chooses where a record goes offers only active
Accounts (US2), while any form opened on an existing record still shows — and preserves —
that record's own Account even when it has since been deactivated (US3).

**Independent Test**: each of the seven selects in
[contracts/template-account-maps.md](./contracts/template-account-maps.md) shows only
active Accounts; and a Transaction whose Account was deactivated after creation opens with
that Account selected and saves with its `account_id` unchanged.

**⚠️ Ship together.** US3's tasks must not be deferred past US2's — see the note at the top
of this file.

### Backend: views pass an active-only map

- [ ] T011 [P] [US2] `biweeklybudget/flaskapp/views/index.py` — in `IndexView.get()` (~line 77) replace `accts` with `active_accts` built from `Account.active_accounts(db_session)`, and pass `active_accts=` instead of `accts=` to `render_template`
- [ ] T012 [P] [US2] `biweeklybudget/flaskapp/views/accounts.py` (~line 84, ~line 114) — same replacement
- [ ] T013 [P] [US2] `biweeklybudget/flaskapp/views/budgets.py` — same replacement in both `BudgetsView.get()` (~line 98) and `OneBudgetView.get()` (~line 148)
- [ ] T014 [P] [US2] `biweeklybudget/flaskapp/views/fuel.py` (~line 66) — same replacement
- [ ] T015 [P] [US2] `biweeklybudget/flaskapp/views/scheduled.py` — same replacement in both view methods (~lines 63, 84)
- [ ] T016 [P] [US2] `biweeklybudget/flaskapp/views/payperiods.py` (~line 231) — same replacement
- [ ] T017 [P] [US2] `biweeklybudget/flaskapp/views/transactions.py` — **add** `active_accts` alongside the existing `accts` in both `TransactionsView.get()` (~line 70) and `OneTransactionView.get()` (~line 105); this page hosts both a table filter and an entry form
- [ ] T018 [P] [US2] `biweeklybudget/flaskapp/views/reconcile.py` (~line 69) — **add** `active_accts` alongside the existing `accts`, for the same reason
- [ ] T019 [US2] Confirm `biweeklybudget/flaskapp/views/ofx.py` is left unchanged (both methods, ~lines 59, 73): its page hosts only the downloaded-transactions filter, which keeps the full map per FR-014

### Frontend: templates emit the right globals

- [ ] T020 [P] [US2] `biweeklybudget/flaskapp/templates/index.html` (~lines 5-7) — replace the `acct_names_to_id` block with an `active_acct_names_to_id` block over `active_accts`
- [ ] T021 [P] [US2] `biweeklybudget/flaskapp/templates/accounts.html` (~lines 13-15) — same replacement
- [ ] T022 [P] [US2] `biweeklybudget/flaskapp/templates/budgets.html` (~lines 8-10) — same replacement
- [ ] T023 [P] [US2] `biweeklybudget/flaskapp/templates/fuel.html` (~lines 15-17) — same replacement
- [ ] T024 [P] [US2] `biweeklybudget/flaskapp/templates/scheduled.html` (~lines 14-16) — same replacement
- [ ] T025 [P] [US2] `biweeklybudget/flaskapp/templates/payperiod.html` (~lines 14-16) — same replacement, leaving the `credit_acct_names_to_id` block below it alone
- [ ] T026 [P] [US2] `biweeklybudget/flaskapp/templates/transactions.html` (~lines 14-16) — **keep** the `acct_names_to_id` block and **add** an `active_acct_names_to_id` block, matching how `budget_names_to_id` and `active_budget_names_to_id` already sit together below it
- [ ] T027 [P] [US2] `biweeklybudget/flaskapp/templates/reconcile.html` (~lines 11-13) — keep and add, as T026
- [ ] T028 [US2] Confirm `biweeklybudget/flaskapp/templates/ofx.html` is unchanged, and grep the templates to verify no template emits a global no script reads and none reads one its view does not pass (contract INV-1)

### Frontend: selects read the active map

- [ ] T029 [P] [US2] `biweeklybudget/flaskapp/static/js/account_transfer_modal.js` (lines 46-47) — point both `acct_txfr_frm_from_account` and `acct_txfr_frm_to_account` at `active_acct_names_to_id`
- [ ] T030 [P] [US2] `biweeklybudget/flaskapp/static/js/budget_transfer_modal.js` (line 45) — point `budg_txfr_frm_account` at `active_acct_names_to_id`
- [ ] T031 [P] [US2] `biweeklybudget/flaskapp/static/js/fuel.js` (line 110) — point `fuel_frm_account` at `active_acct_names_to_id`
- [ ] T032 [P] [US2] `biweeklybudget/flaskapp/static/js/transactions_modal.js` (line 51) — point `trans_frm_account` at `active_acct_names_to_id`
- [ ] T033 [P] [US2] `biweeklybudget/flaskapp/static/js/scheduled_modal.js` (line 153) — point `sched_frm_account` at `active_acct_names_to_id`
- [ ] T034 [P] [US2] `biweeklybudget/flaskapp/static/js/payperiod_modal.js` (line 138) — point `skipschedtrans_frm_account` at `active_acct_names_to_id`
- [ ] T035 [US2] Verify the two table filters still read `acct_names_to_id` and are untouched: `transactions.js` (~line 164) and `ofx.js` (~line 127) — FR-014

### Frontend: keep an existing record's Account (US3)

Each of these appends an option for `msg['account_id']` / `msg['account_name']` when the
select has none, immediately before selecting it — the same move
`transModalDivFillAndShow()` already makes for a deactivated credit-payment account
(`transactions_modal.js:100-110`). Both AJAX endpoints already return `account_name`; no
endpoint changes.

- [ ] T036 [US3] `biweeklybudget/flaskapp/static/js/transactions_modal.js` — in `transModalDivFillAndShow()` (~line 97), add the fallback before selecting the account, with a comment naming the case as the existing credit-payment fallback does
- [ ] T037 [US3] `biweeklybudget/flaskapp/static/js/scheduled_modal.js` — in `schedModalDivFillAndShow()` (~line 194), add the same fallback
- [ ] T038 [US3] `biweeklybudget/flaskapp/static/js/payperiod_modal.js` — in `skipSchedTransModalDivFillAndShow()` (~line 195), add the same fallback. This one is load-bearing: the field is disabled and `serializeForm()` (`forms.js:266-299`) submits disabled selects anyway, so without it a skip would post the wrong account

### Tests: existing assertions (US2, US4)

- [ ] T039 [US2] Remove `['6', 'DisabledBank']` from the twenty entry-form select assertions listed in research.md R6: `test_index.py:526,545`; `test_accounts.py:1144,1163,1300,1319`; `test_budgets.py:626,775`; `test_transactions.py:358,430,554,1581,1756`; `test_payperiods.py:1139,1327,1461,2223,2880`; `test_scheduled.py:202`; `test_fuel.py:464`. Line numbers will shift as edits land — locate each by its select id, not by line
- [ ] T040 [US4] Verify the two **filter** assertions still expect `['6', 'DisabledBank']` and are left untouched: `test_ofx.py:204` and `test_transactions.py:197` (`account_filter`). These two not changing is the evidence for FR-014
- [ ] T041 [US2] Search the acceptance suite for any further assertion on account-select contents that does not use the literal `['6', 'DisabledBank']` (e.g. `test_accounts.py:1089,1206,1361,1907`, `test_budgets.py:1006,1036`, `test_transactions.py:2350`) and update only those that assert an entry-form select

### Tests: new coverage (US3)

- [ ] T042 [US3] Add an acceptance class `TestTransModalDoesNotShowInactiveAccounts` to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py`, modelled on `TestTransModalDoesNotShowInactiveBudgets` (~line 795): create a Transaction against `DisabledBank` (id 6), then assert the Edit modal's `trans_frm_account` options are the active Accounts **plus** `DisabledBank`, that `DisabledBank` is the selected option, and that a Transaction on an active Account shows the active Accounts only (FR-012)
- [ ] T043 [US3] Add the save half of FR-011 to that class: save the modal without touching the Account, then assert from the database that the Transaction's `account_id` is still `6`
- [ ] T044 [P] [US3] Add equivalent coverage for `sched_frm_account` in `biweeklybudget/tests/acceptance/flaskapp/views/test_scheduled.py`: a ScheduledTransaction against `DisabledBank` opens with it selected, and saves with `account_id` unchanged
- [ ] T045 [P] [US3] Add equivalent coverage for `skipschedtrans_frm_account` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py`: the skip form for a ScheduledTransaction on `DisabledBank` shows that Account in its disabled select, and the resulting skip Transaction is created against it

**Checkpoint**: US2, US3 and US4 are complete together; no picker offers an inactive
Account, and no existing record can be silently retargeted.

---

## Phase 5: Polish & Feature Closure

- [ ] T046 Run the full unit suite to completion: `tox -e py314 > <scratchpad>/unit.txt 2>&1`. All pass — a narrowed or timed-out run is not a pass (Constitution II)
- [ ] T047 Run the full acceptance suite to completion: `tox -e acceptance > <scratchpad>/acceptance.txt 2>&1`. All pass. Re-run any of the known-flaky tests (reconcile drag/unignore, fuel log search, Plaid "Uncheck All") in isolation before attributing a failure to this change
- [ ] T048 Confirm the tree is pycodestyle- and pyflakes-clean under the exceptions in `setup.cfg` / `pytest.ini` (max line length 100)
- [ ] T049 [P] Add the `CHANGES.rst` entry under `Unreleased`: one concise bullet led by the issue #356 link, naming the dropdowns and the chart, and noting that an existing record keeps an Account deactivated after the fact. No `version.py` change, no tag (Constitution VI)
- [ ] T050 [P] Run `tox -e docs` and confirm it builds clean. Do **not** chain it with `screenshots` — that deletes the generated PNGs
- [ ] T051 Regenerate the dashboard screenshot, which contains the Account Balances chart and loses the `DisabledBank` line: `tox -e screenshots`, then `git status --short docs/source/_static/` and commit only the PNGs this change actually altered
- [ ] T052 Walk [quickstart.md](./quickstart.md) sections 2–5 against the running app, including the section 4 deactivate-then-edit check, which is the one that proves the fix is not harmful
- [ ] T053 Record the outcome in this file and in `plan.md`, commit the whole milestone, push the branch to `origin`, and open the pull request

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies
- **Phase 2 (Foundational)**: needs Phase 1. **Blocks US1 and US2/US3** — both build their maps from `Account.active_accounts()`
- **Phase 3 (US1)**: needs T003. Independent of Phase 4
- **Phase 4 (US2/US3/US4)**: needs T003. Independent of Phase 3
- **Phase 5 (Polish)**: needs Phases 3 and 4

### User Story Dependencies

- **US1** (chart): independent. Delivers value alone — this is the MVP
- **US2** (pickers) and **US3** (existing records): mutually dependent, one increment
- **US4** (filters keep inactive accounts): no implementation of its own. It is a boundary the US2 work must not cross, verified by T040 and T041

### Within Phase 4

Backend (T011–T019) → templates (T020–T028) → JS selects (T029–T035) → US3 fallbacks
(T036–T038) → tests (T039–T045). A select cannot be pointed at a global the template does
not yet emit, so the order matters even though tasks within each band are parallel.

### Parallel Opportunities

- T004 runs alongside T005–T007
- Phase 3 (US1) and Phase 4 (US2/US3) are fully independent after T003
- T011–T018 are eight different view modules: all parallel
- T020–T027 are eight different templates: all parallel
- T029–T034 are six different JS files: all parallel
- T044 and T045 are different test files: parallel

---

## Implementation Strategy

### MVP (User Story 1)

Phase 1 → Phase 2 → Phase 3, then stop and verify the chart endpoint alone. At that point
the issue's stated *data* problem is fixed and the #353 checklist item on the chart can be
checked, independently of any dropdown work.

### Then the pickers

Phase 4 in one increment. Do not merge US2 without US3: a narrowed select with no re-add
is a regression on existing records, not a partial improvement.

### Then close

Phase 5. Full suites to completion, docs, screenshot, changelog, PR.

---

## Notes

- Commit messages use the prefix `Inactive Accounts Excluded - {Milestone}.{Task}` (Constitution, Development Workflow step 4)
- Line numbers in these tasks are from the pre-change tree and will drift; locate code by symbol or element id
- Redirect suite output to the scratchpad rather than piping to `tail`/`grep`, per `CLAUDE.md`
- In this worktree there is no local venv; use the main checkout's venv for `tox`
