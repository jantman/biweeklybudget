# Implementation Plan: Plaid Update Check All / Uncheck All

**Branch**: `robot-army/issue-262-plaid-update-needs-check-all-uncheck` | **Date**: 2026-09-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260913-104806-plaid-update-check-all/spec.md`

## Summary

The "Plaid Update Transactions" panel of `biweeklybudget/flaskapp/templates/plaid_form.html`
gains a line reading **Check All | Uncheck All** directly above its item table. Each is
a link that calls one small inline JavaScript function, `plaidSetAllItems(checked)`,
which sets the `checked` property of every item checkbox in `#table-update-plaid` and
returns nothing. Nothing is submitted and nothing reloads. The form, the view, and the
`/plaid-update` endpoint are unchanged: the view already updates exactly the `item_*`
fields that are posted, and browsers post only checked boxes.

Acceptance tests in `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py` cover
both links and the resulting form submission data. `docs/source/plaid.rst` mentions the
links, and `CHANGES.rst` gets one `Unreleased` entry.

## Technical Context

**Language/Version**: Python 3.14 (server side unchanged); browser JavaScript inline in
the Jinja2 template.

**Primary Dependencies**: jQuery (already loaded by `base.html` and used by this page's
inline script), Bootstrap 3. No new dependency.

**Storage**: MariaDB, unchanged. No model, schema, or migration change.

**Testing**: pytest + Selenium acceptance tests (`tox -e acceptance`), extending the
existing `TestPlaidUpdateView` class, whose fixture data has two Plaid Items
(`PlaidItem1`, `PlaidItem2`). The full unit and acceptance suites must pass
(Constitution II); `docs` must build (Constitution IV).

**Target Platform**: Modern desktop browsers against the locally served Flask app.

**Project Type**: Flask/SQLAlchemy web application. One template changes.

**Performance Goals**: None; a handful of checkboxes toggled client-side.

**Constraints**: The links MUST NOT submit, navigate, reload or scroll (spec FR-004).
Initial state (all checked) and the Update Transactions button are unchanged (FR-006).

**Scale/Scope**: ~10 lines of template/JS, three acceptance tests, one doc sentence, one
changelog entry.

## Constitution Check

*Constitution v2.1.1. Gate evaluated before Phase 0 and re-evaluated after Phase 1.*

| Principle | Assessment | Status |
|-----------|-----------|--------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Spec written and validated, then this plan, then tasks, all before code. Work stays on the feature branch `robot-army/issue-262-plaid-update-needs-check-all-uncheck`. The change is a **single milestone (M1)**, so there is no inter-milestone boundary to cross; the maintainer's approval is taken at the pull request, before merge. | PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | New acceptance tests exercise both links in a real browser and check the submitted form data (spec SC-001–SC-003). The complete unit and acceptance suites MUST run to completion and pass before the feature is declared done; `migrations`, `docker` and `plaid` are not engaged but still run in CI. Timeouts get raised and re-run, never narrowed. Touched Python stays pycodestyle/pyflakes-clean. | PASS |
| **III. Reversible Migrations** | No change under `biweeklybudget/models/`; not engaged. | N/A |
| **IV. Documentation Is Part Of The Change** | `docs/source/plaid.rst` ("Updating Transactions via UI", step 2) mentions the links. The JS is inline in the template, not in `static/js/`, so the jsdoc output is unaffected. The page is not in the screenshot set. `README.rst` and `CLAUDE.md` don't describe this page. The `docs` environment must build clean. | PASS |
| **V. Escalate Instead Of Guessing** | The issue says only "check all / uncheck all links". Placement, wording and link style follow existing page conventions (research R1–R3) and are surfaced in the PR for the maintainer to overrule. No decision here lacks an obvious default. | PASS |
| **VI. Changelog Every Change; Release Only On Request** | One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link. `version.py` is not touched; no tag. No new Python files, so no new copyright headers. | PASS |
| **Tech constraints** | Follows the existing jQuery/Bootstrap 3 stack; no new dependency, no secrets, no security-posture change, no financial-calculation code touched. Acceptance tests use only the dedicated test database. | PASS |

**Result: no violations. The Complexity Tracking table is therefore omitted.**

Post-Phase-1 re-evaluation: the design adds one template-local function and two links;
no module, abstraction, endpoint, or dependency. The Constitution Check still passes.

## Design

```text
<form method="post">
  <p><a id="plaid_check_all"   href="javascript:plaidSetAllItems(true);">Check All</a>
     | <a id="plaid_uncheck_all" href="javascript:plaidSetAllItems(false);">Uncheck All</a></p>
  <table id="table-update-plaid"> ... input.account-checkbox per item ... </table>
  ...

function plaidSetAllItems(checked) {
    $('#table-update-plaid input.account-checkbox').prop('checked', checked);
}   // returns undefined, so the javascript: URL leaves the page in place
```

- `javascript:` hrefs match the page-level link style used elsewhere (e.g. the
  "make trans. | skip" links in `payperiod.html`) and, unlike `href="#"`, do not scroll
  to the top or change the URL (spec edge case).
- The function MUST return `undefined`: a `javascript:` URL whose expression yields a
  value replaces the document with that value. Hence no `return` of the jQuery object.
- The selector is scoped to `#table-update-plaid`, so no other control changes; with no
  items it matches nothing and does nothing (spec edge cases).
- Submission is unchanged: `PlaidUpdate.post()` builds `item_ids` from the posted
  `item_*` keys, and unchecked boxes are not posted (FR-005).

## Project Structure

### Documentation (this feature)

```text
specs/20260913-104806-plaid-update-check-all/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1 (no data changes)
├── quickstart.md        # Phase 1
├── contracts/
│   └── plaid-update-ui.md  # Phase 1: element IDs and behaviour the tests rely on
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
biweeklybudget/
├── flaskapp/templates/plaid_form.html                  # links + plaidSetAllItems()
└── tests/acceptance/flaskapp/views/test_plaid.py      # new TestPlaidUpdateView tests
docs/source/plaid.rst                                   # "Updating Transactions via UI"
CHANGES.rst                                             # Unreleased entry
```

**Structure Decision**: Existing single Flask project layout; only the files above change.
