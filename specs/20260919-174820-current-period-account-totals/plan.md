# Implementation Plan: Current-Period Per-Account Transaction Totals

**Branch**: `robot-army/issue-355-pay-period-per-account-transaction` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260919-174820-current-period-account-totals/spec.md`

## Summary

Reduce the pay period view's **Per-Account Transaction Totals** panel to the period
actually being viewed, and transpose it so accounts run across the top and a single row
of amounts runs beneath, ending in a grand total.

The data this table renders already exists per-period:
`BiweeklyPayPeriod.account_sums` gives one `{name, total}` per account for one period,
and is unchanged by this feature. All that is removed is the layer above it —
`build_account_period_sums()`, which unioned five periods' accounts into rows of five
totals — and the template that laid those rows out. It becomes `build_account_sums()`,
taking one period and returning the accounts as an ordered list of columns plus the sum
across them, rendered as one header row and one data row.

No model, schema, query or arithmetic changes. This is a presentation change over data
already computed, plus the tests and prose that describe the old shape.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, Jinja2 (backend); jQuery, Bootstrap 3,
DataTables (frontend — none of which this table uses; it is plain server-rendered markup)

**Storage**: MySQL/MariaDB. **No schema change**: no file under `biweeklybudget/models/`
is touched, so Constitution principle III does not engage and no Alembic migration is
required.

**Testing**: pytest — unit (`biweeklybudget/tests/unit/`) and Selenium acceptance
(`biweeklybudget/tests/acceptance/`), run via `tox -e py314` and `tox -e acceptance`

**Target Platform**: Flask web app, localhost single-operator use

**Project Type**: Web application, single Python package with server-rendered templates

**Performance Goals**: Strictly improved. The view reads `account_sums` from five pay
periods today and will read it from one, removing four `_make_account_sums()`
computations per page load. `PayPeriodView.get()` already reads `overall_sums` from all
five periods for the Remaining Balances table, so the adjacent periods are still
constructed; only their per-account grouping stops being computed.

**Constraints**: The table grows horizontally with account count; the existing
`table-responsive` wrapper must keep it scrolling inside its panel rather than widening
the page.

**Scale/Scope**: One helper function, one template block (~30 lines), one new unit test
module, ~9 rewritten acceptance tests, one documentation section, one screenshot and its
caption, one changelog entry.

## Constitution Check

*Checked against `.specify/memory/constitution.md` **v2.1.2**. Gate evaluated before
Phase 0 and re-evaluated after Phase 1 design; both passes below.*

| Principle | Applies? | How this plan satisfies it | Post-design re-check |
|-----------|----------|----------------------------|----------------------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Yes | Spec written first at [spec.md](./spec.md); this plan precedes implementation; work is on feature branch `robot-army/issue-355-pay-period-per-account-transaction`; decomposed into milestones by `/speckit-tasks`. Single feature, worked alone. | PASS — design adds no second feature |
| **II. The Test Gate** (NON-NEGOTIABLE) | Yes | Full `tox -e py314` and `tox -e acceptance` suites run to completion and pass before the feature is declared done, not a narrowed subset. New unit coverage is created for `build_account_sums()` (none exists today — see [research.md](./research.md)). Acceptance tests are rewritten to assert the new shape, not relaxed to tolerate both. pycodestyle/pyflakes clean under `pytest.ini` exceptions. | PASS — see [quickstart.md](./quickstart.md) for the exact commands and expected outcomes |
| **III. Reversible Migrations** | **No** | Nothing under `biweeklybudget/models/` is touched and no schema changes. The `migrations` suite is therefore not implicated; it will still be run as a regression check. | PASS — Phase 1 design confirms no model file appears in any task |
| **IV. Documentation Is Part Of The Change** | Yes | `docs/source/app_usage.rst` §`per_account_totals` is rewritten for the new shape in the same change, deliberately retaining the `not_budget_totals` subsection per FR-012. `docs/make_screenshots.py` caption and its committed rendering in `docs/source/screenshots.rst` are corrected, and `payperiod.png`/`payperiod_sm.png` are regenerated. `tox -e docs` must build without errors. | PASS — documentation tasks are part of the milestone that changes the behaviour, not deferred |
| **V. Escalate Instead Of Guessing** | Yes | The three shape questions the issue left open (where the grand total goes, what happens to the current-period highlight, whether the helper is renamed) are decided explicitly and with rationale in [research.md](./research.md) D1-D6 rather than settled silently mid-edit. Any deviation found during implementation is recorded in this spec directory before it begins. | PASS |
| **VI. Changelog Every Change; Release Only On Request** | Yes | One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link, describing the user-visible change in a sentence or two. `biweeklybudget/version.py` is **not** touched; no tag, no release. | PASS |
| **Stack constraint** (Bootstrap 3 / no parallel frontend) | Yes | The table stays plain server-rendered Bootstrap markup in the existing `table-responsive` wrapper. No DataTables, no new JS, no new dependency. | PASS |
| **Financial correctness** (tests pin expected numbers) | Yes | The per-account arithmetic is **not** changed — `account_sums` is untouched. Even so, both the new unit tests and the rewritten acceptance tests pin exact `Decimal` amounts, including the deliberate disagreement with the period's *spent* figure. | PASS |
| **Test data safety** | Yes | Acceptance tests use the existing `class_refresh_db`/`refreshdb` fixtures against the test database only. | PASS |
| **License headers** | Yes | The one new file (`biweeklybudget/tests/unit/flaskapp/views/test_payperiods.py`) carries the standard AGPL v3 header copied from a sibling test module. | PASS |

**Gate result: PASS.** No violations; the Complexity Tracking table below is
consequently empty.

## Project Structure

### Documentation (this feature)

```text
specs/20260919-174820-current-period-account-totals/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: existing-code survey + shape decisions D1-D6
├── data-model.md        # Phase 1: the view model the template renders
├── quickstart.md        # Phase 1: how to run and validate the change
├── contracts/
│   └── view-model.md    # Phase 1: build_account_sums() contract + rendered HTML contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 (/speckit-tasks) - NOT created by /speckit-plan
```

### Source Code (repository root)

Only these files change:

```text
biweeklybudget/
├── flaskapp/
│   ├── views/
│   │   └── payperiods.py            # build_account_period_sums -> build_account_sums;
│   │                                # PayPeriodView.get() passes one period
│   └── templates/
│       └── payperiod.html           # pp-acct-table transposed, single period
└── tests/
    ├── unit/flaskapp/views/
    │   └── test_payperiods.py       # NEW - unit coverage of build_account_sums
    └── acceptance/flaskapp/views/
        └── test_payperiods.py       # TestPayPeriodAccountTotals{,Empty} rewritten

