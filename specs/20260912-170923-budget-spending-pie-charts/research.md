# Research: Spending By Budget Pie Charts

No `[NEEDS CLARIFICATION]` markers came out of the spec or the Technical Context. The
items below record the technical decisions made while planning, each checked against the
existing code.

## R1: What counts as "spending", in code

**Decision**: For a period `[start, end]`, a budget's spending is

```text
SUM(BudgetTransaction.amount)
  JOIN Transaction ON BudgetTransaction.trans_id = Transaction.id
  JOIN Budget      ON BudgetTransaction.budget_id = Budget.id
WHERE Transaction.date BETWEEN start AND end
  AND Budget.is_income IS FALSE
  AND Transaction.transfer_id IS NULL
  AND NOT Transaction.is_excluded_from_budget
GROUP BY BudgetTransaction.budget_id
```

**Rationale**:

- The `BudgetTransaction` rows are how a transaction is split across budgets. Summing them,
  rather than `Transaction.actual_amount`, gives each budget its own share of a split
  (spec edge case).
- `Transaction.is_excluded_from_budget` has a SQL expression
  (`no_budget_impact OR credit_payment_acct_id IS NOT NULL`). It is the predicate the
  model's own docstring says every consumer should read. `_make_budget_sums` skips the
  same transactions, which is what makes SC-002 hold.
- `do_budget_transfer()` links the two halves of a budget transfer through
  `Transaction.transfer`, so `transfer_id IS NULL` removes transfers precisely. Account
  transfers use the same link. For those, both halves are against one budget and net to
  zero anyway, so excluding them changes nothing but is consistent.
- Only `Transaction` rows are read, never `ScheduledTransaction`, so planned spending
  cannot leak in.
- `Budget.is_active` is not filtered, because spending against a budget that has since
  been deactivated still happened.

**Alternatives considered**:

- *Reuse `BiweeklyPayPeriod.budget_sums['spent']`.* It covers periodic budgets only. It
  cannot give months or years. It counts transfers. And it builds the whole pay period's
  scheduled-transaction projection just to read one number. Rejected, but it is used as
  the oracle for the SC-002 acceptance test.
- *Reuse the existing `_by_month` loop.* It loads every transaction ever recorded into
  Python and filters `is_active=True`, which would drop spending against since-deactivated
  budgets from last year's chart. Rejected. `_by_month` itself is left alone (FR-014).

## R2: Reporting period boundaries

**Decision**: A pure function `reporting_periods(today, current_pp)` returns six periods
in display order. `current_pp` is the `BiweeklyPayPeriod` containing `today`.

| key | start | end |
|-----|-------|-----|
| `current_pay_period` | `current_pp.start_date` | `current_pp.end_date` |
| `previous_pay_period` | `current_pp.previous.start_date` | `current_pp.previous.end_date` |
| `current_month` | 1st of today's month | last day of today's month |
| `previous_month` | 1st of the prior month | last day of the prior month |
| `current_year` | 1 Jan of today's year | 31 Dec of today's year |
| `previous_year` | 1 Jan of the prior year | 31 Dec of the prior year |

Both ends are inclusive. The last day of a month is computed as the first of the next month
minus one day, so leap years and 28–31 day months need no special cases.

**Rationale**: The pay period calculation is the existing `BiweeklyPayPeriod`, which FR-002
requires. Keeping the calendar arithmetic pure, taking `today` rather than calling
`dtnow()` inside, lets unit tests pin 1 January, 31 December, 29 February and 1 March
without a database.

The current periods run to the end of the period, not to today. The spec requires
transactions entered in advance to count, matching the pay period page. Transactions
later than today are rare, and a "to date" chart that dropped them would disagree with
that page.

**Alternatives considered**: Trailing 30 and 365 day windows were rejected in the spec's
Assumptions.

## R3: Chart rendering

**Decision**: Use `Morris.Donut`, which is in the vendored `morris.min.js` 0.5.0 and needs
the Raphael build the other chart pages already load. Each chart is created with
`data: [{label, value}]`, `colors: [...]` in the same order, and a `formatter` that
renders the value as currency plus its percentage. To redraw, the chart's element is
emptied and a new `Morris.Donut` is created. That also covers going to or from the
"no spending" state, which `setData()` cannot, because Morris fails on empty data.

**Rationale**: The constitution forbids a parallel frontend stack. Morris has no solid pie,
and the donut is its pie (spec Assumptions). Recreating a chart costs a few milliseconds
for a handful of segments.

**Alternatives considered**: Chart.js or a hand-drawn Raphael pie. Both were rejected for the
stack constraint and because issue #215 exists for that.

## R4: Consistent colours per budget

**Decision** (revised during implementation): the eight-hue categorical palette validated
by the data-visualisation guidance, in its fixed order (`#2a78d6`, `#eb6834`, `#1baf7a`,
`#eda100`, `#e87ba4`, `#008300`, `#4a3aa7`, `#e34948`). The hues go to the budgets with
the most positive spending summed across all six periods, largest first. Every budget
beyond the eighth gets one muted gray (`#898781`) and remains its own slice, separated by
Morris's white segment stroke and named in the hover label and the table. The ranking is
computed once from the loaded data and never from which budgets are ticked. So a budget has
one colour in every chart, and unticking a budget never repaints the others.

**Rationale**: FR-011. The plan first called for 20 colours indexed by name, cycling if
there were more budgets than colours. The guidance forbids both cycling and generating
hues past a validated set, because extra hues cannot be told apart, and least of all with
colour vision deficiencies. The eight were run through the palette validator: every hard
gate passes (worst adjacent CVD ΔE 9.1, normal-vision ΔE 19.6). Aqua, yellow and magenta
are below 3:1 contrast on white; the table under every chart is the required relief.
Giving the hues to the biggest budgets puts distinct colours where the eye goes first.

**Alternatives considered**: Folding the tail into one "Other" slice. Rejected, because a
folded budget could not be told apart in the chart, and the checkboxes act per budget.

## R5: Where exclusion is applied

**Decision**: The server returns every non-income budget with non-zero spending in any
period, with its `omit_from_graphs` flag. The browser applies the checkbox selection: it
drops unticked budgets, splits positive nets (slices) from negative ones (credits), sums
the total, and computes percentages.

**Rationale**: FR-009 requires changes without a reload, and SC-004 requires them within a
second. Doing the filtering client side avoids a round trip per click. The arithmetic left
to the browser is summing at most a few dozen two-decimal numbers per chart. To keep
floating point error out of displayed totals, the browser sums in integer cents (see
data-model.md, "Client arithmetic").

**Alternatives considered**: Passing the excluded IDs as a query parameter and
re-fetching. That is simpler JS but a round trip per click, and the endpoint would then
have two sources of exclusion. Rejected.

## R6: URL layout

**Decision**:

- Page: `GET /budgets/spending`. `/budgets/<int:budget_id>` uses the `int` converter, so the
  two routes cannot collide. The URL sits under the Budgets section it belongs to.
- Data: `GET /ajax/chart-data/budget-spending/by-period`, a third `aggregation` value on the
  existing `BudgetSpendingChartView`.

**Rationale**: It sits with the other spending-by-budget chart data, and needs no second
view class for the same subject.

## R7: Money in JSON

**Decision**: Per-budget amounts are summed as `Decimal` in SQL and returned through the
app's existing JSON encoding, as the other chart endpoints return their amounts. Each
amount is quantized to cents on the server before serialization, so the browser receives
exact two-decimal values.

**Rationale**: Consistent with the other chart endpoints. Quantizing on the server means
the only rounding happens once, where the `Decimal` still exists.
