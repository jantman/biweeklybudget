---

description: "Task list for Credit Payment Panel Window (issue #358)"
---

# Tasks: Credit Payment Panel Window

**Input**: Design documents from `specs/20260919-073200-credit-payment-panel-window/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/credit-payment-info.md](./contracts/credit-payment-info.md), [quickstart.md](./quickstart.md)

**Tests**: Test tasks are **required**, not optional. Constitution Principle II (NON-NEGOTIABLE) requires new code to be covered by valid tests and the full suites to pass before the feature is done, and the *Financial correctness* constraint requires pinned numbers for changes to pay-period arithmetic.

**Organization**: Tasks are grouped by user story. Each group is one constitution milestone; commit messages use the prefix `Credit Payment Panel Window - M{milestone}.{task}`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are given in every task

## Path Conventions

Single Python package at the repository root: `biweeklybudget/` for source,
`biweeklybudget/tests/unit/` and `biweeklybudget/tests/acceptance/` for tests,
`biweeklybudget/flaskapp/static/js/` for frontend, `docs/source/` for documentation.
Paths below are relative to the repository root,
`/home/jantman/worktrees/biweeklybudget/issue-358`.

## Milestone Map

| Milestone | User Story | Delivers |
|---|---|---|
| M1 | US1 (P1) | The per-account self-healing window — the reported defect is fixed |
| M2 | US2 (P2) + US3 (P3) | The capped table with its summary row, and the window line in the panel |
| M3 | — | Documentation, changelog, the full test gate, and delivery |

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish a green baseline so any later failure is attributable to this change.

- [ ] T001 Activate the main checkout's virtualenv (`source /home/jantman/GIT/biweeklybudget/venv/bin/activate`; this worktree has none), export `TOXINIDIR` and a touched `BIWEEKLYBUDGET_LOG_FILE` per [quickstart.md](./quickstart.md), and run `pytest biweeklybudget/tests/unit/test_credit_payment.py`, redirecting output to a scratchpad file. Record that the baseline is green.
- [ ] T002 Confirm the acceptance test database container is running per `CLAUDE.md` ("Test Database Setup for Development"), then run `tox -e acceptance -- -k "CreditPayment"` redirecting to a scratchpad file, to establish the acceptance baseline for the modules this change touches. Confirm it is green before changing anything.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that must exist before any user story.

**None.** This feature adds no module, model, dependency, setting, schema change or
migration. `biweeklybudget/credit_payment.py`, its tests, and
`biweeklybudget/flaskapp/static/js/transactions_modal.js` already exist and are the only
source files that change. User Story 1 can begin immediately after Phase 1.

**Checkpoint**: Nothing to do — proceed to Phase 3.

---

## Phase 3: User Story 1 - A payment panel that reflects the card, not the archive (Priority: P1) 🎯 MVP — Milestone M1

**Goal**: The charge window is bounded per account by the pay period following the one
holding the earliest payment designated toward that account, floored by
`CREDIT_PAYMENT_BEGIN_DATE`. Recording one payment for a card tightens its window
permanently. The anchoring payment falls outside the window, so it is never subtracted
twice.

**Independent Test**: With one payment designated toward a card whose charges go back
years, compute an attribution for a later payment and confirm the unpaid total, the
period list and the warning all start after that first payment's period — and that the
anchoring payment is not also subtracted as a prior payment. Per
[quickstart.md](./quickstart.md) §2.

### Tests for User Story 1 ⚠️

Written first; they fail until T007 lands.

- [ ] T003 [US1] In `biweeklybudget/tests/acceptance/test_credit_payment.py`, add the anchor payment to `TestCreditPaymentAttribution.test_06_prior_payment_reduces_unpaid`: a `Transaction` dated `date(2017, 4, 10)` for `Decimal('900.00')`, described `Pre-feature payment`, recorded against `BankOne` with `credit_payment_acct=card`, added alongside the existing 2017-05-06 payment. Add a comment stating that it anchors the derived window at 2017-04-21 so the existing assertions in tests 06, 07, 09 and 10 keep their original values and meanings — see [research.md](./research.md) D-5 for the arithmetic. Change no assertion in those tests.
- [ ] T004 [P] [US1] In `biweeklybudget/tests/acceptance/test_credit_payment.py`, add `TestCreditPaymentWindow(AcceptanceHelper)` — a new incremental class with its own `class_refresh_db`/`refreshdb` fixtures, a bank account, a credit account and a periodic budget, `PAY_PERIOD_START_DATE` patched to `date(2017, 4, 7)` and `dtnow` patched — with charges in several consecutive pay periods. Cover, each with pinned numbers: (a) no designated payment at all, so `begin_date` equals the configured `CREDIT_PAYMENT_BEGIN_DATE` and behaviour is as today (FR-004); (b) one designated payment, so `begin_date` is the start of the *following* pay period and earlier charges are excluded (FR-002); (c) that the anchoring payment is **not** also subtracted as a prior payment, asserted by comparing `total_unpaid` against the in-window charge sum (FR-005a) — this is the invariant the boundary design exists for.
- [ ] T005 [P] [US1] In the same new class, cover the remaining window rules with pinned numbers: (a) a configured `CREDIT_PAYMENT_BEGIN_DATE` later than the derived bound wins, via `@patch('%s.settings.CREDIT_PAYMENT_BEGIN_DATE' % pbm, ...)` (FR-007, spec Example D); (b) `exclude_txn_id` naming the anchoring payment still leaves it anchoring the window (FR-005); (c) a payment back-dated before every designated payment gets the configured begin date (FR-003, spec Example E); (d) a payment dated inside the anchor's own period yields an empty window — `periods == []`, `total_unpaid == 0`, the whole amount as excess — and the configured date is *not* reinstated (FR-005b).
- [ ] T006 [P] [US1] In `biweeklybudget/tests/unit/test_credit_payment.py`, add a `TestEffectiveBeginDate` class exercising `_effective_begin_date()` against a mocked session and a mocked `BiweeklyPayPeriod.period_for_date`: that `None` from the query returns the configured date unchanged, that a found date returns `max(configured, period.next.start_date)`, and that `exclude_txn_id` is *not* applied to the derivation query. Follow the module's existing mock-free-where-possible style; use `unittest.mock.patch` as the acceptance module does.

### Implementation for User Story 1

- [ ] T007 [US1] In `biweeklybudget/credit_payment.py`, add `_effective_begin_date()` to `CreditPaymentAttribution`: query `func.min(Transaction.date)` filtered to `Transaction.credit_payment_acct_id == self.account.id` and `Transaction.date <= self.payment_date`, **without** applying `exclude_txn_id`; return `self.configured_begin_date` when the result is `None`, otherwise `max(self.configured_begin_date, BiweeklyPayPeriod.period_for_date(first, self._db).next.start_date)`. Import `func` from `sqlalchemy`. Give the method a docstring in the module's existing reStructuredText style stating what it derives, why the bound sits after the anchoring payment's period, and that the anchor is deliberately not excluded.
- [ ] T008 [US1] In `biweeklybudget/credit_payment.py`, in `__init__`, set `self.configured_begin_date = settings.CREDIT_PAYMENT_BEGIN_DATE` and `self.begin_date = self._effective_begin_date()` before `self._calculate()`. Leave `_charges_by_period()` and `_prior_payments()` untouched — both already read `self.begin_date`, which is what makes every downstream figure consistent (FR-008).
- [ ] T009 [US1] In `biweeklybudget/credit_payment.py`, add `'configured_begin_date': self.configured_begin_date` to `as_dict` beside the existing `begin_date`, per [contracts/credit-payment-info.md](./contracts/credit-payment-info.md).
- [ ] T010 [US1] Run `pytest biweeklybudget/tests/unit/test_credit_payment.py` and `tox -e acceptance -- -k "CreditPayment"`, redirecting to scratchpad files. All green, including every pre-existing assertion. Investigate any failure rather than adjusting the assertion.

**Checkpoint**: the reported defect is fixed. The panel is scoped to the card, not the archive. **Milestone M1 — request human approval before starting M2.**

---

## Phase 4: User Story 2 - A panel that fits in the modal (Priority: P2) + User Story 3 - Knowing what window you are looking at (Priority: P3) — Milestone M2

**Goal**: At most six periods are rendered individually; everything older collapses into
one summary row carrying the collapsed periods' count, date range and both summed
amounts, at the head of the table. The panel states the date it is counting from.

**Why US2 and US3 share a milestone**: both change only
`transModalCreditPaymentInfoHtml()` and `as_dict`, and US3 is two lines of rendering
against data US2 already puts in the payload. Splitting them would mean two passes over
the same function for no independent value.

**Independent Test**: build a window spanning more periods than the cap and confirm the
table holds six period rows plus exactly one summary row, that the summary row states its
count and date range, and that the rendered rows sum to the totals line. Per
[quickstart.md](./quickstart.md) §1 and §3.

### Tests for User Story 2 and 3 ⚠️

- [ ] T011 [P] [US2] In `biweeklybudget/tests/unit/test_credit_payment.py`, add a `TestRollup` class for the cap with pinned `Decimal` numbers: a list of exactly `CREDIT_PAYMENT_MAX_PERIODS` periods produces `rollup is None` and all periods rendered (the boundary is inclusive, FR-013); one more produces a rollup of `count` 1 with the oldest period's dates and amounts; a long list produces the right `count`, `start_date`, `end_date`, and `Decimal` sums; and in every case the invariants from [data-model.md](./data-model.md) hold — individual plus rollup `outstanding` and `attributed` equal the whole-window totals (FR-014).
- [ ] T012 [P] [US2] In `biweeklybudget/tests/acceptance/test_credit_payment.py`, extend the class from T004 with a case whose window spans more than `CREDIT_PAYMENT_MAX_PERIODS` periods with charges, asserting against a real database that `len(a.periods) == CREDIT_PAYMENT_MAX_PERIODS`, that `a.rollup` carries the expected count, dates and `Decimal` sums, and that `a.total_unpaid` and `a.total_attributed` are unchanged by the cap — the cap is a display concern and must never change an amount.
- [ ] T013 [US2] In `biweeklybudget/tests/acceptance/test_credit_payment.py`, add a Selenium class `TestTransCreditPaymentPanel` driving the Add New Transaction modal on `/transactions`: enter an amount, select the credit account under **Credit Card Payment For**, wait for the panel, and assert the table `#credit_payment_periods` holds at most six period rows, that `#credit_payment_rollup` is present with its count and date range when periods were collapsed and absent when they were not, and that `#credit_payment_window` states the window start. Follow the existing modal acceptance tests for the wait pattern; per project memory, `AcceptanceHelper.get()` does not wait for AJAX, so wait explicitly on the panel content.

