# Feature Specification: Plaid Update Check All / Uncheck All

**Feature Branch**: `robot-army/issue-262-plaid-update-needs-check-all-uncheck`

**Created**: 2026-09-13

**Status**: Draft

**Input**: User description: "jantman/biweeklybudget issue #262 — plaid-update needs check all / uncheck all links"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Uncheck all, then pick a few (Priority: P1)

On the Plaid Update page, every Plaid Item in the "Plaid Update Transactions" panel
starts out checked. When the operator wants to update only one or two institutions
(for example, to retry one that failed), they currently have to uncheck every other
item by hand. With an "Uncheck All" link they clear every item in one click, then check
only the ones they want and submit.

**Why this priority**: This is the common case the issue is about: selecting a small
subset out of many items. It is useful on its own even without "Check All".

**Independent Test**: Load the Plaid Update page with two or more Plaid Items, click
"Uncheck All", and confirm every item's checkbox is cleared; check one and submit, and
confirm only that item is updated.

**Acceptance Scenarios**:

1. **Given** the Plaid Update page with all items checked, **When** the operator clicks
   "Uncheck All", **Then** every item's checkbox in the update panel is unchecked.
2. **Given** some items checked and some not, **When** the operator clicks "Uncheck
   All", **Then** every item's checkbox is unchecked.
3. **Given** all items unchecked after "Uncheck All", **When** the operator checks one
   item and clicks "Update Transactions", **Then** only that item is updated.

---

### User Story 2 - Check all again (Priority: P2)

After unchecking some or all items, the operator wants to go back to updating every
institution. A "Check All" link checks every item in one click, without reloading the
page.

**Why this priority**: Completes the pair; the same state is also reachable by
reloading the page, so it is less critical than "Uncheck All".

**Independent Test**: Load the page, uncheck some items, click "Check All", and confirm
every item's checkbox is checked.

**Acceptance Scenarios**:

1. **Given** some or all items unchecked, **When** the operator clicks "Check All",
   **Then** every item's checkbox in the update panel is checked.
2. **Given** all items already checked, **When** the operator clicks "Check All",
   **Then** every item stays checked.

---

### Edge Cases

- No Plaid Items configured: the links do nothing and cause no error.
- Clicking either link does not submit the form, start an update, reload the page, or
  change the page's scroll position.
- Only the item checkboxes in the "Plaid Update Transactions" panel are affected; no
  other control on the page changes.
- Submitting with every item unchecked behaves exactly as it does today when the
  operator unchecks every item by hand.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The "Plaid Update Transactions" panel on the Plaid Update page MUST offer
  a "Check All" link and an "Uncheck All" link, placed with the item checkboxes.
- **FR-002**: Activating "Check All" MUST check every Plaid Item checkbox in that panel.
- **FR-003**: Activating "Uncheck All" MUST uncheck every Plaid Item checkbox in that
  panel.
- **FR-004**: Activating either link MUST NOT submit the form, trigger a Plaid update,
  navigate away, or reload the page.
- **FR-005**: After either link is used, the operator MUST still be able to change
  individual checkboxes, and submitting MUST update exactly the items that are checked
  at submit time.
- **FR-006**: The initial state of the page (every item checked) and the behaviour of
  the "Update Transactions" button MUST be unchanged.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Selecting exactly one Plaid Item out of N takes at most 2 clicks (Uncheck
  All, then the item), regardless of N; today it takes N-1.
- **SC-002**: Returning to all items selected takes 1 click, with no page reload.
- **SC-003**: Using either link never starts a Plaid update; updates start only from the
  "Update Transactions" button.

## Assumptions

- "Links" in the issue means clickable controls styled as links, matching the existing
  "Update / Fix Item" and "Refresh" links on the same page.
- The links apply only to the "Plaid Update Transactions" panel, which is the only
  place on the page with item checkboxes; the "Plaid Items" panel is unchanged.
- The checkbox selection is not saved; reloading the page checks every item again, as
  it does today.
- No change to the `/plaid-update` endpoint, its parameters, or its response formats is
  needed.
