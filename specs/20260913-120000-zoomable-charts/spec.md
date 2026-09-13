# Feature Specification: Zoomable, Pannable Charts

**Feature Branch**: `robot-army/issue-215-better-charts`

**Created**: 2026-09-13

**Status**: Complete

**Input**: GitHub issue [#215](https://github.com/jantman/biweeklybudget/issues/215) — "Better charts": "Consider replacing the charts (or maybe just setting options on them, if they support it) with ones that support zooming, panning, etc. (Bokeh?)"

## Context

The application draws five line charts over time:

| Page | Chart | Series |
|------|-------|--------|
| Index | Account Balances | one per account |
| Budgets | Spending By Budget, Per Pay Period | one per budget |
| Budgets | Spending By Budget, Per Calendar Month | one per budget |
| Fuel Log | Fuel Economy | one per vehicle |
| Fuel Log | Fuel Prices | one |

Each is a fixed picture of its whole date range. With years of history and a dozen or more
budgets or accounts, the lines are packed into a few pixels each: a single pay period or
month cannot be picked out, and one large series (a mortgage account, a rent budget) sets
the vertical scale so the rest are flattened near zero. Hovering shows values for one date
at a time, but there is no way to look closer at a stretch of time or to set one series
aside. The Index page's range buttons (#279) help for that one chart, and only in fixed
steps.

The issue asks for charts that can be zoomed and panned, "etc.". This feature gives all five
line charts the same set of controls for looking closer: zoom into a stretch of time, move
along it, return to the full view, and hide or show individual series.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Zoom into a stretch of time (Priority: P1)

The operator is looking at the Spending By Budget, Per Pay Period chart covering several
years. They want to see the last six months. They drag across the chart from the first
date to the last date they want. The chart redraws showing only that range, with its
date and value axes rescaled to fit it. The values in view fill the chart's height rather
than sitting in a thin band. They can zoom further in the same way. A control on the
chart returns it to the full view in one click.

**Why this priority**: This is what the issue asks for. It is also the most useful single
change: every other control here helps only once the operator is looking at a narrower range.

**Independent Test**: Open any of the five charts with data spanning more than a year.
Drag-select a range of a few months, check that only dates in that range are plotted and
that the value axis spans those dates' values. Then use the reset control and check the
original full view returns.

**Acceptance Scenarios**:

1. **Given** a chart showing its full date range, **When** the operator drag-selects a
   range of dates on it, **Then** the chart shows only that range, and its first and last
   plotted dates are within the selection.
2. **Given** a zoomed chart, **When** the operator looks at the value axis, **Then** it
   spans the values of the data in view (with a small margin), not those of the full range.
3. **Given** a zoomed chart, **When** the operator zooms again, **Then** it narrows further
   within the current view.
4. **Given** a zoomed chart, **When** the operator uses the reset control, **Then** the
   chart returns to exactly the view it opened with.
5. **Given** a chart at its full view, **When** the operator looks for the reset control,
   **Then** it is either absent or visibly inactive, since there is nothing to reset.
6. **Given** the operator scrolls the page with the mouse wheel or touchpad while the
   pointer is over a chart, **When** no modifier key is held, **Then** the page scrolls as
   normal and the chart does not zoom.

---

### User Story 2 - Move along a zoomed chart (Priority: P1)

Having zoomed into three months, the operator wants to see the three months before. They
pan the chart sideways (a mouse drag with a modifier key held) and the view slides along
the date axis, keeping its width. They can also zoom in and out around the pointer with
the mouse wheel while holding the modifier key.

**Why this priority**: Zooming without panning means resetting and re-selecting to see
the neighbouring stretch. The issue names panning explicitly.

**Independent Test**: Zoom a chart to a range, pan it, and check that the visible range
moves along the date axis and keeps its length. Zoom with modifier+wheel and check the
visible range narrows or widens.

**Acceptance Scenarios**:

1. **Given** a zoomed chart, **When** the operator pans it towards earlier dates, **Then**
   the first and last dates in view both move earlier and the span shown stays the same
   length.
2. **Given** a zoomed chart, **When** the operator pans past the first or last date of the
   data, **Then** the view stops at the edge of the data rather than showing empty space
   beyond it.
3. **Given** any chart, **When** the operator holds the modifier key and turns the mouse
   wheel over it, **Then** the chart zooms in or out on the date axis around the pointer.
4. **Given** a chart, **When** the operator looks at it, **Then** a short hint beside it
   says how to zoom, pan and reset, so the controls can be found without documentation.

---

### User Story 3 - Hide and show series (Priority: P2)

On the Spending By Budget charts, the operator wants to compare Groceries and Dining
without the Rent line setting the scale. Each chart has a legend naming every series in its
colour. Clicking a series in the legend hides that line and rescales the value axis to the
lines still shown. Clicking it again brings it back.

**Why this priority**: A series with values much larger than the rest makes the others
unreadable at any zoom level. This is the "etc." most worth having. The charts currently
have no legend at all; a series can only be identified by hovering over it.

**Independent Test**: On a chart with several series, click one in the legend, check its
line disappears and the value axis rescales to the others. Click it again and check the
chart returns to how it was.

**Acceptance Scenarios**:

1. **Given** a chart with several series, **When** the operator looks at it, **Then** a
   legend lists each series by name in the colour of its line.
2. **Given** that legend, **When** the operator clicks a series, **Then** its line is
   hidden, the legend shows it as hidden, and the value axis rescales to the series still
   shown.
3. **Given** a hidden series, **When** the operator clicks it again, **Then** its line
   returns.
4. **Given** hidden series and a zoomed view, **When** the operator resets the zoom,
   **Then** the date range resets and the hidden series stay hidden.
5. **Given** the operator has hidden series or zoomed, **When** the page is reloaded,
   **Then** every chart opens at its full view with every series shown.

---

### User Story 4 - The charts keep doing what they do now (Priority: P1)

Everything the charts do today still works: hovering a date shows each series' value for
that date, in the application's currency format where the values are money; the Index
page's range buttons still choose how much account history is loaded; the Fuel Log charts
still update when a fuel fill is added; each chart still fits the width of its panel when
the window is resized; and the Account Balances chart still shows its "no data" message
when there is nothing to plot.

**Why this priority**: Replacing how a chart is drawn must not take away anything the
operator already relies on.

**Independent Test**: Exercise each existing behaviour listed above on the new charts and
check it matches today's behaviour.

**Acceptance Scenarios**:

1. **Given** any chart, **When** the operator hovers a point, **Then** a tooltip shows its
   date and the value of each visible series on that date. Values on the Account Balances,
   Spending By Budget and Fuel Prices charts are formatted as currency.
2. **Given** the Index page, **When** the operator clicks a range button, **Then** the
   Account Balances chart loads that range of history, any zoom is cleared, and it is still
   one chart, not a second drawn over the first.
3. **Given** the Index page, **When** range buttons are clicked faster than their data
   arrives, **Then** the chart ends up showing the range of the last button clicked.
4. **Given** the Fuel Log page, **When** a fuel fill is added, **Then** both fuel charts
   redraw with the new data without a page reload.
5. **Given** any chart, **When** the window is resized, **Then** the chart redraws to the
   width of its panel.
6. **Given** no account balance data, **When** the Index page opens, **Then** the "no
   data" message shows in place of the chart.

### Edge Cases

- **Gaps in a series**: a budget with no spending in some periods, or a vehicle with no
  fills in a month, has no value on those dates. The line joins the dates on either side,
  as today. It does not drop to zero.
- **A single data point**, or a zoom narrow enough to contain one date: the chart shows
  that point and its value, without an error or a blank chart.
- **Zooming into a range with no data points** is not possible below the spacing of the
  data. The chart will not zoom in so far that no data points are in view.
- **Every series hidden**: the chart shows empty axes and the legend, from which series
  can be shown again; it does not break.
- **Many series** (a dozen or more budgets): each keeps a distinct colour, used for its
  line, legend entry and tooltip entry. The legend wraps rather than overflowing the panel.
- **Budget, account and vehicle names containing characters that have meaning in a web
  page** (such as `<` or `&`) are shown as the literal text in the legend and tooltips.
- **Negative values** (an overdrawn account, a credit card balance, net refunds in a
  spending period) are plotted below zero as today.
- **Touch devices**: the charts still display and show values on tap. Zooming and panning
  by touch is desirable but not required (see Assumptions).
- **Data reloaded while zoomed** (a range button, a new fuel fill): the chart shows the new
  data at its full view.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The five line charts listed in Context MUST support every interaction in
  FR-002 to FR-008, and all five MUST behave the same way.
- **FR-002**: The operator MUST be able to zoom a chart to a range of dates by
  drag-selecting it on the chart.
- **FR-003**: The operator MUST be able to zoom a chart in and out along the date axis with
  the mouse wheel or touchpad while holding a modifier key. Without the modifier key, wheel
  and touchpad scrolling MUST scroll the page as normal.
- **FR-004**: The operator MUST be able to pan a zoomed chart along the date axis by
  dragging with a modifier key held. Panning MUST stop at the first and last dates of the
  data.
- **FR-005**: When a chart's date range changes by zoom or pan, its value axis MUST rescale
  to the values of the visible series within the visible date range.
- **FR-006**: Each chart MUST have a reset control that returns it to its full view. The
  control MUST be absent or visibly inactive when the chart is already at its full view.
- **FR-007**: Each chart MUST have a legend listing each series by name in its colour.
  Clicking a legend entry MUST hide or show that series, and the value axis MUST rescale to
  the series shown.
- **FR-008**: Each chart MUST show a short hint describing how to zoom, pan and reset.
- **FR-009**: Hover tooltips MUST show the date and the value of each visible series at
  that date. Values that are money MUST be in the application's currency format, as now.
- **FR-010**: Zoom level, pan position and hidden series MUST NOT be saved. Every chart
  MUST open at its full view with all series shown.
- **FR-011**: The Index page range buttons (#279) MUST keep working as now, including
  ignoring responses for superseded clicks. Loading a new range MUST clear any zoom.
- **FR-012**: The Fuel Log charts MUST redraw with new data after a fuel fill is added,
  without a page reload.
- **FR-013**: Each chart MUST fit the width of its panel, including after a window resize.
- **FR-014**: The Account Balances chart MUST show its "no data" message when there is no
  data to plot.
- **FR-015**: Everything needed to draw the charts MUST be served by the application
  itself. The charts MUST work with no internet access, as the rest of the application does.
- **FR-016**: The data endpoints behind the charts MUST NOT change: same URLs, parameters
  and responses. No stored data changes.
- **FR-017**: The donut charts on the Spending Charts page (#214) MUST keep their current
  behaviour: slices, colours per budget, hover text, "no spending" message, and the budget
  checkboxes.
- **FR-018**: The chart controls MUST be documented with the application's other pages.

### Key Entities

- **Chart view**: for one chart on the open page, the date range in view and the set of
  hidden series. It exists only on the open page and starts at the full date range with
  every series shown. Nothing about it is stored.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a chart with three or more years of data, the operator can bring a single
  chosen month into view, filling the chart's width, in no more than two actions (one
  drag-select, or a drag-select and one pan).
- **SC-002**: From any zoomed or panned state, the operator can return to the full view in
  one click.
- **SC-003**: With the largest series hidden, the remaining series use the chart's full
  height: the value axis spans the remaining series' values rather than the hidden one's.
- **SC-004**: Every behaviour listed in User Story 4 works on all five charts as it did
  before the change.
- **SC-005**: Each chart responds to zoom, pan, reset and legend clicks within half a second
  with the largest data set the application's test data provides.
- **SC-006**: With the network disconnected from anything but the application, every chart
  still draws and every control still works.

## Assumptions

- **All five line charts, not one.** The issue says "the charts". Giving the operator
  different controls on different pages would be worse than the current consistency, so
  all five change together.
- **The donut charts are out of scope for zoom and pan.** A pie or donut has no axis to zoom
  along; its detail is already in the table beside it. Their behaviour must not change
  (FR-017). Whether they move to the same drawing library as the line charts is a planning
  decision, not a requirement.
- **Charts drawn in the browser, as now.** The issue mentions Bokeh as one option, with a
  question mark. Which library draws the charts is a planning decision. The requirements
  here are the behaviours the issue asks for and what must not regress.
- **The date axis is the one that zooms and pans.** Drag-select, wheel zoom and pan all act
  on dates. The value axis follows automatically (FR-005), which is what makes zooming
  useful here: zooming into a date range of a balances chart is pointless if the vertical
  scale still spans every balance ever held. Free zoom on the value axis alone is not
  needed.
- **A modifier key for wheel zoom and pan.** Wheel zoom without a modifier would take over
  page scrolling whenever the pointer crossed a chart, and the Budgets and Index pages are
  long. Plain drag is kept for the most common action, zooming to a range. The hint (FR-008)
  says which key.
- **Touch zoom and pan are not required.** The application is used from a desktop browser on
  localhost. If the chosen approach supports pinch-zoom and touch pan at no extra cost, they
  may be enabled; they are not tested.
- **The view is not saved.** The Index page already has range buttons and a configurable
  default for the one chart where the opening range matters (#279). Saving zoom state per
  chart would be a second way to keep the same preference.
- **No schema change and no endpoint change.** Everything shown comes from the existing
  chart data endpoints.
