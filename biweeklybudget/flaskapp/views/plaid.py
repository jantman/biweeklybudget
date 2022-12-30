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
from plaid import ApiException
from typing import List, Dict

from biweeklybudget import settings
from biweeklybudget.flaskapp.app import app
from biweeklybudget.utils import plaid_client, dtnow
from biweeklybudget.models.plaid_items import PlaidItem
from biweeklybudget.models.plaid_accounts import PlaidAccount
from biweeklybudget.plaid_updater import PlaidUpdater
from biweeklybudget.version import VERSION
from biweeklybudget.db import db_session

from plaid.models import (
    LinkTokenCreateRequest, ItemPublicTokenExchangeRequest,
    LinkTokenCreateRequestUser, ItemGetRequest, InstitutionsGetByIdRequest,
    AccountsGetRequest, LinkTokenCreateResponse, Products, CountryCode
)

logger = logging.getLogger(__name__)


class PlaidJs(MethodView):
    """
    Handle GET /plaid.js endpoint, for CI/test or production/real.
    """

    def get(self):
        return redirect('static/js/plaid_prod.js')


class PlaidHandleLink(MethodView):
    """
    Handle POST /ajax/plaid/handle_link endpoint.
    """

    def post(self):
        data = request.get_json()
        logger.debug(
            'got POST to /ajax/plaid/handle_link; data=%s', data
        )
        client = plaid_client()
        public_token = data['public_token']
        logger.debug('Plaid token exchange for public token: %s', public_token)
        try:
            req = ItemPublicTokenExchangeRequest(public_token=public_token)
            exchange_response = client.item_public_token_exchange(req)
        except ApiException as e:
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
        item = PlaidItem(
            item_id=exchange_response['item_id'],
            access_token=exchange_response['access_token'],
            last_updated=dtnow(),
            institution_name=data['metadata']['institution']['name'],
            institution_id=data['metadata']['institution']['institution_id']
        )
        logger.info('Add to DB: %s', item)
        db_session.add(item)
        for acct in data['metadata']['accounts']:
            acct = PlaidAccount(
                item_id=exchange_response['item_id'],
                account_id=acct['id'],
                name=acct['name'],
                mask=acct['mask'],
                account_type=acct['type'],
                account_subtype=acct.get('subtype', 'unknown')
            )
            logger.info('Add to DB: %s', acct)
            db_session.add(acct)
        db_session.commit()
        return jsonify({
            'success': True,
            'item_id': exchange_response['item_id'],
            'access_token': exchange_response['access_token']
        })


class PlaidRefreshAccounts(MethodView):
    """
    Handle POST /ajax/plaid/refresh_item_accounts endpoint.
    """

    def post(self):
        data = request.get_json()
        client = plaid_client()
        item_id = data['item_id']
        item: PlaidItem = db_session.query(PlaidItem).get(item_id)
        logger.debug(
            'Plaid refresh accounts for %s', item
        )
        try:
            response = client.accounts_get(
                AccountsGetRequest(access_token=item.access_token)
            )
        except ApiException as e:
            logger.error(
                'Plaid error getting accounts for %s: %s',
                item.access_token, e, exc_info=True
            )
            resp = jsonify({
                'success': False,
                'message': 'Exception: %s' % str(e)
            })
            resp.status_code = 400
            return resp
        logger.info('Plaid account refresh for item %s: %s', item, response)
        a: PlaidAccount
        all_accts = {a.account_id: a for a in item.all_accounts}
        curr_acct_ids = []
        logger.info(
            'Plaid reported %d accounts for the item', len(response['accounts'])
        )
        for acct in response['accounts']:
            acct = acct.to_dict()
            if acct['account_id'] in all_accts:
                curr_acct_ids.append(acct['account_id'])
                continue
            a = PlaidAccount(
                item_id=item.item_id,
                account_id=acct['account_id'],
                name=acct['name'],
                mask=acct['mask'],
                account_type=acct['type'],
                account_subtype=acct.get('subtype', 'unknown')
            )
            curr_acct_ids.append(acct['account_id'])
            logger.info('Add new to DB: %s', a)
            db_session.add(a)
        for aid, a in all_accts.items():
            if aid in curr_acct_ids:
                continue
            logger.info('Account no longer in Plaid item; removing: %s', a)
            db_session.delete(a)
        db_session.commit()
        return jsonify({'success': True})


