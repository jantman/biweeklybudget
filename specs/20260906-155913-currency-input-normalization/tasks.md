---

description: "Task list for Currency Value Input Normalization"
---

# Tasks: Currency Value Input Normalization

**Input**: Design documents from `specs/20260906-155913-currency-input-normalization/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: **REQUIRED**, not optional, for this feature. The issue explicitly asks for
"actual browser tests"; spec FR-011 mandates them; and constitution principle II (The Test
Gate, NON-NEGOTIABLE) requires the full unit and acceptance suites to pass before the
feature is complete.

**Organization**: Tasks are grouped by user story. Note the shape of this particular
feature: Phase 2 is unusually heavy and Phases 3–7 are unusually light, because a single
parser plus a single interception point is what makes all five stories true. The story
phases are where each story gets *wired up and proven*, which is where it can still be
broken.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths are given in every task

## Path Conventions

Single Python package at the repository root. Server code under `biweeklybudget/`,
browser code under `biweeklybudget/flaskapp/static/js/`, tests under
`biweeklybudget/tests/{unit,acceptance}/`.

---

## Phase 1: Setup

**Purpose**: Working environment for the suites this feature must keep green.

- [X] T001 Start the test MariaDB container and export the test DB environment variables per `CLAUDE.md`, then run `python dev/setup_test_db.py` from the repo root to create `budgettest`, `alembicLeft`, and `alembicRight`
- [X] T002 Establish the pre-change baseline: run `tox -e py314` redirecting full output to a scratchpad file, and record which tests pass now so post-change failures are attributable to this feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The parser and the single interception point. Everything else is wiring.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### The parser

- [X] T003 Add `CurrencyParseError(ValueError)` and `parse_currency(value)` to `biweeklybudget/utils.py`, directly below the existing `fmt_currency()`, implementing the 8-step algorithm in `contracts/parse_currency-python.md`: normalize Unicode spaces, strip surrounding parentheses as negation, **loop** stripping currency symbol / ISO code / sign until stable, reject empty, rewrite remaining internal spaces to the locale group separator, then `babel.numbers.parse_decimal(s, locale=settings.LOCALE_NAME, strict=True)`, then apply negation
- [X] T004 [P] Add the `parse_currency` accept-case unit tests to `biweeklybudget/tests/unit/test_utils.py`, table-driven over every accepting row of the matrix in `contracts/parse_currency-python.md`, asserting exact `Decimal` equality **and** `str()` form (so `123` stays `Decimal('123')`, not `Decimal('123.0')`)
- [X] T005 [P] Add the `parse_currency` reject-case unit tests to `biweeklybudget/tests/unit/test_utils.py`, asserting `CurrencyParseError` for every rejecting row: `1 2 3`, `1,23,4.56`, `10,00`, `1,234,`, `,123`, `1.2.3`, `abc`, `''`, `'   '`, `'$'`, `5-`, `-(5)`, `1e5`, `nan`, `inf`, `None`, and a non-string `123`
- [X] T006 [P] Add locale-independence and exactness unit tests to `biweeklybudget/tests/unit/test_utils.py`: with `LOCALE_NAME`/`CURRENCY_CODE` patched to `de_DE`/`EUR`, assert `1.234,56` → `Decimal('1234.56')` and `1,234.56` raises (proves SC-006); and assert `parse_currency('0.1') + parse_currency('0.2') == Decimal('0.3')` (proves FR-007 — no binary float anywhere)

### The interception point

- [X] T007 Add `currency_fields = []` and `decimal_fields = []` class attributes and the `normalize_currency(self, data)` method to `FormHandlerView` in `biweeklybudget/flaskapp/views/formhandlerview.py`, per rules N1–N7 in `contracts/form-handler-normalization.md` — skip absent fields, leave blank/whitespace values untouched, replace parseable values with `str(parse_currency(v))`, accumulate `Invalid amount: "%s"` / `Invalid number: "%s"` errors without short-circuiting
- [X] T008 Wire `normalize_currency()` into `FormHandlerView.post()` in `biweeklybudget/flaskapp/views/formhandlerview.py` so it runs before `validate()` and returns `{'success': False, 'errors': errors}` immediately when it finds any, and wrap the `self.validate(data)` call in the same `try`/`except` that already guards `self.submit(data)` (depends on T007)
- [X] T009 Rewrite `_validate_decimal()` and `_validate_float()` in `biweeklybudget/flaskapp/views/formhandlerview.py` to use `parse_currency()`; **delete** the `assert data[key].startswith('%s' % x)` line from `_validate_float` — that assertion is the entire bare-integer defect. Leave `_validate_int()` untouched; its round-trip assertion is correct for integers (depends on T003)
- [X] T010 Add unit tests for the normalization hook in `biweeklybudget/tests/unit/flaskapp/views/test_formhandlerview.py` using a stub `FormHandlerView` subclass: canonicalization of a good value, blank pass-through, absent-field skip, non-string pass-through, error accumulation across multiple bad fields, and that `validate()` is **not** called when normalization fails (depends on T007, T008)

**Checkpoint**: `tox -e py314` green. Parser and hook exist and are proven; no form uses them yet.

---

## Phase 3: User Story 1 — Thousands separators do not break the app (Priority: P1) 🎯 MVP

**Goal**: `1,234.56` in the Transaction Amount field saves as 1234.56 instead of producing a 500.

**Independent Test**: Open the Add Transaction modal, enter `1,234.56` as Amount with otherwise-valid fields, save, and confirm a `Transaction` row exists with `actual_amount == Decimal('1234.56')` and no error is shown.

- [X] T011 [US1] Declare `currency_fields = ['amount', 'sales_tax']` on `TransactionFormHandler` in `biweeklybudget/flaskapp/views/transactions.py`
- [X] T012 [US1] Override `normalize_currency()` on `TransactionFormHandler` in `biweeklybudget/flaskapp/views/transactions.py` to call `super()` and then normalize the values of the nested `data['budgets']` dict, accumulating failures under `errors['budgets']` — the flat field list cannot reach these, and `validate()` sums them at line 293 (depends on T011)
- [X] T013 [US1] Add acceptance test class `TestTransModalCurrencyNormalization` to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` driving the Add Transaction modal with Amount `1,234.56`, asserting the saved `Transaction.actual_amount == Decimal('1234.56')` and that the response is not a server error (depends on T011)
- [X] T014 [P] [US1] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` covering the remaining accepted formats on the Amount field — `$1,234.56`, ` 1 234.56 `, `(1,234.56)` → `-1234.56` — one submission each (depends on T013)

**Checkpoint**: The reported 500 is gone. SC-001 holds for the Transaction form.

---

## Phase 4: User Story 2 — Bare integers are accepted (Priority: P1)

**Goal**: `123` is accepted wherever `123.0` is accepted today.

**Independent Test**: Enter `123` for Fuel Log Total Cost and `40` for BoM Item Unit Cost; both save rather than returning "Invalid float value".

- [X] T015 [P] [US2] Declare `currency_fields = ['cost_per_gallon', 'total_cost']` and `decimal_fields = ['gallons', 'reported_mpg']` on `FuelLogFormHandler` in `biweeklybudget/flaskapp/views/fuel.py`
- [X] T016 [P] [US2] Declare `currency_fields = ['unit_cost']` on `BoMItemFormHandler` in `biweeklybudget/flaskapp/views/projects.py`
- [X] T017 [P] [US2] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_fuel.py` submitting the Fuel Log modal with whole-number Total Cost `123`, Cost Per Gallon `3`, and Gallons `10`, asserting the saved `FuelFill` values (depends on T015)
- [X] T018 [P] [US2] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_projects.py` submitting the BoM Item modal with Unit Cost `40`, asserting `BoMItem.unit_cost == Decimal('40')` (depends on T016)
- [X] T019 [P] [US2] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` submitting the Transaction modal with a bare-integer Amount `123` (depends on T011)

