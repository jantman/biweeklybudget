# Feature Specification: Plaid Loan Accounts Record Money Owed As A Negative Balance

**Feature Branch**: `robot-army/issue-263-plaid-loan-accounts-report-a-positive`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description: "jantman/biweeklybudget issue #263 — Plaid loan accounts report a
positive balance for money owed. There is no `Loan` account type; the only loan concept is
Plaid's account type, which the Plaid updater handles as an investment statement with the
balance taken from Plaid as-is. Plaid reports a loan balance as a positive number representing
the amount owed, so a mortgage or auto loan linked through Plaid shows up as a positive asset
rather than a liability. Decide between (1) negating the balance at ingest or (2) adding a
`Loan` account type with its own semantics, and settle how loan balances interact with account
totals, the index chart, and the budget-source sums behind the notifications."

## Background & Decision

**Confirmed against Plaid's API definition.** Plaid documents `balances.current` for
`loan`-type accounts as "the principal remaining on the loan ... Similar to `credit`-type
accounts, a positive balance is typically expected, while a negative amount indicates the
lender owing the account holder." biweeklybudget stores that number unchanged, so a linked
$250,000 mortgage is recorded as a balance of **+$250,000**.

Everywhere else in the application a liability is recorded as a **negative** balance: credit
card balances are negative when money is owed, and the available-credit and cash-position
arithmetic depend on that. A loan is a liability and should follow the same convention.

**Decision: negate at ingest (option 1).** When a Plaid `loan` account is updated, the balance
recorded for it is Plaid's balance with its sign reversed. No new account type is added.

Why not option 2 (a `Loan` account type): the problem is only the sign of the stored number.
Loan-linked accounts already sit outside every calculation the sign could corrupt (see
"Interaction with totals and notifications" below), so a new type would add a schema change,
a new section on the Accounts and index pages, and new totals rules, without fixing anything
option 1 leaves broken. Option 1 is also the smallest change that can be reversed cleanly if
a `Loan` type is wanted later: that feature could keep the negative convention and only add
presentation.

The issue's concern that "the stored value disagrees with what Plaid reported" is accepted
deliberately: the stored value follows biweeklybudget's sign convention, not Plaid's, exactly as
OFX credit card statements are already stored in the application's convention.

### Interaction with totals and notifications (settled)

- **Budget-source sums and the notifications banner / Cash Position page**: only Bank and Cash
  accounts are budget funding sources, and only Bank, Cash and Credit accounts contribute to
  the Cash Position waterfall. A Plaid loan is linked to an Investment (or Other) account, so it
  contributes to none of these sums, before or after this change. This feature does not change
  which accounts count.
- **`/accounts` and index page account tables**: there is no summed total across accounts on
  either page. A loan-linked Investment account appears in the Investment Accounts table with
  its own balance, which is now shown negative.
- **Index page Account Balances chart**: plots one line per account and does not sum accounts.
  A loan's line is now plotted below zero, from the first update after this change onward.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A linked loan shows as money owed (Priority: P1)

The operator has a mortgage (or auto or student loan) linked through Plaid to an account in
biweeklybudget. After running a Plaid update, the account's balance on the Accounts page, the
index page and the Account Balances chart is negative, reading as money owed, instead of a
positive figure that looks like an asset.

**Why this priority**: This is the whole of the issue. A loan shown as an asset misstates the
operator's financial position on every page that shows the account.

**Independent Test**: Update a Plaid-linked account whose Plaid account type is `loan` and whose
Plaid balance is 1234.56; confirm the account's recorded balance is -1234.56.

**Acceptance Scenarios**:

1. **Given** an account linked to a Plaid `loan` account whose Plaid current balance is
   `250000.00`, **When** the operator runs a Plaid update, **Then** the account's new recorded
   balance is `-250000.00` and the Accounts page shows it as negative.
2. **Given** the same account, **When** the update completes, **Then** the statement recorded
   for that update carries the same negative balance as the account.
3. **Given** a Plaid `loan` account whose Plaid current balance is negative (the lender owes
   the operator, e.g. an overpayment), **When** the operator runs a Plaid update, **Then** the
   recorded balance is positive, reading as money held rather than owed.
4. **Given** a Plaid `loan` account whose Plaid current balance is zero (paid off), **When**
   the operator runs a Plaid update, **Then** the recorded balance is zero.

---

