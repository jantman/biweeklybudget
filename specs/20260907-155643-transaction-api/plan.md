# Implementation Plan: Transaction API — Name-or-ID Lookup and Console Script

**Branch**: `robot-army/issue-322-implement-the-transaction-http-api-and` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260907-155643-transaction-api/spec.md`

## Summary

Make `POST /forms/transaction` usable by external tooling that knows Accounts and Budgets
by name, and ship a console script that proves it.

Two changes, no schema change and no new dependency:

1. **Resolution at the edge.** A single helper resolves an Account or Budget from either a
   numeric ID or a name. `TransactionFormHandler.validate()` calls it for the three fields
   that identify records — `account`, each key of `budgets`, and `credit_payment_acct` —
   and **rewrites `data` in place to canonical numeric IDs**. Everything downstream
   (`submit()`, and every existing validation rule) then sees exactly the request shape it
   sees today. This is the same in-place-normalization pattern
   `FormHandlerView.normalize_currency()` already uses for currency fields, and it is what
   keeps the blast radius to one method.
2. **A console entry point**, `addtrans`, that builds the JSON body from command-line
   arguments and posts it over HTTP — deliberately over HTTP rather than against the
   database, because the point of the proof of concept is to exercise the API contract.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, `requests` (already in `requirements.txt`,
used by the console script). No new dependency.

**Storage**: MySQL/MariaDB. No schema change; no Alembic migration.

**Testing**: pytest. Unit tests (`biweeklybudget/tests/unit/`) with mocked sessions;
acceptance tests (`biweeklybudget/tests/acceptance/`) against a live Flask app and a real
database, which is where the endpoint behaviour is pinned.

**Target Platform**: Linux; the app also ships as a Docker image.

**Project Type**: Flask web service plus a set of console entry points.

**Performance Goals**: Not a factor. Resolution adds at most one indexed lookup per
identifier per request, on tables with tens of rows.

**Constraints**: Backward compatibility of `POST /forms/transaction` is absolute — the web
UI posts to it. Existing ID-based requests must be byte-for-byte equivalent in behaviour.

**Scale/Scope**: One helper function, one modified `validate()` method, one new module of
roughly 200 lines, plus tests and documentation.

## Constitution Check

*GATE: evaluated before Phase 0, re-evaluated after Phase 1 design. Constitution v1.0.0.*

| Principle | Assessment | Verdict |
|-----------|-----------|---------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Spec written before plan; plan before code; work stays on the existing feature branch `robot-army/issue-322-implement-the-transaction-http-api-and`; decomposed into milestones below. One feature at a time. | PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | Full unit and acceptance suites run to completion before the feature is declared done. `setup.py` gains a console script, which is a packaging change, so the **Docker suite is also in scope**. New code covered by unit tests for the helper and the script, and acceptance tests for the endpoint. pycodestyle/pyflakes clean. | PASS |
| **III. Schema Changes Ship With Reversible Migrations** | No change under `biweeklybudget/models/` to any `Column`, table or model class. A pure-function helper is added to `biweeklybudget/models/utils.py`, which defines no models. No migration required, and the `migrations` suite is unaffected. | PASS (N/A) |
| **IV. Documentation Is Part Of The Change** | `docs/source/http_api.rst` (name-or-ID on three fields, resolution rule, worked example), `docs/source/getting_started.rst` (the new entry point in the Command Line Entrypoints list), a new `docs/source/biweeklybudget.addtrans.rst` wired into `docs/source/biweeklybudget.rst`. `tox -e docs` must build clean. | PASS |
| **V. Escalate Instead Of Guessing** | Three judgement calls are recorded as decisions in [research.md](./research.md) with their alternatives, rather than resolved silently. None of them changes the feature's scope; all are reversible. | PASS |
| **VI. Versioned, Changelogged Releases** | `biweeklybudget/version.py` 1.10.0 → **1.11.0** (new backward-compatible capability = MINOR). `CHANGES.rst` gains a matching entry in the established format. The new module carries the standard AGPL v3 header. | PASS |
| **Technology & Security Constraints** | Python 3.14, Flask/SQLAlchemy, MySQL. No new dependency, no licence question. **Security posture unchanged**: the endpoint already accepts unauthenticated writes from anything that can reach it; accepting a name where it accepted an ID adds no authority. The script assumes localhost and needs no credentials. No secrets introduced. | PASS |
| **Financial correctness** | This feature does not touch pay-period arithmetic, budget allocation, interest, or payoff calculations. It changes only how a record is *addressed*, never what is computed. The rule that budget amounts must sum to the transaction amount is untouched and still enforced server-side. | PASS |

**Result: no violations. Complexity Tracking section omitted as empty.**

Re-check after Phase 1 design: unchanged. The design added no new endpoint, no new
setting, no new model, and no new dependency, so no gate moved.

## Key Design Decisions

Full reasoning in [research.md](./research.md); the contract is in
[contracts/transaction-create.md](./contracts/transaction-create.md).

- **Extend the existing endpoint, do not add a parallel one.** Issue #322 permits either.
  A second endpoint would mean two copies of the inactive-budget rule, the budget-sum
  rule and the credit-account rule — and the copies would drift. The existing endpoint is
  already documented in `docs/source/http_api.rst`.
- **Resolve in `validate()`, mutating `data` to canonical IDs.** `submit()` and every
  existing rule stay untouched, which is what makes "existing ID callers are unaffected"
  something the diff shows rather than something the tests have to prove.
- **Digits-first with a name fallback.** A value of `"123"` is looked up as ID 123; only
  if no such record exists is it tried as the name `"123"`. This keeps the overwhelmingly
  common case unambiguous while leaving a numerically-named record reachable.
- **Case-insensitive, whitespace-stripped exact matching.** No prefix or fuzzy matching:
  a mistyped name must fail loudly, not silently hit the wrong budget. Money is involved.
- **The script posts HTTP, not SQL.** It is the proof that the API works.

## Project Structure

### Documentation (this feature)

```text
specs/20260907-155643-transaction-api/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output: decisions and alternatives
├── data-model.md        # Phase 1 output: entities and resolution rules
├── quickstart.md        # Phase 1 output: how to validate the feature end to end
├── contracts/
│   ├── transaction-create.md   # POST /forms/transaction, as amended
│   └── addtrans-cli.md         # Console script interface
├── checklists/
│   └── requirements.md
└── tasks.md             # Created by /speckit-tasks, not by this command
```

### Source Code (repository root)

```text
biweeklybudget/
├── models/
│   └── utils.py                       # MODIFIED: add resolve_by_name_or_id()
├── flaskapp/
│   └── views/
│       └── transactions.py            # MODIFIED: TransactionFormHandler.validate()
├── addtrans.py                        # NEW: the console script
└── tests/
    ├── unit/
    │   ├── models/
    │   │   └── test_utils.py          # MODIFIED: helper unit tests
    │   └── test_addtrans.py           # NEW: script unit tests
    └── acceptance/
        └── flaskapp/
            └── views/
                └── test_transactions.py   # MODIFIED: name-based endpoint tests

