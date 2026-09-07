# Feature Specification: Index Page Account Balances Chart — History Limiting

**Feature Branch**: `robot-army/issue-279-fix-index-page-chart-when-lots-of-data`

**Created**: 2026-09-07

**Status**: Draft

**Input**: GitHub issue #279 — "Fix index page chart when lots of data"

> With lots of historical data (I currently have 5 years of daily balances), the "Account
> Balances" chart on the index page is taking an extremely long time to load and is almost
> illegible. This chart should be changed to either limit the amount of historical data (make
> that configurable) or else just provide a summary of the data (i.e. only show every N data
> points).
>
> It's possible that if we do #215 and use a more advanced chart library, we could default to
> only showing the last N data points (or days/months/years) and then allow the user to "zoom
> out" in the UI to show more data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Index page loads quickly with years of balance history (Priority: P1)

The operator has years of daily account balance records. When they open the index page, the
Account Balances chart shows a recent, readable slice of history — not every balance ever
recorded — and the page becomes usable in a few seconds rather than tens of seconds.

**Why this priority**: This is the reported defect. Without it the index page — the
application's landing page and most-visited screen — is effectively unusable for a
long-running installation. Everything else in this feature is refinement on top of it.

**Independent Test**: Load the index page against a database seeded with several years of
daily balances for several accounts and confirm the chart renders, that it plots only the
default recent window, and that the data request returns a bounded number of points
regardless of how much history exists.

**Acceptance Scenarios**:

1. **Given** the database holds five years of daily balances for every account, **When** the
   operator opens the index page, **Then** the Account Balances chart displays only the most
   recent default window of history and renders without a perceptible stall.
2. **Given** the database holds five years of daily balances, **When** the chart's data is
   requested, **Then** the response contains no more than the configured maximum number of
   data points, no matter how long the selected window is.
3. **Given** the database holds only two weeks of balances, **When** the operator opens the
   index page, **Then** every available balance point is plotted, unchanged from today's
   behaviour.

---

### User Story 2 - Operator chooses how much history to see (Priority: P2)

From the index page, the operator can widen or narrow the chart's time window — for example
from the default recent window out to one year, five years, or all recorded history — without
leaving the page, and can narrow it back down again.

**Why this priority**: The issue explicitly asks for the ability to "zoom out" to see more
data. Limiting history without any way to see the rest would remove a capability the operator
has today. It is P2 because a fast, readable default chart already delivers the core value.

**Independent Test**: With multi-year data loaded, select each offered range from the index
page and confirm the chart redraws to cover that span, that the earliest plotted date matches
the chosen span, and that the point count stays bounded.

**Acceptance Scenarios**:

1. **Given** the index page is open showing the default window, **When** the operator selects
   a longer range, **Then** the chart redraws covering that longer span without a full page
   reload.
2. **Given** the operator has selected "all history", **When** the chart redraws, **Then** it
   spans from the earliest recorded balance to the most recent, still within the maximum
   point count.
3. **Given** the operator has selected a longer range, **When** they then select a shorter
   one, **Then** the chart redraws to the shorter span.
4. **Given** the operator selects a range, **When** the chart is showing that range, **Then**
   the page makes it visually clear which range is currently selected.

---

### User Story 3 - Operator configures the default window (Priority: P3)

The operator can change how much history the chart shows by default, and the maximum number
of points it will plot, through the application's existing configuration mechanism, without
editing code.

**Why this priority**: The issue asks for the limit to be "configurable". Sensible defaults
serve most of the need, so this is valuable but not the core fix.

**Independent Test**: Set the configuration values to non-default numbers, load the index
page, and confirm the chart's default span and its point count follow the configured values.

**Acceptance Scenarios**:

1. **Given** the default-window setting is changed to a different number of days, **When** the
   index page is opened, **Then** the chart's initial span matches the configured number of
   days.
2. **Given** the maximum-points setting is changed, **When** chart data is requested for a
   long span, **Then** the number of plotted points respects the new maximum.
3. **Given** neither setting is present in the operator's configuration, **When** the index
   page is opened, **Then** documented defaults are used and nothing fails.

---

### Edge Cases

- **No balance records at all**: the chart area renders without error and communicates that
  there is nothing to plot, rather than showing a broken or empty widget with no explanation.
- **Fewer records than the requested window**: the chart plots what exists, starting at the
  earliest record, with no padding or fabricated points.
- **Fewer records than the maximum point count**: no thinning is applied; every point is
  plotted exactly as today.
- **An account that has no balance recorded within the selected window** but has older
  records: its line is still drawn, carrying forward its most recent known balance from before
  the window, so it does not appear to have vanished or dropped to zero.
- **An account created part-way through the window**: its line begins where its data begins;
  it is not back-filled with zeros for dates before it existed.
- **A balance record whose ledger value is absent**: treated as it is today, so this change
  introduces no new interpretation of missing values.
