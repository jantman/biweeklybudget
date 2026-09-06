# Implementation Plan: Currency Value Input Normalization

**Branch**: `robot-army/issue-323-currency-value-input-normalization` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260906-155913-currency-input-normalization/spec.md`

## Summary

Every currency string a user types is converted to a number in one of ~30 scattered
`Decimal(data['x'])` / `float(data['x'])` calls, and two of those conversions are
defective: unguarded conversion inside `validate()` turns `1,234.56` into a 500, and a
`startswith` round-trip assertion in `_validate_float` rejects `123`.

The fix collapses all of that into **two functions and one interception point**:

- `biweeklybudget.utils.parse_currency()` — the single server-side authority, a pre-clean
  step wrapping `babel.numbers.parse_decimal(..., strict=True)` against
  `settings.LOCALE_NAME` / `settings.CURRENCY_CODE`. Babel is already a dependency and
  already provides this module's `fmt_currency()` counterpart.
- `parse_currency()` in `static/js/custom.js` — the browser mirror, sibling of the
  existing `fmt_currency()`, replacing the four `parseFloat()` calls in
  `transactions_modal.js`.
- `FormHandlerView.post()` — normalizes every field named in a per-handler
  `currency_fields` declaration into canonical form *before* `validate()` runs, so all
  existing downstream conversions keep working untouched.

`validate()` also gets the same `try`/`except` guard `submit()` already has, so no
conversion anywhere can produce a 500 again.

Locale conventions are read from settings on both sides and never hard-coded, so a second
locale is a configuration change (verified: `de_DE` parses `1.234,56` correctly through
the same code path).

## Technical Context

**Language/Version**: Python 3.14; ES5-style browser JavaScript (jQuery 1.x / Bootstrap 3 era)

**Primary Dependencies**: Flask, SQLAlchemy, Babel 2.18.0 (already present — supplies both
`format_currency` and `parse_decimal`). **No new dependencies.**

**Storage**: MySQL/MariaDB. **No schema change** — this feature does not touch
`biweeklybudget/models/`.

**Testing**: pytest (unit, `tox -e py314`); pytest + Selenium (acceptance,
`tox -e acceptance`); pycodestyle + pyflakes enforced in the unit env

**Target Platform**: Localhost Flask web application, single trusted operator

**Project Type**: Web application — Flask backend with server-rendered Jinja2 templates and
jQuery/DataTables frontend, in a single Python package

**Performance Goals**: Not applicable. Parsing runs once per submitted form field; no
measurable budget.

**Constraints**: Amounts must remain exact `Decimal`s end to end — no `float` may enter a
value path (financial correctness). Parsing must reject ambiguous input rather than guess.
No new frontend stack (constitution: jQuery/Bootstrap 3/DataTables only).

**Scale/Scope**: 18 currency inputs across 13 form handlers, 2 new functions, 1 new
`try`/`except`, ~4 `parseFloat` replacements, 1 JSON-settings handler.

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | ✅ PASS | Spec written and committed before planning; work is on feature branch `robot-army/issue-323-currency-value-input-normalization`; plan precedes implementation; decomposed into milestones in `tasks.md`. Single feature, worked alone. |
| **II. The Test Gate** (NON-NEGOTIABLE) | ✅ PASS (gate to enforce at completion) | Plan mandates full `py314` **and** `acceptance` suites run to completion and pass before the feature is declared done. New code is covered by real unit tests over the accept/reject matrix plus browser tests (FR-011). pycodestyle/pyflakes clean is enforced by the `py314` env. No suite may be narrowed; a timeout must be raised, not worked around. |
| **III. Reversible Migrations** | ✅ N/A | No change to `biweeklybudget/models/`, therefore no migration. `tox -e migrations` must still pass unchanged, and is included in the verification milestone as a regression check. |
| **IV. Documentation Is Part Of The Change** | ✅ PASS | `docs/source/app_usage.rst` gains an "accepted input formats" subsection alongside the existing localization docs; `CLAUDE.md` needs no change (no new commands or env vars); `biweeklybudget.utils.rst` regenerates under `tox -e docs`; `jsdoc.custom.rst` regenerates under `tox -e jsdoc`. Both doc envs must build clean. |
| **V. Escalate Instead Of Guessing** | ✅ PASS | The one genuinely ambiguous decision — what to do with malformed grouping like `10,00` — is resolved explicitly and conservatively (reject; see research R-3/R-4) rather than guessed at, and the rejection set is written into the spec and pinned by tests. No side quests. |
| **VI. Versioned, Changelogged Releases** | ✅ PASS | `version.py` 1.6.2 → **1.7.0** (added accepted behavior, backward compatible); matching `CHANGES.rst` entry. No new Python or JS files are created, so no new copyright headers are needed — both new functions land in existing files that already carry the AGPL header. |
| **Tech constraints — stack** | ✅ PASS | No new frontend stack; the JS function is plain ES5 in an existing file, using `Intl` which the app already relies on for `fmt_currency`. |
| **Tech constraints — license** | ✅ PASS | No dependency added. Babel is already in `requirements.txt`. |
| **Tech constraints — financial correctness** | ✅ PASS | This change is squarely in "how amounts are computed" territory, so it ships with tests that pin exact expected `Decimal` values, including a no-float-rounding assertion. Parsing returns `Decimal`, never `float`. |
| **Tech constraints — security posture** | ✅ PASS | Unchanged. No new exposure; parsing is total and raises rather than executing anything. |
| **Tech constraints — test data safety** | ✅ PASS | Acceptance tests use the existing `refreshdb`/`testflask` fixtures and test settings; no real database is touched. |
| **Workflow — milestone approval** | ⚠️ DEVIATION | The constitution requires human approval at each milestone boundary. This session was dispatched to run the lifecycle through to a pull request without interactive approval. Recorded in Complexity Tracking below; the PR is the review gate. |

**Post-Phase-1 re-evaluation**: no gate changed status. The design added no dependency, no
model change, no new file, and no new architectural layer — it removes call sites rather
than adding them. The single deviation is procedural (unattended execution), not
technical.

## Project Structure

### Documentation (this feature)

```text
specs/20260906-155913-currency-input-normalization/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output — root causes, library choice, parse rules
├── data-model.md        # Phase 1 output — value/error shapes and the field inventory
├── quickstart.md        # Phase 1 output — how to run and verify
├── contracts/
│   ├── parse_currency-python.md   # Server-side function contract
│   ├── parse_currency-js.md       # Browser function contract
│   └── form-handler-normalization.md  # FormHandlerView interception contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
biweeklybudget/
├── utils.py                              # MODIFIED: + parse_currency(), + CurrencyParseError
├── version.py                            # MODIFIED: 1.6.2 -> 1.7.0
├── flaskapp/
│   ├── static/js/
│   │   ├── custom.js                     # MODIFIED: + parse_currency() (mirrors utils.py)
│   │   └── transactions_modal.js         # MODIFIED: 4x parseFloat -> parse_currency
│   └── views/
│       ├── formhandlerview.py            # MODIFIED: currency_fields, decimal_fields,
│       │                                 #   normalization in post(), guarded validate(),
│       │                                 #   _validate_decimal/_validate_float rewritten
│       ├── transactions.py               # MODIFIED: declare fields + budgets dict override
│       ├── scheduled.py                  # MODIFIED: declare fields
│       ├── payperiods.py                 # MODIFIED: declare fields (2 handlers)
│       ├── budgets.py                    # MODIFIED: declare fields (2 handlers)
│       ├── accounts.py                   # MODIFIED: declare fields (2 handlers)
│       ├── fuel.py                       # MODIFIED: declare currency + decimal fields
│       ├── projects.py                   # MODIFIED: declare fields
│       └── credit_payoffs.py             # MODIFIED: declare fields; normalize JSON settings
└── tests/
    ├── unit/
    │   ├── test_utils.py                 # MODIFIED: + parse_currency test matrix
    │   └── flaskapp/views/
    │       └── test_formhandlerview.py   # NEW or MODIFIED: normalization hook tests
    └── acceptance/flaskapp/views/
        ├── test_transactions.py          # MODIFIED: + normalization browser tests
        ├── test_budgets.py               # MODIFIED: + normalization browser tests
        ├── test_accounts.py              # MODIFIED: + normalization browser tests
        ├── test_fuel.py                  # MODIFIED: + normalization browser tests
        ├── test_projects.py              # MODIFIED: + normalization browser tests
        ├── test_scheduled.py             # MODIFIED: + normalization browser tests
        ├── test_payperiods.py            # MODIFIED: + normalization browser tests
        └── test_credit_payoffs.py        # MODIFIED: + normalization browser tests

