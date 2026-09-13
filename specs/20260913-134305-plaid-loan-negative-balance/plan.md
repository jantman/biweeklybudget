# Implementation Plan: Plaid Loan Accounts Record Money Owed As A Negative Balance

**Branch**: `robot-army/issue-263-plaid-loan-accounts-report-a-positive` | **Date**: 2026-09-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260913-134305-plaid-loan-negative-balance/spec.md`

## Summary

`PlaidUpdater._update_investment()` in `biweeklybudget/plaid_updater.py` records a
statement balance and an `AccountBalance` from Plaid's `balances.current`, and the `loan`
branch of `_stmt_for_acct()` calls it unchanged. `_update_investment()` gains a keyword
argument `negate_balance=False`. When it is true, the cent-rounded balance is negated
before it is stored on the statement and passed to `set_balance()`. The `loan`
branch passes `negate_balance=True`, and the `investment` branch is unchanged.

Unit tests in `biweeklybudget/tests/unit/test_plaid_updater.py` pin the `loan` branch's
call and the negated figures for a positive, a negative, and a zero loan balance. They
also pin that the default (investment) path does not negate. `docs/source/plaid.rst` gets
a "Loan Accounts" section with the sign convention, the recommended account type, and
SQL to correct history recorded before the change. `CHANGES.rst` gets one `Unreleased`
entry.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: None new. `decimal.Decimal` for the arithmetic, as today.

**Storage**: MariaDB, unchanged. No model, schema, or migration change. Only the sign of
values written to the existing `ofx_statements.ledger_bal` and `account_balances.ledger`
columns changes, and only for Plaid `loan` accounts.

**Testing**: pytest. Unit tests (`tox -e py314`) cover `PlaidUpdater` with mocks,
following the existing `TestStmtForAcct` / `TestUpdateInvestment` pattern. The full unit
and acceptance suites must pass (Constitution II), and `docs` must build (Constitution IV).

**Target Platform**: Linux; the Flask app and `PlaidUpdater` run locally or in Docker.

**Project Type**: Flask/SQLAlchemy web application. One updater method and one call site
change.

**Performance Goals**: None; one extra subtraction per loan update.

**Constraints**: Balances for `depository`, `credit` and `investment` accounts MUST NOT
change (spec FR-003). Budget-source, cash-position and notification membership MUST NOT
change (FR-004). No stored data is migrated (FR-005).

**Scale/Scope**: About 10 changed lines in `plaid_updater.py`, its unit tests, one doc
section, and one changelog entry.

## Constitution Check

*Constitution v2.1.1. Gate evaluated before Phase 0 and re-evaluated after Phase 1.*

| Principle | Assessment | Status |
|-----------|-----------|--------|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | Spec written and validated, then this plan, then tasks, all before code. Work stays on the feature branch `robot-army/issue-263-plaid-loan-accounts-report-a-positive`. The change is a **single milestone (M1)**, so there is no inter-milestone boundary to cross. The maintainer's approval is taken at the pull request, before merge. | PASS |
| **II. The Test Gate** (NON-NEGOTIABLE) | New unit tests pin the negated balance on both the statement and the `set_balance()` call for a positive, a negative, and a zero loan balance. They also pin that the investment path is not negated and that the `loan` branch requests negation (SC-001/SC-002). The complete unit and acceptance suites MUST run to completion and pass. `plaid` (sandbox credentials) runs in CI. `migrations` and `docker` are not engaged, since there is no schema or packaging change, but still run in CI. Timeouts get raised and re-run. Touched code stays pycodestyle/pyflakes-clean. | PASS |
| **III. Reversible Migrations** | No change under `biweeklybudget/models/`; not engaged. Correcting historical rows is left to the operator via documented, self-inverse SQL rather than a data migration (research R3). | N/A |
| **IV. Documentation Is Part Of The Change** | `docs/source/plaid.rst` gains a "Loan Accounts" section (FR-006), and the `_update_investment` docstring documents the new argument. `README.rst` and `CLAUDE.md` don't describe Plaid balance handling, so they need no change. The `docs` environment must build clean. | PASS |
| **V. Escalate Instead Of Guessing** | The issue explicitly asks for a choice between two options. The choice (negate at ingest) and the decision not to rewrite history are recorded with reasons in the spec and in research R1/R3, and are put to the maintainer in the PR. Plaid credit-balance sign is noticed and explicitly **not** acted on (spec Assumptions) because it lies outside the issue. | PASS |
| **VI. Changelog Every Change; Release Only On Request** | One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue link, with a sub-bullet on existing history. `version.py` is not touched and no tag is created. There are no new Python files, so no new copyright headers are needed. | PASS |
| **Tech constraints / Financial correctness** | This changes recorded balances, so the expected numbers are pinned by tests, as the financial-correctness constraint requires. No new dependency, secrets, or security-posture change. Acceptance tests keep using only the test database. | PASS |

**Result: no violations. The Complexity Tracking table is therefore omitted.**

Post-Phase-1 re-evaluation: the design adds one keyword argument, with no new module,
abstraction, or dependency. The Constitution Check still passes.

## Design

```text
_stmt_for_acct():
  'investment' → stmt.type='Investment'; _update_investment(end_dt, account, info, stmt)
  'loan'       → stmt.type='Investment'; _update_investment(end_dt, account, info, stmt,
                                                            negate_balance=True)

