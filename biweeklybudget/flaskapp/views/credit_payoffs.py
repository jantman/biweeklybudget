"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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
import json
from decimal import Decimal, ROUND_UP
from datetime import datetime

from flask.views import MethodView
from flask import render_template, request, jsonify

from biweeklybudget.flaskapp.jsonencoder import MagicJSONEncoder
from biweeklybudget.flaskapp.app import app
from biweeklybudget.db import db_session
from biweeklybudget.interest import InterestHelper
from biweeklybudget.models.dbsetting import DBSetting
from biweeklybudget.utils import fmt_currency

logger = logging.getLogger(__name__)


def parse_payoff_settings_json(j):
    """
    Given the 'credit-payoff' DBSettings JSON string value, parse it and return
    a dict with keys "increases" and "onetimes", each having a value of a dict
    of :py:class:`datetime.date` to :py:class:`decimal.Decimal`.

    :param j: 'credit-payoff' DBSettings JSON string value
    :type j: str
    :return: credit payoff settings
    :rtype: dict
    """
    pass


class CreditPayoffsView(MethodView):
    """
    Render the top-level GET /accounts/credit-payoff view using
    ``credit-payoffs.html`` template.
    """

    def _payoffs_list(self, ih):
        """
        Return a payoffs list suitable for rendering.

        :param ih: interest helper instance
        :type ih: biweeklybudget.interest.InterestHelper
        :return: list of payoffs suitable for rendering
        :rtype: list
        """
        res = ih.calculate_payoffs()
        payoffs = []
        for methname in sorted(res.keys(), reverse=True):
            tmp = {
                'name': methname,
                'description': res[methname]['description'],
                'doc': res[methname]['doc'],
                'results': []
            }
            if 'error' in res[methname]:
                tmp['error'] = res[methname]['error']
                continue
            total_pymt = Decimal('0')
            total_int = Decimal('0')
            max_mos = 0
            for k in sorted(res[methname]['results'].keys()):
                r = res[methname]['results'][k]
                acct = ih.accounts[k]
                tmp['results'].append({
                    'name': '%s (%d) (%s @ %s%%)' % (
                        acct.name, k,
                        fmt_currency(abs(acct.balance.ledger)),
                        (acct.effective_apr * Decimal('100')).quantize(
                            Decimal('.01')
                        )
                    ),
                    'total_payments': r['total_payments'],
                    'total_interest': r['total_interest'],
                    'payoff_months': r['payoff_months']
                })
                total_pymt += r['total_payments']
                total_int += r['total_interest']
                if r['payoff_months'] > max_mos:
                    max_mos = r['payoff_months']
            tmp['total'] = {
                'total_payments': total_pymt,
                'total_interest': total_int,
                'payoff_months': max_mos
            }
            payoffs.append(tmp)
        return payoffs

    def _payment_settings_dict(self, settings_json):
        """
        Given the JSON string payment settings, return a dict of payment
        settings as expected by :py:class:`~.InterestHelper` kwargs.

        :param settings_json: payment settings JSON
        :type settings_json: str
        :return: payment settings dict
        :rtype: dict
        """
        res = {'increases': {}, 'onetimes': {}}
        j = json.loads(settings_json)
        for i in j['increases']:
            if not i['enabled']:
                continue
            d = datetime.strptime(i['date'], '%Y-%m-%d').date()
            res['increases'][d] = Decimal(i['amount'])
        for i in j['onetimes']:
            if not i['enabled']:
                continue
            d = datetime.strptime(i['date'], '%Y-%m-%d').date()
            res['onetimes'][d] = Decimal(i['amount'])
        return res

    def get(self):
        setting = db_session.query(DBSetting).get('credit-payoff')
        if setting is None:
            pymt_settings_json = json.dumps({'increases': [], 'onetimes': []})
        else:
            pymt_settings_json = setting.value
        pymt_settings_kwargs = self._payment_settings_dict(pymt_settings_json)
        ih = InterestHelper(db_session, **pymt_settings_kwargs)
        mps = sum(ih.min_payments.values())
        payoffs = self._payoffs_list(ih)
        return render_template(
            'credit-payoffs.html',
            monthly_pymt_sum=mps.quantize(Decimal('.01'), rounding=ROUND_UP),
            payoffs=payoffs,
            pymt_settings_json=pymt_settings_json
        )


class PayoffSettingsFormHandler(MethodView):
    """
    Handle POST /settings/credit-payoff
    """

    def post(self):
        """
        Handle form submission; create or update models in the DB. Raises an
        Exception for any errors.

        :return: message describing changes to DB (i.e. link to created record)
        :rtype: str
        """
        data = request.get_json(force=True, silent=True)
        if data is None:
            logger.error('Error parsing request JSON')
            return jsonify({
                'success': False,
                'error_message': 'Error parsing JSON'
            })
        setting = db_session.query(DBSetting).get('credit-payoff')
        if setting is None:
            setting = DBSetting(name='credit-payoff')
            logger.info('new DBSetting name=credit-payoff')
        else:
            logger.info('Existing DBSetting name=credit-payoff value=%s',
                        setting.value)
        fixeddata = {'increases': [], 'onetimes': []}
        for key in ['increases', 'onetimes']:
            for d in sorted(data[key], key=lambda k: k['date']):
                if d['date'] == '' or d['amount'] == '':
                    continue
                fixeddata[key].append(d)
        val = json.dumps(fixeddata, sort_keys=True, cls=MagicJSONEncoder)
        try:
            parse_payoff_settings_json(val)
        except Exception as ex:
            logger.error('Error converting payoff settings JSON', exc_info=True)
            return jsonify({
                'success': False,
                'error_message': 'Error parsing JSON: %s' % ex
            })
        logger.info('Changing setting value to: %s', val)
        setting.value = val
        db_session.add(setting)
        db_session.commit()
        return jsonify({
            'success': True,
            'success_message': 'Successfully updated setting '
                               '"credit-payoff" in database.'
        })


app.add_url_rule(
    '/accounts/credit-payoff',
    view_func=CreditPayoffsView.as_view('credit_payoffs_view')
)
app.add_url_rule(
    '/settings/credit-payoff',
    view_func=PayoffSettingsFormHandler.as_view('payoff_settings_form')
)
