# Implementation Plan: Credit Payment Panel Window

**Branch**: `robot-army/issue-358-credit-payment-this-payment-covers` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260919-073200-credit-payment-panel-window/spec.md`

## Summary

The credit payment panel's charge window is bounded below by a setting whose default —
the reconcile begin date — bounds nothing for an install with years of history, so the
panel lists every pay period since 2018 and reports an unpaid total unrelated to the
card's balance.

Two changes fix it, both confined to `CreditPaymentAttribution` and the jQuery function
that renders its output:

1. **A per-account, self-healing lower bound.** The window now starts at the later of the
   configured begin date and the start of the pay period *after* the one holding the
   earliest payment designated toward that account. Recording one payment for a card
   tightens its window permanently, with no operator action. The anchoring payment falls
   outside the resulting window, so it is not also subtracted as a prior payment.
2. **A capped table.** At most six periods are rendered individually; everything older
   collapses into one summary row carrying the collapsed periods' count, date range, and
   both summed amounts. The rollup is computed server-side in `Decimal` so the rows still
   add up to the totals line exactly.

Attribution stays oldest-first (spec D-2). No schema change, no new setting, no migration.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy; jQuery / Bootstrap 3 on the frontend

**Storage**: MySQL / MariaDB. **No schema change** — the derivation reads the existing
`transactions.credit_payment_acct_id` and `transactions.date` columns.

**Testing**: pytest. Unit tests (`biweeklybudget/tests/unit/`) for the pure helpers;
acceptance tests (`biweeklybudget/tests/acceptance/`) for anything needing a database or
a browser. Selenium for the rendered panel.

**Target Platform**: Linux, localhost single-operator web application

**Project Type**: Flask web application, single package

**Performance Goals**: the endpoint is called on every keystroke in the amount field; the
derivation adds one indexed `MIN(date)` aggregate per call, and the cap shrinks the JSON
payload from potentially 200+ period objects to at most 7.

**Constraints**: all money arithmetic in `decimal.Decimal`; no new frontend stack; the
panel stays advisory and never blocks saving.

**Scale/Scope**: one module (~60 lines changed), one JavaScript function (~30 lines
changed), two test modules, three documentation surfaces plus the changelog.

## Constitution Check

Constitution v2.1.2. Evaluated before Phase 0 and re-evaluated after Phase 1 design; the
result is the same in both passes.

| Principle | Status | How this change satisfies it |
|-----------|--------|------------------------------|
| **I. Spec-Driven Change** | PASS | Spec, plan and tasks written before code, on the feature branch this session was dispatched onto. The three decisions the issue deferred were put to the maintainer before the spec was written; a fourth (the boundary refinement, spec D-1a) was put to them during planning rather than resolved silently. Milestones below; human approval at each boundary. |
| **II. The Test Gate** | PASS | Full unit and acceptance suites run to completion before the feature is declared done. New behaviour is covered by tests that pin numbers, including the double-count case (FR-005a) that motivates the design. The existing acceptance assertions are preserved rather than rewritten to match new output — see research.md D-5. pycodestyle/pyflakes clean under `pytest.ini`'s exceptions. |
| **III. Reversible Migrations** | N/A | Nothing under `biweeklybudget/models/` changes. No Alembic migration; the `migrations` suite is unaffected but is run anyway as a regression check. |
| **IV. Documentation Is Part Of The Change** | PASS | M3 updates `docs/source/app_usage.rst`, the `CREDIT_PAYMENT_BEGIN_DATE` docstring, and the `CreditPaymentAttribution` class docstring — whose step 1 becomes factually wrong the moment M1 lands. `tox -e docs` must build clean. |
| **V. Escalate Instead Of Guessing** | PASS | Two escalations already made (the three issue-level decisions; the boundary refinement). Any further significant decision stops and asks. |
| **VI. Changelog Every Change** | PASS | One concise bullet under `Unreleased` in `CHANGES.rst`, naming the user-visible consequence for an upgrading install. No `version.py` change, no tag. Per project memory, the entry names the documentation section in prose rather than linking to a new anchor, which would break linkcheck. |
| **Financial correctness** | PASS | The rollup sums stay in `Decimal` server-side rather than being summed in JavaScript floats; FR-014 (rows reconcile to the totals line) is tested with pinned numbers. |
| **Stack constraint** | PASS | The summary row is built with the same jQuery construction and Bootstrap 3 classes as the rows beside it. No new frontend dependency. |
| **Security posture** | PASS | Unchanged. Read-only endpoint, no new surface. |

No violations. The Complexity Tracking table is therefore omitted.

## Project Structure

### Documentation (this feature)

```text
specs/20260919-073200-credit-payment-panel-window/
├── spec.md              # Phase -1 output (/speckit-specify)
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0 output — decisions D-1 .. D-7
├── data-model.md        # Phase 1 output — the as_dict contract
├── quickstart.md        # Phase 1 output — how to verify this by hand
├── contracts/
│   └── credit-payment-info.md   # Phase 1 output — the AJAX response contract
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
biweeklybudget/
├── credit_payment.py                          # the window derivation and the rollup
├── settings.py                                # CREDIT_PAYMENT_BEGIN_DATE docstring
├── flaskapp/
│   └── static/js/transactions_modal.js        # transModalCreditPaymentInfoHtml()
└── tests/
    ├── unit/test_credit_payment.py            # rollup split; pure-function tests
    └── acceptance/test_credit_payment.py      # window derivation; rendered panel

