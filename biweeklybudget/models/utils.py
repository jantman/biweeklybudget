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
import logging

from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.txn_reconcile import TxnReconcile

logger = logging.getLogger(__name__)


def do_budget_transfer(db_sess, txn_date, amount, account,
                       from_budget, to_budget, notes=None):
    """
    Transfer a given amount from ``from_budget`` to ``to_budget`` on
    ``txn_date``. This method does NOT commit database changes. There are places
    where we rely on this function not committing changes.

    :param db_sess: active database session to use for queries
    :type db_sess: sqlalchemy.orm.session.Session
    :param txn_date: date to make the transfer Transactions on
    :type txn_date: datetime.date
    :param amount: amount of money to transfer
    :type amount: float
    :param account:
    :type account: biweeklybudget.models.account.Account
    :param from_budget:
    :type from_budget: biweeklybudget.models.budget_model.Budget
    :param to_budget:
    :type to_budget: biweeklybudget.models.budget_model.Budget
    :param notes: Notes to add to the Transaction
    :type notes: str
    :return: list of Transactions created for the transfer
    :rtype: :py:obj:`list` of :py:class:`~.Transaction` objects
    """
    desc = 'Budget Transfer - %s from %s (%d) to %s (%d)' % (
        amount, from_budget.name, from_budget.id, to_budget.name,
        to_budget.id
    )
    logger.info(desc)
    t1 = Transaction(
        date=txn_date,
        actual_amount=amount,
        budgeted_amount=amount,
        description=desc,
        account=account,
        budget=from_budget,
        notes=notes
    )
    db_sess.add(t1)
    t2 = Transaction(
        date=txn_date,
        actual_amount=(-1 * amount),
        budgeted_amount=(-1 * amount),
        description=desc,
        account=account,
        budget=to_budget,
        notes=notes
    )
    db_sess.add(t2)
    t1.transfer = t2
    db_sess.add(t1)
    t2.transfer = t1
    db_sess.add(t2)
    db_sess.add(TxnReconcile(
        transaction=t1,
        note=desc
    ))
    db_sess.add(TxnReconcile(
        transaction=t2,
        note=desc
    ))
    return [t1, t2]
