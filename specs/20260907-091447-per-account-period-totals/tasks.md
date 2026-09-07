---

description: "Task list for the Per-Account Transaction Totals Per Pay Period feature"
---

# Tasks: Per-Account Transaction Totals Per Pay Period

**Input**: Design documents from `specs/20260907-091447-per-account-period-totals/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/account-sums.md](./contracts/account-sums.md), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are **required**, not optional, for this feature. Constitution Principle II
(The Test Gate, NON-NEGOTIABLE) requires new code to be covered by valid tests, and the
Technology & Security Constraints require that changes to pay-period arithmetic be accompanied
by tests that pin the expected numbers. This feature is pay-period arithmetic.

**Organization**: Tasks are grouped by user story so each can be implemented and verified as an
independent increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story the task serves (US1, US2, US3)
- Every task names the exact file it changes

## Path Conventions

Single project, existing layout. Application code under `biweeklybudget/`, tests under
`biweeklybudget/tests/`, documentation under `docs/source/`, all relative to the repository root.

---

## Phase 1: Setup

**Purpose**: Bring up the environment the later phases verify against. No production code.

- [X] T001 Start the MariaDB test container and export the test environment variables from `CLAUDE.md` ("Test Database Setup for Development"), then run `python dev/setup_test_db.py` from the activated `venv`. No `initdb` re-run and no migration are needed: this feature changes no schema.
- [X] T002 Confirm the baseline is green before touching anything, by running `pytest biweeklybudget/tests/unit/test_biweeklypayperiod.py` and redirecting output to a scratchpad file. Any pre-existing failure must be understood before it can be distinguished from one this feature introduces.

**Checkpoint**: Test database reachable; existing pay period unit tests pass.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The per-account sums themselves. Every user story reads these numbers, so this
phase blocks all three. It changes no page and is verifiable entirely by unit test.

⚠️ **MUST complete before Phase 3.**

- [X] T003 Add `_make_account_sums()` to `biweeklybudget/biweeklypayperiod.py`, placed after `_make_budget_sums()` and before `overall_sums`. It iterates `self.transactions_list` once, accumulating `{account_id: {'name': t['account_name'], 'total': Decimal}}`, applying **no** filtering — real and scheduled transactions alike, and `no_budget_impact` transactions included (research R2). Seed each new entry's total with `Decimal('0.0')` so the value type is always `Decimal`. Write a full docstring in the style of `_make_budget_sums()`, stating the return shape, that unfiltered inclusion is deliberate, and that these totals are not expected to reconcile with `budget_sums`.
- [X] T004 Add the `account_sums` property to `biweeklybudget/biweeklypayperiod.py`, immediately after the `budget_sums` property, returning `self._data['account_sums']` with a docstring cross-referencing `_make_account_sums()`, exactly mirroring how `budget_sums` and `overall_sums` are written.
- [X] T005 Wire the result into the cache in `BiweeklyPayPeriod._data` in `biweeklybudget/biweeklypayperiod.py`: add `self._data_cache['account_sums'] = self._make_account_sums()` after the `budget_sums` line and before the `overall_sums` line. Ordering matters only for readability here — `_make_account_sums()` reads `transactions_list`, which is already populated by that point — but grouping it with the other two sums keeps `clear_cache()` correct without further change.
- [X] T006 Update `TestData::test_initial` in `biweeklybudget/tests/unit/test_biweeklypayperiod.py` to patch `_make_account_sums`, to expect the new `'account_sums'` key in the asserted `_data` dict, and to assert the new method's `mock_calls`. Do the same for `TestData::test_cached` if it enumerates cache keys. This is the one existing assertion the new cache key breaks; it is a mechanical update, not a behaviour change.
- [X] T007 [P] Add `TestAccountSums` to `biweeklybudget/tests/unit/test_biweeklypayperiod.py`, modelled exactly on the existing `TestBudgetSums`: set `_data_cache = {'account_sums': m}` and assert the property returns `m`.
- [X] T008 Add `TestMakeAccountSums` to `biweeklybudget/tests/unit/test_biweeklypayperiod.py` with these cases, each patching `transactions_list` with hand-built trans dicts and asserting literal `Decimal` amounts: (a) several transactions across two accounts sum per account and carry the right names; (b) a scheduled transaction is counted, at its projected amount; (c) a transaction split across two budgets contributes its own `amount` exactly once, not once per split; (d) a `no_budget_impact` transaction **is** counted, and a credit card payment likewise — the explicit inverse of `TestMakeBudgetSumsNoBudgetImpact`; (e) an empty `transactions_list` returns `{}`; (f) a negative amount produces a negative total; (g) the invariant that the sum of all `total` values equals the sum of every transaction's `amount`.
- [X] T009 Run `pytest biweeklybudget/tests/unit/test_biweeklypayperiod.py` redirected to a scratchpad file and confirm every test passes, then run `pytest --flake8 --pycodestyle` over the changed file, or the project's configured lint invocation, and confirm it is clean.

**Checkpoint**: `account_sums` returns correct numbers, is cached with the other sums, is covered
by tests that pin literal amounts, and no rendered page has changed. Delivers FR-004 and FR-013.

---

## Phase 3: User Story 1 — Per-account totals for the pay period being viewed (Priority: P1) 🎯 MVP

**Goal**: The pay period view shows a table of each account's total for the period being viewed.

**Independent test**: Open a pay period with transactions against more than one account; the new
table lists each account with a total equal to the sum of that account's rows in the page's
Transactions table.

- [ ] T010 [US1] Add a module-level helper `build_account_period_sums(periods)` to `biweeklybudget/flaskapp/views/payperiods.py`, taking an ordered list of `BiweeklyPayPeriod` objects and returning `(rows, column_totals)` in the shape given in [data-model.md](./data-model.md) "Derived structure 2": rows are `{'id', 'name', 'totals'}` dicts sorted by name, `totals` has one `Decimal` per period in the given order with `Decimal('0.0')` where an account has no activity, and `column_totals` is the per-period sum across rows. Taking a list rather than five arguments is what lets Phase 4 widen the table without rewriting this. Give it a docstring; it is picked up by the Sphinx API docs.
- [ ] T011 [US1] In `PayPeriodView.get()` in `biweeklybudget/flaskapp/views/payperiods.py`, bind the five pay period objects to local names once — `pp_prev`, `pp`, `pp_next`, `pp_following`, `pp_last` — and rewrite the existing `pp_*_sums` and `pp_*_date` template arguments to read from those bindings instead of re-walking `pp.next.next.next`. The values passed must be identical; this exists so that Phase 4 can read `account_sums` from the same objects without recomputing a period's data (research R4). Verify FR-014 by running the existing `TestCurrentPayPeriod` and `TestPayPeriodOtherPeriodInfo` acceptance tests unchanged.
- [ ] T012 [US1] In `PayPeriodView.get()`, call `build_account_period_sums([pp])` and pass the result to the template as `acct_period_sums` and `acct_period_totals`.
- [ ] T013 [US1] Add the per-account totals panel to `biweeklybudget/flaskapp/templates/payperiod.html`, in its own full-width row placed after the row of four summary tiles and before the row containing the budget and transaction tables (research R7). Follow the structure in [contracts/account-sums.md](./contracts/account-sums.md): `div.panel.panel-default` with heading "Per-Account Transaction Totals", `div.table-responsive`, `table.table.table-bordered#pp-acct-table`, an Account column plus one period column, amounts rendered with `|reddollars|safe` so negatives are red (FR-007), and the current period's `th` and `td`s carrying `class="info"` (FR-008). Add no JavaScript and no DataTables initialisation.
- [ ] T014 [US1] Render the totals row as the final `tbody` row, with `<strong>Total</strong>` in the Account column and `acct_period_totals` across the rest (FR-011).
- [ ] T015 [US1] Add `TestPayPeriodAccountTotals` to `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py`, following the `TestCurrentPayPeriod` pattern: build fixture transactions across at least three accounts including one negative amount and one `no_budget_impact` transaction, load the pay period view, locate `pp-acct-table` by id, extract rows with `self.tbody2elemlist()` and assert the full `innerHTML` list against literal expected values — covering account names, per-account totals, the red span on the negative, the `$0.00` on an account with no activity, and the totals row.
- [ ] T016 [US1] Add an acceptance test to the same class asserting the table renders with headers and a zero totals row, and does not raise, for a pay period containing no transactions at all (spec edge case 1).
- [ ] T017 [US1] Run the pay period acceptance tests — `tox -e acceptance -- -k "PayPeriod"` redirected to a scratchpad file — and confirm both the new tests and every pre-existing one pass.