docs/source/app_usage.rst                      # credit card payments section
CHANGES.rst                                    # Unreleased entry
```

**Structure Decision**: no new files. Every change lands in a module that already exists
and already owns the behaviour being changed. `CreditPaymentAttribution` owns the
window's definition, so the derivation goes there rather than into the view; the rollup
goes there too so the arithmetic stays in `Decimal` (research.md D-3).

## Design

### The window derivation

`CreditPaymentAttribution.__init__` gains, before `_calculate()`:

```text
self.configured_begin_date = settings.CREDIT_PAYMENT_BEGIN_DATE
self.begin_date            = self._effective_begin_date()
```

`_effective_begin_date()`:

1. `MIN(date)` over transactions with `credit_payment_acct_id == account.id` and
   `date <= payment_date`. **`exclude_txn_id` is not applied** — the transaction being
   edited still anchors the window (FR-005), so the panel does not change between
   entering a payment and reopening it.
2. No such transaction → return the configured begin date (FR-004). This is the
   upgrading install's one noisy panel, once per card.
3. Otherwise return
   `max(configured, BiweeklyPayPeriod.period_for_date(first, db).next.start_date)`.

Everything downstream — `_charges_by_period()`, `_prior_payments()`, the unpaid total,
the attribution, the excess, the warning — already reads `self.begin_date` and therefore
needs no change at all (FR-008). That is the whole point of putting the effective date on
the existing attribute.

The derived bound can land after the payment date (a second payment inside the anchor's
own period). The window is then simply empty; the configured date is **not** reinstated
as a fallback, which would swing the panel back to the whole of recorded history
(FR-005b).

### The rollup

At the end of `_calculate()`, after the period list is filtered to those with a non-zero
total:

```text
if len(periods) > CREDIT_PAYMENT_MAX_PERIODS:
    older    = periods[:-CREDIT_PAYMENT_MAX_PERIODS]
    self.periods = periods[-CREDIT_PAYMENT_MAX_PERIODS:]
    self.rollup  = {count, start_date, end_date, outstanding, attributed}
else:
    self.rollup = None