### Implementation for User Story 2 and 3

- [ ] T014 [US2] In `biweeklybudget/credit_payment.py`, add the module-level constant `CREDIT_PAYMENT_MAX_PERIODS = 6` with a comment giving its rationale (six biweekly periods ≈ three months; a display cap, not a setting — [research.md](./research.md) D-4).
- [ ] T015 [US2] In `biweeklybudget/credit_payment.py`, at the end of `_calculate()`, split the filtered oldest-first period list: when it holds more than `CREDIT_PAYMENT_MAX_PERIODS` entries, keep the trailing `CREDIT_PAYMENT_MAX_PERIODS` in `self.periods` and set `self.rollup` to a dict of `count`, `start_date` (oldest collapsed period's start), `end_date` (newest collapsed period's end), and `Decimal` sums of `outstanding` and `attributed`; otherwise set `self.rollup = None`. Initialise `self.rollup = None` in `__init__` beside the other attributes. Leave `total_unpaid`, `total_attributed` and `excess` computed over the whole window, before the split.
- [ ] T016 [US2] In `biweeklybudget/credit_payment.py`, add `'rollup': self.rollup` to `as_dict`, per [contracts/credit-payment-info.md](./contracts/credit-payment-info.md).
- [ ] T017 [US2] In `biweeklybudget/flaskapp/static/js/transactions_modal.js`, in `transModalCreditPaymentInfoHtml()`, prepend a summary row to the table body when `data['rollup']` is non-null: `<tr id="credit_payment_rollup">` with `text-muted`, a period cell reading `N older periods (start – end)`, a status cell reading `rolled up`, then the formatted `outstanding` and `attributed` cells. When `rollup['attributed']` is non-zero, additionally set `font-weight: 700` on the row so a payment landing entirely on collapsed periods is conspicuous (FR-015). Build it with the same jQuery construction and Bootstrap 3 classes as the rows beside it. Update the function's JSDoc.
- [ ] T018 [US3] In `biweeklybudget/flaskapp/static/js/transactions_modal.js`, after the totals paragraph in `transModalCreditPaymentInfoHtml()`, append `<p id="credit_payment_window">` stating the date unpaid charges are counted from, taken from `data['begin_date']`, styled `text-muted` to match the other secondary prose in the panel (FR-016).
- [ ] T019 [US2] Run `pytest biweeklybudget/tests/unit/test_credit_payment.py` and `tox -e acceptance -- -k "CreditPayment"`, redirecting to scratchpad files. All green.

