# Implementation Plan: Plaid Item Last Successful Update Time

**Branch**: `robot-army/issue-268-plaid-show-last-successful-update-time` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260915-194912-plaid-last-successful-update/spec.md`

## Summary

Store the time Plaid reports for each Item's last successful transactions refresh, and show
it in the Plaid Items table beside the existing "Last Polled" time.

The value is already in hand: both code paths that call Plaid's `item_get` — the transaction
downloader and the "Update Item Information from Plaid" action — receive it and currently
only log it. The change is therefore small and mostly additive: one nullable
`last_successful_update` column on `PlaidItem` with an Alembic migration, one shared
extraction helper in `biweeklybudget/utils.py` that reads the value out of a Plaid response
safely and normalises it to UTC, two one-line assignments at the existing write sites, and one
new column in `plaid_form.html` rendered with the same `ago` filter as "Last Polled",
displaying `unknown` where no value is stored.

No new Plaid API call, no new endpoint, no change to any existing response shape.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, `sqlalchemy_utc` (`UtcDateTime`), Alembic,
`plaid-python`, `humanize`; Jinja2 templates with jQuery/Bootstrap 3 on the frontend

**Storage**: MySQL/MariaDB — one added nullable column on the existing `plaid_items` table

**Testing**: pytest — unit (`tox -e py314`), Selenium acceptance (`tox -e acceptance`),
migration (`tox -e migrations`), Docker (`tox -e docker`); `pycodestyle`/`pyflakes` clean per
`pytest.ini`

**Target Platform**: Linux, self-hosted, localhost-only single-operator web application

**Project Type**: Server-rendered Flask web application with a single Python package

**Performance Goals**: Not a factor. The feature adds no query, no API call, and one column
to a table that holds one row per linked institution (single digits in practice).

**Constraints**: The new value is cosmetic and must never be able to fail a transaction
download; `UtcDateTime` rejects naive datetimes, so the extracted value must be made aware
before assignment (see [research.md](./research.md) R3).

**Scale/Scope**: ~6 source files and ~5 test files touched; one Alembic revision; one
screenshot regenerated.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v2.1.2. Gate evaluated before Phase 0 and
re-evaluated after Phase 1 design — see the re-check at the end of this section.*

### I. Spec-Driven Change (NON-NEGOTIABLE)

**PASS.** Written spec under `specs/20260915-194912-plaid-last-successful-update/`, this plan
before any implementation, on the feature branch
`robot-army/issue-268-plaid-show-last-successful-update-time`. No other feature is in flight
in this worktree. The work is decomposed into milestones below, with the milestone boundary
as the approval point.

### II. The Test Gate (NON-NEGOTIABLE)

**PASS by construction; enforced at M3.** The complete unit and acceptance suites must pass
before the feature is declared done. This change touches schema, so the `migrations` and
`docker` suites are in the gate as well, and `docs` must build. No suite may be narrowed to a
passing subset, and a timeout is not a pass — a timed-out suite gets a raised timeout and a
re-run.

Known flaky tests in this repository (reconcile drag/unignore, fuel-log search, Plaid
"Uncheck All", docs linkcheck) are re-run in isolation before any failure is attributed to
this change; they are not waived.

New code is covered by real tests: the extraction helper gets direct unit tests for every
input shape in its contract, the two writers get assertions in their existing unit tests, and
the rendered column is covered end-to-end by the acceptance table assertion — in both the
value and the placeholder case, which is why the two sample-data Items are deliberately given
different values ([research.md](./research.md) R7).

### III. Schema Changes Ship With Reversible Migrations

**PASS.** The `PlaidItem` model change ships with an Alembic revision in the same commit,
`down_revision = 'c5e3a9b1d7f2'` (the verified current head), implementing both `upgrade()`
and `downgrade()`, both tested before commit. The column definition in the migration matches
the model exactly — `UtcDateTime`, nullable — which is what `tox -e migrations` verifies.
`PlaidItem` is an existing class already imported in `models/__init__.py`; no new model class
is introduced.

Autogenerate is **not** used for this revision. The precondition for autogenerate is a test
database at head *before* the model change, and the migration here is a single `add_column`
whose exact form is already established by `f5a002127934_plaid_models.py`. Writing it by hand
(Option B in `CLAUDE.md`) is the lower-risk path and avoids the silently-empty-migration trap
the constitution warns about.

### IV. Documentation Is Part Of The Change

**PASS.** The `plaid-update` screenshot shows the table this change alters, so it is
regenerated and committed along with an extended caption in `docs/source/screenshots.rst`
naming what distinguishes the two time columns. The model and module API pages are
`automodule`-generated and pick up the new column's docstring comment automatically. No prose
in `README.rst`, `CLAUDE.md`, or `docs/source/` enumerates this table's columns
([research.md](./research.md) R8), so nothing else needs rewriting. `tox -e docs` must build
clean.

### V. Escalate Instead Of Guessing

**PASS.** Every question this feature raised was resolved against the code or the installed
dependencies and recorded in [research.md](./research.md) — nothing is left to a guess at
implementation time. Two judgement calls are recorded explicitly rather than made silently:
the placeholder wording (`unknown`, not `never` — R6) and UTC normalisation of a naive value
rather than letting it raise (R3). Any deviation encountered during implementation is written
into this feature's spec as a side quest and committed *before* the deviation begins.

### VI. Changelog Every Change; Release Only On Request

**PASS.** One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link, naming
the user-visible change and the migration. `biweeklybudget/version.py` is **not** touched, no
tag is created, and no release is cut — none was requested.

### Technology & Security Constraints

**PASS.** Python 3.14 and MariaDB throughout; no new dependency of any kind, so no licence
question arises. The UI change follows the existing Jinja/Bootstrap table pattern with no new
frontend machinery. No credential is added, stored, logged, or displayed — the new column
holds a timestamp. Nothing about the localhost-only security posture changes. The change does
not touch pay-period arithmetic, budget allocation, interest, or payoff calculation; the one
correctness hazard it does introduce (a naive datetime failing an update at commit time) is
closed in the helper. Acceptance tests continue to run only against the disposable test
database.

### Post-Design Re-check

Re-evaluated after Phase 1. The design adds one column, one function, two assignments, one
table column, and one migration. It introduces no new project, no new abstraction layer, no
new dependency, and no new endpoint. **No violations; the Complexity Tracking table below is
empty and stays that way.**

## Project Structure

### Documentation (this feature)

```text
specs/20260915-194912-plaid-last-successful-update/
├── spec.md                          # Feature specification
├── plan.md                          # This file
├── research.md                      # Phase 0: R1-R9
├── data-model.md                    # Phase 1: the PlaidItem column
├── quickstart.md                    # Phase 1: how to validate it
├── contracts/
│   └── plaid-items-table.md         # Phase 1: UI table + helper contract
├── checklists/
│   └── requirements.md              # Spec quality checklist
└── tasks.md                         # Phase 2 (/speckit-tasks — not created here)
```

### Source code (repository root)

```text
biweeklybudget/
├── models/
│   └── plaid_items.py               # + last_successful_update column
├── alembic/versions/
│   └── <new>_add_plaid_item_last_successful_update.py   # + add/drop column
├── utils.py                         # + plaid_last_successful_update() helper
├── plaid_updater.py                 # _do_item: record the value
├── flaskapp/
│   ├── views/plaid.py               # PlaidUpdateItemInfo.post: record the value
│   └── templates/plaid_form.html    # + "Last Successful Update" column
└── tests/
    ├── fixtures/sampledata.py       # PlaidItem1 gets a value; PlaidItem2 stays null
    ├── unit/test_utils.py           # + helper tests
    ├── unit/test_plaid_updater.py   # TestDoItem: stub + assert the new field
    ├── unit/flaskapp/views/test_plaid.py   # TestPlaidUpdateItemInfo: same
    └── acceptance/flaskapp/views/test_plaid.py   # test_4_table: new column

