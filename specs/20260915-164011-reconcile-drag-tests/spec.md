# Feature Specification: Restore Skipped Reconcile Drag-and-Drop Acceptance Tests

**Feature Branch**: `robot-army/issue-267-fix-reconcile-acceptance-tests-that`

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "jantman/biweeklybudget issue #267 — "Fix reconcile acceptance tests that were removed (broken)": See commits 1936e64a90904e0cbe5ca43c58eb096a87e103d2 and 91d737dfb30a5784bd42d5bf293ff9ae055b9eba."

## Background

On 2022-10-22 two acceptance test classes for the Reconcile page were switched off
with a blanket skip marker, because their second drag-and-drop in a test always failed
with "element not interactable: [object HTMLDivElement] has no size and location":

- `TestDragAndDropReconcile` (commit 1936e64): drags five OFX transactions onto their
  matching Transactions, submits, and checks that submitting with nothing reconciled
  warns instead of posting.
- `TestUIReconcileMulti` (commit 91d737d): reconciles one pair, submits, then reconciles
  two more pairs and submits again. It also checks that an invalid Transaction ID in the
  page's reconcile state produces a 400 error message.

These are the only acceptance tests that cover the Reconcile page's main workflow:
reconciling several pairs by drag-and-drop in one visit and submitting them. Since they
were skipped, nothing has exercised that workflow, including the error path for an
invalid Transaction ID. The block comments left in the test file record the symptom but
no cause.

## User Scenarios & Testing *(mandatory)*

The "users" here are the maintainer and CI. The value is regression protection for the
reconcile workflow, which is how every downloaded transaction gets matched to the
budget.

### User Story 1 - Multi-pair drag-and-drop reconcile is tested again (Priority: P1)

The maintainer runs the acceptance suite. The two skipped classes run and pass. They
drag several OFX transactions onto their matching Transactions in one page visit, submit
the batch, and check the success message, the page's cleared reconcile state and what
was saved.

**Why this priority**: this is the whole of the issue. The reconcile page's main
workflow currently has no acceptance coverage.

**Independent Test**: run the acceptance suite for these two classes and see every test
in them run (none skipped) and pass.

**Acceptance Scenarios**:

1. **Given** the reconcile fixture data (seven unreconciled OFX transactions, six
   unreconciled Transactions, one already-reconciled pair), **When** the test drags
   five OFX transactions onto their five matching Transactions in one visit and submits,
   **Then** the page reports "Successfully reconciled 5 transactions", its reconcile
   state is empty, and the matching reconcile records are stored.
2. **Given** a fresh copy of that fixture data, **When** the test reconciles one pair
   and submits, then reconciles two more pairs on the refreshed page and submits again,
   **Then** each submit reports the right count ("1", then "2") and clears the page's
   reconcile state.
3. **Given** nothing has been reconciled, **When** the user presses submit, **Then** the
   page warns "No reconciled transactions; did not submit form." and neither column
   changes.
4. **Given** the page's reconcile state holds an invalid Transaction ID, **When** the
   user submits, **Then** the page shows "Error 400: Invalid Transaction ID: 1234" and
   keeps that state.

---

### User Story 2 - The cause is understood and recorded (Priority: P2)

A future maintainer reading these tests sees why the second drag used to fail and why
the tests now pass. They are not left with the 2022 note, which says the cause was
unknown and blames the browser version.

**Why this priority**: without the cause, the same mistake is easy to make again in a
new drag-and-drop test and just as hard to diagnose.

**Independent Test**: read the tests and the feature's research notes. The cause is
stated, and the old "skipped, revisit later" comments are gone.

**Acceptance Scenarios**:

1. **Given** the restored tests, **When** a maintainer reads them, **Then** there is no
   leftover skip marker, stale "can't get it working" comment or debugging scaffold.

---

### Edge Cases

- A test that performs several drags in one visit must not replay an earlier drag. Once
  an OFX transaction has been dropped, its original card is hidden, so a replayed drag
  targets an element with no size.
