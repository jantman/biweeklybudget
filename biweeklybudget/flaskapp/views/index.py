"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016-2024 Jason Antman <http://www.jasonantman.com>

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
from flask import render_template, jsonify, request
from copy import copy
from datetime import timedelta
from math import ceil
from sqlalchemy import asc, func

from biweeklybudget import settings

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
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        budgets = {}
        active_budgets = {}
        for b in db_session.query(Budget).all():
            k = b.name
            if b.is_income:
                k = '%s (i)' % b.name
            budgets[b.id] = k
            if b.is_active:
                active_budgets[b.id] = k
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
            pp_following_idx=pp_following_idx,
            accts=accts,
            budgets=budgets,
            active_budgets=active_budgets
        )


#: Largest ``days`` value :py:func:`~.parse_chart_days` will return as a window.
#: A hundred years is far more history than this application can hold, and
#: anything larger reaches back past every recorded balance, so it is treated as
#: 0 ("all history") -- which is both what the caller meant and what keeps
#: ``dtnow() - timedelta(days=days)`` clear of the OverflowError that
#: :py:class:`datetime.datetime` raises below ``MINYEAR``.
MAX_CHART_DAYS = 36500


def parse_chart_days(raw, default):
    """
    Parse the ``days`` query parameter for
    :py:class:`~.AcctBalanaceChartView`, falling back to ``default`` for
    anything that is not a non-negative integer.

    A value of ``0`` means "all recorded history" and is returned as-is; any
    other non-negative integer is a number of days to count back from now.
    Values above :py:const:`~.MAX_CHART_DAYS` are also returned as ``0``: a
    window that starts before every balance ever recorded *is* all history, and
    collapsing it here is what keeps the caller's arithmetic
    (``dtnow() - timedelta(days=days)``) from overflowing
    :py:class:`datetime.datetime`'s minimum year on an absurd input.

    This never raises. The chart endpoint has no side effects, and for a
    mistyped or stale URL, quietly showing a sensible view is a better outcome
    than a traceback or a ``400`` where a chart should be (FR-010).

    :param raw: the raw query parameter value, or None if it was not given
    :type raw: str or None
    :param default: the value to use when ``raw`` cannot be interpreted
    :type default: int
    :return: number of days of history to return; 0 means all history
    :rtype: int
    """
    if raw is None:
        return default
    try:
        days = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    if days < 0:
        return default
    if days > MAX_CHART_DAYS:
        return 0
    return days


def sample_chart_rows(rows, max_points):
    """
    Reduce ``rows`` to at most ``max_points`` entries by taking every *n*-th
    row, so that the "Account Balances" chart stays legible and quick to draw
    however many years of daily balances have accumulated.

    Guarantees, each of which is covered by a test in
    :py:mod:`biweeklybudget.tests.unit.flaskapp.views.test_index`:

    1. ``len(result) <= max_points`` for every input.
    2. When ``len(rows) <= max_points``, ``rows`` is returned unchanged -- the
       same objects, in the same order. An installation with a small amount of
       history sees exactly what it saw before this sampling existed (FR-013).
    3. When ``rows`` is non-empty, ``result[-1] is rows[-1]``.
    4. Order is preserved.
    5. An empty ``rows`` returns an empty list rather than raising.

    Guarantee 3 is the one that is not merely cosmetic. The right-hand edge of
    this chart is "what are my balances now", and it sits directly above the
    account tables on the same page. A stride that happened to stop two days
    short would make the chart silently disagree with those tables, so the last
    row is always kept even when the stride skips it (FR-005).

    Balances are slow-moving series rather than spiky signals, so a regularly
    sampled subset represents them faithfully. Sampling rather than averaging is
    deliberate: every plotted value is a balance that was actually recorded on
    the date it is plotted against, which is what makes a hovered value
    meaningful in a financial application.

    :param rows: chart data rows, ordered ascending by date
    :type rows: list
    :param max_points: maximum number of rows to return; values below 1 are
      treated as 1
    :type max_points: int
    :return: at most ``max_points`` of ``rows``, ending with ``rows[-1]``
    :rtype: list
    """
    if not rows:
        return rows
    if max_points < 1:
        max_points = 1
    if len(rows) <= max_points:
        return rows
    if max_points == 1:
        return [rows[-1]]
    # Reserve the final slot for the last row and stride across the rest. The
    # naive form -- stride over the whole list, then append the last row if the
    # stride missed it -- can return max_points + 1 rows whenever len(rows) is
    # an exact multiple of the stride (e.g. 6 rows into 3 points), because the
    # stride fills the quota and the appended row overflows it.
    stride = ceil((len(rows) - 1) / (max_points - 1))
    return rows[:-1:stride] + [rows[-1]]


