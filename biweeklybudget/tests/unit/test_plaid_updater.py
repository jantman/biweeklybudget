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

from biweeklybudget.plaid_updater import PlaidUpdateResult, PlaidUpdater
from biweeklybudget.models.account import Account
from biweeklybudget.models.ofx_transaction import OFXTransaction
from plaid import Client
from datetime import datetime
from decimal import Decimal
from pytz import UTC

from unittest.mock import Mock, patch, call, MagicMock, DEFAULT
import pytest

pbm = 'biweeklybudget.plaid_updater'
pb = f'{pbm}.PlaidUpdater'


class TestPlaidUpdateResult:

    def test_happy_path(self):
        acct = Mock(spec_set=Account)
        type(acct).id = 2
        r = PlaidUpdateResult(
            acct, True, 1, 2, 'foo', 123
        )
        assert r.account == acct
        assert r.success is True
        assert r.updated == 1
        assert r.added == 2
        assert r.exc == 'foo'
        assert r.stmt_id == 123
        assert r.as_dict == {
            'account_id': 2,
            'success': True,
            'exception': 'foo',
            'statement_id': 123,
            'added': 2,
            'updated': 1
        }


class TestInit:

    def test_happy_path(self):
        mock_plaid = Mock()
        with patch(f'{pbm}.plaid_client') as m_pc:
            m_pc.return_value = mock_plaid
            cls = PlaidUpdater()
        assert cls.client == mock_plaid
        assert m_pc.mock_calls == [call()]


class TestAvailableAccounts:

    def test_happy_path(self):
        accts = [
            Mock(id=1),
            Mock(id=2)
        ]
        mock_id = Mock()
        mock_pc = Mock()
        mock_account = Mock(id=mock_id, plaid_configured=mock_pc)
        with patch(f'{pbm}.db_session') as mock_db:
            with patch(f'{pbm}.Account', mock_account):
                mock_db.query.return_value.filter.return_value \
                    .order_by.return_value.all.return_value = accts
                res = PlaidUpdater.available_accounts()
        assert res == accts
        assert mock_db.mock_calls == [
            call.query(mock_account),
            call.query().filter(mock_pc),
            call.query().filter().order_by(mock_id),
            call.query().filter().order_by().all()
        ]


class PlaidUpdaterTester:

    def setup(self):
        self.mock_client = MagicMock(spec_set=Client)
        with patch(f'{pbm}.plaid_client') as m_pc:
            m_pc.return_value = self.mock_client
            self.cls = PlaidUpdater()


class TestUpdate(PlaidUpdaterTester):

    def test_accounts_none(self):
        acct1 = Mock()
        acct2 = Mock()
        acct3 = Mock()
        accts = [acct1, acct2, acct3]
        res1 = Mock()
        res2 = Mock()
        res3 = Mock()
        results = [res1, res2, res3]
        with patch(f'{pb}.available_accounts') as m_avail:
            m_avail.return_value = accts
            with patch(f'{pb}._do_acct') as m_do_acct:
                m_do_acct.side_effect = results
                res = self.cls.update()
        assert res == results
        assert m_avail.mock_calls == [call()]
        assert m_do_acct.mock_calls == [
            call(acct1, days=30),
            call(acct2, days=30),
            call(acct3, days=30)
        ]

    def test_accounts_specified(self):
        acct1 = Mock()
        acct2 = Mock()
        acct3 = Mock()
        accts = [acct1, acct2, acct3]
        res1 = Mock()
        res3 = Mock()
        results = [res1, res3]
        with patch(f'{pb}.available_accounts') as m_avail:
            m_avail.return_value = accts
            with patch(f'{pb}._do_acct') as m_do_acct:
                m_do_acct.side_effect = results
                res = self.cls.update(accounts=[acct1, acct3], days=10)
        assert res == results
        assert m_avail.mock_calls == []
        assert m_do_acct.mock_calls == [
            call(acct1, days=10),
            call(acct3, days=10)
        ]


