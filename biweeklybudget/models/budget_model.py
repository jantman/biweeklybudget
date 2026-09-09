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

from sqlalchemy import Column, Integer, Numeric, Boolean, String
from sqlalchemy.orm import relationship

from biweeklybudget.models.base import Base, ModelAsDict
from biweeklybudget.models.budget_account_link import budget_accounts


class Budget(Base, ModelAsDict):

    #: Properties (as opposed to columns) to include in
    #: :py:attr:`~.ModelAsDict.as_dict`. ``account_ids`` is listed here
    #: rather than left to fall out of the relationship because
    #: :py:attr:`~.ModelAsDict.as_dict` is built from ``vars(self)``, and a
    #: relationship appears there only when it happens to have been loaded.
    #: Without this, ``GET /ajax/budget/<id>`` would return linked account
    #: IDs sometimes and omit them other times, and the budget modal's
    #: checkboxes would be intermittently wrong. See GitHub issue #321.
    _dict_properties = ['account_ids']

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

    #: The :py:class:`~.Account` or accounts that physically hold this
    #: budget's money, via the :py:data:`~.budget_accounts` association
    #: table. Many-to-many and optional on both sides; see that table's
    #: documentation for why. Meaningful only for standing budgets, since
    #: periodic budgets do not hold a balance -- but an existing link is
    #: still read and displayed if a budget's type is later flipped, rather
    #: than silently disappearing.
    accounts = relationship(
        'Account', secondary=budget_accounts, backref='budgets'
    )

    @property
    def account_ids(self):
        """
        Return the IDs of the Accounts linked to this Budget.

        :return: IDs of linked Accounts
        :rtype: list
        """
        return [a.id for a in self.accounts]

    def __repr__(self):
        return "<Budget(id=%s, name=%s)>" % (
            self.id, self.name
        )
