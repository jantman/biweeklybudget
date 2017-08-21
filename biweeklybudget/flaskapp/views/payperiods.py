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
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.account import Account
from biweeklybudget.models.scheduled_transaction import ScheduledTransaction
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.db import db_session
from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView

logger = logging.getLogger(__name__)


class PayPeriodsView(MethodView):
    """
    Render the top-level GET /payperiods view using ``payperiods.html`` template
    """

    def get(self):
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), db_session)
        pp_curr_idx = 1
        pp_next_idx = 2
        pp_following_idx = 3
        periods = [
            pp.previous,
            pp
        ]
        x = pp
        # add another
        for i in range(0, 8):
            x = x.next
            periods.append(x)
        # trigger calculation/cache of data before passing on to jinja
        for p in periods:
            p.overall_sums
        return render_template(
            'payperiods.html',
            periods=periods,
            curr_pp=pp,
            pp_curr_idx=pp_curr_idx,
            pp_next_idx=pp_next_idx,
            pp_following_idx=pp_following_idx
        )


class PayPeriodView(MethodView):
    """
    Render the single PayPeriod GET /payperiod/YYYY-MM-DD view using the
    ``payperiod.html`` template.
    """

    def suffix_for_period(self, curr_pp, pp):
        """
        Generate the suffix to use for the given pay period in the view

        :param curr_pp: the current (today) pay period
        :type curr_pp: BiweeklyPayPeriod
        :param pp: the pay period in question
        :type pp: BiweeklyPayPeriod
        :return: suffix for the pay period
        :rtype: str
        """
        if pp.start_date == curr_pp.start_date:
            return '(curr.)'
        if pp.start_date == curr_pp.next.start_date:
            return '(next)'
        if pp.start_date == curr_pp.previous.start_date:
            return '(prev.)'
        return ''

    def get(self, period_date):
        d = datetime.strptime(period_date, '%Y-%m-%d').date()
        pp = BiweeklyPayPeriod.period_for_date(d, db_session)
        curr_pp = BiweeklyPayPeriod.period_for_date(dtnow(), db_session)
        budgets = {}
        for b in db_session.query(Budget).all():
            k = b.name
            if b.is_income:
                k = '%s (i)' % b.name
            budgets[b.id] = k
        standing = {
            b.id: b.current_balance
            for b in db_session.query(Budget).filter(
                Budget.is_periodic.__eq__(False),
                Budget.is_active.__eq__(True)
            ).all()
        }
        periodic = {
            b.id: b.current_balance
            for b in db_session.query(Budget).filter(
                Budget.is_periodic.__eq__(True),
                Budget.is_active.__eq__(True)
            ).all()
        }
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        txfr_date_str = dtnow().strftime('%Y-%m-%d')
        if dtnow().date() < pp.start_date or dtnow().date() > pp.end_date:
            # If we're looking at a non-current pay period, default the
            # transfer modal date to the start of the period.
            txfr_date_str = pp.start_date.strftime('%Y-%m-%d')
        return render_template(
            'payperiod.html',
            pp=pp,
            pp_prev_date=pp.previous.start_date,
            pp_prev_sums=pp.previous.overall_sums,
            pp_prev_suffix=self.suffix_for_period(curr_pp, pp.previous),
            pp_curr_date=pp.start_date,
            pp_curr_sums=pp.overall_sums,
            pp_curr_suffix=self.suffix_for_period(curr_pp, pp),
            pp_next_date=pp.next.start_date,
            pp_next_sums=pp.next.overall_sums,
            pp_next_suffix=self.suffix_for_period(curr_pp, pp.next),
            pp_following_date=pp.next.next.start_date,
            pp_following_sums=pp.next.next.overall_sums,
            pp_following_suffix=self.suffix_for_period(curr_pp, pp.next.next),
            pp_last_date=pp.next.next.next.start_date,
            pp_last_sums=pp.next.next.next.overall_sums,
            pp_last_suffix=self.suffix_for_period(curr_pp, pp.next.next.next),
            budget_sums=pp.budget_sums,
            budgets=budgets,
            standing=standing,
            periodic=periodic,
            transactions=pp.transactions_list,
            accts=accts,
            txfr_date_str=txfr_date_str
        )


class PeriodForDateView(MethodView):
    """
    Render a redirect from a given date to the pay period for that date
    """

    def get(self):
        d_str = request.args.get('date', None)
        if d_str is None:
            pp = BiweeklyPayPeriod.period_for_date(
                dtnow().date(), db_session
            )
            logger.debug('Redirect to current payperiod: %s', pp)
        else:
            d = datetime.strptime(d_str, '%Y-%m-%d').date()
            pp = BiweeklyPayPeriod.period_for_date(d, db_session)
            logger.debug('Found period for %s (%s): %s', d_str, d, pp)
        return redirect(
            '/payperiod/%s' % pp.start_date.strftime('%Y-%m-%d'),
            code=302
        )