**Checkpoint**: SC-002 holds — no currency field requires a trailing `.0`.

---

## Phase 5: User Story 4 — Malformed input is rejected clearly (Priority: P1)

**Goal**: Bad input produces a field-level error, no saved record, and no 500 — never a guessed number.

**Independent Test**: Submit `abc` and `1.2.3` as a Transaction Amount; each shows a field error on Amount, creates no row, and returns HTTP 200 with a JSON error body.

> Sequenced after US1/US2 deliberately: rejection is only meaningful once acceptance is wired, and it is the guard against this feature's own worst failure mode — silently mangling an amount.

- [X] T020 [US4] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` submitting Amount `abc`, asserting the Amount field shows `Invalid amount: "abc"`, the form has the `has-error` class, and the `Transaction` count is unchanged (depends on T011)
- [X] T021 [P] [US4] Add acceptance tests to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` for the remaining rejection cases on Amount — `1.2.3`, `10,00`, `1,23,4.56` — each asserting a field error and no new row (depends on T020)
- [X] T022 [P] [US4] (No-op: `grep -rn 'Invalid float value\|Invalid Decimal value' biweeklybudget/` found no assertions on the old wording, so nothing needed changing.) Update every existing acceptance test that asserts on the old `Invalid float value: "..."` or `Invalid Decimal value: "..."` message text to expect the new `Invalid amount:` / `Invalid number:` wording; find them with `grep -rn 'Invalid float value\|Invalid Decimal value' biweeklybudget/` (depends on T009)
- [X] T023 [US4] Add an acceptance test asserting no 500 is produced: post `{'amount': '1,234.56', ...}` directly to `/forms/transaction` with `requests` and assert the status is 200 and the body is JSON, mirroring the existing direct-POST helper usage in `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` (depends on T011)