### User Story 2 - Other Plaid account types are unaffected (Priority: P1)

Accounts linked to Plaid `depository`, `credit` and `investment` accounts keep recording their
balances exactly as they do today.

**Why this priority**: The fix must not move any other balance. Bank and credit balances feed
the budget and cash-position arithmetic; changing them by accident would be far worse than the
bug being fixed.

**Independent Test**: Update accounts linked to Plaid `depository`, `credit` and `investment`
accounts and confirm each recorded balance equals what the same update records today.

**Acceptance Scenarios**:

1. **Given** an account linked to a Plaid `investment` account with current balance
   `1234.56`, **When** the operator runs a Plaid update, **Then** the recorded balance is
   `1234.56`.
2. **Given** accounts linked to Plaid `depository` and `credit` accounts, **When** the operator
   runs a Plaid update, **Then** their recorded ledger and available balances are unchanged
   from today's behaviour.

---

### Edge Cases

- **Balances recorded before this change**: balances already stored for loan accounts are not
  rewritten. The account's current balance becomes correct at its next Plaid update; its
  Account Balances chart line will show a jump from the old positive figures to the new
  negative ones at that point. The operator documentation explains how to correct the stored
  history if they want to.
- **Which account the loan is linked to**: the sign is decided by the *Plaid* account type
  (`loan`), not by the biweeklybudget account type the operator linked it to. The documentation
  recommends linking loans to an Investment account (where they are shown on the Accounts page
  and excluded from budget sums); linking a loan to a Bank or Cash account would make it a
  budget funding source, which is an operator configuration choice this feature does not
  police.
- **Rounding**: the balance is rounded to cents exactly as it is today, then its sign is
  reversed; a balance that rounds to zero is recorded as zero.
- **Loan transactions**: the loan update path records a balance only and no transactions,
  as today. This feature does not add loan transaction import.
- **A missing Plaid balance** for a loan behaves as it does today (the update for that item
  reports a failure); this feature does not change that.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a Plaid update records a balance for an account linked to a Plaid account of
  type `loan`, the recorded balance MUST be Plaid's current balance, rounded to cents as today,
  with its sign reversed.
- **FR-002**: The statement recorded for that loan update MUST carry the same (sign-reversed)
  balance as the account balance recorded by the same update.
- **FR-003**: Balances recorded for accounts linked to Plaid `depository`, `credit` and
  `investment` accounts MUST be unchanged by this feature.
- **FR-004**: The set of accounts counted as budget funding sources, in the Cash Position
  waterfall, and in the notifications banner MUST be unchanged by this feature.
- **FR-005**: No new account type is added and no stored data is migrated; balances recorded
  before this change are left as they are.
- **FR-006**: The operator documentation for Plaid MUST state that loan balances are recorded
  as negative (money owed), recommend which account type to link a loan to, and explain how to
  correct loan balances recorded before this change.

### Key Entities

- **Plaid account type**: Plaid's classification of a linked account (`depository`, `credit`,
  `investment`, `loan`). Determines how an update records the account's balance.
- **Account balance record**: the balance recorded for an account at each update; what the
  Accounts page, index page and Account Balances chart display.
- **Statement record**: the per-update statement stored alongside the balance, carrying the
  same balance figure.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every Plaid-linked loan account, 100% of balances recorded by updates after
  this change are negative whenever Plaid reports a positive amount owed.
- **SC-002**: For accounts linked to non-loan Plaid accounts, 0 recorded balances differ from
  what the same Plaid data produces today.
- **SC-003**: The budget-funding, cash-position and notification totals for any given set of
  accounts and balances are identical before and after this change.
- **SC-004**: An operator reading the Plaid documentation can find, in one place, how loan
  balances are recorded and how to correct balances recorded before the change.

## Assumptions

- Plaid's documented meaning of a loan's `current` balance (positive = principal owed) holds for
  the operator's institutions. It was confirmed against Plaid's API reference; live production
  Plaid data is not available to this change.
- Operators link Plaid loans to Investment accounts, as the existing code's handling of loans
  as investment statements implies. This is documented, not enforced.
- Plaid `credit` accounts use the same positive-means-owed convention, and today their balances
  are also stored as Plaid reports them. Whether that is also wrong is a separate question,
  explicitly **out of scope** here (FR-003 forbids changing it) and noted in the pull request
  for the maintainer.
- No Alembic migration is needed because no model changes.
