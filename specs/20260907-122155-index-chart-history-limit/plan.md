# Implementation Plan: Index Page Account Balances Chart — History Limiting

**Branch**: `robot-army/issue-279-fix-index-page-chart-when-lots-of-data` | **Date**: 2026-09-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/20260907-122155-index-chart-history-limit/spec.md`

## Summary

The index page's Account Balances chart loads every `AccountBalance` row ever recorded and
plots all of them. At five years of daily balances this is slow and illegible (GitHub issue
#279).

The fix has three parts, in order of how much they matter:

1. **Stop the N+1.** The view resolves each balance's account name through the
   `AccountBalance.account` relationship — one lazy `SELECT` per row, ~18,000 of them at the
   reporter's scale — for a name it already has in a dict it built two lines earlier. Using
   that dict is a one-line change and is the single largest win available.
2. **Bound the query.** The endpoint takes an optional `days` parameter, defaulting to a new
   `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` setting (365), and filters on `overall_date` in SQL.
   A small seed query supplies each account's last balance *before* the window, so dormant
   accounts keep their carried-forward line instead of vanishing or reading as zero.
3. **Bound the payload.** After forward-filling, the date rows are sampled at a regular
   stride down to at most `ACCOUNT_BALANCE_CHART_MAX_POINTS` (300), always keeping the most
   recent point so the chart's right-hand edge agrees with the account tables below it.

The "zoom out" the issue asks for is a Bootstrap 3 button group in the panel heading
(1m/3m/6m/1y/2y/5y/All) that re-fetches and calls Morris's `setData()` in place. The
existing charting library is kept: issue #215's library migration is separate work, and the
constitution forbids introducing a parallel frontend stack. The server side is
library-agnostic, so #215 can later replace the button group without touching it.

No schema change, no migration, no new dependency.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, MariaDB/MySQL (server); jQuery, Bootstrap 3,
Morris.js (client). No new dependency is added.

**Storage**: MariaDB/MariaDB — existing `account_balances` and `accounts` tables, read only.

**Testing**: pytest. Unit tests (`tox -e py314`), Selenium acceptance tests
(`tox -e acceptance`), Alembic model-match tests (`tox -e migrations`), Sphinx
(`tox -e docs`), jsdoc (`tox -e jsdoc`).

**Target Platform**: Self-hosted Flask app on localhost, single trusted operator.

**Project Type**: Server-rendered web application with AJAX endpoints; single Python package.

**Performance Goals**: Default index-page chart view returns a bounded ≤300 dates
irrespective of stored history, and issues O(accounts) queries rather than O(balance rows).
Chart visible and readable within a few seconds at five years × ten accounts, against tens
of seconds today.

**Constraints**: Response shape of `/ajax/chart-data/account-balances` must stay
backward-compatible for external scripts. Forward-filled account lines must remain
continuous — a windowed query must not make a dormant account read as `$0`. Existing
installations must upgrade with no settings changes required.

**Scale/Scope**: ~10 accounts; up to ~20,000 `AccountBalance` rows today and growing daily.
One view class, one JS file, one template, one settings module, plus tests and docs.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v1.0.0. Gate evaluated before Phase 0 and
re-evaluated after Phase 1 design; both passes recorded below.*

| Principle | Assessment | Verdict |
|-----------|------------|---------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Specified, planned, then implemented, in that order, on the feature branch `robot-army/issue-279-fix-index-page-chart-when-lots-of-data`. One feature only. Decomposed into milestones in `tasks.md`. | ✅ PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | Full unit and acceptance suites run to completion before the feature is declared done; `migrations` and `docs` also run. New logic is covered by unit tests of the sampling/parsing helpers and by an acceptance test that seeds thousands of synthetic balances — the bound is the point of the feature, so a test that never sees large data would be a test written to pass. pycodestyle/pyflakes clean under `pytest.ini`. No narrowing to a subset; any timeout is raised and the suite re-run. | ✅ PASS |
| **III. Schema Changes Ship With Reversible Migrations** | No change to `biweeklybudget/models/`. No migration needed. `tox -e migrations` is still run, as the check that this remains true. | ✅ PASS (not applicable) |
| **IV. Documentation Is Part Of The Change** | `docs/source/app_usage.rst` gains an Account Balances Chart section; the two new settings are documented by `#:` comments in `settings.py` (autodoc'd into `biweeklybudget.settings.rst`) and mirrored in `settings_example.py`; `docs/source/http_api.rst` is checked and updated if it covers this endpoint; `tox -e docs` must build clean; `tox -e jsdoc` regenerates `jsdoc.index.rst`, which is committed. | ✅ PASS |
| **V. Escalate Instead Of Guessing** | The one genuine fork — whether to do this on the current chart library or wait for #215 — is resolved in research R2 against the constitution's own stack constraint and recorded in the spec's Assumptions, not guessed at silently. Concrete numeric defaults are recorded with reasoning in R4 and are settings, so they are not one-way doors. No other ambiguity was found; no `[NEEDS CLARIFICATION]` markers remain. | ✅ PASS |
| **VI. Versioned, Changelogged Releases** | `version.py` `1.9.0` → `1.10.0` (MINOR: new user-visible capability and new settings, nothing removed, no incompatible response change). Matching `CHANGES.rst` entry in the established per-issue format. No new Python files need a copyright header beyond the new unit test module, which gets the standard AGPL v3 header. | ✅ PASS |
| **Tech constraints — existing frontend stack** | jQuery + Bootstrap 3 + the already-bundled Morris.js. No new charting library, no parallel frontend stack. This is the explicit reason #215 is deferred rather than folded in. | ✅ PASS |
| **Tech constraints — financial correctness** | This changes no pay-period arithmetic, budget allocation, interest or payoff calculation, and writes nothing. The one correctness risk it *does* introduce is presentational and is treated as a first-class requirement: a windowed query must not make a dormant account's line read as zero. Hence the pre-window seed query (research R5) and guarantee G5, with its own test. | ✅ PASS |
| **Tech constraints — security posture / secrets** | Read-only endpoint, no new surface, no credentials, no change to the localhost-only assumption. | ✅ PASS |
| **Tech constraints — test data safety** | Acceptance tests use the existing `refreshdb` fixture against the test database only. The synthetic large dataset is created inside that fixture's database, never pointed at real data. | ✅ PASS |

