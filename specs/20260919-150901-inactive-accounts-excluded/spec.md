# Feature Specification: Exclude Inactive Accounts From Dropdowns And The Balances Chart

**Feature Branch**: `robot-army/issue-356-inactive-accounts-are-still-offered-in`

**Created**: 2026-09-19

**Status**: Draft

**Input**: GitHub issue [#356](https://github.com/jantman/biweeklybudget/issues/356) — "Inactive Accounts are still offered in account dropdowns and plotted on the Account Balances chart" (labels: bug, robot-army). Found while working through the 2.0.0 release verification checklist, [#353](https://github.com/jantman/biweeklybudget/issues/353).

## Background

Issue [#276](https://github.com/jantman/biweeklybudget/issues/276) made inactive Accounts visible on the Accounts page (greyed, `Active? = NO`), and the changelog entry for that work promised that inactive Accounts remain excluded everywhere else — the dashboard, Cash Position, pay period calculations and the Account Balances chart — and are still rejected as the source or destination of an account transfer.

That promise is only half kept. The dashboard, Cash Position, pay-period arithmetic, the server-side transfer rejection and the "stale data" warning all do filter on active. But every page that offers an account **picker** builds its list from an unfiltered list of all Accounts, and the Account Balances chart on the dashboard plots every Account that has ever recorded a balance. A closed account therefore stays in every dropdown and keeps a flat line on the chart forever.

Closing an account is the user's statement that they are done with it. Once closed it should stop being offered as somewhere to put new money or new records, and it should stop occupying a colour on the balance chart — while every record that already points at it must keep pointing at it, unchanged and visible.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A closed account leaves the balances chart (Priority: P1)

A user who closed a bank account months ago opens the dashboard. The Account Balances chart shows only the accounts they still hold. The closed account's flat line, and its entry in the chart legend, are gone.

**Why this priority**: This is the data problem, not just a cosmetic one. A dead flat line permanently distorts the chart's vertical scale and its legend, and it is the item explicitly named in the 2.0.0 verification checklist. It is also the change a user cannot work around.

**Independent Test**: Load the dashboard with sample data containing one inactive account that has recorded balances. The chart's series list contains every active account and not the inactive one; the active accounts' values are unchanged from before.

**Acceptance Scenarios**:

1. **Given** an inactive Account with recorded balance history, **When** the Account Balances chart data is requested, **Then** that Account appears neither in the chart's series list nor in any data point.
2. **Given** several active Accounts and one inactive Account, **When** the Account Balances chart data is requested for any history window, **Then** every active Account's series is identical to what it was before this change.
3. **Given** an inactive Account whose only balance records fall before the requested history window, **When** the chart data is requested, **Then** no carried-forward value for it is emitted either.
4. **Given** an Account that is deactivated, **When** the dashboard is reloaded, **Then** the chart reflects the change immediately, with no cache to clear and no stored data removed.

---

### User Story 2 - Closed accounts are not offered for new records (Priority: P1)

A user adds a transaction, transfers money between accounts, transfers between budgets, logs a fuel fill or creates a scheduled transaction. Every Account picker in those forms lists only the accounts they still hold.

**Why this priority**: Equal in importance to the chart. Offering a closed account is an invitation to make a record the application will then refuse (transfers) or will silently accept against a closed account (transactions, scheduled transactions, fuel fills). Both outcomes are the application contradicting its own Accounts page.

**Independent Test**: Open each affected form with sample data containing one inactive Account, and read the options of its Account select. The inactive Account is absent; every active Account is present, in the same order as before.

**Acceptance Scenarios**:

1. **Given** an inactive Account, **When** the Account Transfer modal is opened from the dashboard or the Accounts page, **Then** neither the From Account nor the To Account select offers it.
2. **Given** an inactive Account, **When** the Add Transaction modal is opened, **Then** the Account select does not offer it.
3. **Given** an inactive Account, **When** the Budget Transfer modal is opened from the Budgets page or a pay period page, **Then** the Account select does not offer it.
4. **Given** an inactive Account, **When** the Add Scheduled Transaction modal is opened, **Then** the Account select does not offer it.
5. **Given** an inactive Account, **When** the Add Fuel Fill modal is opened, **Then** the Account select does not offer it.
6. **Given** an inactive Account, **When** any of the above forms is submitted, **Then** the resulting record is created against the active Account the user chose, exactly as before.

---

### User Story 3 - An existing record keeps the closed account it points at (Priority: P1)

A user opens an old transaction, or a scheduled transaction, whose Account has since been closed. The form still shows that account as the selected one. Saving the record without touching the Account leaves it pointing where it pointed.

**Why this priority**: Without this, the fix is worse than the bug. Dropping the inactive Account from the list would leave an existing record's Account select showing the wrong account, or nothing at all, and a save would silently retarget or blank a financial record. This must ship in the same change as User Story 2, not after it.

**Independent Test**: Create a transaction against an Account, deactivate the Account, then open that transaction's modal. The select shows the inactive Account as selected, and saving with no other edit leaves the transaction's Account unchanged.

**Acceptance Scenarios**:

1. **Given** a Transaction whose Account is now inactive, **When** its Edit modal is opened, **Then** the Account select shows that inactive Account as the selected option.
2. **Given** that same Transaction, **When** it is saved with no change to the Account, **Then** its Account is unchanged.
3. **Given** a ScheduledTransaction whose Account is now inactive, **When** its Edit modal is opened, **Then** the Account select shows that inactive Account as the selected option, and saving leaves it unchanged.
4. **Given** a ScheduledTransaction whose Account is now inactive, **When** the "skip scheduled transaction" form is opened for it from a pay period page, **Then** the disabled Account field shows that inactive Account, and the resulting skip Transaction is created against it.
5. **Given** a Transaction whose Account is active, **When** its Edit modal is opened, **Then** the Account select contains only active Accounts — the inactive one is not added.

---

### User Story 4 - Historical data stays searchable by closed account (Priority: P2)

A user looking for last year's spending filters the Transactions table, or the downloaded-transactions table, by an account they have since closed. That account is still offered as a filter value.

**Why this priority**: Not a change — a boundary that must be protected. These selects narrow a view of history rather than choosing a destination for new data, and history includes closed accounts. The Budget filter on the same Transactions table already works this way, listing every budget while the Budget entry field lists only active ones. Getting this wrong would hide the user's own history from them.

**Independent Test**: Open the Transactions page and the downloaded-transactions page with sample data containing one inactive Account; the Account filter select still lists it, and filtering by it still returns that account's rows.

**Acceptance Scenarios**:

1. **Given** an inactive Account with transactions, **When** the Transactions page Account filter is opened, **Then** the inactive Account is offered.
2. **Given** an inactive Account with downloaded transactions, **When** that page's Account filter is opened, **Then** the inactive Account is offered.
3. **Given** the Accounts page, **When** it is loaded, **Then** it still lists inactive Accounts, greyed, with `Active? = NO`, exactly as issue #276 specified.

---

### Edge Cases

- **An account is deactivated while a form is open.** The open form keeps the list it was rendered with. The server-side rules are the authority: an account transfer to or from an inactive Account is still rejected with a validation error. No new client-side enforcement is added, and none is removed.
- **The configured default account is inactive.** Forms that preselect a default Account (Add Fuel Fill, Add Scheduled Transaction) simply have nothing preselected, leaving the empty "None" option showing, rather than failing or inventing a selection. A user can still pick any active account.
- **Every Account is inactive.** Entry forms show an Account select with only the empty option; the Account Balances chart returns an empty series list and empty data with a success status, not an error.
- **An inactive Account is the only one with balances in a window.** The chart returns the remaining accounts' data for that window; no series is fabricated for the excluded account and no error is raised for its now-unreferenced balance records.
- **A record points at an Account that no longer exists at all.** Out of scope and unchanged: accounts are deactivated, not deleted, and nothing in this change alters deletion behaviour.
- **A user reactivates a previously inactive Account.** It reappears in every dropdown and on the chart, with its full balance history, on the next page load. Nothing about deactivation is destructive.

## Requirements *(mandatory)*

### Functional Requirements

**Account Balances chart**

- **FR-001**: The Account Balances chart data MUST exclude inactive Accounts from its series list.
- **FR-002**: The Account Balances chart data MUST exclude inactive Accounts from every data point, including the carried-forward values used to keep a line continuous across a history window.
- **FR-003**: Excluding an inactive Account MUST NOT change any active Account's values, the set of dates returned, the ordering of dates, or the response's overall shape.
- **FR-004**: Balance records belonging to inactive Accounts MUST remain stored and MUST NOT cause an error when encountered; they are skipped, not deleted.

**Account pickers for new and edited records**

- **FR-005**: The Account Transfer form's From Account and To Account selects MUST offer only active Accounts.
- **FR-006**: The Add/Edit Transaction form's Account select MUST offer only active Accounts.
- **FR-007**: The Budget Transfer form's Account select MUST offer only active Accounts.
- **FR-008**: The Add/Edit Scheduled Transaction form's Account select MUST offer only active Accounts.
- **FR-009**: The Add Fuel Fill form's Account select MUST offer only active Accounts.
- **FR-010**: The "skip scheduled transaction" form's Account field MUST offer only active Accounts, except as required by FR-011.

**Preserving an existing record's account**

- **FR-011**: When a form is opened to edit an existing record whose Account is inactive, that Account MUST be shown and selected in the Account field, and saving the record without changing that field MUST leave the record's Account unchanged.
- **FR-012**: The inactive Account added under FR-011 MUST appear only for the record that references it; opening a form for a record with an active Account, or for a new record, MUST show only active Accounts.

**What must not change**

- **FR-013**: The Accounts page MUST continue to list inactive Accounts, as specified by issue #276.
- **FR-014**: Account selects that filter a table of existing records — the Transactions page Account filter and the downloaded-transactions page Account filter — MUST continue to offer inactive Accounts.
- **FR-015**: Server-side validation MUST be unchanged: an account transfer whose source or destination is inactive is still rejected, and the rules governing which Accounts may be chosen elsewhere are unaffected.
- **FR-016**: No database schema change, data migration or destructive data change is required or permitted by this feature.

### Key Entities

- **Account**: A financial account, already carrying an active/inactive flag. This feature changes only which Accounts are *offered* and *charted*; no Account attribute is added, changed or removed.
- **Account Balance**: A dated ledger balance belonging to an Account. Records for inactive Accounts are retained and simply not charted.
- **Transaction / ScheduledTransaction / FuelFill**: Records that reference an Account. Their stored Account references are never altered by this feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With sample data containing one inactive Account, the Account Balances chart shows exactly the active Accounts — the inactive Account appears in zero series and zero data points.
- **SC-002**: Every Account picker used to create or edit a record offers exactly the set of active Accounts, in all six affected forms, verified on screen.
- **SC-003**: Opening and saving an existing record whose Account is inactive leaves that record's Account unchanged, in 100% of cases, for both Transactions and ScheduledTransactions.
- **SC-004**: The Accounts page and both table filters still show inactive Accounts, so no historical data becomes unreachable.
- **SC-005**: The complete unit and acceptance suites pass, with the existing assertions that expect an inactive Account in an entry-form dropdown updated to expect its absence, and no assertion weakened or removed to accommodate a failure.
- **SC-006**: The [#353](https://github.com/jantman/biweeklybudget/issues/353) checklist item "Inactive Accounts remain excluded from the dashboard, Cash Position, pay period calculations and the Account Balances chart, are still rejected as transfer source or destination, and get no stale data warning" can be checked off.

## Assumptions

- **"Offered" means selectable for new or edited data; "listed" means visible as history.** The issue names four places and flags five more files as "worth reviewing at the same time". This spec resolves that review by the rule the Budget dropdowns already follow: a select that chooses where a *record* goes lists active only (FR-005 to FR-010), a select that *filters existing rows* lists everything (FR-014). That rule is what puts the Transactions and downloaded-transactions Account filters out of the change and the Fuel Fill, Scheduled Transaction and skip-scheduled-transaction selects into it, beyond the four the issue confirmed on screen.
- **The inactive-budget pattern is the model for the inactive-account fix.** The Budget selects already solve the "deactivated while still referenced" problem by supplying both a full and an active-only list and re-adding the record's own value when it is not in the active list. This feature follows that established pattern rather than inventing a second mechanism.
- **Inactive Accounts are not visually marked in the pickers.** Because they no longer appear except as an existing record's own value, no greying, suffix or "(inactive)" label is added to any select option. The Accounts page remains the place where active state is displayed.
- **No new server-side rejection is added.** Transfers already reject inactive Accounts server-side; transactions, scheduled transactions and fuel fills do not, and this feature does not change that. It removes the invitation, not the ability — a record already pointing at an inactive Account must still be saveable (FR-011), which forbids a blanket server-side rejection.
- **The Accounts page's unfiltered Account query is deliberate and stays.** The fix supplies an additional active-only list rather than filtering the existing one, so the Accounts page keeps listing inactive Accounts (FR-013).
- **Existing acceptance tests will need updating.** A number of tests assert dropdown contents that currently include the sample data's inactive `DisabledBank` account. Updating those assertions to match the new intended behaviour is part of this change, and is distinct from weakening a test to make it pass.
