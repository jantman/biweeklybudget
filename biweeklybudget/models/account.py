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
from sqlalchemy import (
    Column, Integer, String, Boolean, Text, Enum, Numeric, inspect, or_
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import null

from biweeklybudget.models.base import Base, ModelAsDict
from biweeklybudget.models.account_balance import AccountBalance
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.utils import dtnow
from biweeklybudget.prime_rate import PrimeRateCalculator
import json
import enum
from biweeklybudget.settings import STALE_DATA_TIMEDELTA, RECONCILE_BEGIN_DATE

logger = logging.getLogger(__name__)


class AcctType(enum.Enum):
    Bank = 1
    Credit = 2
    Investment = 3
    Cash = 4
    Other = 5

    @property
    def as_dict(self):
        return {'name': self.name, 'value': self.value}


class Account(Base, ModelAsDict):

    __tablename__ = 'accounts'
    __table_args__ = (
        {'mysql_engine': 'InnoDB'}
    )

    #: Primary Key
    id = Column(Integer, primary_key=True)

    #: name for the account
    name = Column(String(50), unique=True, index=True)

    #: description
    description = Column(String(254))

    #: whether or not to concatenate the OFX memo text onto the OFX name text;
    #: for banks like Chase that use the memo for run-on from the name
    ofx_cat_memo_to_name = Column(Boolean, default=False)

    #: path in Vault to read the credentials from
    vault_creds_path = Column(String(254))

    #: JSON-encoded ofxgetter configuration
    ofxgetter_config_json = Column(Text)

    #: For use in reconciling our :py:class:`~.Transaction` entries with
    #: the account's :py:class:`~.OFXTransaction` entries, whether or not to
    #: negate the OfxTransaction amount. We enter Transactions with income
    #: as negative amounts and expenses as positive amounts, but most bank
    #: OFX statements will show the opposite.
    negate_ofx_amounts = Column(Boolean, default=False)

    #: Include Transactions and OFXTransactions from this account when
    #: reconciling. Set to False to exclude accounts that are investment,
    #: payment only, or otherwise won't have a matching Transaction for each
    #: OFXTransaction.
    reconcile_trans = Column(Boolean, default=True, nullable=False)

    #: Type of account (Enum :py:class:`~.AcctType` )
    acct_type = Column(Enum(AcctType))

    #: credit limit, for credit accounts
    credit_limit = Column(Numeric(precision=10, scale=4))

    #: Finance rate (APR) for credit accounts
    apr = Column(Numeric(precision=5, scale=4))

    #: Margin added to the US Prime Rate to determine APR, for credit accounts.
    prime_rate_margin = Column(Numeric(precision=5, scale=4))

    #: Name of the :py:class:`biweeklybudget.interest._InterestCalculation`
    #: subclass used to calculate interest for this account.
    interest_class_name = Column(String(70))

    #: Name of the :py:class:`biweeklybudget.interest._MinPaymentFormula`
    #: subclass used to calculate minimum payments for this account.
    min_payment_class_name = Column(String(70))

    #: whether or not the account is active and can be used, or historical
    is_active = Column(Boolean, default=True)

    #: Relationship to all :py:class:`~.OFXStatement` for this Account
    all_statements = relationship(
        'OFXStatement', order_by='OFXStatement.as_of'
    )

    #: regex for matching transactions as interest charges
    re_interest_charge = Column(
        String(254),
        default='^(interest charge|purchase finance charge)'
    )

    #: regex for matching transactions as interest paid
    re_interest_paid = Column(
        String(254),
        default='^interest paid'
    )

    #: regex for matching transactions as payments
    re_payment = Column(
        String(254),
        default='^(online payment|internet payment|online pymt|payment)'
    )

    #: regex for matching transactions as fees
    re_fee = Column(
        String(254),
        default='^(late fee|past due fee)'
    )

    def __repr__(self):
        return "<Account(id=%d, name='%s')>" % (
            self.id, self.name
        )

    @hybrid_property
    def for_ofxgetter(self):
        """
        Return whether or not this account should be handled by ofxgetter.

        :return: whether or not ofxgetter should run for this account
        :rtype: bool
        """
        return self.ofxgetter_config_json.isnot(None)

    @hybrid_property
    def is_budget_source(self):
        """
        Return whether or not this account should be considered a funding
        source for Budgets.

        :return: whether or not this account is a Budget funding source
        :rtype: bool
        """
        if self.acct_type == AcctType.Bank or self.acct_type == AcctType.Cash:
            return True
        return False

    @is_budget_source.expression
    def is_budget_source(cls):
        return or_(
            cls.acct_type.__eq__(AcctType.Bank),
            cls.acct_type.__eq__(AcctType.Cash),
        )

    @hybrid_property
    def is_stale(self):
        """
        Return whether or not there is stale data for this account.

        :return: whether or not data for this account is stale
        :rtype: bool
        """
        # return False if we've never seen OFX data
        if self.ofx_statement is None:
            return False
        return (dtnow() - self.ofx_statement.as_of) > STALE_DATA_TIMEDELTA

    @property
    def ofxgetter_config(self):
        """
        Return the deserialized ofxgetter_config_json dict.

        :return: ofxgetter config
        :rtype: dict
        """
        try:
            return json.loads(self.ofxgetter_config_json)
        except Exception:
            return {}

    def set_ofxgetter_config(self, config):
        """
        Set ofxgetter configuration.

        :param config: ofxgetter configuration
        :type config: dict
        """
        self.ofxgetter_config_json = json.dumps(config)

    def set_balance(self, **kwargs):
        """
        Create an AccountBalance object for this account and associate it with
        the account. Add it to the current session.
        """
        kwargs['account'] = self
        inspect(self).session.add(AccountBalance(**kwargs))

    @property
    def ofx_statement(self):
        """
        Return the latest OFXStatement for this Account.

        :return: latest OFXStatement for this Account
        :rtype: biweeklybudget.models.ofx_statement.OFXStatement
        """
        if len(self.all_statements) < 1:
            return None
        return self.all_statements[-1]

    @property
    def balance(self):
        """
        Return the latest AccountBalance object for this Account.

        :return: latest AccountBalance for this Account
        :rtype: biweeklybudget.models.account_balance.AccountBalance
        """
        sess = inspect(self).session
        res = sess.query(AccountBalance).with_parent(self).order_by(
            AccountBalance.id.desc()).limit(1).first()
        return res

    @property
    def unreconciled(self):
        """
        Return a query to match all unreconciled Transactions for this account.

        :param db: active database session to use for queries
        :type db: sqlalchemy.orm.session.Session
        :return: query to match all unreconciled Transactions
        :rtype: sqlalchemy.orm.query.Query
        """
        sess = inspect(self).session
        return sess.query(Transaction).filter(
            Transaction.reconcile.__eq__(null()),
            Transaction.date.__ge__(RECONCILE_BEGIN_DATE),
            Transaction.account_id.__eq__(self.id),
            Transaction.date.__le__(dtnow())
        )

    @property
    def unreconciled_sum(self):
        """
        Return the sum of all unreconciled transaction amounts for this account.

        :return: sum of amounts of all unreconciled transactions
        :rtype: float
        """
        total = 0.0
        for t in self.unreconciled:
            total += float(t.actual_amount)
        return total

    @property
    def effective_apr(self):
        """
        Return the effective APR for a credit account. If
        :py:attr:`~.prime_rate_margin` is not Null, return that added to the
        current US Prime Rate. Otherwise, return :py:attr:`~.apr`.

        :return: Effective account APR
        :rtype: decimal.Decimal
        """
        if self.prime_rate_margin is not None:
            sess = inspect(self).session
            return PrimeRateCalculator(sess).calculate_apr(
                self.prime_rate_margin
            )
        return self.apr