**Checkpoint**: SC-004 holds. Rejection is as well-pinned as acceptance.

---

## Phase 6: User Story 3 — Every currency input, not just the reported ones (Priority: P2)

**Goal**: The full FR-009 inventory accepts normalized input.

**Independent Test**: Submit a comma-separated value through each remaining form and assert the persisted value.

- [X] T024 [P] [US3] Declare `currency_fields = ['amount', 'sales_tax']` on `SchedTransFormHandler` in `biweeklybudget/flaskapp/views/scheduled.py`
- [X] T025 [P] [US3] Declare `currency_fields = ['amount', 'sales_tax']` on `SchedToTransFormHandler` and `currency_fields = ['amount']` on `SkipSchedTransFormHandler` in `biweeklybudget/flaskapp/views/payperiods.py`
- [X] T026 [P] [US3] Declare `currency_fields = ['starting_balance', 'current_balance']` on `BudgetFormHandler` and `currency_fields = ['amount']` on `BudgetTxfrFormHandler` in `biweeklybudget/flaskapp/views/budgets.py`
- [X] T027 [P] [US3] Declare `currency_fields = ['credit_limit', 'apr', 'prime_rate_margin']` on `AccountFormHandler` and `currency_fields = ['amount']` on `AccountTxfrFormHandler` in `biweeklybudget/flaskapp/views/accounts.py` — all five are blank-allowed, so rule N2 must keep the existing `.strip() != ''` guards working, and `submit()`'s ">1 means percent" rate handling must stay unchanged
- [X] T028 [US3] Declare `currency_fields = ['interest_amt']` on `AccountOfxFormHandler` in `biweeklybudget/flaskapp/views/credit_payoffs.py`
- [X] T029 [US3] Normalize each `increases[]` / `onetimes[]` `amount` in `PayoffSettingsFormHandler.post()` in `biweeklybudget/flaskapp/views/credit_payoffs.py` before the JSON blob is written to `DBSetting`, returning `{'success': False, 'error_message': ...}` for a bad value. This is a plain `MethodView`, so it calls `parse_currency()` directly. Normalizing on write matters because `_payment_settings_dict()` re-parses the blob while *rendering* the credit-payoff page — a bad stored value breaks the whole page (depends on T003)
- [X] T030 [P] [US3] Add acceptance tests for comma-separated input to `biweeklybudget/tests/acceptance/flaskapp/views/test_scheduled.py` and `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` (depends on T024, T025)
- [X] T031 [P] [US3] Add acceptance tests for comma-separated input to `biweeklybudget/tests/acceptance/flaskapp/views/test_budgets.py` and `biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py` (depends on T026, T027)
- [X] T032 [P] [US3] Add acceptance tests for comma-separated input to `biweeklybudget/tests/acceptance/flaskapp/views/test_credit_payoffs.py`, covering both the OFX interest form and the payoff settings form (depends on T028, T029)

**Checkpoint**: SC-003 holds — every FR-009 input has a test that submits a separator-formatted value and asserts the persisted result.

---

## Phase 7: User Story 5 — Client-side agreement (Priority: P2)

**Goal**: In-browser split validation treats `1,234.56` the way the server does, so it stops blocking submissions the server would accept.

**Independent Test**: In the Transaction modal with Budget Split checked, Amount `1,234.56` and one allocation `1,234.56` produce no mismatch error and Save stays enabled.

