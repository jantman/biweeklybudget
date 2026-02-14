.. _concepts:

Core Concepts
=============

This document explains the core financial concepts and data model behind biweeklybudget.

.. _concepts.pay_periods:

Pay Periods
-----------

All budgeting revolves around **biweekly (14-day) pay periods**. The start date
is configured via :py:attr:`~biweeklybudget.settings.PAY_PERIOD_START_DATE`, and
all subsequent periods are calculated from that anchor date.

Each pay period runs from its start date through 13 days later (inclusive). The
:py:class:`~biweeklybudget.biweeklypayperiod.BiweeklyPayPeriod` class handles
date calculations, period navigation (``.next``, ``.previous``), and aggregation
of all financial activity within a period.

.. _concepts.budgets:

Budgets
-------

Budgets are spending categories. There are two types:

.. _concepts.budgets.periodic:

Periodic Budgets
^^^^^^^^^^^^^^^^

Periodic budgets (``is_periodic=True``) **reset every pay period** with a fixed
``starting_balance``. They are used for recurring expenses like groceries, gas,
dining out, or utilities.

For each pay period, the remaining balance is calculated as::

    remaining = starting_balance - max(allocated, spent)

The ``max(allocated, spent)`` logic ensures that if you've budgeted (allocated)
more than you've actually spent so far, the higher figure is used -- you can't
"free up" budget by not yet having spent what's already committed.

Periodic budgets are included in the per-period budget summary
(:py:meth:`~biweeklybudget.biweeklypayperiod.BiweeklyPayPeriod.budget_sums`),
which shows a breakdown of each budget's starting amount, allocated amount,
spent amount, and remaining balance for the period.

.. _concepts.budgets.standing:

Standing Budgets
^^^^^^^^^^^^^^^^

Standing budgets (``is_periodic=False``) carry a ``current_balance`` forward
**across all time** -- they never reset. They are used for long-term savings
goals, irregular expenses, project funds, or any spending category that
accumulates or depletes over multiple pay periods.

The balance is updated **automatically** via SQLAlchemy event handlers in
:py:mod:`~biweeklybudget.db_event_handlers`. When a
:py:class:`~biweeklybudget.models.budget_transaction.BudgetTransaction` linked
to a standing budget is created, deleted, or modified, the budget's
``current_balance`` adjusts accordingly:

- New transaction against the budget: ``current_balance -= amount``
- Deleted transaction: ``current_balance += amount``
- Modified transaction amount: balance adjusts by the difference

Standing budgets are **not included** in the per-period budget summary, since
they are not scoped to any single pay period.

.. _concepts.budgets.income:

Income Budgets
^^^^^^^^^^^^^^

Either budget type can be marked as ``is_income=True`` to indicate it represents
income rather than an expense. Income budgets contribute to the period's total
income figure, which is used to calculate the overall remaining balance for the
period.

.. _concepts.transactions:

Transactions
------------

A :py:class:`~biweeklybudget.models.transaction.Transaction` represents actual
money movement -- a purchase, payment, deposit, or transfer against an account.

Key characteristics:

- Each transaction has a ``date``, ``description``, and ``account_id``.
- The **actual amount** is not stored directly on the transaction. Instead, it
  is the sum of all linked
  :py:class:`~biweeklybudget.models.budget_transaction.BudgetTransaction`
  records. This is exposed via the ``actual_amount`` hybrid property.
- An optional ``budgeted_amount`` field records what was *planned* to be spent
  (set when a transaction is created from a scheduled transaction), as distinct
  from what was actually spent.
- An optional ``sales_tax`` field can track sales tax separately.
- Transactions can reference a
  :py:class:`~biweeklybudget.models.scheduled_transaction.ScheduledTransaction`
  via ``scheduled_trans_id`` to indicate they were created from a scheduled
  transaction.

.. _concepts.transactions.splits:

Budget Splits
^^^^^^^^^^^^^

A single transaction can be **split across multiple budgets** via
:py:class:`~biweeklybudget.models.budget_transaction.BudgetTransaction` records.
For example, a $100 transaction might be split into $60 against a "Groceries"
budget and $40 against a "Household" budget.

The :py:meth:`~biweeklybudget.models.transaction.Transaction.set_budget_amounts`
method manages this relationship, creating, updating, or deleting
``BudgetTransaction`` records as needed.

.. _concepts.scheduled_transactions:

Scheduled Transactions
----------------------