**Gate result: PASS, both before Phase 0 and after Phase 1 design.** No violations, so the
Complexity Tracking table below is empty.

**Workflow note.** Constitution §Development Workflow steps 3 and 5 require human approval
of the plan and at each milestone boundary. This session was dispatched to run the full
lifecycle autonomously through to an opened pull request, which is the dispatcher's decision
to make and is recorded here rather than treated as silently absent. The pull request is the
review artifact; nothing is merged without it.

## Project Structure

### Documentation (this feature)

```text
specs/20260907-122155-index-chart-history-limit/
├── spec.md              # Feature specification (/speckit-specify)
├── plan.md              # This file (/speckit-plan)
├── research.md          # Phase 0 output — R1..R9
├── data-model.md        # Phase 1 output — entities, invariants, settings
├── quickstart.md        # Phase 1 output — validation scenarios
├── contracts/
│   └── http-api.md      # Phase 1 output — endpoint + client contract
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
biweeklybudget/
├── settings.py                              # + ACCOUNT_BALANCE_CHART_DEFAULT_DAYS,
│                                            #   ACCOUNT_BALANCE_CHART_MAX_POINTS,
│                                            #   both added to _INT_VARS
├── settings_example.py                      # mirror the two new settings
├── version.py                               # 1.9.0 -> 1.10.0
├── flaskapp/
│   ├── views/
│   │   └── index.py                         # AcctBalanaceChartView: drop the N+1,
│   │                                        #   window by days, seed the forward-fill,
│   │                                        #   sample; + module-level helpers
│   ├── templates/
│   │   └── index.html                       # range button group in the panel heading;
│   │                                        #   emit the default-days JS var
│   └── static/js/
│       └── index.js                         # named, JSDoc'd functions; range handling;
│                                            #   Morris setData(); empty-data message
└── tests/
    ├── unit/flaskapp/views/
    │   └── test_index.py                    # NEW - helper logic, no database
    └── acceptance/flaskapp/views/
        └── test_index.py                    # + chart rendering, range selector,
                                             #   endpoint windowing, large-data bound

docs/source/
├── app_usage.rst                            # + Account Balances Chart section
├── http_api.rst                             # + days parameter if endpoint is covered
└── jsdoc.index.rst                          # generated by tox -e jsdoc, committed

CHANGES.rst                                  # + 1.10.0 entry
```

**Structure Decision**: The existing single-package layout is used unchanged. This feature
touches one view class, its template, its JavaScript, the settings module, and the
corresponding tests and docs. No new package, module hierarchy, or architectural layer is
introduced — the work is a query fix plus a presentation control, and inventing structure
for it would be the wrong kind of investment.

The one structural judgement call is extracting the `days` parsing and the interval sampling
out of `AcctBalanaceChartView.get()` into module-level helper functions. This is not
speculative layering: it is what makes the invariants in `data-model.md` testable without a
database or a Selenium session, following the precedent of
`tests/unit/flaskapp/views/test_formhandlerview.py`.

## Complexity Tracking

*No Constitution Check violations. Nothing to justify.*