- [X] T033 [US5] Add `parse_currency(value)` to `biweeklybudget/flaskapp/static/js/custom.js`, directly below `fmt_currency()`, per `contracts/parse_currency-js.md`: derive separators from `Intl.NumberFormat(LOCALE_NAME).formatToParts()`, use the `CURRENCY_SYMBOL` global, mirror the server's accept/reject rules, and return `null` — never `NaN` — for uninterpretable input
- [X] T034 [US5] Replace all four `parseFloat()` calls in `biweeklybudget/flaskapp/static/js/transactions_modal.js` (lines ~265 and ~268 in `validateTransModalSplits()`, ~339 and ~343 in `transModalSplitBudgetChanged()`) with `parse_currency()`, handling `null` explicitly at each site per the table in `contracts/parse_currency-js.md` — skip the remainder auto-fill on `null`, and suppress the mismatch message rather than rendering `NaN` (depends on T033)
- [X] T035 [US5] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py`, alongside the existing `TestTransModalBudgetSplits`, checking Budget Split with Amount `1,234.56` and a matching separator-formatted allocation, asserting `#budget-split-feedback` is empty, `#modalSaveButton` is enabled, and the saved `BudgetTransaction` amounts are correct (depends on T034)
- [X] T036 [P] [US5] Add an acceptance test to `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` for the split remainder auto-fill with a separator-formatted Amount, asserting the auto-filled allocation is the correct remainder and not a truncated one (depends on T034)

**Checkpoint**: All five user stories functional.

---

## Phase 8: Polish & Completion

**Purpose**: Constitution obligations — docs, version, changelog, and the full test gate.

- [X] T037 [P] Document accepted currency input formats in `docs/source/app_usage.rst`, as a subsection of the existing localization content, listing the accepted and rejected forms and noting that conventions follow `LOCALE_NAME`
- [X] T038 [P] Verify `grep -rn "currency_fields\|decimal_fields" biweeklybudget/flaskapp/views/` enumerates the complete FR-009 inventory from `data-model.md`, and that `grep -n parseFloat biweeklybudget/flaskapp/static/js/transactions_modal.js` returns nothing (SC-005)
- [X] T039 Run `tox -e py314` to completion with full output redirected to a scratchpad file; fix every failure and every pycodestyle/pyflakes finding
- [X] T040 Run `tox -e acceptance` to completion with full output redirected to a scratchpad file; fix every failure. A timeout is **not** a pass — raise the `pytest.ini` timeout and the tool timeout and re-run rather than narrowing the selection (constitution II) (depends on T039)
- [X] T041 [P] Run `tox -e migrations` and confirm it passes unchanged — this feature touches no models, so any failure here is a regression (depends on T039)
- [X] T042 Run `tox -e jsdoc` to regenerate `docs/source/jsdoc.custom.rst` for the new JS function and commit the regenerated file (`node` and `jsdoc` are available on this machine) (depends on T033)
- [X] T043 Run `tox -e docs` and confirm it builds clean, including the regenerated `docs/source/biweeklybudget.utils.rst` (depends on T037, T042)
- [X] T044 Bump `VERSION` in `biweeklybudget/version.py` from `1.6.2` to `1.7.0` and add the matching entry to `CHANGES.rst` in the existing format, referencing issue #323 (depends on T039, T040)
- [X] T045 Walk the manual verification table in [quickstart.md](./quickstart.md) against a locally running `flask rundev` instance, confirming all six Transaction-modal rows and the other-form spot checks (depends on T040)
- [X] T046 Update this file and [plan.md](./plan.md) to record completion status, then commit, push the branch to `origin`, and open the pull request (depends on all)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)** → no dependencies
- **Phase 2 (Foundational)** → depends on Phase 1; **BLOCKS every user story**
- **Phase 3 (US1)** → depends on Phase 2. MVP.
- **Phase 4 (US2)** → depends on Phase 2. Independent of US1 except that T019 reuses the Transaction wiring from T011.
- **Phase 5 (US4)** → depends on Phase 2 and on US1/US2 wiring existing, since rejection is asserted through those forms
- **Phase 6 (US3)** → depends on Phase 2 only
- **Phase 7 (US5)** → depends on Phase 2; the browser tests additionally need US1's Transaction wiring
- **Phase 8 (Polish)** → depends on all desired stories

### Critical Path

T003 → T007 → T008 → T011 → T013 → … → T039 → T040 → T044 → T046

T003 (the parser) and T007/T008 (the hook) are the only true bottlenecks. Everything from
Phase 3 onward is wiring and tests over a stable interface.

### Parallel Opportunities

- T004, T005, T006 — three independent test groups over the same new function
- T015–T019 (US2) and T024–T032 (US3) — each touches a different view or test file
- T037, T038, T041 in Phase 8
- Whole phases: US2, US3 and US5 have no dependencies on each other once Phase 2 lands

