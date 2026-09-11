# Feature Specification: Plaid Update Reports Failure In Its Status Code

**Feature Branch**: `robot-army/issue-261-plaid-update-endpoint-needs-to-return`

**Created**: 2026-09-11

**Status**: Draft

**Input**: GitHub issue [#261](https://github.com/jantman/biweeklybudget/issues/261) — "/plaid-update endpoint needs to return non-200 if any failed"

## Context

The `/plaid-update` endpoint downloads transactions from Plaid for one or more Plaid
Items and reports a result for each. It is used both interactively from the browser and
unattended, for example from a scheduled `curl` job, where the documented plain-text and
JSON responses are the intended interface.

Today, when updating an Item fails (an expired login, a Plaid API error, or any other
error), the failure is recorded in that Item's result and the endpoint still answers
with HTTP 200 OK. A script or scheduler that checks the status code, which is the
conventional and often the only check (`curl --fail`, cron wrappers, monitoring), sees
success and never alerts anyone. Failed updates therefore go unnoticed until someone
reads the output, and transactions quietly stop arriving.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An unattended update that fails is detected (Priority: P1)

The maintainer runs a Plaid update for all Items from a scheduled job. One Item's bank
login has expired, so its update fails while the others succeed. The job sees a non-success
status code, treats the run as failed, and alerts the maintainer, who can read the response
body to see which Item failed and why.

**Why this priority**: This is the whole of the issue. Without it, automated updates fail
silently.

**Independent Test**: Request an update of several Items where at least one fails,
using each response format (plain text, JSON, and browser HTML). Confirm the status code
is not 200 and the body still lists every Item's result, including the failure.

**Acceptance Scenarios**:

1. **Given** an update of several Items in which exactly one fails, **When** the update is
   requested with `Accept: text/plain`, **Then** the response status is HTTP 500 and the
   body is the same human-readable summary as before, including the failed Item's error
   and the count of failed accounts.
2. **Given** the same partially failing update, **When** it is requested with
   `Accept: application/json`, **Then** the response status is HTTP 500 and the body is
   the same JSON list of per-Item results as before, with the failed Item's `success`
   set to false.
3. **Given** the same partially failing update, **When** it is requested from a browser
   (any other `Accept` value), **Then** the response status is HTTP 500 and the results
   page renders as before, showing the failed Item.
4. **Given** an update in which every Item fails, **When** it is requested in any of the
   three formats, **Then** the response status is HTTP 500 and the body reports every
   failure.

---

### User Story 2 - A fully successful update still reports success (Priority: P1)

The maintainer's scheduled update runs and every Item updates successfully. The job sees
HTTP 200 and does not alert.

**Why this priority**: Equally essential. An endpoint that reported failure on success
would train the maintainer to ignore its alerts, and the change would be worse than useless.

**Independent Test**: Request an update in which every Item succeeds, in each response
format, and confirm the status is HTTP 200 and the body is unchanged from today.

**Acceptance Scenarios**:

1. **Given** an update in which every Item succeeds, **When** it is requested in any of
   the three formats, **Then** the response status is HTTP 200 and the body is unchanged
   from current behaviour.

### Edge Cases

- **No Items to update** (for example `item_ids=ALL` with no Plaid Items configured):
  nothing failed, so the response is HTTP 200 with an empty result set, as today.
- **Missing `item_ids` on a POST**: unchanged, and still answered with HTTP 400.
- **A requested Item ID that does not exist**: out of scope. That request already fails
  with an HTTP 500 error before any results are produced, and this feature does not
  change it.
- **The form view** (GET with no `item_ids`): unaffected. No update happens, so the page
  is served with HTTP 200 as today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When at least one requested Plaid Item fails to update, the `/plaid-update`
  endpoint MUST respond with HTTP status 500 (Internal Server Error).
- **FR-002**: When every requested Plaid Item updates successfully, or no Items were
  updated, the endpoint MUST respond with HTTP status 200, as today.
- **FR-003**: FR-001 and FR-002 MUST apply identically to all three response formats
  (plain text, JSON, and browser HTML) and to both GET and POST requests.
- **FR-004**: The response body in every format MUST be unchanged by this feature. It
  still carries the complete per-Item results, including successful Items' counts and
  failed Items' errors, so the caller can tell which Items failed and why.
- **FR-005**: The endpoint documentation (the Plaid page's update API section and the HTTP
  API page's summary) MUST describe the status codes the endpoint returns.

### Key Entities

- **Plaid update result**: the existing per-Item outcome record (Item, success flag,
  counts of transactions added and updated, statement IDs, error). The status code is
  derived from these records' success flags. No new data is stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100% of update requests where one or more Items fail, a caller that
  only inspects the status code can tell the update did not fully succeed.
- **SC-002**: In 100% of update requests where all Items succeed, the status code
  reports success, so there are no false alarms.
- **SC-003**: For every request, the response body carries the same information it did
  before the change, so no caller loses detail about which Items failed.

## Assumptions

- **HTTP 500 is the failure status.** The issue asks only for "non-200". HTTP 500 is the
  generic "the server could not fully complete this request" status, and it is what
  `curl --fail`, monitoring tools, and scheduler wrappers already treat as failure. Other
  candidates were rejected. 207 Multi-Status is a 2xx, so it is not detected as a failure.
  502 Bad Gateway implies the fault is always upstream, but an update can fail for local
  reasons too, such as a database error.
- **Partial failure counts as failure.** A single failed Item makes the whole response
  non-200. The caller can distinguish partial from total failure by reading the body.
- **The browser view gets the same status.** A 500 status does not stop a browser from
  rendering the results page, and applying one rule to every format keeps the endpoint
  predictable. The interactive workflow is unchanged.
- **This is a behaviour change for API callers.** Any existing script that treats a
  non-200 as fatal and ignores the body will now see failures it previously missed.
  That is the intent of the issue, and it is recorded in the changelog.
