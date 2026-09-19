---

description: "Task list for the Current-Period Per-Account Transaction Totals feature"
---

# Tasks: Current-Period Per-Account Transaction Totals

**Input**: Design documents from `specs/20260919-174820-current-period-account-totals/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/view-model.md](./contracts/view-model.md),
[quickstart.md](./quickstart.md)

**Tests**: Test tasks are **required**, not optional. Constitution principle II
(NON-NEGOTIABLE) requires new code to be covered by valid tests and the full suites to
pass before the feature is done.

**Feature name for commits**: `Current Period Account Totals`. Commit messages begin
`Current Period Account Totals - {Milestone}.{Task}` per the constitution's Development
Workflow step 4 — e.g. `Current Period Account Totals - M1.2: ...`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are given in every task

## Path Conventions

Single Python package at the repository root: application code under `biweeklybudget/`,
tests under `biweeklybudget/tests/`, documentation under `docs/`.

---

## Phase 1: Setup — Milestone M0

**Goal**: The written specification, plan and task breakdown exist and are committed
before any code changes, per Constitution principle I.

- [x] T001 Write the feature specification in `specs/20260919-174820-current-period-account-totals/spec.md` and the quality checklist in `specs/20260919-174820-current-period-account-totals/checklists/requirements.md` *(M0.1)*
- [x] T002 Write the implementation plan with the v2.1.2 Constitution Check in `specs/20260919-174820-current-period-account-totals/plan.md`, plus `research.md`, `data-model.md`, `contracts/view-model.md` and `quickstart.md` in the same directory *(M0.2)*
- [x] T003 Write this task breakdown in `specs/20260919-174820-current-period-account-totals/tasks.md` *(M0.3)*
- [ ] T004 Commit the M0 artifacts, then bring up the MariaDB test container and initialise the test databases per the Prerequisites in `specs/20260919-174820-current-period-account-totals/quickstart.md`

**Checkpoint**: Spec artifacts committed; a test database is running and reachable.

---

## Phase 2: Foundational — Milestone M1 (blocks every user story)

**Goal**: The panel shows the viewed period only, transposed. This is the whole
behavioural change.

**Why this is one phase rather than three**: US1, US2 and US3 are three ways of reading
one table, not three slices that can ship separately. A helper that returns columns and a
template that renders rows produce a page that renders nothing coherent, so the helper and
the template must change together. What *is* independently testable is each story's
behaviour once this phase lands, which is how Phases 3-5 are organised.

- [ ] T005 Replace `build_account_period_sums(periods)` with `build_account_sums(period)` in `biweeklybudget/flaskapp/views/payperiods.py`: return `(columns, total)` where `columns` is one `{'id', 'name', 'total'}` dict per account in `period.account_sums` sorted ascending by name, and `total` is their sum (`Decimal('0.0')` when empty). Satisfies contract rules C-1 through C-5 in `specs/20260919-174820-current-period-account-totals/contracts/view-model.md` *(M1.1)*
- [ ] T006 Rewrite the function's docstring in `biweeklybudget/flaskapp/views/payperiods.py` for the single-period contract, dropping the paragraph that explained zero-filling for accounts absent from a period — there are no such accounts in a single-period model (see research decision D3) *(M1.1)*
- [ ] T007 In `PayPeriodView.get()` in `biweeklybudget/flaskapp/views/payperiods.py`, call `build_account_sums(pp)` and pass the results to the template as `acct_sums` and `acct_total`, replacing `acct_period_sums`/`acct_period_totals`. Leave `pp_prev`, `pp_next`, `pp_following` and `pp_last` in place — the Remaining Balances table still needs them (FR-013) *(M1.1)*
- [ ] T008 Transpose the `pp-acct-table` table in `biweeklybudget/flaskapp/templates/payperiod.html`: a `<thead>` row of one `<th><a href="/accounts/{id}">{name}</a></th>` per entry of `acct_sums` followed by `<th>Total</th>`, and a `<tbody>` row of the matching `reddollars`-filtered amounts ending in `acct_total`. Drop the `Account` header cell, all four `/payperiod/` column links, and the `class="info"` current-period emphasis. Leave the panel, its heading text and the `table-responsive` wrapper untouched. Satisfies contract rules H-1 through H-9 *(M1.2)*
- [ ] T009 Verify no reference to `build_account_period_sums`, `acct_period_sums` or `acct_period_totals` survives anywhere outside `specs/`, by grepping the repository *(M1.2)*

**Checkpoint**: The pay period view renders a two-row panel for the viewed period. The
acceptance suite is expected to be red at this point — Phase 3 makes it green against the
new shape.

---

## Phase 3: User Story 1 — See where this period's money moved (Priority: P1) — Milestone M2

**Goal**: Prove the amounts are the viewed period's, that the table is two rows, and that
the row ends in a correct grand total.

**Independent test**: Load a pay period with transactions in several accounts; confirm one
header row of account names and one row of amounts, each amount equal to that account's
transactions in the viewed period, matching what the current-period column showed before.

- [ ] T010 [P] [US1] Create `biweeklybudget/tests/unit/flaskapp/views/test_payperiods.py` with the standard AGPL v3 header copied from a sibling test module, and unit tests for `build_account_sums()` using stub periods: several accounts returned in name order, the grand total, a negative total, and `Decimal` arithmetic throughout (contract C-1 to C-4) *(M2.1)*
- [ ] T011 [US1] Rewrite `test_3_table_present_and_rows` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` to assert the exact transposed header and single amount row via `thead2elemlist`/`tbody2elemlist`, pinning `BankOne` at `-$2,215.67` (red), `CashOne` at `$100.00` and the `Total` at `-$2,115.67` (red) *(M2.1)*
- [ ] T012 [US1] Rewrite `test_6_totals_row_sums_current_column` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` as a check that the final cell equals the sum of the account cells beside it, renaming it for the new shape (FR-007, SC-003) *(M2.1)*
- [ ] T013 [US1] Replace `test_7_headers_match_remaining_balances` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` with a test that the table names no pay period at all: no `/payperiod/` href, no date text, and no `class="info"` cell (FR-009, SC-004, research D2). The old test asserted the very coupling this feature removes *(M2.2)*
- [ ] T014 [US1] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` that loading a *different* pay period shows that period's amounts, not the current period's (FR-001) *(M2.2)*
- [ ] T015 [US1] Update `test_5_totals_include_no_budget_impact` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` for the transposed shape, keeping its point intact: `CashOne`'s `$100.00` of card payment and no-budget-impact transactions against the period's `amt-spent` of `$130.00` (FR-005, FR-012) *(M2.2)*

