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
    PlaidJs, PlaidPublicToken, PlaidHandleLink, set_url_rules,
    PlaidConfigJS, PlaidUpdate
)
from biweeklybudget.models.account import Account
from biweeklybudget.models.plaid_items import PlaidItem
from biweeklybudget.models.plaid_accounts import PlaidAccount

from plaid.errors import PlaidError

from unittest.mock import Mock, MagicMock, patch, call, DEFAULT

pbm = 'biweeklybudget.flaskapp.views.plaid'


class TestSetUrlRules:

    def test_rules(self):
        m_phl_view = Mock()
        m_ppt_view = Mock()
        m_pjs_view = Mock()
        m_pj_view = Mock()
        m_pu_view = Mock()
        m_pra_view = Mock()
        m_puii_view = Mock()
        m_app = Mock()
        with patch.multiple(
            pbm,
            PlaidHandleLink=DEFAULT,
            PlaidPublicToken=DEFAULT,
            PlaidJs=DEFAULT,
            PlaidConfigJS=DEFAULT,
            PlaidUpdate=DEFAULT,
            PlaidRefreshAccounts=DEFAULT,
            PlaidUpdateItemInfo=DEFAULT,
            new_callable=MagicMock
        ) as mocks:
            mocks['PlaidHandleLink'].return_value = m_phl_view
            mocks['PlaidPublicToken'].as_view.return_value = m_ppt_view
            mocks['PlaidJs'].as_view.return_value = m_pjs_view
            mocks['PlaidConfigJS'].as_view.return_value = m_pj_view
            mocks['PlaidUpdate'].as_view.return_value = m_pu_view
            mocks['PlaidRefreshAccounts'].return_value = m_pra_view
            mocks['PlaidUpdateItemInfo'].return_value = m_puii_view
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
                '/plaid_config.js', view_func=m_pj_view
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
        mock_client.Item.public_token.create.side_effect = PlaidError(
            'some error message',
            'API_ERROR',
            999,
            'Some Displayed Error Message'
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
            call({'success': False, 'message': 'Exception: some error message'})
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

    def setup_method(self):
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
