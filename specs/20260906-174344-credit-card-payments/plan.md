# Implementation Plan: Special Handling of Credit Card Payments

**Branch**: `robot-army/issue-210-special-handling-of-credit-card-payments` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260906-174344-credit-card-payments/spec.md`

## Summary

A payment toward a credit account must have zero impact on any budget or pay period,
because the charges it settles were already budgeted on their own charge dates. Delivering
that requires two layers, since the flag it is supposed to be built on (issue #319) is open
and unimplemented: a general "excluded from budget arithmetic" designation on `Transaction`,
and a "payment toward this credit account" designation that implies it. A third layer gives
the person entering a payment a live breakdown of which pay periods' charges the amount
settles, and an advisory warning when the amount exceeds every unpaid charge the
application has recorded for that card.

The technical approach: two new columns on `transactions` in one reversible migration; a
derived `is_excluded_from_budget` hybrid property that is the only thing arithmetic reads;
a single filter point in `BiweeklyPayPeriod._make_budget_sums()` and one in
`Account.unreconciled_sum`; a new `biweeklybudget/credit_payment.py` module holding the
attribution arithmetic, served to the existing jQuery modal through one new read-only AJAX
endpoint. The netting approach from #210's original proposal is not implemented; the spec
records the arithmetic showing it recreates the double-count one period later.

Every decision, and the code fact behind it, is in [research.md](./research.md).

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask 3.1.3, SQLAlchemy 2.0.52, Alembic 1.19.2, Babel 2.18.0;
jQuery, Bootstrap 3, and DataTables on the front end

**Storage**: MySQL / MariaDB. Schema managed by Alembic; current head `a1b2c3d4e5f6`

**Testing**: pytest. Unit (`tox -e py314`), acceptance via Selenium (`tox -e acceptance`),
migration (`tox -e migrations`, using alembic-verify), docs (`tox -e docs`)

**Target Platform**: Linux; a Flask application served on localhost for a single trusted
operator

**Project Type**: Web application — a single Python package containing models, a Flask app
with server-rendered Jinja templates, and jQuery front-end assets

**Performance Goals**: No throughput target. The one new endpoint is called on keystrokes in
a modal, so its query count must stay bounded — it reads a single account's transactions
once, not per pay period

**Constraints**: MySQL-specific behaviour is used deliberately and must not be traded away.
No new frontend stack. New Python files carry the AGPL v3 header. Currency arithmetic uses
`Decimal` throughout; no `float` anywhere in the money path

**Scale/Scope**: Two schema columns, one migration, one new module, one new endpoint, three
changed endpoints, two changed model files, one changed calculation file, three changed
front-end files, plus settings and documentation. Single-user data volumes

## Constitution Check

*GATE: evaluated before Phase 0, re-evaluated after Phase 1 design. Constitution v1.0.0.*

### I. Spec-Driven Change (NON-NEGOTIABLE)

| Requirement | Status |
|-------------|--------|
| Written specification under `specs/` before implementation | **PASS** — `spec.md`, committed before this plan |
| Planned before implemented, as separate sequential steps | **PASS** — this document, produced and committed before any code |
| Git feature branch named for the feature | **PASS** — `robot-army/issue-210-special-handling-of-credit-card-payments`, created for this issue |
| One feature at a time, through to verification | **PASS** — issue #319 is folded in as Layer 1 because #210 cannot be built without it; #320 and #322 are explicitly out of scope |
| Decomposed into milestones and tasks | **PASS** — five milestones below |
| Human approval to advance between milestones | **DEVIATION** — see Complexity Tracking |

### II. The Test Gate (NON-NEGOTIABLE)

| Requirement | How this plan satisfies it |
|-------------|---------------------------|
| Complete unit and acceptance suites run to completion and pass before done | M5 runs both in full. No milestone is closed on a filtered subset |
| A timed-out suite has not passed; raise both timeouts and re-run | Recorded as the required response in `tasks.md`; narrowing the run is not an option |
| pycodestyle / pyflakes clean under `pytest.ini` exceptions | Every milestone ends with the lint run |
| New code covered by valid tests, not tests written to pass | Each milestone carries its own tests; the arithmetic tests pin explicit expected numbers for both the same-period and cross-period payoff cases, derived from the spec rather than from the implementation's output |
| Migration and Docker suites for schema or packaging changes | This is a schema change: `tox -e migrations` is part of M1 and M5. Packaging is untouched, so the Docker suite is not implicated |

### III. Schema Changes Ship With Reversible Migrations

| Requirement | Status |
|-------------|--------|
| Model change ships with an Alembic migration in the same change | **PASS** — M1 |
| Both `upgrade()` and `downgrade()`, both tested | **PASS** — plus a `test_migration_<rev>.py` following the `d01774fa3ae3` pattern, which exercises forward and reverse |
| Migration column definitions exactly match model definitions | **PASS** — types fixed in research.md D-1 following the `sales_tax` precedent; `tox -e migrations` verifies head against models |
| New model classes imported in `models/__init__.py` | **N/A** — no new model class; two columns on an existing one |
| `initdb` to current head **before** model changes, for autogenerate | **PASS** — first task in M1, called out explicitly because getting it backwards silently yields an empty migration |

### IV. Documentation Is Part Of The Change

| Requirement | Status |
|-------------|--------|
| Documentation updated in the same change | **PASS** — M5: the credit card payment workflow and the no-budget-impact designation in `docs/source/app_usage.rst`, the new setting in `settings_example.py` and the settings documentation, and an autodoc page for `biweeklybudget.credit_payment` |
| `tox -e docs` builds without errors | **PASS** — run in M5 |
| Replace any documented description of the pseudo-transaction workaround | **PASS** — a search of `docs/` and `README.rst` found no existing description of it, so this reduces to writing the new workflow; recorded so the absence is a finding rather than an oversight |

### V. Escalate Instead Of Guessing

**PASS.** Every open question the specification left is resolved in `research.md` with its
rationale and the alternatives rejected. One point where the specification conflicts with
what the surrounding code implies — excluding an uncleared credit card payment from
`Account.unreconciled_sum` makes the "available balance" figure optimistic — is implemented
as specified, recorded in research.md D-5, and raised in the pull request rather than
silently changed or silently obeyed.

### VI. Versioned, Changelogged Releases

| Requirement | Status |
|-------------|--------|
| `version.py` incremented per SemVer for the scope | **PASS** — M5, 1.7.0 → 1.8.0 (backwards-compatible new functionality) |
| Matching `CHANGES.rst` entry in the existing format | **PASS** — M5 |
| AGPL v3 header on new Python files | **PASS** — `biweeklybudget/credit_payment.py` and the new test files |

### Technology & Security Constraints

| Constraint | Status |
|------------|--------|
| Python 3.14; MySQL/MariaDB required | **PASS** — unchanged |
| No parallel frontend stack | **PASS** — existing `FormBuilder`, Bootstrap 3, DataTables only (research.md D-9) |
| AGPLv3-compatible dependencies | **PASS** — no new dependencies |
| Localhost, single trusted operator | **PASS** — the new endpoint is read-only and adds no exposure |
| No committed credentials | **PASS** — the new setting is a date |
| Financial correctness changes ship with tests pinning expected numbers | **PASS** — this is the core of M2 and M4 |
| Acceptance tests never pointed at a real database | **PASS** — existing `testdb` fixture and settings module, unchanged |

**Gate result: PASS**, with one recorded deviation (below).

### Post-Design Re-evaluation

Re-checked after Phase 1. The design adds one Python module, one endpoint, and two columns.
It introduces no new dependency, no new frontend framework, no new model class, and no
second place where budget arithmetic is decided — the exclusion is read from one derived
property and applied at two filter points. Nothing in the design moves any gate from PASS.

## Project Structure

### Documentation (this feature)

```text
specs/20260906-174344-credit-card-payments/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: decisions D-1 .. D-11
├── data-model.md        # Phase 1: schema and derived entities
├── quickstart.md        # Phase 1: how to validate the feature end to end
├── contracts/
│   └── http-api.md      # Phase 1: changed and new HTTP contracts
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks -- NOT created here)
```

### Source Code (repository root)

```text
biweeklybudget/
├── credit_payment.py                          # NEW -- attribution arithmetic
├── settings.py                                # CREDIT_PAYMENT_BEGIN_DATE
├── settings_example.py                        # documented example of the same
├── biweeklypayperiod.py                       # _dict_for_trans, _dict_for_sched_trans,
│                                              #   _make_budget_sums
├── models/
│   ├── transaction.py                         # two columns, relationship disambiguation,
│   │                                          #   is_excluded_from_budget
│   └── account.py                             # unreconciled_sum
├── alembic/versions/
│   └── <rev>_add_transaction_no_budget_impact_and_credit_payment.py   # NEW
├── flaskapp/
│   ├── views/transactions.py                  # form handler, both AJAX views,
│   │                                          #   new CreditPaymentInfoAjax
│   ├── templates/
│   │   ├── transactions.html                  # credit_acct_names_to_id
│   │   └── payperiod.html                     # excluded-transaction marker
│   └── static/js/
│       ├── transactions_modal.js              # form controls + info panel
│       └── transactions.js                    # DataTable marker
└── tests/
    ├── fixtures/test_settings.py              # CREDIT_PAYMENT_BEGIN_DATE
    ├── unit/
    │   ├── test_credit_payment.py             # NEW -- attribution arithmetic
    │   ├── test_biweeklypayperiod.py          # exclusion from sums
    │   └── models/                            # model-level behaviour
    ├── migrations/
    │   └── test_migration_<rev>.py            # NEW
    └── acceptance/
        ├── test_biweeklypayperiod.py          # same-period and cross-period payoff
        └── flaskapp/views/
            ├── test_transactions.py           # modal controls, persistence, warnings
            └── test_payperiods.py             # excluded transactions shown, not counted

