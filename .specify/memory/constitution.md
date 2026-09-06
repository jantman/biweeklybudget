<!--
SYNC IMPACT REPORT
==================
Version change: (unversioned template) → 1.0.0
Rationale: Initial ratification. The previous file was the unfilled scaffold with
every placeholder intact, so this is the first substantive constitution.

Modified principles: none (initial adoption; no prior named principles existed)

Added sections:
  - Core Principles
    - I. Spec-Driven Change (NON-NEGOTIABLE)
    - II. The Test Gate (NON-NEGOTIABLE)
    - III. Schema Changes Ship With Reversible Migrations
    - IV. Documentation Is Part Of The Change
    - V. Escalate Instead Of Guessing
    - VI. Versioned, Changelogged Releases
  - Technology & Security Constraints (SECTION_2)
  - Development Workflow (SECTION_3)
  - Governance

Removed sections: none

Source material: docs/source/development.rst (Guidelines, Testing, Alembic DB
Migrations, Release Checklist), tox.ini, pytest.ini, CLAUDE.md, README.rst, and the
feature-development rules removed from docs/features/README.md in commit ffcf21f,
which this constitution now supersedes.

Follow-up TODOs: none. RATIFICATION_DATE is set to the date of this initial
adoption rather than deferred, since no earlier constitution existed.
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

### VI. Versioned, Changelogged Releases

`biweeklybudget/version.py` MUST be incremented per Semantic Versioning for the scope
of the change, and `CHANGES.rst` MUST gain a matching entry in the existing format,
as part of completing a feature. New Python files MUST carry the standard AGPL v3
copyright header used throughout the source tree.

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
   feature, bump `version.py`, add the `CHANGES.rst` entry, push, and open a detailed
   pull request. All CI checks MUST pass before merge.
7. **Release**: follow the Release Checklist in `docs/source/development.rst` —
   changelog entries complete, version incremented, changelog header dated, docs
   regenerated via `tox -e docs -e jsdoc -e screenshots` and committed, merged to
   `master`, then tagged.

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

**Version**: 1.0.0 | **Ratified**: 2026-09-06 | **Last Amended**: 2026-09-06
