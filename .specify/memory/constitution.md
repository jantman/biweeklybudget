<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 2.0.0
Rationale: MAJOR. Principle VI is redefined in a backward-incompatible way: under
1.0.0 every completed feature was REQUIRED to increment version.py; under 2.0.0 doing
so is PROHIBITED. A change prepared under the previous wording is non-compliant under
the new one. Motivation: per-feature bumps produced version numbers that were never
released (remote tags stop at 1.6.0 while version.py reached 1.12.1), so a version
number no longer identified anything a user could install.

Modified principles:
  - VI. Versioned, Changelogged Releases → VI. Changelog Every Change; Release Only
    On Request (changes go under an "Unreleased" heading in CHANGES.rst; version
    bumps, tags and releases only on explicit maintainer request, per SemVer 2.0.0)

Modified sections:
  - Development Workflow, step 6 (Complete the feature): no longer bumps version.py
  - Development Workflow, step 7 (Release): only on explicit request; version chosen
    per SemVer 2.0.0 from the accumulated Unreleased entries

Added sections: none
Removed sections: none

Dependent files updated in the same change: CLAUDE.md, docs/source/development.rst
(Guidelines, Release Checklist), .github/PULL_REQUEST_TEMPLATE.md, CHANGES.rst.
.specify/templates/*: checked; none restate the version-bump rule (plan-template's
Constitution Check is derived from this file at runtime). No update needed.

Follow-up TODOs: none.

Previous amendment: 1.0.0 (2026-09-06), initial ratification, derived from
docs/source/development.rst, tox.ini, pytest.ini, CLAUDE.md, README.rst, and the
feature-development rules removed from docs/features/README.md in commit ffcf21f.
-->

# biweeklybudget Constitution

## Core Principles

### I. Spec-Driven Change (NON-NEGOTIABLE)

Every non-trivial change — anything beyond a few mechanical edits — MUST begin as a
written specification under `specs/`, MUST be planned before it is implemented, and
MUST be developed on a Git feature branch named for the feature. Planning and
implementation are separate, sequential steps: the plan is produced and reviewed
first, then the code follows it.

Features MUST be worked one at a time, from specification through implementation to
verification, before the next one is started. Earlier features routinely change the
right answer for later ones; batching them forfeits that information.

Non-trivial features MUST be decomposed into milestones and tasks. Human approval is
REQUIRED to advance from one milestone to the next.

### II. The Test Gate (NON-NEGOTIABLE)

No feature is complete while any test fails. Before a feature is declared done, the
complete unit and acceptance suites MUST be run to completion and MUST all pass.
Migration and Docker suites MUST pass for any change that touches schema or packaging.

A suite that times out has not passed. When a suite times out, the timeout MUST be
raised — both the pytest timeout and the invoking tool's timeout — and the suite
re-run until it completes. Narrowing the run to a passing subset, marking failures
as expected, or reporting a timed-out run as green all violate this principle.

Code MUST be pycodestyle- and pyflakes-clean under the exceptions declared in
`pytest.ini`, and new code MUST be covered by valid tests, not tests written to pass.

Rationale: this application computes the author's real finances. A red suite is the
only cheap signal that the math broke.

### III. Schema Changes Ship With Reversible Migrations

Any change to `biweeklybudget/models/` MUST ship in the same change with an Alembic
migration in `biweeklybudget/alembic/versions/`. Every migration MUST implement both
`upgrade()` and `downgrade()`, and both directions MUST be tested before commit.

Migration column definitions MUST exactly match their model definitions; the
`migrations` tox environment verifies that head matches the models, and it MUST pass.
New model classes MUST be imported in `models/__init__.py` so Alembic can see them.

When autogenerate is used, the test database MUST be initialized to the current head
via `initdb` BEFORE model changes are made. Otherwise autogenerate sees no diff and
silently produces an empty migration.

### IV. Documentation Is Part Of The Change

A change is not finished until the documentation that describes it is updated in the
same change. This covers `README.rst`, `CLAUDE.md`, and `docs/source/`. The `docs`
tox environment MUST build without errors.

Rationale: documentation corrected later is documentation corrected never, and this
project's setup and migration docs are the only recoverable record of how to operate it.

### V. Escalate Instead Of Guessing

Work MUST stop and ask for human guidance when: the path forward is unclear, a
significant decision arises that the approved plan did not cover, or changes are being
made and reverted without a definite direction. Guessing at intent is a defect, not
initiative.

Deviations from the current feature ("side quests") MUST be recorded in the feature's
spec — stating precisely where the work departed and what is needed to resume — and
that record MUST be committed before the deviation begins.

### VI. Changelog Every Change; Release Only On Request

Every change MUST add an entry, in the existing format, at the top of `CHANGES.rst`
under an `Unreleased` heading, creating that heading directly beneath the `Changelog`
title if it is absent. Completing a feature or opening a pull request MUST NOT
increment `biweeklybudget/version.py`, create a tag, or cut a release.

Version increments, tags, and releases happen only when the maintainer explicitly
requests a release. The new version MUST then be chosen per Semantic Versioning 2.0.0
from all `Unreleased` entries accumulated since the last release: MAJOR if any change
is backwards-incompatible for users, otherwise MINOR if any adds functionality,
otherwise PATCH. The `Unreleased` heading MUST then be renamed to `X.Y.Z (YYYY-MM-DD)`,
and the tag MUST be exactly the version number.

Rationale: bumping the version with every feature produced numbers that were never
released (1.7.0 through 1.12.1 were never tagged), so a version stopped identifying
anything a user could install. Accumulating entries under `Unreleased` keeps the
changelog current while making each version number correspond to a real release.

New Python files MUST carry the standard AGPL v3 copyright header used throughout
the source tree.

## Technology & Security Constraints

- **Runtime**: Python 3.14. MySQL or MariaDB is REQUIRED; MySQL-specific SQL modes and
  options are used deliberately and MUST NOT be traded away for portability to an
  untested engine.
- **Stack**: Flask and SQLAlchemy on the backend; jQuery, Bootstrap 3, and DataTables
  on the frontend. New UI work MUST follow the existing modal/DataTables patterns
  rather than introducing a parallel frontend stack.
- **License**: GNU Affero General Public License v3 or later. Dependencies whose
  licenses are incompatible with AGPLv3 distribution MUST NOT be added.
- **Security posture**: This application is designed for localhost use by a single
  trusted operator and holds account numbers and financial history. It MUST NOT be
  given features that presume safe public exposure, and no change may weaken that
  assumption without saying so explicitly.
- **Secrets**: Credentials MUST NOT be committed. OFX credentials live in Hashicorp
  Vault; Plaid and database credentials come from environment variables or the
  settings module named by `SETTINGS_MODULE`.
- **Financial correctness**: Changes to pay-period arithmetic, budget allocation,
  interest, or payoff calculations MUST be accompanied by tests that pin the expected
  numbers. These paths are the reason the project exists.
- **Test data safety**: Acceptance tests drop and reload the database. They MUST NEVER
  be pointed at a real database.

## Development Workflow

1. **Branch**: Create a feature branch off `master` before any work begins.
2. **Specify**: Write the specification, then the plan, then the task breakdown, using
   the Spec Kit commands. Solicit human input on anything ambiguous during planning
   rather than resolving it silently.
3. **Approve**: Obtain human approval of the plan before implementing, and again at
   each milestone boundary.
4. **Implement**: Work the tasks in dependency order. Commit messages MUST begin with
   the milestone/task prefix in the form `{Feature Name} - {Milestone}.{Task}`,
   followed by a one-sentence summary and then further detail.
5. **Close each milestone**, in this order:
   a. Run the unit, acceptance, and (where relevant) Docker and migration suites to
      completion with everything passing.
   b. Update all affected documentation.
   c. Update the feature's spec artifacts to record progress.
   d. Commit the whole of the above together.
6. **Complete the feature**: after all tests pass and the human has verified the
   feature, add the `CHANGES.rst` entry under `Unreleased` (Principle VI), push, and
   open a detailed pull request. Do not change `version.py`. All CI checks MUST pass
   before merge.
7. **Release** — only when the maintainer explicitly requests one: follow the Release
   Checklist in `docs/source/development.rst` — `Unreleased` entries complete, version
   chosen per Semantic Versioning 2.0.0 and set in `version.py`, `Unreleased` heading
   renamed to the version and release date, docs regenerated via
   `tox -e docs -e jsdoc -e screenshots` and committed, merged to `master`, then tagged
   with exactly the version number.

## Governance

This constitution supersedes other development practices for this repository,
including any conflicting guidance in `CLAUDE.md` or the feature-workflow notes it
replaces. Where `CLAUDE.md` gives operational detail (commands, paths, environment
variables) it remains authoritative for that detail; where it conflicts on a rule,
this document wins.

**Amendments** MUST be made by updating this file, MUST state the rationale for the
change in the Sync Impact Report, and MUST be committed as their own change.

**Versioning** of this constitution follows Semantic Versioning:

- **MAJOR**: a principle is removed, or redefined in a way that invalidates work done
  under the previous wording.
- **MINOR**: a principle or section is added, or existing guidance is materially
  expanded.
- **PATCH**: clarifications, wording, and typo fixes that do not change what is required.

**Compliance**: Pull requests and reviews MUST verify compliance with these principles.
Any complexity or deviation MUST be justified in writing in the pull request; an
unjustified deviation is grounds to reject the change. Principles marked
NON-NEGOTIABLE are not subject to case-by-case waiver — changing them requires
amending this constitution first.

**Version**: 2.0.0 | **Ratified**: 2026-09-06 | **Last Amended**: 2026-09-10
