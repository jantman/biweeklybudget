---

description: "Task list for restoring the skipped reconcile drag-and-drop acceptance tests"
---

# Tasks: Restore Skipped Reconcile Drag-and-Drop Acceptance Tests

**Input**: Design documents from `specs/20260915-164011-reconcile-drag-tests/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md)

**Tests**: This feature *is* tests. The restored acceptance classes are both the
deliverable and its verification. No separate test tasks are generated.

**Organization**: one milestone (M1). Commit prefix: `Reconcile Drag Tests - M1.<n>`.
All code tasks edit the same file,
`biweeklybudget/tests/acceptance/flaskapp/views/test_reconcile.py`, so they run in
order and are not marked [P].

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: a disposable test database and acceptance environment (quickstart
"Prerequisites")

- [X] T001 Start a throwaway MariaDB 10.4.7 container (`budgettest267`, port 13367), export the `CLAUDE.md` DB variables pointing at it, and run `dev/setup_test_db.py`. Never point acceptance tests at a real database.
- [X] T002 Build the `acceptance` tox env (`tox -e acceptance --notest`) and `touch .tox/acceptance/liveserver.log`.

---

## Phase 2: Foundational

**Purpose**: the one helper both restored classes use (plan "Design", research R2/R3)

- [X] T003 Add `ReconcileHelper.drag_ofx_to_trans(self, selenium, ofx_id, trans_id)` in `biweeklybudget/tests/acceptance/flaskapp/views/test_reconcile.py`:
  - call `self.wait_for_id()` for `ofx_id` and for `'trans-%s' % trans_id`;
  - drag `ofx_id` onto that Transaction's `.reconcile-drop-target` with a **new** `ActionChains(selenium)`, then `perform()`.

  Its docstring must say, in a few lines, that each drag needs its own chain: on
  Selenium < 4.2 a reused chain replays earlier drags on already-hidden OFX divs, which
  failed with "has no size and location" and was why these tests were skipped in 2022.
  It must also say that the page loads both columns by AJAX, and `get()` does not wait
  for them.

**Checkpoint**: the helper exists; nothing calls it yet.

---

## Phase 3: User Story 1 - Multi-pair drag-and-drop reconcile is tested again (Priority: P1) 🎯 MVP

**Goal**: both skipped classes run and pass with their original assertions (FR-001,
FR-002, FR-003).

**Independent Test**: quickstart step 1. Running
`-k "TestDragAndDropReconcile or TestUIReconcileMulti"` reports `18 passed`, none
skipped.

- [X] T004 [US1] In `biweeklybudget/tests/acceptance/flaskapp/views/test_reconcile.py`, `TestDragAndDropReconcile`:
  - delete the `@pytest.mark.skip` line;
  - in `test_07_drag_and_drop`, replace the five inline `chain.drag_and_drop(...).perform()` blocks with helper calls in the same order and pairs: `('ofx-2-OFX3', 3)`, `('ofx-1-OFX1', 1)`, `('ofx-1-OFX2', 2)`, `('ofx-2-OFXT6', 5)`, `('ofx-2-OFXT7', 6)`;
  - delete the 2022 block comment and the `# DEBUG` … `# END DEBUG` scaffold, and the now-unused `chain` local;
  - leave every assertion unchanged.
- [X] T005 [US1] Same file, `TestUIReconcileMulti`:
  - delete the `@pytest.mark.skip` line and the 2022 class docstring;
  - in `test_07_drag_and_drop`, replace the three inline drags with helper calls: `('ofx-2-OFX3', 3)`, then after the existing `self.wait_for_id(selenium, 'ofx-1-OFX2')`, `('ofx-1-OFX1', 1)` and `('ofx-1-OFX2', 2)`;
  - remove both `chain = ActionChains(selenium)` lines; keep all assertions and the existing wait.
- [X] T006 [US1] Run the two classes in isolation (quickstart step 1). Expect `18 passed`. If a test fails because of the page rather than the harness, stop and escalate (FR-006).
- [X] T007 [US1] Run the same selection 5 consecutive times (SC-002). All 5 must report `18 passed`. Save each run's output to the scratchpad.

