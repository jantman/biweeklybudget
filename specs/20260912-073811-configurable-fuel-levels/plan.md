# Implementation Plan: Configurable Fuel Levels

**Branch**: `robot-army/issue-208-fuel-log-configurable-fuel-levels` | **Date**: 2026-09-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260912-073811-configurable-fuel-levels/spec.md`

## Summary

A new setting, `FUEL_LEVELS`, holds an ordered list of `(label, percentage)` pairs. Its
default reproduces today's `0/10` … `10/10` options. It can be set in the settings module or
through a `FUEL_LEVELS="E:0,1/4:25,…"` environment variable. `biweeklybudget/settings.py`
parses and validates it at import and exits with an error naming the setting if it's
invalid. `fuel.html` exposes it to the page as a JSON global. `fuel.js` builds both fuel
level selects from it in order, with labels escaped, preselecting the lowest percentage
for the starting level and the highest for the ending level. Stored values stay
percentages, so there is no model, migration, form-handler, table, or chart change.

## Technical Context

**Language/Version**: Python 3.14 (3.14.7); browser JavaScript (jQuery, ES5 style as in
the existing `static/js`)

**Primary Dependencies**: Flask 3.1 / Jinja2 3.1 (`tojson` filter). No new dependency.

**Storage**: MariaDB, unchanged. No model, schema, or migration change (research R1).

**Testing**: pytest. Unit tests (`tox -e py314`) cover parsing and validation, plus
import-time behaviour in a subprocess. Selenium acceptance tests (`tox -e acceptance`)
cover the page and form, with both the default list and a custom one (research R7). The
full unit and acceptance suites must pass (Constitution II). `docs` must build
(Constitution IV).

**Target Platform**: Linux; the Flask app served locally or in Docker.

**Project Type**: Flask/SQLAlchemy web application.

**Performance Goals**: None. A list of about a dozen entries, validated once at startup.

**Constraints**: With no configuration, behaviour must be identical to today (spec
FR-003, SC-002). Stored level meaning must not change (FR-006). The HTTP API must not
change.

**Scale/Scope**: `settings.py` (one setting, two functions, import-time hook), one
template line, one JS function, and the tests and docs for them.

## Constitution Check

*Constitution v2.1.1. Gate evaluated before Phase 0 and re-evaluated after Phase 1.*

| Principle | Assessment | Status |
|-----------|-----------|--------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Spec written and validated, then this plan, then tasks, all before code. Work stays on the feature branch `robot-army/issue-208-fuel-log-configurable-fuel-levels`. The change is small enough to be a **single milestone (M1)**, so there is no inter-milestone boundary to cross. The maintainer's human approval is taken at the pull request, before merge. | PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | Unit tests pin every validation rule (spec FR-007) and the default list (FR-003). A subprocess test proves an invalid env var aborts startup, and a valid one is used. Acceptance tests pin options, order, defaults and escaping for the default and a custom list, plus the percentages saved (FR-004–FR-006). The existing default-list acceptance assertions stay as they are, as a regression guard. The complete unit and acceptance suites MUST run to completion and pass. Timeouts get raised and re-run, never narrowed. `migrations`, `docker`, and `plaid` are not engaged but run in CI. New code stays pycodestyle/pyflakes-clean. | PASS |
| **III. Reversible Migrations** | No change under `biweeklybudget/models/`; not engaged. | N/A |
| **IV. Documentation Is Part Of The Change** | The `FUEL_LEVELS` docstring in `settings.py` (rendered by Sphinx as the settings reference) gives the format, env-var syntax, and an example. `docs/source/app_usage.rst`'s Fuel Log settings list gains the new setting. The `level_before`/`level_after` description in `docs/source/http_api.rst` is clarified. `README.rst` and `CLAUDE.md` don't list individual settings, so they need no change. The `docs` environment must build clean. Generated jsdoc pages are regenerated at release per the Release Checklist. | PASS |
| **V. Escalate Instead Of Guessing** | Two scope choices were made with clear defaults rather than escalated: one global list, not one per vehicle; and percentages stored as today. Both are recorded in the spec's Assumptions and called out in the PR for the maintainer to overrule. | PASS |
| **VI. Changelog Every Change; Release Only On Request** | One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link, naming the new setting. `version.py` is not touched; no tag. The one new Python file (a unit test module) carries the standard AGPL header. | PASS |
| **Tech constraints** | No new dependency. The label is operator-supplied and rendered via `tojson` plus HTML escaping, so the setting can't inject script. That keeps the security posture unchanged. No financial-calculation code is touched, and acceptance tests use only the test database. | PASS |

**Result: no violations. The Complexity Tracking table is therefore omitted.**

Post-Phase-1 re-evaluation: the design adds one setting and two small pure functions in
`settings.py` and one helper in `fuel.js`, with no new module or dependency. The
Constitution Check still passes.

## Design

```text
settings.py (import time)
  FUEL_LEVELS = default tenths list
  … SETTINGS_MODULE import may replace it …
  if 'FUEL_LEVELS' in os.environ: FUEL_LEVELS = parse_fuel_levels(env)   ┐ ValueError →
  FUEL_LEVELS = validate_fuel_levels(FUEL_LEVELS)                        ┘ SystemExit('ERROR: FUEL_LEVELS setting is invalid: …')