class SchedToTransFormHandler(FormHandlerView):
    """
    Handle POST /forms/sched_to_trans
    """

    def validate(self, data):
        """
        Validate the form data. Return None if it is valid, or else a hash of
        field names to list of error strings for each field.

        :param data: submitted form data
        :type data: dict
        :return: None if no errors, or hash of field name to errors for that
          field
        """
        _id = int(data['id'])
        # make sure the ID is valid
        db_session.query(ScheduledTransaction).get(_id)
        d = datetime.strptime(data['date'], '%Y-%m-%d').date()
        pp = BiweeklyPayPeriod.period_for_date(d, db_session)
        have_errors = False
        errors = {k: [] for k in data.keys()}
        if data.get('description', '').strip() == '':
            errors['description'].append('Description cannot be empty')
            have_errors = True
        if float(data['amount']) == 0:
            errors['amount'].append('Amount cannot be zero')
            have_errors = True
        if d < pp.start_date or d > pp.end_date:
            errors['date'].append('Date must be in current pay period')
            have_errors = True
        if have_errors:
            return errors
        return None

    def submit(self, data):
        """
        Handle form submission; create or update models in the DB. Raises an
        Exception for any errors.

        :param data: submitted form data
        :type data: dict
        :return: message describing changes to DB (i.e. link to created record)
        :rtype: str
        """
        st_id = int(data['id'])
        st = db_session.query(ScheduledTransaction).get(st_id)
        d = datetime.strptime(data['date'], '%Y-%m-%d').date()
        t = Transaction(
            date=d,
            actual_amount=float(data['amount']),
            budgeted_amount=st.amount,
            description=data['description'],
            notes=data['notes'],
            account=st.account,
            budget=st.budget,
            scheduled_trans=st
        )
        db_session.add(t)
        db_session.commit()
        logger.info('Created Transaction %d for ScheduledTransaction %d',
                    t.id, st.id)
        return 'Successfully created Transaction %d for ' \
               'ScheduledTransaction %d.' % (t.id, st.id)


class SkipSchedTransFormHandler(FormHandlerView):
    """
    Handle POST /forms/skip_sched_trans
    """

    def validate(self, data):
        """
        Validate the form data. Return None if it is valid, or else a hash of
        field names to list of error strings for each field.

        :param data: submitted form data
        :type data: dict
        :return: None if no errors, or hash of field name to errors for that
          field
        """
        _id = int(data['id'])
        # make sure the ID is valid
        db_session.query(ScheduledTransaction).get(_id)
        d = datetime.strptime(data['payperiod_start_date'], '%Y-%m-%d').date()
        BiweeklyPayPeriod.period_for_date(d, db_session)
        have_errors = False
        errors = {k: [] for k in data.keys()}
        if data.get('notes', '').strip() == '':
            errors['notes'].append('Notes cannot be empty')
            have_errors = True
        if have_errors:
            return errors
        return None

    def submit(self, data):
        """
        Handle form submission; create or update models in the DB. Raises an
        Exception for any errors.

        :param data: submitted form data
        :type data: dict
        :return: message describing changes to DB (i.e. link to created record)
        :rtype: str
        """
        st_id = int(data['id'])
        st = db_session.query(ScheduledTransaction).get(st_id)
        d = datetime.strptime(data['payperiod_start_date'], '%Y-%m-%d').date()
        desc = 'Skip ScheduledTransaction %d in period %s' % (
            st_id, data['payperiod_start_date']
        )
        t = Transaction(
            date=d,
            actual_amount=0.0,
            budgeted_amount=0.0,
            description=desc,
            notes=data['notes'],
            account=st.account,
            budget=st.budget,
            scheduled_trans=st
        )
        db_session.add(t)
        db_session.add(TxnReconcile(
            transaction=t,
            note=desc
        ))
        db_session.commit()
        logger.info('Created Transaction %d to skip ScheduledTransaction %d',
                    t.id, st.id)
        return 'Successfully created Transaction %d to skip ' \
               'ScheduledTransaction %d.' % (t.id, st.id)


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

app.add_url_rule(
    '/forms/sched_to_trans',
    view_func=SchedToTransFormHandler.as_view('sched_to_trans_form')
)

app.add_url_rule(
    '/forms/skip_sched_trans',
    view_func=SkipSchedTransFormHandler.as_view('skip_sched_trans_form')
)
