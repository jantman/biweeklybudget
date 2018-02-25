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
from sqlalchemy.orm import relationship
from biweeklybudget.models.base import Base, ModelAsDict


class BudgetTransaction(Base, ModelAsDict):
    """
    Represents the portion (amount) of a Transaction that is allocated
    against a specific budget. There will be one or more BudgetTransactions
    associated with each :py:class:`~.Transaction`.
    """

    __tablename__ = 'budget_transactions'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: Amount of the transaction against this budget
    amount = Column(Numeric(precision=10, scale=4), nullable=False)

    #: ID of the Transaction this is part of
    trans_id = Column(Integer, ForeignKey('transactions.id'))

    #: Relationship - the :py:class:`~.Transaction` this is part of
    transaction = relationship(
        "Transaction", backref="budget_transactions", uselist=False
    )

    #: ID of the Budget this transaction is against
    budget_id = Column(Integer, ForeignKey('budgets.id'))

    #: Relationship - the :py:class:`~.Budget` this transaction is against
    budget = relationship(
        "Budget", backref="budget_transactions", uselist=False
    )

    def __repr__(self):
        return "<BudgetTransaction(id=%s, transaction=%s, " \
               "budget=%s, amount=%s)>" % (
                   self.id, self.transaction, self.budget, self.amount
               )
