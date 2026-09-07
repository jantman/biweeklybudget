# Implementation Plan: Per-Account Transaction Totals Per Pay Period

**Branch**: `robot-army/issue-213-per-account-txn-total-on-each-period` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260907-091447-per-account-period-totals/spec.md`

## Summary

Add a per-account transaction totals table to the single pay period view. Accounts are rows;
the five pay periods the page already displays in its "Remaining Balances" table are columns.

The numbers come from a new `BiweeklyPayPeriod.account_sums` property, built by summing the
existing `transactions_list` by `account_id` — the same list the page's Transactions table
renders — so every cell is verifiable by adding up rows on screen. No new query, no new
endpoint, no schema change. The view is adjusted to bind its five pay period objects to local
names so that reading both `overall_sums` and `account_sums` from each computes each period's
data exactly once, leaving the page's database cost unchanged.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, Jinja2 (server side); Bootstrap 3, jQuery (client
side). No new dependency is added.

**Storage**: MySQL/MariaDB. **No schema change** — all required data already exists.

**Testing**: pytest. Unit tests (`biweeklybudget/tests/unit/`, `Mock(spec_set=Session)`, no
database) and Selenium acceptance tests (`biweeklybudget/tests/acceptance/`, real database
loaded from fixtures). pycodestyle and pyflakes under the exceptions in `pytest.ini`.

**Target Platform**: Linux; the Flask app served on localhost for a single trusted operator.

**Project Type**: Server-rendered web application (single project, existing layout).

**Performance Goals**: No additional database round trips versus the current page (SC-005). The
per-account sums are a single pass over data the request already holds in memory.

**Constraints**: Must not alter any existing number or behaviour on the pay period view
(FR-014). Must follow the existing Bootstrap 3 / server-rendered table pattern rather than
introducing a new frontend approach.

**Scale/Scope**: One new property (~35 lines) plus its docstring on `BiweeklyPayPeriod`, ~25
lines in `PayPeriodView.get()`, one new ~45-line table in one template, tests, and
documentation. Realistic data volume is tens of accounts and hundreds of transactions per
period.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — see below.*

| Principle | Gate | Status |
|-----------|------|--------|
| **I. Spec-Driven Change** | Written spec under `specs/` before planning; planning before implementation; work on a feature branch named for the feature; decomposed into milestones and tasks. | **PASS.** `spec.md` committed as `Per-Account Period Totals - Spec` before this plan. Branch `robot-army/issue-213-per-account-txn-total-on-each-period`. Milestones defined below; `/speckit-tasks` decomposes them. One feature at a time — nothing else is in flight on this branch. |
| **II. The Test Gate** | Full unit and acceptance suites run to completion and pass before the feature is declared done; pycodestyle/pyflakes clean; new code covered by valid tests. | **PASS by construction.** M4 runs both suites to completion. New arithmetic gets unit tests that pin expected numbers, and the rendered table gets acceptance tests. A timed-out suite counts as a failure and its timeout is raised and re-run. |
| **III. Schema Changes Ship With Reversible Migrations** | Any change under `biweeklybudget/models/` ships with an up-and-down-tested Alembic migration. | **NOT ENGAGED.** No file under `biweeklybudget/models/` is touched; see research R9. The `migrations` tox environment is therefore not required by this change, though it must not be broken by it. |
| **IV. Documentation Is Part Of The Change** | `README.rst`, `CLAUDE.md` and `docs/source/` updated in the same change; the `docs` tox environment builds cleanly. | **PASS.** M3 updates `docs/source/app_usage.rst` (what the table means, and why it deliberately disagrees with the budget totals) and the `docs/source/screenshots.rst` caption for the single pay period view. `docs` env is run in M4. `README.rst` and `CLAUDE.md` need no change: neither documents the contents of this view. |
| **V. Escalate Instead Of Guessing** | Stop and ask when the path is unclear or a significant uncalled-for decision arises. | **PASS with a recorded judgement.** The one genuine ambiguity — "for each payperiod" — is resolved in the spec's Assumptions with a reading that is a strict superset of the alternative and costs nothing, so no interpretation is foreclosed. It is called out again in the pull request for the author to overrule. Nothing else in the issue is ambiguous. |
| **VI. Versioned, Changelogged Releases** | `version.py` bumped per SemVer; matching `CHANGES.rst` entry; AGPL header on new Python files. | **PASS.** M5 bumps `1.8.0` → `1.9.0` (a new user-visible, backwards-compatible feature) and adds the `CHANGES.rst` entry. No new Python file is created, so no new copyright header is needed; the existing headers on edited files are left intact. |
| **Technology & Security Constraints** | Existing stack; no dependency added; no weakening of the localhost-only posture; financial changes pinned by tests. | **PASS.** Bootstrap 3 table in the existing pattern; zero new dependencies; read-only display, no new endpoint, no new input, so no new attack surface; the new arithmetic is pinned by unit tests with literal expected amounts. |

**Result: PASS. No violations, so the Complexity Tracking table below is empty.**

### Deviation recorded under Principle I

The constitution requires human approval to advance between milestones. This session was
dispatched to run the specify → plan → tasks → implement lifecycle through to opening a pull
request without intermediate check-ins. Approval is therefore sought once, on the pull request,
covering the whole feature, rather than at each milestone boundary. The milestone structure is
retained so that review can proceed milestone by milestone against commits that map to it. This
is a deviation in *when* approval happens, not in *whether* it happens, and it is stated in the
pull request body as the constitution's Governance section requires of any deviation.

## Project Structure

### Documentation (this feature)

```text
specs/20260907-091447-per-account-period-totals/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── account-sums.md  # Phase 1 output: property + rendered-table contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
biweeklybudget/
├── biweeklypayperiod.py                       # + account_sums property, + _make_account_sums()
├── flaskapp/
│   ├── views/payperiods.py                    # PayPeriodView.get(): bind 5 periods, pass acct sums
│   └── templates/payperiod.html               # + per-account totals table (id="pp-acct-table")
└── tests/
    ├── unit/test_biweeklypayperiod.py         # + TestAccountSums, TestMakeAccountSums;
    │                                          #   update TestData::test_initial for the new key
    └── acceptance/flaskapp/views/
        └── test_payperiods.py                 # + rendered-table assertions

