# Implementation Plan: Omit Accounts From The Account Balances Chart

**Branch**: `robot-army/issue-357-allow-excluding-accounts-from-the-index` | **Date**: 2026-09-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260919-192038-omit-accounts-from-graphs/spec.md`

**Issue**: [#357](https://github.com/jantman/biweeklybudget/issues/357)

## Summary

Give `Account` a persistent `omit_from_graphs` boolean — the same name, modal label
and meaning as the existing `Budget.omit_from_graphs` — settable from the Add/Edit
Account modal, and make `AcctBalanaceChartView.get()` leave flagged Accounts out of
the chart data entirely: no series, no values, no legend entry.

The whole feature is four small edits and one migration. Its risk is not in any of
them; it is in the two ways a change like this quietly goes wrong, so the plan is
organised around them:

1. **Blast radius.** The flag must affect one chart and nothing else — not
   balances, not totals, not pay period arithmetic, not a single account picker.
   That is bought by one decision (R3): the filter goes in the chart view, *not*
   into `Account.active_accounts()`, the helper that every picker shares.
2. **The upgrade.** The new column is `NULL` on every row that already exists, and
   in SQL `NULL = false` is not true. Written as `== False`, the filter would drop
   every pre-upgrade Account from the chart on the first page load after upgrade.
   Written as `isnot(True)` it does not. Both spellings were compiled and compared
   (R3); User Story 4 exists to keep the right one.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy 2.0, Alembic; jQuery + Bootstrap 3 + Chart.js on the frontend

**Storage**: MySQL / MariaDB. One new nullable `BOOLEAN` column on `accounts`.

**Testing**: pytest — `tox -e py314` (unit), `tox -e acceptance` (Selenium + live server), `tox -e migrations`, `tox -e docs`, `tox -e docker`

**Target Platform**: Localhost Flask application, single trusted operator

**Project Type**: Server-rendered web application (Flask backend, jQuery frontend, no separate frontend build)

**Performance Goals**: Strictly non-regressive. The chart endpoint's cost is dominated by the `AccountBalance` scan; this change adds one predicate to a query already bounded by the number of Accounts, and *removes* work by emitting fewer series. Issue #279's point cap and the `accounts` name-map lookup that replaced per-row lazy loads are both untouched.

**Constraints**: No new setting, environment variable or dependency. The chart response keeps its `data`/`keys` shape (FR-017). Migration must be reversible and must match the model exactly.

**Scale/Scope**: ~6 source files, 1 migration, 2 documentation files, 2 regenerated screenshots, 1 changelog entry.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v2.1.2. Re-checked after Phase 1 design — see "Post-Design Re-Check" below.*

| Principle | Status | How this plan satisfies it |
|---|---|---|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | PASS | Spec written and committed (`e48884b`) before planning; this plan precedes implementation; work is on the feature branch `robot-army/issue-357-…`; decomposed into milestones M0–M4 below with a human approval point at each boundary. One feature at a time: #356, the related change, is already merged and is built upon rather than reopened. |
| **II. The Test Gate** (NON-NEGOTIABLE) | PASS | M4 runs the unit and acceptance suites to completion, plus `migrations` and `docker` because this change touches schema. New coverage is added for both the endpoint exclusion and the modal round-trip. No existing assertion is weakened: R5 chose in-test flagging over changing `sampledata.py` precisely so that no unrelated assertion has to be edited. pycodestyle/pyflakes clean under `pytest.ini`. |
| **III. Reversible Migrations** | PASS | M1 ships the model change and its Alembic migration together. `upgrade()` adds the column, `downgrade()` drops it; both are run before commit. The column definition `sa.Boolean(), nullable=True` matches `Column(Boolean, default=False)` exactly (R2). No new model class, so no `models/__init__.py` change. `tox -e migrations` is the gate. |
| **IV. Documentation Is Part Of The Change** | PASS | M3 updates `docs/source/app_usage.rst` and `docs/source/http_api.rst`, regenerates the two screenshots that show the Edit Account modal, and builds `tox -e docs`. It also corrects a pre-existing error in `http_api.rst` left behind by #356 (FR-020). |
| **V. Escalate Instead Of Guessing** | PASS | The two questions issue #357 explicitly left open were escalated to the maintainer and answered before the spec was written; the answers are recorded in the spec. Milestone boundaries are approval points. Any deviation found mid-implementation is recorded in this spec and committed before it is acted on. |
| **VI. Changelog; No Version Bump** | PASS | M4 adds one concise bullet under `Unreleased` in `CHANGES.rst`, led by the issue link. `version.py` is **not** touched, no tag, no release. The entry names the new docs section in prose rather than linking it, because a changelog link to an anchor added in the same PR fails `tox -e docs` linkcheck (R6). |
| **Stack constraint**: follow existing modal/DataTables patterns | PASS | One `FormBuilder.addCheckbox()` call and one `prop('checked', …)` read, copied in shape from `budgets_modal.js`. No new frontend library, no new pattern. |
| **Security posture**: localhost, single trusted operator | PASS | Unchanged. No endpoint is added, none is opened up; one existing endpoint returns strictly *less* data. |
| **Financial correctness**: tests pin expected numbers | PASS, and load-bearing | This setting is presentation-only and must never reach an arithmetic path. The table in R7 enumerates every place Accounts are read and shows exactly one call site is affected. User Story 3 / FR-014 is the assertion of that, and it is the reason the filter is kept out of `Account.active_accounts()`. |
| **Test data safety** | PASS | Acceptance tests use the existing `refreshdb` / `class_refresh_db` fixtures against the test database only. |
| **AGPL header on new Python files** | PASS | The only new Python file is the Alembic migration, which follows the header convention of the existing files in `biweeklybudget/alembic/versions/`. |

**Gate result: PASS — no violations, so the Complexity Tracking table is omitted.**

### The one thing a reviewer should check

Every other claim in this plan is routine. This one is not, and it is worth stating
plainly rather than leaving in a table cell:

> `Account.active_accounts()` is documented in the model as "the single definition
> of *an Account that may be chosen*", and six account pickers depend on it. The
> obvious place to put `omit_from_graphs` is inside it. Doing so would make
> flagging an account silently remove it from every dropdown in the application —
> a direct FR-014 violation, and precisely the over-reach that made deactivation
> the wrong tool for this problem in the first place. The filter therefore lives in
> `AcctBalanaceChartView.get()` and nowhere else.

## Project Structure

### Documentation (this feature)

```text
specs/20260919-192038-omit-accounts-from-graphs/
├── spec.md              # Feature specification (committed e48884b)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── account-balances-chart.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
biweeklybudget/
├── models/
│   └── account.py                       # + omit_from_graphs column
├── alembic/versions/
│   └── <newrev>_account_add_omit_from_graphs.py   # NEW; revises 3f7c2a91e04b
├── flaskapp/
│   ├── views/
│   │   ├── index.py                     # AcctBalanaceChartView.get(): the filter
│   │   └── accounts.py                  # AccountFormHandler.submit(): persist it
│   └── static/js/
│       └── accounts_modal.js            # checkbox in form; read it back on edit
└── tests/acceptance/flaskapp/views/
    ├── test_index.py                    # + chart exclusion class
    └── test_accounts.py                 # + modal round-trip coverage