**Checkpoint**: US1 is demonstrable and covered. `test_2_account_sums` is deliberately left
unchanged — it tests `account_sums`, which this feature does not touch.

---

## Phase 4: User Story 2 — Only accounts with activity, and a way into them (Priority: P2) — Milestone M2

**Goal**: Prove quiet accounts get no column and that account names still link.

**Independent test**: Load a period where one account has no transactions and confirm it
has no column; click a name that is present and confirm it opens that account.

- [ ] T016 [P] [US2] Add unit tests to `biweeklybudget/tests/unit/flaskapp/views/test_payperiods.py` for column membership: an account absent from `account_sums` gets no column, and an account whose total is exactly `Decimal('0.00')` keeps its column (contract C-1, edge case) *(M2.3)*
- [ ] T017 [US2] Update `test_4_quiet_account_absent` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` for the new shape, and extend it to assert that `CreditOne` — which has a transaction in the *previous* period only — now also has no column, proving adjacent-period activity is excluded (FR-003) *(M2.3)*
- [ ] T018 [US2] Update `test_8_account_name_links` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` to find the link in the table header rather than a body row, and keep the click-through assertion (FR-008) *(M2.3)*
- [ ] T019 [US2] Update `test_9_no_datatable_js` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` if needed, and add an assertion that the table is still inside a `table-responsive` ancestor, which is what absorbs the new horizontal growth (FR-011, contract H-9) *(M2.3)*

**Checkpoint**: US2 is demonstrable and covered.

---

## Phase 5: User Story 3 — The panel reads correctly when nothing happened (Priority: P3) — Milestone M2

**Goal**: Prove the empty period renders the panel rather than breaking it.

**Independent test**: Load a pay period with no transactions at all; confirm a `Total`
header over a single `$0.00`.

- [ ] T020 [P] [US3] Add a unit test to `biweeklybudget/tests/unit/flaskapp/views/test_payperiods.py` that a period with empty `account_sums` returns `([], Decimal('0.0'))` rather than raising (contract C-5, FR-010) *(M2.4)*
- [ ] T021 [US3] Rewrite `TestPayPeriodAccountTotalsEmpty.test_2_table_renders_with_zero_totals` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` to assert a single `Total` header cell and a single `$0.00` body cell, with no account columns (FR-010, SC-005, contract H-8) *(M2.4)*
- [ ] T022 [US3] Update the class docstrings of `TestPayPeriodAccountTotals` and `TestPayPeriodAccountTotalsEmpty` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` to describe the single-period transposed table and cite issue #355 alongside #213 *(M2.4)*

**Checkpoint**: All three user stories are demonstrable and covered.

---

## Phase 6: Documentation, Changelog & Verification — Milestone M3

**Goal**: The prose, the screenshot and the changelog describe what actually ships, and
every suite passes in full.

- [ ] T023 [P] Rewrite the `app_usage.per_account_totals` section of `docs/source/app_usage.rst` for the transposed single-period table: one column per account with activity in the period being viewed, a `Total` column, account links, and the `$0.00`-only empty case. Delete the description of five columns matching the Remaining Balances table *(M3.1)*
- [ ] T024 [P] Retain and adjust the `app_usage.per_account_totals.not_budget_totals` subsection of `docs/source/app_usage.rst` — the explanation of why these totals deliberately differ from the budget totals stays (FR-012); only wording that assumed columns-as-periods changes *(M3.1)*
- [ ] T025 [P] Update the `payperiod` screenshot caption in `docs/make_screenshots.py`, removing "across the five periods shown at the top of the page", and make the identical edit to the "Single Pay Period View" caption in `docs/source/screenshots.rst` — that file is generated from the script but is committed, so both must match *(M3.1)*
- [ ] T026 Regenerate the pay period screenshot with `tox -e screenshots` and commit **only** `docs/source/payperiod.png` and `docs/source/payperiod_sm.png`; restore every other PNG the run rewrote. Never run `docs` concurrently. If the run is killed for memory, restore `docs/source/` and note it in the pull request rather than committing a partial set *(M3.1)*
- [ ] T027 Add one concise bullet to `CHANGES.rst` under an `Unreleased` heading (creating the heading beneath the `Changelog` title if absent), led by the issue #355 link, describing the user-visible change in a sentence or two. Do **not** touch `biweeklybudget/version.py` (Constitution principle VI) *(M3.2)*
- [ ] T028 Run the full unit suite to completion — `tox -e py314`, which also applies pycodestyle and pyflakes — redirecting to a scratchpad file, and confirm it passes *(M3.3)*
- [ ] T029 Run the full acceptance suite to completion — `tox -e acceptance` — redirecting to a scratchpad file, and confirm it passes. Re-run any of the known-flaky tests in isolation before attributing a failure to this change *(M3.3)*
- [ ] T030 [P] Run `tox -e docs` to completion and confirm it builds without errors, after any screenshot regeneration has finished (Constitution principle IV) *(M3.3)*
- [ ] T031 [P] Run `tox -e migrations` as a regression check; this feature changes no models and adds no migration, so it must pass untouched *(M3.3)*
- [ ] T032 Walk the manual validation table in `specs/20260919-174820-current-period-account-totals/quickstart.md` against a running app, including the narrow-window horizontal scroll check and a period other than the current one *(M3.3)*
- [ ] T033 Record progress in the feature's spec artifacts, commit the whole milestone, push the branch to `origin`, and open a detailed pull request *(M3.4)*

**Checkpoint**: Feature complete under Constitution Development Workflow steps 5 and 6.

---

## Dependencies

```text
Phase 1 (M0, setup)
      |
      v
