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
from datetime import datetime
import logging

from flask.views import MethodView
from flask import render_template, request, redirect

from biweeklybudget.flaskapp.app import app
from biweeklybudget.utils import dtnow
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.db import db_session

logger = logging.getLogger(__name__)


class PayPeriodsView(MethodView):
    """
    Render the top-level GET /payperiods view using ``payperiods.html`` template
    """

    def get(self):
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), db_session)
        return render_template(
            'payperiods.html',
            pp_prev_date=pp.previous.start_date,
            pp_prev_sums=pp.previous.overall_sums,
            pp_curr_date=pp.start_date,
            pp_curr_sums=pp.overall_sums,
            pp_next_date=pp.next.start_date,
            pp_next_sums=pp.next.overall_sums,
            pp_following_date=pp.next.next.start_date,
            pp_following_sums=pp.next.next.overall_sums
        )


class PayPeriodView(MethodView):
    """
    Render the single PayPeriod GET /payperiod/YYYY-MM-DD view using the
    ``payperiod.html`` template.
    """

    def get(self, period_date):
        d = datetime.strptime(period_date, '%Y-%m-%d').date()
        pp = BiweeklyPayPeriod.period_for_date(d, db_session)
        return render_template(
            'payperiod.html',
            pp=pp,
            pp_prev_date=pp.previous.start_date,
            pp_prev_sums=pp.previous.overall_sums,
            pp_curr_date=pp.start_date,
            pp_curr_sums=pp.overall_sums,
            pp_next_date=pp.next.start_date,
            pp_next_sums=pp.next.overall_sums,
            pp_following_date=pp.next.next.start_date,
            pp_following_sums=pp.next.next.overall_sums,
            pp_last_date=pp.next.next.next.start_date,
            pp_last_sums=pp.next.next.next.overall_sums
        )


class PeriodForDateView(MethodView):
    """
    Render a redirect from a given date to the pay period for that date
    """

    def get(self):
        d_str = request.args.get('date')
        d = datetime.strptime(d_str, '%Y-%m-%d').date()
        pp = BiweeklyPayPeriod.period_for_date(d, db_session)
        logger.debug('Found period for %s (%s): %s', d_str, d, pp)
        return redirect(
            '/payperiod/%s' % pp.start_date.strftime('%Y-%m-%d'),
            code=301
        )


app.add_url_rule(
    '/payperiods',
    view_func=PayPeriodsView.as_view('payperiods_view')
)

app.add_url_rule(
    '/payperiod/<period_date>',
    view_func=PayPeriodView.as_view('payperiod_view')
)

app.add_url_rule(
    '/pay_period_for',
    view_func=PeriodForDateView.as_view('pay_period_for_view')
)
