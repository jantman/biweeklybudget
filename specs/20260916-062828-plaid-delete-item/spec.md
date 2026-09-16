# Feature Specification: Delete a Plaid Item

**Feature Branch**: `robot-army/issue-269-plaid-add-ability-to-delete-an-item`

**Created**: 2026-09-16

**Status**: Draft

**Input**: GitHub issue [#269](https://github.com/jantman/biweeklybudget/issues/269) — "Plaid - Add ability to delete an item"

## Context

A Plaid Item is one linked financial institution: the credential-backed connection through
which this application downloads transactions for one or more accounts at that institution.
The application can create Items — the Plaid Update page has a "Link (Add Plaid Item)"
button — but it has no way to get rid of one. Items accumulate: a closed bank account, an
institution the maintainer no longer uses, a duplicate created while fixing a broken login,
or the entire set of Items when moving between Plaid environments.

Removing one today means leaving the application entirely. The issue documents the procedure:
read the Item's access token out of the database by hand, unlink every Account that points at
one of its Plaid Accounts, delete the Plaid Account and Plaid Item rows with raw SQL, then
open a Python shell inside the running container and call Plaid's Item-removal API with the
token that was just deleted from the database. The project's own documentation carries the
same raw SQL in its "Changing Plaid Environments" section.

That procedure is error-prone in a way that costs real money and real data. The steps are
ordered wrongly for safety — the access token is destroyed before it is used, so a mistake in
the shell step leaves an Item that no longer exists in the application but is still live at
Plaid, still counted against the maintainer's Plaid account, and now unreachable because the
only copy of its token is gone. Getting the database steps out of order instead produces a
foreign key error partway through, leaving half-deleted state. And a hand-written
`DELETE ... WHERE item_id=...` against a financial database is one typo away from removing the
wrong Item.

This feature replaces the whole procedure with a single action in the UI, performed in the
safe order, that either completes fully or changes nothing.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Remove a Plaid Item from the UI (Priority: P1)

The maintainer opens the Plaid Update page, finds the Item they no longer want in the Plaid
Items table, and chooses to delete it. Before anything happens they are shown what deleting it
will do — which institution it is, which of their Accounts will stop being linked to Plaid,
and that the action cannot be undone — and must confirm. On confirming, the Item and its
Plaid Accounts are gone from the application and the table no longer lists it.

**Why this priority**: This is the issue. Everything else in this feature exists to make this
action safe; without it the maintainer is still editing a financial database by hand.

**Independent Test**: With two Plaid Items present, delete one from the page and confirm it
disappears from the Plaid Items table while the other Item, its Plaid Accounts and its links
are untouched.

**Acceptance Scenarios**:

1. **Given** the Plaid Update page listing Plaid Items, **When** the maintainer views the
   Plaid Items table, **Then** each Item row offers a clearly labelled action to delete that
   Item, distinguishable from the existing per-row actions.
2. **Given** the maintainer chooses to delete an Item, **When** the confirmation is presented,
   **Then** it identifies the Item being deleted, names every Account that will be unlinked
   from Plaid as a result, states that the Item will also be removed at Plaid, and states that
   the action cannot be undone.
3. **Given** the confirmation is presented, **When** the maintainer declines it, **Then**
   nothing is deleted, nothing is unlinked, no request is sent to Plaid, and the page is
   unchanged.
4. **Given** the confirmation is presented, **When** the maintainer confirms it, **Then** the
   Item and all of its Plaid Accounts are removed from the application and the Plaid Items
   table no longer shows that Item.
5. **Given** two or more Plaid Items exist, **When** one is deleted, **Then** every other Item,
   its Plaid Accounts, and the Accounts linked to them are entirely unaffected.
6. **Given** an Item whose Plaid Accounts are not linked to any Account, **When** it is
   deleted, **Then** the deletion succeeds with no Account changes and no error.

---

### User Story 2 - The connection is severed at Plaid, not just locally (Priority: P1)

Deleting an Item tells Plaid to remove it. The stored credentials stop being valid, the
institution connection is closed, and the Item stops counting against the maintainer's Plaid
account — without the maintainer ever having to open a shell or handle an access token.

**Why this priority**: A local-only delete is worse than no delete. It silently converts a
manageable Item into an orphan at Plaid that the maintainer can no longer see, no longer
remove, and may continue to be billed for, because the application has just destroyed the only
copy of its access token.

**Independent Test**: Delete an Item and confirm the application asked Plaid to remove that
Item, using that Item's access token, before removing anything locally.

**Acceptance Scenarios**:

1. **Given** an Item being deleted, **When** the deletion runs, **Then** the application
   requests that Plaid remove that Item, and does so before the Item's stored access token is
   discarded.
2. **Given** Plaid confirms the Item was removed, **When** the deletion continues, **Then** the
   Item and its Plaid Accounts are removed from the application.
3. **Given** an Item that Plaid reports does not exist, or whose stored credentials Plaid
   reports as no longer valid — an Item already removed at Plaid, or one whose access token
   has been revoked — **When** the maintainer deletes it, **Then** the deletion completes
   locally rather than leaving the maintainer with an Item they can never remove.
4. **Given** an Item has been deleted, **When** the maintainer next updates transactions or
   refreshes Item information from Plaid, **Then** the deleted Item is not contacted and its
   absence causes no error.

---

### User Story 3 - Accounts survive the deletion with their history intact (Priority: P2)

An Account that was linked to the deleted Item is no longer linked to Plaid, but is otherwise
exactly as it was: same name, same settings, same balance, same transactions and downloaded
statements. The maintainer can link it to a different Plaid Item later, or leave it manual.

**Why this priority**: The maintainer's financial history is the point of the application.
Deleting a connection must never delete what came through it. This is separable from User
Story 1 — the deletion can be built and observed first — but the feature is not safe to ship
without it.

**Independent Test**: Note an Account's data and its Plaid link, delete the Item it is linked
to, and confirm the Account still exists with all of its data and is now simply not linked to
Plaid.

**Acceptance Scenarios**:

1. **Given** an Account linked to one of the deleted Item's Plaid Accounts, **When** the Item
   is deleted, **Then** the Account still exists, is no longer linked to any Plaid Account, and
   is presented exactly as an Account that was never linked to Plaid.
2. **Given** an Account linked to the deleted Item and carrying downloaded transactions,
   statements, balances and reconciliations, **When** the Item is deleted, **Then** none of
   that data is removed or altered.
3. **Given** an Item several of whose Plaid Accounts are linked to different Accounts, **When**
   the Item is deleted, **Then** every one of those Accounts is unlinked, and no Account linked
   to any other Item is touched.
4. **Given** an Account unlinked by a deletion, **When** the maintainer edits that Account,
   **Then** they can link it to a Plaid Account of any remaining Item exactly as before.

---

### User Story 4 - A deletion that cannot complete changes nothing (Priority: P2)

If the Item cannot be removed at Plaid — the service is unreachable, credentials are not
configured, Plaid rejects the request — the maintainer is told what went wrong and nothing has
changed. Their Item, its Plaid Accounts and their Account links are all still there, and they
can try again.

**Why this priority**: The failure mode this feature exists to prevent is partial deletion. An
all-or-nothing guarantee is what makes the UI action safer than the manual procedure, not just
more convenient.

**Independent Test**: Make the removal request to Plaid fail, attempt a deletion, and confirm
the error is reported and that the Item, its Plaid Accounts and every Account link are exactly
as they were.

**Acceptance Scenarios**:

1. **Given** Plaid rejects or cannot service the removal request, **When** the maintainer
   deletes an Item, **Then** an error identifying the failure is presented, and the Item, its
   Plaid Accounts and all Account links remain unchanged.
2. **Given** a deletion that fails, **When** the maintainer reloads the Plaid Update page,
   **Then** the Item is still listed, with the same accounts and the same linked Accounts as
   before the attempt.
3. **Given** a deletion is requested for an Item that no longer exists in the application —
   already deleted from another browser tab, for example — **When** it is processed, **Then**
   a clear message says so and no other data is affected.
4. **Given** a failed deletion, **When** the maintainer retries after the cause is resolved,
   **Then** the deletion succeeds normally.

---

### Edge Cases

- **The Item has no Plaid Accounts at all** (linking failed partway, or every account was
  removed by a refresh): the Item is still deletable, and deleting it is not an error.
- **The Item's Plaid Accounts are linked to no Accounts**: deletion proceeds with no Account
  changes; the confirmation says that nothing will be unlinked rather than showing an empty
  list with no explanation.
- **The same Item is deleted twice** (a double click, or two browser tabs): the second attempt
  reports that the Item is no longer present rather than failing obscurely, and does not remove
  or corrupt anything else.
- **Plaid reports the Item as already removed or its credentials as invalid**: treated as the
  removal having succeeded, so the maintainer is never left holding an undeletable Item
  (User Story 2, scenario 3).
- **Plaid credentials are not configured in this installation**: the deletion is refused with
  an explanation and nothing is changed, exactly as any other failure to reach Plaid.
- **An Account is linked to a Plaid Account of the Item being deleted while that Account is
  also mid-reconciliation or mid-edit elsewhere**: unlinking only clears the Plaid association;
  no other Account field is written, so nothing else can be clobbered.
- **Deleting every Item**: the Plaid Items table is left empty and the page still renders,
  with the link/add action still available.
- **A deleted Item's already-downloaded transactions**: they belong to the Account, not to the
  Item, and are untouched. Deleting an Item stops future downloads for those Accounts; it does
  not erase past ones.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Plaid Items table on the Plaid Update page MUST offer, for each listed Item, a
  clearly labelled action to delete that Item.
- **FR-002**: The system MUST require an explicit confirmation from the maintainer before any
  part of a deletion is performed.
- **FR-003**: The confirmation MUST identify the Item to be deleted, list every Account that
  will be unlinked from Plaid by the deletion (or state that there are none), state that the
  Item will also be removed at Plaid, and state that the action cannot be undone.
- **FR-004**: Declining the confirmation MUST leave all data unchanged and MUST NOT contact
  Plaid.
- **FR-005**: On confirmation, the system MUST request that Plaid remove the Item, and MUST do
  so while the Item's stored access token is still available — that is, before any local data is
  deleted.
- **FR-006**: The system MUST treat a Plaid response indicating that the Item does not exist, or
  that its stored credentials are no longer valid, as a successful removal and continue with the
  local deletion.
- **FR-007**: If the removal request to Plaid fails for any other reason, the system MUST abort
  the deletion, leave the Item, its Plaid Accounts and all Account links unchanged, and report
  the failure to the maintainer in terms that identify what went wrong.
- **FR-008**: After a successful removal at Plaid, the system MUST clear the Plaid association
  of every Account linked to any of that Item's Plaid Accounts, then remove that Item's Plaid
  Accounts, then remove the Item itself.
- **FR-009**: Unlinking an Account MUST change nothing about that Account other than its Plaid
  association. Its transactions, downloaded statements, balances, reconciliations and settings
  MUST be preserved.
- **FR-010**: A deletion MUST be all-or-nothing: either the Item, its Plaid Accounts and the
  affected Account links are all updated, or none of them are. The system MUST NOT leave an Item
  partially deleted.
- **FR-011**: Deleting one Item MUST NOT affect any other Item, its Plaid Accounts, or the
  Accounts linked to them.
- **FR-012**: After a successful deletion, the Plaid Update page MUST reflect the new state
  without the maintainer having to take any further action to refresh it.
- **FR-013**: A request to delete an Item that is not present MUST be reported clearly and MUST
  NOT alter any data.
- **FR-014**: The system MUST NOT display an Item's access token anywhere in the UI, in a
  confirmation, or in an error message produced by this feature.
- **FR-015**: An Account unlinked by a deletion MUST remain eligible to be linked to a Plaid
  Account of any remaining Item through the existing account-editing flow.
- **FR-016**: The documentation MUST describe deleting an Item through the UI, and the existing
  documented manual procedures that exist only because no UI action was available MUST be
  updated to point at it.

### Key Entities

- **Plaid Item**: one linked financial institution connection, identified by its Plaid Item ID
  and holding the access token used to talk to Plaid about it. Owns zero or more Plaid Accounts.
  This feature makes it removable.
- **Plaid Account**: one account at the institution behind a Plaid Item, as Plaid reports it.
  Belongs to exactly one Item and is removed with it. May be linked to at most one Account.
- **Account**: one of the maintainer's accounts in this application, holding its own
  transactions, balances and history. May reference one Plaid Account. This feature only ever
  clears that reference; it never removes an Account or any of its data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The maintainer can remove a Plaid Item completely — locally and at Plaid — from
  the Plaid Update page alone, without running SQL, opening a shell, or handling an access
  token.
- **SC-002**: Every documented manual step in the issue's procedure (six steps across a database
  client, a container shell and the UI) is replaced by one confirmed action in the UI.