docs/
├── source/app_usage.rst                 # "Leaving an account out" + Charts pointer
├── source/http_api.rst                  # form field; correct the `keys` sentence
└── source/*.png                         # regenerate account1, account1-plaid

CHANGES.rst                              # one bullet under Unreleased
```

**Structure Decision**: The repository's existing single-package layout is used
as-is. No new module, package or directory is introduced — every file above
already exists except the migration.

## Implementation Milestones

Each milestone ends at a human approval point (Constitution I).

### M0 — Specify, plan, break down

- **M0.1** Write the specification. *(done — `e48884b`)*
- **M0.2** Write this plan and the Phase 0/1 artifacts.
- **M0.3** Break the feature into tasks (`/speckit-tasks`).

### M1 — Schema: the column and its migration

- **M1.1** Add `omit_from_graphs = Column(Boolean, default=False)` to `Account`,
  immediately after `is_active`, with a docstring comment naming issue #357 in the
  style of the surrounding columns.
- **M1.2** Generate the Alembic migration revising head `3f7c2a91e04b`; write
  `upgrade()`/`downgrade()` after `6d37400ea9cd`.
- **M1.3** Run the migration up and back down against the test database, and run
  `tox -e migrations` to confirm head matches the models.

*Exit*: schema in place and reversible; nothing user-visible has changed yet.

### M2 — Behaviour: the chart honours the flag, the modal sets it

- **M2.1** `AcctBalanaceChartView.get()`: compose the omit filter onto
  `Account.active_accounts(db_session)` using `isnot(True)`, and extend the class
  docstring — which already explains the #356 exclusion — to cover this one and to
  say why `NULL` counts as "not omitted".
- **M2.2** `accounts_modal.js`: add the checkbox after `Active?`; read it back in
  `accountModalDivFillAndShow()` with a strict `=== true` test.
- **M2.3** `AccountFormHandler.submit()`: persist `data['omit_from_graphs']`
  alongside `is_active`.
- **M2.4** Acceptance coverage: a new class in `test_index.py` (via
  `class_refresh_db`, flagging `InvestmentOne`) asserting absence from `keys` and
  from every row for every window, that the other accounts' values and the date set
  are unchanged, and that a `NULL`-flagged account is still charted; plus modal
  round-trip coverage in `test_accounts.py`.

*Exit*: the feature works end to end and is covered.

### M3 — Documentation

- **M3.1** `docs/source/app_usage.rst`: a "Leaving an account out" subsection under
  Account Balances Chart, and the pointer from the Charts legend bullet.
- **M3.2** `docs/source/http_api.rst`: add `omit_from_graphs` to the
  `POST /forms/account` fields; rewrite the chart `keys` sentence (FR-020).
- **M3.3** Regenerate and commit `account1` / `account1-plaid` screenshots.
- **M3.4** `tox -e docs` builds clean.

### M4 — Close the feature

- **M4.1** `CHANGES.rst` entry under `Unreleased`. No version bump.
- **M4.2** Full unit, acceptance, migrations and docker suites to completion,
  everything passing.
- **M4.3** Push the branch, open the pull request, monitor CI, answer reviews until
  clean.

## Risks

| Risk | Where it bites | Mitigation |
|---|---|---|
| `== False` instead of `isnot(True)` | Every pre-upgrade Account vanishes from the chart on first load after upgrade | R3 compiled both spellings; User Story 4 / M2.4 asserts a `NULL`-flagged account is still charted |
| Filter folded into `active_accounts()` | Flagged account silently disappears from six pickers | Called out as the one thing a reviewer should check; M2.1 scopes the filter to the view |
| `sampledata.py` edited to add a flagged account | Dozens of unrelated assertions need editing, each one indistinguishable from weakening a test | R5: flag in-test with `class_refresh_db`; sample data untouched |
| Another feature merges a migration first | `down_revision` points at a stale head | M1.2 re-checks the head at implementation time |
| Changelog links the new docs anchor | `tox -e docs` linkcheck fails | R6: name the section in prose |

## Post-Design Re-Check

Re-evaluated after `data-model.md`, `contracts/` and `quickstart.md` were written.
No gate changed status; no new violation appeared. Two points are worth recording:

- The contract document confirms FR-017 concretely: the response keeps its
  `data`/`keys` keys and every type within them, so the change is
  narrowing-only for existing callers. That is a documentation change, not a
  breaking API change, which keeps the `Unreleased` entry a MINOR-flavoured
  addition rather than anything that would force a MAJOR at release time.
- `data-model.md` confirms no relationship, index, constraint or `models/__init__.py`
  entry is involved — the migration really is one `add_column` — so Principle III's
  "new model classes must be imported" clause does not apply.