docs/source/
├── screenshots.rst                  # extended Plaid Update caption
├── plaid-update.png                 # regenerated
└── plaid-update_sm.png              # regenerated

CHANGES.rst                          # + Unreleased entry
```

**Structure Decision**: The existing single-package layout is used unchanged. Every file above
already exists except the Alembic revision; the feature adds no directory and no module.

## Implementation Approach

### M1 — Store the value

The schema, the helper, and both write sites, with their unit tests. At the end of M1 the
value is being recorded but nothing displays it yet; this is independently verifiable through
the unit suite and by inspecting the database after an update.

1. Add `last_successful_update` to the `PlaidItem` model, documented in the same
   `#:`-comment style as the neighbouring columns so the API docs pick it up.
2. Hand-write the Alembic revision against head `c5e3a9b1d7f2`; test `upgrade` and
   `downgrade` and `upgrade` again against the test database.
3. Add `plaid_last_successful_update()` to `biweeklybudget/utils.py` per
   [contracts/plaid-items-table.md](./contracts/plaid-items-table.md) C2, with unit tests for
   every input shape listed there.
4. Call it from `PlaidUpdater._do_item` beside the existing `item.last_updated = dtnow()`,
   keeping the existing status log line.
5. Call it from `PlaidUpdateItemInfo.post` beside the existing institution assignments.
6. Update the existing unit tests for both writers — their `item_get` stubs and their strict
   `mock_calls` assertions.

### M2 — Show the value

7. Add the "Last Successful Update" column to `plaid_form.html` immediately after "Last
   Polled", using the `ago` filter with a Jinja conditional emitting `unknown` for a null.
8. Give `PlaidItem1` in `sampledata.py` a `last_successful_update` three days before
   `self.dt`, and leave `PlaidItem2`'s unset, so the acceptance suite covers both the
   rendered value and the placeholder.
9. Update `test_4_table` for the new column.

### M3 — Gate, document, deliver

10. Run the full gate: `py314`, `acceptance`, `migrations`, `docs`, `docker`. Re-run any
    known-flaky failure in isolation before attributing it to this change.
11. Regenerate and commit the `plaid-update` screenshots; extend the `screenshots.rst`
    caption. Do not run `docs` after `screenshots` before the PNGs are committed.
12. Add the `CHANGES.rst` entry under `Unreleased`; do not touch `version.py`.
13. Record progress in the spec artifacts, commit, push, open the PR.

## Risks

| Risk | Handling |
|------|----------|
| A naive datetime from Plaid raises at commit and fails a whole transaction download | The helper normalises naive to UTC ([research.md](./research.md) R3) |
| `.get()` chaining raises on a present-but-`None` `status` | The helper coerces each level with `or {}` (R2) |
| Adding a table column silently breaks the acceptance row assertions | `test_4_table` is updated in the same milestone as the template (M2) |
| Regenerating screenshots destroys them via a later `docs` run | Documented ordering constraint; PNGs committed before `docs` runs (R8, quickstart) |
| A pre-existing flaky test is blamed on this change, or masks a real break | Known flaky tests are listed in the Test Gate note and re-run in isolation |

## Complexity Tracking

No Constitution Check violations. Nothing to justify.
