"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

from datetime import timedelta, datetime, date
from functools import total_ordering
from sqlalchemy import or_, asc
from dateutil import relativedelta
from collections import defaultdict
from decimal import Decimal

from biweeklybudget import settings
from biweeklybudget.models import Transaction, ScheduledTransaction, Budget
from biweeklybudget.utils import dtnow


@total_ordering
class BiweeklyPayPeriod(object):
    """
    This object contains all logic related to working with pay periods,
    specifically finding a pay period for a given data, and figuring out the
    start and end dates of pay periods. Sure, the app is called "biweeklybudget"
    but there's no reason to hard-code logic all over the place that's this
    simple.
    """

    def __init__(self, start_date, db_session):
        """
        Create a new BiweeklyPayPeriod instance.

        :param start_date: starting date of the pay period
        :type start_date: :py:class:`datetime.date` or
          :py:class:`datetime.datetime`
        :param db_session: active database session to use for queries
        :type db_session: sqlalchemy.orm.session.Session
        """
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        self._db = db_session
        self._start_date = start_date
        self._end_date = start_date + self.period_length
        self._data_cache = {}
        self._income_budget_id_list = None

    @property
    def period_interval(self):
        """
        Return the interval between BiweeklyPayPeriods as a timedelta.

        :return: interval between BiweeklyPayPeriods
        :rtype: datetime.timedelta
        """
        return timedelta(days=14)

    @property
    def period_length(self):
        """
        Return the length of a BiweeklyPayPeriod; this is calculated as
        :py:attr:`~.period_interval` minus one second.

        :return: length of one BiweeklyPayPeriod
        :rtype: datetime.timedelta
        """
        return self.period_interval - timedelta(days=1)

    @property
    def start_date(self):
        """
        Return the starting date for this pay period. The period is generally
        considered to start at midnight (00:00) of this date.

        :return: start date for pay period
        :rtype: datetime.date
        """
        return self._start_date

    @property
    def end_date(self):
        """
        Return the date of the last day in this pay period. The pay period is
        generally considered to end at the last instant (i.e. 23:59:59) of this
        date.

        :return: last date in the pay period
        :rtype: datetime.date
        """
        return self._end_date

    @property
    def is_in_past(self):
        return self.end_date < dtnow().date()

    @property
    def next(self):
        """
        Return the BiweeklyPayPeriod following this one.

        :return: next BiweeklyPayPeriod after this one
        :rtype: BiweeklyPayPeriod
        """
        return BiweeklyPayPeriod(
            (self.start_date + self.period_interval),
            self._db
        )

    @property
    def previous(self):
        """
        Return the BiweeklyPayPeriod preceding this one.

        :return: previous BiweeklyPayPeriod before this one
        :rtype: BiweeklyPayPeriod
        """
        return BiweeklyPayPeriod(
            (self.start_date - self.period_interval),
            self._db
        )

    def __repr__(self):
        return '<BiweeklyPayPeriod(%s)>' % self._start_date.strftime('%Y-%m-%d')

    def __eq__(self, other):
        if not isinstance(other, BiweeklyPayPeriod):
            return NotImplemented
        return self.start_date == other.start_date

    def __lt__(self, other):
        if not isinstance(other, BiweeklyPayPeriod):
            return NotImplemented
        return self.start_date < other.start_date

    @staticmethod
    def period_for_date(dt, db_session):
        """
        Given a datetime, return the BiweeklyPayPeriod instance describing the
        pay period containing this date.

        .. todo:: This is a very naive, poorly-performing implementation.

        :param dt: datetime or date to find the pay period for
        :type dt: :py:class:`~datetime.datetime` or :py:class:`~datetime.date`
        :param db_session: active database session to use for queries
        :type db_session: sqlalchemy.orm.session.Session
        :return: BiweeklyPayPeriod containing the specified date
        :rtype: :py:class:`~.BiweeklyPayPeriod`
        """
        p = BiweeklyPayPeriod(settings.PAY_PERIOD_START_DATE, db_session)
        if isinstance(dt, datetime):
            dt = dt.date()
        if dt < p.start_date:
            while True:
                if p.end_date >= dt >= p.start_date:
                    return p
                p = p.previous
        if dt > p.end_date:
            while True:
                if p.end_date >= dt >= p.start_date:
                    return p
                p = p.next
        return p

    def filter_query(self, query, date_prop):
        """
        Filter ``query`` for ``date_prop`` in this pay period. Returns a copy
        of the query.

        e.g. to filter an existing query of :py:class:`~.OFXTransaction` for
        the BiweeklyPayPeriod starting on 2017-01-14:

        .. code-block:: python

            q = # some query here
            p = BiweeklyPayPeriod(date(2017, 1, 14))
            q = p.filter_query(q, OFXTransaction.date_posted)

        :param query: The query to filter
        :type query: ``sqlalchemy.orm.query.Query``
        :param date_prop: the Model's date property, to filter on.
        :return: the filtered query
        :rtype: ``sqlalchemy.orm.query.Query``
        """
        return query.filter(
            date_prop >= self.start_date, date_prop <= self.end_date
        )

    def _transactions(self):
        """
        Return a Query for all :py:class:`~.Transaction` for this pay period.

        :return: Query matching all Transactions for this pay period
        :rtype: sqlalchemy.orm.query.Query
        """
        return self.filter_query(
            self._db.query(Transaction),
            Transaction.date
        )

    def _scheduled_transactions_date(self):
        """
        Return a Query for all :py:class:`~.ScheduledTransaction` defined by
        date (schedule_type == "date") for this pay period.

        :return: Query matching all ScheduledTransactions defined by date, for
          this pay period.
        :rtype: sqlalchemy.orm.query.Query
        """
        return self.filter_query(
            self._db.query(ScheduledTransaction).filter(
                ScheduledTransaction.is_active.__eq__(True)),
            ScheduledTransaction.date
        )

    def _scheduled_transactions_per_period(self):
        """
        Return a Query for all :py:class:`~.ScheduledTransaction` defined by
        number per period (schedule_type == "per period") for this pay period.

        :return: Query matching all ScheduledTransactions defined by number
          per period, for this pay period.
        :rtype: sqlalchemy.orm.query.Query
        """
        return self._db.query(ScheduledTransaction).filter(
            ScheduledTransaction.schedule_type.__eq__('per period'),
            ScheduledTransaction.is_active.__eq__(True)
        ).order_by(
            asc(ScheduledTransaction.num_per_period),
            asc(ScheduledTransaction.amount)
        )

    def _scheduled_transactions_monthly(self):
        """
        Return a Query for all :py:class:`~.ScheduledTransaction` defined by
        day of month (schedule_type == "monthly") for this pay period.

        :return: Query matching all ScheduledTransactions defined by day of
          month (monthly) for this period.
        :rtype: sqlalchemy.orm.query.Query
        """
        if self.start_date.day < self.end_date.day:
            # start and end dates are contiguous, in the same month
            return self._db.query(ScheduledTransaction).filter(
                ScheduledTransaction.schedule_type.__eq__('monthly'),
                ScheduledTransaction.is_active.__eq__(True),
                ScheduledTransaction.day_of_month <= self.end_date.day,
                ScheduledTransaction.day_of_month >= self.start_date.day
            )
        # else we span two months
        return self._db.query(ScheduledTransaction).filter(
            ScheduledTransaction.schedule_type.__eq__('monthly'),
            ScheduledTransaction.is_active.__eq__(True),
            or_(
                ScheduledTransaction.day_of_month <= self.end_date.day,
                ScheduledTransaction.day_of_month >= self.start_date.day
            )
        )

    @property
    def transactions_list(self):
        """
        Return an ordered list of dicts, each representing a transaction for
        this pay period. Dicts have keys and values as described in
        :py:meth:`~._trans_dict`.

        :return: ordered list of transaction dicts
        :rtype: list
        """
        return self._data['all_trans_list']

    @property
    def _income_budget_ids(self):
        """
        Return a list of all :py:class:`~.Budget` IDs for Income budgets.

        :return: list of income budget IDs
        :rtype: list
        """
        if self._income_budget_id_list is None:
            self._income_budget_id_list = [
                b.id for b in self._db.query(
                    Budget).filter(Budget.is_income.__eq__(True)).all()
            ]
        return self._income_budget_id_list

    @property
    def _data(self):
        """
        Return the object-local data cache dict. Built it if not already
        present.

        :return: object-local data cache
        :rtype: dict
        """
        if len(self._data_cache) > 0:
            return self._data_cache
        self._data_cache = {
            'transactions': self._transactions().all(),
            'st_date': self._scheduled_transactions_date().all(),
            'st_per_period': self._scheduled_transactions_per_period().all(),
            'st_monthly': self._scheduled_transactions_monthly().all()
        }
        self._data_cache['all_trans_list'] = self._make_combined_transactions()
        self._data_cache['budget_sums'] = self._make_budget_sums()
        self._data_cache['overall_sums'] = self._make_overall_sums()
        return self._data_cache

    def clear_cache(self):
        """
        Clear the cached transaction, budget and sum data stored in
        `self._data_cache` and returned by :py:attr:`~._data`.
        """
        self._data_cache = {}

    def _make_combined_transactions(self):
        """
        Combine all Transactions and ScheduledTransactions from
        ``self._data_cache`` into one ordered list of similar dicts, adding
        dates to the monthly ScheduledTransactions as appropriate and excluding
        ScheduledTransactions that have been converted to real Transactions.
        Store the finished list back into ``self._data_cache``.
        """
        unordered = []
        # ScheduledTransaction ID to count of real trans for each
        st_ids = defaultdict(int)
        for t in self._data_cache['transactions']:
            unordered.append(self._trans_dict(t))
            if t.scheduled_trans_id is not None:
                st_ids[t.scheduled_trans_id] += 1
        for t in self._data_cache['st_date']:
            if t.id not in st_ids:
                unordered.append(self._trans_dict(t))
        for t in self._data_cache['st_monthly']:
            if t.id not in st_ids:
                unordered.append(self._trans_dict(t))
        ordered = []
        for t in self._data_cache['st_per_period']:
            d = self._trans_dict(t)
            for _ in range(0, (t.num_per_period - st_ids[t.id])):
                ordered.append(d)
        for t in sorted(unordered, key=lambda k: k['date']):
            ordered.append(t)

        def sortkey(k):
            d = k.get('date', None)
            if d is None:
                d = date.min
            return d, k['amount']

        return sorted(ordered, key=sortkey)

    @property
    def budget_sums(self):
        """
        Return a dict of budget sums; the return value of
        :py:meth:`~._make_budget_sums`.

        :return: dict of dicts, transaction sums and amounts per budget
        :rtype: dict
        """
        return self._data['budget_sums']

    def _make_budget_sums(self):
        """
        Find the sums of all transactions per periodic budget ID ; return a dict
        where keys are budget IDs and values are per-budget dicts containing:

        - ``budget_amount`` *(Decimal.decimal)* - the periodic budget
          :py:attr:`~.Budget.starting_balance`.
        - ``allocated`` *(Decimal.decimal)* - sum of all
          :py:class:`~.ScheduledTransaction` and :py:class:`~.Transaction`
          amounts against the budget this period. For actual transactions, we
          use the :py:attr:`~.Transaction.budgeted_amount` if present (not
          None).
        - ``spent`` *(Decimal.decimal)* - the sum of all actual
          :py:class:`~.Transaction` amounts against the budget this period.
        - ``trans_total`` *(Decimal.decimal)* - the sum of spent amounts for
          Transactions that have them, or allocated amounts for
          ScheduledTransactions.
        - ``remaining`` *(Decimal.decimal)* - the remaining amount in the
          budget. This is ``budget_amount`` minus the greater of ``allocated``
          or ``trans_total``. For income budgets, this is always positive.

        :return: dict of dicts, transaction sums and amounts per budget
        :rtype: dict
        """
        res = {}
        for b in self._db.query(Budget).filter(
            Budget.is_active.__eq__(True),
            Budget.is_periodic.__eq__(True)
        ).all():
            res[b.id] = {
                'budget_amount': b.starting_balance,
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': b.is_income
            }
        for t in self.transactions_list:
            if t['budget_id'] not in res:
                # inactive budget
                continue
            if t['type'] == 'ScheduledTransaction':
                res[t['budget_id']]['allocated'] += t['amount']
                res[t['budget_id']]['trans_total'] += t['amount']
                continue
            # t['type'] == 'Transaction'
            res[t['budget_id']]['trans_total'] += t['amount']
            if t['budgeted_amount'] is None:
                res[t['budget_id']]['allocated'] += t['amount']
                res[t['budget_id']]['spent'] += t['amount']
            else:
                res[t['budget_id']]['allocated'] += t['budgeted_amount']
                res[t['budget_id']]['spent'] += t['amount']
        for b in res.keys():
            if res[b]['trans_total'] > res[b]['allocated']:
                res[b]['remaining'] = res[
                    b]['budget_amount'] - res[b]['trans_total']
            else:
                res[b]['remaining'] = res[
                    b]['budget_amount'] - res[b]['allocated']
            if res[b]['is_income']:
                res[b]['remaining'] = abs(res[b]['remaining'])
        return res

    @property
    def overall_sums(self):
        """
        Return a dict of overall sums; the return value of
        :py:meth:`~._make_overall_sums`.

        :return: dict describing sums for the pay period
        :rtype: dict
        """
        return self._data['overall_sums']

    def _make_overall_sums(self):
        """
        Return a dict describing the overall sums for this pay period, namely:

        - ``allocated`` *(Decimal.decimal)* total amount allocated via
          :py:class:`~.ScheduledTransaction`,
          :py:class:`~.Transaction` (counting the
          :py:attr:`~.Transaction.budgeted_amount` for Transactions that have
          one), or :py:class:`~.Budget` (not counting income budgets).
        - ``spent`` *(Decimal.decimal)* total amount actually spent via
          :py:class:`~.Transaction`.
        - ``income`` *(Decimal.decimal)* total amount of income allocated this
          pay period. Calculated value (from :py:meth:`~._make_budget_sums` /
          ``self._data_cache['budget_sums']``) should be negative, but is
          returned as its positive inverse (absolute value).
        - ``remaining`` *(Decimal.decimal)* income minus the greater of
          ``allocated`` or ``spent`` for current or future pay periods, or minus
          ``spent`` for pay periods ending in the past (:py:attr:`~.is_in_past`)

        :return: dict describing sums for the pay period
        :rtype: dict
        """
        res = {
            'allocated': Decimal('0.0'),
            'spent': Decimal('0.0'),
            'income': Decimal('0.0'),
            'remaining': Decimal('0.0')
        }
        for _, b in self._data_cache['budget_sums'].items():
            if b['is_income']:
                if abs(b['trans_total']) > abs(b['budget_amount']):
                    res['income'] += abs(b['trans_total'])
                else:
                    res['income'] += abs(b['budget_amount'])
                continue
            if b['allocated'] > b['budget_amount']:
                res['allocated'] += b['allocated']
            else:
                res['allocated'] += b['budget_amount']
            res['spent'] += b['spent']
        if res['spent'] > res['allocated'] or self.is_in_past:
            res['remaining'] = res['income'] - res['spent']
        else:
            res['remaining'] = res['income'] - res['allocated']
        return res

    def _trans_dict(self, t):
        """
        Given a Transaction or ScheduledTransaction, return a dict of a
        common format describing the object.

        The resulting dict will have the following layout:

        * ``type`` (**str**) "Transaction" or "ScheduledTransaction"
        * ``id`` (**int**) the id of the object
        * ``date`` (**date**) the date of the transaction, or None for
          per-period ScheduledTransactions
        * ``sched_type`` (**str**) for ScheduledTransactions, the schedule
          type ("monthly", "date", or "per period")
        * ``sched_trans_id`` (**int**) for Transactions, the
          ScheduledTransaction ``id`` that it was created from, or None.
        * ``description`` (**str**) the transaction description
        * ``amount`` (**Decimal.decimal**) the transaction amount
        * ``budgeted_amount`` (**Decimal.decimal**) the budgeted amount.
          This may be None.
        * ``account_id`` (**int**) the id of the Account the transaction is
          against.
        * ``account_name`` (**str**) the name of the Account the transaction is
          against.
        * ``budget_id`` (**int**) the id of the Budget the transaction is
          against.
        * ``budget_name`` (**str**) the name of the Budget the transaction is
          against.
        * ``reconcile_id`` (**int**) the ID of the TxnReconcile, or None

        :param t: the object to return a dict for
        :type t: :py:class:`~.Transaction` or :py:class:`~.ScheduledTransaction`
        :return: dict describing ``t``
        :rtype: dict
        """
        if isinstance(t, Transaction):
            return self._dict_for_trans(t)
        return self._dict_for_sched_trans(t)

    def _dict_for_trans(self, t):
        """
        Return a dict describing the Transaction t. Called from
        :py:meth:`~._trans_dict`.

        The resulting dict will have the following layout:

        * ``type`` (**str**) "Transaction" or "ScheduledTransaction"
        * ``id`` (**int**) the id of the object
        * ``date`` (**date**) the date of the transaction, or None for
          per-period ScheduledTransactions
        * ``sched_type`` (**str**) for ScheduledTransactions, the schedule
          type ("monthly", "date", or "per period")
        * ``sched_trans_id`` (**int**) for Transactions, the
          ScheduledTransaction ``id`` that it was created from, or None.
        * ``description`` (**str**) the transaction description
        * ``amount`` (**Decimal.decimal**) the transaction amount
        * ``budgeted_amount`` (**Decimal.decimal**) the budgeted amount.
          This may be None.
        * ``account_id`` (**int**) the id of the Account the transaction is
          against.
        * ``account_name`` (**str**) the name of the Account the transaction is
          against.
        * ``budget_id`` (**int**) the id of the Budget the transaction is
          against.
        * ``budget_name`` (**str**) the name of the Budget the transaction is
          against.
        * ``reconcile_id`` (**int**) the ID of the TxnReconcile, or None

        :param t: transaction to describe
        :type t: Transaction
        :return: common-format dict describing ``t``
        :rtype: dict
        """
        res = {
            'type': 'Transaction',
            'id': t.id,
            'date': t.date,
            'sched_type': None,
            'sched_trans_id': t.scheduled_trans_id,
            'description': t.description,
            'amount': t.actual_amount,
            'account_id': t.account_id,
            'account_name': t.account.name,
            'budget_id': t.budget_id,
            'budget_name': t.budget.name
        }
        if t.reconcile is None:
            res['reconcile_id'] = None
        else:
            res['reconcile_id'] = t.reconcile.id
        if t.budgeted_amount is None:
            res['budgeted_amount'] = None
        else:
            res['budgeted_amount'] = t.budgeted_amount
        return res

    def _dict_for_sched_trans(self, t):
        """
        Return a dict describing the ScheduledTransaction t. Called from
        :py:meth:`~._trans_dict`.

        The resulting dict will have the following layout:

        * ``type`` (**str**) "Transaction" or "ScheduledTransaction"
        * ``id`` (**int**) the id of the object
        * ``date`` (**date**) the date of the transaction, or None for
          per-period ScheduledTransactions
        * ``sched_type`` (**str**) for ScheduledTransactions, the schedule
          type ("monthly", "date", or "per period")
        * ``sched_trans_id`` **None**
        * ``description`` (**str**) the transaction description
        * ``amount`` (**Decimal.decimal**) the transaction amount
        * ``budgeted_amount`` **None**
        * ``account_id`` (**int**) the id of the Account the transaction is
          against.
        * ``account_name`` (**str**) the name of the Account the transaction is
          against.
        * ``budget_id`` (**int**) the id of the Budget the transaction is
          against.
        * ``budget_name`` (**str**) the name of the Budget the transaction is
          against.
        * ``reconcile_id`` (**int**) the ID of the TxnReconcile, or None

        :param t: ScheduledTransaction to describe
        :type t: ScheduledTransaction
        :return: common-format dict describing ``t``
        :rtype: dict
        """
        res = {
            'type': 'ScheduledTransaction',
            'id': t.id,
            'sched_type': t.schedule_type,
            'sched_trans_id': None,
            'description': t.description,
            'amount': t.amount,
            'budgeted_amount': None,
            'account_id': t.account_id,
            'account_name': t.account.name,
            'budget_id': t.budget_id,
            'budget_name': t.budget.name,
            'reconcile_id': None
        }
        if t.schedule_type == 'date':
            res['date'] = t.date
            return res
        if t.schedule_type == 'per period':
            res['date'] = None
            return res
        # else it's a monthly transaction, and we need to figure out the date
        # for it that falls in this PayPeriod.
        if self.start_date.day <= t.day_of_month <= self.end_date.day:
            res['date'] = date(
                year=self.start_date.year,
                month=self.start_date.month,
                day=t.day_of_month
            )
            return res
        # If we got here, we're in a pay period that spans two months; i.e.
        # start_date.day > end_date.day.
        if t.day_of_month >= self.start_date.day:
            # in the same month as start_date.day
            res['date'] = date(
                year=self.start_date.year,
                month=self.start_date.month,
                day=t.day_of_month
            )
            return res
        # else t.day_of_month < self.start_date.day, which means it's actually
        # ``t.day_of_month`` in the next month...
        res['date'] = date(
            year=self.start_date.year,
            month=self.start_date.month,
            day=t.day_of_month
        ) + relativedelta.relativedelta(months=1)
        return res
