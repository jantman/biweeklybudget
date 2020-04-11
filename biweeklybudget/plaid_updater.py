"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2020 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_DOWN
from typing import Optional

from pytz import UTC

from biweeklybudget.db import db_session, upsert_record
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.ofx_statement import OFXStatement
from biweeklybudget.models.account import Account
from biweeklybudget.utils import plaid_client, dtnow

logger = logging.getLogger(__name__)


class PlaidUpdateResult:
    """Describes the result of updating a single account via Plaid."""

    def __init__(
        self, account: Account, success: bool, updated: int, added: int,
        exc: Optional[Exception], stmt_id: Optional[int]
    ):
        """
        Store the result of an update.

        :param account: the Account that this update pertains to
        :param success: whether the update succeeded or not
        :param updated: count of updated transactions
        :param added: count of added transactions
        :param exc: exception encountered, if any
        :param stmt_id: added Statement ID
        """
        self.account = account
        self.success = success
        self.updated = updated
        self.added = added
        self.exc = exc
        self.stmt_id = stmt_id

    @property
    def as_dict(self):
        return {
            'account_id': self.account.id,
            'success': self.success,
            'exception': str(self.exc),
            'statement_id': self.stmt_id,
            'added': self.added,
            'updated': self.updated
        }


class PlaidUpdater:

    def __init__(self):
        self.client = plaid_client()

    @classmethod
    def available_accounts(cls):
        """
        Return a list of :py:class:`~.Account` objects that can be updated via
        Plaid.

        :return: Accounts that can be updated via Plaid
        :rtype: list of :py:class:`~.Account` objects
        """
        return db_session.query(Account).filter(
            Account.plaid_configured
        ).order_by(Account.id).all()

    def update(self, accounts=None, days=30):
        """
        Update account balances and transactions from Plaid, for either all
        accounts that are configured for Plaid (default) or a specified list of
        Accounts.

        :param accounts: a list of :py:class:`~.Account` objects to update
        :type accounts: list or None
        :param days: number of days of transactions to get from Plaid
        :type days: int
        :return: list of :py:class:`~.PlaidUpdateResult` instances
        :rtype: list
        """
        if accounts is None:
            accounts = self.available_accounts()
        logger.debug(
            'Running Plaid update for %d accounts: %s',
            len(accounts), accounts
        )
        result = []
        for acct in accounts:
            result.append(self._do_acct(acct, days=days))
        return result

    def _do_acct(self, account, days):
        """
        Update balances and transactions from Plaid for one account.

        :param account: the account to update
        :type account: Account
        :param days: number of days of transactions to get from Plaid
        :type days: int
        """
        logger.info('Plaid update for %s', account)
        try:
            end_date = dtnow()
            end_ds = end_date.strftime('%Y-%m-%d')
            start_date = end_date - timedelta(days=days)
            start_ds = start_date.strftime('%Y-%m-%d')
            logger.debug(
                'Downloading Plaid transactions for account: %s from %s to %s',
                account.name, start_ds, end_ds
            )
            txns = self.client.Transactions.get(
                account.plaid_token, start_ds, end_ds
            )
            logger.debug('Plaid Transactions API result: %s', txns)
            sid, added, updated = self._stmt_for_acct(
                account, txns, end_date
            )
            return PlaidUpdateResult(
                account, True, updated, added, None, sid
            )
        except Exception as ex:
            logger.error(
                'Exception encountered when updating account: %s (%d)',
                account.name, account.id, exc_info=True
            )
            return PlaidUpdateResult(
                account, False, 0, 0, ex, None
            )

    def _stmt_for_acct(self, account, txns, end_dt):
        """
        Put Plaid transaction data to the DB

        :param account: the account to update
        :type account: Account
        :param txns: Plaid transaction response
        :type txns: dict
        """
        acct = txns['accounts'][0]
        stmt = OFXStatement(
            account_id=account.id,
            filename=f'Plaid_{account.name}_{int(end_dt.timestamp())}.ofx',
            file_mtime=end_dt,
            as_of=end_dt,
            currency=acct['balances']['iso_currency_code'],
            acctid=acct['mask']
        )
        if txns['item']['institution_id'] is not None:
            stmt.bankid = txns['item']['institution_id']
        if acct['type'] == 'credit':
            stmt.type = 'CreditCard'
            self._update_bank_or_credit(
                end_dt, account, acct, txns, stmt
            )
        elif acct['type'] == 'depository':
            stmt.type = 'Bank'
            self._update_bank_or_credit(
                end_dt, account, acct, txns, stmt
            )
        elif acct['type'] == 'investment':
            stmt.type = 'Investment'
            self._update_investment(end_dt, account, acct, stmt)
        else:
            raise RuntimeError(
                'ERROR: Unknown account type: ' +
                txns['accounts'][0].get('type', '<none>')
            )
        count_new, count_upd = self._new_updated_counts()
        db_session.commit()
        logger.info('Account "%s" - inserted %d new OFXTransaction(s), updated '
                    '%d existing OFXTransaction(s)',
                    account.name, count_new, count_upd)
        logger.debug('Done updating OFX in DB')
        return stmt.id, count_new, count_upd

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

    def _update_bank_or_credit(self, end_dt, account, acct, txns, stmt):
        logger.debug('Generating statement for credit account')
        stmt.as_of = end_dt
        stmt.ledger_bal_as_of = end_dt
        stmt.ledger_bal = Decimal(acct['balances']['current']).quantize(
            Decimal('.01'), rounding=ROUND_HALF_DOWN
        )
        if acct['balances'].get('available', None) is not None:
            stmt.avail_bal = Decimal(
                acct['balances']['available']
            ).quantize(Decimal('.01'), rounding=ROUND_HALF_DOWN)
            stmt.avail_bal_as_of = end_dt
        stmt.currency = acct['balances']['iso_currency_code']
        db_session.add(stmt)
        account.set_balance(
            overall_date=stmt.as_of,
            ledger=stmt.ledger_bal,
            ledger_date=stmt.ledger_bal_as_of,
            avail=stmt.avail_bal,
            avail_date=stmt.avail_bal_as_of
        )
        if len(txns['transactions']) != txns['total_transactions']:
            raise RuntimeError(
                f'ERROR: Plaid response indicates {txns["total_transactions"]}'
                f' total transactions but only contains '
                f'{len(txns["transactions"])} transactions.'
            )
        for pt in txns['transactions']:
            if pt['pending']:
                logger.info('Skipping pending transaction: %s', pt)
                continue
            kwargs = {
                'amount': Decimal(str(pt['amount'])).quantize(
                    Decimal('.01'), rounding=ROUND_HALF_DOWN
                ),
                'date_posted': datetime.strptime(
                    pt["date"], '%Y-%m-%d'
                ).replace(tzinfo=UTC),
                'fitid': pt['payment_meta']['reference_number'],
                'name': pt['name'],
                'account_id': account.id,
                'statement': stmt
            }
            if kwargs['fitid'] is None:
                kwargs['fitid'] = pt['transaction_id']
            upsert_record(
                OFXTransaction,
                ['account_id', 'fitid'],
                **kwargs
            )

    def _update_investment(self, end_dt, account, acct, stmt):
        logger.debug('Generating statement for investment account')
        stmt.as_of = end_dt
        stmt.ledger_bal = Decimal(acct['balances']['current']).quantize(
            Decimal('.01'), rounding=ROUND_HALF_DOWN
        )
        stmt.ledger_bal_as_of = end_dt
        stmt.currency = acct['balances']['iso_currency_code']
        db_session.add(stmt)
        account.set_balance(
            overall_date=stmt.as_of,
            ledger=stmt.ledger_bal,
            ledger_date=stmt.ledger_bal_as_of
        )
