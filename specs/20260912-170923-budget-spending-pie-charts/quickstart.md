# Quickstart: validating Spending By Budget Pie Charts

## Prerequisites

The MariaDB test container and environment variables, per `CLAUDE.md` ("Test Database
Setup for Development"). Use the main checkout's venv `tox` (worktrees have no venv).

## Automated validation

```bash
# unit tests: period boundaries
tox -e py314 -- biweeklybudget/tests/unit/test_budget_spending.py

# acceptance tests: counting rules, SC-002, endpoint, page, checkboxes, links
tox -e acceptance -- biweeklybudget/tests/acceptance/test_budget_spending.py \
    biweeklybudget/tests/acceptance/flaskapp/views/test_budget_spending.py

# existing budgets page tests (FR-014)
tox -e acceptance -- biweeklybudget/tests/acceptance/flaskapp/views/test_budgets.py

# the Test Gate: everything
tox -e py314 && tox -e acceptance && tox -e migrations && tox -e docs && tox -e jsdoc
```

Redirect each run's output to a scratchpad file.

## Manual scenarios

With the sample data loaded and `flask rundev` running:

1. Open `/budgets/spending`. Six panels appear. Each title shows its dates. "Current Pay
   Period" is the period containing today.
2. In any panel, check that the table's amounts add up to the panel's total and that the
   percentages sum to about 100%.
3. Note Standing1 (sample data marks it "Omit from graphs"): its checkbox is unticked, and
   it is in no chart. Tick it: it appears, and totals rise by its amount. Untick it again.
4. Untick every budget: every panel shows "No spending in this period."
5. Reload the page: the selection is back to the default.
6. For the current pay period, open `/payperiod/<start>` and compare each periodic budget's
   Spent column with the chart's table (SC-002; budgets with transfers may differ, by
   design).
7. The navigation menu has "Spending Charts". The Budgets page has a link to this page
   beside its existing charts, and those charts are unchanged.
