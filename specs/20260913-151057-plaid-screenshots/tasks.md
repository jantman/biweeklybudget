---

description: "Task list for Plaid Screenshots"
---

# Tasks: Plaid Screenshots

**Input**: Design documents from `specs/20260913-151057-plaid-screenshots/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/screenshots.md, quickstart.md

**Tests**: The screenshot generator is exercised by a full `screenshots` run (also a CI
job); there is no pytest for it. The result-template fix (FR-009) gets a unit test that
renders the real template (Constitution II). The whole feature is one milestone (M1).

**Organization**: Grouped by user story. All three stories edit the `screenshots` list in
`docs/make_screenshots.py`, so their tasks are sequential, not parallel.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

- Generator: `docs/make_screenshots.py` (`Screenshotter.screenshots`, preshot methods, `Screenshotter.run`)
- Template: `biweeklybudget/flaskapp/templates/plaid_result.html`
- Unit test: `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py`
- Docs: `docs/source/plaid.rst`; Changelog: `CHANGES.rst`

---

## Phase 1: Setup

- [X] T001 Start a MariaDB 10.4.7 test container on a port no other worktree uses, create the test databases (`dev/setup_test_db.py`), and write the DB and tox environment variables to a scratchpad `env.sh`. Create a scratchpad venv with `pycodestyle` and `pyflakes` for linting `docs/make_screenshots.py`.
  - *Done 2026-09-13.* Container `budgettest-issue264` on port 13364.

---

## Phase 2: User Story 1 - Plaid Update page (Priority: P1) MVP

**Goal**: The Screenshots page shows the Plaid Update page (FR-001, FR-004).

**Independent Test**: A `screenshots` run produces `plaid-update.png` showing both sample Items in both tables.

- [X] T002 [US1] Add a `plaid-update` entry (path `/plaid-update`, title "Plaid Update", one-sentence description) to `Screenshotter.screenshots` in `docs/make_screenshots.py`, directly after the `ofx` entry.

---

## Phase 3: User Story 3 - Linking an Account to Plaid (Priority: P3)

Listed before US2 because its entry comes second on the page (research R3); it has no dependency on US2.

**Goal**: The Screenshots page shows the Edit Account modal with its Plaid Account selector visible (FR-003).

**Independent Test**: `account1-plaid.png` shows the selector set to `Inst1 / Acct1 (foo)`.

- [X] T003 [US3] In `docs/make_screenshots.py`, add an `account1-plaid` entry (path `/accounts/1`, title "Linking an Account to Plaid") after `plaid-update`, with a `_account_plaid_preshot` method that waits for the modal and scrolls `#modalDiv` to the bottom.

---

## Phase 4: User Story 2 - Plaid Update result (Priority: P2)

**Goal**: The Screenshots page shows a Plaid Update result with one success, one failure and the total row (FR-002, FR-005, FR-009).

**Independent Test**: `plaid-update-result.png` shows an Inst1 row with counts and statement IDs, an Inst2 row with the sample error, and "1 Failed" in the Total row, from a run with no Plaid credentials.

- [X] T004 [US2] Write a unit test in `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` that renders the real `plaid_result.html` with a result that has statement IDs and asserts they appear in the "Statement IDs" cell. Run it and confirm it fails.
  - *Done 2026-09-13.* `TestPlaidResultTemplate::test_statement_ids_and_failure` failed before the fix, on the `<td>[21728, 21729]</td>` assertion only (the page rendered and the Item row matched).
- [X] T005 [US2] Fix `biweeklybudget/flaskapp/templates/plaid_result.html` to render `pur.stmt_ids` instead of the nonexistent `pur.stmt_id`; confirm T004's test passes.
- [X] T006 [US2] In `docs/make_screenshots.py`, add a stub `PlaidUpdater` subclass (no Plaid client; `update()` returns fixed `PlaidUpdateResult`s per data-model.md, writes nothing) and install it on `biweeklybudget.flaskapp.views.plaid` in `Screenshotter.run` before `self.server.start()`. Add a `plaid-update-result` entry (path `/plaid-update?item_ids=ALL`, title "Plaid Update Result") after `account1-plaid`.

---

## Phase 5: Polish & Cross-Cutting

- [X] T007 [P] Add a sentence to the Usage section of `docs/source/plaid.rst` linking to the Screenshots page (`:doc:`screenshots``) for the Plaid Update page, linking an Account, and update results (FR-007).
- [X] T008 [P] Add a concise `Unreleased` entry for issue #264 to `CHANGES.rst` (new Plaid screenshots; result page now shows statement IDs). Do not change `biweeklybudget/version.py`.
- [X] T009 Lint the changed parts of `docs/make_screenshots.py` with pycodestyle (repo `setup.cfg`) and pyflakes.
  - *Done 2026-09-13.* No new warnings. The remaining E402s (imports after the settings setup) and pyflakes warnings (`re`, `defaultdict`, duplicate `os`) are in lines this change does not touch.
- [X] T010 Run `tox -e screenshots` with no `PLAID_*` variables set; review the three new images against `contracts/screenshots.md` and check that the existing entries are unchanged in the generated `screenshots.rst` (SC-002, SC-003). Then discard the regenerated files under `docs/source/` (research R5).
  - *Done 2026-09-13.* `screenshots: OK` with no Plaid credentials. All three images match the contract; the result page shows `[21728]` under Statement IDs, the sample error for Inst2, and "1 Failed" (HTTP 500 from the view, as designed for a failed Item). The generated `screenshots.rst` only adds sections (the three Plaid ones, plus Cash Position and Spending Charts from earlier features); the one changed line is the Single Pay Period description, a mismatch that predates this change (the committed `.rst` was edited by hand, the generator was not). Regenerated files discarded.
- [X] T011 Test gate: run `tox -e py314`, `tox -e acceptance` and `tox -e docs` to completion, sequentially for the two DB suites, with output redirected to scratchpad files. All must pass.
  - *Done 2026-09-13.* `py314: OK`, 961 passed, 4 skipped (fresh env, no cached style checks). `acceptance: OK`, 880 passed, 24 skipped (20 min). `docs: OK`, with no broken links and the `plaid.rst` link resolving to the Screenshots page. A first `docs` run failed only because it overlapped the `screenshots` run, which deletes and rewrites the PNGs that linkcheck checks; re-run on its own, it passed.
- [X] T012 Mark tasks complete in this file, record the test results, and commit.
- [X] T013 At the maintainer's request (research R5, superseded), commit the three Plaid screenshots to `docs/source/` (`plaid-update`, `account1-plaid`, `plaid-update-result`, each with its `_sm.png` thumbnail) and add their sections to `docs/source/screenshots.rst` after "OFX Transactions", exactly as the generator writes them. Re-run `tox -e docs` so linkcheck confirms the image targets exist.

---

## Dependencies & Execution Order

- T001 before everything that runs code (T004, T009-T011).
- T002 → T003 → T006: same list in the same file, in page order.
- T004 → T005 (test first).
- T007, T008 are independent of all other tasks.
- T010 after T002, T003, T005, T006. T011 after all code changes. T012 last.

## Parallel Opportunities

- T007 and T008 alongside any code task.
- T004/T005 (template) alongside T002/T003 (generator): different files.

## Implementation Strategy

MVP is T002 alone: one Plaid screenshot. The rest adds the linking and result
screenshots and the result-page fix, all in one milestone and one pull request.