**Checkpoint**: US1 is complete and independently shippable. Delivers FR-001, FR-002, FR-006,
FR-007, FR-011, FR-012 and FR-014 for a single column, and SC-001, SC-002 and SC-003.

---

## Phase 4: User Story 2 — Compare each account across neighbouring pay periods (Priority: P2)

**Goal**: The table's columns are the same five pay periods the "Remaining Balances" table shows.

**Independent test**: The table's column headers match `#pay-period-table`'s in order, label,
suffix and linking, and each cell matches the total that account has when that period is opened
directly.

**Depends on**: Phase 3 (widens the table Phase 3 built; the helper already takes a list).

- [ ] T018 [US2] In `PayPeriodView.get()` in `biweeklybudget/flaskapp/views/payperiods.py`, change the `build_account_period_sums` call to pass all five bound periods in column order — `[pp_prev, pp, pp_next, pp_following, pp_last]`. Because T011 bound them once, this adds no database work: each period's `_data` was already built for its `overall_sums`.
- [ ] T019 [US2] Widen the header row of `#pp-acct-table` in `biweeklybudget/flaskapp/templates/payperiod.html` to five period columns, reusing the `pp_prev_date`/`pp_prev_suffix` family of template variables already passed for `#pay-period-table` so the two headers cannot drift apart. Non-current headers are `<a href="/payperiod/{{ ... |dateymd }}">` links (FR-009); the current period's header stays plain text with `class="info"` (FR-003, FR-008).
- [ ] T020 [US2] Widen the body and totals rows of `#pp-acct-table` to iterate the five entries of each row's `totals` and of `acct_period_totals`, keeping `class="info"` on the current period's cell in every row including the totals row.
- [ ] T021 [US2] Extend `TestPayPeriodAccountTotals` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` with a test asserting the header row's `innerHTML`: five period columns in order, the correct `/payperiod/YYYY-MM-DD` hrefs on the four non-current ones, the `(prev.)` / `(curr.)` / `(next)` suffixes, and `class="info"` on the current one.
- [ ] T022 [US2] Add a test to the same class asserting cross-period correctness: with fixture transactions in more than one of the five displayed periods, an account's row shows the right total in each column and `$0.00` in the columns where it has no activity (FR-006), and the totals row sums each column independently.
- [ ] T023 [US2] Add a test to the same class asserting that the columns of `#pp-acct-table` line up with those of `#pay-period-table` — same count, same date labels, same order — by reading both tables' header rows in one page load. This is the assertion that keeps FR-003 true if either table's period set is ever changed.
- [ ] T024 [US2] Run `tox -e acceptance -- -k "PayPeriod"` redirected to a scratchpad file; all pass.