class AcctBalanaceChartView(MethodView):
    """
    Handle GET /ajax/chart-data/account-balances endpoint.

    Accepts one optional query parameter, ``days``: the number of days of
    history to return, counting back from now. ``0`` means all recorded
    history. When it is absent or cannot be read as a non-negative integer,
    :py:attr:`~biweeklybudget.settings.ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` is
    used; see :py:func:`~.parse_chart_days`.

    The response shape is ``{'data': [...], 'keys': [...]}``, unchanged from
    before the windowing added for GitHub issue #279, so external scripts
    reading this endpoint keep working. ``days=0`` reproduces the previous
    full-history response, subject to the point cap below.

    It guarantees that:

    * at most
      :py:attr:`~biweeklybudget.settings.ACCOUNT_BALANCE_CHART_MAX_POINTS`
      dates are returned, for any ``days`` and any amount of stored history;
    * ``data`` is ascending by date, with no duplicates;
    * when the window holds no more dates than that cap, every one of them is
      returned and nothing is sampled away;
    * the most recent date in the window is always the last element;
    * every account keeps a continuous line: an account with no balance
      recorded inside the window carries forward its most recent value from
      *before* the window rather than being reported as absent or zero;
    * a ``NULL`` ledger is reported as ``0.0``, as it always has been;
    * with no balance records at all, ``data`` is empty and the status is still
      200.
    """

    def get(self):
        accounts = {
            x.id: x.name for x in db_session.query(Account).all()
        }
        acct_names = accounts.values()
        days = parse_chart_days(
            request.args.get('days'),
            settings.ACCOUNT_BALANCE_CHART_DEFAULT_DAYS
        )
        window_start = None
        if days > 0:
            window_start = dtnow() - timedelta(days=days)
        datedict = {x: None for x in acct_names}
        data = {}
        q = db_session.query(AccountBalance)
        if window_start is not None:
            q = q.filter(AccountBalance.overall_date >= window_start)
        for bal in q.order_by(asc(AccountBalance.overall_date)).all():
            ds = bal.overall_date.strftime('%Y-%m-%d')
            if ds not in data:
                data[ds] = copy(datedict)
                data[ds]['date'] = ds
            # accounts[bal.account_id], not bal.account.name: the latter is a
            # lazy-loaded relationship, so it issues one SELECT per balance row
            # for a name this method already loaded into `accounts` above. At
            # five years of daily balances across ten accounts that was ~18,000
            # round trips, and it was the dominant cost of this endpoint.
            name = accounts[bal.account_id]
            if bal.ledger is None:
                data[ds][name] = 0.0
            else:
                data[ds][name] = float(bal.ledger)
        # Seed the forward-fill with each account's last known balance from
        # before the window. Without this, an account whose most recent balance
        # predates the window has no row to carry forward from and is plotted
        # as null -- which on a balance chart reads as "this account went to
        # zero". That is the one way windowing can be quietly, financially
        # wrong, so the seed is not optional. It costs one query bounded by the
        # number of accounts, never by the amount of history.
        last = self._balances_before(accounts, window_start)
        resdata = []
        for k in sorted(data.keys()):
            d = copy(data[k])
            for subk in acct_names:
                if d[subk] is None:
                    d[subk] = last[subk]
            last = d
            resdata.append(d)
        res = {
            'data': sample_chart_rows(
                resdata, settings.ACCOUNT_BALANCE_CHART_MAX_POINTS
            ),
            'keys': sorted(acct_names)
        }
        return jsonify(res)

    def _balances_before(self, accounts, window_start):
        """
        Return each account's most recent ledger balance strictly before
        ``window_start``, as ``{account_name: float or None}``.

        This is the starting state for the forward-fill in :py:meth:`~.get`,
        so that an account with no balance recorded inside the requested window
        keeps its last known value instead of appearing to have dropped to
        zero. An account with no record at all before the window gets ``None``:
        its line legitimately begins where its data begins and must not be
        back-filled to a date on which the account did not yet exist.

        :param accounts: mapping of account ID to account name
        :type accounts: dict
        :param window_start: start of the requested window, or None when all
          history was requested (in which case there is nothing before it)
        :type window_start: datetime.datetime or None
        :return: mapping of account name to its pre-window balance, or None
        :rtype: dict
        """
        res = {name: None for name in accounts.values()}
        if window_start is None:
            return res
        # one row per account: the newest overall_date before the window
        latest = db_session.query(
            AccountBalance.account_id,
            func.max(AccountBalance.overall_date).label('overall_date')
        ).filter(
            AccountBalance.overall_date < window_start
        ).group_by(AccountBalance.account_id).subquery()
        q = db_session.query(AccountBalance).join(
            latest,
            (AccountBalance.account_id == latest.c.account_id) &
            (AccountBalance.overall_date == latest.c.overall_date)
        )
        for bal in q.all():
            name = accounts.get(bal.account_id)
            if name is None:
                continue
            res[name] = 0.0 if bal.ledger is None else float(bal.ledger)
        return res


app.add_url_rule('/', view_func=IndexView.as_view('index_view'))
app.add_url_rule(
    '/ajax/chart-data/account-balances',
    view_func=AcctBalanaceChartView.as_view('acct_balance_chart_view')
)