### Sequential Constraints (same file — do NOT parallelize)

- T007 → T008 → T009 all edit `formhandlerview.py`
- T011 → T012 both edit `transactions.py`
- T013, T014, T019, T020, T021, T023, T035, T036 all append to `test_transactions.py`; write them in ID order
- T033 → T034: `transactions_modal.js` cannot be changed before `custom.js` defines the function

---

## Parallel Example: Phase 2 tests

```bash
# After T003 lands, these three test groups are independent:
Task: "parse_currency accept-case unit tests in biweeklybudget/tests/unit/test_utils.py"
Task: "parse_currency reject-case unit tests in biweeklybudget/tests/unit/test_utils.py"
Task: "parse_currency locale and exactness unit tests in biweeklybudget/tests/unit/test_utils.py"
```

## Parallel Example: Phase 6 handler declarations

```bash
Task: "Declare currency_fields on SchedTransFormHandler in views/scheduled.py"
Task: "Declare currency_fields on the two payperiods handlers in views/payperiods.py"
Task: "Declare currency_fields on the two budgets handlers in views/budgets.py"
Task: "Declare currency_fields on the two accounts handlers in views/accounts.py"
```

---

## Implementation Strategy

### MVP (Phases 1–3)

Setup → Foundational → US1. At that point the reported 500 is fixed and provable. **Stop
and validate** before going further.

### Incremental Delivery

1. Phases 1–2 → parser and hook exist, unit-tested, wired to nothing
2. Phase 3 → US1: the reported crash is gone (MVP)
3. Phase 4 → US2: the second reported defect is gone
4. Phase 5 → US4: rejection pinned, so acceptance cannot silently over-reach
5. Phase 6 → US3: the whole FR-009 inventory
6. Phase 7 → US5: client and server agree
7. Phase 8 → docs, version, changelog, full gate, PR

### Notes

- Commit messages use the constitution's `Currency Value Input Normalization - {Milestone}.{Task}` prefix
- Do not skip T022. The wording change in T009 silently breaks existing acceptance
  assertions, and those failures will otherwise look like feature bugs
- Do not weaken `strict=True` in T003 to make a test pass. Without it, Babel reads `10,00`
  as `1000` — the exact silent-corruption failure this feature exists to prevent


---

## Completion Status

**All 46 tasks complete.** Suites run to completion on 2026-09-06 against
MariaDB 10.4.7 and Chromium:

| Suite | Result |
|-------|--------|
| `tox -e py314` (unit, pycodestyle, pyflakes) | **498 passed**, 0 failed |
| `tox -e acceptance` (Selenium browser tests) | **577 passed**, 24 skipped, 0 failed |
| `tox -e migrations` | **6 passed**, 0 failed (unchanged - no model changes) |
| `tox -e docs` | build succeeded |
| `tox -e jsdoc` | OK; `docs/source/jsdoc.custom.rst` regenerated and committed |
| `tox -e screenshots` | OK |

Notes on execution:

- **T022 was a no-op.** `grep -rn 'Invalid float value\|Invalid Decimal value'`
  found no assertions on the old message wording anywhere in the tree, so the
  rewording in T009 broke nothing.
- **Three parser defects were found and fixed during implementation**, none of which
  the plan anticipated:
  1. Babel's `parse_decimal` falls through to `Decimal()`, which accepts `1e5`,
     `nan` and `inf`. Added an explicit character-class check so only digits and
     the locale's two separators reach the parser.
  2. The JS `endsWith` emulation matched when `lastIndexOf` returned `-1` and the
     token was longer than the string, so `parse_currency('.5')` and `('5.')`
     returned `null` - any input shorter than `'USD'` was corrupted. Fixed with a
     length guard.
  3. The JS parser rejected `.5`, which the server accepts. The client must never
     be stricter than the server or it blocks submissions the server would allow.
- **One test-isolation bug was found by the full suite**, not by the targeted runs:
  `TestCurrencyNormalizationDoesNotChangeExistingBehavior` mutates the database but
  originally lacked the `class_refresh_db` fixture, so a transaction it created
  leaked into `test_fuel.py` and broke a count assertion there. Fixed by adding the
  fixture.
- `tox -e screenshots` regenerates every documentation PNG. Those diffs come from
  the local Chromium's rendering rather than from this change, so they were reverted;
  screenshots belong to the release checklist, not to this feature.