**Checkpoint**: US2 complete. Delivers FR-003, FR-008 and FR-009, and completes FR-006 and
FR-011 across all five columns.

---

## Phase 5: User Story 3 — Reach an account's detail from its total (Priority: P3)

**Goal**: Account names in the table link to the account.

**Independent test**: Clicking an account name opens that account's detail page.

**Depends on**: Phase 3 (the rows it links from).

- [ ] T025 [US3] Wrap the account name cell in `#pp-acct-table` in `biweeklybudget/flaskapp/templates/payperiod.html` in `<a href="/accounts/{{ row['id'] }}">`, matching how budget names link in `#pb-table` and account names link in `#trans-table` (FR-010).
- [ ] T026 [US3] Extend the `innerHTML` assertions in `TestPayPeriodAccountTotals` in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` to expect the anchor markup, and add a test that clicks an account name and asserts the resulting URL is that account's detail view.

**Checkpoint**: All three user stories complete. Every functional requirement delivered.

---

## Phase 6: Documentation

**Purpose**: Constitution Principle IV — documentation ships with the change, not after it.

- [ ] T027 [P] Add a section to `docs/source/app_usage.rst` describing the per-account transaction totals table: what it totals, that it covers the five pay periods shown across the top of the view, and — prominently — that it deliberately **includes** credit card payments and no-budget-impact transactions and therefore is not expected to agree with the budget totals on the same page, because it reports account activity rather than budget consumption (research R2).
- [ ] T028 [P] Update the "Single Pay Period View" caption in `docs/source/screenshots.rst` to mention the per-account transaction totals. The screenshot images themselves are regenerated by `tox -e screenshots` as part of the release checklist, not per feature.
- [ ] T029 Confirm `README.rst` and `CLAUDE.md` need no change — neither enumerates the contents of this view — and record that conclusion here rather than leaving it unstated.

**Checkpoint**: Documentation describes the feature as shipped.

---

## Phase 7: Full Verification

**Purpose**: Constitution Principle II. A narrowed run is not a pass, and a timed-out run is not
a pass.

- [ ] T030 Run `tox -e py314` to completion, output redirected to a scratchpad file. All pass.
- [ ] T031 Run `tox -e acceptance` to completion — the whole suite, not a `-k` selection — output redirected to a scratchpad file. All pass. If it times out, raise both the pytest timeout and the invoking tool's timeout and re-run until it completes.
- [ ] T032 [P] Run `tox -e docs` to completion. It must build with no errors, including the API documentation for the new property and helper.
- [ ] T033 [P] Run `tox -e migrations` to completion. This feature changes no schema; the run demonstrates it did not disturb the environment.
- [ ] T034 Walk the manual checks in [quickstart.md](./quickstart.md) §3 and §4 against a running `flask rundev`, in particular verifying by hand that one account's cell equals the sum of that account's rows in the Transactions table (SC-002).

**Checkpoint**: Every suite the constitution requires has run to completion and passed.

---

## Phase 8: Release Bookkeeping & Delivery

**Purpose**: Constitution Principle VI, and this session's delivery obligation.

- [ ] T035 Bump `VERSION` in `biweeklybudget/version.py` from `1.8.0` to `1.9.0` — a new backwards-compatible user-visible feature.
- [ ] T036 Add the `1.9.0` entry to `CHANGES.rst` in the established format, citing `Issue #213`, describing the table, the five-period scope and why that reading of the issue was chosen, and stating plainly that account totals include credit card payments and no-budget-impact transactions and so will not match the budget totals.
- [ ] T037 Record the outcome of each phase in this file, ticking the boxes, so the spec artifacts reflect what was actually built (Constitution Development Workflow step 5c).
- [ ] T038 Commit, push the branch to `origin`, and open a pull request describing the change, the Constitution Check result, the "for each payperiod" interpretation the author may overrule, and the recorded Principle I deviation on milestone approval.
- [ ] T039 Monitor the pull request's CI jobs to completion, and respond to review feedback with `/answer-reviews` until Claude's review reports no issues and Copilot's, if present, recommends approval.

