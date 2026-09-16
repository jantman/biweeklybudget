# Implementation Plan: Duplicate Name Validation on Account and Budget Forms

**Branch**: `robot-army/issue-275-silent-failure-on-duplicate-account-name` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260916-183529-duplicate-name-validation/spec.md`

## Summary

Account and Budget names must be unique, but neither form checks that. The uniqueness
rule is discovered only when MySQL rejects the `INSERT`/`UPDATE`, and the driver's
`IntegrityError` string is handed to the user as a red `Server Error:` banner naming
internal tables and constraints.

The fix is one new helper on `FormHandlerView` —
`_validate_unique_name()` — called from `AccountFormHandler.validate()` and
`BudgetFormHandler.validate()`. It queries for a record of the same class whose
lower-cased name equals the submitted name, trimmed and lower-cased, excluding the
record being edited, and appends a plain-language message to `errors['name']`. The
save then never starts, so the record store is untouched and the session needs no
rollback.

**No schema change, no Alembic revision, no JavaScript change.** The per-field error
rendering the fix needs already exists in `handleFormSubmitted()`
([research.md](./research.md) R4), and the check sits in front of existing
constraints rather than altering them (R5).

Two decisions carry the design. First, the check compares names *case-insensitively*
and *after trimming* — not because that is the gentler reading, but because anything
looser would pass names the database or the HTTP API's name resolution then chokes on
(R2). Second, the issue's own request for a browser re-test of the original "silent
failure" report is a gate, not a footnote: it is milestone M1 and it runs before a
line of the fix is written, because if a duplicate submission really produces no
feedback at all, then a field-level message would not be seen either and the scope is
wrong.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask (`MethodView` via `FormHandlerView`), SQLAlchemy
(`sqlalchemy.func.lower` for the comparison); jQuery/Bootstrap 3 on the frontend,
unchanged

**Storage**: MySQL/MariaDB — existing tables, read only. Two `SELECT`s added on the
form-submission path; no DDL, no new columns, no data migration.

**Testing**: pytest — unit (`tox -e py314`), Selenium acceptance (`tox -e acceptance`),
docs (`tox -e docs`); `pycodestyle`/`pyflakes` clean per `pytest.ini`. Browser
observation for M1 via the Chrome automation tooling against a locally run app.

**Target Platform**: Linux, self-hosted, localhost-only single-operator web application

**Project Type**: Server-rendered Flask web application with a single Python package

**Performance Goals**: Not a factor. One indexed lookup per form submission, against
tables holding tens of rows.

**Constraints**: The check must reach the same verdict the unique index would, or it
replaces one confusing failure with a different one (FR-007, R2). It must exclude the
record being edited, or every account edit breaks (FR-002/FR-004, R3). It must not
stack a second message on top of the existing "Name cannot be empty" for a blank name
(spec Edge Cases).

**Scale/Scope**: 3 source files and 3 test files touched; 1 new method, 2 call sites,
1 changelog bullet, 1 docs paragraph. No new module, no new dependency, no migration.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v2.1.2. Gate evaluated before
Phase 0 and re-evaluated after Phase 1 design — see the re-check at the end of this
section.*

### I. Spec-Driven Change (NON-NEGOTIABLE)

**PASS.** A written spec exists under
`specs/20260916-183529-duplicate-name-validation/` and was written before this plan,
which is itself written before any implementation. Work is on the feature branch
`robot-army/issue-275-silent-failure-on-duplicate-account-name`, created for this
issue; no other feature is in flight in this worktree, and no new branch is created.
The work is decomposed into the four milestones below.

*Note on milestone approval*: the constitution asks for human approval at each
milestone boundary. This session was dispatched to carry the issue through to a pull
request, so the pull request is the review point, as it has been for the preceding
`robot-army/*` features in this repository. Each milestone is still a separate commit
so the boundaries stay legible to a reviewer.

### II. The Test Gate (NON-NEGOTIABLE)

**PASS by construction; enforced at M4.** The complete unit and acceptance suites must
run to completion with everything passing before the feature is declared done, and
`docs` must build. No suite may be narrowed to a passing subset, and a timed-out suite
has not passed: a timeout gets both the pytest timeout and the invoking tool's timeout
raised, and the suite re-run until it completes.

`migrations` and `docker` are **not** required by this change — no model, no packaging,
no template and no static asset is touched (R4, R5). That is a claim about the diff,
so it is checked against the diff at M4 rather than asserted here: if the diff turns
out to touch a model or a packaged asset, the corresponding suite joins the gate.

Known-flaky tests in this repository (the reconcile drag/unignore tests, the fuel-log
search test, and the Plaid "Uncheck All" test) have pre-existing missing-wait races.
A failure in one of those is re-run in isolation before it is attributed to this
change — and, if it then passes, it is reported as the known flake it is, never
counted as a pass for a test this change broke.

New code is covered by tests written against the behaviour the spec describes — the
message reaching the Name field, the record store unchanged, the rename-to-self path
still saving — not tests shaped to whatever the implementation happens to do.

### III. Schema Changes Ship With Reversible Migrations

**NOT APPLICABLE, verified rather than assumed.** Nothing under
`biweeklybudget/models/` is modified. `grep -rn "unique=True" biweeklybudget/models/`
returns exactly the three pre-existing constraints this change validates *in front of*
(R5). With no model change there is no migration to write and no head-versus-models
drift to introduce. M4 re-checks the diff against `biweeklybudget/models/` to confirm
this held.

### IV. Documentation Is Part Of The Change

**PASS.** `docs/source/` describes the account and budget forms; the duplicate-name
rule is user-visible behaviour on both, so the relevant page gains a sentence at M3.
The new helper carries a docstring in the project's existing style, which feeds the
API documentation the `docs` build generates. `tox -e docs` must build without errors
at M4. `README.rst` and `CLAUDE.md` describe setup and architecture, neither of which
this change alters, so neither is touched.

### V. Escalate Instead Of Guessing

**PASS, with one explicit escalation point.** The spec's User Story 4 and FR-009 exist
because the original report is unexplained. M1 observes the current behaviour in a
browser and records it. If that observation shows a duplicate submission failing with
*no* feedback at all — contradicting what the code says should happen — M1 stops, the
finding is written into the spec as a departure, that record is committed before
anything else, and guidance is sought. It is not worked around, and the fix is not
written on the assumption that the observation was mistaken.

### VI. Changelog Every Change; Release Only On Request

**PASS.** One concise bullet is added at M4 under the `Unreleased` heading in
`CHANGES.rst`, led by the issue link, in the format of the existing entries.
`biweeklybudget/version.py` is **not** touched, no tag is created, and no release is
cut. The problem narrative stays in this spec and in the pull request body, out of the
changelog.

### Technology & Security Constraints

**PASS.** Python 3.14, Flask and SQLAlchemy on the backend; no frontend change at all,
so no parallel frontend stack is introduced. No new dependency, therefore no licence
question. No change to the localhost-only security posture — the change removes
internal schema details from an error message shown to the operator, which is a small
move in the safer direction. No credentials involved. No pay-period, budget-allocation,
interest or payoff arithmetic is touched, so the financial-correctness clause has
nothing to bite on. Acceptance tests run against the throwaway test database via the
existing `refreshdb` fixtures, never a real one.

### Post-Design Re-Check

**PASS, unchanged.** Phase 1 produced no new entity, no new endpoint, no new external
contract and no new dependency — the design is one method on an existing base class
and two call sites. The one thing the design *did* settle that the pre-Phase-0 gate
could not is whether Principle III applies, and R5 confirms it does not. No entry is
needed in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/20260916-183529-duplicate-name-validation/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: R1-R5
├── data-model.md        # Phase 1: entities and the validation rule
├── quickstart.md        # Phase 1: how to verify the feature end to end
├── contracts/
│   └── form-endpoints.md  # Phase 1: POST /forms/account and /forms/budget
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
biweeklybudget/
├── flaskapp/
│   ├── views/
│   │   ├── formhandlerview.py   # MODIFIED: new _validate_unique_name() helper
│   │   ├── accounts.py          # MODIFIED: call it from AccountFormHandler.validate()
│   │   └── budgets.py           # MODIFIED: call it from BudgetFormHandler.validate()
│   └── static/js/forms.js       # UNCHANGED: already renders per-field errors (R4)
├── models/                      # UNCHANGED: no schema change (R5)
└── tests/
    ├── unit/flaskapp/views/
    │   └── test_formhandlerview.py   # MODIFIED: unit tests for the helper
    └── acceptance/flaskapp/views/
        ├── test_accounts.py          # MODIFIED: duplicate account name
        └── test_budgets.py           # MODIFIED: duplicate budget name

docs/source/                     # MODIFIED: one paragraph on the uniqueness rule
CHANGES.rst                      # MODIFIED: one bullet under Unreleased
```

**Structure Decision**: The existing single-package Flask layout is used as-is. The
helper goes on `FormHandlerView` because both handlers already inherit from it and
both need identical logic; see [research.md](./research.md) R1 for why that is
preferred over copying the existing inline duplicate-Plaid-account block twice.

## Milestones

Each milestone ends in its own commit, prefixed `Duplicate Name Validation - M.T` per
the constitution's workflow.

### M1 — Observe the current behaviour (gates everything else)

Satisfies FR-009 and spec User Story 4. Run the application locally against the test
fixture data, submit a duplicate account name through the Add Account modal in a real
browser, and record what the user actually sees — banner text, field state, whether
the record was created. Write the finding into `spec.md` and commit it before any
source change.

**Exit**: the observation is recorded in `spec.md` and committed. If the observation
is "no feedback at all", M1 instead records that as a departure per Principle V and
stops for guidance.

### M2 — The check

`FormHandlerView._validate_unique_name()`, called from both handlers, with unit tests
in `test_formhandlerview.py` covering: duplicate rejected; own name accepted; rename
onto another record rejected; trimmed comparison; case-insensitive comparison; blank
name adds no second message.

**Exit**: unit suite passes; `pycodestyle`/`pyflakes` clean.

### M3 — Acceptance coverage and documentation

Acceptance tests in `test_accounts.py` and `test_budgets.py` for the create path, the
rename path, and the save-under-own-name path, asserting both the rendered
`formfeedback` message and — via direct `requests.post` — the JSON `errors` payload,
following the patterns already in those files. Documentation paragraph added.

**Exit**: new acceptance tests pass; `tox -e docs` builds.

### M4 — Close the gate

Full unit and acceptance suites to completion, `tox -e docs`, diff re-checked against
`biweeklybudget/models/` to confirm the Principle III claim. `CHANGES.rst` entry under
`Unreleased`. Then push and open the pull request.

**Exit**: everything green, PR open, CI passing.

## Complexity Tracking

No Constitution Check violations. This section is intentionally empty.