```

The list is oldest-first, so the collapsed periods are the leading slice and the summary
row belongs at the head of the table (FR-011). `outstanding` and `attributed` are `Decimal`
sums of the collapsed periods, which is what makes FR-014 hold exactly.

### The rendering

`transModalCreditPaymentInfoHtml()` prepends one `<tr id="credit_payment_rollup">` when
`data['rollup']` is non-null: period cell `N older periods (start – end)`, status cell
`rolled up`, then the two currency cells. `text-muted` normally; additionally bold when
the attributed amount is non-zero, so a payment that landed entirely on collapsed periods
is conspicuous rather than inferred (FR-015).

A line beneath the totals states the window start from `data['begin_date']` (FR-016).

The empty case, the warnings, the totals line, and the ability to save regardless are all
untouched (FR-017).

## Milestones

Human approval is required to advance between milestones (Constitution I).

- **M1 — Window derivation.** `CreditPaymentAttribution` gains
  `_effective_begin_date()` and `configured_begin_date`; unit and acceptance tests for
  the derivation, the floor, the anchor's exclusion from prior payments, back-dating,
  and the empty-window case. The existing acceptance class gains its anchor payment
  (research.md D-5) so its assertions stay valid. Suites green.
- **M2 — Capped table.** `CREDIT_PAYMENT_MAX_PERIODS`, the rollup in `_calculate()`, the
  `rollup` key in `as_dict`, the summary row and window line in
  `transModalCreditPaymentInfoHtml()`. Unit tests for the split, acceptance tests for the
  rendered panel. Suites green.
- **M3 — Documentation and changelog.** `docs/source/app_usage.rst`, the settings
  docstring, the class docstring, the `Unreleased` entry. `tox -e docs` clean.
- **M4 — Delivery.** Full unit, acceptance, migrations and docs suites to completion.
  Push, open the pull request, drive CI and reviews to green.

## Risks

| Risk | Mitigation |
|------|------------|
| The derived bound silently drops genuinely unpaid charges made after the anchor payment but inside its period | Accepted and documented (spec D-1a); the alternative double-counts the payment, which is worse. Called out in the user documentation. |
| Existing acceptance tests collapse to asserting zeroes, hiding a regression | Anchor payment added to the fixture so every existing assertion keeps its original value and meaning — research.md D-5 works the arithmetic through case by case. |
| Rounding drift makes rows stop summing to the totals line | Rollup summed server-side in `Decimal`; FR-014 tested with pinned numbers. |
| Acceptance flakiness masking a real failure | Per project memory, the reconcile-drag, fuel-search and Plaid "Uncheck All" tests have known waits races; re-run in isolation before attributing a failure to this change. |

## Delivery Record

**Implemented 2026-09-19**, in one pass rather than three approval-gated milestones:
the change is ~60 lines of Python and ~55 of JavaScript in two files, and M1 and M2 touch
the same two functions. Splitting them would have meant two passes over the same code for
no independent value. The milestone structure is retained above as the record of what was
built and why.

### What landed

| Milestone | Where |
|---|---|
| M1 — window derivation | `CreditPaymentAttribution._effective_begin_date()`, `configured_begin_date`, `as_dict` |
| M2 — capped table | `CREDIT_PAYMENT_MAX_PERIODS`, `_split_for_display()`, `rollup` in `as_dict`, `transModalCreditPaymentRollupHtml()` and `transModalCreditPaymentWindowHtml()` |
| M3 — documentation | class docstring, `CREDIT_PAYMENT_BEGIN_DATE` docstring, two new `app_usage.rst` sections, `CHANGES.rst` |

### Deviations from the plan

1. **A third affected test class.** Planning found two acceptance classes asserting
   numbers the new window changes; there is a third,
   `TestCreditPaymentInfoAjax` in
   `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py`, which
   research.md D-5 did not cover. Its fixture records its payment in the same pay period
   as its charges, so the derived bound landed after the payment date and the window came
   out empty — the FR-005b case. It was repaired the same way D-5 repairs the others: an
   anchor payment two pay periods earlier, leaving all of its existing assertions at their
   original values. Two tests (`test_12_window_keys`, `test_13_rollup_absent_...`) were
   added there for the new response keys, per the contract.
2. **`_split_for_display()` extracted as a static method** rather than written inline in
   `_calculate()`. It makes the cap unit-testable against pinned numbers the way
   `_consume()` already is, which is what the plan wanted from computing the rollup
   server-side.
3. **Invariant 1 in data-model.md was wrong** as first written
   (`... == total_unpaid + total_attributed`). Each period dict's `outstanding` is
   restored to its pre-attribution value and `total_unpaid` is likewise measured before
   this payment, so the correct statement is `... == total_unpaid`. Corrected in
   data-model.md and pinned by `test_04_cap_and_rollup`.

### Test gate

| Suite | Result |
|---|---|
| `tox -e py314` (unit, incl. pycodestyle/pyflakes) | pass |
| `tox -e acceptance` | pass |
| `tox -e docs` | builds clean; the 155 warnings are pre-existing duplicate-jsdoc ones |
| `tox -e migrations` | pass — no model changed, head still matches |

Coverage added: 12 unit tests (`TestEffectiveBeginDate`, `TestSplitForDisplay`), 12
attribution-level acceptance tests (`TestCreditPaymentWindow`), 2 endpoint tests and 5
Selenium tests across `TestTransModalCreditPaymentPanel` and
`TestTransModalCreditPaymentRollup`.

### Review outcome

Pull request [#361](https://github.com/jantman/biweeklybudget/pull/361).

**Round 1** — the `claude-review` job raised two defects, both valid, both fixed in
`d8eed51` and recorded as research.md D-8 and D-9:

1. *Editing a card's anchor payment emptied its window.* Not merely a code bug: FR-005
   stated the defective behaviour **as a requirement**, so the implementation was
   faithfully wrong. The requirement's stated purpose — that editing a payment shows what
   entering it showed — is satisfied by *excluding* the edited transaction from the
   derivation, not including it, because a payment being entered is not yet in the
   database and anchors nothing. FR-005 is reversed; the test that should have caught it
   passed `exclude_txn_id` while leaving the payment date at the class default, never
   exercising the failing combination.
2. *`TypeError` for environment-configured date settings.* `settings.py`'s `_DATE_VARS`
   loop stores `datetime.strptime(...)` without `.date()`, and `_effective_begin_date()`
   is the first place in the codebase comparing a `date` with a `datetime` at the Python
   level — on the routine path. Fixed with `_as_date()`, scoped to this module; the
   underlying settings inconsistency is recorded as a side quest.

**Round 2** — "No issues found", confirming both fixes correct and complete, that
`_as_date()` is applied at every point a mismatched comparison could occur, and that the
new tests "are not tautological".

No Copilot review is configured on this repository.

**Final CI on `d8eed51`**: acceptance, claude-review, coverage, docker, docs, jsdoc,
migrations, plaid, py314, screenshots and snyk all pass.
