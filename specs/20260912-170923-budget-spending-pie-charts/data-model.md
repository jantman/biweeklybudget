# Data Model: Spending By Budget Pie Charts

No tables or columns are added or changed. Everything below is derived at request time
from existing rows.

## Existing data read

| Model | Fields used |
|-------|-------------|
| `Transaction` | `id`, `date`, `transfer_id`, `no_budget_impact`, `credit_payment_acct_id` (the last two via the `is_excluded_from_budget` hybrid) |
| `BudgetTransaction` | `trans_id`, `budget_id`, `amount` |
| `Budget` | `id`, `name`, `is_income`, `omit_from_graphs` |
| `BiweeklyPayPeriod` | `period_for_date()`, `start_date`, `end_date`, `previous` |

## Derived: ReportingPeriod

| Field | Type | Notes |
|-------|------|-------|
| `key` | str | One of `current_pay_period`, `previous_pay_period`, `current_month`, `previous_month`, `current_year`, `previous_year` |
| `name` | str | Display name, e.g. "Current Pay Period" |
| `start_date` | date | Inclusive |
| `end_date` | date | Inclusive |

**Invariants** (unit-tested):

- Always exactly six, in the order above.
- `start_date <= end_date` for every period.
- For each type, the previous period ends the day before the current one starts.
- `today` lies within every current period.
- The pay periods are 14 days, and match `BiweeklyPayPeriod.period_for_date(today)` and
  its `previous`.

## Derived: BudgetSpending (per period)

A map of `budget_id` to net `Decimal`, as specified in research R1. Budgets with a net of
exactly zero are omitted. Amounts are quantized to `0.01`.

**Rules** (acceptance-tested, one test each):

| Transaction | Counted? |
|-------------|----------|
| Ordinary, against a non-income budget, dated in the period | yes |
| Split across budgets | each budget gets its own share |
| Dated outside the period (including one day either side) | no |
| Against an income budget | no |
| Either half of a budget transfer | no |
| `no_budget_impact = True` | no |
| Credit card payment (`credit_payment_acct_id` set) | no |
| Against an inactive budget | yes |
| A refund (negative amount) | yes, reduces the net |
| A scheduled transaction not yet made real | no, never read |

## Derived: endpoint response

See [contracts/http-api.md](contracts/http-api.md). In short: a `budgets` list covering
every budget that appears in any period, and a `periods` list of the six ReportingPeriods,
each carrying its `spending` as a list of `{budget_id, amount}`.

## Client state: BudgetSelection

A set of included budget IDs, held in page memory only.

- **Initial**: every budget in `budgets` where `omit_from_graphs` is false.
- **Changed by**: a checkbox `change` event.
- **Never saved**: a reload restores the initial selection (FR-010).

## Client arithmetic (per chart, per redraw)

For the chart's `spending` entries whose budget is in the selection:

1. `slices` = entries with `amount > 0`, sorted by amount descending, then name.
2. `credits` = entries with `amount < 0`, sorted by name.
3. `totalCents` = sum over slices of `Math.round(amount * 100)`. The total is displayed
   as `totalCents / 100`, so float error cannot accumulate into the total.
4. Each slice's percentage = `amount / total * 100`, displayed to one decimal place.
5. If `slices` is empty, the chart shows the "no spending" message. Any credits are
   still listed.

**Invariant** (SC-003): the slices' amounts sum to the displayed total, to the cent.
