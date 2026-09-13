# Research: Plaid Loan Accounts Record Money Owed As A Negative Balance

The Technical Context had no NEEDS CLARIFICATION items. These notes record the choices
behind the design and the facts they rest on.

## R0: What Plaid reports for a loan

- **Finding**: Plaid's Accounts API reference defines `balances.current` for `loan`-type
  accounts as "the principal remaining on the loan, except in the case of student loan
  accounts at Sallie Mae (`ins_116944`) [where it] includes both principal and any
  outstanding interest. Similar to `credit`-type accounts, a positive balance is typically
  expected, while a negative amount indicates the lender owing the account holder."
- **Consequence**: the stored balance of a linked mortgage is currently the positive
  principal. biweeklybudget's convention, set in commit `e25c607` ("credit account
  balances are negative") and relied on by `credit_account_sum()`, `CashPosition`, and
  the `credit_limit + ledger` available-credit figures, is that money owed is negative.
- **Limit**: live production Plaid data is not reachable from this change. The code
  path has taken `current` unmodified since loans were added in `4797daf` (2020), so the
  stored value is exactly Plaid's figure.

## R1: Negate at ingest vs. a new `Loan` account type

- **Decision**: negate at ingest, keyed on the Plaid account type `loan`.
- **Rationale**: the defect is a sign. Every consumer of the stored balance already
  treats negative as owed, and loan-linked accounts (Investment type) are in none of the
  summed figures: `is_budget_source` is Bank/Cash, and `CashPosition` counts Bank/Cash/
  Credit. Flipping the sign fixes every display without a schema change, a migration, or
  new UI.
- **Alternatives considered**:
  - *Add `AcctType.Loan`*: needs an Alembic enum migration, a new section on `/accounts`
    and the index page, a new `acct_icon`, and new totals rules. It fixes nothing
    extra, and a later feature can still add it on top of the negative convention.
  - *Negate at display time*: would leave `AccountBalance` positive, so the chart
    endpoint, `CashPosition`, and every future reader would each need to know about
    Plaid loan types. That spreads the special case into many readers instead of one
    writer.
  - *Use the existing `negate_ofx_amounts` flag*: it negates transaction amounts, not
    balances, and is operator-controlled. Overloading it would change behaviour for
    credit accounts that already set it.

## R2: How to negate a `Decimal`

- **Decision**: unary minus (`-bal`), after quantizing to cents.
- **Rationale** (verified on Python 3): under the default context `-Decimal('0.00')` is
  `Decimal('0.00')`, because `__neg__` applies context rounding and returns positive zero.
  `-Decimal('1234.57')` is `Decimal('-1234.57')` and `-Decimal('-50.25')` is
  `Decimal('50.25')`.
- **Alternatives considered**: `bal * Decimal('-1')` (the idiom `negate_ofx_amounts`
  uses for transactions) and `bal.copy_negate()` both give `Decimal('-0.00')` for a zero
  balance. That value compares equal to zero, but it prints as `-0.00` in logs and in the
  object held by the session before a DB round trip. A unit test pins
  `str(balance) == '0.00'` so a later switch to either idiom is caught.

## R3: Balances recorded before the change

- **Decision**: don't rewrite them in code. Document self-inverse SQL in `plaid.rst` for
  the operator to run once if they want continuous chart history.
- **Rationale**: a data migration would have to decide which rows came from Plaid loan
  updates. `account_balances` rows don't record their source, and an account may have been
  linked to a Plaid loan only part of the time or had balances entered some other way.
  The operator knows their history, and the code does not. Leaving the rows alone is also
  what the spec requires (FR-005). The current balance corrects itself at the next update.
- **SQL (documented)**: negate `account_balances.ledger` and `ofx_statements.ledger_bal`
  for accounts whose linked `plaid_accounts.account_type = 'loan'`, run once after
  upgrading and **before** the next Plaid update. Running it a second time undoes it,
  which is why the docs say to run it once, before the next update.

## R4: Scope boundary: Plaid credit balances

- **Finding**: Plaid documents `credit` balances as positive-owed too, and
  `_update_bank_or_credit()` stores them as reported. Changing that would move balances
  that feed the budget and cash-position arithmetic, and it is not what issue #263 asks.
- **Decision**: out of scope (spec FR-003). Raised in the PR description for the
  maintainer.
