# Feature Specification: Spending By Budget Pie Charts

**Feature Branch**: `robot-army/issue-214-spending-by-budget-charts`

**Created**: 2026-09-12

**Status**: Complete

**Input**: GitHub issue [#214](https://github.com/jantman/biweeklybudget/issues/214) — "Spending by budget - charts": "pie charts for spending by budget - current and prev pay period, monthly, yearly, with a way to exclude specific budgets"

## Context

The Budgets page already has two line charts of spending by budget, one point per pay
period and one per calendar month, over all history. They answer "how has spending on
Groceries changed over time?" They do not answer "where did my money go this pay period,
this month or this year?" To answer that the operator has to read a spent figure per
budget off the pay period page and do the arithmetic.

The issue asks for pie charts of spending by budget for the current and previous pay
period, calendar month and calendar year, with a way to leave specific budgets out of
them.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See where the money went, per period (Priority: P1)

The operator opens the spending charts page. It shows six pie charts side by side: the
current pay period, the previous pay period, the current calendar month, the previous
calendar month, the current calendar year and the previous calendar year. Each chart is
titled with its period and the exact dates it covers, and shows the total spent. Each
slice is one budget, sized by what was spent against it in that period. Hovering a slice,
or reading the table under the chart, gives the budget's name, the amount and its share of
the total.

**Why this priority**: This is the chart the issue asks for. Without it nothing else in the
feature has anything to act on.

**Independent Test**: With known transactions in each of the six periods, open the page and
check that each chart's slices, amounts, percentages and total match the transactions
dated in that period.

**Acceptance Scenarios**:

1. **Given** transactions against several budgets in the current pay period, **When** the
   operator opens the page, **Then** the current pay period chart has one slice per budget
   with spending, each sized and labelled with that budget's total, and the chart's total
   equals the sum of the slices.
2. **Given** the same data, **When** the operator reads the table under a chart, **Then**
   it lists each budget with its amount and its percentage of the chart's total, largest
   first, and the percentages sum to 100% (within rounding).
3. **Given** a period with no spending, **When** the page opens, **Then** that chart shows
   a "no spending" message in place of a pie, and the other charts are unaffected.
4. **Given** today's date, **When** the page opens, **Then** each chart's title shows the
   first and last date of the period it covers, so the operator can see which pay period,
   month and year "current" and "previous" mean.

---

### User Story 2 - Leave specific budgets out (Priority: P1)

Some budgets would dominate every pie and hide everything else, such as rent or a
mortgage, or they are not what the operator wants to compare. The page lists every budget
that appears in any of the charts, each with a checkbox. Unticking a budget removes it from
all six charts at once. Totals and percentages are recalculated over the budgets still
shown. Ticking it again puts it back. Budgets already marked "Omit from graphs" start
unticked and can be ticked back in for a one-off look.

**Why this priority**: The issue asks for exclusion by name, and a pie chart without it is
unreadable whenever a single budget is most of the spending.

**Independent Test**: Untick one budget and check that it disappears from every chart and
that every chart's total and percentages are recalculated without it. Then tick it again
and check that the original charts come back.

**Acceptance Scenarios**:

1. **Given** the page is open with every budget included, **When** the operator unticks
   budget A, **Then** A disappears from all six charts and tables, and each chart's total
   drops by exactly A's amount in that period.
2. **Given** A has been unticked, **When** the operator ticks it again, **Then** all six
   charts return to what they showed before.
3. **Given** a budget marked "Omit from graphs", **When** the page opens, **Then** that
   budget is unticked and absent from every chart. **When** the operator ticks it, **Then**
   it appears in the charts.
4. **Given** the operator unticks every budget with spending in a period, **When** the
   chart redraws, **Then** that chart shows the "no spending" message rather than an empty
   or broken pie.
5. **Given** the operator has changed the selection, **When** the page is reloaded,
   **Then** the selection returns to its default: every budget included except those marked
   "Omit from graphs".

---

### User Story 3 - Find the charts (Priority: P2)

The operator can reach the spending charts page from the navigation menu and from the
Budgets page, next to the existing spending-by-budget line charts.

**Why this priority**: A page nobody can find gets no use, but the charts are useful by
URL before this story is done.

**Independent Test**: From the index page, follow the navigation link. From the Budgets
page, follow the link beside the existing charts. Both arrive at the spending charts page.

**Acceptance Scenarios**:

1. **Given** any page of the application, **When** the operator uses the navigation menu,
   **Then** there is an entry that opens the spending charts page.
2. **Given** the Budgets page, **When** the operator looks at the existing spending
   charts, **Then** a link beside them opens the spending charts page.

### Edge Cases

- **Refunds and returns**: a refund recorded against a budget reduces that budget's
  spending in the period it is dated in. If a budget's refunds exceed its spending in a
  period, its net is negative. A pie cannot show a negative slice, so the budget is
  left out of the slices and the total, and is listed under the chart as a net credit with
  its amount. It is never silently dropped.
- **A budget whose net spending is exactly zero** in a period does not appear in that
  chart.
- **A transaction split across several budgets** contributes each budget's share to that
  budget's slice, not the whole transaction amount to each.
- **Transfers between budgets or accounts** move money; they are not spending, and they are
  not counted.
- **Credit card payments and transactions marked as having no budget impact** are not
  counted. This matches the pay period page's "spent" figure (issues #210 and #319).
- **Income budgets** are never shown. What comes in is not spending.
- **Inactive budgets** with spending in a period are shown. The spending happened, and
  leaving it out would make the year's total wrong.
- **Scheduled transactions that have not happened yet** are not counted. The charts show
  what was actually spent, not what is planned.
- **Transactions dated later in the current period than today** (entered in advance) are
  counted in the current period, as the pay period page counts them.
- **Early in a period** (for example on 1 January) the current period's chart may have little
  or no data. It shows what exists, or the "no spending" message.
- **Budget names containing characters that have meaning in a web page** (such as `<` or
  `&`) are shown as the literal text.
- **Many budgets**: every budget with spending gets its own slice. Each budget keeps the
  same colour in every chart on the page, so a budget can be followed from chart to chart.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST provide a page showing six pie charts of spending by
  budget: current pay period, previous pay period, current calendar month, previous
  calendar month, current calendar year and previous calendar year.
- **FR-002**: "Current" MUST mean the pay period, month or year containing today's date,
  and "previous" the one immediately before it. Pay period boundaries MUST come from the
  application's existing pay period calculation.
- **FR-003**: Each chart MUST show its period's name, its first and last dates, and the
  total spent across the budgets shown.
- **FR-004**: A budget's spending in a period MUST be the net sum of the amounts allocated
  to that budget by actual transactions dated within the period, inclusive of both end
  dates. It MUST exclude income budgets; scheduled transactions not yet made into actual
  transactions; transfers between budgets or accounts; and transactions that have no
  budget impact, which includes credit card payments.
- **FR-005**: Each budget with positive net spending in a period MUST appear as one slice
  of that period's chart, sized in proportion to its spending.
- **FR-006**: Each chart MUST have a table listing every budget shown in it, with the
  budget's name, its amount, and its percentage of the chart's total, ordered from largest
  to smallest.
- **FR-007**: A budget with negative net spending in a period MUST NOT be a slice or count
  toward that chart's total, and MUST be listed under the chart as a net credit with its
  amount.
- **FR-008**: A chart with no positive spending among the budgets shown MUST display a
  "no spending" message instead of a pie.
- **FR-009**: The page MUST list, with a checkbox each, every budget that has spending in
  any of the six periods. Changing a checkbox MUST add the budget to, or remove it from,
  all six charts and their tables immediately, without reloading the page, and each
  chart's total and percentages MUST be recalculated over the budgets still shown.
- **FR-010**: Budgets marked "Omit from graphs" MUST start unticked. All other budgets
  MUST start ticked. The selection MUST NOT be saved; reloading the page restores this
  default. The operator makes an exclusion permanent by marking the budget "Omit from
  graphs", as for the existing charts.
- **FR-011**: Each budget MUST have the same colour in every chart on the page.
- **FR-012**: The page MUST be reachable from the navigation menu and from a link beside
  the existing spending charts on the Budgets page.
- **FR-013**: The data behind the charts MUST be available from an HTTP endpoint that
  returns each of the six periods' dates and per-budget spending, and each budget's "Omit
  from graphs" flag, so the page and any external script read the same numbers.
- **FR-014**: The existing spending-by-budget line charts on the Budgets page MUST NOT
  change.
- **FR-015**: The page, the endpoint, and how spending is counted MUST be documented with
  the application's other pages and endpoints.

### Key Entities

- **Reporting period**: a named date range: current or previous pay period, calendar month or
  calendar year. It has a first date and a last date, both inclusive.
- **Budget spending in a period**: for one budget and one reporting period, the net amount
  spent (FR-004). It is derived from existing transactions and stored nowhere.
- **Budget selection**: the set of budgets currently included in the charts. It exists
  only on the open page; its default comes from each budget's existing "Omit from graphs"
  flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The operator can see how spending was divided among budgets in any of the six
  periods within one page load, with no arithmetic of their own.
- **SC-002**: For every periodic budget with no transfers in the current or previous pay
  period, the amount shown for it equals the "spent" figure for that budget on that pay
  period's page, to the cent.
- **SC-003**: For every chart, the slices' amounts sum to the chart's total, to the cent,
  and the percentages in its table sum to 100% within rounding.
- **SC-004**: Excluding or re-including a budget updates all six charts within one second,
  with no page reload.
- **SC-005**: Opening the page changes nothing stored, and the existing Budgets page charts
  show exactly what they showed before.

## Assumptions

- **A new page rather than more panels on the Budgets page.** Six pie charts, each with a
  table, plus a budget selection list, would push the Budgets page's budget tables well
  below the fold. The Budgets page gains a link instead.
- **Donut-style pie charts.** The application's existing charting library draws a pie with
  a hole in the middle (a donut), not a solid pie. That is still a pie chart in the sense
  the issue means, and the hole is where the chart's total goes. Adding a second charting
  library for a solid pie is not justified. Moving all charts to another library is issue
  #215, which is separate work.
- **Calendar months and years, not trailing 30 or 365 days.** The issue names "monthly,
  yearly" beside pay periods, which are fixed calendar ranges. Calendar months and years
  also match the existing per-month line chart.
- **"Current" periods are to date.** The current month or year chart shows spending so
  far, not a projection.
- **Transfers are not spending.** The pay period page's "spent" includes budget transfers
  because it tracks how much of each budget's allocation is used. A chart titled "spending"
  that showed a transfer from a savings budget as spending from it would be wrong. The
  price of leaving transfers out is that a budget with transfers in a pay period can show a
  different figure here than its "spent" on that pay period's page. SC-002 is scoped to
  budgets without transfers for that reason.
- **Standing budgets are included.** Spending from a standing budget (a car repair fund,
  say) is real spending and belongs in "where did the money go". The existing per-month line
  chart already includes standing budgets.
- **The selection is not saved.** "Omit from graphs" is the existing, permanent,
  per-budget way to exclude a budget from charts, and it is editable on the budget form.
  The checkboxes are for a one-off look. Saving the selection would be a second, competing
  place to keep the same preference.
- **No schema change.** Everything shown is derived from existing transactions, budgets
  and the existing "Omit from graphs" flag.