---

## Dependencies & Execution Order

```text
Phase 1 (Setup)
   ↓
Phase 2 (Foundational: account_sums)  ← blocks everything
   ↓
Phase 3 (US1, P1)  ← MVP; independently shippable
   ↓
   ├── Phase 4 (US2, P2)  ← widens US1's table
   └── Phase 5 (US3, P3)  ← links US1's rows; independent of Phase 4
   ↓
Phase 6 (Documentation)
   ↓
Phase 7 (Full verification)
   ↓
Phase 8 (Release & delivery)
```

**Story independence**: US1 stands alone and delivers the issue's core value. US2 and US3 each
build on US1's table but not on each other, and could be done in either order or dropped without
affecting the other. US3's template edit (T025) and US2's (T019, T020) touch the same file and so
must not be run in parallel with each other.

## Parallel Execution Opportunities

Genuinely parallelisable work is limited here — most tasks touch one of four files — and is
marked `[P]`:

- **Phase 2**: T007 (a new independent test class) alongside T003/T004/T005.
- **Phase 6**: T027 and T028 edit different documentation files.
- **Phase 7**: T032 (`docs`) and T033 (`migrations`) are independent of each other and of the
  test suites, and may run concurrently if the machine can host the containers.

Everything else is sequential, because it edits `biweeklypayperiod.py`, `payperiods.py`,
`payperiod.html` or `test_payperiods.py`, one file at a time.

## Implementation Strategy

**MVP** is Phase 1 → Phase 2 → Phase 3. That alone satisfies the narrow reading of issue #213 —
a table of per-account transaction totals on the pay period view — and is shippable on its own.

**Incremental delivery**: Phase 4 then widens the same table to five periods, which is the
reading of "for each payperiod" the spec adopts, and Phase 5 adds navigation. Building the view
helper to take a list of periods from the start (T010) is what makes Phase 4 a widening rather
than a rewrite.

**Risk concentrated in one task**: T011 is the only task that edits code paths feeding existing,
asserted numbers. It is a pure refactor — bind then read, instead of re-walking — and the
existing acceptance tests for the "Remaining Balances" table and the four summary tiles are the
check on it. If those tests fail after T011, the refactor is wrong; nothing later in the plan
should be attempted until they are green again.