docs/source/
├── app_usage.rst                              # the workflow, replacing the workaround
├── biweeklybudget.credit_payment.rst          # NEW autodoc page
├── biweeklybudget.rst                         # add the new module to the toctree
└── biweeklybudget.settings_example.rst        # picks up the new setting automatically

CHANGES.rst                                    # 1.8.0 entry
biweeklybudget/version.py                      # 1.7.0 -> 1.8.0
```

**Structure Decision**: The repository is a single Python package with the Flask application
nested inside it (`biweeklybudget/flaskapp/`) and its front-end assets served from
`flaskapp/static/js/`. This feature adds one module at package top level, beside
`biweeklypayperiod.py` and `interest.py`, which are the existing homes for calculation logic
that is neither a model nor a view. Nothing new is introduced structurally.

## Milestones

Each milestone is a commit-sized unit that leaves the tree green. Commit messages take the
form `Credit Card Payments - M.T` per the constitution's Development Workflow.

### M1 — Schema, model, and settings foundation

Stand up the test database and run `initdb` to the current head **first**, then add the two
columns, the disambiguated relationships, the `is_excluded_from_budget` hybrid, and the
`CREDIT_PAYMENT_BEGIN_DATE` setting; autogenerate and hand-finish the Alembic migration with
both directions; add the migration test.

*Risk concentrated here*: the second foreign key to `accounts.id` breaks the existing
`account` relationship unless it is disambiguated (research.md D-2). This milestone is not
closed until the unit suite imports and passes.

**Gate**: `tox -e py314`, `tox -e migrations`, lint.

### M2 — Exclusion from budget arithmetic

Carry `no_budget_impact` through `_dict_for_trans()` and `_dict_for_sched_trans()`, skip
excluded transactions in `_make_budget_sums()`, and skip them in `Account.unreconciled_sum`.
Unit tests pin the same-period and cross-period payoff arithmetic against numbers taken from
the spec's acceptance scenarios, and assert that an excluded transaction still appears in
`transactions_list`.

**Gate**: `tox -e py314`, lint.

### M3 — Transaction form and transaction lists

Server-side: the credit-account list on both transaction views, the two new fields through
`TransactionFormHandler` validate and submit, the credit-account-type validation, and the
new fields on both transaction AJAX endpoints. Front end: the checkbox and select in the
modal, populating them on edit, and the excluded marker in the `/transactions` DataTable and
the pay period transaction table.

**Gate**: `tox -e py314`, `tox -e acceptance`, lint.

### M4 — Payment attribution and warnings

`biweeklybudget/credit_payment.py` implementing the algorithm in research.md D-7, the
`GET /ajax/credit-payment-info` endpoint, and the modal's live info panel. Unit tests cover
the arithmetic — including the tracking-window boundary, self-exclusion when editing, and
the over-payment and self-payment warnings — and acceptance tests cover the panel.

**Gate**: `tox -e py314`, `tox -e acceptance`, lint.

### M5 — Documentation, version, changelog, and the full gate

The workflow documentation in `app_usage.rst`, the settings documentation, the autodoc page,
the `CHANGES.rst` entry, and the version bump to 1.8.0. Then the complete suites, run to
completion: unit, acceptance, migrations, and docs.

**Gate**: `tox -e py314`, `tox -e acceptance`, `tox -e migrations`, `tox -e docs`, lint.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle I: advancing between milestones without human approval at each boundary | The session was dispatched with explicit standing instruction to run the lifecycle through implementation, commit, push, open a pull request, and iterate on review feedback autonomously. That instruction comes from the same person whose approval the principle protects, and it covers the whole of this feature | Halting at each of five milestone boundaries would leave the work unfinished against an explicit instruction to complete it. The protection the principle exists for is preserved by the pull request: nothing merges without human review, and the milestone structure and its gates are kept intact so the review can follow the work milestone by milestone |
| Two new columns rather than issue #319's one | #210 cannot be delivered without #319's flag, and #319 is open and unimplemented. Building only the general flag would leave the credit-card layer — the actual subject of this issue — undelivered; building only a credit-payment column would leave #319's non-credit-card cases (statement credits, cash-back redemptions, balance-reconcile adjustments) with no way to be expressed | A single column cannot carry both facts: which credit account is paid, and whether the user independently marked a transaction as having no budget impact. Collapsing them makes FR-014 unimplementable (research.md D-3) |
| A new top-level module for arithmetic that one endpoint calls | Financial arithmetic must be unit-testable with pinned numbers, and the spec commits this calculation to being the shared foundation for issue #322 rather than something #322 reimplements | Inlining it in the view handler makes it reachable only through Selenium, and guarantees the duplicate implementation the spec set out to avoid |
