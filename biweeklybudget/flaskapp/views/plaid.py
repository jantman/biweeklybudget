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

import os
import logging
from textwrap import dedent
from flask.views import MethodView
from flask import jsonify, request, redirect, render_template
from plaid.errors import PlaidError

from biweeklybudget import settings
from biweeklybudget.flaskapp.app import app
from biweeklybudget.utils import plaid_client
from biweeklybudget.models.account import Account
from biweeklybudget.plaid_updater import PlaidUpdater
from biweeklybudget.version import VERSION
from biweeklybudget.db import db_session

logger = logging.getLogger(__name__)


class PlaidJs(MethodView):
    """
    Handle GET /plaid.js endpoint, for CI/test or production/real.
    """

    def get(self):
        if os.environ.get('CI', 'false') == 'true':
            return redirect('static/js/plaid_test.js')
        return redirect('static/js/plaid_prod.js')


class PlaidAccessToken(MethodView):
    """
    Handle POST /ajax/plaid/get_access_token endpoint.
    """

    def post(self):
        if os.environ.get('CI', 'false') == 'true':
            return jsonify({
                'item_id': 'testITEMid',
                'access_token': 'testTOKEN'
            })
        client = plaid_client()
        public_token = request.form['public_token']
        logger.debug('Plaid token exchange for public token: %s', public_token)
        try:
            exchange_response = client.Item.public_token.exchange(public_token)
        except PlaidError as e:
            logger.error(
                'Plaid error exchanging token %s: %s',
                public_token, e, exc_info=True
            )
            resp = jsonify({
                'success': False,
                'message': 'Exception: %s' % str(e)
            })
            resp.status_code = 400
            return resp
        logger.info(
            'Plaid token exchange: public_token=%s response=%s',
            public_token, exchange_response
        )
        return jsonify(exchange_response)


class PlaidPublicToken(MethodView):
    """
    Handle POST /ajax/plaid/create_public_token endpoint.
    """

    def post(self):
        if os.environ.get('CI', 'false') == 'true':
            return jsonify({'public_token': 'testPUBLICtoken'})
        client = plaid_client()
        access_token = request.form['access_token']
        logger.debug(
            'Plaid create public token for acess token: %s', access_token
        )
        try:
            response = client.Item.public_token.create(access_token)
        except PlaidError as e:
            logger.error(
                'Plaid error creating token for %s: %s',
                access_token, e, exc_info=True
            )
            resp = jsonify({
                'success': False,
                'message': 'Exception: %s' % str(e)
            })
            resp.status_code = 400
            return resp
        logger.info(
            'Plaid token creation: access_token=%s response=%s',
            access_token, response
        )
        return jsonify(response)


class PlaidUpdate(MethodView):
    """
    Handle GET /plaid-update

    This single endpoint has multiple functions:

    * If called with no query parameters, displays a form template to use to
      interactively update Plaid accounts.
    * If called with an ``account_ids`` query argument, performs a Plaid update
      of the specified CSV list of account IDs, or all Plaid-enabled accounts if
      the value is ``ALL``. The response from this endpoint can be in one of
      three forms:

      * If the ``Accept`` HTTP header is set to ``application/json``, return a
        JSON list of update results. Each list item is the JSON-ified value of
        :py:meth:`~.PlaidUpdateResult.as_dict`.
      * If the ``Accept`` HTTP header is set to ``text/plain``, return a plain
        text human-readable summary of the update operation.
      * Otherwise, return a templated view of the update operation results.
    """

    def get(self):
        """
        Handle GET. If the ``account_ids`` query parameter is set, then return
        :py:meth:`~._update`, else return :py:meth:`~._form`.
        """
        ids = request.args.get('account_ids')
        if ids is None:
            return self._form()
        return self._update(ids)

    def _update(self, ids):
        """Handle an update for Plaid accounts."""
        logger.info('Handle Plaid Update request; account_ids=%s', ids)
        updater = PlaidUpdater()
        if ids == 'ALL':
            accounts = PlaidUpdater.available_accounts()
        else:
            ids = ids.split(',')
            accounts = [
                db_session.query(Account).get(int(x)) for x in ids
            ]
        results = updater.update(accounts=accounts)
        if request.headers.get('accept') == 'application/json':
            return jsonify([x.as_dict for x in results])
        elif request.headers.get('accept') == 'text/plain':
            s = ''
            num_updated = 0
            num_added = 0
            num_failed = 0
            for r in results:
                if not r.success:
                    num_failed += 1
                    s += f'{r.account.name} ({r.account.id}): Failed: {r.exc}\n'
                    continue
                num_updated += r.updated
                num_added += r.added
                s += f'{r.account.name} ({r.account.id}): {r.updated} ' \
                     f'updated, {r.added} added (stmt {r.stmt_id})\n'
            s += f'TOTAL: {num_updated} updated, {num_added} added, ' \
                 f'{num_failed} account(s) failed'
            return s
        # have to do this here in python and iterate twice, because of
        # https://github.com/pallets/jinja/issues/641
        num_updated = 0
        num_added = 0
        num_failed = 0
        for r in results:
            num_updated += r.updated
            num_added += r.added
            if not r.success:
                num_failed += 1
        return render_template(
            'plaid_result.html',
            results=results,
            num_added=num_added,
            num_updated=num_updated,
            num_failed=num_failed
        )

    def _form(self):
        return render_template(
            'plaid_form.html', accounts=PlaidUpdater.available_accounts()
        )


class PlaidConfigJS(MethodView):
    """
    Handle GET /plaid_config.js endpoint.
    """

    def get(self):
        return dedent(f"""
        // generated by utils.PlaidConfigJS
        var BIWEEKLYBUDGET_VERSION = "{VERSION}";
        var PLAID_ENV = "{settings.PLAID_ENV}";
        var PLAID_PRODUCTS = "{settings.PLAID_PRODUCTS}";
        var PLAID_PUBLIC_KEY = "{settings.PLAID_PUBLIC_KEY}";
        var PLAID_COUNTRY_CODES = "{settings.PLAID_COUNTRY_CODES}";
        """)


def set_url_rules(a):
    a.add_url_rule(
        '/ajax/plaid/get_access_token',
        view_func=PlaidAccessToken.as_view('plaid_access_token')
    )
    a.add_url_rule(
        '/ajax/plaid/create_public_token',
        view_func=PlaidPublicToken.as_view('plaid_public_token')
    )
    a.add_url_rule('/plaid.js', view_func=PlaidJs.as_view('plaid_js'))
    a.add_url_rule(
        '/plaid-update',
        view_func=PlaidUpdate.as_view('plaid_update')
    )
    a.add_url_rule(
        '/plaid_config.js',
        view_func=PlaidConfigJS.as_view('plaid_config_js')
    )


set_url_rules(app)
