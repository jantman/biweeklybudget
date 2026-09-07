# Feature Specification: Per-Account Transaction Totals Per Pay Period

**Feature Branch**: `robot-army/issue-213-per-account-txn-total-on-each-period`

**Created**: 2026-09-07

**Status**: Draft

**Input**: User description: "Per-Account Txn total on each period (jantman/biweeklybudget issue #213, labels: enhancement, robot-army): Add a table containing the per-account transaction totals for each payperiod, on the payperiod view."

## Overview

The pay period view (`/payperiod/YYYY-MM-DD`) already answers "how much is budgeted, spent
and remaining overall" and "how much per budget". It cannot currently answer "how much
moved through each of my accounts this period". Reconciling a bank or credit card statement,
or sanity-checking that a card's activity looks right before its payment comes due, means
scanning the flat transaction list and adding amounts by hand.

This feature adds a table to the pay period view giving, for every account with activity, the
total of that account's transactions in each of the five pay periods the page already
displays across the top (previous, current, next, following, last).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See per-account totals for the pay period being viewed (Priority: P1)

As the person managing their finances, when I open a pay period I want to see, at a glance,
the total amount of transactions against each of my accounts during that period, so that I
know how much moved through each account without adding up the transaction list by hand.

**Why this priority**: This is the core of the request. On its own it delivers the whole
value of the feature for the period the user is actually looking at.

**Independent Test**: Load a pay period view for a period that has transactions against more
than one account, and confirm the new table lists each of those accounts with a total equal
to the sum of that account's transaction amounts shown in the page's Transactions table.

**Acceptance Scenarios**:

1. **Given** a pay period containing transactions against two different accounts, **When** I
   open that pay period's view, **Then** a per-account totals table is displayed listing both
   accounts, each with the sum of its transactions for that period.
2. **Given** a pay period with an account whose transactions sum to a negative amount (net
   income into the account), **When** I view the table, **Then** that account's total is
   displayed as a negative amount, distinguished visually the same way other negative amounts
   are on this page.
3. **Given** a pay period containing both real transactions and not-yet-converted scheduled
   transactions against the same account, **When** I view the table, **Then** the account's
   total includes both, matching the amounts listed in the page's Transactions table.
4. **Given** a pay period containing a transaction that is excluded from budget arithmetic
   (a credit card payment, or one explicitly marked as having no budget impact), **When** I
   view the table, **Then** that transaction is still included in its account's total, because
   money did move through the account.

---

### User Story 2 - Compare each account's totals across neighbouring pay periods (Priority: P2)

As the person managing their finances, I want each account's total shown for the same five
pay periods the page already shows across the top, so that I can see at a glance whether an
account's activity this period is unusual compared with the period before and the periods
coming up.

**Why this priority**: This is the "for each payperiod" half of the request and the reason
the table is worth more than a single column. It builds directly on Story 1 and is only
useful once Story 1 exists.

**Independent Test**: Open a pay period view and confirm the table's columns are the same
five pay periods, in the same order, as the "Remaining Balances" table at the top of the page,
and that each cell matches the total that account has when that period is opened directly.

**Acceptance Scenarios**:

1. **Given** the pay period view, **When** I look at the per-account totals table, **Then**
   its columns are the same five pay periods, labelled the same way and in the same order, as
   the "Remaining Balances" table at the top of the page.
2. **Given** the per-account totals table, **When** I look at the column for the period being
   viewed, **Then** it is visually emphasised in the same way the current period's column is
   emphasised in the "Remaining Balances" table.
3. **Given** a column header for a pay period other than the one being viewed, **When** I
   click it, **Then** I am taken to that pay period's view, exactly as the headers of the
   "Remaining Balances" table behave.
4. **Given** an account with transactions in one displayed period but none in another,
   **When** I view the table, **Then** the account appears as a row and its total for the
   period with no transactions is shown as zero rather than being blank or omitted.

---

### User Story 3 - Reach an account's detail from its total (Priority: P3)

As the person managing their finances, when a per-account total looks surprising I want to go
straight from the table to that account, so that I can investigate without navigating from
scratch.

**Why this priority**: A convenience that matches how every other name in this page's tables
behaves. It adds no new numbers and can be added last without affecting the rest.

**Independent Test**: Click an account name in the new table and confirm the account's detail
page opens.

**Acceptance Scenarios**:

1. **Given** the per-account totals table, **When** I click an account's name, **Then** that
   account's detail view opens.

---

### Edge Cases

- **No transactions at all in any of the five periods**: the table is still rendered, with its
  headers and a totals row of zeros, and no account rows. The page must not error.
- **An account that is no longer active but has transactions in a displayed period**: the
  account still appears, because its money still moved. Accounts with no transactions in any
  of the five displayed periods do not appear at all, so the table stays as short as the data
  warrants.
