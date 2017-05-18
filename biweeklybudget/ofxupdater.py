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
from datetime import datetime

from ofxparse import AccountType, OfxParser
from pytz import UTC

from biweeklybudget.db import db_session, upsert_record
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.ofx_statement import OFXStatement
from biweeklybudget.models.account import Account
from biweeklybudget.utils import dtnow

logger = logging.getLogger(__name__)


class DuplicateFileException(Exception):
    """
    Exception raised when trying to parse a file that has already been parsed
    for the Account (going by the OFX signon date).
    """
    pass


class OFXUpdater(object):
    """
    Class to wrap updating the database with a parsed OFX file.
    """

    def __init__(self, acct_id, acct_name, cat_memo=False):
        """
        Initialize OFXUpdater for a specified account.

        :param acct_id: account database ID
        :type acct_id: int
        :param acct_name: account name
        :type acct_name: str
        :param cat_memo: whether or not to concatenate OFX Memo to Name
        :type cat_memo: bool
        """
        logger.debug(
            'Initializing OFXUpdater for account "%s" (%d)', acct_name, acct_id
        )
        self.acct_id = acct_id
        self.acct_name = acct_name
        self.acct = db_session.query(Account).get(self.acct_id)
        self.cat_memo = cat_memo

    def update(self, ofx, mtime=None, filename=None):
        """
        Update a single OFX file for this account.

        :param ofx: Ofx instance for parsed file
        :type ofx: ``ofxparse.ofxparse.Ofx``
        :param mtime: OFX file modification time (or current time)
        :type mtime: datetime.datetime
        :param filename: OFX file name
        :type filename: str
        :returns: the OFXStatement created by this run
        :rtype: biweeklybudget.models.ofx_statement.OFXStatement
        """
        if mtime is None:
            mtime = dtnow()
        if hasattr(ofx, 'status') and ofx.status['severity'] == 'ERROR':
            raise RuntimeError("OFX Error: %s" % vars(ofx))
        stmt = self._create_statement(ofx, mtime, filename)
        if ofx.account.type == AccountType.Bank:
            stmt.type = 'Bank'
            return self._update_bank_or_credit(ofx, stmt)
        elif ofx.account.type == AccountType.CreditCard:
            stmt.type = 'CreditCard'
            return self._update_bank_or_credit(ofx, stmt)
        elif ofx.account.type == AccountType.Investment:
            return self._update_investment(ofx, stmt)
        raise RuntimeError("Don't know how to update AccountType %d",
                           ofx.account.type)

    def _create_statement(self, ofx, mtime, filename):
        """
        Create an OFXStatement for this OFX file. If one already exists with
        the same account and filename, raise DuplicateFileException.

        :param ofx: Ofx instance for parsed file
        :type ofx: ``ofxparse.ofxparse.Ofx``
        :param mtime: OFX file modification time (or current time)
        :type mtime: datetime.datetime
        :param filename: OFX file name
        :type filename: str
        :return: the OFXStatement object
        :rtype: biweeklybudget.models.ofx_statement.OFXStatement
        :raises: DuplicateFileException
        """
        ofx_date = OfxParser.parseOfxDateTime(
            ofx.signon.dtserver).replace(tzinfo=UTC)
        stmt = db_session.query(OFXStatement).filter(
            OFXStatement.account_id == self.acct.id,
            OFXStatement.filename == filename
        ).first()
        if stmt is not None:
            logger.debug('Found existing statement with same as_of date, '
                         'id=%d; raising DuplicateFileException()', stmt.id)
            raise DuplicateFileException()
        logger.debug('Creating new OFXStatement account_id=%s filename=%s '
                     'as_of=%s', self.acct.id, filename, ofx_date)
        a = OFXStatement(
            account_id=self.acct.id,
            filename=filename,
            file_mtime=mtime,
            as_of=ofx_date,
            currency=ofx.account.curdef,
            acctid=ofx.account.account_id
        )
        if ofx.account.institution is not None:
            a.bankid = ofx.account.institution.fid
        if ofx.account.routing_number is not None:
            a.routing_number = ofx.account.routing_number
        if ofx.account.account_type is not None:
            a.acct_type = ofx.account.account_type
        if hasattr(ofx.account, 'brokerid'):
            a.brokerid = ofx.account.brokerid
        return a

    def _update_bank_or_credit(self, ofx, stmt):
        """
        Update a single OFX file for this Bank or Credit account.

        :param ofx: Ofx instance for parsed file
        :type ofx: ``ofxparse.ofxparse.Ofx``
        :param stmt: the OFXStatement for this statement
        :type stmt: biweeklybudget.models.ofx_statement.OFXStatement
        :returns: the OFXStatement object
        :rtype: biweeklybudget.models.ofx_statement.OFXStatement
        """
        # Note that as of 0.16, OfxParser returns tz-naive UTC datetimes
        logger.debug('Updating Bank/Credit account')
        if hasattr(ofx.account.statement, 'available_balance'):
            stmt.avail_bal = ofx.account.statement.available_balance
        if hasattr(ofx.account.statement, 'available_balance_date'):
            stmt.avail_bal_as_of = \
                ofx.account.statement.available_balance_date.replace(tzinfo=UTC)
        stmt.ledger_bal = ofx.account.statement.balance
        stmt.ledger_bal_as_of = \
            ofx.account.statement.balance_date.replace(tzinfo=UTC)
        db_session.add(stmt)
        self.acct.set_balance(
            overall_date=stmt.as_of,
            ledger=stmt.ledger_bal,
            ledger_date=stmt.ledger_bal_as_of,
            avail=stmt.avail_bal,
            avail_date=stmt.avail_bal_as_of
        )
        for txn in ofx.account.statement.transactions:
            try:
                kwargs = OFXTransaction.params_from_ofxparser_transaction(
                    txn, self.acct.id, stmt, cat_memo=self.cat_memo
                )
            except RuntimeError as ex:
                logger.error(ex)
                continue
            upsert_record(
                OFXTransaction,
                ['account_id', 'fitid'],
                **kwargs
            )
        return stmt

    def _update_investment(self, ofx, stmt):
        """
        Update a single OFX file for this Investment account.

        :param ofx: Ofx instance for parsed file
        :type ofx: ``ofxparse.ofxparse.Ofx``
        :param stmt: the OFXStatement for this statement
        :type stmt: biweeklybudget.models.ofx_statement.OFXStatement
        :returns: the OFXStatement object
        :rtype: biweeklybudget.models.ofx_statement.OFXStatement
        """
        logger.debug('Updating Investment account')
        stmt.type = 'Investment'
        value = 0
        earliest_dt = datetime.max
        for pos in ofx.account.statement.positions:
            if hasattr(pos, 'date') and isinstance(pos.date, datetime):
                if pos.date < earliest_dt:
                    earliest_dt = pos.date
            if hasattr(pos, 'market_value'):
                value += pos.market_value
            else:
                value += (pos.units * pos.unit_price)
        if earliest_dt != datetime.max:
            stmt.ledger_bal_as_of = earliest_dt.replace(tzinfo=UTC)
        if value != 0:
            stmt.ledger_bal = value
        db_session.add(stmt)
        self.acct.set_balance(
            overall_date=stmt.as_of,
            ledger=stmt.ledger_bal,
            ledger_date=stmt.ledger_bal_as_of
        )
        return stmt
