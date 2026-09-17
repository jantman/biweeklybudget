# Implementation Plan: Show Inactive Accounts So They Can Be Re-Activated

**Branch**: `robot-army/issue-276-inability-to-re-activate-an-account` | **Date**: 2026-09-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260917-053603-show-inactive-accounts/spec.md`

## Summary

Deactivating an Account removes it from all three tables on the Accounts page, which is the
only place its edit modal can be reached — so unchecking one checkbox strands the account
behind a hand-written SQL `UPDATE` ([issue #276](https://github.com/jantman/biweeklybudget/issues/276)).

The flag itself already works: the form handler writes `is_active` on every save and the modal
reads it back into the checkbox. The only broken link is that `accounts.html` is rendered from
queries filtered to `is_active == True`. Dropping that filter and marking the resulting rows
the way `budgets.html` already marks inactive budgets — a leading "Active?" column plus the
shared `tr.inactive` grey — restores the round trip with no model, form, or JavaScript change.

Three smaller things ride along because surfacing these rows makes them reachable: the two
duplicated view methods that both carry the filter are collapsed into one helper; the
"stale data" red is suppressed on inactive rows, where it would fire on every row and mean
nothing; and the balance-derived cells are guarded so an account with no recorded balance or
credit limit costs one blank cell rather than a 500 on the whole page.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, Jinja2 (backend); jQuery, Bootstrap 3, DataTables (frontend) — no new dependency

**Storage**: MySQL / MariaDB. **No schema change**; `accounts.is_active` already exists

**Testing**: pytest — unit (`biweeklybudget/tests/unit/`) and Selenium acceptance (`biweeklybudget/tests/acceptance/`), run via `tox`

**Target Platform**: Flask web application, localhost single-operator use

**Project Type**: Web application (server-rendered Jinja templates + jQuery, single package)

**Performance Goals**: Unchanged. The three listing queries lose a `WHERE` clause and return a
handful more rows for a single operator's account list; no new query, no N+1

**Constraints**: No figure displayed anywhere else in the application may change (spec SC-005).
New UI must follow the existing Bootstrap 3 / Jinja table patterns rather than introducing new
styling (constitution: Technology & Security Constraints)

**Scale/Scope**: 1 template, 1 view module, 1 docs page, 1 screenshot caption; on the order of
tens of accounts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against `.specify/memory/constitution.md` v2.1.2.

| Principle | Status | How this plan satisfies it |
|-----------|--------|----------------------------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | PASS | Spec written and committed (`f910a8b`) before planning; this plan precedes implementation; work is on the feature branch `robot-army/issue-276-inability-to-re-activate-an-account`; decomposed into milestones below, one feature at a time. |
| **II. The Test Gate** (NON-NEGOTIABLE) | PASS | Full unit and acceptance suites run to completion and pass before the feature is declared done. Existing Accounts-page assertions updated for the deliberate change (research R7); new behaviour gets its own acceptance coverage, including an end-to-end deactivate → re-activate round trip. pycodestyle/pyflakes clean under `pytest.ini`. Suites are never narrowed to a passing subset; a timeout is re-run with a raised timeout. |
| **III. Reversible Migrations** | N/A | Nothing under `biweeklybudget/models/` changes. `Account.is_active` already exists (research R9), so no Alembic migration and the `migrations` environment is not a gate here. |
| **IV. Documentation Is Part Of The Change** | PASS | New "Inactive Accounts" section in `docs/source/app_usage.rst`; `/accounts` screenshot caption added in `docs/make_screenshots.py` (the generator — `screenshots.rst` is generated output); `/accounts` screenshots regenerated and committed. `tox -e docs` must build clean. |
| **V. Escalate Instead Of Guessing** | PASS | The one genuinely ambiguous point — how far "shown in the UI" reaches — was put to the maintainer before any code was planned and answered "Accounts page only" (recorded in the spec's Assumptions and in `checklists/requirements.md`). No side quests; the view-method extraction (research R2) is inside the code being changed and is recorded here rather than done silently. |
| **VI. Changelog Every Change; Release Only On Request** | PASS | One concise bullet added to `CHANGES.rst` under `Unreleased`, led by the issue link. `version.py` is **not** touched; no tag, no release. |
| **Technology & Security Constraints** | PASS | No new dependency. Reuses the existing `tr.inactive` CSS class and the Budgets page's Jinja table pattern rather than adding a parallel frontend approach. No change to the security posture, no secrets. **Financial correctness**: no arithmetic changes — the same figures from the same queries, now for more rows; spec SC-005 pins this and the untouched dashboard/cash-position/pay-period tests enforce it. |

**Result**: Gate passes. No entries in Complexity Tracking.

**Post-Phase-1 re-check**: Re-evaluated after the design artifacts below were written. No
principle moves. The design adds no model change (III stays N/A), no dependency, and no new
CSS; the largest judgement call in it — collapsing the two duplicate view methods — is
recorded in research R2 with its rejected alternatives, which is what V asks for. Gate still
passes.

## Project Structure

### Documentation (this feature)

```text
specs/20260917-053603-show-inactive-accounts/
├── spec.md                      # Feature specification (committed f910a8b)
├── plan.md                      # This file
├── research.md                  # Phase 0 output — R1..R9
├── data-model.md                # Phase 1 output — no schema change; read model
├── quickstart.md                # Phase 1 output — how to validate
├── contracts/
│   └── accounts-page.md         # Phase 1 output — the Accounts page UI contract
└── checklists/
    └── requirements.md          # Spec quality checklist (all items passing)