class TestDoAcct(PlaidUpdaterTester):

    def test_happy_path(self):
        mock_get = Mock()
        type(self.mock_client).Transactions = mock_get
        mock_get.get.return_value = {'foo': 'bar'}
        mock_acct = Mock(plaid_token='tkn', id=5)
        type(mock_acct).name = 'acct1'
        with patch(f'{pb}._stmt_for_acct') as m_sfa:
            m_sfa.return_value = ('mysid', 3, 7)
            with patch(f'{pbm}.dtnow') as m_dtnow:
                m_dtnow.return_value = datetime(2020, 5, 25, 0, 0, 0)
                res = self.cls._do_acct(mock_acct, 15)
        assert isinstance(res, PlaidUpdateResult)
        assert res.account == mock_acct
        assert res.updated == 7
        assert res.added == 3
        assert res.success is True
        assert res.exc is None
        assert res.stmt_id == 'mysid'
        assert mock_get.mock_calls == [
            call.get('tkn', '2020-05-10', '2020-05-25')
        ]
        assert m_sfa.mock_calls == [
            call(mock_acct, {'foo': 'bar'}, datetime(2020, 5, 25, 0, 0, 0))
        ]

    def test_exception(self):
        mock_get = Mock()
        type(self.mock_client).Transactions = mock_get
        exc = RuntimeError('foo')
        mock_get.get.side_effect = exc
        mock_acct = Mock(plaid_token='tkn', id=5)
        type(mock_acct).name = 'acct1'
        with patch(f'{pb}._stmt_for_acct') as m_sfa:
            m_sfa.return_value = ('mysid', 3, 7)
            with patch(f'{pbm}.dtnow') as m_dtnow:
                m_dtnow.return_value = datetime(2020, 5, 25, 0, 0, 0)
                res = self.cls._do_acct(mock_acct, 15)
        assert isinstance(res, PlaidUpdateResult)
        assert res.account == mock_acct
        assert res.updated == 0
        assert res.added == 0
        assert res.success is False
        assert res.exc == exc
        assert res.stmt_id is None
        assert mock_get.mock_calls == [
            call.get('tkn', '2020-05-10', '2020-05-25')
        ]
        assert m_sfa.mock_calls == []


class TestStmtForAcct(PlaidUpdaterTester):

    def test_credit(self):
        mock_acct = Mock(id=5)
        type(mock_acct).name = 'acct5'
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        txns = {
            'item': {
                'institution_id': 'abc123'
            },
            'accounts': [
                {
                    'type': 'credit',
                    'balances': {
                        'iso_currency_code': 'USD'
                    },
                    'mask': '012345'
                }
            ]
        }
        mock_stmt = Mock(id=123)
        with patch.multiple(
            pb,
            _update_bank_or_credit=DEFAULT,
            _update_investment=DEFAULT,
            _new_updated_counts=DEFAULT
        ) as mocks:
            mocks['_new_updated_counts'].return_value = (1, 2)
            with patch(f'{pbm}.OFXStatement') as m_ofxstmt:
                with patch(f'{pbm}.db_session') as m_dbsess:
                    m_ofxstmt.return_value = mock_stmt
                    res = self.cls._stmt_for_acct(mock_acct, txns, end_dt)
        assert res == (123, 1, 2)
        assert mocks['_update_bank_or_credit'].mock_calls == [
            call(end_dt, mock_acct, txns['accounts'][0], txns, mock_stmt)
        ]
        assert mocks['_update_investment'].mock_calls == []
        assert mocks['_new_updated_counts'].mock_calls == [call()]
        assert m_ofxstmt.mock_calls == [
            call(
                account_id=5,
                filename='Plaid_acct5_1590379200.ofx',
                file_mtime=end_dt,
                as_of=end_dt,
                currency='USD',
                acctid='012345'
            )
        ]
        assert mock_stmt.bankid == 'abc123'
        assert mock_stmt.type == 'CreditCard'
        assert m_dbsess.mock_calls == [call.commit()]

    def test_investment(self):
        mock_acct = Mock(id=5)
        type(mock_acct).name = 'acct5'
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        txns = {
            'item': {
                'institution_id': None
            },
            'accounts': [
                {
                    'type': 'investment',
                    'balances': {
                        'iso_currency_code': 'USD'
                    },
                    'mask': '012345'
                }
            ]
        }
        mock_stmt = Mock(id=123)
        with patch.multiple(
            pb,
            _update_bank_or_credit=DEFAULT,
            _update_investment=DEFAULT,
            _new_updated_counts=DEFAULT
        ) as mocks:
            mocks['_new_updated_counts'].return_value = (1, 2)
            with patch(f'{pbm}.OFXStatement') as m_ofxstmt:
                with patch(f'{pbm}.db_session') as m_dbsess:
                    m_ofxstmt.return_value = mock_stmt
                    res = self.cls._stmt_for_acct(mock_acct, txns, end_dt)
        assert res == (123, 1, 2)
        assert mocks['_update_bank_or_credit'].mock_calls == []
        assert mocks['_update_investment'].mock_calls == [
            call(end_dt, mock_acct, txns['accounts'][0], mock_stmt)
        ]
        assert mocks['_new_updated_counts'].mock_calls == [call()]
        assert m_ofxstmt.mock_calls == [
            call(
                account_id=5,
                filename='Plaid_acct5_1590379200.ofx',
                file_mtime=end_dt,
                as_of=end_dt,
                currency='USD',
                acctid='012345'
            )
        ]
        assert mock_stmt.type == 'Investment'
        assert m_dbsess.mock_calls == [call.commit()]

    def test_unknown_type(self):
        mock_acct = Mock(id=5)
        type(mock_acct).name = 'acct5'
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        txns = {
            'item': {
                'institution_id': None
            },
            'accounts': [
                {
                    'type': 'foo',
                    'balances': {
                        'iso_currency_code': 'USD'
                    },
                    'mask': '012345'
                }
            ]
        }
        mock_stmt = Mock(id=123)
        with patch.multiple(
            pb,
            _update_bank_or_credit=DEFAULT,
            _update_investment=DEFAULT,
            _new_updated_counts=DEFAULT
        ) as mocks:
            mocks['_new_updated_counts'].return_value = (1, 2)
            with patch(f'{pbm}.OFXStatement') as m_ofxstmt:
                with patch(f'{pbm}.db_session') as m_dbsess:
                    m_ofxstmt.return_value = mock_stmt
                    with pytest.raises(RuntimeError) as exc:
                        self.cls._stmt_for_acct(mock_acct, txns, end_dt)
        assert str(exc.value) == 'ERROR: Unknown account type: foo'
        assert mocks['_update_bank_or_credit'].mock_calls == []
        assert mocks['_update_investment'].mock_calls == []
        assert mocks['_new_updated_counts'].mock_calls == []
        assert m_ofxstmt.mock_calls == [
            call(
                account_id=5,
                filename='Plaid_acct5_1590379200.ofx',
                file_mtime=end_dt,
                as_of=end_dt,
                currency='USD',
                acctid='012345'
            )
        ]
        assert m_dbsess.mock_calls == []


