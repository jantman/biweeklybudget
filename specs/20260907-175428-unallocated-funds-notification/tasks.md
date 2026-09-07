---

description: "Task list for the unallocated-funds notification fix (GitHub issue #320)"
---

# Tasks: Correct the Unallocated-Funds Notification

**Input**: Design documents from `specs/20260907-175428-unallocated-funds-notification/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/notification-content.md](./contracts/notification-content.md), [quickstart.md](./quickstart.md)

**Tests**: REQUIRED, not optional. Constitution principle II (The Test Gate) is
NON-NEGOTIABLE, and the Technology & Security Constraints require that changes to
budget arithmetic ship with tests pinning the expected numbers. Test tasks below
are therefore first-class deliverables, not an optional extra.

**Organization**: Phases map one-to-one onto the four milestones in
[plan.md](./plan.md). Human approval is required to advance between milestones
(Constitution principle I). Each task carries the commit prefix to use, in the
constitution's required form `Unallocated Funds Notification - M{milestone}.{task}`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: `[US1]`, `[US2]`, `[US3]` per the user stories in [spec.md](./spec.md)
- Every task names its exact file path

## Path Conventions

Single-project layout, unchanged: application code in `biweeklybudget/`, tests in
`biweeklybudget/tests/`, docs in `docs/source/`.

---

## Phase 1: Setup & Baseline

**Purpose**: Get a working test environment and a recorded pre-change baseline, so
every later number can be shown to have moved for the right reason.

- [X] T001 Start the MariaDB test container and export the test-database environment variables per `CLAUDE.md`, then run `python dev/setup_test_db.py` and `initdb` from the activated venv. No commit.
- [X] T002 Run the unit suite unchanged and save the output to the scratchpad: `tox -e py314 > <scratchpad>/baseline-unit.txt 2>&1`. Confirm it passes before any edit, so later failures are attributable to this feature. No commit.
- [X] T003 Record, in `<scratchpad>/baseline-figures.txt`, the current expected values asserted by `biweeklybudget/tests/acceptance/flaskapp/views/test_base_template.py` (`acct_bal` 12889.24, `stand_bal` 132939.07, `pp_bal` 11.76, `unrec_amt` -333.33) and the two active credit-account ledger balances from `biweeklybudget/tests/fixtures/sampledata.py` (CreditOne latest -952.06, CreditTwo -5498.65). No commit.

**Checkpoint**: Environment works, suite is green, baseline recorded.

---

## Phase 2: Foundational

**Purpose**: Confirm the prerequisites this feature consumes rather than builds.

There is deliberately **no** foundational construction work. Per
[plan.md](./plan.md) Constitution Check principle III, no model, schema or
migration change is involved, and no new module or package is created. The two
capabilities this feature depends on already exist and are reused as-is.

- [X] T004 Re-confirm against the working tree, and note the result in [research.md](./research.md) if it differs from R2/R4: that `Account.active_credit_accounts()` (`biweeklybudget/models/account.py`) filters on `AcctType.Credit` **and** `is_active`, and that `Account.unreconciled_sum()` skips `Transaction.is_excluded_from_budget`. If either is not as recorded, STOP and escalate (Constitution principle V) — the plan's scoping of defect #2 depends on it. No commit unless research.md changes.

**Checkpoint**: Prerequisites verified. User story work can begin.

---

## Phase 3: User Story 1 — The banner accounts for money owed on credit accounts (Priority: P1) 🎯 MVP

**Milestone**: M1 (the figure) — the arithmetic lands and is provable on its own.

**Goal**: A `credit_account_sum()` figure that correctly reflects money owed on
active credit accounts, with the sign convention pinned by tests.

**Independent Test**: With funding accounts at a known balance and credit accounts
at a known amount owed, the new figure is negative by exactly the amount owed;
inactive credit accounts, non-credit accounts, and accounts with no recorded
balance contribute nothing.

### Tests for User Story 1

> Write these first and confirm they fail against the unmodified controller.

- [X] T005 [US1] Add a `TestCreditAccountSum` class to `biweeklybudget/tests/unit/flaskapp/test_notifications.py` covering, with a mocked session: (a) one active credit account owing money reduces the figure by exactly that amount, asserted as a **signed** `Decimal` — not merely "smaller"; (b) two credit accounts sum; (c) delegation to ``Account.active_credit_accounts()`` with the given session, which is where the active/credit filtering lives -- **note**: asserting the inactive-account and non-credit-account exclusions here by mocking that helper would be a tautology, so FR-002 is covered for real against the database in T014a instead; (e) an account whose `balance` is `None` contributes zero without raising; (f) an account whose `balance.ledger` is `None` contributes zero without raising; (g) **an overpaid card with a positive ledger increases the figure** — this is the case an `abs()`-based implementation fails, per [research.md](./research.md) R1. Commit prefix: `Unallocated Funds Notification - M1.1`.

### Implementation for User Story 1

- [X] T006 [US1] Add the `credit_account_sum(sess=None)` static to `NotificationsController` in `biweeklybudget/flaskapp/notifications.py`, immediately after `budget_account_sum()`. Mirror that method's shape: `sess` defaulting to `db_session`, a `Decimal('0.0')` accumulator, iteration in Python. Source accounts from `Account.active_credit_accounts(sess)`; skip any account where `acct.balance is None` or `acct.balance.ledger is None`; add `acct.balance.ledger` **with its own sign** — never `abs()`, never negated. Docstring must state the sign convention (negative when owed) and cite issue #320, so the next reader does not "fix" the sign. Commit prefix: `Unallocated Funds Notification - M1.2`.
- [X] T007 [US1] Run `tox -e py314 > <scratchpad>/m1-unit.txt 2>&1` and confirm the new tests pass and nothing regressed. Fix any pycodestyle/pyflakes failure. Commit prefix: `Unallocated Funds Notification - M1.3`.
- [X] T008 [US1] Update the Milestone section of [plan.md](./plan.md) to record M1 complete, and commit T005–T008 together with the passing-suite evidence noted in the commit body (Constitution Workflow step 5). Commit prefix: `Unallocated Funds Notification - M1.4`.

**Checkpoint (M1 — human approval required before Phase 4)**: The credit figure is
correct and independently proven. The banner does not use it yet, so nothing
user-visible has changed.

---

## Phase 4: User Story 2 — The banner names the quantities it reports (Priority: P2)

**Milestone**: M2 (the notification) — delivers the *rest* of US1 as well.

**Goal**: `get_notifications()` compares funds available against funds committed
and emits the sentence in [contracts/notification-content.md](./contracts/notification-content.md).

**Independent Test**: The rendered banner reports funds available net of credit
balances, names the credit deduction as its own linked term, describes the
pay-period figure as allocated-but-unspent, and carries five links in the
contract's order.

> **Note on story independence**: US1's *arithmetic* was delivered independently in
> Phase 3, but US1's and US2's *user-visible* changes both rewrite the same
> sentence and necessarily ship together. Splitting the sentence rewrite in two
> would mean writing it twice; see [research.md](./research.md) R6.

### Tests for User Story 2

- [X] T009 [US2] In `biweeklybudget/tests/unit/flaskapp/test_notifications.py`, add `credit_account_sum=DEFAULT` to the `patch.multiple(pb, ...)` call in **all five** `patch.multiple` blocks in `TestNotifications` (the class has six tests, but `test_num_stale_accounts` uses a plain `patch` and needs no change) and give each a return value. Omitting even one leaves that test hitting the real database instead of the mock — check every one, not just the two that assert the sentence. Commit prefix: `Unallocated Funds Notification - M2.1`.
- [X] T010 [US2] Update `test_get_notifications_over_balance` and `test_get_notifications_under_balance` in the same file to assert the new sentence exactly as specified in [contracts/notification-content.md](./contracts/notification-content.md), with a non-zero `credit_account_sum` so the test proves the credit term is actually applied to funds available rather than ignored. Commit prefix: `Unallocated Funds Notification - M2.1`.
- [X] T011 [P] [US2] Add a unit test asserting the equality case: when funds available (after credit balances) exactly equals funds committed, **no** funds-comparison notification is emitted — the case that becomes common once the fix lands (SC-001). Commit prefix: `Unallocated Funds Notification - M2.1`.
- [X] T012 [P] [US2] Add a unit test asserting that funds available may be negative — credit balances exceeding funding balances produce the `alert-danger` notification with a negative, currency-formatted available figure (FR-011 and the spec's edge case). Commit prefix: `Unallocated Funds Notification - M2.1`.

### Implementation for User Story 2

- [X] T013 [US2] Rewrite `get_notifications()` in `biweeklybudget/flaskapp/notifications.py`: compute `funds_available = budget_account_sum() + credit_account_sum()` and compare it against the unchanged `funds_committed`; emit the exact sentence, link targets, link texts and `classes` from [contracts/notification-content.md](./contracts/notification-content.md). Do not change `standing_budgets_sum()`, `pp_sum()` or `budget_account_unreconciled()` (FR-004). Update the `logger.info` line to include the credit figure. Commit prefix: `Unallocated Funds Notification - M2.2`.
- [X] T014 [US2] Recompute the expected figures in `TestBudgetOverBalanceNotification` in `biweeklybudget/tests/acceptance/flaskapp/views/test_base_template.py`: add a `credit_account_sum` assertion to `test_2_confirm_pp` and update `test_3_notification` for the new sentence and **five** links (the test indexes links positionally). Funds available becomes `12889.24 - 6450.71 = 6438.53`. **Verify the class still demonstrates an over-balance** — if the reduced available figure flips the verdict, adjust that class's own fixture setup so it still tests what its name says; never relabel the assertion to match whatever the code produces. Commit prefix: `Unallocated Funds Notification - M2.3`.
- [X] T014a [US2] Add a `TestCreditAccountSumAccountSelection` acceptance class to `biweeklybudget/tests/acceptance/flaskapp/views/test_base_template.py` covering FR-002 against the real database: inactive credit account excluded, the same account included once activated, bank/investment accounts excluded, a credit account with no balance row contributing zero, and the banner still rendering in that state. Added because these exclusions cannot be honestly asserted at the unit level (see T005). Commit prefix: `Unallocated Funds Notification - M2.3`.
- [X] T015 [US2] Do the same for `TestPPOverBalanceNotification.test_2_notification` and its `test_*_confirm_pp` in the same file, recomputing every expected value from the fixtures and re-checking the verdict. Commit prefix: `Unallocated Funds Notification - M2.3`.
- [X] T016 [US2] Do the same for `TestPPUnderBalanceNotification.test_3_notification` and its `test_*_confirm_pp` in the same file. Commit prefix: `Unallocated Funds Notification - M2.3`.
- [X] T017 [US2] Run `tox -e py314 > <scratchpad>/m2-unit.txt 2>&1` and `tox -e acceptance > <scratchpad>/m2-acceptance.txt 2>&1`. Both must complete and pass in full — a narrowed run or a timeout is not a pass; raise the timeout and re-run if needed (Constitution principle II). Commit prefix: `Unallocated Funds Notification - M2.4`.
- [X] T018 [US2] Update the Milestone section of [plan.md](./plan.md) to record M2 complete, and commit T009–T018 together. If any acceptance fixture had to be adjusted under T014–T016, say so explicitly in the commit body and state why. Commit prefix: `Unallocated Funds Notification - M2.5`.

**Checkpoint (M2 — human approval required before Phase 5)**: The banner is correct
and correctly labelled. FR-001 through FR-008 and FR-011 are delivered.

---

## Phase 5: User Story 3 — Transactions with no cash impact stay out of the comparison (Priority: P3)

**Milestone**: M3 (regression coverage).

**Goal**: Tie the existing `is_excluded_from_budget` behaviour to the banner, so
the already-delivered fix for the issue's defect #2 cannot regress silently.

**Independent Test**: Unreconciled transactions that carry no real cash impact
leave the banner's unreconciled figure and its verdict unmoved, while remaining
listed and reconcilable in the reconcile view.

> **No new exclusion logic is written here.** The mechanism exists on `master`
> ([research.md](./research.md) R4). If these tests fail, the bug is in that code,
> not in this feature — stop and escalate rather than adding a second exclusion
> rule. In particular, do **not** implement the issue's fallback suggestion of
> matching reconcile notes against `pseudo-trans`.

- [ ] T019 [US3] Add an incremental acceptance class to `biweeklybudget/tests/acceptance/flaskapp/views/test_base_template.py` that, against a funding account, adds an ordinary unreconciled transaction plus an unreconciled transaction marked `no_budget_impact`, and asserts the banner's unreconciled figure counts only the ordinary one and the verdict is unchanged by the excluded transaction. Follow the existing incremental-class pattern (`class_refresh_db`, `refreshdb`, `testflask`, `@pytest.mark.incremental`, numbered test methods). Commit prefix: `Unallocated Funds Notification - M3.1`.
- [ ] T020 [US3] Extend that class to cover an unreconciled transaction designated as a payment toward an active credit account, asserting it likewise does not contribute to the banner's unreconciled figure (FR-009). Commit prefix: `Unallocated Funds Notification - M3.1`.
- [ ] T021 [US3] Extend that class to assert both excluded transactions still appear in the reconcile view and remain reconcilable (FR-010) — excluding them from the arithmetic must never hide them from reconciliation. Commit prefix: `Unallocated Funds Notification - M3.1`.
- [ ] T022 [US3] Run `tox -e acceptance > <scratchpad>/m3-acceptance.txt 2>&1` in full and confirm it passes. Commit T019–T022 together and record M3 complete in [plan.md](./plan.md). Commit prefix: `Unallocated Funds Notification - M3.2`.

**Checkpoint (M3 — human approval required before Phase 6)**: All three user
stories delivered and independently covered.

---

## Phase 6: Documentation, Version, Changelog & Close-out

**Milestone**: M4.

- [ ] T023 [P] Add a section to `docs/source/app_usage.rst` describing the notification: what it compares (funds available vs. funds committed), that money owed on active credit accounts reduces funds available and why, what each of the three committed terms means, and explicitly that "current pay period allocated but unspent" is a different quantity from the pay period view's "remaining" — since that confusion is what issue #209/#320 reported. Follow the existing section style with a `.. _app_usage.<anchor>:` label, and cross-reference the existing `app_usage.no_budget_impact` section. Delivers FR-012. Commit prefix: `Unallocated Funds Notification - M4.1`.
- [ ] T024 [P] Bump `biweeklybudget/version.py` by a **PATCH** increment — a user-visible bug fix in reported figures, with no API or schema change (Constitution principle VI). Commit prefix: `Unallocated Funds Notification - M4.2`.
- [ ] T025 [P] Add a `CHANGES.rst` entry in the existing format for the new version, describing the corrected comparison, the relabelled pay-period figure, and the issue numbers (#320, #209). Commit prefix: `Unallocated Funds Notification - M4.2`.
- [ ] T026 Run the full gate and save each to the scratchpad: `tox -e py314`, `tox -e acceptance`, `tox -e docs`, `tox -e migrations`. All four must complete and pass. `migrations` passing with no migration added is the check that no schema drift crept in ([plan.md](./plan.md), principle III). Commit prefix: `Unallocated Funds Notification - M4.3`.
- [ ] T027 Walk the scenarios in [quickstart.md](./quickstart.md) against the running app (`flask rundev`), including the overpaid-card sign check and the no-credit-accounts case (SC-005). Commit prefix: `Unallocated Funds Notification - M4.3`.
- [ ] T028 Update [plan.md](./plan.md) and this file to record M4 complete, commit everything, push the branch to `origin`, and open a pull request describing the three defects, what was fixed, what was verified as already fixed, and the constitution compliance. Then monitor CI to completion. Commit prefix: `Unallocated Funds Notification - M4.4`.

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies.
- **Phase 2 (Foundational)**: after Phase 1. Verification only — nothing is built.
- **Phase 3 (US1 / M1)**: after Phase 2.
- **Phase 4 (US2 / M2)**: after Phase 3 — T013 calls `credit_account_sum()`, which T006 creates.
- **Phase 5 (US3 / M3)**: after Phase 4 — its assertions read the banner sentence that T013 finalises.
- **Phase 6 (M4)**: after all stories.

Milestone boundaries (end of Phases 3, 4, 5) require human approval before the
next phase begins.

### User story dependencies

- **US1 (P1)**: independent. Its arithmetic ships alone in Phase 3.
- **US2 (P2)**: depends on US1's `credit_account_sum()`. Its sentence rewrite also
  carries US1's user-visible half — see the note in Phase 4.
- **US3 (P3)**: no logic dependency (the behaviour already exists), but its
  assertions read the final sentence, so it follows Phase 4.

### Parallel opportunities

- T011 and T012 are independent new unit tests and can be written in parallel.
- T023, T024 and T025 touch three different files and can run in parallel.
- T014, T015 and T016 all edit the same file and must **not** be parallelised.
- T009 and T010 edit the same file and must not be parallelised.

---

## Implementation Strategy

### MVP

Phases 1–3 (through M1) deliver the correct credit figure with full test
coverage, provable in isolation and safe to stop at — nothing user-visible has
changed yet.

### Incremental delivery

1. Phases 1–2 → environment and prerequisites verified.
2. Phase 3 (M1) → the figure exists and is correct. **Stop, validate, approve.**
3. Phase 4 (M2) → the banner is corrected and relabelled; the user-visible fix
   lands. **Stop, validate, approve.**
4. Phase 5 (M3) → regression coverage pins the already-fixed defect #2.
   **Stop, validate, approve.**
5. Phase 6 (M4) → docs, version, changelog, full gate, PR.

---

## Notes

- `[P]` means different files and no dependency on an incomplete task.
- Commit after each task or logical group, always with the milestone/task prefix.
- **Never** use `abs()` on a credit balance in this feature's arithmetic
  ([research.md](./research.md) R1). If a test seems to demand it, the test is wrong.
- **Never** relabel an acceptance assertion to match whatever the code now
  produces; fix the fixture so the class still demonstrates its named case.
- Redirect all test output to scratchpad files rather than piping to
  `tail`/`head`/`grep`, per `CLAUDE.md`.
- Acceptance tests drop and reload the database — only ever point them at the
  throwaway test container.