_update_investment(..., negate_balance=False):
  bal = Decimal(current).quantize(0.01, ROUND_HALF_DOWN)   # as today
  if negate_balance: bal = -bal                             # 250000.00 → -250000.00; 0.00 → 0.00
  stmt.ledger_bal = bal; account.set_balance(ledger=bal, ...)
```

- Rounding happens before negation (spec edge case). `ROUND_HALF_DOWN` is symmetric about
  zero, so the order doesn't affect the magnitude either way.
- Unary minus, not `bal * Decimal('-1')` or `copy_negate()`: under the default context
  `-Decimal('0.00')` is `0.00`, while the other two give `-0.00`, which prints as `-0.00`
  in logs and before a DB round trip (research R2).
- The statement and the account balance are set from the same variable, so they cannot
  disagree (FR-002).
- `stmt.type` stays `'Investment'` for loans. The OFX statement type describes the
  statement's shape (balance only, no transactions), which is unchanged.
- No other code path reads Plaid's account type, so nothing else changes. The account
  tables, the chart, and `CashPosition` all read the stored balance.

### Project Structure

Documentation for this feature:

```text
specs/20260913-134305-plaid-loan-negative-balance/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── plaid-loan-balance.md   # Phase 1: stored-balance sign contract per Plaid type
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2, written by /speckit-tasks
```

Repository files this change touches:

```text
biweeklybudget/
├── plaid_updater.py                       # _stmt_for_acct loan branch; _update_investment
└── tests/unit/test_plaid_updater.py       # TestStmtForAcct.test_loan; TestUpdateInvestment
docs/source/plaid.rst                      # new "Loan Accounts" section
CHANGES.rst                                # Unreleased entry
```

**Structure Decision**: the existing layout is kept. No new file outside `specs/`.

## Milestones

- **M1 — Negate loan balances, tests, and docs.** Write the failing unit tests, change
  `_update_investment()` and the `loan` branch, add the `plaid.rst` section and the
  `CHANGES.rst` entry. Run the Test Gate (unit, acceptance, docs), record the results
  here, then commit, push, and open the PR.

## Risks

| Risk | Mitigation |
|------|-----------|
| The operator's loan accounts show a jump from +X to -X in the Account Balances chart at the first update after upgrading. | Documented in `plaid.rst` with self-inverse SQL to flip the pre-upgrade rows, and flagged in the changelog entry. |
| An operator linked a Plaid loan to a Bank or Cash account, so it is a budget source, and the budget sums now drop by twice the loan's principal. | That linkage already counted the loan as cash (wrong the other way). The docs recommend Investment. The PR calls it out. |
| A future `investment` update accidentally negates. | The default is `False`, and a unit test pins that the investment path records Plaid's figure unchanged. |
| Plaid's loan sign convention differs for some institution. | Plaid documents positive-owed for all loans (a Sallie Mae note concerns the magnitude, not the sign). A negative Plaid figure is handled symmetrically (spec scenario 3). |
