# Implementation Plan: Balance-less Accounts Must Not Break The Landing Pages

**Branch**: `robot-army/issue-334-active-account-with-no-accountbalance` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260917-075406-balanceless-account-pages/spec.md`

## Summary

An active `Account` with no `AccountBalance` row takes the index page down with an
`UndefinedError` in three table cells that do arithmetic on the missing ledger figure. The
fix is to guard those cells in `index.html` the way `accounts.html` already guards its
equivalents — a `{% set ledger = acct.balance.ledger if acct.balance else None %}` per
table and an `is not none` test on each derived cell — plus the statement guard that stops
a bare `()` rendering beside a blank balance. No Python and no model changes. The Accounts
page half of the issue is already fixed (verified by reproduction, research R3) and gets
acceptance coverage rather than a change.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, Jinja2, SQLAlchemy; jQuery / Bootstrap 3 / DataTables on
the frontend. No dependency is added.

**Storage**: MySQL / MariaDB. No schema change.

**Testing**: pytest; Selenium acceptance tests against a live Flask server
(`biweeklybudget/tests/acceptance/`), with `requests` for plain status-code assertions.

**Target Platform**: Linux, localhost single-operator web application.

**Project Type**: Flask web application, single package.

**Performance Goals**: Unchanged. The guards add no query — `acct.balance` was already
being evaluated on each of these lines, and the `{% set %}` evaluates it once per row where
the template previously evaluated it two or three times, so the credit table issues fewer
queries than before, not more.

**Constraints**: The rendered output for any account that has a balance must be
byte-for-byte what it is today; the existing acceptance tests assert exact cell text and
are the check on that.

**Scale/Scope**: One template, three tables, nine lines changed. One new acceptance test
class. One changelog bullet.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v2.1.2.*

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies | How this change complies |
|---|---|---|
| **I. Spec-Driven Change** | Yes | Spec written and committed before planning; plan before implementation; work is on the feature branch `robot-army/issue-334-active-account-with-no-accountbalance`, created off `master` for this issue. Decomposed into milestones below. |
| **II. The Test Gate** | Yes | Full unit and acceptance suites run to completion and pass before the feature is declared done. New acceptance tests assert real rendered output, and must be confirmed to fail against the unfixed template before the fix is applied, so they are not tests written to pass. Template change is not Python, but the new test code must be pycodestyle/pyflakes clean under `pytest.ini`'s exceptions. |
| **III. Schema Changes Ship With Reversible Migrations** | No | Nothing under `biweeklybudget/models/` is touched. Research R4 chose the template-guard shape over an `Account` property partly for this reason. No migration is created, and the `migrations` environment has nothing new to verify. |
| **IV. Documentation Is Part Of The Change** | Partially | No user-facing behaviour changes for any account that has a balance, and no setting, command, or endpoint is added or renamed, so `README.rst`, `CLAUDE.md` and `docs/source/` have nothing to correct. The `docs` environment must still build. Screenshots are generated from sample data, which this change does not alter. |
| **V. Escalate Instead Of Guessing** | Yes | The issue's one open design call (blank vs. `$0.00`) is not guessed: it is decided by the precedent recorded in `specs/20260917-053603-show-inactive-accounts/research.md` R5 and written down in the spec's Assumptions. The one thing encountered outside the feature — the credit payoff page's pre-existing 500 — is recorded in research R6 and left alone rather than chased. |
| **VI. Changelog Every Change; Release Only On Request** | Yes | One concise bullet under `Unreleased` in `CHANGES.rst`, led by the issue link. `version.py` is not touched, no tag, no release. No new Python file, so no new copyright header is needed. |
| **Financial correctness** (Tech constraints) | Yes | No arithmetic changes. The change decides only whether a figure is displayed, never what it is. The guard deliberately refuses to substitute a zero, so no fabricated number can enter a display or a total. |
| **Stack constraints** | Yes | Jinja template edit in the existing Bootstrap 3 table markup. No frontend stack, dependency, or pattern is introduced. |
| **Test data safety** | Yes | The reproduction and the tests use the disposable `budgettest` database in a throwaway MariaDB container. |

**Result: PASS.** No violations, so the Complexity Tracking table is omitted.

**Post-Phase-1 re-check**: the design artifacts introduce no new files under
`biweeklybudget/models/`, no new dependency, and no new public interface. The table above
stands unchanged.

## Project Structure

### Documentation (this feature)

```text
specs/20260917-075406-balanceless-account-pages/
├── spec.md                      # Feature specification
├── plan.md                      # This file
├── research.md                  # Phase 0 output, from reproduction
├── data-model.md                # Phase 1 output
├── quickstart.md                # Phase 1 output
├── contracts/
│   └── index-page-tables.md     # Phase 1 output: rendered-output contract
├── checklists/
│   └── requirements.md          # Spec quality checklist
└── tasks.md                     # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
biweeklybudget/
├── flaskapp/
│   └── templates/
│       ├── index.html           # CHANGED: guard the balance-derived cells
│       └── accounts.html        # unchanged; already guarded (research R3)
├── models/
│   └── account.py               # unchanged (research R4)
└── tests/
    └── acceptance/flaskapp/views/
        ├── test_index.py        # CHANGED: new TestIndexMissingData class
        └── test_accounts.py     # unchanged; TestAccountsMissingData is the pattern