Phase 2 (M1, helper + template)   <-- blocks everything below
      |
      +---------------+---------------+
      v               v               v
Phase 3 (US1)   Phase 4 (US2)   Phase 5 (US3)     <-- independent of each other
      |               |               |
      +---------------+---------------+
                      |
                      v
              Phase 6 (M3, docs + verification)
```

**Story dependencies**: none between US1, US2 and US3. All three depend on Phase 2, and
all three feed Phase 6.

**Within Phase 2**: T005 → T006 → T007 → T008 → T009 are sequential; T005-T007 and T009
touch `payperiods.py` and T008 touches the template, but a half-applied pair leaves the
page unrenderable, so they are worked as one unit.

**Within Phases 3-5**: the `[P]` unit-test tasks (T010, T016, T020) touch a different file
from the acceptance tasks and can proceed alongside them. The acceptance tasks within a
phase all edit `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` and are
therefore sequential with respect to each other.

## Parallel Execution Examples

**After Phase 2 completes** — the three unit-test tasks are in one file but in distinct,
non-overlapping test classes, and each acceptance phase is independent of the others:

```text
T010 [P] [US1] unit: ordering, totals, signs
T016 [P] [US2] unit: column membership and the exact-zero account
T020 [P] [US3] unit: the empty period
```

**In Phase 6** — documentation edits touch three separate files:

```text
T023 [P] docs/source/app_usage.rst  (section rewrite)
T025 [P] docs/make_screenshots.py + docs/source/screenshots.rst  (captions)
T030 [P] tox -e docs   # only once T026's screenshot run has finished
T031 [P] tox -e migrations
```

`tox -e docs` must never overlap a `tox -e screenshots` run; `tox -e py314` and
`tox -e acceptance` share the test database and must run sequentially.

## Implementation Strategy

**MVP**: Phase 2 alone delivers the entire user-visible change — a transposed,
current-period-only panel. Phases 3-5 make it verifiable, and Phase 6 makes it shippable.
None of the three is optional: Constitution principle II forbids declaring the feature
done with any suite red or new code uncovered, and principle IV forbids deferring the
documentation.

**Order**: work Phase 2 first and expect the acceptance suite to go red against the old
assertions — that redness is the evidence the shape changed. Then Phase 3, 4 and 5 turn it
green against the new shape, story by story. Do not soften an assertion to accommodate
both shapes; the old shape is gone.

**Milestone approval**: the constitution requires human approval to advance between
milestones. This session was dispatched to run the lifecycle through to a pull request, so
each milestone checkpoint is recorded here and in the commit history for review on the
pull request rather than blocking mid-run.