- **SC-003**: After deleting an Item, no trace of it or its Plaid Accounts remains in the
  application, and every Account that was linked to it still exists with all of its
  transactions, balances and reconciliations intact.
- **SC-004**: An Item deleted through the UI is also removed at Plaid, so it stops counting
  against the maintainer's Plaid account; this holds without the maintainer performing any
  additional step.
- **SC-005**: When a deletion cannot complete, inspecting the data afterwards shows it exactly
  as it was before the attempt — no Item, Plaid Account or Account link partially removed — and
  the maintainer has been told why.
- **SC-006**: Deleting one Item out of several leaves the others fully functional: a subsequent
  transaction update for the remaining Items succeeds and reports no failures.
- **SC-007**: An Account unlinked by a deletion can be re-linked to a different Plaid Item
  through the existing account form with no intermediate repair step.

## Assumptions

- **The Plaid Update page is the right and only home for this action.** That page already
  carries the Plaid Items table and every other per-Item action ("Update / Fix Item",
  "Refresh"), so it is where a maintainer manages Items. No delete affordance is added to the
  Accounts pages or anywhere else.
- **Removing the Item at Plaid is part of deleting it, not a separate opt-in.** The issue's
  procedure does both, and the reason the manual procedure is dangerous is precisely that the
  two halves can come apart. This feature does not offer a "delete locally only" option.
