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

from sqlalchemy import (
    Column, String, PrimaryKeyConstraint, Text, Numeric, Boolean, ForeignKey,
    Integer, inspect
)
from sqlalchemy.sql.expression import null
from sqlalchemy_utc import UtcDateTime
from sqlalchemy.orm import relationship
from pytz import UTC
from datetime import datetime
import logging
from decimal import Decimal

from biweeklybudget.models.base import Base, ModelAsDict
from biweeklybudget.models.ofx_statement import OFXStatement
from biweeklybudget.settings import RECONCILE_BEGIN_DATE

logger = logging.getLogger(__name__)


class OFXTransaction(Base, ModelAsDict):

    __tablename__ = 'ofx_trans'
    __table_args__ = (
        PrimaryKeyConstraint('account_id', 'fitid'),
        {'mysql_engine': 'InnoDB'}
    )

    #: Account ID this transaction is associated with
    account_id = Column(
        Integer, ForeignKey('accounts.id'), nullable=False
    )

    #: Account this transaction is associated with
    account = relationship('Account', uselist=False)

    #: OFXStatement ID this transaction was last seen in
    statement_id = Column(
        Integer, ForeignKey('ofx_statements.id'), nullable=False
    )

    #: OFXStatement this transaction was last seen in
    statement = relationship(
        "OFXStatement", backref="ofx_trans"
    )

    #: OFX - FITID
    fitid = Column(String(255))

    #: OFX - Transaction Type
    trans_type = Column(String(50))

    #: OFX - Date Posted
    date_posted = Column(UtcDateTime)

    #: OFX - Amount
    amount = Column(Numeric(precision=10, scale=4))  # Amount format from OFX

    #: OFX - Name
    name = Column(String(255), index=True)

    #: OFX - Memo
    memo = Column(String(255), index=True)

    #: OFX - SIC
    sic = Column(String(255))

    #: OFX - MCC
    mcc = Column(String(255))

    #: OFX - Checknum
    checknum = Column(String(32))

    # app-specific fields

    #: Description
    description = Column(String(254), index=True)

    #: Notes
    notes = Column(Text)

    #: Account's ``re_payment`` matched
    is_payment = Column(Boolean, default=False)

    #: Account's ``re_late_fee`` matched
    is_late_fee = Column(Boolean, default=False)

    #: Account's ``re_interest_charge`` matched
    is_interest_charge = Column(Boolean, default=False)

    #: Account's ``re_fee`` matched
    is_other_fee = Column(Boolean, default=False)

    #: Account's ``re_interest_paid`` matched
    is_interest_payment = Column(Boolean, default=False)

    #: The reconcile_id for the OFX Transaction
    reconcile_id = Column(Integer, ForeignKey('txn_reconciles.id'))

    def __repr__(self):
        return "<OFXTransaction(account_id='%s', fitid='%s')>" % (
            self.account_id, self.fitid
        )

    @staticmethod
    def params_from_ofxparser_transaction(t, acct_id, stmt, cat_memo=False):
        """
        Given an ofxparser.ofxparser.Transaction object, generate and return
        a dict of kwargs to create a new OFXTransaction.

        :param t: ofxparser transaction
        :type t: ``ofxparser.ofxparser.Transaction``
        :param acct_id: OFXAccount ID
        :type acct_id: int
        :param stmt: OFXStatement this transaction was on
        :type stmt: biweeklybudget.models.ofx_statement.OFXStatement
        :param cat_memo: whether or not to concatenate OFX Memo to Name
        :type cat_memo: bool
        :return: dict of kwargs to create an OFXTransaction
        :rtype: dict
        """
        if t.id is None:
            raise RuntimeError('Transaction has no ID: %s', vars(t))
        kwargs = {
            'account_id': acct_id,
            'statement': stmt,
            'memo': t.memo,
            'name': t.payee,
            'amount': t.amount,
            'trans_type': t.type,
            # Note that as of 0.16, OfxParser returns tz-naive UTC datetimes
            'date_posted': t.date.replace(tzinfo=UTC),
            'fitid': t.id,
            'sic': t.sic,
            'mcc': t.mcc
        }
        if cat_memo:
            del kwargs['memo']
            kwargs['name'] = t.payee + t.memo
        for x in ['mcc', 'sic', 'checknum']:
            if not hasattr(t, x):
                continue
            val = getattr(t, x)
            if val is not None and val != '':
                kwargs[x] = val
        return kwargs

    @property
    def account_amount(self):
        """
        Return the amount of the transaction, appropriately negated if the
        :py:class:`~.Account` for this transaction has
        :py:attr:`~.Account.negate_ofx_amounts` True.

        :return: amount, negated as appropriate
        :rtype: decimal.Decimal
        """
        if not self.account.negate_ofx_amounts:
            return self.amount
        return self.amount * Decimal(-1.0)

    @staticmethod
    def unreconciled(db):
        """
        Return a query to match all unreconciled OFXTransactions.

        :param db: active database session to use for queries
        :type db: sqlalchemy.orm.session.Session
        :return: query to match all unreconciled OFXTransactions
        :rtype: sqlalchemy.orm.query.Query
        """
        cutoff_date = datetime(
            RECONCILE_BEGIN_DATE.year, RECONCILE_BEGIN_DATE.month,
            RECONCILE_BEGIN_DATE.day, 0, 0, 0, tzinfo=UTC
        )
        return db.query(OFXTransaction).filter(
            OFXTransaction.reconcile.__eq__(null()),
            OFXTransaction.date_posted.__ge__(cutoff_date),
            OFXTransaction.account.has(reconcile_trans=True)
        )

    @property
    def first_statement_by_date(self):
        """
        Return the first OFXStatement on or after `self.date_posted`.

        :return: first OFXStatement on or after `self.date_posted`
        :rtype: biweeklybudget.models.ofx_statement.OFXStatement
        """
        sess = inspect(self).session
        res = sess.query(OFXStatement).filter(
            OFXStatement.account.__eq__(self.account),
            OFXStatement.as_of.__ge__(self.date_posted)
        ).order_by(OFXStatement.as_of.asc()).first()
        logger.debug('First statement for %s: %s',
                     self, res)
        return res
