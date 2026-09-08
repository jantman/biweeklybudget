---

description: "Task list for the Cash Position Page feature"
---

# Tasks: Cash Position Page

**Input**: Design documents from `specs/20260908-155554-cash-position-page/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are **included and mandatory**. Constitution principle II
(The Test Gate, NON-NEGOTIABLE) requires new code to be covered by valid tests,
and "Financial correctness" requires tests that pin the expected numbers.

**Organization**: Phases map onto the five milestones in [plan.md](./plan.md).
M1 and M2 are shared infrastructure that every user story needs; M3 delivers
user stories 1 and 2; M4 delivers user story 3; M5 is the documentation and
full test gate.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependency on an incomplete task
- **[Story]**: `[US1]`, `[US2]`, `[US3]` — maps to the user stories in [spec.md](./spec.md)
- Every task names the exact file it touches

## Commit convention

Each task's commit message begins `Cash Position Page - M{milestone}.{task}: `
followed by a one-sentence summary and then detail, per constitution workflow
step 4. Task IDs below carry their milestone number, so T-M1.3 commits as
`Cash Position Page - M1.3: ...`.

## Path conventions

Single Python package at the repository root: `biweeklybudget/`. Tests live in
`biweeklybudget/tests/{unit,acceptance,migrations}/`. Docs in `docs/source/`.

---

## Phase 1 (M1): Schema and Model

**Purpose**: The `budget_accounts` association and its migration. No UI, no
behaviour change. Blocks the diagnostics in US3 and nothing else, but is done
first so the migration is written against an unmodified head.

**⚠️ ORDER-CRITICAL**: T-M1.1 must complete *before* T-M1.2. Alembic
autogenerate compares the models against the live database; if the model
changes first, `initdb` brings the database up to the new state and
autogenerate silently produces an empty migration (constitution III).

- [X] T-M1.1 Bring the test database up to current head `f9df90273cdd` following [quickstart.md](./quickstart.md) §1 — `docker run` the MariaDB container, export the environment, `python dev/setup_test_db.py`, then `initdb`. Confirm with `alembic -c biweeklybudget/alembic/alembic.ini current`.
- [X] T-M1.2 Create the `budget_accounts` table in `biweeklybudget/models/budget_account_link.py` as a `sqlalchemy.Table` on `Base.metadata`: `budget_id` and `account_id`, both non-null `Integer` FKs with `ondelete='CASCADE'`, composite primary key over the pair, `mysql_engine='InnoDB'`. Include the standard AGPL v3 header copied from an existing model module.
- [X] T-M1.3 Import the new module in `biweeklybudget/models/__init__.py` so Alembic and `alembic-verify` see the table.
- [X] T-M1.4 Add the `accounts` relationship to `Budget` in `biweeklybudget/models/budget_model.py` — `relationship('Account', secondary=budget_accounts, backref='budgets')` — plus an `account_ids` property and its `_dict_properties` entry, per [data-model.md](./data-model.md).
- [X] T-M1.5 Generate the migration with `alembic ... revision --autogenerate -m "add budget_accounts table"`, then review and hand-correct the generated file in `biweeklybudget/alembic/versions/`. Verify `down_revision = 'f9df90273cdd'`, that `upgrade()` creates the table with both cascading FKs and the composite PK, and that `downgrade()` drops it.
- [X] T-M1.6 Test the migration both ways against the live test database: `upgrade head`, `downgrade -1`, `upgrade head`. Both directions must run clean (constitution III).
- [X] T-M1.7 Write `biweeklybudget/tests/migrations/test_migration_<rev>.py` following the shape of `test_migration_f9df90273cdd.py`: assert `budget_accounts` is absent in `verify_before` and present in `verify_after`, and that it has the expected columns.
- [X] T-M1.8 Run `tox -e migrations` to completion, redirecting output to a scratchpad file. `alembic-verify` must confirm head matches the models — it only can if T-M1.3 was done.

**Checkpoint**: schema in place and reversible; `tox -e py314` unaffected.

---

## Phase 2 (M2): The Shared Calculation

**Purpose**: The single calculation both the page and the banner consume
(FR-005). This is the foundational phase for every user story — nothing in
US1, US2 or US3 can be built without it.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T-M2.1 Create `biweeklybudget/cashposition.py` with the AGPL v3 header and the `AccountLine`, `BudgetLine` and `CoverageGroup` value types described in [data-model.md](./data-model.md).
- [X] T-M2.2 Implement `CashPosition.__init__(self, sess=None)` in `biweeklybudget/cashposition.py`, defaulting to `db_session` and computing the statement eagerly, selecting exactly the record sets named in [contracts/cash-position-statement.md](./contracts/cash-position-statement.md) (FR-006).
- [X] T-M2.3 Implement the five waterfall terms and both subtotals in `biweeklybudget/cashposition.py`, applying the five normative sign rules from the statement contract — credit balances added with their recorded sign, unreconciled subtracted, no clamping, no `abs()`.
- [X] T-M2.4 Implement `None`-safe balance handling in `biweeklybudget/cashposition.py`: an account with `balance is None` or `balance.ledger is None` contributes `Decimal('0')` and is marked `counted = False` (FR-023).
- [X] T-M2.5 [P] Implement coverage-group construction in `biweeklybudget/cashposition.py` as a pure function over association pairs — iterative BFS over the bipartite graph, restricted to active standing budgets, emitting no group for a component with no budgets (FR-018, FR-019, research R3).
- [X] T-M2.6 [P] Implement `unlinked_accounts` in `biweeklybudget/cashposition.py`: active budget-funding accounts with no *active* linked standing budget. An account linked only to inactive budgets counts as unlinked (FR-017).
- [X] T-M2.7 Refactor the five arithmetic static methods of `NotificationsController` in `biweeklybudget/flaskapp/notifications.py` into delegations to `CashPosition`, keeping their names, signatures, return types and docstring meaning. `num_unreconciled_ofx` is untouched.
- [X] T-M2.8 Write `biweeklybudget/tests/unit/test_cashposition.py` pinning every term, both subtotals and the final figure with **signed** values, including: a credit account in credit, a standing budget with a negative balance, an account with no recorded balance, an account whose `balance.ledger` is `None`, an empty database, and a pay period with nothing in it.
- [X] T-M2.9 Add the FR-004 invariant assertion to `biweeklybudget/tests/unit/test_cashposition.py` across a matrix in which each term takes a zero, positive and negative value: `uncommitted == (ledger + credit) - (standing + pp + unreconciled)`.
- [X] T-M2.10 [P] Add coverage-group unit tests to `biweeklybudget/tests/unit/test_cashposition.py` covering one-account/one-budget, one-account/many-budgets, many-account/many-budget, an account with no budgets, and an account linked only to inactive budgets.
- [X] T-M2.11 Add parity tests to `biweeklybudget/tests/unit/flaskapp/test_notifications.py` asserting the delegating methods return what they returned before, and confirm the pre-existing tests in that file still pass **unchanged**.
- [X] T-M2.12 Run `tox -e py314` to completion, redirecting output to a scratchpad file.

**Checkpoint**: the arithmetic exists, is shared, and is pinned by tests. User story work can begin.

---

## Phase 3 (M3): The Page — User Stories 1 and 2 🎯 MVP

**Goal (US1, P1)**: Show the whole calculation, not just its conclusion — the
five terms, both named subtotals, and a final figure that equals the banner's
discrepancy.

**Goal (US2, P2)**: Trace any line back to where it came from — itemization by
account and budget, ledger alongside projected, and a link on every aggregate.

**Independent Test (US1)**: Load `/cash-position` against a database with
non-zero values for every term; each term, subtotal and the final figure match
values computed independently, and the final figure equals the banner's
reported discrepancy.

**Independent Test (US2)**: Each itemized line names its account or budget, the
itemized values sum to the aggregate above them, and every aggregate link
resolves.

### Tests for Phase 3

- [X] T-M3.1 [P] [US1] Write `biweeklybudget/tests/acceptance/flaskapp/views/test_cash_position.py` asserting the five terms, both subtotals and the final figure by the element IDs fixed in [contracts/cash-position-page.md](./contracts/cash-position-page.md), reading `data-amount` rather than formatted currency.
- [X] T-M3.2 [US1] Add the page-versus-banner agreement test to `biweeklybudget/tests/acceptance/flaskapp/views/test_cash_position.py`: the final figure equals the discrepancy the notification banner reports (FR-004, SC-001).
- [X] T-M3.3 [P] [US1] Add an empty/degenerate-database test to `biweeklybudget/tests/acceptance/flaskapp/views/test_cash_position.py` — the page renders a complete waterfall of zeros rather than failing or omitting lines (FR-022, SC-005).
- [X] T-M3.4 [P] [US2] Add itemization tests to `biweeklybudget/tests/acceptance/flaskapp/views/test_cash_position.py`: each detail table's rows sum to its total, and that total equals the waterfall term above it (FR-011, SC-004).
- [X] T-M3.5 [P] [US2] Add link tests to `biweeklybudget/tests/acceptance/flaskapp/views/test_cash_position.py` asserting every aggregate and per-record link resolves to the URL named in the page contract (FR-012, SC-003).

### Implementation for Phase 3

- [X] T-M3.6 [US1] Create `biweeklybudget/flaskapp/views/cashposition.py` with the AGPL v3 header, a `CashPositionView` `MethodView` rendering `cash-position.html` from a `CashPosition`, and `app.add_url_rule('/cash-position', ...)`.
- [X] T-M3.7 [US1] Create `biweeklybudget/flaskapp/templates/cash-position.html` extending `base.html` and including `notifications.html`, rendering the five terms and two subtotals with the element IDs and `data-amount` attributes from the page contract.
- [X] T-M3.8 [US1] Add the plain-language explanation beside each term in `biweeklybudget/flaskapp/templates/cash-position.html`, in particular that credit balances are recorded negative when money is owed (FR-013).
- [X] T-M3.9 [US1] Render negative amounts distinctly in `biweeklybudget/flaskapp/templates/cash-position.html` using the existing `dollars` and `reddollars` filters; never clamp or `abs()` a subtotal (FR-007).
- [X] T-M3.10 [US1] Add the pay period and per-balance as-of reporting to `biweeklybudget/flaskapp/templates/cash-position.html` (FR-024).
- [X] T-M3.11 [P] [US2] Add the budget-funding account detail table to `biweeklybudget/flaskapp/templates/cash-position.html` — name, ledger, unreconciled, projected, as-of — rendering "no balance recorded" and `data-counted="false"` for an account with no balance (FR-008, FR-023).
- [X] T-M3.12 [P] [US2] Add the credit account and standing budget detail tables to `biweeklybudget/flaskapp/templates/cash-position.html`, each with its own total row (FR-009, FR-010, FR-011).
- [X] T-M3.13 [US2] Add the per-line links in `biweeklybudget/flaskapp/templates/cash-position.html` to `/accounts`, `/accounts/<id>`, `/reconcile`, `/budgets`, `/budgets/<id>` and `/pay_period_for` (FR-012).
- [X] T-M3.14 [US1] Add the "Cash Position" nav entry to `biweeklybudget/flaskapp/templates/nav.html` immediately after "Home", with the `fa-balance-scale` icon.
- [X] T-M3.15 [US1] Update the exact nav link list assertion in `biweeklybudget/tests/acceptance/flaskapp/views/test_base_template.py` to include `('/cash-position', 'Cash Position')` in its new position.
- [X] T-M3.16 [US1] Add the `/cash-position` link to the discrepancy banner in `biweeklybudget/flaskapp/notifications.py`, leaving its wording otherwise unchanged (FR-025), and update the banner-link assertions in `biweeklybudget/tests/acceptance/flaskapp/views/test_base_template.py`.
- [X] T-M3.17 Run `tox -e acceptance` to completion, redirecting output to a scratchpad file.

**Checkpoint**: US1 and US2 fully functional. The page answers the issue's core question and every line is traceable.

---

## Phase 4 (M4): Diagnostics and Link Editing — User Story 3

**Goal (US3, P3)**: Explain structurally unallocated money — name the
budget-funding accounts nothing allocates, and report balance deltas over
coverage groups.

**Independent Test**: With a budget-funding account linked to no standing
budget, and separately with an account linked to budgets whose balances do not
sum to it, the page calls each situation out by name with the amount involved.

### Tests for Phase 4

- [ ] T-M4.1 [P] [US3] Add unlinked-account tests to `biweeklybudget/tests/acceptance/flaskapp/views/test_cash_position.py`: the account is named with its balance and the explanation that its balance sits in the uncommitted total (FR-017, SC-006).
- [ ] T-M4.2 [P] [US3] Add coverage-group tests to `biweeklybudget/tests/acceptance/flaskapp/views/test_cash_position.py` covering the one-account/many-budget case with an exact delta (SC-007), the many-to-many case reported at group level only (FR-019), a balanced group shown as balanced rather than omitted (FR-020), and the all-clear message (FR-021).
- [ ] T-M4.3 [P] [US3] Add a no-links-configured test to `biweeklybudget/tests/acceptance/flaskapp/views/test_cash_position.py`: the waterfall is unaffected, every budget-funding account is listed as unlinked, and the page says the links are not configured (SC-008).
- [ ] T-M4.4 [P] [US3] Add budget modal tests to `biweeklybudget/tests/acceptance/flaskapp/views/test_budgets.py`: link checkboxes appear for a standing budget, are hidden when the type is switched to Periodic, and a saved selection round-trips on reopen.

### Implementation for Phase 4

- [ ] T-M4.5 [US3] Add the diagnostics section to `biweeklybudget/flaskapp/templates/cash-position.html` — `cash-position-diagnostics`, `table-unlinked-accounts`, `coverage-group-<n>` and `diagnostics-all-clear` per the page contract.
- [ ] T-M4.6 [US3] Render the group-level explanation in `biweeklybudget/flaskapp/templates/cash-position.html`: a one-account group is labelled a per-account delta; a multi-account group states that the delta is reported for the group because the application records no split (FR-019).
- [ ] T-M4.7 [US3] Mark accounts in a coverage group that do not contribute to the waterfall — inactive, or not budget-funding — as not counted in `biweeklybudget/flaskapp/templates/cash-position.html`, rather than dropping them (spec Edge Cases).
- [ ] T-M4.8 [P] [US3] Add the `budget_source_accounts` JS global (id → name for active budget-funding accounts) to `biweeklybudget/flaskapp/templates/budgets.html`, and pass the data from both `BudgetsView.get` and `OneBudgetView.get` in `biweeklybudget/flaskapp/views/budgets.py`.
- [ ] T-M4.9 [US3] Add one `acct_<id>` checkbox per budget-funding account to the budget form in `biweeklybudget/flaskapp/static/js/budgets_modal.js`, shown and hidden by `budgetModalDivHandleType()` alongside the standing-balance field, and checked from the `account_ids` returned by `/ajax/budget/<id>` (FR-015, research R4).
- [ ] T-M4.10 [US3] Handle the `acct_<id>` keys in `BudgetFormHandler.submit()` in `biweeklybudget/flaskapp/views/budgets.py`, replacing the budget's linked account set. Ignore them for periodic budgets.
- [ ] T-M4.11 [P] [US3] Add budget/account links to `biweeklybudget/tests/fixtures/sampledata.py` so the acceptance tests have a non-empty coverage group, a balanced group, and at least one unlinked budget-funding account.
- [ ] T-M4.12 Run `tox -e acceptance` and `tox -e py314` to completion, redirecting output to scratchpad files.

**Checkpoint**: all three user stories independently functional.

---

## Phase 5 (M5): Documentation, Version, and the Full Test Gate

**Purpose**: Constitution IV (documentation is part of the change), VI
(versioned, changelogged releases), and II (the full test gate).

- [ ] T-M5.1 [P] Add a "Cash Position" section to `docs/source/app_usage.rst` explaining the waterfall, coverage groups, and why deltas are reported per group rather than per account; cross-link it from the existing "The Unallocated Funds Notification" section.
- [ ] T-M5.2 [P] Create `docs/source/biweeklybudget.cashposition.rst`, `docs/source/biweeklybudget.models.budget_account_link.rst` and `docs/source/biweeklybudget.flaskapp.views.cashposition.rst`, and reference them from `docs/source/biweeklybudget.rst`, `docs/source/biweeklybudget.models.rst` and `docs/source/biweeklybudget.flaskapp.views.rst`.
- [ ] T-M5.3 [P] Add the new page to `docs/source/screenshots.rst` and `docs/make_screenshots.py`.
- [ ] T-M5.4 Bump `VERSION` in `biweeklybudget/version.py` from `1.11.1` to `1.12.0`.
- [ ] T-M5.5 Add the 1.12.0 entry to `CHANGES.rst` in the established format, covering the page, the shared calculation refactor, the schema change, and why deltas are per coverage group.
- [ ] T-M5.6 Update `specs/20260908-155554-cash-position-page/spec.md` and `plan.md` to record what was built, and add a completion note to `checklists/requirements.md`.
- [ ] T-M5.7 Confirm every new Python file carries the standard AGPL v3 copyright header, and that new code is pycodestyle- and pyflakes-clean under the exceptions in `pytest.ini`.
- [ ] T-M5.8 Run the full `tox` suite to completion — `py314`, `docs`, `jsdoc`, `screenshots`, `acceptance`, `docker`, `migrations`, `plaid` — redirecting output to a scratchpad file. A timeout is **not** a pass: raise the timeout and re-run until the suite completes (constitution II).
- [ ] T-M5.9 Walk [quickstart.md](./quickstart.md) end to end against a running `flask rundev` to confirm the feature behaves as documented.
- [ ] T-M5.10 Commit, push the branch to `origin`, and open a pull request describing the change and its constitution compliance.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (M1)** — no dependencies; must be first so the migration is autogenerated against an unmodified head.
- **Phase 2 (M2)** — depends on Phase 1 only for `Budget.accounts` (used by T-M2.5/T-M2.6). **Blocks all user stories.**
- **Phase 3 (M3)** — depends on Phase 2.
- **Phase 4 (M4)** — depends on Phase 2 and Phase 3 (it extends the same template).
- **Phase 5 (M5)** — depends on all of the above.

### User story dependencies

- **US1 (P1)** — needs Phase 2 only. Delivers the MVP on its own.
- **US2 (P2)** — needs Phase 2; shares the template with US1 but its tasks are separable.
- **US3 (P3)** — needs Phase 1 (the association) and Phase 2 (coverage groups), and extends the US1 template.

### Within each phase

- Tests are written alongside implementation, not after it; every checkpoint requires its suite green.
- Model before calculation, calculation before view, view before template detail.
- Migration generated only after the model change, and only against a database at the previous head.

### Parallel opportunities

- T-M2.5 and T-M2.6 are independent functions in the same new module.
- T-M3.1, T-M3.3, T-M3.4, T-M3.5 are separable test additions.
- T-M3.11 and T-M3.12 touch different template blocks.
- T-M4.1 through T-M4.4 are independent test additions; T-M4.8 and T-M4.11 touch unrelated files.
- T-M5.1, T-M5.2 and T-M5.3 are independent documentation files.

### Serial by necessity

- T-M1.1 → T-M1.2 (autogenerate correctness).
- T-M1.2 → T-M1.3 → T-M1.5 → T-M1.6 → T-M1.7 → T-M1.8.
- T-M3.7 → T-M3.8/9/10/11/12/13 — all edit `cash-position.html`.
- T-M4.5 → T-M4.6 → T-M4.7 — same file.
- T-M5.4 → T-M5.5 → T-M5.8.

---

## Implementation Strategy

### MVP

Phase 1 + Phase 2 + the US1 tasks of Phase 3 (T-M3.1, T-M3.2, T-M3.3, T-M3.6
through T-M3.10, T-M3.14, T-M3.15, T-M3.16). That is a working Cash Position
page showing the whole calculation with a bottom line that provably matches the
banner — the issue's central complaint answered — with no itemization and no
diagnostics.

### Incremental delivery

1. Phase 1 → schema in place and reversible.
2. Phase 2 → the arithmetic exists, is shared, and is pinned.
3. Phase 3 US1 → **MVP**: the waterfall.
4. Phase 3 US2 → itemization and traceability.
5. Phase 4 US3 → diagnostics and link editing.
6. Phase 5 → docs, version, full gate, pull request.

Each step leaves the application working and its suites green.

---

## Notes

- `[P]` means different files with no dependency on an incomplete task.
- Commit after each task or logical group, prefixed `Cash Position Page - M{n}.{t}: `.
- Redirect all test output to a scratchpad file rather than piping to `tail` or `grep`, per `CLAUDE.md`, so the whole run can be examined.
- Do not narrow a failing suite to a passing subset, and do not report a timed-out run as green (constitution II).
- The per-milestone approval of constitution principle I is satisfied in advance by the dispatching instruction; see [plan.md](./plan.md).
