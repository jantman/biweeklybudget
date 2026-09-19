# Implementation Plan: Plaid Credit Card Balances Recorded As Negative

**Branch**: `robot-army/issue-354-cash-position-adds-plaid-sourced-credit` | **Date**: 2026-09-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260918-200526-plaid-credit-negative-balance/spec.md`

## Summary

`PlaidUpdater` records a Plaid `credit` account's balance with Plaid's own sign, but
Plaid reports `balances.current` for a credit card as the **positive amount owed** while
biweeklybudget records money owed as a **negative** balance. Every consumer of that
balance — the Cash Position waterfall, the unallocated-funds notification, the Account
Balances chart — implements the negative-means-owed convention correctly, so the single
wrong thing is the sign at the point of recording.

The fix mirrors what issue #263 did for Plaid loan accounts: give
`PlaidUpdater._update_bank_or_credit()` a `negate_balance` keyword argument, defaulting to
`False`, and pass `negate_balance=True` from the `credit` branch of `_stmt_for_acct()`.
The `depository` branch keeps the default, so bank and cash balances are untouched. The
negation is a unary minus applied to the quantized `Decimal` so that a zero balance stays
`0.00` and an overpaid card (negative reported balance) becomes a positive recorded
balance. Transaction amounts and the available balance are not touched.

Alongside that, `_update_bank_or_credit()` gains a purely diagnostic consistency check
(FR-008): when negating, and when both the account's credit limit and Plaid's available
balance are known, compare the available balance against `limit - current` and
`limit + current`; log when the reversed hypothesis fits strictly better and by more than
the balance itself. It changes nothing and cannot fail an update.

No schema change, so no Alembic migration. Historical rows are corrected by the operator
with documented SQL, following the precedent of the "Loan Accounts" section of
`docs/source/plaid.rst`.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: `plaid-python==44.0.0` (pinned; the source of the balance sign
contract), SQLAlchemy, Flask. No new dependency.

**Storage**: MySQL/MariaDB. Affected tables (data only, no schema change):
`ofx_statements.ledger_bal`, `account_balances.ledger`.

**Testing**: pytest. Unit tests in `biweeklybudget/tests/unit/`, run via `tox -e py314`;
acceptance tests via `tox -e acceptance`; docs build via `tox -e docs`. The relevant
existing unit tests are `TestStmtForAcct` and `TestUpdateBankOrCredit` in
`biweeklybudget/tests/unit/test_plaid_updater.py`.

**Target Platform**: Linux, localhost single-operator web application.

**Project Type**: Flask/SQLAlchemy web application (single Python package).

**Performance Goals**: N/A — the change is a sign flip and one arithmetic comparison per
credit account per update.

**Constraints**: Financial correctness (Constitution, Technology & Security Constraints):
the recorded signs must be pinned by tests. The diagnostic check must never alter a
recorded value nor cause an update to be reported as failed.

**Scale/Scope**: Three source files touched (`plaid_updater.py`, its unit tests, and the
docs), plus `CHANGES.rst`. No UI, model, or view change.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design — see
"Post-Design Re-Check" below.*

| Principle | Assessment |
|-----------|------------|
| **I. Spec-Driven Change** | PASS. `spec.md` written and committed before planning; this plan precedes implementation; work is on the feature branch `robot-army/issue-354-cash-position-adds-plaid-sourced-credit`. Decomposed into milestones M1–M3 in `tasks.md`. |
| **II. The Test Gate** | PASS by construction, verified at implementation. Full unit and acceptance suites must be run to completion and pass before the feature is declared done. New behaviour is covered by unit tests that pin the recorded sign for positive, negative and zero credit balances and for a depository balance (FR-013). Code must be pycodestyle/pyflakes clean. |
| **III. Schema Changes Ship With Reversible Migrations** | NOT APPLICABLE. Nothing under `biweeklybudget/models/` changes; no column is added, removed or retyped. The change alters only the *value* written to existing columns going forward. Corrective SQL for pre-existing rows is documentation, not a migration — see Complexity Tracking for why this is the right call and not an evasion. |
| **IV. Documentation Is Part Of The Change** | PASS. `docs/source/plaid.rst` gains a "Credit Card Accounts" section; `docs/source/app_usage.rst` gains a cross-reference from the Cash Position sign discussion. `tox -e docs` must build without errors. |
| **V. Escalate Instead Of Guessing** | PASS, with one recorded judgement call: the issue suggested a "debug-level warning" for the consistency check; this plan logs at WARNING. Rationale in `research.md` (Decision 5), and it will be called out in the pull request so the maintainer can say otherwise with a one-word change. |
| **VI. Changelog Every Change; Release Only On Request** | PASS. A concise entry is added at the top of `CHANGES.rst` under a newly created `Unreleased` heading (there is none today — 2.0.0 is the top section). `biweeklybudget/version.py` is **not** touched; no tag, no release. |
| **Financial correctness constraint** | PASS. Tests pin the expected numbers for every sign case, and an end-to-end test asserts the Cash Position figure moves the right way. |
| **Test data safety** | PASS. No change to test fixtures or to what the acceptance suite points at. |
| **Secrets** | PASS. No credential handling is touched. |

**Post-Design Re-Check** (after Phase 1): unchanged. The design adds no new module, no new
dependency, no new configuration setting, and no new public interface beyond a keyword
argument on an existing private method. The only item that needed justification —
correcting historical rows by documented SQL rather than by an Alembic migration — is
recorded in Complexity Tracking below and follows an existing precedent in this
repository.

## Project Structure

### Documentation (this feature)

```text
specs/20260918-200526-plaid-credit-negative-balance/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── plaid-balance-signs.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
biweeklybudget/
├── plaid_updater.py                      # CHANGED: negate_balance on
│                                         #   _update_bank_or_credit(); credit branch
│                                         #   of _stmt_for_acct() passes True;
│                                         #   diagnostic sign-consistency check
├── cashposition.py                       # UNCHANGED (already correct)
├── flaskapp/notifications.py             # UNCHANGED (already correct)
├── models/                               # UNCHANGED (no schema change)
├── alembic/versions/                     # UNCHANGED (no migration)
└── tests/
    └── unit/
        └── test_plaid_updater.py         # CHANGED: sign cases + diagnostic check