setup.py                               # MODIFIED: addtrans console_scripts entry
CHANGES.rst                            # MODIFIED: 1.11.0 entry
biweeklybudget/version.py              # MODIFIED: 1.10.0 -> 1.11.0
docs/source/
├── http_api.rst                       # MODIFIED: name-or-ID on three fields
├── getting_started.rst                # MODIFIED: addtrans in entrypoint list
├── biweeklybudget.rst                 # MODIFIED: toctree entry
└── biweeklybudget.addtrans.rst        # NEW: module API page
```

**Structure Decision**: The existing layout is used as-is. The helper goes in
`biweeklybudget/models/utils.py` because it is a model-level lookup concern and that
module already exists for exactly this kind of cross-model utility
(`do_budget_transfer()`); putting it in the view would make it unreachable from the next
form handler that needs it. The console script sits at package top level beside
`wishlist2project.py`, `ofxgetter.py` and `initdb.py`, matching how every other entry
point in this project is laid out.

## Milestones

Human approval is required to advance between milestones (Constitution I). Each milestone
closes with its tests run, its documentation updated, and one commit prefixed
`Transaction API - M{n}.{t}`.

### M1 — Resolution helper

`resolve_by_name_or_id()` in `biweeklybudget/models/utils.py`, with unit tests covering:
ID hit, name hit, case and whitespace insensitivity, digits-first precedence, the
numerically-named fallback, miss returns `None`, and empty/`None`/non-string input.

### M2 — Endpoint accepts names

`TransactionFormHandler.validate()` resolves and canonicalizes `account`, `budgets` keys
and `credit_payment_acct`; rejects unresolvable values with field-level errors naming the
offending value; rejects a `budgets` mapping in which two keys resolve to the same Budget.
Acceptance tests for each field by name, for mixed ID/name requests, for each failure, and
for the existing ID-only behaviour still passing untouched.

### M3 — `addtrans` console script

New module and `setup.py` entry point; argument parsing, payload construction, HTTP POST,
success/validation-error/transport-error handling, `--dry-run`, and verbosity flags
matching the project's other scripts. Unit tests with `requests.post` mocked.

### M4 — Documentation, version, changelog

`http_api.rst`, `getting_started.rst`, the new module page and its toctree entry;
`version.py` to 1.11.0; the `CHANGES.rst` entry. `tox -e docs` clean.

### M5 — Full verification and pull request

Unit, acceptance and Docker suites run to completion and pass; branch pushed; pull request
opened; CI green; review comments answered.
