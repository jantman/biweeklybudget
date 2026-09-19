# Implementation Plan: Exclude Inactive Accounts From Dropdowns And The Balances Chart

**Branch**: `robot-army/issue-356-inactive-accounts-are-still-offered-in` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260919-150901-inactive-accounts-excluded/spec.md`

## Summary

Inactive Accounts are offered in every account picker and plotted on the dashboard's
Account Balances chart, because eleven view methods build the same unfiltered
`{a.name: a.id for a in db_session.query(Account).all()}` map and the chart view builds
the same unfiltered `{x.id: x.name}` map.

The fix is in three parts:

1. **One place for the filter.** Add `Account.active_accounts(db)`, mirroring the existing
   `Account.active_credit_accounts(db)`, and build every active-only map from it.
2. **A second template variable.** Ship `active_acct_names_to_id` to the pages that host
   account *pickers*, and keep `acct_names_to_id` only on the three pages whose scripts
   filter a table of existing rows. Each entry-form select switches to the active map.
3. **Keep an existing record's account.** The three modals that open on an existing record
   append an option for that record's own Account when it is not in the active list, using
   the `account_name` both AJAX endpoints already return — the same move
   `transModalDivFillAndShow()` already makes for a deactivated credit-payment account.

The chart excludes inactive Accounts by filtering the one `accounts` dict everything else
derives from, and skipping balance rows for accounts not in it.

No model column, no migration, no schema or packaging change.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, Jinja2 (backend); jQuery, Bootstrap 3,
DataTables, Chart.js (frontend). No new dependency.

**Storage**: MySQL/MariaDB. No schema change; no data is written, altered or deleted.

**Testing**: pytest — unit (`biweeklybudget/tests/unit/`) and Selenium acceptance
(`biweeklybudget/tests/acceptance/`), run via `tox -e py314` and `tox -e acceptance`.

**Target Platform**: Flask web app on localhost, single trusted operator.

**Project Type**: Web application — Flask views and Jinja templates serving jQuery
frontend code from `biweeklybudget/flaskapp/static/js/`.

**Performance Goals**: Unchanged. The chart endpoint reads exactly the rows it reads
today; the account queries gain a `WHERE is_active` and stay bounded by account count.

**Constraints**: The chart response shape (`{'data': [...], 'keys': [...]}`) is read by
external scripts and must not change (FR-003). An existing record's Account must survive
an edit (FR-011). The Accounts page must keep listing inactive Accounts (FR-013).

**Scale/Scope**: 1 model method, 10 view methods across 7 modules, 9 templates, 6
JavaScript files, ~21 existing acceptance assertions updated, 3 new test classes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Constitution
v2.1.2.

| Principle | Status | How this plan satisfies it |
|---|---|---|
| **I. Spec-Driven Change** | PASS | Spec written and committed before this plan (`M0.1`); this plan precedes implementation; work is on the feature branch `robot-army/issue-356-inactive-accounts-are-still-offered-in`; decomposed into milestones M1–M3 below. |
| **II. The Test Gate** | PASS | Full unit and acceptance suites run to completion before the feature is declared done (M3). Existing assertions are updated to the new intended behaviour, not weakened — and two of the twenty-two deliberately do *not* change (R6), which is the evidence. New behaviour gets new tests: a unit test for `Account.active_accounts`, an endpoint test for the chart exclusion, and an acceptance class for the inactive-account-on-an-existing-record case modelled on `TestTransModalDoesNotShowInactiveBudgets`. pycodestyle/pyflakes clean. |
| **III. Reversible Migrations** | N/A | Nothing under `biweeklybudget/models/` changes structurally: `Account` gains a static query method, no column, table or relationship. No migration is required, and the `migrations` suite is therefore not in scope (R7). |
| **IV. Documentation** | PASS | `CHANGES.rst` entry under `Unreleased` (M3). `tox -e docs` must build clean. The dashboard `index` screenshot shows the Account Balances chart and will lose the `DisabledBank` series, so it is regenerated and committed (M3), per the maintainer's standing preference that screenshot changes ship in the PR. No `README.rst` or `CLAUDE.md` change is implied — neither documents dropdown contents. |
| **V. Escalate Instead Of Guessing** | PASS | The one genuinely open question in the issue — the scope of the five additional views it flagged but did not confirm — is resolved by an explicit, stated rule (pick-for-a-record vs. filter-existing-rows) recorded in the spec's Assumptions so it can be rejected in review, rather than silently. |
| **VI. Changelog; No Release** | PASS | One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link. `version.py` untouched; no tag, no release. |
| **Financial correctness** | PASS | No pay-period, budget, interest or payoff arithmetic is touched. The chart's *values* are unchanged for every account that remains; only the set of plotted accounts narrows, and the date set is deliberately preserved (R4). |
| **Security posture / Secrets** | N/A | No change to either. |
| **Test data safety** | PASS | Acceptance tests use the existing test database fixtures; no change to how they are pointed. |

**Result: PASS, no violations.** Complexity Tracking is therefore empty and omitted.

**Post-Phase-1 re-check**: PASS, unchanged. The Phase 1 design adds no new abstraction
beyond the single model method justified in R3, introduces no dependency, and touches no
model column — every gate above holds as written.

## Project Structure

### Documentation (this feature)

```text
specs/20260919-150901-inactive-accounts-excluded/
├── spec.md              # Phase -1: the specification
├── plan.md              # This file
├── research.md          # Phase 0: R1-R7, the implementation decisions
├── data-model.md        # Phase 1: entities touched (none structurally)
├── quickstart.md        # Phase 1: how to verify this end to end
├── contracts/
│   ├── account-balances-chart.md   # the chart endpoint's contract
│   └── template-account-maps.md    # which page gets which account map
├── checklists/
│   └── requirements.md  # spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
biweeklybudget/
├── models/
│   └── account.py                      # + Account.active_accounts(db)
├── flaskapp/
│   ├── views/
│   │   ├── index.py                    # IndexView: active map; AcctBalanaceChartView: filter
│   │   ├── accounts.py                 # AccountsView: active map
│   │   ├── budgets.py                  # BudgetsView, OneBudgetView: active map
│   │   ├── transactions.py             # TransactionsView, OneTransactionView: + active map
│   │   ├── scheduled.py                # ScheduledView, OneScheduledView: active map
│   │   ├── reconcile.py                # ReconcileView: + active map
│   │   ├── fuel.py                     # FuelView: active map
│   │   └── payperiods.py               # PayPeriodView: active map
│   ├── templates/
│   │   ├── index.html, accounts.html, budgets.html, fuel.html,
│   │   ├── scheduled.html, payperiod.html      # acct_names_to_id -> active_acct_names_to_id
│   │   ├── reconcile.html, transactions.html   # both maps
│   │   └── ofx.html                            # unchanged (filter only)
│   └── static/js/
│       ├── account_transfer_modal.js   # from/to selects -> active map
│       ├── budget_transfer_modal.js    # account select -> active map
│       ├── fuel.js                     # account select -> active map
│       ├── transactions_modal.js       # active map + re-add record's account
│       ├── scheduled_modal.js          # active map + re-add record's account
│       └── payperiod_modal.js          # active map + re-add record's account
└── tests/
    ├── unit/models/test_account.py             # Account.active_accounts
    └── acceptance/flaskapp/views/
        ├── test_index.py, test_accounts.py, test_budgets.py,
        ├── test_transactions.py, test_scheduled.py, test_fuel.py,
        └── test_payperiods.py                  # updated + new assertions