fuel.html   var FUEL_LEVELS = {{ settings.FUEL_LEVELS|tojson }};

fuel.js     fuelLevelOptions(defaultValue) → [{value: pct, label: escaped label, selected}]
            fuelModalDivForm(): addSelect(level_before, fuelLevelOptions(min pct))
                                addSelect(level_after,  fuelLevelOptions(max pct))
```

- The env-var step runs after the settings module is imported, like the other env
  overrides. Validation runs last, so both sources are checked (research R4).
- `parse_fuel_levels` splits on `,`, then on each entry's last `:`, strips whitespace,
  requires `\d+` percentages, and returns pairs. Validation of counts, ranges, and
  uniqueness is left to `validate_fuel_levels`, so the rules live in one place.
- `validate_fuel_levels` returns a new list of `(str(label).strip(), pct)` tuples.
- `addSelect()` is used instead of `addLabelToValueSelect()` so integer-like labels keep
  their order. Labels are escaped in `fuel.js` because `addSelect()` doesn't escape
  (research R6).

### Project Structure

Documentation for this feature:

```text
specs/20260912-073811-configurable-fuel-levels/
├── spec.md
├── plan.md                        # this file
├── research.md                    # Phase 0
├── data-model.md                  # Phase 1
├── quickstart.md                  # Phase 1
├── contracts/
│   └── fuel-levels-setting.md     # Phase 1: setting format, validation, page contract
├── checklists/
│   └── requirements.md
└── tasks.md                       # Phase 2, written by /speckit-tasks
```

Repository files this change touches:

```text
biweeklybudget/
├── settings.py                                        # FUEL_LEVELS, parse/validate, import-time hook
├── flaskapp/templates/fuel.html                       # FUEL_LEVELS JS global
├── flaskapp/static/js/fuel.js                         # build level selects from FUEL_LEVELS
├── tests/unit/test_settings_fuel_levels.py            # new: parse/validate + subprocess import
└── tests/acceptance/flaskapp/views/test_fuel.py       # default global; custom list options/escaping/save
docs/source/app_usage.rst                              # Fuel Log settings list
docs/source/http_api.rst                               # level_before/level_after wording
CHANGES.rst                                            # Unreleased entry
```

**Structure Decision**: the existing layout is kept. The one new file is a unit test module.

## Milestones

- **M1 — Setting, form, tests, and docs.** Add the setting and its parsing/validation with
  unit tests. Expose it on the fuel page and build the selects from it, with acceptance
  tests. Update the docs and `CHANGES.rst`. Run the Test Gate (unit, acceptance, docs),
  record the results in the spec artifacts, then commit, push, and open the PR.

## Risks

| Risk | Mitigation |
|------|-----------|
| The default drifts from today's options, silently changing the form for everyone. | The existing `LEVEL_OPTS` acceptance assertions are kept unchanged. A unit test pins the default list value. |
| A label containing `<`, `&` or `</script>` breaks the page or injects markup. | `tojson` in the template; HTML escaping in `fuel.js`. An acceptance test uses such a label and asserts it is shown literally. |
| Integer-like labels (a numbered bar gauge) are shown out of order. | Options are built from an ordered array, not an object. An acceptance test uses numeric labels configured out of numeric order. |
| An existing settings module defines `FUEL_LEVELS` for some other purpose and now fails validation. | Unlikely (the name is new). The error names the setting, so it is fixable at once. |
| Testing import-time `SystemExit` pollutes the shared `settings` module. | Tested in a subprocess, never via `importlib.reload` (research R7). |
