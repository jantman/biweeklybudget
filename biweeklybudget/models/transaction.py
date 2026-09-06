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
from sqlalchemy import (
    Column, Integer, Numeric, String, Date, Boolean, ForeignKey, inspect, func,
    select, or_
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.ext.hybrid import hybrid_property
from biweeklybudget.models.base import Base, ModelAsDict
from biweeklybudget.models.budget_transaction import BudgetTransaction
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.utils import dtnow
from biweeklybudget.settings import RECONCILE_BEGIN_DATE

logger = logging.getLogger(__name__)


class Transaction(Base, ModelAsDict):
    """
    Class that describes Transactions that have actually occurred, against one
    account and one or more budgets.

    Note that in addition to the usual class attributes, the constructor of
    this class also accepts a ``budget_amounts`` keyword argument, which passes
    its value on to :py:meth:`~.set_budget_amounts`.
    """

    __tablename__ = 'transactions'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Class properties to include in :py:attr:`~.ModelAsDict.as_dict` result.
    _dict_properties = ['actual_amount', 'is_excluded_from_budget']

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: date of the transaction
    date = Column(Date, default=dtnow().date())

    #: Budgeted amount of the transaction, if it was budgeted ahead of time
    #: via a :py:class:`~.ScheduledTransaction`. This attribute is only set by
    #: :py:meth:`~.SchedToTransFormHandler.submit` and
    #: :py:meth:`~.SkipSchedTransFormHandler.submit`. And, for some incorrect
    #: reason, by :py:func:`biweeklybudget.models.utils.do_budget_transfer`.
    budgeted_amount = Column(Numeric(precision=10, scale=4))

    #: description
    description = Column(String(254), nullable=False, index=True)

    #: free-form notes
    notes = Column(String(254))

    #: ID of the account this transaction is against
    account_id = Column(Integer, ForeignKey('accounts.id'))

    #: Relationship - :py:class:`~.Account` this transaction is against
    #:
    #: Note: ``transactions`` has two foreign keys to ``accounts.id`` -- this
    #: one and :py:attr:`~.credit_payment_acct_id` -- so ``foreign_keys`` must
    #: be stated explicitly on both relationships. Without it, SQLAlchemy
    #: cannot infer the join condition and raises ``AmbiguousForeignKeysError``
    #: when the mappers are configured.
    account = relationship(
        "Account", backref="transactions", uselist=False,
        foreign_keys=[account_id]
    )

    #: ID of the ScheduledTransaction this Transaction was created from;
    #: set when a scheduled transaction is converted to a real one
    scheduled_trans_id = Column(
        Integer, ForeignKey('scheduled_transactions.id')
    )

    #: Relationship - the :py:class:`~.ScheduledTransaction`
    #: this Transaction was created from; set when a scheduled transaction
    #: is converted to a real one
    scheduled_trans = relationship(
        "ScheduledTransaction", backref="transactions", uselist=False
    )

    #: ID of the Budget this transaction was planned to be funded by, if it
    #: was planned ahead via a :py:class:`~.ScheduledTransaction`
    planned_budget_id = Column(Integer, ForeignKey('budgets.id'))

    #: Relationship - the :py:class:`~.Budget` this transaction was planned to
    #: be funded by, if it was planned ahead via a
    #: :py:class:`~.ScheduledTransaction`.
    planned_budget = relationship(
        "Budget", backref="planned_transactions", uselist=False,
        foreign_keys=[planned_budget_id]
    )

    #: If the transaction is one half of a transfer, the Transaction ID of the
    #: other half/side of the transfer.
    transfer_id = Column(Integer, ForeignKey('transactions.id'))

    #: Relationship - the :py:class:`~.Transaction` that makes up the other
    #: half/side of a transfer, if this transaction was for a transfer.
    transfer = relationship(
        "Transaction", remote_side=[id], post_update=True, uselist=False
    )

    #: Amount of sales tax paid on this transaction.
    sales_tax = Column(
        Numeric(precision=10, scale=4), nullable=False, default=0.0
    )

    #: Whether this Transaction is excluded from all budget and pay period
    #: arithmetic. Set for transactions that need to exist so they can be
    #: reconciled against a real OFX/Plaid bank transaction, but that do not
    #: represent spending or income against any budget -- statement credits,
    #: cash-back redemptions applied as a statement credit, and manual balance
    #: reconcile adjustments.
    #:
    #: This stores only the user's explicit choice. Setting
    #: :py:attr:`~.credit_payment_acct_id` also excludes a Transaction from
    #: budget arithmetic, independently of this flag; read
    #: :py:attr:`~.is_excluded_from_budget` for the effective answer, never
    #: this column on its own.
    no_budget_impact = Column(Boolean, default=False, nullable=False)

    #: ID of the credit :py:class:`~.Account` that this Transaction is a
    #: payment toward, or None if it is not a credit card payment.
    #:
    #: A payment toward a credit account has zero budget impact: every charge
    #: on the card is budgeted on its own charge date, in its own pay period,
    #: and the payment is purely a movement of cash between two accounts this
    #: application already tracks. Setting this makes the Transaction excluded
    #: from budget arithmetic; see :py:attr:`~.is_excluded_from_budget`.
    credit_payment_acct_id = Column(Integer, ForeignKey('accounts.id'))

    #: Relationship - the credit :py:class:`~.Account` that this Transaction is
    #: a payment toward, if any. See the note on :py:attr:`~.account` for why
    #: ``foreign_keys`` is stated explicitly.
    credit_payment_acct = relationship(
        "Account", backref="credit_payments", uselist=False,
        foreign_keys=[credit_payment_acct_id]
    )

    def __init__(self, **kwargs):
        """
        Custom constructor for Transaction class to allow setting/syncing
        BudgetTransactions via constructor.

        :param kwargs: class constructor keyword arguments
        :type kwargs: dict
        """
        cls_ = type(self)
        for k in kwargs:
            if k == 'budget_amounts':
                self.set_budget_amounts(kwargs[k])
            elif not hasattr(cls_, k):
                raise TypeError(
                    "%r is an invalid keyword argument for %s" %
                    (k, cls_.__name__))
            setattr(self, k, kwargs[k])

    def __repr__(self):
        return "<Transaction(id=%s)>" % self.id

    @hybrid_property
    def actual_amount(self):
        """
        Actual amount of the transaction.

        :return: actual total amount of the transaction
        :rtype: decimal.Decimal
        """
        return sum([
            bt.amount for bt in self.budget_transactions
        ])

    @actual_amount.expression
    def actual_amount(cls):
        # see: https://docs.sqlalchemy.org/en/latest/orm/extensions/hybrid.html
        # #correlated-subquery-relationship-hybrid
        return select(
            func.sum(BudgetTransaction.amount)
        ).where(
            BudgetTransaction.trans_id.__eq__(cls.id)
        ).label('actual_amount')

    @hybrid_property
    def is_excluded_from_budget(self):
        """
        Whether this Transaction is excluded from all budget and pay period
        arithmetic, either because it was explicitly marked as having no budget
        impact (:py:attr:`~.no_budget_impact`) or because it is a payment
        toward a credit account (:py:attr:`~.credit_payment_acct_id`).

        This is the value every consumer should read. The two underlying fields
        are kept separate rather than collapsed into one so that clearing the
        credit account designation restores a Transaction's ordinary budget
        impact, while a no-budget-impact flag the user set themselves survives
        that change.

        The relationship is checked as well as the foreign key so that a
        Transaction constructed as ``Transaction(credit_payment_acct=acct)``
        answers correctly before it has been flushed, when the foreign key is
        still None. The foreign key is checked first, so the relationship is
        only consulted when it is the only thing set.

        :return: whether this Transaction is excluded from budget arithmetic
        :rtype: bool
        """
        return bool(self.no_budget_impact) or (
            self.credit_payment_acct_id is not None or
            self.credit_payment_acct is not None
        )

    @is_excluded_from_budget.expression
    def is_excluded_from_budget(cls):
        return or_(
            cls.no_budget_impact.is_(True),
            cls.credit_payment_acct_id.isnot(None)
        )

    @staticmethod
    def unreconciled(db):
        """
        Return a query to match all unreconciled Transactions.

        :param db: active database session to use for queries
        :type db: sqlalchemy.orm.session.Session
        :return: query to match all unreconciled Transactions
        :rtype: sqlalchemy.orm.query.Query
        """
        return db.query(Transaction).filter(
            Transaction.reconcile.__eq__(null()),
            Transaction.date.__ge__(RECONCILE_BEGIN_DATE),
            Transaction.account.has(reconcile_trans=True)
        )

    def set_budget_amounts(self, budget_amounts):
        """
        Manage child :py:class:`~.BudgetTransaction` objects corresponding to
        budget allocations of the amount of this transaction. Given a dictionary
        (``budget_amounts``) of budgets (either int ID or :py:class:`~.Budget`
        instances) to Decimal amounts, ensure that the BudgetTransactions for
        this Transaction match those amounts.

        This method does NOT commit changes; it will modify database state
        and add the modifications to this object's session, but the calling
        code must commit changes.

        :param budget_amounts: Mapping of one or more Budgets to the amount of
          this Transaction allocated to that Budget. Keys may be either an int
          :py:attr:`~.Budget.id` or a :py:class:`~.Budget` instance, values must
          be a Decimal.
        :type budget_amounts: dict
        """
        assert isinstance(budget_amounts, type({}))
        assert len(budget_amounts) > 0
        logger.debug(
            'Setting budget amounts on %s to: %s', self, budget_amounts
        )
        sess = inspect(self).session
        # ensure keys are all Budget objects, not IDs
        for k in list(budget_amounts.keys()):
            if not isinstance(k, Budget):
                budg = sess.query(Budget).get(k)
                logger.debug('Swapping key from %s to %s', k, budg)
                budget_amounts[budg] = budget_amounts[k]
                del budget_amounts[k]
        # delete BudgetTransactions for any budget we're not using anymore,
        # or update amounts on any that are changed
        for btrans in self.budget_transactions:
            if btrans.budget not in budget_amounts.keys():
                logger.info('Removing %s from %s', btrans, self)
                sess.delete(btrans)
            elif btrans.amount != budget_amounts[btrans.budget]:
                logger.debug(
                    'Updating amount to %s on %s for %s',
                    budget_amounts[btrans.budget], btrans, self
                )
                btrans.amount = budget_amounts[btrans.budget]
        # finally, add any new ones that didn't exist before
        btrans = {bt.budget: bt for bt in self.budget_transactions}
        for budg in budget_amounts.keys():
            if budg not in btrans:
                bt = BudgetTransaction(
                    transaction=self,
                    budget=budg,
                    amount=budget_amounts[budg]
                )
                logger.debug('Adding %s to %s', bt, self)
                # SQLAlchemy 2.0 requires explicit add to session when
                # Transaction is already in a session; when called from
                # constructor, sess is None and cascade works implicitly
                if sess is not None:
                    sess.add(bt)
