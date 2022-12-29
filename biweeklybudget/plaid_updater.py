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
from datetime import datetime, timedelta, time
from decimal import Decimal, ROUND_HALF_DOWN
from typing import Optional, List, Dict

from pytz import UTC

from biweeklybudget.db import db_session, upsert_record
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.ofx_statement import OFXStatement
from biweeklybudget.models.account import Account
from biweeklybudget.models.plaid_items import PlaidItem
from biweeklybudget.models.plaid_accounts import PlaidAccount
from biweeklybudget.utils import plaid_client, dtnow

from plaid.models import (
    ItemGetRequest, TransactionsGetRequest, TransactionsGetRequestOptions
)

logger = logging.getLogger(__name__)


class PlaidUpdateResult:
    """Describes the result of updating a single account via Plaid."""

    def __init__(
        self, item: PlaidItem, success: bool, updated: int, added: int,
        exc: Optional[Exception], stmt_ids: Optional[List[int]]
    ):
        """
        Store the result of an update.

        :param item: the PlaidItem that this update pertains to
        :param success: whether the update succeeded or not
        :param updated: count of updated transactions
        :param added: count of added transactions
        :param exc: exception encountered, if any
        :param stmt_ids: list of added Statement IDs
        """
        self.item = item
        self.success = success
        self.updated = updated
        self.added = added
        self.exc = exc
        self.stmt_ids = stmt_ids

    @property
    def as_dict(self):
        return {
            'item_id': self.item.item_id,
            'success': self.success,
            'exception': str(self.exc),
            'statement_ids': self.stmt_ids,
            'added': self.added,
            'updated': self.updated
        }


