---

description: "Task breakdown for issue #357, Omit Accounts From The Account Balances Chart"
---

# Tasks: Omit Accounts From The Account Balances Chart

**Input**: Design documents from `specs/20260919-192038-omit-accounts-from-graphs/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Issue**: [#357](https://github.com/jantman/biweeklybudget/issues/357) · **Branch**: `robot-army/issue-357-allow-excluding-accounts-from-the-index`

**Tests**: Included, and not optional. Constitution II requires new code to be covered by valid tests and the full suites to pass before the feature is declared done.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: The user story from [spec.md](./spec.md) the task serves (US1–US4)
- Every task names the exact file it touches

## Commit convention

Each task commits with the prefix the constitution requires:

```text
Omit Accounts From Graphs - M{milestone}.{task}: {one-sentence summary} (issue #357)
```

so T004 commits as `Omit Accounts From Graphs - M1.1: …`. The mapping is given per
phase below.

## Phase / milestone map

| Phase | Milestone | Delivers |
|---|---|---|
| 1 | M0 | Spec, plan, tasks *(T001–T003 — done)* |
| 2 | M1 | The column and its reversible migration — **blocks everything** |
| 3 | M2 | US1 + US4: the chart honours the flag, and the upgrade is a no-op |
| 4 | M2 | US2: setting the flag from the Account modal |
| 5 | M2 | US3: proving nothing else moved |
| 6 | M3 | Documentation and screenshots |
| 7 | M4 | Changelog, full suites, PR |

---

## Phase 1: Setup (M0 — complete)

**Purpose**: Specification and design. No code.

- [x] T001 Write the feature specification in `specs/20260919-192038-omit-accounts-from-graphs/spec.md` *(commit `e48884b`)*
- [x] T002 Write the plan and Phase 0/1 artifacts in `specs/20260919-192038-omit-accounts-from-graphs/` *(commit `3b06369`)*
- [x] T003 Break the feature into tasks in `specs/20260919-192038-omit-accounts-from-graphs/tasks.md` *(this file)*

**Checkpoint**: Design approved; implementation may begin.

---

## Phase 2: Foundational — the schema (M1)

**Purpose**: Add the column and its migration. Every user story reads or writes this column, so nothing else can start.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [M1.1] Add `omit_from_graphs = Column(Boolean, default=False)` to `Account` in `biweeklybudget/models/account.py`, immediately after the `is_active` column, with a `#:` docstring comment naming issue #357 in the style of the surrounding columns. Declare it identically to `Budget.omit_from_graphs` in `biweeklybudget/models/budget_model.py` — no server default, nullable.
- [X] T005 [M1.2] Re-confirm the current Alembic head is still `3f7c2a91e04b` (`alembic -c biweeklybudget/alembic/alembic.ini current`, or walk `revision`/`down_revision` under `biweeklybudget/alembic/versions/`), then create the migration `biweeklybudget/alembic/versions/<rev>_account_add_omit_from_graphs.py` with `down_revision = '<the head>'`, an `upgrade()` of `op.add_column('accounts', sa.Column('omit_from_graphs', sa.Boolean(), nullable=True))` and a `downgrade()` of `op.drop_column('accounts', 'omit_from_graphs')`, following `biweeklybudget/alembic/versions/6d37400ea9cd_add_omit_from_graphs_boolean_to_budget_.py`.
- [X] T006 [M1.3] Run the migration to head and back down one revision against the test database, confirming the column appears and disappears and that no other Account data is affected, then run `tox -e migrations` to confirm head matches the models (Constitution III).

**Checkpoint**: The column exists and is reversible. Nothing user-visible has changed.

---

## Phase 3: User Story 1 + User Story 4 — the chart honours the flag (Priority: P1) 🎯 MVP

**Goal**: A flagged Account is absent from the chart data entirely, and an Account whose flag has never been set is still charted.

**Independent Test**: With one Account flagged, request `/ajax/chart-data/account-balances`; the flagged Account is in zero series and zero data points, while the dates and every other Account's values are unchanged. With no Account flagged (the post-upgrade state), the response is identical to before the migration.

**Why US1 and US4 share a phase**: they are the same line of code seen from two sides. US4 is not a later refinement — it is the assertion that US1's filter was written `isnot(True)` and not `== False`. Splitting them would let the MVP ship with the one defect that blanks every user's chart on upgrade.

### Implementation

- [X] T007 [US1] [US4] [M2.1] In `AcctBalanaceChartView.get()` in `biweeklybudget/flaskapp/views/index.py`, build the `accounts` name map from `Account.active_accounts(db_session).filter(Account.omit_from_graphs.isnot(True))`. Use `isnot(True)` and **not** `__eq__(False)`: the column is `NULL` for every row that predates the migration, and `NULL = false` is not true in SQL, so the `== False` spelling drops every pre-upgrade Account from the chart (see [research.md](./research.md) R3). Do **not** add the filter to `Account.active_accounts()` itself — six account pickers share that helper and must be unaffected (FR-014).
- [X] T008 [US1] [US4] [M2.1] Extend the `AcctBalanaceChartView` class docstring in `biweeklybudget/flaskapp/views/index.py`, which already documents the issue #356 inactive-account exclusion, to state that Accounts marked omit-from-graphs are excluded the same way and for the same reasons, that an unset (`NULL`) flag means "charted", and that the two exclusions compose so that an Account which is both is excluded once (FR-013). Keep the existing guarantees list intact — in particular the one about dates being unaffected by which accounts are charted, which now covers both exclusions.

### Tests for User Story 1 + 4

- [X] T009 [US1] [US4] [M2.4] Add `TestAcctBalanceChartExcludesOmittedAccounts` to `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`, beside the existing `TestAcctBalanceChartExcludesInactiveAccounts` and modelled on it. Use `@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')` so the class may alter data and have it restored; flag `InvestmentOne` (id 5, active, with balances inside the window) in an ordered first test via the `testdb` fixture. Do **not** flag anything in `biweeklybudget/tests/fixtures/sampledata.py` — see [research.md](./research.md) R5. Assert: the flagged Account is not in `keys`; it is in no `data` row for `''`, `?days=0`, `?days=15` and `?days=365`; every remaining Account's values and the full date list are unchanged from the unflagged response; and an Account that is both inactive and flagged is excluded without error.
- [X] T010 [P] [US4] [M2.4] Add a test to the same class in `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py` asserting that an Account whose `omit_from_graphs` is `NULL` — set explicitly to `None` via `testdb` to reproduce the post-upgrade state — is still present in `keys` and in every `data` row. This is the regression guard for the `== False` trap; without it the defect is invisible until a user upgrades.

**Checkpoint**: The feature's core behaviour works and the upgrade path is pinned. The flag is not yet settable from the UI.

---

## Phase 4: User Story 2 — setting the flag from the modal (Priority: P1)

**Goal**: The Add/Edit Account modal offers an **Omit from graphs?** checkbox that reads and writes the stored setting.

**Independent Test**: Open an Account's modal, tick the checkbox, save, reopen — it is ticked and `GET /ajax/account/<id>` reports `true`. Untick, save, reopen — unticked.

### Implementation

- [X] T011 [P] [US2] [M2.2] In `accountModalDivForm()` in `biweeklybudget/flaskapp/static/js/accounts_modal.js`, add `.addCheckbox('account_frm_omit_from_graphs', 'omit_from_graphs', 'Omit from graphs?')` directly after the existing `Active?` checkbox, matching the label and call shape used at `biweeklybudget/flaskapp/static/js/budgets_modal.js:114`.
- [X] T012 [US2] [M2.2] In `accountModalDivFillAndShow()` in `biweeklybudget/flaskapp/static/js/accounts_modal.js`, set the checkbox from the response with a strict `if(msg['omit_from_graphs'] === true)` test (checked) / `else` (unchecked), placed next to the existing `is_active` block. The strict comparison is what renders a `NULL` flag as unticked rather than as `undefined`.
- [X] T013 [P] [US2] [M2.3] In `AccountFormHandler.submit()` in `biweeklybudget/flaskapp/views/accounts.py`, add `account.omit_from_graphs = data['omit_from_graphs']` immediately after the existing `account.is_active = data['is_active']` line. Add no validation in `validate()` — a checkbox has no invalid value, which is why the Budget handler validates nothing either.

### Tests for User Story 2

- [X] T014 [US2] [M2.4] Add modal coverage to `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py`, following the `budget_frm_omit_from_graphs` pattern in `biweeklybudget/tests/acceptance/flaskapp/views/test_budgets.py`: the Add Account modal shows `account_frm_omit_from_graphs` unticked; an existing unflagged Account's modal shows it unticked; ticking it and saving stores `omit_from_graphs is True` on the Account; reopening shows it ticked; unticking and saving stores `False`; and saving without touching it leaves the stored value unchanged.

**Checkpoint**: The feature is usable end to end.

---

## Phase 5: User Story 3 — proving nothing else moved (Priority: P1)

**Goal**: A flagged Account is unchanged everywhere except the chart.

**Independent Test**: With an Account flagged, the Accounts page, Cash Position, pay period figures, all six account pickers and the stale-data warnings are identical to their output with the flag cleared.

**Why this is its own phase**: FR-014 is the requirement that makes the feature safe to use, and it is verified by *absence* of change — which no other task would notice failing. The call-site table in [research.md](./research.md) R7 is the map of what to check.

- [X] T015 [US3] [M2.4] Add a test to `biweeklybudget/tests/acceptance/flaskapp/views/test_index.py` (in the Phase 3 class) asserting that flagging an Account does not remove it from `Account.active_accounts()` — the guard against the single most likely wrong implementation, folding the filter into that shared helper. Query the helper directly via `testdb` with the Account flagged and assert it is still returned.
- [X] T016 [P] [US3] [M2.4] Verify by inspection and targeted test runs that no other code path reads `omit_from_graphs`: `grep -rn omit_from_graphs biweeklybudget/` must show Account hits only in `models/account.py`, `flaskapp/views/index.py`, `flaskapp/views/accounts.py`, `flaskapp/static/js/accounts_modal.js`, the migration and the tests. Run the accounts, cash-position, payperiod and transaction acceptance modules to confirm they are untouched.

**Checkpoint**: All four user stories are functional and the blast radius is proven to be one chart.

---

## Phase 6: Documentation (M3)

**Purpose**: Constitution IV — a change is not finished until the documentation describing it is updated in the same change.

- [X] T017 [P] [M3.1] Add a "Leaving an account out" subsection to the **Account Balances Chart** section of `docs/source/app_usage.rst`, sitting alongside the existing "Accounts with no recent balances" subsection: what the setting does, that it is per-account on the Edit Account modal, that the account is removed from the chart entirely rather than hidden, that everything else about the account is unaffected, and that legend click-to-hide remains the tool for a temporary hide. Add a pointer to it from the legend bullet in the **Charts** section, mirroring how the Spending Charts section points at the Budget flag.
- [X] T018 [P] [M3.2] In `docs/source/http_api.rst`: add `omit_from_graphs` *(boolean, optional)* to the `POST /forms/account` request-field list, and rewrite the Account Balance Chart Data section's `keys` description — it currently reads "Includes inactive accounts", which issue #356 already made untrue — to state that `keys` holds the charted accounts, being those that are active and not marked omit-from-graphs (FR-020).
- [ ] T019 [M3.3] Regenerate the screenshots that show the Edit Account modal with `tox -e screenshots` and commit the changed PNGs: `docs/source/account1.png`, `account1_sm.png`, `account1-plaid.png`, `account1-plaid_sm.png`. Confirm no other screenshot changed — in particular the index page, which must be unaffected because no sample Account is flagged. Never run `tox -e docs` in the same invocation as `screenshots`; it deletes the PNGs. If a caption needs changing, edit it in `docs/make_screenshots.py`, which generates `docs/source/screenshots.rst`.
- [ ] T020 [M3.4] Run `tox -e docs` to completion, redirecting output to a scratchpad file, and confirm it builds clean including linkcheck.

**Checkpoint**: Documentation matches the code.

---

## Phase 7: Close the feature (M4)

**Purpose**: Constitution VI and II, then delivery.

- [X] T021 [M4.1] Add one concise bullet to `CHANGES.rst` under an `Unreleased` heading (creating the heading directly beneath `Changelog` if absent), led by the issue #357 link, describing the new **Omit from graphs?** setting and noting the schema migration. Keep it to a sentence or two with at most a couple of short sub-bullets, per the existing entries. **Do not link to the new `app_usage.rst` section** — a changelog link to an anchor added in the same pull request fails `tox -e docs` linkcheck; name the section in prose. **Do not touch `biweeklybudget/version.py`**, create a tag, or cut a release.
- [ ] T022 [M4.2] Run the full suites to completion, each redirected to a scratchpad file rather than piped to `tail`/`grep`: `tox -e py314`, `tox -e acceptance`, `tox -e migrations`, `tox -e docs`. All must pass in full — a narrowed or timed-out run is not a pass (Constitution II). Re-run a known-flaky failure (reconcile drag/unignore, fuel log search, Plaid "Uncheck All", docs linkcheck timeouts) in isolation before attributing it to this change.
- [ ] T023 [M4.2] Work through `specs/20260919-192038-omit-accounts-from-graphs/quickstart.md` against a running application, in particular step 2 — the post-upgrade check that an all-`NULL` column still charts every Account.
- [ ] T024 [M4.3] Push the branch to `origin` with `git push -u origin HEAD:refs/heads/robot-army/issue-357-allow-excluding-accounts-from-the-index` (the branch tracks `origin/master`, so a bare `git push` would target master), open a detailed pull request referencing issue #357, monitor CI to completion, and use `/answer-reviews` until Claude's review reports no issues found and Copilot, if present, recommends approval.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (M0)**: complete.
- **Phase 2 (M1)**: blocks everything. No user story can start without the column.
- **Phase 3 (US1+US4)**: depends on Phase 2. This is the MVP.
- **Phase 4 (US2)**: depends on Phase 2 only — the modal work does not need the chart filter, so it could be done in parallel with Phase 3 if staffed. In practice Phase 3 first, because it is the MVP.
- **Phase 5 (US3)**: depends on Phase 3 and Phase 4, since it asserts that neither of them reached further than intended.
- **Phase 6 (M3)**: depends on the behaviour being final, because T019 screenshots the finished modal.
- **Phase 7 (M4)**: depends on everything.

### Within Phase 2

T004 → T005 → T006, strictly sequential: the model change defines the migration, and the migration must exist before it can be run.

### Within Phase 3

T007 and T008 touch the same file and are one logical change. T009 depends on T007. T010 is `[P]` with T009 only in the sense that it is a separate test — both land in the same class, so write them together.

### Parallel opportunities

This is a small feature and most of it is sequential. The genuinely parallel pairs:

- T011 (`accounts_modal.js` form) and T013 (`accounts.py` submit) — different files, no shared state.
- T017 (`app_usage.rst`) and T018 (`http_api.rst`) — different files.
- T016's verification greps can run alongside anything.

---

## Implementation Strategy

### MVP

Phase 2 + Phase 3. At that point a flagged Account is genuinely off the chart and
the upgrade is safe — but the flag can only be set by hand in SQL. That is a
legitimate stopping point for validating the risky half of the feature before
building the UI on top of it.

### Incremental delivery

1. **M1** — column and migration. Reversible, invisible.
2. **M2, Phase 3** — chart exclusion + upgrade guard. The MVP; validate here.
3. **M2, Phase 4** — the modal checkbox. Feature usable end to end.
4. **M2, Phase 5** — prove the blast radius.
5. **M3** — documentation and screenshots.
6. **M4** — changelog, full suites, pull request.

Human approval is required at each milestone boundary (Constitution I).

---

## Notes

- `[P]` tasks touch different files and have no dependency on an incomplete task.
- Commit after each task or logical group, with the `Omit Accounts From Graphs - M{n}.{t}` prefix.
- The one line to get right in this whole feature is T007's `isnot(True)`. T010 is the test that keeps it.
- Redirect suite output to a scratchpad file rather than piping to `tail`/`grep` (CLAUDE.md), so the whole run can be read.
- In this worktree there is no local venv; use the main checkout's `tox`, and `touch .tox/acceptance/liveserver.log` before an acceptance run.
- Any deviation from this breakdown must be recorded in [spec.md](./spec.md) and committed **before** it is acted on (Constitution V).
