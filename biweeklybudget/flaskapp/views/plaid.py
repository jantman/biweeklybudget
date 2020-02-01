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
from flask.views import MethodView
from flask import jsonify, request, url_for, redirect
from plaid import Client
from plaid.errors import PlaidError

from biweeklybudget.flaskapp.app import app
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.account import Account
from biweeklybudget.db import db_session
from biweeklybudget import settings

logger = logging.getLogger(__name__)


def plaid_client():
    """
    Return an initialized :py:class:`plaid.Client` instance.

    :return: initialized Plaid client
    :rtype: plaid.Client
    """
    logger.debug('Getting Plaid client instance')
    assert settings.PLAID_CLIENT_ID is not None
    assert settings.PLAID_SECRET is not None
    assert settings.PLAID_PUBLIC_KEY is not None
    assert settings.PLAID_ENV is not None
    return Client(
        client_id=settings.PLAID_CLIENT_ID,
        secret=settings.PLAID_SECRET,
        public_key=settings.PLAID_PUBLIC_KEY,
        environment=settings.PLAID_ENV,
        api_version='2019-05-29'
    )


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


app.add_url_rule(
    '/ajax/plaid/get_access_token',
    view_func=PlaidAccessToken.as_view('plaid_access_token')
)
app.add_url_rule('/plaid.js', view_func=PlaidJs.as_view('plaid_js'))