**Checkpoint**: the panel is bounded and self-describing whatever the window. **Milestone M2 — request human approval before starting M3.**

---

## Phase 5: Polish, Documentation & Delivery — Milestone M3

**Purpose**: Constitution Principles II, IV and VI — documentation in the same change, the
full test gate, the changelog entry, and delivery.

- [ ] T020 [P] In `biweeklybudget/credit_payment.py`, rewrite step 1 of the `CreditPaymentAttribution` class docstring's algorithm, which becomes factually wrong the moment T007 lands: the window's lower bound is now derived per account and floored by the setting. State why the bound sits after the anchoring payment's period (it would otherwise be subtracted twice) and what an account with no designated payment gets. Document the new `rollup` attribute and the cap in the same docstring.
- [ ] T021 [P] In `biweeklybudget/settings.py`, update the `CREDIT_PAYMENT_BEGIN_DATE` docstring comment: it is now a floor beneath a per-account derived bound, not the window on its own. Keep the existing explanation of why a lower bound is needed at all, and say that the derived bound makes moving this date forward unnecessary for most installs (FR-019).
- [ ] T022 [P] In `docs/source/app_usage.rst`, in the *What the payment panel tells you* section, replace the closing paragraph about `CREDIT_PAYMENT_BEGIN_DATE` with prose covering: that payments recorded before this feature existed carry no card designation and are not subtracted; that the window therefore starts after the first payment recorded for each card and tightens by itself; that an upgrading user will see one panel counting from the configured begin date for each card, and a scoped one from then on; that charges made after that first payment but inside its pay period fall outside the window; and that the table shows at most six periods with older ones summarised in one row (FR-018).
- [ ] T023 In `CHANGES.rst`, add a bullet under `Unreleased` (creating the heading beneath the `Changelog` title if absent) in the existing concise format: link issue #358, state that the credit payment panel now counts unpaid charges from the first payment recorded for each card rather than from `CREDIT_PAYMENT_BEGIN_DATE`, and that the table is capped at six pay periods with older ones summarised. Note in a sub-bullet that payments recorded before 2.0.0 carry no card designation, so the first payment entered for each card after upgrading still shows the old wide window. Per project memory, name the documentation section in prose — do **not** link to a docs anchor added in this change, which breaks `tox -e docs` linkcheck. Do not touch `biweeklybudget/version.py`.
- [ ] T024 Run `tox -e docs`, redirecting to a scratchpad file. It must build without errors. A linkcheck failure on an unrelated external URL is a known transient per project memory — re-run before treating it as a failure.
- [ ] T025 Run the complete unit suite (`tox -e py314`) and the complete acceptance suite (`tox -e acceptance`) to completion, redirecting each to a scratchpad file. Both must pass in full. A suite that times out has not passed: raise the pytest and tool timeouts and re-run (Constitution II). Known-flaky tests per project memory — reconcile drag/unignore, fuel log search, Plaid "Uncheck All" — are unrelated; re-run them in isolation before attributing a failure to this change.
- [ ] T026 Run `tox -e migrations`, redirecting to a scratchpad file, as a regression check. This change alters no model and adds no migration, so head must still match the models.
- [ ] T027 Run a lint pass (pycodestyle and pyflakes under the exceptions in `setup.cfg`/`pytest.ini`, `max-line-length` 100) over every changed Python file. Per project memory this needs a scratch venv in a worktree. Clean before commit.
- [ ] T028 Update this feature's spec artifacts to record progress and the delivered outcome, then commit the whole milestone together with the prefix `Credit Payment Panel Window - M3.{task}`.
- [ ] T029 Push the branch to `origin` with `git push -u origin HEAD:refs/heads/robot-army/issue-358-credit-payment-this-payment-covers` — per project memory this worktree's branch tracks `origin/master`, so a bare `git push` would push to master — and open a pull request describing the problem, the two changes, the decisions taken with the maintainer (spec D-1, D-1a, D-2, D-3), and the accepted cost of the boundary rule.
- [ ] T030 Monitor the pull request's CI jobs to completion. When all are complete, run `/answer-reviews` to respond to review comments, and repeat until reviews from Claude state "No issues found" and any Copilot review recommends approval.