- **Plaid is asked first, and a failure there stops everything.** This inverts the order in the
  issue's manual procedure, which deletes the database rows before using the access token. Doing
  it the other way round is what makes an all-or-nothing guarantee possible, and means a
  transient Plaid outage costs the maintainer a retry rather than an unreachable Item.
- **"Already gone at Plaid" counts as success.** Otherwise an Item whose token was revoked, or
  which was removed at Plaid through some other route, could never be cleared from the
  application through the UI — the exact dead end this feature exists to remove. The existing
  documented SQL remains available as a last resort for anything this cannot reach.
- **Accounts are unlinked, never deleted.** The issue's procedure says to set the Plaid
  association of affected Accounts to "none", and this preserves that: an Account is the
  maintainer's record, not Plaid's.
- **Confirmation happens in the page, in the style the application already uses.** The
  application's existing modal pattern is used rather than a browser-native dialog, so the
  confirmation can name the affected Accounts and can be exercised by the acceptance suite.
- **Deletion is not undoable and no soft-delete is introduced.** Other "removals" in this
  application are deactivations (Accounts, Budgets, Projects, Vehicles) because their history
  matters. A Plaid Item carries no history of its own — everything downloaded through it belongs
  to the Account — and it cannot be soft-deleted anyway, because removing it at Plaid is
  irreversible from this application's side. Re-linking the institution is the undo.
- **No schema change is expected.** Deleting an Item is expressible with the existing tables and
  relationships; the feature adds behaviour, not storage. Should the implementation find a
  schema change unavoidable, it ships with a reversible migration as the constitution requires.
- **Existing per-Item actions are unchanged.** "Update / Fix Item", "Refresh", "Update Item
  Information from Plaid", the Check All/Uncheck All selection and the transaction update flow
  all keep working exactly as they do now.
- **Bulk deletion is out of scope.** The issue asks to delete *an* Item. Deleting several at once
  (the "Changing Plaid Environments" case) is served by repeating the action, and a multi-select
  destructive operation raises its own confirmation-design questions.
