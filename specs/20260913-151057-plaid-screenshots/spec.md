# Feature Specification: Plaid Screenshots

**Feature Branch**: `robot-army/issue-264-add-screenshots-for-plaid`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description: "jantman/biweeklybudget issue #264 — "Add screenshots for Plaid" (labels: enhancement). Issue body: "Add screenshots for Plaid-related things""

## User Scenarios & Testing *(mandatory)*

The audience is someone reading the documentation to decide whether to use
biweeklybudget's Plaid support, or to learn how to use it. Today the Screenshots page
shows no Plaid screen, and the only screenshot of the Edit Account modal is cut off just
above its "Plaid Account" field.

### User Story 1 - See the Plaid Update page (Priority: P1)

A reader opens the Screenshots page and sees the Plaid Update page: the "Plaid Update
Transactions" table of Plaid Items to update (with its Check All / Uncheck All links and
Update Transactions button) and the "Plaid Items" table with each Item's institution,
accounts, last-polled time and its Update / Fix Item and Refresh actions, plus the Link
button that adds an Item.

**Why this priority**: This page is where all Plaid work starts (linking, updating,
fixing Items). One screenshot of it shows most of what the Plaid feature is.

**Independent Test**: Generate the screenshots and open the new Plaid Update image; both
tables are populated with the sample Plaid Items.

**Acceptance Scenarios**:

1. **Given** the sample data with its two Plaid Items, **When** the screenshots are
   generated, **Then** the Screenshots page has a "Plaid Update" entry whose image shows
   both Plaid Items in both tables.

---

### User Story 2 - See the result of a Plaid update (Priority: P2)

A reader sees what an update produces: a results table with, for each Item, the number
of transactions updated and added and any error, and a total row. The example includes
one Item that updated successfully and one that failed, so the reader sees how a
failure is reported.

**Why this priority**: It shows the outcome of the main Plaid workflow, including the
failure reporting added for issue #261. It depends on nothing but is less central than
the page that starts the workflow.

**Independent Test**: Generate the screenshots and open the new result image; it shows a
successful row, a failed row with its error, and a total row reporting one failure.

**Acceptance Scenarios**:

1. **Given** the sample Plaid Items, **When** the screenshots are generated, **Then** the
   Screenshots page has a "Plaid Update Result" entry whose image shows one Item with
   updated/added counts, one Item with an error message, and a total row that says
   "1 Failed".

---

### User Story 3 - See how an Account is linked to Plaid (Priority: P3)

A reader sees the Edit Account modal with its "Plaid Account" selector visible and set
to the Plaid account the Account is linked to, which is the step in the documented
linking process where a Plaid account is chosen.

**Why this priority**: It completes the picture of linking, but the selector is one field
in a modal already partly shown by the existing Account Details screenshot.

**Independent Test**: Generate the screenshots and open the new image; the "Plaid Account"
selector and its selected value are visible, not cut off.

**Acceptance Scenarios**:

1. **Given** a sample Account linked to a sample Plaid account, **When** the screenshots
   are generated, **Then** the Screenshots page has an entry whose image shows that
   Account's Edit Account modal with the "Plaid Account" selector showing the linked
   Plaid Item and account.

---

### Edge Cases

- The Plaid Link flow (connecting a new institution) runs in a window served by Plaid and
  needs real Plaid credentials; it cannot be captured from sample data and is out of scope.
- Screenshot generation runs in CI with no Plaid credentials and no Plaid network access.
  The update result must therefore come from fixed sample results, never a real update.
- The failed Item's error text is invented sample text. It must not look like, or
  contain, a real credential or token.
- Showing an update result must not add, change or remove data used by the screenshots
  that follow it.
- The Plaid Account selector is at the bottom of a long modal; the screenshot must show
  it even though it is below the modal's initially visible area.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The generated documentation screenshots MUST include the Plaid Update page,
  showing the sample Plaid Items in both of its tables.
- **FR-002**: The generated screenshots MUST include a Plaid Update result page showing at
  least one successful Item, at least one failed Item with its error, and the total row
  reporting the number of failures.
- **FR-003**: The generated screenshots MUST include the Edit Account modal of an Account
  linked to Plaid, with the "Plaid Account" selector and its selected value visible.
- **FR-004**: Each new screenshot MUST have a title and a one-sentence description on the
  Screenshots page, and a thumbnail linking to the full-size image, like the existing
  entries.
- **FR-005**: Generating the screenshots MUST NOT need Plaid credentials or contact Plaid.
- **FR-006**: Adding the Plaid screenshots MUST NOT change what any existing screenshot
  shows.
- **FR-007**: The Plaid documentation MUST point readers to the Plaid screenshots.
- **FR-008**: The new screenshots MUST be produced by the existing automated screenshot
  generation, with no manual steps, so they are regenerated with the others.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The Screenshots page gains exactly three Plaid entries (update page, update
  result, account linking), each with a thumbnail and full-size image.
- **SC-002**: A complete screenshot generation run finishes successfully with no Plaid
  credentials available, locally and in CI.
- **SC-003**: Every existing screenshot entry is still generated, with the same title,
  description and content as before.
- **SC-004**: A reader of the Plaid documentation reaches the Plaid screenshots in one
  click.

## Assumptions

- Screenshots and the generated Screenshots page are regenerated and committed as part of
  a release (constitution, Development Workflow step 7), as for the Cash Position and
  Spending Charts screenshots added by earlier features. This change adds the Plaid
  screenshots to the generator and verifies them with a full local run; it does not
  commit regenerated images.
- The sample data's two Plaid Items, their Plaid accounts, and the Accounts linked to
  them are adequate and are not changed.
- The existing Account Details screenshot stays as it is; the Plaid Account selector gets
  its own entry rather than replacing it.
- The update result shows plausible counts and an invented error for the failed Item.
  Only its appearance matters, not the result of a real update.
