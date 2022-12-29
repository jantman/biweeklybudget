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
from biweeklybudget.models.plaid_items import PlaidItem
from biweeklybudget.models.plaid_accounts import PlaidAccount
from plaid.api.plaid_api import PlaidApi
from datetime import datetime, date
from decimal import Decimal
from pytz import UTC

from unittest.mock import Mock, patch, call, MagicMock, DEFAULT
import pytest

pbm = 'biweeklybudget.plaid_updater'
pb = f'{pbm}.PlaidUpdater'


class TestPlaidUpdateResult:

    def test_happy_path(self):
        item = Mock(spec_set=PlaidItem)
        type(item).item_id = 4
        r = PlaidUpdateResult(
            item, True, 1, 2, 'foo', [123]
        )
        assert r.item == item
        assert r.success is True
        assert r.updated == 1
        assert r.added == 2
        assert r.exc == 'foo'
        assert r.stmt_ids == [123]
        assert r.as_dict == {
            'item_id': 4,
            'success': True,
            'exception': 'foo',
            'statement_ids': [123],
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


class TestAvailableItems:

    def test_happy_path(self):
        items = [
            Mock(id=1),
            Mock(id=2)
        ]
        mock_name = Mock()
        mock_item = Mock(institution_name=mock_name)
        with patch(f'{pbm}.db_session') as mock_db:
            with patch(f'{pbm}.PlaidItem', mock_item):
                mock_db.query.return_value.order_by.return_value.all\
                    .return_value = items
                res = PlaidUpdater.available_items()
        assert res == items
        assert mock_db.mock_calls == [
            call.query(mock_item),
            call.query().order_by(mock_name),
            call.query().order_by().all()
        ]


class PlaidUpdaterTester:

    def setup_method(self):
        self.mock_client = MagicMock()
        with patch(f'{pbm}.plaid_client') as m_pc:
            m_pc.return_value = self.mock_client
            self.cls = PlaidUpdater()


class TestUpdate(PlaidUpdaterTester):

    def test_accounts_none(self):
        item1 = Mock()
        item2 = Mock()
        item3 = Mock()
        items = [item1, item2, item3]
        res1 = Mock()
        res2 = Mock()
        res3 = Mock()
        results = [res1, res2, res3]
        with patch(f'{pb}.available_items') as m_avail:
            m_avail.return_value = items
            with patch(f'{pb}._do_item') as m_do_item:
                m_do_item.side_effect = results
                res = self.cls.update()
        assert res == results
        assert m_avail.mock_calls == [call()]
        assert m_do_item.mock_calls == [
            call(item1, days=30),
            call(item2, days=30),
            call(item3, days=30)
        ]

    def test_accounts_specified(self):
        item1 = Mock()
        item2 = Mock()
        item3 = Mock()
        items = [item1, item2, item3]
        res1 = Mock()
        res3 = Mock()
        results = [res1, res3]
        with patch(f'{pb}.available_items') as m_avail:
            m_avail.return_value = items
            with patch(f'{pb}._do_item') as m_do_item:
                m_do_item.side_effect = results
                res = self.cls.update(items=[item1, item3], days=10)
        assert res == results
        assert m_avail.mock_calls == []
        assert m_do_item.mock_calls == [
            call(item1, days=10),
            call(item3, days=10)
        ]


class TestDoItem(PlaidUpdaterTester):

    def test_happy_path(self):
        acctA = Mock(spec_set=Account)
        acctB = Mock(spec_set=Account)
        accts = [
            Mock(
                spec_set=PlaidAccount, item_id='Item1', account_id=1,
                account=acctA
            ),
            Mock(
                spec_set=PlaidAccount, item_id='Item1', account_id=3,
                account=acctB
            ),
        ]
        mock_item = Mock(
            item_id='Item1', access_token='Token1',
            last_updated=datetime(2019, 1, 1, 1, 1, 1)
        )
        self.mock_client.item_get.return_value = {
            'item': {},
            'status': {'transactions': {'foo': 'bar'}}
        }
        txns = [
            [
                {'account_id': 1, 'amount': 10},
                {'account_id': 1, 'amount': 11},
                {'account_id': 3, 'amount': 30}
            ],
            {
                1: {'account_id': 1, 'foo': 'bar'},
                3: {'account_id': 3, 'baz': 'blam'}
            }
        ]

        mock_igr = Mock()

        def se_sfa(_, acct, *args):
            if acct['account_id'] == 1:
                return 'sid1', 1, 4
            return 'sid2', 2, 3

        with patch.multiple(
            pbm,
            db_session=DEFAULT,
            PlaidAccount=DEFAULT,
            dtnow=DEFAULT,
            ItemGetRequest=DEFAULT,
        ) as mocks:
            mocks['db_session'].query.return_value.filter. \
                return_value.all.return_value = accts
            mocks['ItemGetRequest'].return_value = mock_igr
            with patch(f'{pb}._stmt_for_acct') as m_sfa:
                m_sfa.side_effect = se_sfa
                mocks['dtnow'].return_value = datetime(2020, 5, 25, 0, 0, 0)
                with patch(f'{pb}._get_transactions') as m_gt:
                    m_gt.return_value = txns
                    res = self.cls._do_item(mock_item, 15)
        assert isinstance(res, PlaidUpdateResult)
        assert res.item == mock_item
        assert res.updated == 7
        assert res.added == 3
        assert res.success is True
        assert res.exc is None
        assert res.stmt_ids == ['sid1', 'sid2']
        assert m_sfa.mock_calls == [
            call(
                acctA,
                {'account_id': 1, 'foo': 'bar'},
                [
                    {'account_id': 1, 'amount': 10},
                    {'account_id': 1, 'amount': 11},
                ],
                datetime(2020, 5, 25, 0, 0, 0)
            ),
            call(
                acctB,
                {'account_id': 3, 'baz': 'blam'},
                [
                    {'account_id': 3, 'amount': 30}
                ],
                datetime(2020, 5, 25, 0, 0, 0)
            )
        ]
        assert mock_item.last_updated == datetime(2020, 5, 25, 0, 0, 0)
        assert mocks['db_session'].mock_calls == [
            call.query(mocks['PlaidAccount']),
            call.query().filter(False),
            call.query().filter().all(),
            call.add(mock_item),
            call.commit()
        ]
        assert mocks['ItemGetRequest'].mock_calls == [
            call(access_token='Token1')
        ]
        assert m_gt.mock_calls == [
            call(
                'Token1',
                datetime(2020, 5, 10, 0, 0, 0),
                datetime(2020, 5, 25, 0, 0, 0)
            )
        ]

    def test_acct_none(self):
        acctA = Mock(spec_set=Account)
        accts = [
            Mock(
                spec_set=PlaidAccount, item_id='Item1', account_id=1,
                account=acctA
            ),
            Mock(
                spec_set=PlaidAccount, item_id='Item1', account_id=3,
                account=None
            ),
        ]
        mock_item = Mock(
            item_id='Item1', access_token='Token1',
            last_updated=datetime(2019, 1, 1, 1, 1, 1)
        )
        self.mock_client.item_get.return_value = {
            'item': {},
            'status': {'transactions': {'foo': 'bar'}}
        }
        txns = [
            [
                {'account_id': 1, 'amount': 10},
                {'account_id': 1, 'amount': 11},
                {'account_id': 3, 'amount': 30}
            ],
            {
                1: {'account_id': 1, 'foo': 'bar'},
                3: {'account_id': 3, 'baz': 'blam'}
            }
        ]

        mock_igr = Mock()

        def se_sfa(_, acct, *args):
            if acct['account_id'] == 1:
                return 'sid1', 1, 4
            return 'sid2', 2, 3

        with patch.multiple(
            pbm,
            db_session=DEFAULT,
            PlaidAccount=DEFAULT,
            dtnow=DEFAULT,
            ItemGetRequest=DEFAULT,
        ) as mocks:
            mocks['db_session'].query.return_value.filter.\
                return_value.all.return_value = accts
            mocks['ItemGetRequest'].return_value = mock_igr
            with patch(f'{pb}._stmt_for_acct') as m_sfa:
                m_sfa.side_effect = se_sfa
                mocks['dtnow'].return_value = datetime(2020, 5, 25, 0, 0, 0)
                with patch(f'{pb}._get_transactions') as m_gt:
                    m_gt.return_value = txns
                    res = self.cls._do_item(mock_item, 15)
        assert isinstance(res, PlaidUpdateResult)
        assert res.item == mock_item
        assert res.updated == 4
        assert res.added == 1
        assert res.success is True
        assert res.exc is None
        assert res.stmt_ids == ['sid1']
        assert m_sfa.mock_calls == [
            call(
                acctA,
                {'account_id': 1, 'foo': 'bar'},
                [
                    {'account_id': 1, 'amount': 10},
                    {'account_id': 1, 'amount': 11},
                ],
                datetime(2020, 5, 25, 0, 0, 0)
            )
        ]
        assert mock_item.last_updated == datetime(2020, 5, 25, 0, 0, 0)
        assert mocks['db_session'].mock_calls == [
            call.query(mocks['PlaidAccount']),
            call.query().filter(False),
            call.query().filter().all(),
            call.add(mock_item),
            call.commit()
        ]
        assert mocks['ItemGetRequest'].mock_calls == [
            call(access_token='Token1')
        ]
        assert m_gt.mock_calls == [
            call(
                'Token1',
                datetime(2020, 5, 10, 0, 0, 0),
                datetime(2020, 5, 25, 0, 0, 0)
            )
        ]

    def test_exception(self):
        acctA = Mock(spec_set=Account)
        acctB = Mock(spec_set=Account)
        accts = [
            Mock(
                spec_set=PlaidAccount, item_id='Item1', account_id=1,
                account=acctA
            ),
            Mock(
                spec_set=PlaidAccount, item_id='Item1', account_id=3,
                account=acctB
            ),
        ]
        mock_item = Mock(
            item_id='Item1', access_token='Token1',
            last_updated=datetime(2019, 1, 1, 1, 1, 1)
        )
        self.mock_client.item_get.return_value = {
            'item': {},
            'status': {'transactions': {'foo': 'bar'}}
        }
        txns = [
            [
                {'account_id': 1, 'amount': 10},
                {'account_id': 1, 'amount': 11},
                {'account_id': 3, 'amount': 30}
            ],
            {
                1: {'account_id': 1, 'foo': 'bar'},
                3: {'account_id': 3, 'baz': 'blam'}
            }
        ]

        mock_igr = Mock()

        def se_sfa(_, acct, *args):
            if acct['account_id'] == 1:
                return 'sid1', 1, 4
            return 'sid2', 2, 3

        ex = RuntimeError('foo')
        with patch.multiple(
            pbm,
            db_session=DEFAULT,
            PlaidAccount=DEFAULT,
            dtnow=DEFAULT,
            ItemGetRequest=DEFAULT,
        ) as mocks:
            mocks['db_session'].query.return_value.filter. \
                return_value.all.return_value = accts
            mocks['ItemGetRequest'].return_value = mock_igr
            with patch(f'{pb}._stmt_for_acct') as m_sfa:
                m_sfa.side_effect = se_sfa
                mocks['dtnow'].return_value = datetime(2020, 5, 25, 0, 0, 0)
                with patch(f'{pb}._get_transactions') as m_gt:
                    m_gt.side_effect = ex
                    res = self.cls._do_item(mock_item, 15)
        assert isinstance(res, PlaidUpdateResult)
        assert res.item == mock_item
        assert res.updated == 0
        assert res.added == 0
        assert res.success is False
        assert res.exc == ex
        assert res.stmt_ids is None
        assert m_sfa.mock_calls == []
        assert mocks['db_session'].mock_calls == []
        assert mocks['ItemGetRequest'].mock_calls == [
            call(access_token='Token1')
        ]
        assert m_gt.mock_calls == [
            call(
                'Token1',
                datetime(2020, 5, 10, 0, 0, 0),
                datetime(2020, 5, 25, 0, 0, 0)
            )
        ]


class TestGetTransactions(PlaidUpdaterTester):

    def test_happy_path_no_paginate(self):
        self.mock_client.transactions_get.return_value = {
            'transactions': [
                {'trans': 1}, {'trans': 2}, {'trans': 3}
            ],
            'accounts': [
                {'account_id': 1, 'foo': 'bar'},
                {'account_id': 3, 'baz': 'blam'}
            ],
            'total_transactions': 3
        }

        mock_tgr1 = Mock()
        mock_tgro1 = Mock()

        with patch.multiple(
            pbm,
            TransactionsGetRequest=DEFAULT,
            TransactionsGetRequestOptions=DEFAULT,
        ) as mocks:
            mocks['TransactionsGetRequest'].side_effect = [mock_tgr1]
            mocks['TransactionsGetRequestOptions'].side_effect = [mock_tgro1]
            res = self.cls._get_transactions(
                'aToken', datetime(2020, 5, 10, 0, 0, 0),
                datetime(2020, 5, 25, 0, 0, 0)
            )
        assert res == (
            [{'trans': 1}, {'trans': 2}, {'trans': 3}],
            {
                1: {'account_id': 1, 'foo': 'bar'},
                3: {'account_id': 3, 'baz': 'blam'}
            }
        )
        assert mocks['TransactionsGetRequest'].mock_calls == [
            call(
                access_token='aToken',
                start_date=date(2020, 5, 10),
                end_date=date(2020, 5, 25),
                options=mock_tgro1
            )
        ]
        assert mocks['TransactionsGetRequestOptions'].mock_calls == [call()]

    def test_happy_path_paginate(self):
        self.mock_client.transactions_get.side_effect = [
            {
                'transactions': [
                    {'trans': 1}, {'trans': 2}
                ],
                'accounts': [
                    {'account_id': 1, 'foo': 'bar'},
                    {'account_id': 3, 'baz': 'blam'}
                ],
                'total_transactions': 5
            },
            {
                'transactions': [
                    {'trans': 3}, {'trans': 4}
                ],
                'accounts': [
                    {'account_id': 1, 'foo': 'bar'},
                    {'account_id': 3, 'baz': 'blam'}
                ],
                'total_transactions': 5
            },
            {
                'transactions': [
                    {'trans': 5}
                ],
                'accounts': [
                    {'account_id': 1, 'foo': 'bar'},
                    {'account_id': 3, 'baz': 'blam'}
                ],
                'total_transactions': 5
            },
        ]

        mock_tgr1 = Mock()
        mock_tgro1 = Mock()
        mock_tgr2 = Mock()
        mock_tgro2 = Mock()
        mock_tgr3 = Mock()
        mock_tgro3 = Mock()

        with patch.multiple(
            pbm,
            TransactionsGetRequest=DEFAULT,
            TransactionsGetRequestOptions=DEFAULT,
        ) as mocks:
            mocks['TransactionsGetRequest'].side_effect = [
                mock_tgr1, mock_tgr2, mock_tgr3
            ]
            mocks['TransactionsGetRequestOptions'].side_effect = [
                mock_tgro1, mock_tgro2, mock_tgro3
            ]
            res = self.cls._get_transactions(
                'aToken', datetime(2020, 5, 10, 0, 0, 0),
                datetime(2020, 5, 25, 0, 0, 0)
            )
        assert res == (
            [
                {'trans': 1}, {'trans': 2}, {'trans': 3}, {'trans': 4},
                {'trans': 5}
            ],
            {
                1: {'account_id': 1, 'foo': 'bar'},
                3: {'account_id': 3, 'baz': 'blam'}
            }
        )
        assert mocks['TransactionsGetRequest'].mock_calls == [
            call(
                access_token='aToken',
                start_date=date(2020, 5, 10),
                end_date=date(2020, 5, 25),
                options=mock_tgro1
            ),
            call(
                access_token='aToken',
                start_date=date(2020, 5, 10),
                end_date=date(2020, 5, 25),
                options=mock_tgro2
            ),
            call(
                access_token='aToken',
                start_date=date(2020, 5, 10),
                end_date=date(2020, 5, 25),
                options=mock_tgro3
            )
        ]
        assert mocks['TransactionsGetRequestOptions'].mock_calls == [
            call(), call(offset=2), call(offset=4)
        ]


class TestStmtForAcct(PlaidUpdaterTester):

    def test_credit(self):
        mock_item = Mock(institution_id='abc123')
        mock_plaid_account = Mock(
            account_type='credit', plaid_item=mock_item
        )
        mock_acct = Mock(id=5, plaid_account=mock_plaid_account)
        type(mock_acct).name = 'acct5'
        end_dt = datetime(2020, 5, 25, 0, 0, 0, tzinfo=UTC)
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
        pai = {
            'mask': 'XXXX',
            'balances': {
                'iso_currency_code': 'USD'
            }
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
                    res = self.cls._stmt_for_acct(mock_acct, pai, txns, end_dt)
        assert res == (123, 1, 2)
        assert mocks['_update_bank_or_credit'].mock_calls == [
            call(end_dt, mock_acct, pai, txns, mock_stmt)
        ]
        assert mocks['_update_investment'].mock_calls == []
        assert mocks['_new_updated_counts'].mock_calls == [call()]
        assert m_ofxstmt.mock_calls == [
            call(
                account_id=5,
                filename='Plaid_acct5_1590364800.ofx',
                file_mtime=end_dt,
                as_of=end_dt,
                currency='USD',
                acctid='XXXX'
            )
        ]
        assert mock_stmt.bankid == 'abc123'
        assert mock_stmt.type == 'CreditCard'
        assert m_dbsess.mock_calls == [call.commit()]

    def test_depository(self):
        mock_item = Mock(institution_id='abc123')
        mock_plaid_account = Mock(
            account_type='depository', plaid_item=mock_item
        )
        mock_acct = Mock(id=5, plaid_account=mock_plaid_account)
        type(mock_acct).name = 'acct5'
        end_dt = datetime(2020, 5, 25, 0, 0, 0, tzinfo=UTC)
        txns = {
            'item': {
                'institution_id': 'abc123'
            },
            'accounts': [
                {
                    'type': 'depository',
                    'subtype': 'checking',
                    'balances': {
                        'iso_currency_code': 'USD'
                    },
                    'mask': '012345'
                }
            ]
        }
        pai = {
            'mask': 'XXXX',
            'balances': {
                'iso_currency_code': 'USD'
            }
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
                    res = self.cls._stmt_for_acct(mock_acct, pai, txns, end_dt)
        assert res == (123, 1, 2)
        assert mocks['_update_bank_or_credit'].mock_calls == [
            call(end_dt, mock_acct, pai, txns, mock_stmt)
        ]
        assert mocks['_update_investment'].mock_calls == []
        assert mocks['_new_updated_counts'].mock_calls == [call()]
        assert m_ofxstmt.mock_calls == [
            call(
                account_id=5,
                filename='Plaid_acct5_1590364800.ofx',
                file_mtime=end_dt,
                as_of=end_dt,
                currency='USD',
                acctid='XXXX'
            )
        ]
        assert mock_stmt.bankid == 'abc123'
        assert mock_stmt.type == 'Bank'
        assert m_dbsess.mock_calls == [call.commit()]

    def test_investment(self):
        mock_item = Mock(institution_id='abc123')
        mock_plaid_account = Mock(
            account_type='investment', plaid_item=mock_item
        )
        mock_acct = Mock(id=5, plaid_account=mock_plaid_account)
        type(mock_acct).name = 'acct5'
        end_dt = datetime(2020, 5, 25, 0, 0, 0, tzinfo=UTC)
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
        pai = {
            'mask': 'XXXX',
            'balances': {
                'iso_currency_code': 'USD'
            }
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
                    res = self.cls._stmt_for_acct(mock_acct, pai, txns, end_dt)
        assert res == (123, 1, 2)
        assert mocks['_update_bank_or_credit'].mock_calls == []
        assert mocks['_update_investment'].mock_calls == [
            call(end_dt, mock_acct, pai, mock_stmt)
        ]
        assert mocks['_new_updated_counts'].mock_calls == [call()]
        assert m_ofxstmt.mock_calls == [
            call(
                account_id=5,
                filename='Plaid_acct5_1590364800.ofx',
                file_mtime=end_dt,
                as_of=end_dt,
                currency='USD',
                acctid='XXXX'
            )
        ]
        assert mock_stmt.type == 'Investment'
        assert m_dbsess.mock_calls == [call.commit()]

    def test_loan(self):
        mock_item = Mock(institution_id='abc123')
        mock_plaid_account = Mock(
            account_type='loan', plaid_item=mock_item
        )
        mock_acct = Mock(id=5, plaid_account=mock_plaid_account)
        type(mock_acct).name = 'acct5'
        end_dt = datetime(2020, 5, 25, 0, 0, 0, tzinfo=UTC)
        txns = {
            'item': {
                'institution_id': None
            },
            'accounts': [
                {
                    'type': 'loan',
                    'balances': {
                        'iso_currency_code': 'USD'
                    },
                    'mask': '012345'
                }
            ]
        }
        pai = {
            'mask': 'XXXX',
            'balances': {
                'iso_currency_code': 'USD'
            }
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
                    res = self.cls._stmt_for_acct(mock_acct, pai, txns, end_dt)
        assert res == (123, 1, 2)
        assert mocks['_update_bank_or_credit'].mock_calls == []
        assert mocks['_update_investment'].mock_calls == [
            call(end_dt, mock_acct, pai, mock_stmt)
        ]
        assert mocks['_new_updated_counts'].mock_calls == [call()]
        assert m_ofxstmt.mock_calls == [
            call(
                account_id=5,
                filename='Plaid_acct5_1590364800.ofx',
                file_mtime=end_dt,
                as_of=end_dt,
                currency='USD',
                acctid='XXXX'
            )
        ]
        assert mock_stmt.type == 'Investment'
        assert m_dbsess.mock_calls == [call.commit()]

    def test_unknown_type(self):
        mock_item = Mock(institution_id='abc123')
        mock_plaid_account = Mock(
            account_type='FooBarBaz', plaid_item=mock_item
        )
        mock_acct = Mock(id=5, plaid_account=mock_plaid_account)
        type(mock_acct).name = 'acct5'
        end_dt = datetime(2020, 5, 25, 0, 0, 0, tzinfo=UTC)
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
        pai = {
            'mask': 'XXXX',
            'balances': {
                'iso_currency_code': 'USD'
            }
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
                        self.cls._stmt_for_acct(mock_acct, pai, txns, end_dt)
        assert str(exc.value) == 'ERROR: Unknown account type: FooBarBaz'
        assert mocks['_update_bank_or_credit'].mock_calls == []
        assert mocks['_update_investment'].mock_calls == []
        assert mocks['_new_updated_counts'].mock_calls == []
        assert m_ofxstmt.mock_calls == [
            call(
                account_id=5,
                filename='Plaid_acct5_1590364800.ofx',
                file_mtime=end_dt,
                as_of=end_dt,
                currency='USD',
                acctid='XXXX'
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
        mock_acct = Mock(id=4, negate_ofx_amounts=False)
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        acct = {
            'balances': {
                'current': '1234.5678',
                'iso_currency_code': 'USD',
                'available': 854.2903
            }
        }
        txns = [
            {
                'pending': True,
            },
            {
                'pending': False,
                'amount': 123.4567,
                'date': date(2020, 2, 23),
                'payment_meta': {
                    'reference_number': None
                },
                'name': 'Some Txn',
                'transaction_id': 'TXN001'
            },
            {
                'pending': False,
                'amount': 482.86392,
                'date': date(2020, 3, 15),
                'payment_meta': {
                    'reference_number': '456def'
                },
                'name': 'Other Txn',
                'transaction_id': 'TXN002'
            }
        ]
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

    def test_negate_amounts(self):
        mock_stmt = Mock(avail_bal=None, avail_bal_as_of=None)
        mock_acct = Mock(id=4, negate_ofx_amounts=True)
        end_dt = datetime(2020, 5, 25, 0, 0, 0)
        acct = {
            'balances': {
                'current': '1234.5678',
                'iso_currency_code': 'USD',
                'available': 854.2903
            }
        }
        txns = [
            {
                'pending': True,
            },
            {
                'pending': False,
                'amount': 123.4567,
                'date': date(2020, 2, 23),
                'payment_meta': {
                    'reference_number': None
                },
                'name': 'Some Txn',
                'transaction_id': 'TXN001'
            },
            {
                'pending': False,
                'amount': 482.86392,
                'date': date(2020, 3, 15),
                'payment_meta': {
                    'reference_number': '456def'
                },
                'name': 'Other Txn',
                'transaction_id': 'TXN002'
            }
        ]
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
                amount=Decimal('-123.46'),
                date_posted=datetime(2020, 2, 23, 0, 0, 0, tzinfo=UTC),
                fitid='TXN001',
                name='Some Txn',
                account_id=4,
                statement=mock_stmt
            ),
            call(
                OFXTransaction,
                ['account_id', 'fitid'],
                amount=Decimal('-482.86'),
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
        txns = []
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
