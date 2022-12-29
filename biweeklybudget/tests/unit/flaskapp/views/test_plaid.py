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

from textwrap import dedent
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch, call, DEFAULT
from plaid import ApiException
from plaid.models import LinkTokenCreateResponse

from biweeklybudget import settings
from biweeklybudget.version import VERSION
from biweeklybudget.flaskapp.views.plaid import (
    PlaidJs, PlaidPublicToken, PlaidHandleLink, set_url_rules,
    PlaidConfigJS, PlaidUpdate, PlaidRefreshAccounts,
    PlaidUpdateItemInfo, PlaidLinkToken
)
from biweeklybudget.utils import dtnow
from biweeklybudget.models.account import Account
from biweeklybudget.models.plaid_items import PlaidItem
from biweeklybudget.models.plaid_accounts import PlaidAccount

pbm = 'biweeklybudget.flaskapp.views.plaid'


class TestSetUrlRules:

    def test_rules(self):
        m_phl_view = Mock()
        m_ppt_view = Mock()
        m_pjs_view = Mock()
        m_pu_view = Mock()
        m_pra_view = Mock()
        m_puii_view = Mock()
        m_plt_view = Mock()
        m_app = Mock()
        with patch.multiple(
            pbm,
            PlaidHandleLink=DEFAULT,
            PlaidPublicToken=DEFAULT,
            PlaidJs=DEFAULT,
            PlaidUpdate=DEFAULT,
            PlaidRefreshAccounts=DEFAULT,
            PlaidUpdateItemInfo=DEFAULT,
            PlaidLinkToken=DEFAULT,
            new_callable=MagicMock
        ) as mocks:
            mocks['PlaidHandleLink'].return_value = m_phl_view
            mocks['PlaidPublicToken'].as_view.return_value = m_ppt_view
            mocks['PlaidJs'].as_view.return_value = m_pjs_view
            mocks['PlaidUpdate'].as_view.return_value = m_pu_view
            mocks['PlaidRefreshAccounts'].return_value = m_pra_view
            mocks['PlaidUpdateItemInfo'].return_value = m_puii_view
            mocks['PlaidLinkToken'].return_value = m_plt_view
            set_url_rules(m_app)
        assert m_app.mock_calls == [
            call.add_url_rule(
                '/ajax/plaid/handle_link',
                view_func=mocks['PlaidHandleLink'].as_view('plaid_handle_link')
            ),
            call.add_url_rule(
                '/ajax/plaid/create_public_token',
                view_func=m_ppt_view
            ),
            call.add_url_rule(
                '/plaid.js',
                view_func=m_pjs_view
            ),
            call.add_url_rule(
                '/plaid-update',
                view_func=m_pu_view
            ),
            call.add_url_rule(
                '/ajax/plaid/refresh_item_accounts',
                view_func=mocks['PlaidRefreshAccounts'].as_view(
                    'plaid_refresh_item_accounts'
                )
            ),
            call.add_url_rule(
                '/ajax/plaid/update_item_info',
                view_func=mocks['PlaidUpdateItemInfo'].as_view(
                    'plaid_update_item_info'
                )
            ),
            call.add_url_rule(
                '/ajax/plaid/create_link_token',
                view_func=mocks['PlaidLinkToken'].as_view(
                    'plaid_link_token'
                )
            )
        ]


class TestPlaidJs:

    @patch.dict('os.environ', {}, clear=True)
    def test_normal(self):
        with patch(f'{pbm}.redirect') as m_redir:
            m_redir.side_effect = lambda x: x
            res = PlaidJs().get()
        assert res == 'static/js/plaid_prod.js'


