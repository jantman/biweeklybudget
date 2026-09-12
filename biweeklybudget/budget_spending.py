"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016-2024 Jason Antman <http://www.jasonantman.com>

    This file is part of biweeklybudget, also known as biweeklybudget.

    biweeklybudget is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    biweeklybudget is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with biweeklybudget.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/biweeklybudget> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""

import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, not_

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.budget_transaction import BudgetTransaction
from biweeklybudget.models.transaction import Transaction

logger = logging.getLogger(__name__)

#: The reporting periods charted on the Spending By Budget page, as
#: ``(key, display name)`` pairs in display order. See GitHub issue #214.
PERIODS = [
    ('current_pay_period', 'Current Pay Period'),
    ('previous_pay_period', 'Previous Pay Period'),
    ('current_month', 'Current Month'),
    ('previous_month', 'Previous Month'),
    ('current_year', 'Current Year'),
    ('previous_year', 'Previous Year'),
]

CENT = Decimal('0.01')


def _month_end(d):
    """
    Return the last day of the calendar month containing ``d``.

    :param d: any date in the month
    :type d: datetime.date
    :return: last day of that month
    :rtype: datetime.date
    """
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


def reporting_periods(today, current_pp):
    """
    Return the six reporting periods charted on the Spending By Budget page,
    in the order of :py:data:`~.PERIODS`.

    "Current" means the pay period, calendar month or calendar year containing
    ``today``; "previous" means the one immediately before it. Both ends of
    every period are inclusive. Current periods run to the end of the period,
    not to ``today``, so a transaction entered in advance is counted in its
    period exactly as the pay period view counts it.

    This does no database access and does not read the clock, so that its
    boundaries can be unit-tested for any date.

    :param today: the date to report relative to
    :type today: datetime.date
    :param current_pp: the pay period containing ``today``; anything with
      ``start_date``, ``end_date`` and ``previous`` attributes, normally
      :py:class:`~.BiweeklyPayPeriod`
    :return: list of six dicts, each with keys ``key``, ``name``,
      ``start_date`` and ``end_date`` (the latter two
      :py:class:`datetime.date`)
    :rtype: list
    """
    prev_pp = current_pp.previous
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    bounds = {
        'current_pay_period': (current_pp.start_date, current_pp.end_date),
        'previous_pay_period': (prev_pp.start_date, prev_pp.end_date),
        'current_month': (month_start, _month_end(today)),
        'previous_month': (prev_month_end.replace(day=1), prev_month_end),
        'current_year': (date(today.year, 1, 1), date(today.year, 12, 31)),
        'previous_year': (
            date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
        ),
    }
    return [
        {
            'key': key,
            'name': name,
            'start_date': bounds[key][0],
            'end_date': bounds[key][1]
        }
        for key, name in PERIODS
    ]


def spending_by_budget(db_session, start_date, end_date):
    """
    Return the net amount spent against each budget by actual
    :py:class:`~.Transaction` s dated from ``start_date`` to ``end_date``,
    inclusive.

    This is the sum of each budget's :py:class:`~.BudgetTransaction` amounts,
    so a Transaction split across budgets gives each budget its own share.
    Refunds (negative amounts) reduce the net. The following are not counted:

    * Income budgets (:py:attr:`~.Budget.is_income`). Money coming in is not
      spending.
    * Transfers, i.e. Transactions with a :py:attr:`~.Transaction.transfer`
      counterpart, as created by :py:func:`~.do_budget_transfer` and account
      transfers. They move money between budgets or accounts; nothing is
      spent. Note that the pay period view's "spent" figure *does* include
      budget transfers, because it tracks how much of each budget's
      allocation is used, so the two can differ for a budget with transfers.
    * Transactions excluded from budget arithmetic
      (:py:attr:`~.Transaction.is_excluded_from_budget`): those marked as
      having no budget impact, and credit card payments. This is the same
      rule the pay period view applies (GitHub issues #210 and #319).
    * :py:class:`~.ScheduledTransaction` s, which are never read here; only
      what was actually spent is counted.

    Inactive budgets are counted; the spending happened.

    :param db_session: active database session to use for queries
    :type db_session: sqlalchemy.orm.session.Session
    :param start_date: first date to include
    :type start_date: datetime.date
    :param end_date: last date to include
    :type end_date: datetime.date
    :return: dict of budget ID to net amount, rounded to cents. Budgets whose
      net rounds to zero are omitted.
    :rtype: dict
    """
    rows = db_session.query(
        BudgetTransaction.budget_id,
        func.sum(BudgetTransaction.amount)
    ).join(
        Transaction, BudgetTransaction.trans_id == Transaction.id
    ).join(
        Budget, BudgetTransaction.budget_id == Budget.id
    ).filter(
        Transaction.date >= start_date,
        Transaction.date <= end_date,
        Budget.is_income.isnot(True),
        Transaction.transfer_id.is_(None),
        not_(Transaction.is_excluded_from_budget)
    ).group_by(BudgetTransaction.budget_id).all()
    res = {}
    for budget_id, total in rows:
        amt = Decimal(total).quantize(CENT, rounding=ROUND_HALF_UP)
        if amt != 0:
            res[budget_id] = amt
    return res


def budget_spending_by_period(db_session, today):
    """
    Return the data behind the Spending By Budget page: net spending per
    budget (per :py:func:`~.spending_by_budget`) for each of the reporting
    periods (per :py:func:`~.reporting_periods`) relative to ``today``.

    The result is the response of
    ``GET /ajax/chart-data/budget-spending/by-period``:

    * ``budgets`` - list of dicts (``id``, ``name``, ``omit_from_graphs``)
      for every budget with a non-zero net in at least one period, sorted by
      name then ID. Budgets marked "omit from graphs" are included, with the
      flag, so that the page can offer to put them back in.
    * ``periods`` - list of six dicts in :py:data:`~.PERIODS` order, each with
      ``key``, ``name``, ``start_date`` and ``end_date`` (``YYYY-MM-DD``
      strings, both inclusive), and ``spending``, a list of dicts
      (``budget_id``, ``amount``) sorted by budget ID. ``amount`` is a
      :py:class:`~decimal.Decimal` rounded to cents; negative means a net
      credit.

    :param db_session: active database session to use for queries
    :type db_session: sqlalchemy.orm.session.Session
    :param today: the date to report relative to
    :type today: datetime.date
    :return: the response dict described above
    :rtype: dict
    """
    current_pp = BiweeklyPayPeriod.period_for_date(today, db_session)
    periods = []
    budget_ids = set()
    for p in reporting_periods(today, current_pp):
        sums = spending_by_budget(db_session, p['start_date'], p['end_date'])
        budget_ids.update(sums.keys())
        periods.append({
            'key': p['key'],
            'name': p['name'],
            'start_date': p['start_date'].strftime('%Y-%m-%d'),
            'end_date': p['end_date'].strftime('%Y-%m-%d'),
            'spending': [
                {'budget_id': bid, 'amount': sums[bid]}
                for bid in sorted(sums.keys())
            ]
        })
    budgets = []
    if budget_ids:
        budgets = db_session.query(Budget).filter(
            Budget.id.in_(budget_ids)
        ).all()
    return {
        'budgets': [
            {
                'id': b.id,
                'name': b.name,
                'omit_from_graphs': bool(b.omit_from_graphs)
            }
            for b in sorted(budgets, key=lambda x: (x.name, x.id))
        ],
        'periods': periods
    }
