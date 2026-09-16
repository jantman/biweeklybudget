---

description: "Task list for Plaid Item Last Successful Update Time (issue #268)"
---

# Tasks: Plaid Item Last Successful Update Time

**Input**: Design documents from `specs/20260915-194912-plaid-last-successful-update/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/plaid-items-table.md](./contracts/plaid-items-table.md),
[quickstart.md](./quickstart.md)

**Tests**: Included, and not optional here. Constitution Principle II requires new code to be
covered by valid tests, and Principle III requires both migration directions to be tested
before commit.

**Organization**: Phases map onto the milestones in `plan.md`. Commit messages use the
prefix `Plaid Last Successful Update - M{milestone}.{task}` per Constitution Workflow step 4.
Human approval is required to advance from one milestone to the next (Principle I).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task serves (US1, US2, US3)
- Paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Make the environment able to run and verify the change. No source edits.

- [X] T001 Start the MariaDB test container and export the test-database environment described in `CLAUDE.md`, then run `python dev/setup_test_db.py` and `initdb` to bring the test database to the current Alembic head (`c5e3a9b1d7f2`) before any model change
- [X] T002 Confirm the tox runner works from this worktree by running `tox -e py314 -- biweeklybudget/tests/unit/test_plaid_updater.py` from the main checkout's venv, redirecting output to the scratchpad per `CLAUDE.md`; this is the pre-change baseline

**Checkpoint**: Test database at head, unit suite runnable, baseline result recorded.

---

## Phase 2: Foundational — schema (Milestone M1, part 1)

**Purpose**: The column must exist before anything can write to or read from it. This phase
delivers User Story 3 (safe upgrade/downgrade) and unblocks US1 and US2.

**⚠️ BLOCKING**: T003–T006 must complete before Phase 3 or Phase 4 begins.

- [X] T003 [US3] Add the `last_successful_update` column to `PlaidItem` in `biweeklybudget/models/plaid_items.py` — `Column(UtcDateTime)`, nullable, placed after `last_updated`, with a `#:` docstring comment in the style of the neighbouring columns saying it is the time Plaid last successfully updated this Item's transactions (per [data-model.md](./data-model.md))
- [X] T004 [US3] Hand-write the Alembic revision `biweeklybudget/alembic/versions/<rev>_add_plaid_item_last_successful_update.py` with `down_revision = 'c5e3a9b1d7f2'`, an `upgrade()` that adds `sa.Column('last_successful_update', UtcDateTime(timezone=True), nullable=True)` to `plaid_items`, and a `downgrade()` that drops it — matching the form used for `last_updated` in `f5a002127934_plaid_models.py`, and carrying the standard AGPL header if the file template lacks one
- [X] T005 [US3] Test both migration directions against the test database: `upgrade head`, verify the column and that existing `plaid_items` rows survive, `downgrade -1`, verify the column is gone and rows survive, then `upgrade head` again (per [quickstart.md](./quickstart.md))
- [X] T005a [US3] Add a per-migration roundtrip test `biweeklybudget/tests/migrations/test_migration_3f7c2a91e04b.py` subclassing `MigrationTest`, in the style of `test_migration_c5e3a9b1d7f2.py` — insert a `plaid_items` row before the migration, assert the column is absent before and after the reverse, present and null (with the existing row data intact) after the forward migration, and that it accepts a value. *(Added during implementation: the repository keeps one of these per recent revision, and Principle II requires new code to be covered.)*
- [X] T006 [US3] Run `tox -e migrations` to confirm the migration head matches the models, redirecting output to the scratchpad

**Checkpoint**: The column exists, the migration is reversible and verified, and User Story 3
is satisfied and independently tested.

---

## Phase 3: User Story 2 — record the value (Priority: P1, Milestone M1, part 2)

**Goal**: Whenever the application asks Plaid about an Item, the last-successful-update time
Plaid reports is stored against that Item.

