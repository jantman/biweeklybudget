# Implementation Plan: Cash Position Page

**Branch**: `robot-army/issue-321-add-a-cash-position-page-showing-the` | **Date**: 2026-09-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260908-155554-cash-position-page/spec.md`

## Summary

Add a `/cash-position` page that lays the available-funds calculation out as a
waterfall: itemized budget-funding account balances, the unreconciled
adjustment that turns ledger into projected, credit account balances applied
with their recorded sign, a **Net liquid position** subtotal, then standing
budgets and the current pay period's allocated-but-unspent, giving **Truly
unallocated / uncommitted funds**.

The arithmetic moves out of `flaskapp/notifications.py` into a new
`biweeklybudget/cashposition.py`, which both the page and the existing banner
consume, so the two cannot disagree (FR-004, FR-005). A new many-to-many
`budget_accounts` association records which accounts hold a standing budget's
money; the page uses it to name budget-funding accounts that nothing allocates
and to report balance deltas over *coverage groups* — the maximal sets of
accounts and budgets reachable through the links — because a many-to-many
association records no split of a budget's balance across its accounts.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask 3.x, SQLAlchemy 2.x, Alembic, Jinja2. Frontend:
jQuery, Bootstrap 3, Font Awesome 4, the bundled SB Admin 2 theme. **No new
runtime dependency is added.**

**Storage**: MySQL / MariaDB. One new table, `budget_accounts`.

**Testing**: pytest. `tox -e py314` (unit), `tox -e acceptance` (Selenium),
`tox -e migrations` (alembic-verify + per-revision tests), `tox -e docs`,
`tox -e jsdoc`. Markers per `pytest.ini`.

**Target Platform**: Linux, single-operator localhost web application.

**Project Type**: Server-rendered Flask web application with a jQuery frontend.

**Performance Goals**: None beyond "does not make page loads noticeably
slower". The waterfall's inputs are already computed on every page load for
the banner; consolidating them removes duplicate queries rather than adding
them.

**Constraints**: Bootstrap 3 / jQuery / DataTables only — no parallel frontend
stack (constitution, Technology Constraints). AGPLv3-compatible dependencies
only. Existing `NotificationsController` public methods must keep working.

**Scale/Scope**: Tens of accounts and budgets. One new page, one new module,
one new model module, one new migration, one new template, edits to the budget
modal, the nav, the notification banner, and the docs.

## Constitution Check

*Gate evaluated against `.specify/memory/constitution.md` v1.0.0.*

### Pre-Phase 0

| Principle | Status | How this plan satisfies it |
|---|---|---|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | PASS | Spec written and validated first (`spec.md`, `checklists/requirements.md`), planned here before any code, on a feature branch. Decomposed into five milestones below. Per-milestone human approval is addressed in the note under this table. |
| **II. The Test Gate** (NON-NEGOTIABLE) | PASS (planned) | M5 runs unit, acceptance, migrations, docs and jsdoc suites to completion. Every milestone lands its own tests. New code is pycodestyle/pyflakes clean under `pytest.ini`'s exceptions. |
| **III. Reversible Migrations** | PASS (planned) | The `budget_accounts` table ships with an Alembic migration implementing both `upgrade()` and `downgrade()`, a per-revision test, and the new model module imported in `models/__init__.py`. The test database is initialized to the current head (`f9df90273cdd`) *before* the model change so autogenerate sees a real diff. |
| **IV. Documentation Is Part Of The Change** | PASS (planned) | `docs/source/app_usage.rst` gains a Cash Position section; three new API stubs are added and referenced; screenshots updated. `tox -e docs` must build clean. |
| **V. Escalate Instead Of Guessing** | PASS | Both open questions were escalated during `/speckit-specify` and answered by the repository owner; the answers and their consequences are recorded in the spec's Clarifications section and in [research.md](./research.md) R2/R3. Nothing was guessed. |
| **VI. Versioned, Changelogged Releases** | PASS (planned) | M5 bumps `version.py` 1.11.1 → 1.12.0 and adds a `CHANGES.rst` entry. New Python files carry the standard AGPL v3 header. |
| **Financial correctness** | PASS (planned) | FR-004 is enforced by a test asserting the page's final figure equals the banner's discrepancy. Unit tests pin *signed* values including a credit account in credit and a standing budget with a negative balance. |
| **Security posture** | PASS | Read-only page, no new external exposure, no new secret, no new setting. |
| **Test data safety** | PASS | Acceptance tests use the existing `refreshdb`/`testflask` fixtures against the test database only. |

**Note on per-milestone approval (Principle I)**: the constitution requires
human approval to advance between milestones. The instruction that dispatched
this session explicitly directs implementation to run to completion — commit,
push, open a pull request, monitor CI, and answer reviews. That is the
approval, given in advance for the whole run, and it is recorded here rather
than assumed. Every other milestone-close obligation still applies at each
boundary: suites green, docs updated, spec artifacts updated, committed
together.

### Post-Phase 1 re-check

Re-evaluated after [data-model.md](./data-model.md),
[contracts/](./contracts/) and [quickstart.md](./quickstart.md) were written.
**No principle moves to FAIL and no new violation appears.** Two points the
design surfaced, both resolved within the rules rather than around them:

1. Refactoring `NotificationsController` to delegate to `CashPosition` touches
   code covered by tests added a day earlier under #320. Principle II is
   satisfied by *keeping* those methods and their tests — they become parity
   tests for the delegation — rather than deleting tests that would otherwise
   fail. See [research.md](./research.md) R1.
2. `Budget.as_dict` is derived from `vars(self)`, so exposing linked account
   IDs to the modal needs an explicit `_dict_properties` entry rather than a
   relationship that may or may not be loaded. Recorded in
   [data-model.md](./data-model.md); no principle implicated.

**Complexity Tracking**: not required — no violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/20260908-155554-cash-position-page/
├── plan.md                        # This file
├── spec.md                        # /speckit-specify output
├── research.md                    # Phase 0 output
├── data-model.md                  # Phase 1 output
├── quickstart.md                  # Phase 1 output
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── cash-position-statement.md # The shared calculation's contract
│   └── cash-position-page.md      # The rendered page's DOM contract
└── tasks.md                       # /speckit-tasks output (not created here)
```

