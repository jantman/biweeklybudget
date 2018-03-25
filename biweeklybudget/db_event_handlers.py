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

This is mostly based on http://flask.pocoo.org/docs/0.12/patterns/sqlalchemy/
"""

import logging
import time
import os
from sqlalchemy import event, inspect

from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.budget_transaction import BudgetTransaction
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.utils import fmt_currency

logger = logging.getLogger(__name__)


def handle_budget_trans_amount_change(**kwargs):
    """
    Handle change of :py:attr:`.BudgetTransaction.amount` for existing
    instances (``trans_id`` is not None). For new or deleted instances, we rely
    on :py:func:`~.handle_new_or_deleted_budget_transaction` called via
    :py:func:`~.handle_before_flush`.

    If the BudgetTransaction's :py:attr:`~.BudgetTransaction.budget` uses a
    :py:class:`~.Budget` with :py:attr:`~.Budget.is_periodic` ``False`` (i.e. a
    standing budget), update the Budget's :py:attr:`~.Budget.current_balance`
    for this transaction.

    See: :py:meth:`sqlalchemy.orm.events.AttributeEvents.set`

    :param kwargs: keyword arguments
    :type kwargs: dict
    """
    tgt = kwargs['target']
    if tgt.trans_id is None:
        logger.debug('got BudgetTransaction with trans_id None; skipping')
        return
    if tgt.budget.is_periodic:
        logger.debug('got BudgetTransaction with periodic budget; skipping')
        return
    value = kwargs['value']
    oldvalue = kwargs['oldvalue']
    session = inspect(tgt).session
    diff = oldvalue - value
    old_budg_curr = tgt.budget.current_balance
    new_budg = old_budg_curr + diff
    logger.info(
        'Handle BudgetTransaction %d against standing budget %d UPDATE; '
        'actual_amount change from %s to %s; update budget current_balance '
        'from %s to %s',
        tgt.id, tgt.budget.id, oldvalue, value, old_budg_curr, new_budg
    )
    tgt.budget.current_balance = new_budg
    session.add(tgt.budget)


def handle_new_or_deleted_budget_transaction(session):
    """
    ``before_flush`` event handler
    (:py:meth:`sqlalchemy.orm.events.SessionEvents.before_flush`)
    on the DB session, to handle creation of *new* BudgetTransactions or
    deletion of BudgetTransactions. For updates to existing BudgetTransactions,
    we rely on :py:func:`~.handle_budget_trans_amount_change`.

    If the BudgetTransaction's :py:attr:`~.BudgetTransaction.budget` is a
    :py:class:`~.Budget` with :py:attr:`~.Budget.is_periodic` ``False`` (i.e. a
    standing budget), update the Budget's :py:attr:`~.Budget.current_balance`
    for this transaction.

    :param session: current database session
    :type session: sqlalchemy.orm.session.Session
    """
    # handle NEW
    updated = 0
    for obj in session.new:
        if not isinstance(obj, BudgetTransaction):
            continue
        if obj.budget is not None:
            budg = obj.budget
        else:
            budg = session.query(Budget).get(obj.budget_id)
        if budg.is_periodic:
            continue
        logger.debug(
            'Session has new BudgetTransaction referencing standing '
            'budget id=%s', budg.id
        )
        old_amt = budg.current_balance
        budg.current_balance = old_amt - obj.amount
        logger.info(
            'New BudgetTransaction (%s) for %s against standing budget id=%s; '
            'update budget current_balance from %s to %s', obj,
            fmt_currency(obj.amount), budg.id, fmt_currency(old_amt),
            fmt_currency(budg.current_balance)
        )
        session.add(budg)
        updated += 1
    logger.debug(
        'Done handling new BudgetTransactions; updated %d standing budgets',
        updated
    )
    # handle DELETED
    updated = 0
    for obj in session.deleted:
        if not isinstance(obj, BudgetTransaction):
            continue
        if obj.budget is not None:
            budg = obj.budget
        else:
            budg = session.query(Budget).get(obj.budget_id)
        if budg.is_periodic:
            continue
        logger.debug(
            'Session has deleted BudgetTransaction referencing standing '
            'budget id=%s', budg.id
        )
        old_amt = budg.current_balance
        budg.current_balance = old_amt + obj.amount
        logger.info(
            'Deleted BudgetTransaction (%s) for %s against standing budget '
            'id=%s; update budget current_balance from %s to %s',
            obj, fmt_currency(obj.amount), budg.id,
            fmt_currency(old_amt), fmt_currency(budg.current_balance)
        )
        session.add(budg)
        updated += 1
    logger.debug(
        'Done handling deleted BudgetTransactions; '
        'updated %d standing budgets', updated
    )


def handle_ofx_transaction_new_or_change(session):
    """
    ``before_flush`` event handler
    (:py:meth:`sqlalchemy.orm.events.SessionEvents.before_flush`)
    on the DB session, to handle setting the ``is_*`` fields on new or changed
    OFXTransaction instances according to its Account.

    :param session: current database session
    :type session: sqlalchemy.orm.session.Session
    """
    for obj in session.new:
        if isinstance(obj, OFXTransaction):
            try:
                obj.update_is_fields()
            except Exception:
                logger.error('Error setting OFXTransaction is_ fields',
                             exc_info=True)
    for obj in session.dirty:
        if isinstance(obj, OFXTransaction):
            try:
                obj.update_is_fields()
            except Exception:
                logger.error('Error setting OFXTransaction is_ fields',
                             exc_info=True)


def handle_account_re_change(session):
    """
    Handler for change of one of:

    * :py:attr:`~.Account.re_interest_paid`
    * :py:attr:`~.Account.re_interest_charge`
    * :py:attr:`~.Account.re_late_fee`
    * :py:attr:`~.Account.re_other_fee`
    * :py:attr:`~.Account.re_payment`

    When one of these regexes is changed on an Account, we trigger a re-run
    of :py:meth:`~.OFXTransaction.update_is_fields` on all OFXTransactions for
    the account.

    :param session: current database session
    :type session: sqlalchemy.orm.session.Session
    """
    attrs = [
        're_interest_paid',
        're_interest_charge',
        're_late_fee',
        're_other_fee',
        're_payment'
    ]
    for obj in session.dirty:
        if not isinstance(obj, Account):
            continue
        changed = []
        insp = inspect(obj)
        for attr in attrs:
            hx = getattr(insp.attrs, attr).history
            if hx is None or hx.added is None or hx.deleted is None:
                continue
            if len(hx.added) > 0 and len(hx.deleted) > 0:
                logger.debug(
                    '%s %s changed from %s to %s',
                    obj, attr, hx.deleted, hx.added
                )
                changed.append(attr)
        if len(changed) < 1:
            continue
        logger.debug(
            '%s has regex changes; triggering update_is_fields() on all child '
            'OFXTransactions.', obj
        )
        for stmt in obj.all_statements:
            for txn in stmt.ofx_trans:
                txn.update_is_fields()
        logger.debug('Done with update_is_fields() for %s', obj)


def handle_before_flush(session, flush_context, instances):
    """
    Hook into ``before_flush``
    (:py:meth:`sqlalchemy.orm.events.SessionEvents.before_flush`)
    on the DB session, to handle updates that need to be made before persisting
    data. Currently, this method just calls a number of other methods to handle
    specific cases:

    * :py:func:`~.handle_new_or_deleted_budget_transaction`

    :param session: current database session
    :type session: sqlalchemy.orm.session.Session
    :param flush_context: internal SQLAlchemy object
    :type flush_context: sqlalchemy.orm.session.UOWTransaction
    :param instances: deprecated
    """
    logger.debug('handle_before_flush handler')
    handle_new_or_deleted_budget_transaction(session)
    handle_ofx_transaction_new_or_change(session)
    handle_account_re_change(session)
    logger.debug('handle_before_flush done')


def query_profile_before(conn, cursor, statement, parameters, context, _):  # noqa
    """
    Query profiling database event listener, to be added as listener on the
    Engine's ``before_cursor_execute`` event.

    For information, see:
    http://docs.sqlalchemy.org/en/latest/faq/performance.html#query-profiling
    """
    conn.info.setdefault('query_start_time', []).append(time.time())
    logger.debug(
        "Start Query: %s; parameters: %s", statement.replace('\n', ' '),
        parameters
    )


def query_profile_after(conn, cursor, statement, parameters, context, _):  # noqa
    """
    Query profiling database event listener, to be added as listener on the
    Engine's ``after_cursor_execute`` event.

    For information, see:
    http://docs.sqlalchemy.org/en/latest/faq/performance.html#query-profiling
    """
    total = time.time() - conn.info['query_start_time'].pop(-1)
    logger.debug(
        "Query complete in %f seconds. Query: %s; parameters: %s", total,
        statement.replace('\n', ' '), parameters
    )


def init_event_listeners(db_session, engine):
    """
    Initialize/register all SQLAlchemy event listeners.

    See http://docs.sqlalchemy.org/en/latest/orm/events.html

    :param db_session: the Database Session
    :type db_session: sqlalchemy.orm.scoping.scoped_session
    :param engine: top-level Database Engine instance
    :type engine: sqlalchemy.engine.Engine
    """
    if os.environ.get('SQL_QUERY_PROFILE', 'false') == 'true':
        logger.debug('Enabling SQL query timing event handlers.')
        event.listen(engine, 'before_cursor_execute', query_profile_before)
        event.listen(engine, 'after_cursor_execute', query_profile_after)
    logger.debug('Setting up DB model event listeners')
    event.listen(
        BudgetTransaction.amount,
        'set',
        handle_budget_trans_amount_change,
        active_history=True,
        named=True
    )
    event.listen(
        db_session,
        'before_flush',
        handle_before_flush
    )