```

### Source Code (repository root)

```text
biweeklybudget/
├── flaskapp/
│   ├── views/
│   │   └── accounts.py                     # CHANGED: drop is_active filter; collapse
│   │                                       #   AccountsView.get / OneAccountView.get
│   │                                       #   duplication into one helper
│   ├── templates/
│   │   └── accounts.html                   # CHANGED: "Active?" column in all three
│   │                                       #   tables; tr.inactive on inactive rows;
│   │                                       #   stale warning gated on is_active;
│   │                                       #   balance/credit-limit cells guarded
│   └── static/
│       ├── css/custom.css                  # UNCHANGED — tr.inactive already exists
│       └── js/accounts_modal.js            # UNCHANGED — already round-trips is_active
├── models/account.py                       # UNCHANGED — no schema change
└── tests/
    ├── fixtures/sampledata.py              # UNCHANGED — DisabledBank (id 6) already
    │                                       #   exists and is already inactive
    └── acceptance/flaskapp/views/
        └── test_accounts.py                # CHANGED: update the table assertions;
                                            #   add TestInactiveAccounts

docs/
├── make_screenshots.py                     # CHANGED: description for the /accounts shot
└── source/
    ├── app_usage.rst                       # CHANGED: new "Inactive Accounts" section
    ├── screenshots.rst                     # REGENERATED (generated file)
    └── accounts.png, accounts_sm.png       # REGENERATED

CHANGES.rst                                 # CHANGED: one bullet under Unreleased
```

**Structure Decision**: The existing single-package layout is used unchanged. This feature is
one page of an existing Flask application: the view module that queries for it, the Jinja
template that renders it, the acceptance test module that covers it, and the docs page that
describes it. No new modules, packages, or directories.

## Implementation Approach

### M1 — Make inactive accounts visible and re-activatable

The functional core. `views/accounts.py`: extract the body shared by `AccountsView.get()` and
`OneAccountView.get()` into one helper taking an optional `account_id`, and drop
`Account.is_active == True` from the three queries in it. `templates/accounts.html`: add the
leading `Active?` column to the bank, credit and investment tables, rendering `yes` or a red
`NO`, and set `class="inactive"` on the `tr` for inactive accounts — matching
`templates/budgets.html:80,109` in both markup and wording.

Delivers spec FR-001 through FR-005 and FR-008, and User Story 1 and 2 in full.

### M2 — Handle what becomes reachable

`templates/accounts.html`: gate the `text-danger` stale class on `acct.is_active` (FR-007,
research R4), and guard the balance- and credit-limit-derived cells so a missing value renders
as an empty cell instead of raising (FR-006, research R5).

Kept separate from M1 because it is defensive work on paths M1 exposes, and is worth reviewing
as such rather than blurred into the visible change.

### M3 — Acceptance coverage and documentation

Update the Accounts-page assertions listed in research R7 for the deliberate change, and add a
`TestInactiveAccounts` acceptance class covering: the greyed row and its class, the `Active?`
cells, the inactive account's name still linking to its modal, the modal showing `Active?`
unchecked, and the full round trip — deactivate an active account, find it still listed as
inactive, re-activate it from its modal, confirm it is active again in the page and in the
database.

`docs/source/app_usage.rst` gains an "Inactive Accounts" section (FR-010): what deactivating
an account does and does not do, that inactive accounts stay listed and greyed on the Accounts
page, and how to re-activate one. `docs/make_screenshots.py` gains a description for the
`/accounts` entry, and the `/accounts` screenshots are regenerated and committed. Build
`tox -e docs` clean — in a separate invocation from `screenshots`, which it would otherwise
delete.

### M4 — Changelog, test gate, pull request

Add the concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link; leave
`version.py` untouched. Run the unit and acceptance suites to completion with everything
passing (Principle II), push the branch, open the pull request, and see CI green.

### Out of scope

Confirmed with the maintainer and recorded in the spec: the dashboard, the cash position page,
pay-period arithmetic, the account balance chart, and the transaction/transfer account pickers
all keep their present treatment of inactive accounts (FR-009, research R6). Deleting accounts
is not added (spec Assumptions). No "show/hide inactive" filter control is added.

## Risks

| Risk | Mitigation |
|------|------------|
| A changed figure somewhere else in the application | No arithmetic is touched and no other query is touched (research R6). The dashboard, cash position and pay period suites are left untouched and must stay green — that is the check. |
| Acceptance assertions updated to match a *bug* rather than the intended change | Each updated assertion is changed only by adding the `Active?` cell and the `DisabledBank` row; any other movement in those lists is treated as a defect, not as an assertion to update. |
| The view-method extraction silently changes `/accounts/<id>` | Both routes keep their existing acceptance coverage (`TestAccountsMainPage`, `test_11_get_acct1_url`, `test_41_get_acct4_url`), which must pass unchanged apart from the two deliberate additions. |
| Regenerating screenshots clobbers unrelated images | Regenerate, then commit only the `/accounts` files this change actually alters. Never run `docs` in the same tox invocation as `screenshots`. |

## Complexity Tracking

> No Constitution Check violations. Table intentionally empty.
