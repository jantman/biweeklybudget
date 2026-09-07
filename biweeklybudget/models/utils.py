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

from sqlalchemy import func

from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.txn_reconcile import TxnReconcile

logger = logging.getLogger(__name__)


def resolve_by_name_or_id(db_sess, cls, value):
    """
    Resolve a single :py:class:`~.Account` or :py:class:`~.Budget` from a value
    that may be either its numeric ID or its name.

    This exists so that the Transaction HTTP API is usable by external tooling
    that knows records by the names shown in the UI, rather than only by the
    database IDs the web frontend happens to have to hand. See GitHub issue
    #322.

    The resolution order is deliberate:

    1. The value is coerced to a string and stripped of surrounding whitespace.
       An empty result, or ``None``, is not a reference at all and yields
       ``None`` without touching the database; the caller decides whether an
       absent reference is an error for that particular field.
    2. If what remains is all ASCII digits it is looked up as a primary key. A
       hit ends resolution - IDs are the pre-existing meaning of these fields
       and keep precedence over names.
    3. Otherwise - a non-digit value, or a digit value matching no primary key
       - it is looked up as a name, matched whole and case-insensitively.
       ``Account.name`` and ``Budget.name`` are both unique, so at most one
       record can match.

    Step 3 running after a *missed* ID lookup is what keeps a record whose name
    happens to be numeric (a budget called "2024", say) reachable. The residual
    ambiguity - ID 12 existing alongside a different record named "12" - is
    resolved in favor of the ID, and is documented as such in
    ``docs/source/http_api.rst``.

    ``func.lower()`` is used explicitly rather than relying on the database's
    collation being case-insensitive, so that the behavior is a property of
    this code and is pinned by a test.

    :param db_sess: active database session to use for queries
    :type db_sess: sqlalchemy.orm.session.Session
    :param cls: the model class to resolve; must have ``id`` and a unique
      ``name`` column
    :type cls: type
    :param value: the ID or name to resolve; anything falsy or blank yields
      ``None``
    :type value: str or int or None
    :return: the matching instance of ``cls``, or ``None`` if the value
      resolves to no record. Callers are responsible for turning ``None`` into
      a validation error naming the value that could not be resolved.
    :rtype: ``cls`` or None
    """
    if value is None:
        return None
    value = str(value).strip()
    if value == '':
        return None
    if value.isdigit():
        res = db_sess.query(cls).get(int(value))
        if res is not None:
            return res
        logger.debug(
            'No %s with ID %s; trying to resolve "%s" as a name',
            cls.__name__, value, value
        )
    res = db_sess.query(cls).filter(
        func.lower(cls.name) == value.lower()
    ).one_or_none()
    if res is not None:
        logger.debug(
            'Resolved %s name "%s" to ID %s', cls.__name__, value, res.id
        )
    return res


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
        budget_amounts={from_budget: amount},
        budgeted_amount=amount,
        description=desc,
        account=account,
        notes=notes,
        planned_budget=from_budget
    )
    db_sess.add(t1)
    t2 = Transaction(
        date=txn_date,
        budget_amounts={to_budget: (-1 * amount)},
        budgeted_amount=(-1 * amount),
        description=desc,
        account=account,
        notes=notes,
        planned_budget=to_budget
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