**Checkpoint**: US1 delivered. The reconcile workflow has acceptance coverage again.

---

## Phase 4: User Story 2 - The cause is understood and recorded (Priority: P2)

**Goal**: no stale notes remain, and the cause is written where it will be read
(FR-004, FR-005).

**Independent Test**: quickstart step 3. The grep finds nothing, and the helper's
docstring and `research.md` R1 state the cause.

- [X] T008 [US2] Run `grep -n "pytest.mark.skip\|2022-10-22\|# DEBUG" biweeklybudget/tests/acceptance/flaskapp/views/test_reconcile.py`. Expect no output. Confirm `ReconcileHelper.drag_ofx_to_trans`'s docstring states the cause, matching `specs/20260915-164011-reconcile-drag-tests/research.md` R1.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T009 [P] Add a concise entry at the top of the `Unreleased` section of `CHANGES.rst`, led by the `Issue #267` link: the Reconcile page's multi-transaction drag-and-drop acceptance tests, skipped since 2022, run again. No sub-bullets are needed; users see no change.
- [X] T010 Run the complete unit suite plus style checks, `tox -e py314`, to completion (constitution II; pyflakes confirms no unused imports are left in `test_reconcile.py`).
- [ ] T011 Run the complete acceptance suite, `tox -e acceptance` (about 17 minutes; run in the background). Expect `acceptance: OK`, with 18 fewer skipped tests than `master`. Known flaky tests (e.g. `test_36_ignore_and_unignore_ofx`) get an isolated re-run before being blamed on this change, and any such re-run is reported.
### Side quest (recorded in spec.md "Side Quest" before starting; research R5)

- [X] T014 Commit the side-quest record (spec.md, research.md, this section) before touching `test_plaid.py`.
- [X] T015 In `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py`, add a `TestPlaidUpdateView` helper that clicks a Check/Uncheck All link and waits until every Item checkbox has the expected state. Use it for every such click in `test_6_uncheck_all`, `test_7_uncheck_all_then_select_one` and `test_8_check_all`, and leave all assertions unchanged.
- [ ] T016 Run `TestPlaidUpdateView` in isolation, then re-run T011 (the complete acceptance suite).

- [ ] T012 Update `specs/20260915-164011-reconcile-drag-tests/spec.md` Status and mark these tasks done. Commit all M1 changes with a `Reconcile Drag Tests - M1.<n>:` message.
- [ ] T013 Push the branch to `origin`, open a PR against `master` using `.github/PULL_REQUEST_TEMPLATE.md`, monitor CI (`acceptance` and `docker` both run these tests), and answer reviews with `/answer-reviews` until Claude reports "No issues found" and Copilot, if present, recommends approval.

---

## Dependencies & Execution Order

- **Setup (T001-T002)** → **Foundational (T003)** → **US1 (T004-T007)** → **US2 (T008)** → **Polish (T010-T013)**.
- T009 (`CHANGES.rst`) touches a different file and can be done any time after T003 [P].
- T004 and T005 edit the same file. Do them one after the other, and do both before
  T006, which runs both classes.
- T010 and T011 share the test database, so run them one after the other, never
  together.
- US2 depends on US1: its cleanup is part of the T004/T005 edits, and T008 only
  verifies it.

## Parallel Example

```bash
# Only one pair of tasks can run in parallel (different files, no dependency):
Task: "T005 Restore TestUIReconcileMulti in test_reconcile.py"   # after T004
Task: "T009 Add the Issue #267 entry to CHANGES.rst"
```

## Implementation Strategy

- **MVP**: US1 (T001-T007). Coverage is back and proven stable.
- US2 is a verification step on the same edits. It is cheap, but it stops the 2022
  mistake from being repeated in the next drag test.
- Polish closes the constitution's test gate and delivers the PR.

## Notes

- No application code changes (FR-006). If the page turns out to be at fault, stop and
  escalate rather than changing it.
- Do not weaken any assertion to get a pass (FR-003).
