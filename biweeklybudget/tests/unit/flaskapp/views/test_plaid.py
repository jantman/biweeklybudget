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

from biweeklybudget.flaskapp.views.plaid import (
    plaid_client, PlaidJs, PlaidPublicToken, PlaidAccessToken, set_url_rules
)
from unittest.mock import Mock, MagicMock, patch, call, DEFAULT

pbm = 'biweeklybudget.flaskapp.views.plaid'


class TestSetUrlRules:

    def test_rules(self):
        m_pat_view = Mock()
        m_ppt_view = Mock()
        m_pjs_view = Mock()
        m_app = Mock()
        with patch.multiple(
            pbm,
            PlaidAccessToken=DEFAULT,
            PlaidPublicToken=DEFAULT,
            PlaidJs=DEFAULT
        ) as mocks:
            mocks['PlaidAccessToken'].as_view.return_value = m_pat_view
            mocks['PlaidPublicToken'].as_view.return_value = m_ppt_view
            mocks['PlaidJs'].as_view.return_value = m_pjs_view
            set_url_rules(m_app)
        assert m_app.mock_calls == [
            call.add_url_rule(
                '/ajax/plaid/get_access_token',
                view_func=m_pat_view
            ),
            call.add_url_rule(
                '/ajax/plaid/create_public_token',
                view_func=m_ppt_view
            ),
            call.add_url_rule(
                '/plaid.js',
                view_func=m_pjs_view
            )
        ]


class TestPlaidClient:

    def test_happy_path(self):
        mock_client = Mock()
        with patch(f'{pbm}.Client', autospec=True) as m_client:
            m_client.return_value = mock_client
            res = plaid_client()
        assert res == mock_client
        assert m_client.mock_calls == [
            call(
                client_id='plaidCID',
                secret='plaidSecret',
                public_key='plaidPubKey',
                environment='sandbox',
                api_version='2019-05-29'
            )
        ]


class TestPlaidJs:

    def test_ci(self):
        with patch(f'{pbm}.redirect') as m_redir:
            m_redir.side_effect = lambda x: x
            res = PlaidJs().get()
        assert res == 'static/js/plaid_test.js'

    @patch.dict('os.environ', {}, clear=True)
    def test_normal(self):
        with patch(f'{pbm}.redirect') as m_redir:
            m_redir.side_effect = lambda x: x
            res = PlaidJs().get()
        assert res == 'static/js/plaid_prod.js'


class TestPlaidAccessToken:

    @patch.dict('os.environ', {}, clear=True)
    def test_normal(self):
        mock_json = Mock()
        mock_req = Mock(form={'public_token': 'foo'})
        mock_client = MagicMock()
        mock_client.Item.public_token.exchange.return_value = {
            'exchange': 'response'
        }
        with patch(f'{pbm}.jsonify') as m_jsonify:
            m_jsonify.return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                with patch(f'{pbm}.plaid_client') as m_client:
                    m_client.return_value = mock_client
                    res = PlaidAccessToken().post()
        assert res == mock_json
        assert m_jsonify.mock_calls == [
            call({'exchange': 'response'})
        ]
        assert mock_json.mock_calls == []
        assert m_client.mock_calls == [
            call(),
            call().Item.public_token.exchange('foo')
        ]

    def test_ci(self):
        mock_json = Mock()
        mock_req = Mock(form={'public_token': 'foo'})
        mock_client = MagicMock()
        mock_client.Item.public_token.exchange.return_value = {
            'exchange': 'response'
        }
        with patch(f'{pbm}.jsonify') as m_jsonify:
            m_jsonify.return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                with patch(f'{pbm}.plaid_client') as m_client:
                    m_client.return_value = mock_client
                    res = PlaidAccessToken().post()
        assert res == mock_json
        assert m_jsonify.mock_calls == [
            call({
                'item_id': 'testITEMid',
                'access_token': 'testTOKEN'
            })
        ]
        assert mock_json.mock_calls == []
        assert m_client.mock_calls == []


class TestPlaidPublicToken:

    @patch.dict('os.environ', {}, clear=True)
    def test_normal(self):
        mock_json = Mock()
        mock_req = Mock(form={'access_token': 'foo'})
        mock_client = MagicMock()
        mock_client.Item.public_token.create.return_value = {
            'create': 'response'
        }
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
            call().Item.public_token.create('foo')
        ]

    def test_ci(self):
        mock_json = Mock()
        mock_req = Mock(form={'access_token': 'foo'})
        mock_client = MagicMock()
        mock_client.Item.public_token.create.return_value = {
            'create': 'response'
        }
        with patch(f'{pbm}.jsonify') as m_jsonify:
            m_jsonify.return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                with patch(f'{pbm}.plaid_client') as m_client:
                    m_client.return_value = mock_client
                    res = PlaidPublicToken().post()
        assert res == mock_json
        assert m_jsonify.mock_calls == [
            call({'public_token': 'testPUBLICtoken'})
        ]
        assert mock_json.mock_calls == []
        assert m_client.mock_calls == []
