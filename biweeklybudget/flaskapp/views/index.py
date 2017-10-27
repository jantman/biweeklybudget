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

from flask.views import MethodView
from flask import render_template, jsonify
from copy import copy
from sqlalchemy import asc

from biweeklybudget.flaskapp.app import app
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.models.account import Account, AcctType, AccountBalance
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.db import db_session
from biweeklybudget.utils import dtnow


class IndexView(MethodView):
    """
    Render the GET / view using the ``index.html`` template.
    """

    def get(self):
        standing = db_session.query(Budget).filter(
            Budget.is_active.__eq__(True), Budget.is_periodic.__eq__(False)
        ).order_by(Budget.name).all()
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), db_session)
        pp_curr_idx = 1
        pp_next_idx = 2
        pp_following_idx = 3
        periods = [pp]
        x = pp
        # add another
        for i in range(0, 8):
            x = x.next
            periods.append(x)
        # trigger calculation/cache of data before passing on to jinja
        for p in periods:
            p.overall_sums
        return render_template(
            'index.html',
            bank_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Bank,
                Account.is_active == True).all(),  # noqa
            credit_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Credit,
                Account.is_active == True).all(),  # noqa
            investment_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Investment,
                Account.is_active == True).all(),  # noqa
            standing_budgets=standing,
            periods=periods,
            curr_pp=pp,
            pp_curr_idx=pp_curr_idx,
            pp_next_idx=pp_next_idx,
            pp_following_idx=pp_following_idx
        )


class AcctBalanaceChartView(MethodView):
    """
    Handle GET /ajax/chart-data/account-balances endpoint.
    """

    def get(self):
        accounts = {
            x.id: x.name for x in db_session.query(Account).all()
        }
        acct_names = accounts.values()
        datedict = {x: None for x in acct_names}
        data = {}
        for bal in db_session.query(AccountBalance).order_by(
            asc(AccountBalance.overall_date)
        ).all():
            ds = bal.overall_date.strftime('%Y-%m-%d')
            if ds not in data:
                data[ds] = copy(datedict)
                data[ds]['date'] = ds
            if bal.ledger is None:
                data[ds][bal.account.name] = 0.0
            else:
                data[ds][bal.account.name] = float(bal.ledger)
        resdata = []
        last = None
        for k in sorted(data.keys()):
            if last is None:
                last = data[k]
                continue
            d = copy(data[k])
            for subk in acct_names:
                if d[subk] is None:
                    d[subk] = last[subk]
            last = d
            resdata.append(d)
        res = {
            'data': resdata,
            'keys': sorted(acct_names)
        }
        return jsonify(res)


app.add_url_rule('/', view_func=IndexView.as_view('index_view'))
app.add_url_rule(
    '/ajax/chart-data/account-balances',
    view_func=AcctBalanaceChartView.as_view('acct_balance_chart_view')
)
