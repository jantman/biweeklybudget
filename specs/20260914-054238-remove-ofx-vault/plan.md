# Implementation Plan: Remove OFX Downloading, Vault and Keychain

**Branch**: `robot-army/issue-265-deprecate-ofx-and-remove-vault-and` | **Date**: 2026-09-14 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/20260914-054238-remove-ofx-vault/spec.md`

## Summary

Delete the OFX download/import stack (three console scripts, two `/api/ofx` endpoints,
the `ofxapi` package, the vendored `ofxclient`, the Vault client, the screen-scraper
base class), the three settings and three Account columns that only configured it,
and the five packages only it needed (`hvac`, `keyring`, `SecretStorage`, `ofxhome`,
`ofxparse`). Drop the columns with a reversible Alembic migration. Keep everything
Plaid uses, including the "OFX"-named models, page and `negate_ofx_amounts`. Update
tests, docs, screenshots, the Docker build checks, `CLAUDE.md`, the changelog, and
(as a separate PATCH amendment) the constitution's Secrets rule.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask 3.1, SQLAlchemy 2.0, Alembic 1.19; frontend jQuery +
Bootstrap 3 + DataTables (only `accounts_modal.js` changes)

**Storage**: MySQL/MariaDB; one migration dropping three `accounts` columns

**Testing**: pytest via tox — `py314`, `acceptance`, `migrations`, `docs`, `jsdoc`,
`screenshots`, `docker`

**Target Platform**: Linux server / Docker image, localhost use

**Project Type**: Web application (Flask) plus console scripts, single package

**Performance Goals**: N/A (removal)

**Constraints**: No change to Plaid behaviour, reconciliation, or any financial
calculation; existing data other than the three columns untouched

**Scale/Scope**: ~12 modules/packages deleted (~4k lines incl. vendored code), ~25
files edited, 1 migration + test, ~10 doc stubs deleted

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment | Status |
|---|---|---|
| I. Spec-Driven Change | Spec, plan, tasks under `specs/20260914-054238-remove-ofx-vault/`; work on the session's feature branch. One implementation milestone (M1); the work is a single coherent removal whose parts cannot ship separately without leaving broken references, so splitting would only add approval stops. The PR is the human review/approval point. | PASS |
| II. Test Gate | Full `py314` and `acceptance` suites run to completion; `migrations` (schema change) and `docker` (packaging change) also required and run. pycodestyle/pyflakes clean via the `py314` env. New migration gets a `MigrationTest`; removed-endpoint and ignored-settings behaviour get tests. | PASS |
| III. Reversible Migrations | New migration with `upgrade()` and `downgrade()`; downgrade restores the original column types/positions; round-trip tested; `test_model_and_migration_schemas_are_the_same` verifies head = models. No new model classes. | PASS |
| IV. Documentation | README, `CLAUDE.md`, `docs/source/` (ofx page deleted, getting started, concepts, plaid, flask_app, http_api, apidoc stubs), screenshots updated in this change; `docs` env must build. | PASS |
| V. Escalate Instead Of Guessing | The one scope question (whether "OFX stuff" includes the Plaid-used OFX models) is resolved by the code: removing them removes Plaid. Decision recorded in spec Assumptions and research R1 and called out in the PR for review. No side quests. | PASS |
| VI. Changelog; No Version Bump | Concise `Unreleased` entry, marked breaking, listing removed commands/endpoints/settings/fields and the migration; `version.py` untouched. | PASS |
| Tech & Security: Secrets | The constraint "OFX credentials live in Hashicorp Vault" becomes obsolete. Corrected by a PATCH amendment (2.1.1 → 2.1.2) in its own commit, per Governance. Removing an unpickling HTTP endpoint (`POST /api/ofx/statement`) and a credentials store reduces attack surface; no new exposure. | PASS (with amendment) |
| Tech: License | Only removals of dependencies. | PASS |
| Tech: Financial correctness | No change to pay-period, budget, interest or payoff code. Interest-charge detection over OFX transactions is unchanged. | PASS |

**Post-design re-check**: data-model.md and contracts/ introduce no new entities,
endpoints or dependencies; all rows above still PASS.

## Project Structure

### Documentation (this feature)

```text
specs/20260914-054238-remove-ofx-vault/
├── spec.md
├── plan.md                         # this file
├── research.md                     # decisions R1–R7
├── data-model.md                   # Account columns dropped; migration shape
├── quickstart.md                   # validation commands
├── contracts/removed-interfaces.md # scripts, endpoints, settings, fields, modules
├── checklists/requirements.md
└── tasks.md                        # /speckit-tasks
```

### Source Code (repository root)

```text
biweeklybudget/
├── ofxgetter.py                 # DELETE
├── backfill_ofx.py              # DELETE
├── vault.py                     # DELETE
├── screenscraper.py             # DELETE
├── ofxapi/                      # DELETE (package)
├── vendored/                    # DELETE (only ofxclient)
├── settings.py                  # drop 3 settings
├── settings_example.py          # drop 3 settings
├── models/account.py            # drop 3 columns + for_ofxgetter/ofxgetter_config/set_ofxgetter_config
├── models/ofx_transaction.py    # drop params_from_ofxparser_transaction
├── alembic/versions/<rev>_remove_ofxgetter_account_fields.py   # NEW
├── flaskapp/views/ofx.py        # drop OfxAccounts, OfxStatementPost + routes + imports
├── flaskapp/views/accounts.py   # drop 3 fields from validate/submit
├── flaskapp/static/js/accounts_modal.js  # drop 3 form fields + fill code
└── tests/
    ├── fixtures/{sampledata.py,test_settings.py}      # drop fields/settings
    ├── fixtures/CreditOne_2017-07-28_05-30-00.ofx     # DELETE
    ├── docker_build.py                                # drop 3 command checks
    ├── migrations/test_migration_<rev>.py             # NEW
    ├── unit/{test_settings_*.py, models/test_ofx_transaction.py, test_interest.py}
    └── acceptance/{flaskapp/views/test_ofx.py, test_accounts.py, …}
setup.py, requirements.txt, setup.cfg, pytest.ini, .coveragerc, tox.ini
README.rst, CLAUDE.md, CHANGES.rst, .specify/memory/constitution.md
docs/make_screenshots.py, docs/source/{index,getting_started,concepts,plaid,flask_app,http_api,biweeklybudget}.rst
docs/source/ofx.rst + 9 removed-module apidoc stubs       # DELETE
docs/source/account1*.png                                  # regenerated
```

**Structure Decision**: Existing single-package layout; this feature only deletes
and edits files within it, plus one new migration and its test.

## Delivery Order (single milestone M1)

1. Delete the modules, vendored tree, console scripts and `/api/ofx` routes; remove
   the dependency pins; clean config excludes. (App still runs; tests referencing
   removed code are removed in the same step.)
2. Remove the settings (+ unit test that leftover definitions are ignored).
3. Remove the Account columns/members, add the migration + migration test, update
   the form handler, modal JS, sample data and the tests that set the fields.
4. Docs, `CLAUDE.md`, screenshot description, apidoc stubs, Docker checks.
5. Changelog entry. Constitution PATCH amendment as its own commit.
6. Test gate: `py314`, `acceptance`, `migrations`, `docker`, `docs`, `jsdoc`,
   `screenshots` (not concurrently with `docs`); commit changed screenshots.

## Complexity Tracking

No violations to justify.
