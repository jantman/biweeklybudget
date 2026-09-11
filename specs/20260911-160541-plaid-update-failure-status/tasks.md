---

description: "Task list for Plaid Update Reports Failure In Its Status Code"
---

# Tasks: Plaid Update Reports Failure In Its Status Code

**Input**: Design documents from `specs/20260911-160541-plaid-update-failure-status/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/plaid-update.md, quickstart.md

**Tests**: Included. The spec's success criteria SC-001/SC-002 are verified by them, and
Constitution II requires new code to be covered by valid tests.

**Organization**: Grouped by user story. Both stories are P1 and are delivered by the same
few lines in one method, so they share the implementation task (T003) and differ in
the cases their tests pin. The whole feature is one milestone (M1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

## Path Conventions

- View: `biweeklybudget/flaskapp/views/plaid.py`
- View unit tests: `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` (class `TestPlaidUpdate`)
- Docs: `docs/source/plaid.rst`, `docs/source/http_api.rst`
- Changelog: `CHANGES.rst`

---

## Phase 1: Setup

**Purpose**: A working test environment, so the tests in Phase 3 can be seen to fail and then pass.

- [ ] T001 Start the MariaDB test container and create the test databases per `CLAUDE.md` ("Test Database Setup for Development"), then confirm the unmodified `TestPlaidUpdate` class passes via `tox -e py314 -- biweeklybudget/tests/unit/flaskapp/views/test_plaid.py`. That gives a green baseline before any change.

---

## Phase 2: Foundational

None. No shared infrastructure, model, or migration is needed.

---

## Phase 3: User Story 1 — An unattended update that fails is detected (Priority: P1) 🎯 MVP

**Goal**: A `/plaid-update` request in which any Plaid Item fails returns HTTP 500 in all three response formats, with an unchanged body.

**Independent Test**: The US1 unit tests below pass. Manually, `quickstart.md` step 2 makes `curl --fail` exit 22 when an Item's login is reset.

### Tests for User Story 1

> Write these first and confirm they FAIL against the current code (which returns a bare body, i.e. implicitly 200).

- [ ] T002 [US1] In `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py`, class `TestPlaidUpdate`:
  - Change the assertions in `test_update_template`, `test_update_plain`, and `test_update_plain_nondefault_num_days`. Each of these already includes a `success=False` result, so each must now assert `res == (<same body as today>, 500)`.
  - Add `test_update_json_failure`: `Accept: application/json` with one successful and one failed result. Assert `res == (mock_json, 500)` and that `jsonify` is called with both results' `as_dict`.
  - Add `test_update_all_failed`: `Accept: text/plain`, every result failed. Assert status 500 and a body listing each failure with `0 updated, 0 added, 2 account(s) failed`.

### Implementation for User Story 1

- [ ] T003 [US1] In `biweeklybudget/flaskapp/views/plaid.py`, `PlaidUpdate._update()`:
  - Right after `results = updater.update(...)`, compute `status = 200 if all(r.success for r in results) else 500`.
  - Return `(s, status)` from the `text/plain` branch, `(jsonify(...), status)` from the `application/json` branch, and `(render_template(...), status)` from the HTML branch.
  - Change nothing else in the bodies (spec FR-004).
  - Add a sentence to the `_update` docstring: HTTP 500 if any Item failed to update, else 200.

**Checkpoint**: The T002 tests pass. US1 is delivered.

---

## Phase 4: User Story 2 — A fully successful update still reports success (Priority: P1)

**Goal**: A `/plaid-update` request in which every Item succeeds, or there are no Items, still returns HTTP 200 with an unchanged body in all three formats.

**Independent Test**: The US2 unit tests below pass.

### Tests for User Story 2

- [ ] T004 [US2] In `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py`, class `TestPlaidUpdate`:
  - Change `test_update_json`, which is all-successful, to assert `res == (mock_json, 200)`.
  - Add `test_update_template_all_success`: default `Accept`, all results successful. Assert `res == (rendered, 200)` and `render_template` called with `num_failed=0`.
  - Add `test_update_plain_all_success`: `text/plain`, all results successful. Assert status 200 and a body ending `0 account(s) failed`.
  - Add `test_update_no_items`: `update()` returns `[]`. Assert status 200 for the JSON format, with `jsonify([])`.

### Implementation for User Story 2

- [ ] T005 [US2] No further code beyond T003, since `all([])` is `True` and so gives 200. Confirm the T004 tests pass against the T003 change, and fix T003 if they don't.

**Checkpoint**: Both stories pass.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T006 [P] In `biweeklybudget/flaskapp/views/plaid.py`, extend the `PlaidUpdate` class docstring's response-format list with the status rule: HTTP 200 when every Item updated successfully, HTTP 500 when one or more failed. The body is the same in both cases.
- [ ] T007 [P] In `docs/source/plaid.rst`, section "Updating Transactions via API", add a paragraph stating the status codes (200 all succeeded; 500 one or more Items failed, with the body still reporting every Item; 400 for a POST missing `item_ids`) and noting that `curl --fail` can therefore detect failed updates.
- [ ] T008 [P] In `docs/source/http_api.rst`, add the status-code rule to the one-paragraph `/plaid-update` summary (line ~804).
- [ ] T009 [P] In `CHANGES.rst`, add one concise bullet at the top of the `Unreleased` section, led by the `Issue #261` link. It says that `/plaid-update` now returns HTTP 500 when any Plaid Item fails to update (all response formats; body unchanged), with a short sub-bullet warning API callers that previously saw 200 on partial failure. Do not touch `biweeklybudget/version.py`.
- [ ] T010 Run the Test Gate (Constitution II) to completion, redirecting output to scratchpad files:
  - `tox -e py314`, which also covers pycodestyle and pyflakes.
  - `tox -e acceptance`.
  - `tox -e docs`.

  Raise the timeouts and re-run if a suite times out, rather than narrowing it. `migrations`, `docker`, and `plaid` are not engaged by this change and run in CI.
