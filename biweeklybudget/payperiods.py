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

from datetime import timedelta, datetime
from functools import total_ordering

from biweeklybudget import settings
from biweeklybudget.models import Transaction, ScheduledTransaction


@total_ordering
class BiweeklyPayPeriod(object):
    """
    This object contains all logic related to working with pay periods,
    specifically finding a pay period for a given data, and figuring out the
    start and end dates of pay periods. Sure, the app is called "biweeklybudget"
    but there's no reason to hard-code logic all over the place that's this
    simple.
    """

    def __init__(self, start_date):
        """
        Create a new BiweeklyPayPeriod instance.

        :param start_date: starting date of the pay period
        :type start_date: :py:class:`datetime.date` or
          :py:class:`datetime.datetime`
        """
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        self._start_date = start_date
        self._end_date = start_date + self.period_length

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
    def next(self):
        """
        Return the BiweeklyPayPeriod following this one.

        :return: next BiweeklyPayPeriod after this one
        :rtype: BiweeklyPayPeriod
        """
        return BiweeklyPayPeriod((self.start_date + self.period_interval))

    @property
    def previous(self):
        """
        Return the BiweeklyPayPeriod preceding this one.

        :return: previous BiweeklyPayPeriod before this one
        :rtype: BiweeklyPayPeriod
        """
        return BiweeklyPayPeriod((self.start_date - self.period_interval))

    @staticmethod
    def period_for_date(dt):
        """
        Given a datetime, return the BiweeklyPayPeriod instance describing the
        pay period containing this date.

        .. todo:: This is a very naive, poorly-performing implementation.

        :param dt: datetime or date to find the pay period for
        :type dt: :py:class:`~datetime.datetime` or :py:class:`~datetime.date`
        :return: BiweeklyPayPeriod containing the specified date
        :rtype: :py:class:`~.BiweeklyPayPeriod`
        """
        p = BiweeklyPayPeriod(settings.PAY_PERIOD_START_DATE)
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

    def transactions(self, db_session):
        """
        Return a Query for all :py:class:`~.Transaction` for this pay period.

        :param db_session: DB Session to run query with
        :type db_session: sqlalchemy.orm.session.Session
        :return: Query matching all Transactions for this pay period
        :rtype: sqlalchemy.orm.query.Query
        """
        return self.filter_query(
            db_session.query(Transaction),
            Transaction.date
        )

    def scheduled_transactions_date(self, db_session):
        """
        Return a Query for all :py:class:`~.ScheduledTransaction` defined by
        date (schedule_type == "date") for this pay period.

        :param db_session: DB Session to run query with
        :type db_session: sqlalchemy.orm.session.Session
        :return: Query matching all ScheduledTransactions defined by date, for
          this pay period.
        :rtype: sqlalchemy.orm.query.Query
        """
        return self.filter_query(
            db_session.query(ScheduledTransaction),
            ScheduledTransaction.date
        )
