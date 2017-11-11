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

from sqlalchemy import Column, Integer, Numeric, Boolean, String
from biweeklybudget.models.base import Base, ModelAsDict


class Budget(Base, ModelAsDict):

    __tablename__ = 'budgets'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: Whether the budget is standing (long-running) or periodic (resets each
    #: pay period or budget cycle)
    is_periodic = Column(Boolean, default=True)

    #: name of the budget
    name = Column(String(50), unique=True, index=True)

    #: description
    description = Column(String(254))

    #: starting balance for periodic budgets
    starting_balance = Column(Numeric(precision=10, scale=4))

    #: current balance for standing budgets
    current_balance = Column(Numeric(precision=10, scale=4))

    #: whether active or historical
    is_active = Column(Boolean, default=True)

    #: whether this is an Income budget (True) or expense (False).
    is_income = Column(Boolean, default=False)

    #: whether or not to omit this budget from spending graphs
    omit_from_graphs = Column(Boolean, default=False)

    def __repr__(self):
        return "<Budget(id=%d)>" % (
            self.id
        )