class TestPlaidHandleLink:

    @patch.dict('os.environ', {}, clear=True)
    def test_normal(self):
        mock_json = Mock()
        mock_ipter = Mock()
        mock_req = MagicMock()
        mock_req.get_json.return_value = {
            'public_token': 'pubToken',
            'metadata': {
                'institution': {
                    'name': 'Inst1',
                    'institution_id': 'IID1'
                },
                'accounts': [
                    {
                        'id': 'AID1',
                        'name': 'Name1',
                        'mask': 'XXX1',
                        'type': 'depository',
                        'subtype': 'checking'
                    },
                    {
                        'id': 'AID2',
                        'name': 'Name2',
                        'mask': 'XXX2',
                        'type': 'credit'
                    }
                ]
            }
        }
        mock_client = MagicMock()
        mock_client.item_public_token_exchange.return_value = {
            'item_id': 'itemId',
            'access_token': 'accToken'
        }
        mock_sess = Mock()

        m_item1 = Mock()
        m_acct1 = Mock()
        m_acct2 = Mock()

        def se_item(**kwargs):
            return m_item1

        def se_acct(**kwargs):
            if kwargs['account_id'] == 'AID1':
                return m_acct1
            return m_acct2

        with patch.multiple(
            pbm,
            jsonify=DEFAULT,
            request=mock_req,
            plaid_client=DEFAULT,
            PlaidItem=DEFAULT,
            PlaidAccount=DEFAULT,
            ItemPublicTokenExchangeRequest=DEFAULT,
            db_session=mock_sess
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['PlaidItem'].side_effect = se_item
            mocks['PlaidAccount'].side_effect = se_acct
            mocks['ItemPublicTokenExchangeRequest'].return_value = mock_ipter
            res = PlaidHandleLink().post()
        assert res == mock_json
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().item_public_token_exchange(mock_ipter)
        ]
        assert mocks['ItemPublicTokenExchangeRequest'].mock_calls == [
            call(public_token='pubToken')
        ]
        assert mock_client.mock_calls == [
            call.item_public_token_exchange(mock_ipter)
        ]
        assert mocks['jsonify'].mock_calls == [
            call({
                'success': True,
                'item_id': 'itemId',
                'access_token': 'accToken'
            })
        ]
        assert mock_json.mock_calls == []
        assert mock_sess.mock_calls == [
            call.add(m_item1),
            call.add(m_acct1),
            call.add(m_acct2),
            call.commit()
        ]
        assert mocks['PlaidItem'].mock_calls == [
            call(
                item_id='itemId',
                access_token='accToken',
                last_updated=datetime(
                    2017, 7, 28, 6, 24, 44, tzinfo=timezone.utc
                ),
                institution_name='Inst1',
                institution_id='IID1'
            )
        ]
        assert mocks['PlaidAccount'].mock_calls == [
            call(
                item_id='itemId',
                account_id='AID1',
                name='Name1',
                mask='XXX1',
                account_type='depository',
                account_subtype='checking'
            ),
            call(
                item_id='itemId',
                account_id='AID2',
                name='Name2',
                mask='XXX2',
                account_type='credit',
                account_subtype='unknown'
            )
        ]

    @patch.dict('os.environ', {}, clear=True)
    def test_exception(self):
        mock_json = Mock()
        mock_ipter = Mock()
        mock_req = MagicMock()
        mock_req.get_json.return_value = {
            'public_token': 'pubToken',
            'metadata': {
                'institution': {
                    'name': 'Inst1',
                    'institution_id': 'IID1'
                },
                'accounts': [
                    {
                        'id': 'AID1',
                        'name': 'Name1',
                        'mask': 'XXX1',
                        'type': 'depository',
                        'subtype': 'checking'
                    },
                    {
                        'id': 'AID2',
                        'name': 'Name2',
                        'mask': 'XXX2',
                        'type': 'credit'
                    }
                ]
            }
        }
        mock_client = MagicMock()
        mock_client.item_public_token_exchange.side_effect = ApiException(
            reason='foo', status=123
        )
        mock_sess = Mock()

        m_item1 = Mock()
        m_acct1 = Mock()
        m_acct2 = Mock()

        def se_item(**kwargs):
            return m_item1

        def se_acct(**kwargs):
            if kwargs['account_id'] == 'AID1':
                return m_acct1
            return m_acct2

        with patch.multiple(
            pbm,
            jsonify=DEFAULT,
            request=mock_req,
            plaid_client=DEFAULT,
            PlaidItem=DEFAULT,
            PlaidAccount=DEFAULT,
            ItemPublicTokenExchangeRequest=DEFAULT,
            db_session=mock_sess
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['PlaidItem'].side_effect = se_item
            mocks['PlaidAccount'].side_effect = se_acct
            mocks['ItemPublicTokenExchangeRequest'].return_value = mock_ipter
            res = PlaidHandleLink().post()
        assert res == mock_json
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().item_public_token_exchange(mock_ipter)
        ]
        assert mocks['ItemPublicTokenExchangeRequest'].mock_calls == [
            call(public_token='pubToken')
        ]
        assert mock_client.mock_calls == [
            call.item_public_token_exchange(mock_ipter)
        ]
        assert mocks['jsonify'].mock_calls == [
            call({
                'success': False,
                'message': 'Exception: (123)\nReason: foo\n'
            })
        ]
        assert mock_json.mock_calls == []
        assert mock_json.status_code == 400
        assert mock_sess.mock_calls == []
        assert mocks['PlaidItem'].mock_calls == []
        assert mocks['PlaidAccount'].mock_calls == []


class TestPlaidPublicToken:

    @patch.dict('os.environ', {}, clear=True)
    def test_normal(self):
        mock_json = Mock()
        mock_req = Mock(form={'item_id': 'Item1'})
        mock_client = MagicMock()
        mock_client.Item.public_token.create.return_value = {
            'create': 'response'
        }
        mock_item = Mock(item_id='Item1', access_token='aToken')
        mock_db = Mock()
        mock_query = Mock()
        mock_query.get.return_value = mock_item
        mock_db.query.return_value = mock_query
        with patch(f'{pbm}.db_session', mock_db):
            with patch(f'{pbm}.jsonify') as m_jsonify:
                m_jsonify.return_value = mock_json
                with patch(f'{pbm}.request', mock_req):
                    with patch(f'{pbm}.plaid_client') as m_client:
                        m_client.return_value = mock_client
                        res = PlaidPublicToken().post()
        assert res == mock_json
        assert m_jsonify.mock_calls == [
            call({'create': 'response'})
        ]
        assert mock_json.mock_calls == []
        assert m_client.mock_calls == [
            call(),
            call().Item.public_token.create('aToken')
        ]
        assert mock_db.mock_calls == [
            call.query(PlaidItem),
            call.query().get('Item1')
        ]

    @patch.dict('os.environ', {}, clear=True)
    def test_exception(self):
        mock_json = Mock()
        mock_req = Mock(form={'item_id': 'Item1'})
        mock_client = MagicMock()
        mock_client.Item.public_token.create.side_effect = ApiException(
            reason='some error message',
            status=999,
        )
        mock_item = Mock(item_id='Item1', access_token='aToken')
        mock_db = Mock()
        mock_query = Mock()
        mock_query.get.return_value = mock_item
        mock_db.query.return_value = mock_query
        with patch(f'{pbm}.db_session', mock_db):
            with patch(f'{pbm}.jsonify') as m_jsonify:
                m_jsonify.return_value = mock_json
                with patch(f'{pbm}.request', mock_req):
                    with patch(f'{pbm}.plaid_client') as m_client:
                        m_client.return_value = mock_client
                        res = PlaidPublicToken().post()
        assert res == mock_json
        assert m_jsonify.mock_calls == [
            call({
                'success': False,
                'message': 'Exception: (999)\nReason: some error message\n'
            })
        ]
        assert mock_json.mock_calls == []
        assert mock_json.status_code == 400
        assert m_client.mock_calls == [
            call(),
            call().Item.public_token.create('aToken')
        ]
        assert mock_db.mock_calls == [
            call.query(PlaidItem),
            call.query().get('Item1')
        ]