A :py:class:`~biweeklybudget.models.scheduled_transaction.ScheduledTransaction`
defines a recurring or one-time planned transaction for forecasting purposes.
Each is linked to exactly **one budget** and **one account**.

There are five schedule types (mutually exclusive):

.. list-table::
   :header-rows: 1

   * - Type
     - Field(s)
     - Example
   * - One-time date
     - ``date``
     - March 1, 2026
   * - Monthly
     - ``day_of_month`` (1-28)
     - 15th of each month
   * - Per period
     - ``num_per_period``
     - 2 times per pay period
   * - Weekly
     - ``day_of_week`` (0=Mon, 6=Sun)
     - Every Monday
   * - Annual
     - ``annual_month`` + ``annual_day``
     - January 15th

Scheduled transactions can be marked inactive (``is_active=False``) to disable
them without deleting.

.. _concepts.scheduled_transactions.projection:

Pay Period Projection
^^^^^^^^^^^^^^^^^^^^^

The :py:class:`~biweeklybudget.biweeklypayperiod.BiweeklyPayPeriod` class merges
actual transactions with scheduled transaction projections to give a complete
financial picture for each period:

1. All actual ``Transaction`` records with dates in the period are included.
2. Scheduled transactions are projected into the period based on their schedule
   type. For monthly and annual types, the actual date(s) within the period are
   calculated. Weekly transactions always appear twice (since a period spans
   exactly two weeks).
3. Scheduled transactions that have already been converted to real transactions
   (tracked via ``scheduled_trans_id``) are excluded to avoid double-counting.
   For "per period" and weekly types, only the remaining occurrences are
   projected.

This merged view is used throughout the application to show both what has
happened and what is expected for the remainder of the period.

.. _concepts.reconciliation:

Reconciliation
--------------

:py:class:`~biweeklybudget.models.txn_reconcile.TxnReconcile` links manually
entered ``Transaction`` records to downloaded bank data
(:py:class:`~biweeklybudget.models.ofx_transaction.OFXTransaction`). This
one-to-one mapping verifies that manual entries match what the bank reports.

Bank transactions can be downloaded automatically via OFX Direct Connect
(:ref:`ofx`) or Plaid (:ref:`plaid`).

.. _concepts.projects:

Projects and Bills of Materials
-------------------------------

:py:class:`~biweeklybudget.models.projects.Project` provides a standalone cost
planning and tracking system for multi-item purchases or goals. Each project
contains a **Bill of Materials** (BoM) -- a list of
:py:class:`~biweeklybudget.models.projects.BoMItem` records, each with a name,
quantity, unit cost, and optional URL and notes.

Projects are **independent from the budgeting and transaction systems**. They do
not link to budgets or transactions; they serve as a cost estimator and shopping
list rather than an accounting ledger.

.. _concepts.projects.cost_tracking:

Cost Tracking
^^^^^^^^^^^^^

Each BoM item has a ``quantity`` and ``unit_cost``. The ``line_cost`` is
calculated automatically as ``quantity * unit_cost``.

Items can be marked inactive (``is_active=False``) when purchased or no longer
needed, rather than being deleted. This preserves the project's history and
enables two cost views on each project:

- **Total cost**: sum of all BoM item line costs (active and inactive), showing
  the overall project budget.
- **Remaining cost**: sum of only active BoM item line costs, showing what is
  still left to purchase.

Projects themselves can also be deactivated when complete.

.. _concepts.how_it_fits_together:

How It All Fits Together
------------------------

1. Define **Budgets**: periodic budgets for recurring expenses that reset each
   pay period, and standing budgets for long-term goals that carry forward.
2. Create **Scheduled Transactions** against those budgets to forecast expected
   spending and income.
3. The **Pay Period** view aggregates real and projected transactions to show
   your financial picture for each 14-day period, including per-budget remaining
   balances and an overall income-minus-expenses summary.
4. As real **Transactions** occur, they replace scheduled projections and debit
   the appropriate budgets (via budget transaction splits). Standing budget
   balances update automatically.
5. Downloaded bank transactions (**OFX Transactions**) are **reconciled**
   against manual transactions to ensure everything is accounted for.

The key distinction is that **periodic budgets** answer "how much is left *this
period*?" while **standing budgets** answer "how much *total* remains?" -- and
the pay period projection engine handles merging scheduled forecasts with actual
spending to give you the full picture.