class PlaidUpdateItemInfo(MethodView):
    """
    Handle POST /ajax/plaid/update_item_info endpoint.
    """

    def post(self):
        client = plaid_client()
        logger.info('Refreshing Plaid item info')
        item: PlaidItem
        for item in db_session.query(PlaidItem).all():
            logger.debug(
                'Plaid refresh item: %s', item
            )
            try:
                response = client.item_get(
                    ItemGetRequest(access_token=item.access_token)
                )
            except ApiException as e:
                logger.error(
                    'Plaid error getting item %s: %s',
                    item, e, exc_info=True
                )
                resp = jsonify({
                    'success': False,
                    'message': 'Exception: %s' % str(e)
                })
                resp.status_code = 400
                return resp
            logger.info('Plaid item info item %s: %s', item, response)
            item.institution_id = response['item']['institution_id']
            inst = client.institutions_get_by_id(
                InstitutionsGetByIdRequest(
                    institution_id=response['item']['institution_id'],
                    country_codes=[
                        CountryCode(x)
                        for x in settings.PLAID_COUNTRY_CODES.split(',')
                    ]
                )
            )
            item.institution_name = inst['institution']['name']
            db_session.add(item)
        db_session.commit()
        return jsonify({'success': True})


class PlaidUpdate(MethodView):
    """
    Handle GET or POST /plaid-update

    This single endpoint has multiple functions:

    * If GET with no query parameters, displays a form template to use to
      interactively update Plaid accounts.
    * If GET or POST with an ``item_ids`` query parameter, performs a Plaid
      update (via :py:meth:`~._update`) of the specified CSV list of Plaid Item
      IDs, or all Plaid Items if the value is ``ALL``. The POST method also
      accepts an optional ``num_days`` parameter specifying an integer number of
      days of transactions to update. The response from this endpoint can be in
      one of three forms:

      * If the ``Accept`` HTTP header is set to ``application/json``, return a
        JSON list of update results. Each list item is the JSON-ified value of
        :py:attr:`~.PlaidUpdateResult.as_dict`.
      * If the ``Accept`` HTTP header is set to ``text/plain``, return a plain
        text human-readable summary of the update operation.
      * Otherwise, return a templated view of the update operation results, as
        would be returned to a browser.
    """

    def post(self):
        """
        Handle POST. If the ``item_ids`` query parameter is set, then return
        :py:meth:`~._update`, else return a HTTP 400. If the optional
        ``num_days`` query parameter is set, pass that on to the update method.
        """
        ids = request.args.get('item_ids')
        if ids is None and request.form:
            ids = ','.join([
                x.replace('item_', '') for x in request.form.keys()
            ])
        if ids is None:
            return jsonify({
                'success': False,
                'message': 'Missing parameter: item_ids'
            }), 400
        kwargs = {}
        if 'num_days' in request.args:
            kwargs['num_days'] = int(request.args['num_days'])
        return self._update(ids, **kwargs)

    def get(self):
        """
        Handle GET. If the ``item_ids`` query parameter is set, then return
        :py:meth:`~._update`, else return :py:meth:`~._form`.
        """
        ids = request.args.get('item_ids')
        if ids is None:
            return self._form()
        kwargs = {}
        if 'num_days' in request.args:
            kwargs['num_days'] = int(request.args['num_days'])
        return self._update(ids, **kwargs)

    def _update(self, ids: str, num_days: int = 30):
        """
        Handle an update for Plaid accounts by instantiating a
        :py:class:`~.PlaidUpdater`, calling its :py:meth:`~.PlaidUpdater.update`
        method with the proper arguments, and then returning the result in a
        form determined by the ``Accept`` header.

        :param ids: a comma-separated string listing the :py:class:`~.PlaidItem`
          IDs to update, or the string ``ALL`` to update all Items.
        :type ids: str
        :param num_days: number of days to retrieve transactions for; default 30
        :type num_days: int
        """
        logger.info(
            'Handle Plaid Update request; item_ids=%s num_days=%d',
            ids, num_days
        )
        updater = PlaidUpdater()
        if ids == 'ALL':
            items = PlaidUpdater.available_items()
        else:
            ids = ids.split(',')
            items = [
                db_session.query(PlaidItem).get(x) for x in ids
            ]
        results = updater.update(items=items, days=num_days)
        if request.headers.get('accept') == 'text/plain':
            s = ''
            num_updated = 0
            num_added = 0
            num_failed = 0
            for r in results:
                if not r.success:
                    num_failed += 1
                    s += f'{r.item.institution_name} ({r.item.item_id}): ' \
                         f'Failed: {r.exc}\n'
                    continue
                num_updated += r.updated
                num_added += r.added
                s += f'{r.item.institution_name} ({r.item.item_id}): ' \
                     f'{r.updated} ' \
                     f'updated, {r.added} added (stmts: {r.stmt_ids})\n'
            s += f'TOTAL: {num_updated} updated, {num_added} added, ' \
                 f'{num_failed} account(s) failed'
            return s
        if request.headers.get('accept') == 'application/json':
            return jsonify([x.as_dict for x in results])
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
        items: List[PlaidItem] = db_session.query(PlaidItem).all()
        x: PlaidItem
        a: PlaidAccount
        plaid_accounts: Dict[str, str] = {
            x.item_id: ', '.join(
                [
                    f'{a.name} ({a.mask})'
                    for a in sorted(x.all_accounts, key=lambda a: a.name)
                ]
            ) for x in items
        }
        accounts = {
            x.item_id: ', '.join(
                filter(
                    None,
                    [
                        None if a.account is None else
                        f'{a.account.name} ({a.account.id})'
                        for a in x.all_accounts
                    ]
                )
            ) for x in items
        }
        return render_template(
            'plaid_form.html', plaid_items=items, plaid_accounts=plaid_accounts,
            accounts=accounts
        )