docs/source/
├── app_usage.rst                              # + what the table means and why it differs
└── screenshots.rst                            # + caption mentions per-account totals

CHANGES.rst                                    # + 1.9.0 entry
biweeklybudget/version.py                      # 1.8.0 -> 1.9.0
```

**Structure Decision**: The existing single-project layout is used unchanged. This feature is a
read-only addition to one existing view backed by one new property on an existing class; it
introduces no new module, package or directory.

## Milestones

Commits use the constitution's prefix form `Per-Account Period Totals - M{n}.{t}`.

### M1 — Backend: `BiweeklyPayPeriod.account_sums`

Add `_make_account_sums()` and the `account_sums` property, wire the result into `_data_cache`,
and unit test the arithmetic. Delivers FR-004, FR-013 and, for the arithmetic, FR-005.
Independently verifiable: `pytest biweeklybudget/tests/unit/test_biweeklypayperiod.py` passes
with the new tests, and no page has changed.

### M2 — Frontend: the table on the pay period view

Bind the five pay period objects in `PayPeriodView.get()`, pass their account sums to the
template, and render the table. Delivers FR-001, FR-002, FR-003, FR-006 through FR-012 and
FR-014. Independently verifiable through the acceptance tests for the rendered table.

### M3 — Documentation

`docs/source/app_usage.rst` and `docs/source/screenshots.rst`. Delivers Principle IV.

### M4 — Full verification

Run unit, acceptance and docs suites to completion, plus the migrations suite to demonstrate
this change did not disturb it. Everything passes; no narrowing, no timeouts reported as green.

### M5 — Release bookkeeping

Version bump and `CHANGES.rst` entry, then push and open the pull request.

## Post-Design Constitution Re-Check

Re-evaluated after producing `research.md`, `data-model.md`, `contracts/account-sums.md` and
`quickstart.md`:

- No design decision introduced a model change, so **III** remains not engaged.
- No design decision introduced a new dependency, endpoint, setting or stored value, so the
  **Technology & Security Constraints** verdict is unchanged.
- The decision in research R5 to have `account_sums` omit accounts with no activity, and to let
  the view supply zeros for the periods on screen, keeps the financial arithmetic inside one
  unit-testable method and out of the template — strengthening compliance with **II**.
- The decision in research R4 to bind the five period objects touches existing view code, which
  is the one place this feature could plausibly violate **FR-014**. It is covered by the existing
  acceptance tests for the "Remaining Balances" table and the summary tiles, which assert the
  exact values that code produces and must continue to pass untouched.

**Result: PASS.** No new violations. Complexity Tracking remains empty.

## Complexity Tracking

No constitutional violations require justification; this table is intentionally empty.