docs/source/
├── plaid.rst                             # CHANGED: "Credit Card Accounts" section
│                                         #   with convention + corrective SQL
└── app_usage.rst                         # CHANGED: cross-reference from the Cash
                                          #   Position sign discussion

CHANGES.rst                               # CHANGED: new Unreleased entry
```

**Structure Decision**: Single Python package, unchanged. The whole behavioural change is
contained in `biweeklybudget/plaid_updater.py`; nothing downstream needs to know, because
every downstream consumer already implements the negative-means-owed convention. This is
the narrowest possible surface for the fix and matches how #263 was structured.

## Milestones

Milestones are deliberately few; this is a small, well-understood correction.

* **M1 — Correct the recorded sign.** The `negate_balance` argument, the credit branch
  passing it, and unit tests pinning every sign case. At the end of M1 the reported defect
  is fixed and the test gate for it is in place.
* **M2 — Diagnostic consistency check.** The non-fatal `available` vs `limit ± current`
  comparison and its tests. Independent of M1 and droppable without affecting the fix.
* **M3 — Documentation, changelog, and the full test gate.** The Plaid docs section with
  corrective SQL, the Cash Position cross-reference, the `CHANGES.rst` entry under a new
  `Unreleased` heading, and complete unit + acceptance + docs runs.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Historical rows are corrected by operator-run SQL documented in `docs/source/plaid.rst`, not by an Alembic migration — so a data-affecting change ships without a migration. | The wrong sign is already written into years of `account_balances.ledger` and `ofx_statements.ledger_bal` rows, and the Account Balances chart plots them. The operator needs *some* way to correct them, and they need to be told what happens if they do nothing. | An Alembic migration was rejected. (a) It could not be made safely reversible in the sense Principle III requires: `downgrade()` would have to re-break the data, and a user who had already corrected some rows by hand would be corrupted in both directions. (b) It cannot distinguish balances that came from Plaid from balances an account had before it was linked, so it would flip rows that were always correct. (c) Principle III governs changes to `biweeklybudget/models/`; nothing under `models/` changes here. (d) Issue #263 faced this exact situation for loan accounts and resolved it with documented SQL; doing the same thing keeps one documented procedure rather than two mechanisms for one problem. |
