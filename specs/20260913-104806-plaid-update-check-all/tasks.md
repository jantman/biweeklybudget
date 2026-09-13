---

description: "Task list for Plaid Update Check All / Uncheck All"
---

# Tasks: Plaid Update Check All / Uncheck All

**Input**: Design documents from `specs/20260913-104806-plaid-update-check-all/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/plaid-update-ui.md, quickstart.md

**Tests**: Included. The spec's success criteria SC-001–SC-003 are verified by them, and
Constitution II requires new code to be covered by valid tests.

**Organization**: Grouped by user story. Both stories are delivered by the same few lines
of template (T003): one helper function and two links. US2 adds only its test. The whole
feature is one milestone (M1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

- Template: `biweeklybudget/flaskapp/templates/plaid_form.html`
- Acceptance tests: `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py` (class `TestPlaidUpdateView`; fixture Items `PlaidItem1`, `PlaidItem2`, checkbox ids `item_PlaidItem1`, `item_PlaidItem2`)
- Docs: `docs/source/plaid.rst`
- Changelog: `CHANGES.rst`

---

## Phase 1: Setup

**Purpose**: A working acceptance-test environment, so the Phase 3 tests can be seen to fail and then pass.

- [X] T001 Start the MariaDB test container and create the test databases per `CLAUDE.md` ("Test Database Setup for Development"), then confirm the unmodified `TestPlaidUpdateView` class passes via `tox -e acceptance -- biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py`, with output redirected to a scratchpad file. That gives a green baseline before any change.

---

## Phase 2: Foundational

None. No shared infrastructure, model, endpoint, or migration is needed.

---

## Phase 3: User Story 1 — Uncheck all, then pick a few (Priority: P1) 🎯 MVP

**Goal**: An "Uncheck All" link on the Plaid Update page clears every item checkbox without submitting or reloading, after which the operator can check individual items and submit only those.

**Independent Test**: The US1 acceptance tests below pass; manually, `quickstart.md` steps 2 and 4.

### Tests for User Story 1

> Write these first and confirm they FAIL against the current template (no `#plaid_uncheck_all` element).

- [X] T002 [US1] In `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py`, class `TestPlaidUpdateView`, add:
  - `test_5_check_uncheck_links`: `#plaid_check_all` and `#plaid_uncheck_all` exist inside `#panel-plaid-update` with texts `Check All` and `Uncheck All`, and every checkbox in `#table-update-plaid input.account-checkbox` starts checked.
  - `test_6_uncheck_all`: click `#plaid_uncheck_all`; assert both item checkboxes are unselected and `selenium.current_url` is still `<base_url>/plaid-update`.
  - `test_7_uncheck_all_then_select_one`: click `#plaid_uncheck_all`, click checkbox `#item_PlaidItem2`; assert the form's serialized data (via `selenium.execute_script` returning `$('#panel-plaid-update form').serialize()`) equals `item_PlaidItem2=1`. This checks what would be submitted without calling Plaid.

### Implementation for User Story 1

- [X] T003 [US1] In `biweeklybudget/flaskapp/templates/plaid_form.html` (see plan "Design" and `contracts/plaid-update-ui.md`):
  - Inside the `<form>` of `#panel-plaid-update`, immediately before `<div class="table-responsive">`, add `<p><a href="javascript:plaidSetAllItems(true);" id="plaid_check_all">Check All</a> | <a href="javascript:plaidSetAllItems(false);" id="plaid_uncheck_all">Uncheck All</a></p>`.
  - In the `extra_foot_script` inline `<script>`, add a JSDoc-commented `function plaidSetAllItems(checked)` that runs `$('#table-update-plaid input.account-checkbox').prop('checked', checked);` and returns nothing. A returned value would replace the page via the `javascript:` URL.
  - Do not change the checkboxes, the Update Transactions button, or the Plaid Items panel.
  - Re-run the T002 tests; they now pass.

**Checkpoint**: US1 is fully functional and testable.

---

## Phase 4: User Story 2 — Check all again (Priority: P2)

**Goal**: A "Check All" link checks every item checkbox without reloading.

**Independent Test**: The US2 acceptance test below passes; manually, `quickstart.md` step 3.

### Tests for User Story 2

- [X] T004 [US2] In `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py`, class `TestPlaidUpdateView`, add `test_8_check_all`: click checkbox `#item_PlaidItem1` to uncheck it, and assert it is unselected. Click `#plaid_check_all`, then assert both item checkboxes are selected and the URL is unchanged. Click `#plaid_check_all` again and assert they stay selected. The implementation is T003's; confirm this test passes.

**Checkpoint**: US1 and US2 both work.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T005 [P] In `docs/source/plaid.rst`, "Updating Transactions via UI", extend step 2 to say the "Check All" and "Uncheck All" links above the table select or clear every Item.
- [X] T006 [P] Add a concise `CHANGES.rst` bullet at the top of `Unreleased`, led by the `Issue #262 <https://github.com/jantman/biweeklybudget/issues/262>`_ link: the Plaid Update page has "Check All" and "Uncheck All" links for the Plaid Items to update. Do not touch `biweeklybudget/version.py`.
- [X] T007 Constitution II/IV gate: run the complete unit (`tox -e py314`) and acceptance (`tox -e acceptance`) suites to completion, plus `tox -e docs`, redirecting output to scratchpad files. All must pass, and a timeout means raise and re-run, never narrow. Run pycodestyle/pyflakes on the changed test file (max-line-length 100). Re-run known-flaky tests (reconcile drag, fuel log search) in isolation before blaming this change.
- [X] T008 Mark all tasks complete in this file, commit (`Plaid Update Check All - M1.N: ...`), push the branch to `origin`, and open a PR against `master` that follows `.github/PULL_REQUEST_TEMPLATE.md`, noting the research R1–R3 judgement calls for the maintainer.

---

## Dependencies & Execution Order

- T001 → T002 → T003 → T004 → T007 → T008.
- T005 and T006 touch separate files and can be done any time after T003, in parallel with each other and with T004.
- US2 depends on US1 only because they share T003's implementation; its test is independent.

### Parallel Opportunities

```text
After T003:  T004 (test_plaid.py)  ∥  T005 (plaid.rst)  ∥  T006 (CHANGES.rst)
```

## Implementation Strategy

MVP is US1 (T001–T003): "Uncheck All" alone solves the issue's main case. US2 costs one
test on the same implementation, so the whole feature ships as one milestone (M1) in
one PR, gated by T007.