class TestPlaidRefreshAccounts:

    @patch.dict('os.environ', {}, clear=True)
    def test_normal(self):
        mock_json = Mock()
        mock_req = MagicMock()
        mock_req.get_json.return_value = {
            'item_id': 'IID1'
        }
        mock_client = MagicMock()
        mock_client.accounts_get.return_value = {
            'accounts': [
                {
                    'account_id': 'AID1',
                    'name': 'Name1',
                    'mask': 'XXX1',
                    'type': 'depository',
                    'subtype': 'checking',
                },
                {
                    'account_id': 'AID2',
                    'name': 'Name2',
                    'mask': 'XXX2',
                    'type': 'depository',
                    'subtype': 'savings',
                },
                {
                    'account_id': 'AID3',
                    'name': 'Name3',
                    'mask': 'XXX3',
                    'type': 'credit',
                }
            ]
        }
        m_acct1 = Mock(account_id='AID1')
        m_acct2 = Mock(account_id='AID2')
        m_acct3 = Mock(account_id='AID3')
        m_acct4 = Mock(account_id='AID4')
        mock_item = Mock(
            item_id='IID1', access_token='accToken',
            all_accounts=[m_acct2, m_acct4]
        )

        m_agr = Mock()

        def se_item(**kwargs):
            return mock_item

        def se_acct(**kwargs):
            if kwargs['account_id'] == 'AID1':
                return m_acct1
            if kwargs['account_id'] == 'AID2':
                return m_acct2
            if kwargs['account_id'] == 'AID3':
                return m_acct3

        mock_sess = MagicMock()
        mock_sess.query.return_value.get.return_value = mock_item

        with patch.multiple(
                pbm,
                jsonify=DEFAULT,
                request=mock_req,
                plaid_client=DEFAULT,
                PlaidItem=DEFAULT,
                PlaidAccount=DEFAULT,
                AccountsGetRequest=DEFAULT,
                db_session=mock_sess
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['PlaidItem'].side_effect = se_item
            mocks['PlaidAccount'].side_effect = se_acct
            mocks['AccountsGetRequest'].return_value = m_agr
            res = PlaidRefreshAccounts().post()
        assert res == mock_json
        assert mocks['AccountsGetRequest'].mock_calls == [
            call(access_token='accToken')
        ]
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().accounts_get(m_agr)
        ]
        assert mock_client.mock_calls == [
            call.accounts_get(m_agr)
        ]
        assert mocks['jsonify'].mock_calls == [
            call({'success': True})
        ]
        assert mock_json.mock_calls == []
        assert mock_sess.mock_calls == [
            call.query(mocks['PlaidItem']),
            call.query().get('IID1'),
            call.add(m_acct1),
            call.add(m_acct3),
            call.delete(m_acct4),
            call.commit()
        ]
        assert mocks['PlaidItem'].mock_calls == []
        assert mocks['PlaidAccount'].mock_calls == [
            call(
                item_id='IID1',
                account_id='AID1',
                name='Name1',
                mask='XXX1',
                account_type='depository',
                account_subtype='checking'
            ),
            call(
                item_id='IID1',
                account_id='AID3',
                name='Name3',
                mask='XXX3',
                account_type='credit',
                account_subtype='unknown'
            )
        ]

    @patch.dict('os.environ', {}, clear=True)
    def test_exception(self):
        mock_json = Mock()
        mock_req = MagicMock()
        mock_req.get_json.return_value = {
            'item_id': 'IID1'
        }
        mock_client = MagicMock()
        mock_client.accounts_get.side_effect = ApiException(
            reason='fooerror', status=500
        )
        m_acct1 = Mock(account_id='AID1')
        m_acct2 = Mock(account_id='AID2')
        m_acct3 = Mock(account_id='AID3')
        m_acct4 = Mock(account_id='AID4')
        mock_item = Mock(
            item_id='IID1', access_token='accToken',
            all_accounts=[m_acct2, m_acct4]
        )

        m_agr = Mock()

        def se_item(**kwargs):
            return mock_item

        def se_acct(**kwargs):
            if kwargs['account_id'] == 'AID1':
                return m_acct1
            if kwargs['account_id'] == 'AID2':
                return m_acct2
            if kwargs['account_id'] == 'AID3':
                return m_acct3

        mock_sess = MagicMock()
        mock_sess.query.return_value.get.return_value = mock_item

        with patch.multiple(
                pbm,
                jsonify=DEFAULT,
                request=mock_req,
                plaid_client=DEFAULT,
                PlaidItem=DEFAULT,
                PlaidAccount=DEFAULT,
                AccountsGetRequest=DEFAULT,
                db_session=mock_sess
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['PlaidItem'].side_effect = se_item
            mocks['PlaidAccount'].side_effect = se_acct
            mocks['AccountsGetRequest'].return_value = m_agr
            res = PlaidRefreshAccounts().post()
        assert res == mock_json
        assert mocks['AccountsGetRequest'].mock_calls == [
            call(access_token='accToken')
        ]
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().accounts_get(m_agr)
        ]
        assert mock_client.mock_calls == [
            call.accounts_get(m_agr)
        ]
        assert mocks['jsonify'].mock_calls == [
            call({
                'success': False,
                'message': 'Exception: (500)\nReason: fooerror\n'
            })
        ]
        assert mock_json.mock_calls == []
        assert mock_sess.mock_calls == [
            call.query(mocks['PlaidItem']),
            call.query().get('IID1')
        ]
        assert mocks['PlaidItem'].mock_calls == []
        assert mocks['PlaidAccount'].mock_calls == []