**Independent Test**: Run a transaction update and an Item-information refresh against a Plaid
response carrying a known time, and confirm the time is stored on the Item. Nothing needs to
display it yet.

### Implementation for User Story 2

- [X] T007 [US2] Add `plaid_last_successful_update(item_get_response)` to `biweeklybudget/utils.py` implementing contract C2 in [contracts/plaid-items-table.md](./contracts/plaid-items-table.md): chained `.get()` with `or {}` coercion at each level, returning `None` for any absent/None/empty level, and attaching UTC to a naive datetime; include a full docstring in the file's existing style
- [X] T008 [US2] In `PlaidUpdater._do_item` (`biweeklybudget/plaid_updater.py`), assign `item.last_successful_update = plaid_last_successful_update(iteminfo)` alongside the existing `item.last_updated = dtnow()`, keeping the existing transactions-status log line, and import the helper
- [X] T009 [P] [US2] In `PlaidUpdateItemInfo.post` (`biweeklybudget/flaskapp/views/plaid.py`), assign `item.last_successful_update = plaid_last_successful_update(response)` alongside the existing `institution_id`/`institution_name` assignments, before the existing `db_session.add(item)`, and import the helper

### Tests for User Story 2

- [X] T010 [P] [US2] Add unit tests for the helper in `biweeklybudget/tests/unit/test_utils.py` covering every row of contract C2's behaviour table: aware datetime passed through, naive datetime returned UTC-aware, `last_successful_update` absent, `transactions` absent/None/empty, `status` absent/None/empty
- [X] T011 [US2] Update `TestDoItem`'s three tests in `biweeklybudget/tests/unit/test_plaid_updater.py` — put a known `last_successful_update` into the `item_get` stub's `status.transactions`, assert `mock_item.last_successful_update`, and keep the strict `db_session.mock_calls` assertions correct
- [X] T012 [P] [US2] Update `TestPlaidUpdateItemInfo` in `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` — add `status.transactions.last_successful_update` to the `item_get` stubs (including one Item where it is absent) and assert the resulting attribute on each mock Item
- [X] T013 [US2] Run `tox -e py314` to completion and confirm it passes, redirecting output to the scratchpad

**Checkpoint**: The value is recorded by both writers, covered by unit tests, and User Story 2
is independently verified. **Milestone M1 complete — pause for approval.**

---

## Phase 4: User Story 1 — show the value (Priority: P1, Milestone M2)

**Goal**: The Plaid Items table shows each Item's last successful update time beside "Last
Polled", with an unambiguous placeholder when none is recorded.

**Independent Test**: With sample data holding one Item that has a recorded time and one that
does not, load `/plaid-update` and confirm each row renders the expected cell in the new
column.

### Implementation for User Story 1

- [X] T014 [US1] Add the "Last Successful Update" column to the Plaid Items table in `biweeklybudget/flaskapp/templates/plaid_form.html` — a `<th>` immediately after "Last Polled" and a `<td>` rendering `{{ i.last_successful_update|ago }}` when set and the literal `unknown` when not, per contract C1
- [X] T015 [P] [US1] In `biweeklybudget/tests/fixtures/sampledata.py::_plaid_items`, give `PlaidItem1` a `last_successful_update` of `self.dt - timedelta(days=3)` and leave `PlaidItem2`'s unset, so the acceptance suite covers both the rendered value and the placeholder (per [research.md](./research.md) R7)

### Tests for User Story 1

- [X] T016 [US1] Update `test_4_table` in `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py` for the new column: `PlaidItem1`'s row gains `3 days ago` and `PlaidItem2`'s gains `unknown`, both between the existing `now` and `Update / Fix Item` cells
- [ ] T017 [US1] Run `tox -e acceptance` to completion and confirm it passes, re-running any known-flaky failure (reconcile drag/unignore, fuel-log search, Plaid "Uncheck All") in isolation before attributing it to this change; redirect output to the scratchpad