docs/source/app_usage.rst                 # MODIFIED: accepted input formats
docs/source/jsdoc.custom.rst              # REGENERATED by tox -e jsdoc
CHANGES.rst                               # MODIFIED: 1.7.0 entry
```

**Structure Decision**: The existing single-package Flask layout is used as-is. No new
files are created: the server function joins its formatting counterpart in
`biweeklybudget/utils.py`, and the browser function joins *its* counterpart in
`static/js/custom.js`. This is deliberate — `custom.js` is already loaded on every page by
`base.html` and already receives the `LOCALE_NAME` / `CURRENCY_CODE` / `CURRENCY_SYMBOL`
globals, so no new `<script>` tag or template change is needed, and `docs/make_jsdoc.py`
auto-discovers the file.

## Implementation Milestones

Milestone boundaries are where the constitution requires the suites to be green and the
docs updated.

- **M1 — Parsing core.** `parse_currency()` + `CurrencyParseError` in `utils.py`, with the
  full unit-test matrix (accept, reject, locale, exactness). Independently verifiable with
  `tox -e py314`.
- **M2 — Server-side wiring.** `FormHandlerView` normalization hook, guarded `validate()`,
  rewritten `_validate_decimal`/`_validate_float`, `currency_fields` declared on all 13
  handlers, `TransactionFormHandler` budgets override, `PayoffSettingsFormHandler` JSON
  normalization. Delivers Stories 1, 2, 3 and 4 end to end for any client.
- **M3 — Browser wiring.** `parse_currency()` in `custom.js`; `transactions_modal.js`
  switched off `parseFloat`. Delivers Story 5.
- **M4 — Browser tests.** Acceptance coverage across the FR-009 inventory (FR-011, SC-003,
  SC-004).
- **M5 — Completion.** Docs, regenerated jsdoc, version bump, `CHANGES.rst`, full
  `py314` + `acceptance` + `docs` + `jsdoc` + `migrations` suites green, PR opened.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Constitution §Development Workflow step 3 — "Obtain human approval of the plan before implementing, and again at each milestone boundary" is not obtained interactively | This session was dispatched to run `/speckit-specify → /speckit-plan → /speckit-tasks → /speckit-implement` through to an opened pull request without a human in the loop. Stopping at the first milestone boundary would deliver nothing. | Not applicable — the deviation is imposed by how the work was dispatched, not chosen for convenience. It is mitigated rather than removed: every artifact (spec, plan, research, tasks) is committed for review, the full test gate is still enforced before completion, and the pull request stands as the human approval gate before anything merges. |
| `FormHandlerView` gains a declarative `currency_fields` / `decimal_fields` class attribute — a small amount of framework machinery | Without it, normalization must be repeated at ~30 conversion sites across `validate()` and `submit()` in 13 handlers. The issue explicitly asks for normalization "in as few places as possible using specific reused functions/methods", and SC-005 requires a reviewer be able to enumerate every conversion from one function's callers. | Per-call-site normalization was rejected: 30 edits, 30 chances to miss one, and no way to audit completeness. A full form-object/WTForms layer was also rejected as far more machinery than the issue warrants. |