CHANGES.rst                      # CHANGED: one bullet under Unreleased
```

**Structure Decision**: Existing layout; no new modules or directories. The change is
confined to the one template that carries the defect and the acceptance test file for the
page it renders, mirroring where the equivalent fix for `accounts.html` landed under issue
#276.

## Implementation Approach

### The template change

Each of the three account tables in `index.html` gets the same treatment, identical in form
to `accounts.html:60`, `:104` and `:147`:

1. Introduce `{% set ledger = acct.balance.ledger if acct.balance else None %}` inside the
   row loop, before the balance cell. This collapses both failure routes — no balance row,
   and a balance row with a `NULL` ledger (research R5) — into a single `None`.
2. Print the balance as `{{ ledger|dollars }}`, which renders blank for `None`.
3. Wrap the balance-age span in `{% if acct.ofx_statement %}`, so an account with no
   statement renders no parentheses at all rather than an empty pair.
4. Guard each derived cell with `{% if ledger is not none %}`, adding
   `and acct.credit_limit is not none` on the two credit-table cells that also need the
   limit. A guarded-out cell renders as an empty `<td>`.

The staleness branch inside the age span becomes the class-attribute form
`accounts.html` uses — `class="data_age{% if acct.is_stale %} text-danger{% endif %}"` —
in place of the current `{% if %}…{% else %}…{% endif %}` pair around two whole spans. It
emits byte-identical markup, and is only ever reached when a statement exists;
`Account.is_stale` already returns `False` when there is none.

### The tests

A new `TestIndexMissingData` class in `test_index.py`, modelled on `TestAccountsMissingData`
in `test_accounts.py`: `class_refresh_db` + `refreshdb` + `testflask`, `incremental`, adding
three **active** balance-less accounts in the first test, then asserting `/` and `/accounts`
are both 200 and that each new row's cell text is exactly the blank-celled form. Exact-text
assertions are what hold FR-003 and FR-005; a status-code-only test would pass against a
fix that printed `$0.00`.

Each new test must be seen to fail against the unfixed template before the fix lands
(Principle II: tests that are valid, not tests written to pass).

## Milestones

Human approval is required to advance from one milestone to the next (Principle I).

### M1 — Specification and plan  ✅ complete

1. Spec, quality checklist (**done**, commit `258c5fd`).
2. Research by reproduction, plan, design artifacts (this milestone).

### M2 — Failing tests, then the fix  ✅ complete

1. Add `TestIndexMissingData` to `test_index.py`; run it against the unfixed template and
   record that it fails with the expected `UndefinedError`.
2. Apply the guards to the three tables in `index.html`.
3. Re-run the new class and the existing `TestIndexAccounts` / `TestAccountsMainPage` /
   `TestAccountsMissingData` classes; all pass, and no existing expected cell text changes.

### M3 — Full suites and close-out  ✅ complete through the pull request

1. Run the complete unit suite and the complete acceptance suite to completion; all pass.
2. Build the docs environment.
3. `CHANGES.rst` bullet under `Unreleased`.
4. Update the spec artifacts to record the outcome; commit.
5. Push the branch, open the pull request, and drive CI and reviews to green.

## Risks

- **Silently changing a working row.** The nine edited lines all sit in rows that currently
  render correct figures for every sample account. The existing acceptance tests assert
  those rows' exact text, so a mistake shows up as a failure rather than as a wrong number
  in production. This is the reason the full acceptance suite, not just the new class, is
  the gate.
- **The acceptance suite's known flakes.** *(Did not materialise: the full run was clean on the first attempt.)* Reconcile drag/unignore, fuel log search and the
  Plaid "Uncheck All" tests have missing-wait races unrelated to this change. A failure in
  one of those is re-run in isolation before being attributed to this work — and never
  waved away without re-running.