- The dropped OFX transaction must be accepted only by the Transaction with the same
  account and amount. Tests must use matching pairs; mismatches are already covered by
  `TestDragLimitations`.
- The page loads both columns asynchronously. A drag must not start until the element
  it targets exists.
- These classes refresh the database per class, so they must not depend on state left
  by other classes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `TestDragAndDropReconcile` and `TestUIReconcileMulti` MUST run as part of
  the acceptance suite. The blanket skip markers MUST be removed, with no replacement
  skip or expected-failure marker.
- **FR-002**: Every test in the two classes MUST pass in a local acceptance run and in
  CI. That covers both CI jobs that run the acceptance suite: `acceptance`, and `docker`
  against the built image.
- **FR-003**: The tests MUST keep their original assertions about the outcome: the
  reconciled pairs, success, warning and error messages and their alert styles, and the
  stored reconcile records. Weakening an assertion to make a test pass is not
  acceptable.
- **FR-004**: The 2022 "skipped, revisit later" comments and the leftover
  debugging scaffold (the extra wait, sleep and hover on `trans-1` in
  `TestDragAndDropReconcile.test_07_drag_and_drop`) MUST be removed.
- **FR-005**: The root cause of the "has no size and location" failure MUST be recorded
  in the feature's research notes. A short comment MUST sit where a future test writer
  would repeat the mistake.
- **FR-006**: The application's behaviour MUST NOT change. If investigation shows the
  Reconcile page itself is at fault, stop and escalate rather than change it silently.

### Key Entities

- **Reconcile page state**: the page-side mapping of Transaction ID to OFX transaction
  (account and FITID) that the submit button posts. Tests read it after each drag.
- **Reconcile record**: the stored link between a Transaction and an OFX transaction,
  created on submit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The acceptance suite's skip count drops by the 18 tests in these two
  classes (9 each: 6 shared fixture-loading steps plus 3 of its own), and all 18 pass.
- **SC-002**: The two classes pass on 5 consecutive isolated local runs. This guards
  against swapping a deterministic failure for a flaky one.
- **SC-003**: The complete unit and acceptance suites pass locally, and every CI check on
  the pull request passes.

## Side Quest: Plaid Update Check/Uncheck All race (recorded 2026-09-15)

Recorded under constitution Principle V, before any work on it began.

- **Where the work departed**: at T011, the complete acceptance run (constitution
  Principle II). Two full local runs on this branch failed only in
  `test_plaid.py::TestPlaidUpdateView`:
  - run 1: `test_6_uncheck_all`;
  - run 2: `test_6_uncheck_all` and `test_8_check_all`.
- **Not caused by this feature**: those tests run before any reconcile test in the
  suite, and every module before them is unchanged from `master`. The class passes
  3/3 when run on its own.
- **Why it can't be left alone**: Principle II does not allow a feature to be declared
  done while a suite fails, and it forbids narrowing the run or marking failures as
  expected.
- **Cause** (see [research.md](research.md) R5): the Check All / Uncheck All links are
  `javascript:` hrefs. The browser runs a `javascript:` URL as a queued task, not
  inside the click, and the tests check the checkboxes straight after clicking.
- **Change**: test-only. After clicking either link, wait until every Item checkbox
  reaches the expected state, then make the original assertions unchanged. No
  application change, no weakened assertion.
- **To resume the main feature**: after the fix, re-run
  `TestPlaidUpdateView` in isolation, then the complete acceptance suite (T011), then
  continue at T012.

## Assumptions

- The Reconcile page's drag-and-drop works for real users. It is the maintainer's
  day-to-day workflow and nobody has reported it broken, so a failure that only hits
  the second drag in a test points at the test harness, not the page.
- The pinned browser-automation library version stays as it is. Fixing the tests must
  not need a dependency change.
- CHANGES.rst gets a one-line entry under `Unreleased`, per the constitution, even
  though users see no change. There is no documentation page for these tests, so no
  other docs change is needed.
- Other known flaky reconcile tests (e.g. `test_11_unreconcile`,
  `test_36_ignore_and_unignore_ofx`) are out of scope unless the same root cause turns
  out to affect them.