- **Requested range is invalid, unrecognised, negative, or absurdly large**: the request is
  handled predictably — falling back to the default window rather than erroring or attempting
  an unbounded query.
- **Thinning must not hide the present**: whatever thinning is applied, the most recent
  recorded balance point is always plotted, so the right-hand edge of the chart reflects
  current balances.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Account Balances chart MUST, by default, plot only balances within a bounded
  recent time window rather than all recorded history.
- **FR-002**: The number of days in that default window MUST be configurable through the
  application's existing settings mechanism, with a documented default that is applied when
  the operator has not set a value.
- **FR-003**: The chart's underlying data request MUST return no more than a configurable
  maximum number of dates, regardless of the span requested or the volume of stored history.
- **FR-004**: When a requested span contains more dates than that maximum, the data MUST be
  reduced by sampling at a regular interval across the span, preserving the shape of each
  account's balance history rather than truncating it.
- **FR-005**: The most recent available balance date within the requested span MUST always be
  included in the returned data, even when sampling would otherwise skip it.
- **FR-006**: The chart's data request MUST retrieve only the balance records it needs for the
  requested span from storage, rather than retrieving all records and discarding most of them.
- **FR-007**: Users MUST be able to select the chart's time span from the index page, from a
  set of offered ranges that includes at minimum the default window, one year, and all
  recorded history.
- **FR-008**: Selecting a different span MUST update the chart in place, without a full page
  reload and without navigating away from the index page.
- **FR-009**: The index page MUST visually indicate which span is currently displayed.
- **FR-010**: An unrecognised, malformed, or out-of-range span request MUST fall back to the
  default window rather than failing or returning unbounded data.
- **FR-011**: Each account's line MUST continue to carry forward its last known balance across
  dates where that account has no record, so lines stay continuous, as they do today.
- **FR-012**: When there are no balance records to plot, the chart area MUST show a clear
  "no data" indication rather than an error or an unexplained blank.
- **FR-013**: The behaviour of the chart for installations with small amounts of history MUST
  be unchanged: all points plotted, no thinning, no visible difference from today.
- **FR-014**: The new configuration settings MUST be documented alongside the project's other
  settings, and the change MUST be recorded in the changelog.

### Key Entities

- **Account balance record**: a recorded balance for one account as of one point in time. The
  set of these records over time is what the chart plots. This feature does not change how
  they are created, stored, or what they mean.
- **Chart time span**: the range of dates the chart currently covers, chosen by the operator
  from a set of offered ranges and defaulting to a configured recent window.
- **Chart data series**: one line per account, made up of the sampled dates within the span
  and that account's balance at each.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With five years of daily balances across ten accounts, the index page's chart
  becomes visible and readable within a few seconds, where today it stalls for tens of seconds.
- **SC-002**: The chart's data response contains at most the configured maximum number of
  dates — a bounded, predictable amount — for any requested span, including "all history".
- **SC-003**: The volume of stored history no longer affects how much data the index page
  transfers or draws for its default view: doubling the years of history stored leaves the
  default view's point count unchanged.
- **SC-004**: An operator can move from the default view to a full-history view and back
  entirely from the index page, in no more than one interaction each way.
- **SC-005**: An operator can change the default window and the maximum point count without
  editing application code, and the change takes effect on the next page load.
- **SC-006**: For an installation with less history than the default window, the chart is
  indistinguishable from the current behaviour.
- **SC-007**: The complete unit and acceptance suites pass, with new tests covering the
  windowing, the sampling, the fallback behaviour, and the range selection.

## Assumptions

- The existing chart library remains in use. Issue #215 (adopting a more advanced chart
  library) is a separate piece of work; this feature deliberately delivers the range-selection
  behaviour with the current stack rather than depending on that migration. The constitution's
  direction to follow the existing frontend stack rather than introducing a parallel one
  supports this.
- "Configurable" means the project's existing settings module mechanism, consistent with how
  every other operator-tunable value in the application is exposed. No new configuration
  system is introduced and no per-user preference storage is added.
- The default window is assumed to be the last year of history, and the maximum point count is
  assumed to be a value in the low hundreds — enough to keep a line chart smooth at typical
  screen widths while staying an order of magnitude below five years of daily points. The
  exact numbers are settled during planning; both are configurable, so neither is a one-way
  door.
- The offered ranges are assumed to be a small fixed set of spans (such as one month, three
  months, six months, one year, two years, five years, and all history) rather than free-form
  date entry. Arbitrary custom date ranges are out of scope.
- The selected range is not remembered between page loads; every visit starts at the
  configured default. Persisting the operator's last choice is out of scope.
- Sampling by a regular interval across the span is acceptable for this data. Account balances
  are slow-moving series, so a regularly sampled subset represents them faithfully; no
  statistical aggregation (averaging, min/max envelopes) is required.
- The application remains single-operator and localhost-only; no access control or
  multi-tenancy concerns arise from this change.
- No database schema change is required — this feature only changes how existing records are
  queried and presented — so no migration is expected.