### Source Code (repository root)

```text
biweeklybudget/
├── cashposition.py                        # NEW - the shared calculation
├── version.py                             # EDIT - 1.11.1 -> 1.12.0
├── models/
│   ├── __init__.py                        # EDIT - import the new module
│   ├── budget_account_link.py             # NEW - budget_accounts table
│   ├── budget_model.py                    # EDIT - accounts relationship,
│   │                                      #        _dict_properties
│   └── account.py                         # EDIT - budgets backref
├── alembic/versions/
│   └── <rev>_add_budget_accounts_table.py # NEW - up + down
├── flaskapp/
│   ├── notifications.py                   # EDIT - delegate to CashPosition,
│   │                                      #        add Cash Position link
│   ├── views/
│   │   ├── cashposition.py                # NEW - CashPositionView
│   │   └── budgets.py                     # EDIT - links in form + ajax
│   ├── templates/
│   │   ├── cash-position.html             # NEW
│   │   ├── nav.html                       # EDIT - new entry
│   │   └── budgets.html                   # EDIT - accounts JS global
│   └── static/js/
│       └── budgets_modal.js               # EDIT - link checkboxes
└── tests/
    ├── fixtures/sampledata.py             # EDIT - sample links
    ├── unit/
    │   ├── test_cashposition.py           # NEW
    │   └── flaskapp/test_notifications.py # EDIT - parity tests
    ├── migrations/test_migration_<rev>.py # NEW
    └── acceptance/flaskapp/views/
        ├── test_cash_position.py          # NEW
        ├── test_base_template.py          # EDIT - nav list, banner link
        └── test_budgets.py                # EDIT - modal checkboxes

docs/source/
├── app_usage.rst                                   # EDIT - new section
├── screenshots.rst                                 # EDIT
├── biweeklybudget.rst                              # EDIT - toctree
├── biweeklybudget.models.rst                       # EDIT - toctree
├── biweeklybudget.flaskapp.views.rst               # EDIT - toctree
├── biweeklybudget.cashposition.rst                 # NEW
├── biweeklybudget.models.budget_account_link.rst   # NEW
└── biweeklybudget.flaskapp.views.cashposition.rst  # NEW

docs/make_screenshots.py                            # EDIT - new page
CHANGES.rst                                         # EDIT - 1.12.0 entry
```

**Structure Decision**: This is an established single-package Flask
application; the feature follows its existing layout exactly. Domain
arithmetic goes beside `biweeklypayperiod.py` at the package root, the view
goes in `flaskapp/views/`, the model in `models/`, and each gets the matching
test file in the suite that covers its layer. No new directory, no new
package, no new dependency.

## Milestones

Ordered so that each one is independently verifiable and leaves the
application working. The spec's user stories map onto M3 (P1 and P2) and M4
(P3).

### M1 — Schema and model

`budget_accounts` association table, `Budget.accounts` / `Account.budgets`
relationships, `models/__init__.py` import, Alembic migration with tested
`upgrade()` and `downgrade()`, and the per-revision migration test. No UI, no
behaviour change. **Done when** `tox -e migrations` passes and `tox -e py314`
is unaffected.

### M2 — The shared calculation

`biweeklybudget/cashposition.py` producing the whole statement;
`NotificationsController` refactored to delegate; unit tests pinning every
term, both subtotals, the final figure, coverage grouping, and the
sign/None/empty cases. **Done when** `tox -e py314` passes with the new tests
and the pre-existing notification tests still pass unchanged.

### M3 — The page (spec user stories P1 and P2)

`CashPositionView`, `cash-position.html`, nav entry, the banner's new link,
and acceptance tests for the waterfall, the itemizations, the totals and the
links. **Done when** `tox -e acceptance` passes, including the updated nav
assertion.

### M4 — Diagnostics and link editing (spec user story P3)

Unlinked-account call-out, coverage-group deltas, the budget modal's link
checkboxes, `BudgetFormHandler` and `BudgetAjax` changes, sample data, and
acceptance tests for all of it. **Done when** `tox -e acceptance` and
`tox -e py314` pass.

### M5 — Documentation, version, and the full gate

`app_usage.rst`, the API stubs, screenshots, `version.py` → 1.12.0,
`CHANGES.rst`, and the spec artifacts updated to record what was built.
**Done when** unit, acceptance, migrations, docs, jsdoc and docker suites have
all run to completion and passed (constitution II).

---

## Outcome

All five milestones complete. See the Implementation Record in
[spec.md](./spec.md) for what was decided during implementation and why,
including the one place the plan was wrong: `CashPosition` computes its terms
lazily rather than eagerly, because eager construction broke existing unit
tests that pass a mock session, and because the banner reads five figures and
should not pay for the rest.

The Constitution Check above stands as written. No principle moved to FAIL
during implementation and no violation needed justifying.