class TestPlaidUpdateItemInfo:

    @patch.dict('os.environ', {}, clear=True)
    def test_normal(self):
        mock_json = Mock()
        mock_client = MagicMock()
        m_item1 = Mock(item_id='IID1', access_token='accToken1')
        m_item2 = Mock(item_id='IID2', access_token='accToken2')
        m_item3 = Mock(item_id='IID3', access_token='accToken3')

        mock_sess = MagicMock()
        mock_sess.query.return_value.all.return_value = [
            m_item1, m_item2, m_item3
        ]

        m_at1 = Mock(access_token='accToken1')
        m_at2 = Mock(access_token='accToken2')
        m_at3 = Mock(access_token='accToken3')

        m_iid1 = Mock(institution_id='inst1')
        m_iid2 = Mock(institution_id='inst2')

        def se_igr(access_token=None):
            if access_token == 'accToken1':
                return m_at1
            if access_token == 'accToken2':
                return m_at2
            if access_token == 'accToken3':
                return m_at3

        def se_igbir(institution_id=None, country_codes=None):
            if institution_id == 'inst1':
                return m_iid1
            if institution_id == 'inst2':
                return m_iid2

        def se_get(igr):
            if igr.access_token == 'accToken1':
                return {
                    'item': {
                        'institution_id': 'inst1'
                    }
                }
            if igr.access_token == 'accToken2':
                return {
                    'item': {
                        'institution_id': 'inst2'
                    }
                }
            if igr.access_token == 'accToken3':
                return {
                    'item': {
                        'institution_id': 'inst1'
                    }
                }

        mock_client.item_get.side_effect = se_get

        def se_inst(data):
            if data.institution_id == 'inst1':
                return {
                    'institution': {
                        'name': 'name1'
                    }
                }
            if data.institution_id == 'inst2':
                return {
                    'institution': {
                        'name': 'name2'
                    }
                }

        mock_client.institutions_get_by_id.side_effect = se_inst

        with patch.multiple(
                pbm,
                jsonify=DEFAULT,
                plaid_client=DEFAULT,
                PlaidItem=DEFAULT,
                PlaidAccount=DEFAULT,
                ItemGetRequest=DEFAULT,
                InstitutionsGetByIdRequest=DEFAULT,
                db_session=mock_sess
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['ItemGetRequest'].side_effect = se_igr
            mocks['InstitutionsGetByIdRequest'].side_effect = se_igbir
            res = PlaidUpdateItemInfo().post()
        assert res == mock_json
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().item_get(m_at1),
            call().institutions_get_by_id(m_iid1),
            call().item_get(m_at2),
            call().institutions_get_by_id(m_iid2),
            call().item_get(m_at3),
            call().institutions_get_by_id(m_iid1),
        ]
        assert m_item1.institution_id == 'inst1'
        assert m_item1.institution_name == 'name1'
        assert m_item2.institution_id == 'inst2'
        assert m_item2.institution_name == 'name2'
        assert m_item3.institution_id == 'inst1'
        assert m_item3.institution_name == 'name1'
        assert mocks['jsonify'].mock_calls == [
            call({'success': True})
        ]
        assert mock_json.mock_calls == []
        assert mock_sess.mock_calls == [
            call.query(mocks['PlaidItem']),
            call.query().all(),
            call.add(m_item1),
            call.add(m_item2),
            call.add(m_item3),
            call.commit()
        ]
        assert mocks['PlaidItem'].mock_calls == []
        assert mocks['PlaidAccount'].mock_calls == []

    @patch.dict('os.environ', {}, clear=True)
    def test_exception(self):
        mock_json = Mock()
        mock_client = MagicMock()
        m_item1 = Mock(item_id='IID1', access_token='accToken1')
        m_item2 = Mock(item_id='IID2', access_token='accToken2')
        m_item3 = Mock(item_id='IID3', access_token='accToken3')

        mock_sess = MagicMock()
        mock_sess.query.return_value.all.return_value = [
            m_item1, m_item2, m_item3
        ]

        m_at1 = Mock(access_token='accToken1')
        m_at2 = Mock(access_token='accToken2')
        m_at3 = Mock(access_token='accToken3')

        m_iid1 = Mock(institution_id='inst1')
        m_iid2 = Mock(institution_id='inst2')

        def se_igr(access_token=None):
            if access_token == 'accToken1':
                return m_at1
            if access_token == 'accToken2':
                return m_at2
            if access_token == 'accToken3':
                return m_at3

        def se_igbir(institution_id=None, country_codes=None):
            if institution_id == 'inst1':
                return m_iid1
            if institution_id == 'inst2':
                return m_iid2

        def se_get(igr):
            if igr.access_token == 'accToken1':
                return {
                    'item': {
                        'institution_id': 'inst1'
                    }
                }
            if igr.access_token == 'accToken2':
                raise ApiException(
                    reason='foo', status=123
                )
            if igr.access_token == 'accToken3':
                return {
                    'item': {
                        'institution_id': 'inst1'
                    }
                }

        mock_client.item_get.side_effect = se_get

        def se_inst(data):
            if data.institution_id == 'inst1':
                return {
                    'institution': {
                        'name': 'name1'
                    }
                }
            if data.institution_id == 'inst2':
                return {
                    'institution': {
                        'name': 'name2'
                    }
                }

        mock_client.institutions_get_by_id.side_effect = se_inst

        with patch.multiple(
                pbm,
                jsonify=DEFAULT,
                plaid_client=DEFAULT,
                PlaidItem=DEFAULT,
                PlaidAccount=DEFAULT,
                ItemGetRequest=DEFAULT,
                InstitutionsGetByIdRequest=DEFAULT,
                db_session=mock_sess
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['ItemGetRequest'].side_effect = se_igr
            mocks['InstitutionsGetByIdRequest'].side_effect = se_igbir
            res = PlaidUpdateItemInfo().post()
        assert res == mock_json
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().item_get(m_at1),
            call().institutions_get_by_id(m_iid1),
            call().item_get(m_at2),
        ]
        assert m_item1.institution_id == 'inst1'
        assert m_item1.institution_name == 'name1'
        assert mocks['jsonify'].mock_calls == [
            call({
                'success': False,
                'message': 'Exception: (123)\nReason: foo\n'
            })
        ]
        assert mock_json.mock_calls == []
        assert mock_sess.mock_calls == [
            call.query(mocks['PlaidItem']),
            call.query().all(),
            call.add(m_item1),
        ]
        assert mocks['PlaidItem'].mock_calls == []
        assert mocks['PlaidAccount'].mock_calls == []


