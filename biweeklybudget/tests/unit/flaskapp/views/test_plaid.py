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
from biweeklybudget import settings
from biweeklybudget.version import VERSION
from biweeklybudget.flaskapp.views.plaid import (
    PlaidJs, PlaidPublicToken, PlaidAccessToken, set_url_rules,
    PlaidConfigJS, PlaidUpdate
)
from biweeklybudget.models.account import Account

from plaid.errors import PlaidError

from unittest.mock import Mock, MagicMock, patch, call, DEFAULT

pbm = 'biweeklybudget.flaskapp.views.plaid'


class TestSetUrlRules:

    def test_rules(self):
        m_pat_view = Mock()
        m_ppt_view = Mock()
        m_pjs_view = Mock()
        m_pj_view = Mock()
        m_pu_view = Mock()
        m_app = Mock()
        with patch.multiple(
            pbm,
            PlaidAccessToken=DEFAULT,
            PlaidPublicToken=DEFAULT,
            PlaidJs=DEFAULT,
            PlaidConfigJS=DEFAULT,
            PlaidUpdate=DEFAULT
        ) as mocks:
            mocks['PlaidAccessToken'].as_view.return_value = m_pat_view
            mocks['PlaidPublicToken'].as_view.return_value = m_ppt_view
            mocks['PlaidJs'].as_view.return_value = m_pjs_view
            mocks['PlaidConfigJS'].as_view.return_value = m_pj_view
            mocks['PlaidUpdate'].as_view.return_value = m_pu_view
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
            ),
            call.add_url_rule(
                '/plaid-update',
                view_func=m_pu_view
            ),
            call.add_url_rule(
                '/plaid_config.js', view_func=m_pj_view
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

    @patch.dict('os.environ', {}, clear=True)
    def test_exception(self):
        mock_json = Mock()
        mock_req = Mock(form={'public_token': 'foo'})
        mock_client = MagicMock()
        mock_client.Item.public_token.exchange.side_effect = PlaidError(
            'some error message',
            'API_ERROR',
            999,
            'Some Displayed Error Message'
        )
        with patch(f'{pbm}.jsonify') as m_jsonify:
            m_jsonify.return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                with patch(f'{pbm}.plaid_client') as m_client:
                    m_client.return_value = mock_client
                    res = PlaidAccessToken().post()
        assert res == mock_json
        assert m_jsonify.mock_calls == [
            call({'success': False, 'message': 'Exception: some error message'})
        ]
        assert mock_json.mock_calls == []
        assert mock_json.status_code == 400
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

    @patch.dict('os.environ', {}, clear=True)
    def test_exception(self):
        mock_json = Mock()
        mock_req = Mock(form={'access_token': 'foo'})
        mock_client = MagicMock()
        mock_client.Item.public_token.create.side_effect = PlaidError(
            'some error message',
            'API_ERROR',
            999,
            'Some Displayed Error Message'
        )
        with patch(f'{pbm}.jsonify') as m_jsonify:
            m_jsonify.return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                with patch(f'{pbm}.plaid_client') as m_client:
                    m_client.return_value = mock_client
                    res = PlaidPublicToken().post()
        assert res == mock_json
        assert m_jsonify.mock_calls == [
            call({'success': False, 'message': 'Exception: some error message'})
        ]
        assert mock_json.mock_calls == []
        assert mock_json.status_code == 400
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


class TestPlaidConfigJS:

    def test_happy_path(self):
        assert PlaidConfigJS().get() == dedent(f"""
        // generated by utils.PlaidConfigJS
        var BIWEEKLYBUDGET_VERSION = "{VERSION}";
        var PLAID_ENV = "{settings.PLAID_ENV}";
        var PLAID_PRODUCTS = "{settings.PLAID_PRODUCTS}";
        var PLAID_PUBLIC_KEY = "{settings.PLAID_PUBLIC_KEY}";
        var PLAID_COUNTRY_CODES = "{settings.PLAID_COUNTRY_CODES}";
        """)


class TestPlaidUpdate:

    pb = f'{pbm}.PlaidUpdate'

    def setup(self):
        self.cls = PlaidUpdate()

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
        m_acct1 = Mock()
        type(m_acct1).name = 'Acct1'
        type(m_acct1).id = 1
        m_acct2 = Mock()
        type(m_acct2).name = 'Acct2'
        type(m_acct2).id = 2
        m_acct3 = Mock()
        type(m_acct3).name = 'Acct3'
        type(m_acct3).id = 3
        rendered = Mock()
        with patch(f'{pbm}.PlaidUpdater.available_accounts') as m_aa:
            m_aa.return_value = [m_acct1, m_acct2, m_acct3]
            with patch(f'{pbm}.render_template') as m_render:
                m_render.return_value = rendered
                res = self.cls._form()
        assert res == rendered
        assert m_render.mock_calls == [
            call('plaid_form.html', accounts=[m_acct1, m_acct2, m_acct3])
        ]

    def test_update_template(self):
        mock_req = Mock(headers={})
        m_acct1 = Mock()
        type(m_acct1).name = 'Acct1'
        type(m_acct1).id = 1
        m_acct2 = Mock()
        type(m_acct2).name = 'Acct2'
        type(m_acct2).id = 2
        m_acct3 = Mock()
        type(m_acct3).name = 'Acct3'
        type(m_acct3).id = 3

        def db_get(_id):
            if _id == 1:
                return m_acct1
            if _id == 2:
                return m_acct2
            if _id == 3:
                return m_acct3

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
            mocks['PlaidUpdater'].available_accounts.return_value = [
                m_acct1, m_acct2, m_acct3
            ]
            mocks['render_template'].return_value = rendered
            mocks['jsonify'].return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                res = self.cls._update('ALL')
        assert res == rendered
        assert mocks['PlaidUpdater'].mock_calls == [
            call(),
            call.available_accounts(),
            call().update(accounts=[m_acct1, m_acct2, m_acct3])
        ]
        assert mock_updater.mock_calls == [
            call.update(accounts=[m_acct1, m_acct2, m_acct3])
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
        m_acct1 = Mock()
        type(m_acct1).name = 'Acct1'
        type(m_acct1).id = 1
        m_acct2 = Mock()
        type(m_acct2).name = 'Acct2'
        type(m_acct2).id = 2
        m_acct3 = Mock()
        type(m_acct3).name = 'Acct3'
        type(m_acct3).id = 3

        def db_get(_id):
            if _id == 1:
                return m_acct1
            if _id == 2:
                return m_acct2
            if _id == 3:
                return m_acct3

        mock_db = Mock()
        mock_query = Mock()
        mock_query.get.side_effect = db_get
        mock_db.query.return_value = mock_query
        mock_updater = Mock()
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
            mocks['PlaidUpdater'].available_accounts.return_value = [
                m_acct1, m_acct2, m_acct3
            ]
            mocks['render_template'].return_value = rendered
            mocks['jsonify'].return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                with patch(f'{pbm}.db_session', mock_db):
                    res = self.cls._update('1,2,3')
        assert res == mock_json
        assert mocks['PlaidUpdater'].mock_calls == [
            call(),
            call().update(accounts=[m_acct1, m_acct2, m_acct3])
        ]
        assert mock_updater.mock_calls == [
            call.update(accounts=[m_acct1, m_acct2, m_acct3])
        ]
        assert mocks['render_template'].mock_calls == []
        assert mocks['jsonify'].mock_calls == [
            call(['res1', 'res2', 'res3'])
        ]
        assert mock_db.mock_calls == [
            call.query(Account),
            call.query().get(1),
            call.query(Account),
            call.query().get(2),
            call.query(Account),
            call.query().get(3),
        ]

    def test_update_text(self):
        mock_req = Mock(headers={'accept': 'text/plain'})
        m_acct1 = Mock()
        type(m_acct1).name = 'Acct1'
        type(m_acct1).id = 1
        m_acct2 = Mock()
        type(m_acct2).name = 'Acct2'
        type(m_acct2).id = 2
        m_acct3 = Mock()
        type(m_acct3).name = 'Acct3'
        type(m_acct3).id = 3

        def db_get(_id):
            if _id == 1:
                return m_acct1
            if _id == 2:
                return m_acct2
            if _id == 3:
                return m_acct3

        mock_db = Mock()
        mock_query = Mock()
        mock_query.get.side_effect = db_get
        mock_db.query.return_value = mock_query
        mock_updater = Mock(db=mock_db)
        rendered = Mock()
        mock_json = Mock()
        result = [
            Mock(
                success=True, updated=1, added=1,
                as_dict='res1', account=m_acct1, stmt_id=111
            ),
            Mock(
                success=False, updated=0, added=0, as_dict='res2',
                account=m_acct2, exc='My Exception'
            ),
            Mock(
                success=True, updated=2, added=4, as_dict='res3',
                account=m_acct3, stmt_id=333
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
            mocks['PlaidUpdater'].available_accounts.return_value = [
                m_acct1, m_acct2, m_acct3
            ]
            mocks['render_template'].return_value = rendered
            mocks['jsonify'].return_value = mock_json
            with patch(f'{pbm}.request', mock_req):
                res = self.cls._update('ALL')
        assert res == 'Acct1 (1): 1 updated, 1 added (stmt 111)\n' \
                      'Acct2 (2): Failed: My Exception\n' \
                      'Acct3 (3): 2 updated, 4 added (stmt 333)\n' \
                      'TOTAL: 3 updated, 5 added, 1 account(s) failed'
        assert mocks['PlaidUpdater'].mock_calls == [
            call(),
            call.available_accounts(),
            call().update(accounts=[m_acct1, m_acct2, m_acct3])
        ]
        assert mock_updater.mock_calls == [
            call.update(accounts=[m_acct1, m_acct2, m_acct3])
        ]
        assert mocks['render_template'].mock_calls == []
        assert mocks['jsonify'].mock_calls == []