---

## Dependencies

```text
Phase 1 (T001-T002)  Setup / baseline
        │
        ▼
Phase 3 (T003-T010)  US1 — Milestone M1   ← MVP; fixes the reported defect alone
        │
        ▼  (human approval)
Phase 4 (T011-T019)  US2 + US3 — Milestone M2
        │
        ▼  (human approval)
Phase 5 (T020-T030)  Docs, changelog, test gate, delivery — Milestone M3
```

**Story dependencies**: US2 depends on US1 only in sequencing, not in substance — the cap
would work against today's window too. It is second because the window fix is what makes
the panel correct, and the cap is what keeps it correct under any window. US3 is bundled
with US2 because both touch only the same rendering function.

**Within Phase 3**: T003, T004, T005 and T006 are independent of each other (T003 edits an
existing class, T004/T005 a new one, T006 a different file) and precede T007. T007 → T008
→ T009 are sequential in the same file. T010 is the gate.

**Within Phase 4**: T011, T012, T013 are independent. T014 → T015 → T016 are sequential in
`credit_payment.py`; T017 and T018 both edit `transactions_modal.js` and so are
sequential with each other, but independent of T014–T016. T019 is the gate.

**Within Phase 5**: T020, T021 and T022 are in three different files and fully parallel.
T023 follows them. T024–T027 are the gates, then T028 → T029 → T030.

## Parallel Execution Examples

```text
# Phase 3, tests first:
T003, T004, T005, T006   — four test tasks, three files, no shared state

# Phase 4, tests first:
T011, T012, T013         — unit, attribution-level acceptance, Selenium

# Phase 5, documentation:
T020, T021, T022         — credit_payment.py, settings.py, app_usage.rst
```

## Implementation Strategy

**MVP is Milestone M1 alone.** US1 fixes the defect the issue reports: after it, the panel
is scoped to the card and the over-payment warning means something again. The cap (M2) is
the guarantee that it stays readable under any window, and is worth having, but the
feature delivers its value at M1.

**Increment order** is the milestone order, each closed per Constitution Workflow step 5:
suites green, documentation updated, spec artifacts updated to record progress, committed
together.