class TestPlaidConfigJS:

    def test_happy_path(self):
        assert PlaidConfigJS().get() == dedent(f"""
        // generated by utils.PlaidConfigJS
        var BIWEEKLYBUDGET_VERSION = "{VERSION}";
        var PLAID_ENV = "{settings.PLAID_ENV}";
        var PLAID_PRODUCTS = "{settings.PLAID_PRODUCTS}";
        var PLAID_COUNTRY_CODES = "{settings.PLAID_COUNTRY_CODES}";
        """)


class TestPlaidUpdate:

    pb = f'{pbm}.PlaidUpdate'

    def setup_method(self):
        self.cls = PlaidUpdate()

    def test_post(self):
        mock_update = Mock()
        mock_request = Mock(form=None, args={'account_ids': 'id1,id2'})
        with patch(f'{pbm}.request', mock_request):
            with patch(f'{self.pb}._update') as m_update:
                with patch(f'{pbm}.jsonify') as m_jsonify:
                    m_update.return_value = mock_update
                    res = self.cls.post()
        assert res == mock_update
        assert m_update.mock_calls == [call('id1,id2')]
        assert m_jsonify.mock_calls == []

    def test_post_form(self):
        mock_update = Mock()
        mock_request = Mock(
            form={'item_id3': 'foo', 'item_id4': 'bar'}, args={}
        )
        with patch(f'{pbm}.request', mock_request):
            with patch(f'{self.pb}._update') as m_update:
                with patch(f'{pbm}.jsonify') as m_jsonify:
                    m_update.return_value = mock_update
                    res = self.cls.post()
        assert res == mock_update
        assert m_update.mock_calls == [call('id3,id4')]
        assert m_jsonify.mock_calls == []

    def test_post_ids_none(self):
        mock_update = Mock()
        mock_request = Mock(args={}, form={})
        with patch(f'{pbm}.request', mock_request):
            with patch(f'{self.pb}._update') as m_update:
                with patch(f'{pbm}.jsonify') as m_jsonify:
                    m_update.return_value = mock_update
                    res = self.cls.post()
        assert res == (m_jsonify.return_value, 400)
        assert m_update.mock_calls == []
        assert m_jsonify.mock_calls == [
            call({
                'success': False, 'message': 'Missing parameter: account_ids'
            })
        ]

    def test_get_form(self):
        mock_req = Mock(args={})
        mock_form = Mock()
        mock_update = Mock()
        with patch(f'{self.pb}._form', autospec=True) as m_form:
            m_form.return_value = mock_form
            with patch(f'{self.pb}._update', autospec=True) as m_update:
                m_update.return_value = mock_update
                with patch(f'{pbm}.request', mock_req):
                    res = self.cls.get()
        assert res == mock_form
        assert m_form.mock_calls == [call(self.cls)]
        assert m_update.mock_calls == []

    def test_get_update(self):
        mock_req = Mock(args={'account_ids': '1,2,3'})
        mock_form = Mock()
        mock_update = Mock()
        with patch(f'{self.pb}._form', autospec=True) as m_form:
            m_form.return_value = mock_form
            with patch(f'{self.pb}._update', autospec=True) as m_update:
                m_update.return_value = mock_update
                with patch(f'{pbm}.request', mock_req):
                    res = self.cls.get()
        assert res == mock_update
        assert m_form.mock_calls == []
        assert m_update.mock_calls == [call(self.cls, '1,2,3')]

    def test_form(self):
        accts = [
            Mock(spec_set=Account, id='AID1'),
            Mock(spec_set=Account, id='AID2')
        ]
        type(accts[0]).name = 'AName1'
        type(accts[1]).name = 'AName2'
        plaid_accts = [
            Mock(spec_set=PlaidAccount, mask='XXX1', account=accts[0]),
            Mock(spec_set=PlaidAccount, mask='XXX2', account=None),
            Mock(spec_set=PlaidAccount, mask='XXX3', account=accts[1]),
        ]
        type(plaid_accts[0]).name = 'Acct1'
        type(plaid_accts[1]).name = 'Acct2'
        type(plaid_accts[2]).name = 'Acct3'
        items = [
            Mock(
                spec_set=PlaidItem, item_id='Item1',
                all_accounts=[plaid_accts[0], plaid_accts[1]]
            ),
            Mock(
                spec_set=PlaidItem, item_id='Item2',
                all_accounts=[plaid_accts[2]]
            )
        ]
        rendered = Mock()
        mock_db = Mock()
        mock_query = Mock()
        mock_query.all.return_value = items
        mock_db.query.return_value = mock_query
        with patch(f'{pbm}.db_session', mock_db):
            with patch(f'{pbm}.render_template') as m_render:
                m_render.return_value = rendered
                res = self.cls._form()
        assert res == rendered
        assert m_render.mock_calls == [
            call(
                'plaid_form.html',
                plaid_items=items,
                plaid_accounts={
                    'Item1': 'Acct1 (XXX1), Acct2 (XXX2)',
                    'Item2': 'Acct3 (XXX3)'
                },
                accounts={
                    'Item1': 'AName1 (AID1)',
                    'Item2': 'AName2 (AID2)'
                }
            )
        ]

    def test_update_template(self):
        mock_req = Mock(headers={})
        accts = [
            Mock(spec_set=Account, id='AID1'),
            Mock(spec_set=Account, id='AID2')
        ]
        type(accts[0]).name = 'AName1'
        type(accts[1]).name = 'AName2'
        plaid_accts = [
            Mock(spec_set=PlaidAccount, mask='XXX1', account=accts[0]),
            Mock(spec_set=PlaidAccount, mask='XXX2', account=None),
            Mock(spec_set=PlaidAccount, mask='XXX3', account=accts[1]),
        ]
        type(plaid_accts[0]).name = 'Acct1'
        type(plaid_accts[1]).name = 'Acct2'
        type(plaid_accts[2]).name = 'Acct3'
        items = [
            Mock(
                spec_set=PlaidItem, item_id='Item1',
                all_accounts=[plaid_accts[0], plaid_accts[1]]
            ),
            Mock(
                spec_set=PlaidItem, item_id='Item2',
                all_accounts=[plaid_accts[2]]
            )
        ]

        def db_get(_id):
            if _id == 'Item1':
                return items[0]
            if _id == 'Item2':
                return items[1]

        mock_db = Mock()
        mock_query = Mock()
        mock_query.get.side_effect = db_get
        mock_db.query.return_value = mock_query
        mock_updater = Mock(db=mock_db)
        rendered = Mock()
        mock_json = Mock()
        result = [
            Mock(success=True, updated=1, added=1, as_dict='res1'),
            Mock(success=False, updated=0, added=0, as_dict='res2'),
            Mock(success=True, updated=2, added=4, as_dict='res3')
        ]
        mock_updater.update.return_value = result
        with patch.multiple(
            pbm,
            PlaidUpdater=DEFAULT,
            render_template=DEFAULT,
            jsonify=DEFAULT
        ) as mocks:
            mocks['PlaidUpdater'].return_value = mock_updater
            mocks['PlaidUpdater'].available_items.return_value = items
            mocks['render_template'].return_value = rendered
            mocks['jsonify'].return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                res = self.cls._update('ALL')
        assert res == rendered
        assert mocks['PlaidUpdater'].mock_calls == [
            call(),
            call.available_items(),
            call().update(items=items)
        ]
        assert mock_updater.mock_calls == [
            call.update(items=items)
        ]
        assert mocks['render_template'].mock_calls == [call(
            'plaid_result.html',
            results=result,
            num_added=5,
            num_updated=3,
            num_failed=1
        )]
        assert mocks['jsonify'].mock_calls == []

    def test_update_json(self):
        mock_req = Mock(headers={'accept': 'application/json'})
        accts = [
            Mock(spec_set=Account, id='AID1'),
            Mock(spec_set=Account, id='AID2')
        ]
        type(accts[0]).name = 'AName1'
        type(accts[1]).name = 'AName2'
        plaid_accts = [
            Mock(spec_set=PlaidAccount, mask='XXX1', account=accts[0]),
            Mock(spec_set=PlaidAccount, mask='XXX2', account=None),
            Mock(spec_set=PlaidAccount, mask='XXX3', account=accts[1]),
        ]
        type(plaid_accts[0]).name = 'Acct1'
        type(plaid_accts[1]).name = 'Acct2'
        type(plaid_accts[2]).name = 'Acct3'
        items = [
            Mock(
                spec_set=PlaidItem, item_id='Item1',
                all_accounts=[plaid_accts[0], plaid_accts[1]]
            ),
            Mock(
                spec_set=PlaidItem, item_id='Item2',
                all_accounts=[plaid_accts[2]]
            )
        ]

        def db_get(_id):
            if _id == 'Item1':
                return items[0]
            if _id == 'Item2':
                return items[1]

        mock_db = Mock()
        mock_query = Mock()
        mock_query.get.side_effect = db_get
        mock_db.query.return_value = mock_query
        mock_updater = Mock()
        rendered = Mock()
        mock_json = Mock()
        result = [
            Mock(success=True, updated=1, added=2, as_dict='res1')
        ]
        mock_updater.update.return_value = result
        with patch.multiple(
            pbm,
            PlaidUpdater=DEFAULT,
            render_template=DEFAULT,
            jsonify=DEFAULT
        ) as mocks:
            mocks['PlaidUpdater'].return_value = mock_updater
            mocks['PlaidUpdater'].available_accounts.return_value = items
            mocks['render_template'].return_value = rendered
            mocks['jsonify'].return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                with patch(f'{pbm}.db_session', mock_db):
                    res = self.cls._update('Item1')
        assert res == mock_json
        assert mocks['PlaidUpdater'].mock_calls == [
            call(),
            call().update(items=[items[0]])
        ]
        assert mock_updater.mock_calls == [
            call.update(items=[items[0]])
        ]
        assert mocks['render_template'].mock_calls == []
        assert mocks['jsonify'].mock_calls == [
            call(['res1'])
        ]
        assert mock_db.mock_calls == [
            call.query(PlaidItem),
            call.query().get('Item1'),
        ]

    def test_update_plain(self):
        mock_req = Mock(headers={'accept': 'text/plain'})
        accts = [
            Mock(spec_set=Account, id='AID1'),
            Mock(spec_set=Account, id='AID2')
        ]
        type(accts[0]).name = 'AName1'
        type(accts[1]).name = 'AName2'
        plaid_accts = [
            Mock(spec_set=PlaidAccount, mask='XXX1', account=accts[0]),
            Mock(spec_set=PlaidAccount, mask='XXX2', account=None),
            Mock(spec_set=PlaidAccount, mask='XXX3', account=accts[1]),
        ]
        type(plaid_accts[0]).name = 'Acct1'
        type(plaid_accts[1]).name = 'Acct2'
        type(plaid_accts[2]).name = 'Acct3'
        items = [
            Mock(
                spec_set=PlaidItem, item_id='Item1',
                all_accounts=[plaid_accts[0], plaid_accts[1]],
                institution_name='InstName1'
            ),
            Mock(
                spec_set=PlaidItem, item_id='Item2',
                all_accounts=[plaid_accts[2]],
                institution_name='InstName2'
            )
        ]

        def db_get(_id):
            if _id == 'Item1':
                return items[0]
            if _id == 'Item2':
                return items[1]

        mock_db = Mock()
        mock_query = Mock()
        mock_query.get.side_effect = db_get
        mock_db.query.return_value = mock_query
        mock_updater = Mock()
        rendered = Mock()
        mock_json = Mock()
        result = [
            Mock(
                success=True, updated=1, added=2, as_dict='res1',
                stmt_ids='SID1,SID2,SID3', item=items[0]
            ),
            Mock(
                success=False, item=items[1], exc='MyException'
            )
        ]
        mock_updater.update.return_value = result
        with patch.multiple(
            pbm,
            PlaidUpdater=DEFAULT,
            render_template=DEFAULT,
            jsonify=DEFAULT
        ) as mocks:
            mocks['PlaidUpdater'].return_value = mock_updater
            mocks['PlaidUpdater'].available_accounts.return_value = items
            mocks['render_template'].return_value = rendered
            mocks['jsonify'].return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                with patch(f'{pbm}.db_session', mock_db):
                    res = self.cls._update('Item1')
        assert res == "InstName1 (Item1): 1 updated, 2 added (stmts: SID1," \
                      "SID2,SID3)\nInstName2 (Item2): Failed: MyException\n" \
                      "TOTAL: 1 updated, 2 added, 1 account(s) failed"
        assert mocks['PlaidUpdater'].mock_calls == [
            call(),
            call().update(items=[items[0]])
        ]
        assert mock_updater.mock_calls == [
            call.update(items=[items[0]])
        ]
        assert mocks['render_template'].mock_calls == []
        assert mocks['jsonify'].mock_calls == []
        assert mock_db.mock_calls == [
            call.query(PlaidItem),
            call.query().get('Item1'),
        ]