**Checkpoint**: The column renders both cases, the acceptance suite passes, and User Story 1
is independently verified. **Milestone M2 complete — pause for approval.**

---

## Phase 5: Gate, document, deliver (Milestone M3)

**Purpose**: Constitution Principles II, IV and VI, and delivery.

### Test gate (Principle II)

- [X] T018 Run `tox -e py314` and `tox -e acceptance` to completion on the finished change and confirm both pass, redirecting output to the scratchpad; raise the timeout and re-run rather than reporting any timed-out suite
- [X] T019 Run `tox -e migrations` on the finished change and confirm it passes
- [~] T020 Run `tox -e docker` and confirm it passes — required because this change touches schema; ensure the main venv's `bin` is first on `PATH` and that no other acceptance run overlaps it. **Attempted three times and killed by the host for low memory each time; deferred to the CI docker job.** See the results table below

### Documentation (Principle IV)

- [X] T021 Run `tox -e screenshots` to regenerate `docs/source/plaid-update.png` and `docs/source/plaid-update_sm.png`, and commit both; do **not** run `tox -e docs` in the same invocation or afterwards until the PNGs are committed
- [X] T022 [P] Extend the "Plaid Update" caption to name what distinguishes the two time columns (when the application last polled the Item, versus when Plaid last successfully refreshed it). *Corrected during implementation:* `docs/source/screenshots.rst` is **generated** by `docs/make_screenshots.py` (`make_rst()` deletes and rewrites it from each screenshot's `description`), so the caption is edited there and reaches the page via T021's regeneration; editing the `.rst` directly would be silently discarded
- [X] T023 Run `tox -e docs` and confirm it builds clean, re-running on a transient linkcheck timeout

### Changelog and spec artifacts (Principles VI and I)

- [X] T024 [P] Add a concise `CHANGES.rst` bullet under `Unreleased` (creating the heading if absent) led by the issue #268 link, stating the new column in the Plaid Items table and noting the database migration; do **not** touch `biweeklybudget/version.py`
- [X] T025 Mark this `tasks.md` complete and set `spec.md`'s **Status** to Complete, recording the test-gate results

### Delivery

- [ ] T026 Commit the whole of M3 together, push the branch to `origin` with `git push -u origin HEAD:refs/heads/robot-army/issue-268-plaid-show-last-successful-update-time` (the branch's upstream is `origin/master`, so a bare `git push` would target master), and open a pull request describing the change
- [ ] T027 Monitor the CI jobs on the pull request to completion, then run `/answer-reviews` and repeat until Claude's review reports "No issues found" and Copilot's review, if present, recommends approval

**Checkpoint**: Feature complete, gated, documented, and delivered.

### Test gate results (2026-09-15)

| Suite | Result |
|-------|--------|
| `tox -e py314` (unit) | **825 passed, 147 skipped, 0 failed.** The skips are pytest-pycodestyle's "previously passed" cache for files unchanged since the earlier full run in this session, which reported 968 passed / 4 skipped; every file this change touches was re-checked. |
| `tox -e acceptance` | **900 passed, 0 failed** in 23m45s. `TestPlaidUpdateView::test_4_table` passed with the new column asserted in both the value and the placeholder case. No flaky failures occurred, so no re-runs were needed. |
| `tox -e migrations` | **10 passed**, including the new `test_migration_3f7c2a91e04b` roundtrip. Both directions were additionally exercised by hand against the test database with an existing `plaid_items` row intact throughout. |
| `tox -e docs` | **build succeeded** (exit 0). One new warning, an unresolvable cross-reference to the external `plaid.model.item_get_response.ItemGetResponse`, of exactly the same kind as the pre-existing `plaid.api.plaid_api.PlaidApi` warning beside it; neither is fatal and neither is new in kind. |
| `tox -e screenshots` | Regenerated. The first attempt was killed by the system for low memory part-way through; because the script deletes every PNG before regenerating, that left all 49 missing, and they were restored with `git checkout -- docs/source/`. The retry succeeded. Only the two `plaid-update` PNGs are committed — see [research.md](./research.md) R8 on the unrelated drift the regeneration exposed. |
| `tox -e docker` | **Not completed locally — deferred to CI.** Attempted three times (full run twice, then with `TEST_DOCKER=false` to isolate the build); the host killed each one for low memory. The host's swap was fully exhausted by unrelated workloads throughout, and the same pressure had already killed a `screenshots` run. The second attempt did get far enough to **build the image successfully** (`jantman/biweeklybudget:5783bf46-dirty_...` was tagged) before being killed during the container-acceptance phase, so the failure is environmental and not a property of this change. Every container and image those runs left behind was removed. The repository's CI runs the `docker` job on the pull request, and that run is the gate. |

**Outstanding**: `tox -e docker` per the row above. Constitution Principle II requires the
Docker suite to pass for a schema change; it must be green in CI before this is merged, and
it was not possible to demonstrate that on this host.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies. T001 must run before any model change, or Alembic
  autogenerate — if it were ever used here — would see no diff.
- **Phase 2 (Foundational / US3)**: depends on Phase 1. **Blocks Phases 3 and 4.**
- **Phase 3 (US2)**: depends on Phase 2. Does not depend on Phase 4.
- **Phase 4 (US1)**: depends on Phase 2 only. It reads the column; it does not need the
  writers, because the acceptance fixtures populate the column directly.
- **Phase 5**: depends on Phases 3 and 4 both being complete.

### User story dependencies

- **US3 (P2, safe upgrade)**: the schema itself — first, because both other stories need the
  column to exist.
- **US2 (P1, record the value)**: after US3. Independently testable through the unit suite.
- **US1 (P1, show the value)**: after US3, independently of US2. Independently testable
  through the acceptance suite against fixture data.

The spec's priorities put US1 and US2 level at P1 and US3 at P2, but US3's schema is a
mechanical prerequisite for both, so it is implemented first regardless of priority. Neither
P1 story is useful without the other in production: US2 with no US1 stores a value nobody can
see, and US1 with no US2 shows a column that never fills.

### Parallel opportunities

This is a small, mostly sequential change and parallelism is not where its risk lies. The
genuinely independent tasks are marked `[P]`:

- T009 (the view writer) is independent of T008 (the updater writer) — different files, both
  depending only on T007.
- T010 and T012 touch different test files and can be written alongside T011.
- T015 (fixtures) is independent of T014 (template).
- T022 (caption) and T024 (changelog) touch unrelated files.

Within a milestone, source and its tests are best written together rather than in parallel by
different hands: the strict `mock_calls` assertions in this repository's unit tests make the
test and the code it covers one unit of work.

---

## Implementation Strategy

### Milestone-by-milestone, with approval between

1. **Phase 1 + Phase 2 (M1 part 1)** — the column and its reversible migration. Verifiable on
   its own: `tox -e migrations` passes and both directions have been exercised by hand.
2. **Phase 3 (M1 part 2)** — recording. Verifiable on its own: `tox -e py314` passes and the
   value lands on the Item. **Stop; M1 complete; approval required before M2.**
3. **Phase 4 (M2)** — display. Verifiable on its own: `tox -e acceptance` passes with both the
   value and the placeholder asserted. **Stop; M2 complete; approval required before M3.**
4. **Phase 5 (M3)** — the full gate, documentation, changelog, PR, CI, reviews.

### Notes

- Commit after each milestone at minimum, with the prefix
  `Plaid Last Successful Update - M{milestone}.{task}`.
- Redirect every tox run's output to the scratchpad rather than piping to `tail`, so the full
  output can be examined (`CLAUDE.md`).
- `TestDoItem`'s three tests fail when `test_plaid_updater.py` is run entirely on its own; run
  the file with the rest of the suite before treating that as a regression.
- Any deviation from this plan is recorded in `spec.md` as a side quest and committed before
  the deviation begins (Principle V).
