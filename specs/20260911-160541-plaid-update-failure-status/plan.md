# Implementation Plan: Plaid Update Reports Failure In Its Status Code

**Branch**: `robot-army/issue-261-plaid-update-endpoint-needs-to-return` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260911-160541-plaid-update-failure-status/spec.md`

## Summary

`PlaidUpdate._update()` in `biweeklybudget/flaskapp/views/plaid.py` already has the list
of per-Item `PlaidUpdateResult`s before it builds any of its three responses. It will
compute one status code from that list: HTTP 500 if any result has `success` false,
otherwise HTTP 200. Each of the three return statements (plain text, JSON, HTML template)
then returns `(body, status)` instead of a bare body. Bodies are untouched.

Unit tests in `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` pin the status
for each format in both the failing and the all-successful case, plus the empty-result
case. The Plaid documentation page and the HTTP API summary gain a sentence on status
codes, and `CHANGES.rst` gets one `Unreleased` entry.

## Technical Context

**Language/Version**: Python 3.14 (3.14.7)

**Primary Dependencies**: Flask 3.1.3 / Werkzeug 3.1.8. A Flask view can return a
`(body, status)` tuple for any body type the view already returns (`str`, a `Response`
from `jsonify`, or rendered template text). No new dependency.

**Storage**: MariaDB, unchanged. No model, schema, or migration change.

**Testing**: pytest. Unit tests (`tox -e py314`) cover the view with mocks, following the
existing `TestPlaidUpdate` pattern. The full unit and acceptance suites must pass
(Constitution II). `docs` must build (Constitution IV).

**Target Platform**: Linux; the Flask app served locally or in Docker.

**Project Type**: Flask/SQLAlchemy web application. One view method changes.

**Performance Goals**: None. One pass over an already-built list of a handful of results.

**Constraints**: Response bodies MUST NOT change (spec FR-004). No change to
`PlaidUpdater` or `PlaidUpdateResult`.

**Scale/Scope**: One method (~5 changed lines), its unit tests, two doc pages, one
changelog entry.

## Constitution Check

*Constitution v2.1.1. Gate evaluated before Phase 0 and re-evaluated after Phase 1.*

| Principle | Assessment | Status |
|-----------|-----------|--------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Spec written and validated, then this plan, then tasks, all before code. Work stays on the feature branch `robot-army/issue-261-plaid-update-endpoint-needs-to-return`. The change is small enough to be a **single milestone (M1)**, so there is no inter-milestone boundary to cross. The maintainer's human approval is taken at the pull request, before merge. | PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | New and changed unit tests pin the status code for every response format in the failing, all-successful, and empty cases (spec SC-001/SC-002). The complete unit and acceptance suites MUST run to completion and pass before the feature is declared done. The `plaid` suite needs Plaid sandbox credentials and runs in CI. The `migrations` and `docker` suites are not engaged (no schema or packaging change) but still run in CI. Timeouts get raised and re-run, never narrowed. Touched code stays pycodestyle/pyflakes-clean. | PASS |
| **III. Reversible Migrations** | No change under `biweeklybudget/models/`; not engaged. | N/A |
| **IV. Documentation Is Part Of The Change** | `docs/source/plaid.rst` (update API section) and `docs/source/http_api.rst` (summary) are updated in the same change, along with the `PlaidUpdate` docstring that Sphinx renders. The `docs` environment must build clean. `README.rst` and `CLAUDE.md` don't describe this endpoint's responses, so they need no change. | PASS |
| **V. Escalate Instead Of Guessing** | The issue asks only for "non-200". Choosing HTTP 500, and applying it to the browser view too, are judgement calls with obvious defaults. They are recorded with reasoning in research R1 and R2 and surfaced in the PR for the maintainer to overrule, not guessed silently. | PASS |
| **VI. Changelog Every Change; Release Only On Request** | One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link, noting the behaviour change for API callers. `version.py` is not touched; no tag. No new Python files, so no new copyright headers. | PASS |
| **Tech constraints** | No new dependency, no license question, no secrets, no security-posture change, no financial-calculation code touched. Acceptance tests keep using only the dedicated test database. | PASS |

**Result: no violations. The Complexity Tracking table is therefore omitted.**

Post-Phase-1 re-evaluation: the design adds no module, abstraction, or dependency. It
is a local change to one method's return values, and the Constitution Check still passes.

## Design

```text
results = updater.update(items=items, days=num_days)
status  = 200 if all(r.success for r in results) else 500   # all([]) is True → 200
text/plain        → return s, status
application/json  → return jsonify([...]), status
otherwise (HTML)  → return render_template(...), status
```

- `all()` over an empty list is `True`, so "no Items updated" is 200 with no special case
  (spec edge case).
- The status is computed once, before the format branch, so the three formats can't
  drift apart (spec FR-003).
- GET and POST both reach `_update()`, so both are covered (FR-003).
- The request handlers' existing 400 for a POST missing `item_ids`, and the GET form view,
  are outside `_update()` and unchanged.

### Project Structure

Documentation for this feature:

```text
specs/20260911-160541-plaid-update-failure-status/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── plaid-update.md  # Phase 1: the endpoint's status-code contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2, written by /speckit-tasks
```

Repository files this change touches:

```text
biweeklybudget/
├── flaskapp/views/plaid.py                      # PlaidUpdate._update + class docstring
└── tests/unit/flaskapp/views/test_plaid.py      # TestPlaidUpdate status assertions + new cases
docs/source/plaid.rst                            # status codes in the update API section
docs/source/http_api.rst                         # status codes in the summary
CHANGES.rst                                      # Unreleased entry
```

**Structure Decision**: the existing layout is kept. No new file outside `specs/`.

## Milestones

- **M1 — Status code, tests, and docs.** Change `_update()` and its docstring. Update
  the three existing `_update` unit tests to assert the status, and add tests for the
  cases they don't cover. Update the two doc pages and `CHANGES.rst`. Run the Test Gate
  (unit, acceptance, docs), record the results in the spec artifacts, then commit, push,
  and open the PR.

## Risks

| Risk | Mitigation |
|------|-----------|
| An existing caller treats any non-200 as fatal and now aborts on a partial failure. | That is the requested behaviour. The changelog entry calls it out so operators can adjust. |
| Returning a tuple changes the body or its content type. | Flask applies the status to the same response it would have built. The unit tests assert the exact body object and status, and the acceptance browser flow (`test_plaidlink.py::test_17`) still renders the failed-results page. Research R3 covers why that test is unaffected. |
| A failing-update response is mistaken for an unhandled server crash. | The body still carries the full per-Item report, and the docs state that 500 with a results body means one or more Items failed. |