docs/
├── make_screenshots.py              # payperiod screenshot caption
└── source/
    ├── app_usage.rst                # per_account_totals section
    ├── screenshots.rst              # committed rendering of the caption
    └── payperiod{,_sm}.png          # regenerated screenshot

CHANGES.rst                          # one Unreleased bullet
```

Untouched, and deliberately so: `biweeklybudget/biweeklypayperiod.py` (the arithmetic),
everything under `biweeklybudget/models/`, `biweeklybudget/alembic/`,
`biweeklybudget/version.py`, and the `pay-period-table` Remaining Balances markup
(FR-013).

**Structure Decision**: the existing single-package Flask layout is kept as-is. This is a
localised change to one view and one template within it; no new package, module directory
or frontend asset is introduced. The only new file is a unit test module placed beside
the existing `biweeklybudget/tests/unit/flaskapp/views/test_index.py`, which is the
established home for tests of plain module-level view helpers (that directory has no
`__init__.py`, matching the rest of the unit tree's convention for it).

## Implementation Approach

### The helper

`build_account_period_sums(periods) -> (rows, column_totals)` becomes
`build_account_sums(period) -> (columns, total)`:

- `columns`: one dict per account with at least one transaction in `period`, sorted
  ascending by account name, each `{'id': int, 'name': str, 'total': Decimal}`.
- `total`: the sum of every column's `total`, `Decimal('0.0')` when there are none.

The zero-filling the old docstring explained disappears with the union over periods —
every account on screen is one the period observed, so `account_sums` already has a total
for it (research D3). Full contract in [contracts/view-model.md](./contracts/view-model.md).

`PayPeriodView.get()` calls it with `pp` alone and passes `acct_sums` / `acct_total` to
the template (research D5). `pp_prev`, `pp_next`, `pp_following` and `pp_last` remain in
the view — the Remaining Balances table still needs them — they simply stop being fed to
this helper.

### The template

The `pp-acct-table` body becomes a header row of one linked account name per column
followed by a `Total` header, and a single data row of `reddollars`-filtered amounts
ending in the grand total. The `class="info"` current-period emphasis is dropped
(research D2), and no `/payperiod/<date>` link appears anywhere in the table (FR-009).
Everything outside the `<table>` — panel, heading, `table-responsive` wrapper — is
unchanged.

### The tests

- **Unit** (new): `build_account_sums()` against stub periods — several accounts sorted
  by name, the grand total, a negative total, an exact-zero account keeping its column,
  and the empty period returning `([], Decimal('0.0'))`.
- **Acceptance** (rewritten): `TestPayPeriodAccountTotals` keeps its fixture unchanged —
  its previous- and next-period transactions now serve as proof that adjacent-period
  activity is *excluded* (research, Risks) — and its assertions move to the transposed
  single-period shape: headers, the one amount row, the absent quiet account, the
  no-budget-impact total that deliberately disagrees with `amt-spent`, the grand total,
  the account links, the absence of any other period, and no DataTables wrapper.
  `TestPayPeriodAccountTotalsEmpty` asserts the `Total`-only header and single `$0.00`.
  Test 2's direct `account_sums` assertion is left alone; it tests untouched behaviour.

### The documentation

`app_usage.rst` §`per_account_totals` is rewritten to describe one row of accounts for
the period being viewed. The `not_budget_totals` subsection stays — FR-012 is explicit
that this explanation survives — with only the wording that assumed columns-as-periods
adjusted. The screenshot caption loses "across the five periods shown at the top of the
page" in both `make_screenshots.py` and `screenshots.rst`, and `payperiod.png` /
`payperiod_sm.png` are regenerated so the committed screenshot shows the shipped table.

## Complexity Tracking

> No Constitution Check violations. Nothing to justify.