```

**Structure Decision**: The existing Flask application layout is used unchanged. This is
a behavioural fix distributed across the view/template/JS layers that already exist; it
introduces no new module, package or directory. The only new *code* location is a static
method on the existing `Account` model, justified in R3.

## Milestones

Work is decomposed into three milestones, each independently testable and each ending in
a green run of the suites it affects.

### M1 — The chart stops plotting inactive Accounts

Delivers User Story 1 (FR-001 to FR-004). `Account.active_accounts()` plus the
`AcctBalanaceChartView` change, its unit test, and the updated/added endpoint tests.
Independently verifiable: the chart endpoint's `keys` no longer contain `DisabledBank`
while every other account's data is byte-identical.

### M2 — Account pickers offer only active Accounts, without losing an existing record's

Delivers User Stories 2, 3 and 4 (FR-005 to FR-015). Views, templates and JavaScript
together, because splitting "narrow the list" from "keep the record's own value" across
milestones would leave the tree in a state that silently retargets records (US3's "why
this priority"). Includes the twenty updated assertions, the two deliberately unchanged
ones, and the new acceptance coverage for an existing record on an inactive Account.

### M3 — Close the feature

Full unit and acceptance suites to completion; `tox -e docs` clean; the regenerated
`index` screenshot; the `CHANGES.rst` entry under `Unreleased`; spec artifacts updated to
record the outcome. Then push and open the pull request.
