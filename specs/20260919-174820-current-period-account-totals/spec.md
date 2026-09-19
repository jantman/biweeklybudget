# Feature Specification: Current-Period Per-Account Transaction Totals

**Feature Branch**: `robot-army/issue-355-pay-period-per-account-transaction`

**Created**: 2026-09-19

**Status**: Draft

**Input**: GitHub issue [#355](https://github.com/jantman/biweeklybudget/issues/355) —
"Pay period per-account transaction totals: show only the current period, with accounts
as columns"

## Context

The pay period view carries a **Per-Account Transaction Totals** panel, added by issue
#213. It answers a question no other part of the page answers: how much money moved
through each account. As built, it shows five pay periods — the previous period, the one
being viewed, and the three that follow — as five columns, with one row per account that
had activity in any of them.

Two problems with that shape, both reported from the 2.0.0 release verification
checklist (#353):

1. The four non-current columns are not meaningful in practice. Future periods contain
   only projected scheduled transactions, and the previous period's totals are a
   question better asked by viewing that period. The value of the panel is seeing where
   *this* period's money actually moved.
2. One row per account, on a page that is already very long, spends a large amount of
   vertical space on those four unhelpful columns.

Transposing the table — accounts across the top, a single row of amounts beneath —
reduces the panel to two rows regardless of how many accounts exist, and dropping the
other four periods removes four fifths of the data that is not being used.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See where this period's money moved, at a glance (Priority: P1)

A user viewing a pay period wants to know how much money moved through each of their
accounts during that period. They scroll to the Per-Account Transaction Totals panel and
read one row: an amount per account, and a grand total. The panel occupies two rows of
the page rather than one row per account.

**Why this priority**: This is the whole of the requested change and the entire value of
the panel. Without it there is nothing to ship.

**Independent Test**: Load a pay period with transactions in several accounts and confirm
the panel shows one header row of account names and one row of amounts, that each amount
equals the sum of that account's transactions in the viewed period, and that the amounts
match what the per-account totals showed in the current-period column before this change.

**Acceptance Scenarios**:

1. **Given** a pay period in which three accounts have transactions, **When** the user
   views that pay period, **Then** the Per-Account Transaction Totals table shows one
   header cell per account (plus a `Total` header) and exactly one row of amounts
   beneath it.
2. **Given** an account with transactions in the viewed period, **When** the user views
   the period, **Then** the amount shown for that account equals the sum of that
   account's transactions in that period, with income negative and shown in red and
   spending positive.
3. **Given** a pay period being viewed, **When** the user reads the table, **Then** the
   final cell is the sum of every account's amount for that period.
4. **Given** a period other than the current one is being viewed, **When** the user
   reads the table, **Then** the amounts are those of the period being viewed, not of
   today's period.

---

### User Story 2 - Only accounts with activity, and a way into them (Priority: P2)

A user sees only the accounts that actually had activity in the viewed period, so the
table stays as narrow as the period's activity allows, and can click an account name to
open that account.

**Why this priority**: Narrowing the account set is what keeps a transposed table from
growing without bound, and the account links are existing behaviour users rely on to get
from an unexpected number to its detail. Both matter, but the table is useful before
either is perfect.

**Independent Test**: Load a period in which one account has no transactions and confirm
that account has no column, then click an account name that is present and confirm it
opens that account's page.

**Acceptance Scenarios**:

1. **Given** an account with no transactions in the viewed period, **When** the user
   views that period, **Then** that account has no column in the table.
2. **Given** an account that had transactions in an adjacent period but none in the
   viewed period, **When** the user views the period, **Then** that account has no
   column in the table.
3. **Given** an account column in the table, **When** the user clicks its name, **Then**
   that account's page opens.

---

### User Story 3 - The panel still reads correctly when nothing happened (Priority: P3)

A user viewing a pay period with no transactions at all still sees the panel, rather than
a broken or missing table, and can tell that the answer is zero.

**Why this priority**: It is a single edge case rather than the main journey, but the
panel appearing empty or malformed on a fresh database or a far-future period would look
like a bug.

**Independent Test**: Load a pay period with no transactions in any account and confirm
the table renders with a `Total` column showing `$0.00`.

**Acceptance Scenarios**:

1. **Given** a pay period in which no account has any transaction, **When** the user
   views that period, **Then** the table renders with a `Total` header and a single
   amount cell of `$0.00`, and no account columns.

---

### Edge Cases

- **No accounts have activity**: the table still renders, with the `Total` column alone
  and `$0.00` beneath it (User Story 3).
- **Many accounts have activity**: the table grows horizontally. It sits inside the
  page's existing responsive-table wrapper, which scrolls it horizontally rather than
  letting it overflow the page.
- **An account nets exactly zero** in the viewed period while having transactions in it:
  it keeps its column and shows `$0.00`. Presence is decided by having transactions, not
  by a non-zero total.
- **Inactive accounts** with transactions in the period: unchanged from today — the
  table reports whatever accounts the period's transactions belong to, with no
  active/inactive filtering of its own.
- **A period whose only activity is a credit card payment or a no-budget-impact
  transaction**: that account appears with the full amount, and the table's total
  deliberately disagrees with the period's *spent* figure above it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Per-Account Transaction Totals panel MUST show totals for the pay
  period being viewed, and for no other pay period.
- **FR-002**: The table MUST present accounts as columns and the amounts as a single
  row: one header row and one data row.
- **FR-003**: The table MUST include a column for each account that has at least one
  transaction in the viewed period, and MUST NOT include a column for any account that
  has none.
- **FR-004**: Account columns MUST be ordered by account name, ascending.
- **FR-005**: Each account's amount MUST be the sum of that account's transactions in
  the viewed period, including scheduled transactions the period projects, credit card
  payments, and transactions marked *No Budget Impact*.
- **FR-006**: Amounts MUST keep their existing sign convention and formatting: spending
  positive, income negative and displayed in red, formatted as currency.
- **FR-007**: The table MUST end with a `Total` column whose value is the sum of every
  account amount in the row.
- **FR-008**: Each account column header MUST link to that account's page.
- **FR-009**: The table MUST NOT link to, label, or otherwise display the previous,
  next, following or last pay periods.
- **FR-010**: With no accounts having activity in the viewed period, the table MUST still
  render, showing the `Total` column with a zero amount.
- **FR-011**: The table MUST remain plain server-rendered markup inside the existing
  responsive-table wrapper — no sorting, paging or client-side table widget is added.
- **FR-012**: The documented explanation of why these totals intentionally differ from
  the page's budget totals (they include credit card payments and no-budget-impact
  transactions) MUST be retained, and the documentation MUST be updated to describe the
  table's new shape and single-period scope.
- **FR-013**: The `Remaining Balances` table at the top of the pay period view MUST be
  unchanged; it keeps its five periods.

### Key Entities

- **Pay period**: the fortnight being viewed, which now solely determines the table's
  contents.
- **Account**: a financial account; contributes a column when it has at least one
  transaction in the viewed period, identified by its name and linked to its page.
- **Per-account total**: one amount per account — the sum of that account's transactions
  in the viewed period.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The panel occupies exactly two table rows for any number of accounts,
  down from one row per active account plus a totals row.
- **SC-002**: Each account's amount on the pay period view equals the amount that
  account showed in the current-period column of the previous five-column table, for the
  same period and data.
- **SC-003**: The `Total` cell equals the sum of the account amounts shown beside it, for
  every period tested.
- **SC-004**: No pay period other than the one being viewed can be identified anywhere in
  the panel.
- **SC-005**: A pay period with no transactions renders the panel without error.
- **SC-006**: The full unit and acceptance suites pass, and the documentation build
  succeeds.

## Assumptions

- The panel's heading text stays **Per-Account Transaction Totals**. The page already
  names the pay period it is showing, in its title and in the summary above the panel, so
  the panel does not need to repeat it.
- The current-period highlight styling that distinguished one of the five columns is
  dropped, having nothing left to distinguish.
- The table keeps its `pp-acct-table` element id, so existing test selectors and any
  user styling continue to find it.
- "Transactions in the period" keeps exactly its present meaning — whatever the pay
  period already reports as its per-account sums, which is the same set of transactions
  the page's Transactions table lists.
- The helper that builds this table's data is used only by this table, so narrowing it to
  a single period affects nothing else on the site.
- No database schema change is involved; this is a presentation change over data that is
  already computed.