class PlaidLinkToken(MethodView):
    """
    Handle POST /ajax/plaid/create_link_token endpoint.
    """

    def post(self):
        data = request.get_json()
        client = plaid_client()
        logger.debug('Plaid create link token')
        kwargs = dict(
            products=[
                Products(x) for x in settings.PLAID_PRODUCTS.split(',')
            ],
            client_name=f'github.com/jantman/biweeklybudget {VERSION}',
            country_codes=[
                CountryCode(x)
                for x in settings.PLAID_COUNTRY_CODES.split(',')
            ],
            language="en",
            user=LinkTokenCreateRequestUser(
                client_user_id=settings.PLAID_USER_ID
            ),
        )
        if 'item_id' in data:
            item_id = data['item_id']
            item: PlaidItem = db_session.query(PlaidItem).get(item_id)
            logger.info('PlaidLinkToken for updating item %s', item_id)
            kwargs['access_token'] = item.access_token
        try:
            req = LinkTokenCreateRequest(**kwargs)
            response: LinkTokenCreateResponse = client.link_token_create(req)
            logger.debug('Plaid link_token_create response: %s', response)
        except ApiException as e:
            logger.error(
                'Plaid error creating Link token: %s', e, exc_info=True
            )
            resp = jsonify({
                'success': False,
                'message': 'Exception: %s' % str(e)
            })
            resp.status_code = 400
            return resp
        logger.info(
            'Plaid Link token creation: %s', response
        )
        return jsonify({'link_token': response.link_token})


def set_url_rules(a):
    a.add_url_rule(
        '/ajax/plaid/handle_link',
        view_func=PlaidHandleLink.as_view('plaid_handle_link')
    )
    a.add_url_rule('/plaid.js', view_func=PlaidJs.as_view('plaid_js'))
    a.add_url_rule(
        '/plaid-update',
        view_func=PlaidUpdate.as_view('plaid_update')
    )
    a.add_url_rule(
        '/ajax/plaid/refresh_item_accounts',
        view_func=PlaidRefreshAccounts.as_view('plaid_refresh_item_accounts')
    )
    a.add_url_rule(
        '/ajax/plaid/update_item_info',
        view_func=PlaidUpdateItemInfo.as_view('plaid_update_item_info')
    )
    a.add_url_rule(
        '/ajax/plaid/create_link_token',
        view_func=PlaidLinkToken.as_view('plaid_link_token')
    )


set_url_rules(app)
