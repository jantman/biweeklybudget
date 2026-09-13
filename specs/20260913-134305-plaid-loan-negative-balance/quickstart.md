# Quickstart: Validating Plaid Loan Negative Balances

## Prerequisites

- The main checkout's virtualenv with `tox` (see project memory: worktrees have no venv).
- A MariaDB 10.4.7 test container and the test environment variables from `CLAUDE.md`
  (unit tests need MySQL to collect `test_plaid.py` / `test_utils.py`).

## 1. Unit tests: the behaviour contract

```bash
pytest biweeklybudget/tests/unit/test_plaid_updater.py -k "TestStmtForAcct or TestUpdateInvestment"
```

Expected:

- `TestStmtForAcct::test_loan`: the loan branch calls `_update_investment(...,
  negate_balance=True)` and sets `stmt.type == 'Investment'`.
- `TestStmtForAcct::test_investment`: the investment branch calls it without negation.
- `TestUpdateInvestment`: `1234.5678` is stored as `1234.57` by default. With negation it
  becomes `-1234.57` on both the statement and `set_balance(ledger=...)`, `-50.25` becomes
  `50.25`, and `0` becomes `0.00` (with `str() == '0.00'`). See
  [contracts/plaid-loan-balance.md](./contracts/plaid-loan-balance.md).

## 2. Full Test Gate

```bash
tox -e py314      # unit + pycodestyle + pyflakes
tox -e acceptance
tox -e docs
```

All must pass, with output redirected to a scratchpad file (CLAUDE.md).

## 3. Documented history-correction SQL

Against the **test** database, with an account linked to a `plaid_accounts` row of
`account_type='loan'` and a positive `account_balances.ledger`, run the SQL from
`docs/source/plaid.rst` "Loan Accounts". Confirm the ledger values flip sign and that
rows for non-loan accounts are untouched. Run it again and confirm it restores the
original values.

## 4. Optional: Plaid sandbox

With sandbox credentials, `tox -e plaid` links the sandbox institution, which includes
"Plaid Student Loan (7777)". After an update, an account linked to that loan shows a
negative balance on `/accounts`.
