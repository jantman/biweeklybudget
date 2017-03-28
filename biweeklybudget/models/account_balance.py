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

from sqlalchemy import Column, Integer, Numeric, ForeignKey
from sqlalchemy_utc import UtcDateTime
from sqlalchemy.orm import relationship
from biweeklybudget.models.base import Base, ModelAsDict
from biweeklybudget.utils import dtnow


class AccountBalance(Base, ModelAsDict):

    __tablename__ = 'account_balances'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: ID of the account this balance is for
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)

    #: Relationship to :py:class:`~.Account` this balance is for
    account = relationship(
        "Account", backref="all_balances"
    )

    #: Ledger balance, or investment account value, or credit card balance
    ledger = Column(Numeric(precision=10, scale=4))

    #: as-of date for the ledger balance
    ledger_date = Column(UtcDateTime)

    #: Available balance
    avail = Column(Numeric(precision=10, scale=4))

    #: as-of date for the available balance
    avail_date = Column(UtcDateTime)

    #: overall balance as of DateTime
    overall_date = Column(UtcDateTime, default=dtnow())

    def __repr__(self):
        return "<AccountBalance(id=%d)>" % (
            self.id
        )
