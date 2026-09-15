# Feature Specification: Plaid Item Last Successful Update Time

**Feature Branch**: `robot-army/issue-268-plaid-show-last-successful-update-time`

**Created**: 2026-09-15

**Status**: Draft

**Input**: GitHub issue [#268](https://github.com/jantman/biweeklybudget/issues/268) — "Plaid - show last_successful_update time"

## Context

Transactions arrive in this application from Plaid, which in turn pulls them from each
financial institution on its own schedule. There are therefore two distinct "when was this
last updated?" questions, and today the application can only answer one of them:

- **When did *we* last ask Plaid for this Item's transactions?** The Plaid Items table on
  the Plaid Update page answers this in its "Last Polled" column.
- **When did *Plaid* last successfully pull this Item's transactions from the
  institution?** Nothing in the UI answers this.

The second question is the one that matters when transactions stop appearing. An Item whose
bank login has silently degraded keeps answering our requests successfully — we poll it,
Plaid returns the transactions it already has, and "Last Polled" says "a minute ago" — while
Plaid itself has not managed to reach the institution for days or weeks. From the UI, that
Item is indistinguishable from a healthy one.

Plaid reports exactly this: every Item status response carries the time transactions were
last successfully refreshed for that Item. The application already retrieves it on every
update and writes it to the log, then discards it. The maintainer would have to read server
logs to find it, which in practice means nobody ever does.

This feature stores that timestamp with the Plaid Item and shows it in the UI beside the
existing "Last Polled" time, so a stale Item is visible at a glance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See when Plaid last refreshed each Item (Priority: P1)

The maintainer opens the Plaid Update page. The Plaid Items table shows, for each Item,
both when the application last polled it and when Plaid itself last successfully refreshed
that Item's transactions. An Item whose institution connection has gone stale stands out
because its Plaid-side refresh time is days or weeks old while its poll time is recent.

**Why this priority**: This is the whole of the issue — the value is in seeing the time, and
seeing it is what turns a silent failure into a visible one.

**Independent Test**: With Plaid Items in the database carrying known last-successful-update
times (including one with none recorded), load the Plaid Update page and confirm each Item's
row shows the expected time in a column distinct from "Last Polled".

**Acceptance Scenarios**:

1. **Given** a Plaid Item whose last successful update time has been recorded, **When** the
   maintainer views the Plaid Items table on the Plaid Update page, **Then** that Item's row
   shows the recorded time in a dedicated column, formatted the same relative way as the
   existing "Last Polled" column ("2 hours ago").
2. **Given** a Plaid Item that has never had a last successful update time recorded — for
   example one added before this feature existed and not yet refreshed — **When** the
   maintainer views the Plaid Items table, **Then** that Item's row shows an unambiguous
   placeholder rather than a blank cell or an error.
3. **Given** two Plaid Items, one refreshed by Plaid minutes ago and one not refreshed for
   weeks, **When** the maintainer views the Plaid Items table, **Then** the two times are
   distinguishable from each other and each is distinguishable from that Item's poll time.

---

### User Story 2 - The time is recorded whenever the application talks to Plaid about an Item (Priority: P1)

Whenever the application asks Plaid about an Item — either as part of downloading
transactions, or when the maintainer explicitly refreshes Item information — the
last-successful-update time Plaid reports is stored with that Item, replacing whatever was
stored before.

**Why this priority**: Without this, the column in User Story 1 has nothing to show. The two
stories are separable — the display can be built and tested against stored data — but
neither is useful alone.

**Independent Test**: Run a Plaid transaction update for an Item where Plaid reports a known
last-successful-update time, then confirm that time is stored against the Item. Repeat using
the "Update Item Information from Plaid" action.

**Acceptance Scenarios**:

1. **Given** a Plaid Item and a Plaid response reporting a last successful transaction
   update time, **When** the application downloads transactions for that Item, **Then** the
   reported time is stored against that Item and appears in the UI.
2. **Given** a Plaid Item with a previously stored last successful update time, **When** a
   later update reports a newer time, **Then** the stored time is replaced by the newer one.
3. **Given** a Plaid Item, **When** the maintainer uses the "Update Item Information from
   Plaid" action, **Then** the last successful update time Plaid reports for that Item is
   stored, without requiring a transaction download.
4. **Given** a Plaid Item for which Plaid reports no last successful update time — an Item
   newly linked, or one Plaid has never managed to refresh — **When** the application
   updates that Item, **Then** no time is recorded for it and the UI shows the same
   placeholder as for an Item that has never been updated, with no error.

---

### User Story 3 - Existing Items keep working across the upgrade (Priority: P2)

A maintainer upgrading an existing installation finds their Plaid Items intact, with the new
time simply not yet known for any of them, and populated for each Item as it is next
updated. Downgrading to the previous version is equally uneventful.

**Why this priority**: Required for the change to be safe to ship, but it delivers no new
capability on its own.

**Independent Test**: Apply the upgrade to a database holding Plaid Items, confirm the Items
and their existing data survive and the new time is empty; apply the downgrade and confirm
the database returns to its previous shape.

**Acceptance Scenarios**:

1. **Given** a database from the previous version holding Plaid Items, **When** it is
   upgraded, **Then** every Item retains its existing data and has no last successful update
   time recorded.
2. **Given** an upgraded database, **When** it is downgraded to the previous version,
   **Then** the schema matches the previous version and the remaining Item data is intact.

---

### Edge Cases

- **Plaid reports no time for an Item** (a newly linked Item, or one Plaid has never
  successfully refreshed): nothing is recorded and the UI shows its "never recorded"
  placeholder. This is not an error condition and must not be presented as one.
- **An update fails partway through**: if the application never gets a usable Item status
  from Plaid, the previously stored time is left untouched rather than being cleared — a
  stale-but-real time is more useful than no time, and a failed poll says nothing about when
  Plaid last succeeded.
- **The stored time is older than the poll time**, which is the normal case: the display
  must not imply the two are the same measurement or that the older one is wrong.
- **The stored time is in the future or far in the past** relative to the viewer's clock:
  it is displayed as reported, with no special-casing.
- **An Item exists with no accounts mapped, or with a failing login**: the time is still
  recorded and displayed for it, because those are exactly the Items whose staleness the
  maintainer needs to see.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each Plaid Item MUST be able to carry the time at which Plaid last successfully
  updated that Item's transactions, as reported by Plaid, or no time at all if Plaid has not
  reported one.
- **FR-002**: The system MUST record that time for an Item whenever it downloads transactions
  for that Item, replacing any previously recorded value.
- **FR-003**: The system MUST record that time for an Item whenever the maintainer refreshes
  Item information from Plaid, replacing any previously recorded value.
- **FR-004**: When Plaid reports no such time for an Item, the system MUST record no time for
  it, and MUST NOT treat this as an error or prevent the rest of that update from completing.
- **FR-005**: When the system cannot obtain an Item status from Plaid, it MUST leave any
  previously recorded time for that Item unchanged.
- **FR-006**: The Plaid Items table in the UI MUST show each Item's recorded time in its own
  labelled column, distinct from and alongside the existing "Last Polled" column, so the two
  cannot be confused.
- **FR-007**: The recorded time MUST be displayed in the same relative, human-readable form
  used by the existing "Last Polled" column, so the two can be compared at a glance.
- **FR-008**: An Item with no recorded time MUST display an unambiguous placeholder in that
  column rather than a blank cell, a raw empty value, or an error.
- **FR-009**: Recorded times MUST be stored and compared unambiguously with respect to time
  zone, consistent with the other timestamps the application stores.
- **FR-010**: Upgrading an existing installation MUST preserve all existing Plaid Item data
  and MUST NOT require the maintainer to re-link any Item; downgrading MUST return the
  database to its previous shape.

### Key Entities

- **Plaid Item**: a linked financial institution connection. Already carries its Plaid
  identifier, institution name and ID, access token, and the time the application last polled
  it. Gains one attribute: the time Plaid last successfully updated this Item's transactions,
  which may be absent.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From the Plaid Update page alone, and without consulting any log file, the
  maintainer can tell for every Plaid Item when Plaid last successfully refreshed its
  transactions.
- **SC-002**: Given a set of Items of which one has not been refreshed by Plaid for weeks
  while all have been polled recently, the maintainer can identify the stale Item from a
  single view of the page.
- **SC-003**: After one transaction update or one Item-information refresh, every Item for
  which Plaid reports a time displays that time; no additional maintainer action is needed to
  populate it.
- **SC-004**: An existing installation upgrades and downgrades with no data loss and no
  manual steps beyond the migration itself.
- **SC-005**: Items for which Plaid reports no time display a clear placeholder and are not
  reported as failures, in the UI or in the update's result.

## Assumptions

- **Only the transactions last-successful-update time is in scope.** Plaid also reports a
  last-*failed*-update time, and reports status for products other than transactions. The
  issue asks for the last successful transactions update, and only that is stored and shown.
  Surfacing failure times is a separate change.
- **The existing "Last Polled" column stays exactly as it is.** It answers a different
  question and remains useful; the new time is added beside it rather than replacing it.
- **A single stored time per Item is sufficient.** No history of past values is kept — the
  most recent reading replaces the previous one. History would be a larger feature with its
  own storage and UI questions, and the issue does not ask for it.
- **The Plaid Update page is the right and only place to show this.** That page already
  carries the Plaid Items table and the "Last Polled" column, so it is where a maintainer
  looks for Item health. Adding the time to other pages is out of scope.
- **Plaid's reported time is taken at face value.** The application does not attempt to
  validate it against its own clock, correct it, or infer a time when Plaid reports none.
- **Existing installations are upgraded by the project's normal database migration.** No
  backfill of the new time is possible or attempted, because the value can only come from
  Plaid; Items acquire it on their next update.