class TestPlaidLinkToken:

    @patch.dict('os.environ', {}, clear=True)
    def test_initial_link(self):
        mock_req = Mock()
        mock_req.get_json.return_value = {}
        mock_json = Mock()
        mock_client = MagicMock()
        link_token = 'fooToken'
        expiration = dtnow() + timedelta(hours=1)
        req_id = 'requestId'
        mock_client.link_token_create.return_value = LinkTokenCreateResponse(
            link_token, expiration, req_id
        )
        mock_product = Mock()
        mock_country = Mock()
        mock_ltcr = Mock()
        mock_user = Mock()

        mock_sess = MagicMock()

        with patch.multiple(
            pbm,
            request=mock_req,
            jsonify=DEFAULT,
            plaid_client=DEFAULT,
            LinkTokenCreateRequest=DEFAULT,
            PlaidItem=DEFAULT,
            Products=DEFAULT,
            CountryCode=DEFAULT,
            LinkTokenCreateRequestUser=DEFAULT,
            db_session=mock_sess,
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['LinkTokenCreateRequest'].return_value = mock_ltcr
            mocks['Products'].return_value = mock_product
            mocks['CountryCode'].return_value = mock_country
            mocks['LinkTokenCreateRequestUser'].return_value = mock_user
            res = PlaidLinkToken().post()
        assert res == mock_json
        assert mocks['jsonify'].mock_calls == [
            call({'link_token': 'fooToken'})
        ]

        assert mock_json.mock_calls == []
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().link_token_create(mock_ltcr)
        ]
        assert mocks['Products'].mock_calls == [call('transactions')]
        assert mocks['CountryCode'].mock_calls == [call('US')]
        assert mocks['LinkTokenCreateRequestUser'].mock_calls == [
            call(client_user_id='1')
        ]
        assert mocks['LinkTokenCreateRequest'].mock_calls == [
            call(
                products=[mock_product],
                client_name=f'github.com/jantman/biweeklybudget {VERSION}',
                country_codes=[mock_country],
                language='en',
                user=mock_user,
            )
        ]
        assert mock_sess.mock_calls == []

    @patch.dict('os.environ', {}, clear=True)
    def test_update(self):
        mock_req = Mock()
        mock_req.get_json.return_value = {'item_id': 'IID1'}
        mock_json = Mock()
        mock_client = MagicMock()
        link_token = 'fooToken'
        expiration = dtnow() + timedelta(hours=1)
        req_id = 'requestId'
        mock_client.link_token_create.return_value = LinkTokenCreateResponse(
            link_token, expiration, req_id
        )
        mock_product = Mock()
        mock_country = Mock()
        mock_ltcr = Mock()
        mock_user = Mock()
        mock_item = Mock(
            item_id='IID1', access_token='accToken', all_accounts=[]
        )

        mock_sess = MagicMock()
        mock_sess.query.return_value.get.return_value = mock_item

        def se_item(**kwargs):
            return mock_item

        with patch.multiple(
            pbm,
            request=mock_req,
            jsonify=DEFAULT,
            plaid_client=DEFAULT,
            LinkTokenCreateRequest=DEFAULT,
            Products=DEFAULT,
            CountryCode=DEFAULT,
            PlaidItem=DEFAULT,
            LinkTokenCreateRequestUser=DEFAULT,
            db_session=mock_sess,
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['LinkTokenCreateRequest'].return_value = mock_ltcr
            mocks['Products'].return_value = mock_product
            mocks['CountryCode'].return_value = mock_country
            mocks['LinkTokenCreateRequestUser'].return_value = mock_user
            mocks['PlaidItem'].side_effect = se_item
            res = PlaidLinkToken().post()
        assert res == mock_json
        assert mocks['jsonify'].mock_calls == [
            call({'link_token': 'fooToken'})
        ]

        assert mock_json.mock_calls == []
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().link_token_create(mock_ltcr)
        ]
        assert mocks['Products'].mock_calls == [call('transactions')]
        assert mocks['CountryCode'].mock_calls == [call('US')]
        assert mocks['LinkTokenCreateRequestUser'].mock_calls == [
            call(client_user_id='1')
        ]
        assert mocks['LinkTokenCreateRequest'].mock_calls == [
            call(
                products=[mock_product],
                client_name=f'github.com/jantman/biweeklybudget {VERSION}',
                country_codes=[mock_country],
                language='en',
                user=mock_user,
                access_token='accToken'
            )
        ]
        assert mock_sess.mock_calls == [
            call.query(mocks['PlaidItem']),
            call.query().get('IID1')
        ]

    @patch.dict('os.environ', {}, clear=True)
    def test_initial_link_exception(self):
        mock_req = Mock()
        mock_req.get_json.return_value = {}
        mock_json = Mock()
        mock_client = MagicMock()
        mock_client.link_token_create.side_effect = ApiException(
            reason='some error message',
            status=999,
        )
        mock_product = Mock()
        mock_country = Mock()
        mock_ltcr = Mock()
        mock_user = Mock()

        mock_sess = MagicMock()

        with patch.multiple(
            pbm,
            request=mock_req,
            jsonify=DEFAULT,
            plaid_client=DEFAULT,
            LinkTokenCreateRequest=DEFAULT,
            Products=DEFAULT,
            PlaidItem=DEFAULT,
            CountryCode=DEFAULT,
            LinkTokenCreateRequestUser=DEFAULT,
            db_session=mock_sess,
        ) as mocks:
            mocks['jsonify'].return_value = mock_json
            mocks['plaid_client'].return_value = mock_client
            mocks['LinkTokenCreateRequest'].return_value = mock_ltcr
            mocks['Products'].return_value = mock_product
            mocks['CountryCode'].return_value = mock_country
            mocks['LinkTokenCreateRequestUser'].return_value = mock_user
            res = PlaidLinkToken().post()
        assert res == mock_json
        assert mocks['jsonify'].mock_calls == [
            call({
                'success': False,
                'message': 'Exception: (999)\nReason: some error message\n'
            })
        ]
        assert mock_json.mock_calls == []
        assert mock_json.status_code == 400
        assert mocks['plaid_client'].mock_calls == [
            call(),
            call().link_token_create(mock_ltcr)
        ]
        assert mocks['Products'].mock_calls == [call('transactions')]
        assert mocks['CountryCode'].mock_calls == [call('US')]
        assert mocks['LinkTokenCreateRequestUser'].mock_calls == [
            call(client_user_id='1')
        ]
        assert mocks['LinkTokenCreateRequest'].mock_calls == [
            call(
                products=[mock_product],
                client_name=f'github.com/jantman/biweeklybudget {VERSION}',
                country_codes=[mock_country],
                language='en',
                user=mock_user,
            )
        ]
        assert mock_sess.mock_calls == []
