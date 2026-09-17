# Feature Specification: Show Inactive Accounts So They Can Be Re-Activated

**Feature Branch**: `robot-army/issue-276-inability-to-re-activate-an-account`

**Created**: 2026-09-17

**Status**: Draft

**Input**: GitHub issue [#276](https://github.com/jantman/biweeklybudget/issues/276) — "Inability to re-activate an Account" (labels: bug, robot-army); part of what was reported in #270.

> When the "Active" checkbox on the Account Edit modal is unchecked, the Account completely
> disappears from the UI. There's currently no way to re-activate an account aside from
> manually updating the database. Inactive accounts should still be shown in the UI except
> grayed out, the way inactive scheduled transactions are handled.
>
> **WORKAROUND:** connect to the database and manually re-enable the account
> (`SELECT id,name,is_active FROM accounts WHERE is_active=0;` then
> `UPDATE accounts SET is_active=1 WHERE id=6;`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Re-activate an account without touching the database (Priority: P1)

A user deactivates an account — deliberately, or by unchecking "Active?" in the Account
Edit modal without realising what it does. The account vanishes from every list on the
Accounts page, so there is no link left to open its edit modal and no way to undo the
change short of opening a MySQL client and running an `UPDATE`. The user needs the
deactivated account to remain visible on the Accounts page, visually distinguished from
the active ones, and still clickable so its edit modal opens and "Active?" can be
re-checked.

**Why this priority**: This is the entire bug. Without it a user who unchecks one
checkbox has permanently lost access to that account through the application, and the
only documented recovery is hand-editing the production database — an operation the
application otherwise never asks of its user, and one that risks far worse damage than
the mistake being repaired.

**Independent Test**: Deactivate an account through the Account Edit modal, confirm it is
still listed on the Accounts page as an inactive row, click it, re-check "Active?", save,
and confirm the account is listed as active again — all without a database client.

**Acceptance Scenarios**:

1. **Given** an account marked inactive, **When** the user loads the Accounts page,
   **Then** the account appears in the table for its account type, visually marked as
   inactive, and its name is a link that opens the Account Edit modal.
2. **Given** the Account Edit modal open for an inactive account, **When** the user
   checks "Active?" and saves, **Then** the save succeeds, the page reloads, and the
   account is shown as active.
3. **Given** an active account, **When** the user unchecks "Active?" in its edit modal and
   saves, **Then** the account remains listed on the Accounts page, now marked inactive.
4. **Given** an inactive account, **When** the user opens its edit modal, **Then**
   "Active?" is shown unchecked, reflecting its stored state.

---

### User Story 2 - Tell active and inactive accounts apart at a glance (Priority: P2)

A user scanning the Accounts page needs to know immediately which accounts are live and
which are historical, so that an inactive account's stale balance is never mistaken for a
current one and so the presence of extra rows does not make the page harder to read than
it was before.

**Why this priority**: Story 1 delivers the fix; without this, the fix reintroduces a
different problem — an account that no longer counts toward anything sitting
indistinguishably among ones that do, on a page about money. The application already
solves exactly this for Budgets, whose page lists inactive budgets in a greyed row with an
explicit "Active?" column, and for Scheduled Transactions and Projects, whose rows are
greyed the same way.

**Independent Test**: Load the Accounts page with both active and inactive accounts
present and confirm each table carries an "Active?" indication per row and that inactive
rows are visually greyed, matching the treatment on the Budgets page.

**Acceptance Scenarios**:

1. **Given** the Accounts page with both active and inactive accounts, **When** it is
   rendered, **Then** inactive rows are greyed using the application's existing inactive-row
   styling and active rows are not.
2. **Given** the Accounts page, **When** it is rendered, **Then** each account table shows,
   per row, whether that account is active, in the same "Active?" form the Budgets page
   uses.
3. **Given** the Accounts page, **When** it is rendered, **Then** accounts are ordered by
   name within each account-type table, with active and inactive accounts interleaved by
   name rather than segregated.

---

### Edge Cases

- **An inactive account has no recorded balance or statement.** An account can be created
  and deactivated before any balance is ever recorded for it. The Accounts page must
  render such a row without error, leaving the balance-derived cells blank or zero rather
  than failing the whole page. (Surfacing inactive accounts makes this state reachable in
  a way it largely was not before.)
- **An inactive credit account.** Credit rows compute Available and Difference from the
  credit limit and balance; an inactive credit account with a missing credit limit or
  balance must not break those cells or the page.
- **An inactive account's data is stale.** Inactive accounts will nearly always have old
  data, so the "stale data" red highlight would fire on essentially every inactive row and
  say nothing. The staleness warning must not be applied to inactive accounts.
- **Every account of a type is inactive.** The table for that account type still renders,
  showing those rows, rather than appearing empty.
- **No inactive accounts exist.** The Accounts page looks and behaves as it does today,
  aside from the new per-row active indication.
- **An inactive account is reachable by direct URL.** Opening `/accounts/<id>` for an
  inactive account opens its edit modal as it does for an active one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Accounts page MUST list every account of each account type — bank,
  credit, and investment — regardless of whether the account is active.
- **FR-002**: Each account row on the Accounts page MUST indicate whether that account is
  active, presented the way the Budgets page presents budget activity.
- **FR-003**: Rows for inactive accounts MUST be visually greyed using the application's
  existing inactive-row styling, the same styling applied to inactive budgets, scheduled
  transactions, and project items.
- **FR-004**: An inactive account's name on the Accounts page MUST be a link that opens
  that account's edit modal, exactly as an active account's name is.
- **FR-005**: The Account Edit modal MUST show the account's stored active state in the
  "Active?" checkbox, and saving with that checkbox checked MUST make the account active
  again.
- **FR-006**: The Accounts page MUST render account rows whose balance, statement, or
  credit limit is absent without raising an error.
- **FR-007**: The "stale data" warning MUST NOT be applied to inactive accounts.
- **FR-008**: Accounts MUST remain ordered by name within each account-type table, with
  inactive accounts placed by name among the active ones.
- **FR-009**: The treatment of inactive accounts everywhere outside the Accounts page
  MUST be unchanged. The dashboard, the cash position page, pay period calculations, and
  the account balance chart MUST continue to leave inactive accounts out, and the account
  transfer and transaction forms MUST continue to reject an inactive account with the
  error they already give. This change makes inactive accounts *visible and editable on
  the Accounts page*; it does not make them *usable*.
- **FR-010**: Documentation describing the Accounts page MUST be updated to state that
  inactive accounts are listed there, greyed, and can be re-activated from their edit
  modal.

### Key Entities

- **Account**: A financial account (bank, credit, or investment). Already carries an
  "active" flag that marks it as usable versus historical. No change to what an account
  is or what is stored about it — only to whether the Accounts page shows it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who has deactivated an account can re-activate it entirely through
  the web interface, in under one minute, with no database client and no knowledge of the
  account's numeric id.
- **SC-002**: 100% of accounts, active and inactive, are reachable from the Accounts page;
  no account can be put into a state where the application offers no way to reach it.
- **SC-003**: A user viewing the Accounts page can correctly identify every inactive
  account from the page alone, without opening any modal.
- **SC-004**: The database workaround described in issue #276 is no longer needed for any
  account, and can be removed from the record as the only recovery path.
- **SC-005**: No balance, total, or projection shown anywhere in the application changes
  as a result of this feature.

## Assumptions

- **Scope is the Accounts page.** "Shown in the UI" is read as the Accounts page — the
  page whose job is managing accounts and which hosts the edit modal. This mirrors how
  the application already treats Budgets: the Budgets page lists inactive budgets greyed,
  while the dashboard's standing-budget panel lists only active ones. Surfacing inactive
  accounts on the dashboard, the cash position page, or in transaction and transfer
  account pickers is explicitly out of scope, and FR-009 requires those to keep excluding
  them.
- **"The way inactive scheduled transactions are handled"** is read as the existing
  greyed-row treatment (`tr.inactive`) shared by Scheduled Transactions, Projects, and
  Budgets. The Budgets page is taken as the closer model, because like Accounts it is a
  server-rendered table rather than a DataTables-driven one, and it already pairs the
  greyed row with an explicit "Active?" column.
- **No filter control is added.** No "show/hide inactive" toggle is introduced; the
  number of accounts a single operator holds does not warrant one, and the greyed styling
  plus the "Active?" column is the distinction the issue asks for.
- **No schema change.** The `is_active` flag on accounts already exists and already
  persists correctly; the bug is purely that the Accounts page filters inactive accounts
  out of its queries. No Alembic migration is expected.
- **Deactivation behaviour is unchanged.** Unchecking "Active?" continues to mean what it
  means today — the account stops contributing to balances, totals, and pickers. Only its
  disappearance from the Accounts page is treated as the defect.
- **Deleting accounts is out of scope.** This feature makes deactivation reversible; it
  does not add a way to remove an account.