- **Transactions excluded from budget arithmetic**: included in account totals (see Story 1,
  scenario 4). The per-account total is a statement of account activity, not of budget
  consumption, so the two sets of numbers are not expected to agree and must not be presented
  as if they should.
- **Scheduled transactions with no fixed date** (per-period and weekly schedules): counted in
  the period they are projected into, consistently with how the page's Transactions table
  already lists them.
- **A scheduled transaction that has already been converted to a real transaction**: counted
  once, not twice, consistently with the rest of the page.
- **Very many accounts**: the table must remain readable and must not force the page to scroll
  horizontally on a normal desktop window.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The pay period view MUST display a table of per-account transaction totals.
- **FR-002**: The table MUST contain one row per account that has at least one transaction in
  at least one of the five pay periods displayed on the page, and no row for any other account.
- **FR-003**: The table MUST contain one column per pay period displayed by the page's
  "Remaining Balances" table — the previous, current, next, following and last periods — in
  that same order, with the same labels and the same suffix annotations (`(prev.)`, `(curr.)`,
  `(next)`).
- **FR-004**: Each cell MUST show the sum of the amounts of all transactions against that
  account in that pay period, counting both real transactions and scheduled transactions that
  have not been converted to real ones, and counting transactions that are excluded from budget
  arithmetic.
- **FR-005**: The set of transactions summed for a given account and period MUST be exactly
  the set of transactions the page's Transactions table lists for that account when that period
  is viewed, so that a reader can verify any cell by adding up the rows on screen.
- **FR-006**: A cell for an account/period combination with no transactions MUST show zero.
- **FR-007**: Negative totals MUST be visually distinguished using the same convention the rest
  of the page uses for negative amounts.
- **FR-008**: The column for the pay period currently being viewed MUST be visually emphasised
  in the same way as in the "Remaining Balances" table.
- **FR-009**: Column headers for pay periods other than the one being viewed MUST link to those
  pay periods' views.
- **FR-010**: Each account name MUST link to that account's detail view.
- **FR-011**: The table MUST include a totals row giving, for each period, the sum of all
  accounts' totals for that period.
- **FR-012**: Account rows MUST be ordered by account name, so that the ordering is stable
  between page loads and between periods.
- **FR-013**: The per-account totals MUST be available as a documented, reusable property of
  the pay period abstraction rather than computed inside the view, so that the same numbers can
  be obtained and tested without rendering a page.
- **FR-014**: Adding this table MUST NOT change any existing number, table or behaviour on the
  pay period view.

### Key Entities

- **Account**: an existing financial account (bank, credit, investment, cash). Contributes a
  row when it has transactions in any displayed period; identified to the reader by its name.
- **Pay period**: an existing fortnightly window. Contributes a column; five are displayed.
- **Transaction / Scheduled transaction**: existing records already summarised on this page.
  Each belongs to exactly one account and falls in exactly one pay period, and contributes its
  amount to exactly one cell.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can determine the total transaction amount for any account in the
  displayed pay period from the pay period view alone, without opening another page and without
  performing any arithmetic.
- **SC-002**: Every cell in the table equals the sum of the corresponding transactions listed
  on the corresponding pay period's view — verifiable by hand for any account and period, with
  zero discrepancies.
- **SC-003**: The totals row for the current period equals the sum of every account's total for
  that period, exactly.
- **SC-004**: All existing numbers on the pay period view are unchanged by this feature, as
  demonstrated by the existing test suite continuing to pass unmodified in respect of them.
- **SC-005**: The pay period view continues to load in the time it did before the change, with
  no additional database round trips beyond those the page already makes.

## Assumptions

- **Scope of "each payperiod"**: the request's "for each payperiod" is taken to mean the five
  pay periods this view already presents side by side in its "Remaining Balances" table, rather
  than an unbounded history. This gives the same period-to-period comparison the page already
  offers for remaining balances, keeps the table a fixed width, and costs nothing extra: the
  view already computes all five periods' data in full in order to render that table.
- **"Transaction totals" means account activity, not budget consumption**: the total is the sum
  of the amounts of the transactions against the account, including scheduled transactions the
  page projects into the period and including transactions excluded from budget arithmetic. The
  intent is to mirror the transaction list, which is what a reader would otherwise add up by
  hand.
- **Sign convention**: amounts keep the sign they already have elsewhere in the application —
  spending is positive and income is negative — so that the new table reads consistently with
  the Transactions table directly beside it.
- **Placement**: the table goes on the single pay period view (`/payperiod/YYYY-MM-DD`). The
  pay periods list view (`/payperiods`) is out of scope.
- **No schema change**: all the information required already exists in the database; no new
  tables, columns or migrations are needed.
- **No new configuration**: the feature is always on and has no settings.
