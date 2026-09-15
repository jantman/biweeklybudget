# Implementation Plan: Restore Skipped Reconcile Drag-and-Drop Acceptance Tests

**Branch**: `robot-army/issue-267-fix-reconcile-acceptance-tests-that` | **Date**: 2026-09-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/20260915-164011-reconcile-drag-tests/spec.md`

## Summary

Re-enable `TestDragAndDropReconcile` and `TestUIReconcileMulti` in
`biweeklybudget/tests/acceptance/flaskapp/views/test_reconcile.py`. They were skipped on
2022-10-22 because every second drag in a test failed with "has no size and location".

Research ([research.md](research.md) R1) found the cause. Selenium 3.141.0, pinned
then, did not clear an `ActionChains` queue after `perform()`. The tests reused one
chain, so each later `perform()` replayed the earlier drags, including the first one,
against an OFX card the first drop had hidden. Selenium 4.2+ clears the queue, and with
the skip markers removed both classes already pass on today's pinned Selenium 4.48.0.

The work therefore:

- removes the skip markers, the stale 2022 comments and the debugging scaffold;
- routes every drag in the two classes through one `ReconcileHelper` helper, which
  builds a fresh chain per drag and first waits for both elements to be present. A
  short comment on the helper records the cause (R2, R3);
- leaves every assertion unchanged;
- proves stability with five consecutive isolated runs, then the full unit and
  acceptance suites.

No application code changes.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: pytest, selenium 4.48.0, pytest-selenium 4.1.0 (all already
pinned in `tox.ini`; none change). Chromium/ChromeDriver 152 locally; CI uses its own
Chrome.

**Storage**: MariaDB 10.4 test database (dropped and reloaded by the acceptance fixtures).

**Testing**: `tox -e acceptance` (and `-e py314` for the unit suite and style checks)

**Target Platform**: Linux, headless Chrome

**Project Type**: web application (Flask + jQuery UI). This change touches the
acceptance test suite only.

**Performance Goals**: N/A. The two classes add about 70 s to the acceptance run.

**Constraints**: FR-003 (assertions unchanged); FR-006 (no application change; escalate
if the page turns out to be at fault)

**Scale/Scope**: one test module, one new helper method, one changelog line

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
|-----------|------------|--------|
| I. Spec-Driven Change | Spec, plan and tasks under `specs/20260915-164011-reconcile-drag-tests/`, on the session's feature branch. One milestone (M1); there is no milestone boundary to approve inside it. | PASS |
| II. The Test Gate | The complete unit (`py314`, which includes pycodestyle/pyflakes) and acceptance suites run to completion and pass before the PR. The two restored classes also pass 5 consecutive isolated runs. Nothing is marked skip or xfail; this change *removes* two skips. The helper is exercised by the 6 restored tests, which assert real outcomes (reconciled state, messages, DB rows). | PASS |
| III. Reversible Migrations | No model or schema change. | N/A |
| IV. Documentation | No user-facing behaviour or doc page changes. `docs/source/development.rst` does not describe individual tests. The explanation of the cause lives in the helper's comment and `research.md`. The `docs` build is unaffected, but still runs in CI. | PASS |
| V. Escalate Instead Of Guessing | The root cause is established from library source, not guessed (R1). FR-006 names the escalation trigger. No side quests. | PASS |
| VI. Changelog; Release Only On Request | One concise `Unreleased` entry in `CHANGES.rst`. `version.py` is untouched; no tag. | PASS |
| Constraints: test data safety | The acceptance runs use a throwaway MariaDB container (`budgettest267`, port 13367), never a real database. | PASS |
| Constraints: stack / security / secrets | No new dependency, frontend code, credential or exposure. | PASS |

**Post-design re-check**: unchanged. The design adds one test helper and nothing
outside the test module and changelog. No violations, so Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/20260915-164011-reconcile-drag-tests/
├── plan.md              # This file
├── research.md          # Root cause (R1), design decisions (R2-R4)
├── data-model.md        # States the page/DB entities the tests check (no changes)
├── quickstart.md        # How to validate
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # /speckit-tasks output
```

No `contracts/`: the change exposes no interface.

### Source Code (repository root)

```text
biweeklybudget/tests/acceptance/flaskapp/views/test_reconcile.py
    ReconcileHelper.drag_ofx_to_trans()   # new: fresh chain per drag, waits for both ends
    TestDragAndDropReconcile              # skip + 2022 comment + debug scaffold removed; uses helper
    TestUIReconcileMulti                  # skip + 2022 docstring removed; uses helper
CHANGES.rst                               # Unreleased entry
biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py
    TestPlaidUpdateView.click_set_all()   # side quest: wait for Check/Uncheck All to apply
```

The `test_plaid.py` change is a side quest, added after planning when the
complete acceptance run (T011) failed twice there for reasons unrelated to this
feature. It is recorded in [spec.md](spec.md) ("Side Quest"), with the cause in
[research.md](research.md) R5.

**Structure Decision**: the existing single-project layout; all changes are in the one
acceptance test module plus the changelog.

## Design

- **`ReconcileHelper.drag_ofx_to_trans(selenium, ofx_id, trans_id)`**
  - Waits (`wait_for_id`) for the OFX element `ofx_id` and the Transaction element
    `trans-<trans_id>` to be present.
  - Drags the OFX element onto that Transaction's `.reconcile-drop-target` using a new
    `ActionChains(selenium)`, exactly the source/target pair the old inline code used.
  - Its docstring says each drag gets its own chain because a reused chain replayed
    earlier drags on Selenium < 4.2 (the cause of the 2022 skip). It must not be
    reused for several drags.
- **`TestDragAndDropReconcile.test_07_drag_and_drop`**: the five drags become five
  helper calls in the original order and pairs (OFX3→3, OFX1→1, OFX2→2, OFXT6→5,
  OFXT7→6). The block comment and the `# DEBUG` … `# END DEBUG` scaffold are deleted.
  The assertions are unchanged.
- **`TestUIReconcileMulti`**: the class docstring (the 2022 note) is removed. In
  `test_07_drag_and_drop` the three drags become helper calls. The existing
  `wait_for_id(selenium, 'ofx-1-OFX2')` and all assertions are unchanged.
- `TestDragLimitations` and other single-drag tests are **not** changed (R2).
- **Imports**: `WebDriverWait`, `EC` and `sleep` stay in use elsewhere in the module.
  Pyflakes in the `py314` run confirms nothing is left unused.

## Milestones

- **M1 - Restore the tests**: the helper, the un-skip and cleanup, the changelog, the
  local stability runs and the full suites, then commit, push and open the PR. CI is
  monitored and reviews are answered until clean.

## Complexity Tracking

No violations.
