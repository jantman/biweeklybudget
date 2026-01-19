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

from sqlalchemy import (
    Column, Integer, String, Boolean, Date, SmallInteger, Numeric,
    ForeignKey, func
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import case

from biweeklybudget.models.base import Base, ModelAsDict
from biweeklybudget.utils import date_suffix
from sqlalchemy.ext.hybrid import hybrid_property

#: Weekday names indexed by day_of_week value (0=Monday, 6=Sunday)
WEEKDAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday',
                 'Friday', 'Saturday', 'Sunday']

#: Month abbreviations indexed by month number (1-12, index 0 unused)
MONTH_ABBREVS = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


class ScheduledTransaction(Base, ModelAsDict):

    __tablename__ = 'scheduled_transactions'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: Amount of the transaction
    amount = Column(Numeric(precision=10, scale=4), nullable=False)

    #: Sales tax paid on this transaction
    sales_tax = Column(
        Numeric(precision=10, scale=4), nullable=False, default=0.0
    )

    #: description
    description = Column(String(254), nullable=False, index=True)

    #: notes
    notes = Column(String(254))

    #: ID of the account the transaction is against
    account_id = Column(Integer, ForeignKey('accounts.id'))

    #: Relationship - :py:class:`~.Account` the transaction is against
    account = relationship(
        "Account", backref="scheduled_transactions"
    )

    #: ID of the budget the transaction is against
    budget_id = Column(Integer, ForeignKey('budgets.id'))

    #: Relationship - :py:class:`~.Budget` the transaction is against
    budget = relationship(
        "Budget", backref="scheduled_transactions"
    )

    #: whether the scheduled transaction is enabled or disabled
    is_active = Column(Boolean, default=True)

    #: Denotes a scheduled transaction that will happen once on the given date
    date = Column(Date)

    #: Denotes a scheduled transaction that happens on the same day of each
    #: month
    day_of_month = Column(SmallInteger)

    #: Denotes a scheduled transaction that happens N times per pay period
    num_per_period = Column(SmallInteger)

    #: Denotes a scheduled transaction that happens every week on a given day
    #: (0=Monday, 6=Sunday)
    day_of_week = Column(SmallInteger)

    #: Month for annual scheduled transaction (1-12)
    annual_month = Column(SmallInteger)

    #: Day for annual scheduled transaction (1-31)
    annual_day = Column(SmallInteger)

    def __repr__(self):
        return "<ScheduledTransaction(id=%d)>" % (
            self.id
        )

    @validates('day_of_month')
    def validate_day_of_month(self, _, value):
        if value is None:
            return value
        assert value > 0
        assert value <= 28
        return value

    @validates('num_per_period')
    def validate_num_per_period(self, _, value):
        if value is None:
            return value
        assert value > 0
        return value

    @validates('day_of_week')
    def validate_day_of_week(self, _, value):
        if value is None:
            return value
        assert value >= 0
        assert value <= 6
        return value

    @validates('annual_month')
    def validate_annual_month(self, _, value):
        if value is None:
            return value
        assert value >= 1
        assert value <= 12
        return value

    @validates('annual_day')
    def validate_annual_day(self, _, value):
        if value is None:
            return value
        assert value >= 1
        assert value <= 31
        return value

    @hybrid_property
    def recurrence_str(self):
        """
        Return a string describing the recurrence interval. This is a string
        of the format ``YYYY-mm-dd``, ``N per period``, ``N(st|nd|rd|th)``,
        ``Every {Weekday}``, or ``{Mon} {Day}{suffix}`` where ``N`` is an
        integer.

        :return: string describing recurrence interval
        :rtype: str
        """
        if self.schedule_type == 'date':
            return self.date.strftime('%Y-%m-%d')
        if self.schedule_type == 'monthly':
            return '%d%s' % (
                self.day_of_month,
                date_suffix(self.day_of_month)
            )
        if self.schedule_type == 'per period':
            return '%d per period' % self.num_per_period
        if self.schedule_type == 'weekly':
            return 'Every %s' % WEEKDAY_NAMES[self.day_of_week]
        if self.schedule_type == 'annual':
            return '%s %d%s' % (
                MONTH_ABBREVS[self.annual_month],
                self.annual_day,
                date_suffix(self.annual_day)
            )
        return None

    @recurrence_str.expression
    def recurrence_str(cls):
        # SQLAlchemy 2.0: case() no longer takes a list, pass tuples directly
        return case(
            (
                cls.date.isnot(None),
                func.date_format(cls.date, '%Y-%m-%d')
            ),
            (
                cls.day_of_month.isnot(None),
                cls.day_of_month
            ),
            (
                cls.num_per_period.isnot(None),
                func.concat(cls.num_per_period, ' per period')
            ),
            (
                cls.day_of_week.isnot(None),
                func.concat(
                    'Every ',
                    func.elt(
                        cls.day_of_week + 1,
                        'Monday', 'Tuesday', 'Wednesday', 'Thursday',
                        'Friday', 'Saturday', 'Sunday'
                    )
                )
            ),
            (
                cls.annual_month.isnot(None),
                func.concat(
                    func.elt(
                        cls.annual_month,
                        'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
                    ),
                    ' ',
                    cls.annual_day
                )
            ),
            else_=''
        )

    @hybrid_property
    def schedule_type(self):
        """
        Return a string describing the type of schedule; one of ``date`` (a
        specific Date), ``per period`` (a number per pay period), ``monthly``
        (a given day of the month), ``weekly`` (a given day of the week), or
        ``annual`` (a given month and day each year).

        :return: string describing type of schedule
        :rtype: str
        """
        if self.date is not None:
            return 'date'
        if self.day_of_month is not None:
            return 'monthly'
        if self.num_per_period is not None:
            return 'per period'
        if self.day_of_week is not None:
            return 'weekly'
        if self.annual_month is not None:
            return 'annual'
        return None

    @schedule_type.expression
    def schedule_type(cls):
        return case(
            (cls.date.isnot(None), 'date'),
            (cls.day_of_month.isnot(None), 'monthly'),
            (cls.num_per_period.isnot(None), 'per period'),
            (cls.day_of_week.isnot(None), 'weekly'),
            (cls.annual_month.isnot(None), 'annual'),
            else_=''
        )
