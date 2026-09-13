# Implementation Plan: Plaid Screenshots

**Branch**: `robot-army/issue-264-add-screenshots-for-plaid` | **Date**: 2026-09-13 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/20260913-151057-plaid-screenshots/spec.md`

## Summary

Add three Plaid entries to the documentation screenshot generator
(`docs/make_screenshots.py`): the Plaid Update page, the Edit Account modal scrolled to
its Plaid Account selector, and a Plaid Update result with one successful and one failed
Item. The result page is produced by swapping `PlaidUpdater` in the Plaid view module for a
stub that returns fixed results, before the live server process is forked, so no Plaid
credentials or network access are needed. Point the Plaid docs at the screenshots, and
fix the result page's always-empty "Statement IDs" column, which the new screenshot
would otherwise show (see research R4).

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, Jinja2, Selenium + headless Chrome, Pillow, pytest-flask
`LiveServer` (all already used by the `screenshots` tox env)

**Storage**: MariaDB test database, reloaded from sample data at the start of each
screenshot run. No schema change.

**Testing**: pytest (unit, with `--pycodestyle --flakes`), acceptance suite, `docs` tox
env, and a full `screenshots` tox env run (also a CI job).

**Target Platform**: Linux (developer machine and GitHub Actions)

**Project Type**: Web application (Flask) plus its documentation tooling

**Performance Goals**: N/A (adds three screenshots, a few seconds, to a run of several
minutes)

**Constraints**: Screenshot generation must work with no Plaid credentials and no network
access to Plaid; it must not alter the data later screenshots are taken from.

**Scale/Scope**: One generator script, one template line, one docs page, one changelog
entry, one unit test.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Spec-Driven Change | PASS | Spec, plan and tasks under `specs/20260913-151057-plaid-screenshots/`, on the session's feature branch. One milestone for implementation. |
| II. Test Gate | PASS (planned) | Full unit and acceptance suites run to completion before completion, plus `screenshots` and `docs` envs. The template fix gets a unit test that renders the real template. `docs/make_screenshots.py` is outside pytest's lint target, so it is checked with pycodestyle/pyflakes by hand. |
| III. Reversible Migrations | N/A | No model changes. |
| IV. Documentation | PASS (planned) | `docs/source/plaid.rst` links to the screenshots. `screenshots.rst` is generated; it and the PNGs are regenerated at release (see research R5). README/CLAUDE.md unaffected. |
| V. Escalate Instead Of Guessing | PASS | The result-template fix is a deviation from the issue's literal scope; it is recorded in the spec before the work begins. No open questions. |
| VI. Changelog; No Version Bump | PASS (planned) | One concise `Unreleased` entry; `version.py` untouched. |
| Security posture / Secrets | PASS | The stub's error text is invented and contains no token or credential. No app behaviour is exposed to the network. |
| Test data safety | PASS | Screenshots run against the throwaway test DB only. |

Post-design re-check: unchanged, all PASS.

## Project Structure

### Documentation (this feature)

```text
specs/20260913-151057-plaid-screenshots/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── screenshots.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
docs/
├── make_screenshots.py            # 3 new entries, preshot for the modal, Plaid updater stub
└── source/
    └── plaid.rst                  # link to the Plaid screenshots
biweeklybudget/
├── flaskapp/templates/
│   └── plaid_result.html          # stmt_id -> stmt_ids
└── tests/unit/flaskapp/views/
    └── test_plaid.py              # render the real result template
CHANGES.rst                        # Unreleased entry
```

**Structure Decision**: Existing single-project layout. No new modules.

## Complexity Tracking

No constitution violations to justify.
