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
from pytz import UTC

from biweeklybudget.vendored.ofxparse import AccountType, OfxParser
from biweeklybudget.db import db_session, upsert_record
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.ofx_statement import OFXStatement
from biweeklybudget.models.account import Account
from biweeklybudget.utils import dtnow
from biweeklybudget.ofxapi.exceptions import DuplicateFileException

logger = logging.getLogger(__name__)


class OfxApiLocal(object):

    def __init__(self, db_sess):
        """
        Initialize a new Local OFX API client, when running ofxgetter or
        ofxbackfiller with direct database access, or used to back the OFX
        HTTP API.

        :param db_sess: active database session to use for queries
        :type db_sess: sqlalchemy.orm.session.Session
        """
        self._db = db_sess

    def get_accounts(self):
        """
        Query the database for all
        :py:attr:`ofxgetter-enabled
        <biweeklybudget.models.account.Account.for_ofxgetter>`
        :py:class:`Accounts <biweeklybudget.models.account.Account>` that have
        a non-empty
        :py:attr:`biweeklybudget.models.account.Account.ofxgetter_config` and a
        non-None
        :py:attr:`biweeklybudget.models.account.Account.vault_creds_path`.
        Return a dict of string
        :py:attr:`Account name <biweeklybudget.models.account.Account.name>` to
        dict with keys:

        - ``vault_path`` - :py:attr:`~.Account.vault_creds_path`
        - ``config`` - :py:attr:`~.Account.ofxgetter_config`
        - ``id`` - :py:attr:`~.Account.id`
        - ``cat_memo`` - :py:attr:`~.Account.ofx_cat_memo_to_name`

        :return: dict of account names to configuration
        :rtype: dict
        """
        result = {}
        for acct in self._db.query(Account).filter(
            Account.for_ofxgetter
        ).order_by(Account.name).all():
            if acct.vault_creds_path is None and acct.ofxgetter_config == {}:
                continue
            result[acct.name] = {
                'vault_path': acct.vault_creds_path,
                'config': acct.ofxgetter_config,
                'id': acct.id,
                'cat_memo': acct.ofx_cat_memo_to_name
            }
        logger.debug('Query found %d ofxgetter-enabled Accounts', len(result))
        return result

    def update_statement_ofx(self, acct_id, ofx, mtime=None, filename=None):
        """
        Update a single statement for the specified account, from an OFX file.

        :param acct_id: Account ID that statement is for
        :type acct_id: int
        :param ofx: Ofx instance for parsed file
        :type ofx: ``ofxparse.ofxparse.Ofx``
        :param mtime: OFX file modification time (or current time)
        :type mtime: datetime.datetime
        :param filename: OFX file name
        :type filename: str
        :returns: 3-tuple of the int ID of the
          :py:class:`~biweeklybudget.models.ofx_statement.OFXStatement`
          created by this run, int count of new :py:class:`~.OFXTransaction`
          created, and int count of :py:class:`~.OFXTransaction` updated
        :rtype: tuple
        :raises: :py:exc:`RuntimeError` on error parsing OFX or unknown account
          type; :py:exc:`~.DuplicateFileException` if the file (according to the
          OFX signon date/time) has already been recorded.
        """
        logger.info(
            'Updating Account %d with OFX Statement filename="%s" (mtime %s)',
            acct_id, filename, mtime
        )
        acct = db_session.query(Account).get(acct_id)
        if mtime is None:
            mtime = dtnow()
        if hasattr(ofx, 'status') and ofx.status['severity'] == 'ERROR':
            raise RuntimeError("OFX Error: %s" % vars(ofx))
        stmt = self._create_statement(acct, ofx, mtime, filename)
        if ofx.account.type == AccountType.Bank:
            stmt.type = 'Bank'
            s = self._update_bank_or_credit(acct, ofx, stmt)
        elif ofx.account.type == AccountType.CreditCard:
            stmt.type = 'CreditCard'
            s = self._update_bank_or_credit(acct, ofx, stmt)
        elif ofx.account.type == AccountType.Investment:
            s = self._update_investment(acct, ofx, stmt)
        else:
            raise RuntimeError("Don't know how to update AccountType %d",
                               ofx.account.type)
        count_new, count_upd = self._new_updated_counts()
        db_session.commit()
        return s.id, count_new, count_upd

    def _new_updated_counts(self):
        """
        Return integer counts of the number of :py:class:`~.OFXTransaction`
        objects that have been created and updated.

        :return: 2-tuple of new OFXTransactions created, OFXTransactions updated
        :rtype: tuple
        """
        count_new = 0
        count_upd = 0
        for obj in db_session.dirty:
            if isinstance(obj, OFXTransaction):
                count_upd += 1
        for obj in db_session.new:
            if isinstance(obj, OFXTransaction):
                count_new += 1
        return count_new, count_upd

    def _create_statement(self, acct, ofx, mtime, filename):
        """
        Create an OFXStatement for this OFX file. If one already exists with
        the same account and filename, raise DuplicateFileException.

        :param acct: the Account this statement is for
        :type acct: biweeklybudget.models.account.Account
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
            OFXStatement.account_id == acct.id,
            OFXStatement.filename == filename
        ).first()
        if stmt is not None:
            logger.debug('Found existing statement with same as_of date, '
                         'id=%d; raising DuplicateFileException()', stmt.id)
            raise DuplicateFileException(acct.id, filename, stmt.id)
        logger.debug('Creating new OFXStatement account_id=%s filename=%s '
                     'as_of=%s', acct.id, filename, ofx_date)
        a = OFXStatement(
            account_id=acct.id,
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

    def _update_bank_or_credit(self, acct, ofx, stmt):
        """
        Update a single OFX file for this Bank or Credit account.

        :param acct: the Account this statement is for
        :type acct: biweeklybudget.models.account.Account
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
        acct.set_balance(
            overall_date=stmt.as_of,
            ledger=stmt.ledger_bal,
            ledger_date=stmt.ledger_bal_as_of,
            avail=stmt.avail_bal,
            avail_date=stmt.avail_bal_as_of
        )
        for txn in ofx.account.statement.transactions:
            try:
                kwargs = OFXTransaction.params_from_ofxparser_transaction(
                    txn, acct.id, stmt, cat_memo=acct.ofx_cat_memo_to_name
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

    def _update_investment(self, acct, ofx, stmt):
        """
        Update a single OFX file for this Investment account.

        :param acct: the Account this statement is for
        :type acct: biweeklybudget.models.account.Account
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
        acct.set_balance(
            overall_date=stmt.as_of,
            ledger=stmt.ledger_bal,
            ledger_date=stmt.ledger_bal_as_of
        )
        return stmt