- [ ] T011 Record results in the spec artifacts: in `spec.md`, set Status to Complete, mark the tasks here done, and note the Test Gate results in `plan.md`. Commit with the prefix `Plaid Update Failure Status - M1.x`.
- [ ] T012 Push the branch to `origin`, open the pull request (following `.github/PULL_REQUEST_TEMPLATE.md`, and surfacing research R1/R2's choices for the maintainer), then monitor CI and answer reviews.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)** blocks everything that runs tests.
- **US1**: T002 (tests, failing) → T003 (implementation) → T002 tests pass.
- **US2**: T004 depends on T003 only in that its tests pass once T003 is in. It may be written alongside T002, but both edit the same test file, so they're done sequentially. T005 is verification.
- **Polish**: T006–T009 touch different files and can be done in parallel once T003 is done. T010 depends on all of T002–T009. T011 depends on T010. T012 depends on T011.

### User Story Dependencies

- US1 and US2 share T003. US2 needs no code of its own but is independently testable through its own test cases.

### Parallel Opportunities

- T006, T007, T008, T009 (four different files).
- Within T010, the `py314`, `acceptance`, and `docs` tox environments can run concurrently if the database container can serve both the unit and acceptance suites. Otherwise run them sequentially, since both suites reload the test database.

---

## Parallel Example: Polish

```bash
Task: "Extend the PlaidUpdate class docstring in biweeklybudget/flaskapp/views/plaid.py"
Task: "Document status codes in docs/source/plaid.rst"
Task: "Document status codes in docs/source/http_api.rst"
Task: "Add Unreleased entry to CHANGES.rst"
```

---

## Implementation Strategy

### MVP First

T001 → T002 → T003 is the MVP: failures are detectable. T004–T005 lock in that success is
still 200, and T006–T012 document, verify, and deliver. At this size all of it ships
together as milestone M1 in one pull request.

---

## Notes

- Bodies must not change (FR-004). Every changed assertion compares against the same body object or string as before, so a body regression fails the test.
- Unit tests need the MariaDB container (see `CLAUDE.md`). Without it, `test_plaid.py` and `test_utils.py` fail to collect.
