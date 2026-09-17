# Feature Specification: Balance-less Accounts Must Not Break The Landing Pages

**Feature Branch**: `robot-army/issue-334-active-account-with-no-accountbalance`

**Created**: 2026-09-17

**Status**: Draft

**Input**: GitHub issue #334 — "Active account with no AccountBalance row makes / and /accounts fail with HTTP 500"

## Overview

An account that has never had a balance recorded for it — the state every account is in
between the moment it is created and the moment its first balance arrives — makes the
application's landing page fail to render. Because the landing page is where the
application opens, a single such account effectively locks the operator out of the UI at
exactly the moment they are most likely to be looking at it: just after adding an account.

The same defect on the Accounts page was fixed by the "Show Inactive Accounts" change
(issue #276), but only for the inactive accounts that change made visible. The landing
page still carries it, and nothing pins the Accounts page's behaviour for an *active*
balance-less account.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add an account and keep using the application (Priority: P1)

The operator adds a new account through the Accounts page — a new credit card, a new bank
account — and then navigates to the landing page to see where they stand. The new account
has no balance yet; its first balance will not arrive until the next Plaid update or until
the operator records one by hand. The landing page must still render, showing the new
account in its table with its value cells blank, and showing every other account's figures
exactly as before.

**Why this priority**: Without it the operator cannot reach the landing page at all. Every
other view of the application is reached from it, so this is not a degraded page — it is a
lockout, and it is triggered by the most ordinary action there is.

**Independent Test**: Add an active account of each displayed type with no balance
recorded, then request the landing page. It renders successfully and lists the new
accounts.

**Acceptance Scenarios**:

1. **Given** an active bank account with no recorded balance, **When** the operator opens
   the landing page, **Then** the page renders successfully and the bank table contains a
   row for that account.
2. **Given** an active credit account with no recorded balance and no credit limit,
   **When** the operator opens the landing page, **Then** the page renders successfully and
   the credit table contains a row for that account.
3. **Given** an active investment account with no recorded balance, **When** the operator
   opens the landing page, **Then** the page renders successfully and the investment table
   contains a row for that account.
4. **Given** any of the above, **When** the operator reads the new account's row, **Then**
   the cells that would be derived from the missing balance are blank, rather than showing
   a figure the application does not actually know.
5. **Given** any of the above, **When** the operator reads the rows of accounts that *do*
   have balances, **Then** every figure in those rows is unchanged from what it was before
   the balance-less account existed.

---

### User Story 2 - The Accounts page tolerates an active balance-less account (Priority: P2)

The operator opens the Accounts page while a newly added, still-active account has no
balance. The page renders, listing that account with blank value cells, the same way it
already does for an inactive account with no data.

**Why this priority**: The Accounts page is the only place an account can be edited, so
losing it while an account is half set up is nearly as bad as losing the landing page. The
behaviour is believed already correct; what is missing is anything that holds it correct.
An account that is *active* takes a different path through the page than the inactive one
currently covered — the staleness treatment differs — so the covered case does not prove
this one.

**Independent Test**: Add an active account of each displayed type with no balance, then
request the Accounts page. It renders successfully with blank value cells for those rows.

**Acceptance Scenarios**:

1. **Given** an active bank, credit, or investment account with no recorded balance,
   **When** the operator opens the Accounts page, **Then** the page renders successfully.
2. **Given** that account's row, **When** the operator reads it, **Then** its
   balance-derived cells are blank and the row is shown as active.

---

### User Story 3 - A recorded balance with no ledger figure is treated the same (Priority: P3)

An account can have a balance record whose ledger figure is absent — the record exists but
the number the pages display does not. The operator must see the same blank cells and
working pages as for an account with no balance record at all.

**Why this priority**: It is a second, independent route to the identical failure, and
closing only the first one leaves the pages breakable. It is rarer than the P1 case, which
is why it ranks below it.

**Independent Test**: Record a balance with no ledger figure for an active account and
request both pages; both render with blank cells for that account.

**Acceptance Scenarios**:

1. **Given** an active account whose most recent balance record has no ledger figure,
   **When** the operator opens the landing page or the Accounts page, **Then** the page
   renders successfully with that account's balance-derived cells blank.

---

### Edge Cases

- **A credit account with a balance but no credit limit.** The "available credit" figures
  are derived from both. With either missing, those cells must be blank rather than
  breaking the page.
- **An account with no statement.** A balance-less account has also never had a statement,
  so the "as of" age shown beside the balance has nothing to report. It must be omitted
  entirely rather than rendered as empty parentheses beside a blank balance.
- **Staleness for an account with no statement.** Staleness is measured from the newest
  statement. An account without one is not stale and must not be flagged as such.
- **Every account is balance-less.** The pages must render, with all figures blank; no
  total or aggregate may report a fabricated number.
- **The account is inactive.** The landing page lists only active accounts, so an inactive
  balance-less account must remain absent from it, exactly as today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The landing page MUST render successfully when any account it lists has no
  recorded balance.
- **FR-002**: The Accounts page MUST render successfully when any account it lists — active
  or inactive — has no recorded balance.
- **FR-003**: Where a displayed figure cannot be computed because the balance, the ledger
  figure within it, or the credit limit it depends on is absent, the application MUST show
  that cell as blank. It MUST NOT substitute zero or any other stand-in value, because "no
  balance has ever been recorded" and "the balance is $0.00" are different facts about the
  operator's money and must not be made to look alike.
- **FR-004**: An account with no recorded balance MUST still appear in the table for its
  type, with its name and its link to the rest of the application intact, so that the
  operator can see and act on the account they just created.
- **FR-005**: The age of the data shown beside a balance MUST be omitted, rather than shown
  empty, for an account that has no statement to date it from.
- **FR-006**: An account with no statement MUST NOT be flagged as having stale data.
- **FR-007**: Every figure shown for an account that does have a balance MUST be unchanged
  by this work.
- **FR-008**: A balance record that exists but carries no ledger figure MUST be treated
  exactly as no balance record at all, on both pages.
- **FR-009**: Which accounts each page lists MUST be unchanged: the landing page continues
  to list only active accounts, and the Accounts page continues to list all of them.
- **FR-010**: Both pages' behaviour with a balance-less *active* account MUST be covered by
  automated acceptance tests, since nothing exercises that state today.

### Key Entities

- **Account**: A financial account the operator holds. Its current balance is not stored on
  the account itself but derived from the most recent balance record, of which there may be
  none.
- **Account balance record**: A dated record of an account's ledger and available figures.
  An account may have none, and a record that exists may itself carry no ledger figure.
- **Statement**: A dated record downloaded for an account, used to say how old the displayed
  balance is and whether it has gone stale. An account may have none.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With an active account of every displayed type present and no balance recorded
  for any of them, the landing page and the Accounts page both render successfully, where
  today the landing page fails outright.
- **SC-002**: The operator can add an account and continue using every page of the
  application without first recording a balance for it.
- **SC-003**: No figure shown anywhere in the application for an account that has a balance
  changes as a result of this work.
- **SC-004**: An account with no recorded balance is distinguishable at a glance from an
  account whose balance is zero: the first shows nothing, the second shows $0.00.
- **SC-005**: The complete unit and acceptance suites pass, including new tests that fail
  against the current code for the landing page.

## Assumptions

- **Blank, not zero, and not hidden.** The issue leaves this as an open design call and
  suggests $0.00. It is settled here against that suggestion, following the precedent set
  and reasoned in `specs/20260917-053603-show-inactive-accounts/research.md` (R5): the
  Accounts page already renders these cells blank, and inventing a zero balance was
  explicitly rejected there because it makes "never recorded" indistinguishable from
  "zero" — a meaningful difference when the subject is the operator's real money. Omitting
  the row instead was never on the table: the operator needs to see the account they just
  created. Doing anything else on the landing page would leave the two pages disagreeing
  about the same account.
- **The fix belongs where the pages are rendered, not in the data model.** The same
  precedent rejected having the account report a synthetic zero balance, because the
  balance is also read by the charts, the cash position page, and the pay period
  calculations, which each need to know that no balance exists.
- **The Accounts page is already correct** and needs test coverage rather than change. This
  is to be verified rather than assumed during planning; if it proves incorrect for an
  active account, fixing it is in scope under FR-002.
- **Sample data used by the tests is unchanged.** The balance-less accounts a test needs are
  created by that test, as the existing inactive-account coverage does, so that no other
  test's expected figures shift.

## Out of Scope

- **The credit payoff page.** An active credit account with no balance breaks it too, by the
  same root cause but through a different, calculation-side code path that would need its
  own decision about what a payoff projection means for an account with no balance. Issue
  #334 is scoped to the landing and Accounts pages, and this change stays there. The defect
  is real and is reported in the pull request so it can be tracked separately.
- **Recording a balance automatically when an account is created.** That would hide this
  class of failure rather than fix it, and would put a fabricated zero balance into the
  operator's financial history.
- **The balance chart, the cash position page, and the pay period views**, which already
  handle an absent balance.