class TestNewUpdatedCounts(PlaidUpdaterTester):

    def test_none(self):
        mock_sess = Mock(dirty=[Mock()], new=['foo', 1])
        with patch(f'{pbm}.db_session', mock_sess):
            res = self.cls._new_updated_counts()
        assert res == (0, 0)

    def test_some(self):
        mock_sess = Mock(
            dirty=[Mock(), OFXTransaction()],
            new=['foo', OFXTransaction(), 1, OFXTransaction()]
        )
        with patch(f'{pbm}.db_session', mock_sess):
            res = self.cls._new_updated_counts()
        assert res == (2, 1)


class TestUpdateBankOrCredit(PlaidUpdaterTester):

    def test_happy_path(self):
        mock_stmt = Mock(avail_bal=None, avail_bal_as_of=None)
        mock_acct = Mock(id=4)
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        acct = {
            'balances': {
                'current': '1234.5678',
                'iso_currency_code': 'USD',
                'available': 854.2903
            }
        }
        txns = {
            'total_transactions': 3,
            'transactions': [
                {
                    'pending': True,
                },
                {
                    'pending': False,
                    'amount': 123.4567,
                    'date': '2020-02-23',
                    'payment_meta': {
                        'reference_number': None
                    },
                    'name': 'Some Txn',
                    'transaction_id': 'TXN001'
                },
                {
                    'pending': False,
                    'amount': 482.86392,
                    'date': '2020-03-15',
                    'payment_meta': {
                        'reference_number': '456def'
                    },
                    'name': 'Other Txn',
                    'transaction_id': 'TXN002'
                }
            ]
        }
        with patch(f'{pbm}.db_session') as mock_db:
            with patch(f'{pbm}.upsert_record') as mock_upsert:
                self.cls._update_bank_or_credit(
                    end_dt, mock_acct, acct, txns, mock_stmt
                )
        assert mock_stmt.as_of == end_dt
        assert mock_stmt.ledger_bal == Decimal('1234.57')
        assert mock_stmt.ledger_bal_as_of == end_dt
        assert mock_stmt.avail_bal == Decimal('854.29')
        assert mock_stmt.avail_bal_as_of == end_dt
        assert mock_stmt.currency == 'USD'
        assert mock_db.mock_calls == [call.add(mock_stmt)]
        assert mock_acct.mock_calls == [
            call.set_balance(
                overall_date=end_dt,
                ledger=Decimal('1234.57'),
                ledger_date=end_dt,
                avail=Decimal('854.29'),
                avail_date=end_dt
            )
        ]
        assert mock_upsert.mock_calls == [
            call(
                OFXTransaction,
                ['account_id', 'fitid'],
                amount=Decimal('123.46'),
                date_posted=datetime(2020, 2, 23, 0, 0, 0, tzinfo=UTC),
                fitid='TXN001',
                name='Some Txn',
                account_id=4,
                statement=mock_stmt
            ),
            call(
                OFXTransaction,
                ['account_id', 'fitid'],
                amount=Decimal('482.86'),
                date_posted=datetime(2020, 3, 15, 0, 0, 0, tzinfo=UTC),
                fitid='456def',
                name='Other Txn',
                account_id=4,
                statement=mock_stmt
            )
        ]

    def test_no_transactions(self):
        mock_stmt = Mock(avail_bal=None, avail_bal_as_of=None)
        mock_acct = Mock(id=4)
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        acct = {
            'balances': {
                'current': '1234.5678',
                'iso_currency_code': 'USD'
            }
        }
        txns = {
            'total_transactions': 0,
            'transactions': []
        }
        with patch(f'{pbm}.db_session') as mock_db:
            with patch(f'{pbm}.upsert_record') as mock_upsert:
                self.cls._update_bank_or_credit(
                    end_dt, mock_acct, acct, txns, mock_stmt
                )
        assert mock_stmt.as_of == end_dt
        assert mock_stmt.ledger_bal == Decimal('1234.57')
        assert mock_stmt.ledger_bal_as_of == end_dt
        assert mock_stmt.currency == 'USD'
        assert mock_db.mock_calls == [call.add(mock_stmt)]
        assert mock_acct.mock_calls == [
            call.set_balance(
                overall_date=end_dt,
                ledger=Decimal('1234.57'),
                ledger_date=end_dt,
                avail=None,
                avail_date=None
            )
        ]
        assert mock_upsert.mock_calls == []

    def test_wrong_num_of_transactions(self):
        mock_stmt = Mock(avail_bal=None, avail_bal_as_of=None)
        mock_acct = Mock(id=4)
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        acct = {
            'balances': {
                'current': '1234.5678',
                'iso_currency_code': 'USD'
            }
        }
        txns = {
            'total_transactions': 0,
            'transactions': [
                {'foo': 'bar'}
            ]
        }
        with patch(f'{pbm}.db_session') as mock_db:
            with patch(f'{pbm}.upsert_record') as mock_upsert:
                with pytest.raises(RuntimeError) as exc:
                    self.cls._update_bank_or_credit(
                        end_dt, mock_acct, acct, txns, mock_stmt
                    )
        assert str(exc.value) == 'ERROR: Plaid response indicates 0 ' \
                                 'total transactions but only contains ' \
                                 '1 transactions.'
        assert mock_stmt.as_of == end_dt
        assert mock_stmt.ledger_bal == Decimal('1234.57')
        assert mock_stmt.ledger_bal_as_of == end_dt
        assert mock_stmt.currency == 'USD'
        assert mock_db.mock_calls == [call.add(mock_stmt)]
        assert mock_acct.mock_calls == [
            call.set_balance(
                overall_date=end_dt,
                ledger=Decimal('1234.57'),
                ledger_date=end_dt,
                avail=None,
                avail_date=None
            )
        ]
        assert mock_upsert.mock_calls == []


class TestUpdateInvestment(PlaidUpdaterTester):

    def test_happy_path(self):
        mock_stmt = Mock()
        mock_acct = Mock()
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        acct = {
            'balances': {
                'current': '1234.5678',
                'iso_currency_code': 'USD'
            }
        }
        with patch(f'{pbm}.db_session') as mock_db:
            self.cls._update_investment(end_dt, mock_acct, acct, mock_stmt)
        assert mock_stmt.as_of == end_dt
        assert mock_stmt.ledger_bal == Decimal('1234.57')
        assert mock_stmt.ledger_bal_as_of == end_dt
        assert mock_stmt.currency == 'USD'
        assert mock_db.mock_calls == [call.add(mock_stmt)]
        assert mock_acct.mock_calls == [
            call.set_balance(
                overall_date=end_dt,
                ledger=Decimal('1234.57'),
                ledger_date=end_dt
            )
        ]
