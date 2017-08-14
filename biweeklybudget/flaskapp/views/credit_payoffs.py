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
from decimal import Decimal, ROUND_UP

from flask.views import MethodView
from flask import render_template

from biweeklybudget.flaskapp.app import app
from biweeklybudget.db import db_session
from biweeklybudget.interest import InterestHelper

logger = logging.getLogger(__name__)


class CreditPayoffsView(MethodView):
    """
    Render the top-level GET /accounts/credit-payoff view using
    ``credit-payoffs.html`` template.
    """

    def get(self):
        ih = InterestHelper(db_session)
        mps = sum(ih.min_payments.values())
        res = ih.calculate_payoffs()
        payoffs = []
        for methname in sorted(res.keys()):
            tmp = {
                'name': methname,
                'description': res[methname]['description'],
                'doc': res[methname]['doc'],
                'results': []
            }
            total_pymt = Decimal('0')
            total_int = Decimal('0')
            max_mos = 0
            for k in sorted(res[methname]['results'].keys()):
                r = res[methname]['results'][k]
                tmp['results'].append({
                    'name': '%s (%d)' % (ih.accounts[k].name, k),
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
        return render_template(
            'credit-payoffs.html',
            monthly_pymt_sum=mps.quantize(Decimal('.01'), rounding=ROUND_UP),
            payoffs=payoffs
        )


app.add_url_rule(
    '/accounts/credit-payoff',
    view_func=CreditPayoffsView.as_view('credit_payoffs_view')
)
