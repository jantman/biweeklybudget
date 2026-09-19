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

* **M1 — Correct the recorded sign** (spec User Story 1, P1). The `negate_balance`
  argument, the credit branch passing it, and unit tests pinning every sign case. At the
  end of M1 the reported defect is fixed and the test gate for it is in place.
* **M2 — Documentation and changelog** (spec User Story 2, P1). The Plaid "Credit Card
  Accounts" section with the convention and corrective SQL, the Cash Position
  cross-reference, and the `CHANGES.rst` entry under a new `Unreleased` heading.
* **M3 — Diagnostic consistency check, then the full test gate and delivery** (spec User
  Story 3, P3). The non-fatal `available` vs `limit ± current` comparison and its tests —
  droppable without affecting the fix — followed by complete unit, acceptance and docs
  runs, the push and the pull request.

Task-level breakdown is in [tasks.md](./tasks.md), whose phases map one-to-one onto these
milestones.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Historical rows are corrected by operator-run SQL documented in `docs/source/plaid.rst`, not by an Alembic migration — so a data-affecting change ships without a migration. | The wrong sign is already written into years of `account_balances.ledger` and `ofx_statements.ledger_bal` rows, and the Account Balances chart plots them. The operator needs *some* way to correct them, and they need to be told what happens if they do nothing. | An Alembic migration was rejected. (a) It could not be made safely reversible in the sense Principle III requires: `downgrade()` would have to re-break the data, and a user who had already corrected some rows by hand would be corrupted in both directions. (b) It cannot distinguish balances that came from Plaid from balances an account had before it was linked, so it would flip rows that were always correct. (c) Principle III governs changes to `biweeklybudget/models/`; nothing under `models/` changes here. (d) Issue #263 faced this exact situation for loan accounts and resolved it with documented SQL; doing the same thing keeps one documented procedure rather than two mechanisms for one problem. |

## Test Gate Record

Run 2026-09-18 on the feature branch, from the main checkout's virtualenv against a
MariaDB 10.4.7 test container (Constitution Principle II, step 5a).

| Suite | Result |
|---|---|
| `tox -e py314` (full unit) | **OK** — 1015 passed, 4 skipped, 0 failed. The `.tox/py314/.pytest_cache` was cleared first, so all 143 pycodestyle/pyflakes checks actually ran rather than being skipped as "previously passed". |
| `tox -e acceptance` (full) | **OK** — 965 passed, 0 failed, 22m13s. First run, no flakes; none of the known-flaky tests needed a re-run. |
| `tox -e docs` | **OK** — no broken links. |
| `tox -e migrations` | **Not run, not applicable.** No change under `biweeklybudget/models/` and no migration; Principle III's trigger is not met. |
| `tox -e docker` | **Left to CI**, which runs the `docker` job on the pull request. This host has repeatedly killed local `docker` runs for low memory; CI is the real gate. |
| pycodestyle / pyflakes on the changed files | **Clean.** The two pyflakes findings in `test_plaid_updater.py` (an unused `PlaidApi` import at line 43, an unused `txns` local at line 406) are pre-existing at unchanged lines and are covered by the exceptions in `pytest.ini`. |

During implementation the three `TestDoItem` tests failed whenever
`test_plaid_updater.py` was run on its own (`AttributeError: Mock object has no attribute
'account'` — a backref not yet configured). They pass in the full suite, as recorded
above, and are unrelated to this change.

One correction was needed along the way: the first draft of the `CHANGES.rst` entry linked
the new documentation section on readthedocs, which `linkcheck` rejected because the anchor
only exists once the change is published. It now names the section in prose, exactly as the
issue #263 entry does for "Loan Accounts".

## Delivery Record

Pull request [#360](https://github.com/jantman/biweeklybudget/pull/360), opened 2026-09-18
from `robot-army/issue-354-cash-position-adds-plaid-sourced-credit`.

**CI**: all checks pass on `cb1310a` — `py314`, `acceptance`, `docker`, `docs`, `jsdoc`,
`migrations`, `plaid`, `screenshots`, `coverage`, `claude-review`, Snyk. The `docker` job
is the gate for packaging, which is not run locally on this host.

**Review**: one finding, and it was a real bug in this feature's own work.

The automated review showed that the second condition on the diagnostic warning,
`err_normal > abs(current)`, was algebraically implied by the first and so could never
filter anything. Writing `d` for `avail - limit`, the residuals are `|d + current|` and
`|d - current|`, so the reversed hypothesis wins exactly when `d` and `current` share a
sign — and whenever they do, `|d + current| = |d| + |current| > |current|` already. The
claim in Decision 4 of `research.md` that the second condition "is what keeps the check
quiet" was therefore wrong as implemented: the check warned on any same-sign mismatch down
to a single cent.

Reproduced independently before changing anything (symbolically, and over 300k random
`Decimal` triples where the clause changed the outcome in zero cases), then fixed in
`cb1310a`: the condition is now `err_reversed < abs(current)`, which requires the reversed
hypothesis to *fit* rather than merely to fit better, and which is not vacuous (it changes
the outcome in roughly an eighth of random triples). A regression test covers the case the
old condition was meant to catch and did not — $10 owed with a $30 pending credit —
verified to fail against the old condition and pass against the new one.

One claim was retracted rather than defended in the course of that fix. A test asserting
that a stale `credit_limit` is also suppressed was drafted, checked, found false (a limit
recorded far enough below the real one still satisfies both conditions), and deleted; the
docstring now states plainly that this remains a heuristic on a relation Plaid itself
calls approximate. The same residual — a false positive when net pending inflow falls
between one and three times the balance — was independently identified by the second
review pass and deliberately not flagged, on the grounds that it is inherent to the
heuristic, documented, and advisory only.

The second review reported "No issues found. Checked for bugs and CLAUDE.md compliance."
No Copilot review is configured on this repository.

**Open for the maintainer**: the WARNING-vs-DEBUG log level for the diagnostic check,
recorded in `research.md` Decision 5 and raised in the pull request description. A
one-word change either way.