class PlaidUpdater:

    def __init__(self):
        self.client = plaid_client()

    @classmethod
    def available_items(cls):
        """
        Return a list of :py:class:`~.PlaidItem` objects that can be updated via
        Plaid.

        :return: PlaidItem that can be updated via Plaid
        :rtype: list of :py:class:`~.PlaidItem` objects
        """
        return db_session.query(PlaidItem).order_by(
            PlaidItem.institution_name
        ).all()

    def update(self, items=None, days=30):
        """
        Update account balances and transactions from Plaid, for either all
        Plaid Items that are available or a specified list of Item IDs.

        :param items: a list of :py:class:`~.PlaidItem` objects to update
        :type items: list or None
        :param days: number of days of transactions to get from Plaid
        :type days: int
        :return: list of :py:class:`~.PlaidUpdateResult` instances
        :rtype: list
        """
        if items is None:
            items = self.available_items()
        logger.debug(
            'Running Plaid update for %d items: %s',
            len(items), items
        )
        result = []
        for item in items:
            result.append(self._do_item(item, days=days))
        return result

    def _do_item(self, item, days):
        """
        Request transactions from Plaid for one Item. Update balances and
        transactions for each Account in that item.

        :param item: the item to update
        :type item: PlaidItem
        :param days: number of days of transactions to get from Plaid
        :type days: int
        :rtype: PlaidUpdateResult
        """
        logger.info('Plaid update for %s', item)
        try:
            end_date: datetime = dtnow()
            start_date: datetime = end_date - timedelta(days=days)
            iteminfo = self.client.item_get(
                ItemGetRequest(access_token=item.access_token)
            )
            logger.info(
                'Item %s transactions status: %s', item,
                iteminfo.get('status', {}).get('transactions')
            )
            logger.debug(
                'Downloading Plaid transactions for item: %s from %s to %s',
                item, start_date, end_date
            )
            txns: List[dict]
            accts: Dict
            txns, accts = self._get_transactions(
                item.access_token, start_date, end_date
            )
            accounts: Dict[str, PlaidAccount] = {}
            pa: PlaidAccount
            for pa in db_session.query(PlaidAccount).filter(
                PlaidAccount.item_id == item.item_id
            ).all():
                accounts[pa.account_id] = pa
            stmt_ids: List[int] = []
            added: int = 0
            updated: int = 0
            txns_per_acct: Dict[str, list] = {}
            for t in txns:
                if t['account_id'] not in txns_per_acct:
                    txns_per_acct[t['account_id']] = []
                txns_per_acct[t['account_id']].append(t)
            for plaid_account_id in accts.keys():
                plaid_acct: PlaidAccount = accounts[plaid_account_id]
                acct: Optional[Account] = plaid_acct.account
                if acct is None:
                    logger.warning(
                        'Plaid item %s returned transactions for %s, but it is '
                        'not mapped to an Account.', item, plaid_acct
                    )
                    continue
                sid, a, u = self._stmt_for_acct(
                    acct, accts[plaid_account_id],
                    txns_per_acct.get(plaid_account_id, []), end_date
                )
                added += a
                updated += u
                stmt_ids.append(sid)
            item.last_updated = dtnow()
            db_session.add(item)
            db_session.commit()
            return PlaidUpdateResult(
                item, True, updated, added, None, stmt_ids
            )
        except Exception as ex:
            logger.error(
                'Exception encountered when updating item: %s (%s)',
                item.institution_name, item.item_id, exc_info=True
            )
            return PlaidUpdateResult(
                item, False, 0, 0, ex, None
            )

    def _get_transactions(
            self, access_token: str, start_dt: datetime, end_dt: datetime
    ):
        kwargs = {
            'access_token': access_token,
            'start_date': start_dt.date(),
            'end_date': end_dt.date(),
            'options': TransactionsGetRequestOptions()
        }
        txns: List[dict] = []
        accts: dict = {}
        req = TransactionsGetRequest(**kwargs)
        logger.debug('Issuing transactions get request')
        resp = self.client.transactions_get(req)
        txns = resp['transactions']
        for acct in resp['accounts']:
            accts[acct['account_id']] = acct
        logger.debug(
            'Got %d transactions; expecting %d total',
            len(txns), resp['total_transactions']
        )
        while len(txns) < resp['total_transactions']:
            kwargs['options'] = TransactionsGetRequestOptions(
                offset=len(txns)
            )
            req = TransactionsGetRequest(**kwargs)
            logger.debug(
                'Issuing transactions get request with offset=%d', len(txns)
            )
            resp = self.client.transactions_get(req)
            txns.extend(resp['transactions'])
            for acct in resp['accounts']:
                accts[acct['account_id']] = acct
        return txns, accts

    def _stmt_for_acct(
        self, account: Account, plaid_acct_info: dict, plaid_txns: List[dict],
        end_dt: datetime
    ):
        """
        Put Plaid transaction data to the DB

        :param account: the account to update
        :param plaid_acct_info: dict of account information from Plaid
        :param txns: list of transactions from Plaid
        :param end_dt: current time, as of when transactions were retrieved
        """
        stmt = OFXStatement(
            account_id=account.id,
            filename=f'Plaid_{account.name}_{int(end_dt.timestamp())}.ofx',
            file_mtime=end_dt,
            as_of=end_dt,
            currency=plaid_acct_info['balances']['iso_currency_code'],
            acctid=plaid_acct_info['mask']
        )
        stmt.bankid = account.plaid_account.plaid_item.institution_id
        if account.plaid_account.account_type == 'credit':
            stmt.type = 'CreditCard'
            self._update_bank_or_credit(
                end_dt, account, plaid_acct_info, plaid_txns, stmt
            )
        elif account.plaid_account.account_type == 'depository':
            stmt.type = 'Bank'
            self._update_bank_or_credit(
                end_dt, account, plaid_acct_info, plaid_txns, stmt
            )
        elif account.plaid_account.account_type == 'investment':
            stmt.type = 'Investment'
            self._update_investment(end_dt, account, plaid_acct_info, stmt)
        elif account.plaid_account.account_type == 'loan':
            # For now, this should work...
            stmt.type = 'Investment'
            self._update_investment(end_dt, account, plaid_acct_info, stmt)
        else:
            raise RuntimeError(
                'ERROR: Unknown account type: ' +
                account.plaid_account.account_type
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

    def _update_bank_or_credit(
        self, end_dt: datetime, account: Account, plaid_acct_info: dict,
        plaid_txns: List[dict], stmt: OFXStatement
    ):
        logger.debug('Generating statement for credit account')
        stmt.as_of = end_dt
        stmt.ledger_bal_as_of = end_dt
        stmt.ledger_bal = Decimal(
            plaid_acct_info['balances']['current']
        ).quantize(
            Decimal('.01'), rounding=ROUND_HALF_DOWN
        )
        if plaid_acct_info['balances'].get('available', None) is not None:
            stmt.avail_bal = Decimal(
                plaid_acct_info['balances']['available']
            ).quantize(Decimal('.01'), rounding=ROUND_HALF_DOWN)
            stmt.avail_bal_as_of = end_dt
        stmt.currency = plaid_acct_info['balances']['iso_currency_code']
        db_session.add(stmt)
        account.set_balance(
            overall_date=stmt.as_of,
            ledger=stmt.ledger_bal,
            ledger_date=stmt.ledger_bal_as_of,
            avail=stmt.avail_bal,
            avail_date=stmt.avail_bal_as_of
        )
        for pt in plaid_txns:
            if pt['pending']:
                logger.info('Skipping pending transaction: %s', pt)
                continue
            kwargs = {
                'amount': Decimal(str(pt['amount'])).quantize(
                    Decimal('.01'), rounding=ROUND_HALF_DOWN
                ),
                'date_posted': datetime.combine(
                    pt["date"], time(0, 0, 0), tzinfo=UTC
                ),
                'fitid': pt['payment_meta']['reference_number'],
                'name': pt['name'],
                'account_id': account.id,
                'statement': stmt
            }
            if account.negate_ofx_amounts:
                kwargs['amount'] = kwargs['amount'] * Decimal('-1.0')
            if kwargs['fitid'] is None:
                kwargs['fitid'] = pt['transaction_id']
            upsert_record(
                OFXTransaction,
                ['account_id', 'fitid'],
                **kwargs
            )

    def _update_investment(
        self, end_dt: datetime, account: Account, plaid_acct_info: dict,
        stmt: OFXStatement
    ):
        logger.debug('Generating statement for investment account')
        stmt.as_of = end_dt
        stmt.ledger_bal = Decimal(
            plaid_acct_info['balances']['current']
        ).quantize(Decimal('.01'), rounding=ROUND_HALF_DOWN)
        stmt.ledger_bal_as_of = end_dt
        stmt.currency = plaid_acct_info['balances']['iso_currency_code']
        db_session.add(stmt)
        account.set_balance(
            overall_date=stmt.as_of,
            ledger=stmt.ledger_bal,
            ledger_date=stmt.ledger_bal_as_of
        )
