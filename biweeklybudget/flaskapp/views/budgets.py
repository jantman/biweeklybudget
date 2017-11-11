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
from flask.views import MethodView
from flask import render_template, jsonify
from datetime import datetime
from decimal import Decimal

from biweeklybudget.flaskapp.app import app
from biweeklybudget.db import db_session
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView
from biweeklybudget.models.account import Account
from biweeklybudget.models.utils import do_budget_transfer
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.utils import dtnow

logger = logging.getLogger(__name__)


class BudgetsView(MethodView):
    """
    Render the GET /budgets view using the ``budgets.html`` template.
    """

    def get(self):
        standing = db_session.query(Budget).filter(
            Budget.is_periodic.__eq__(False)
        ).order_by(Budget.name).all()
        periodic = db_session.query(Budget).filter(
            Budget.is_periodic.__eq__(True)
        ).order_by(Budget.name).all()
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        budgets = {}
        for b in db_session.query(Budget).all():
            k = b.name
            if b.is_income:
                k = '%s (i)' % b.name
            budgets[b.id] = k
        return render_template(
            'budgets.html',
            standing=standing,
            periodic=periodic,
            accts=accts,
            budgets=budgets
        )


class OneBudgetView(MethodView):
    """
    Render the GET /budgets/<int:budget_id> view using the ``budgets.html``
    template.
    """

    def get(self, budget_id):
        standing = db_session.query(Budget).filter(
            Budget.is_periodic.__eq__(False)
        ).order_by(Budget.name).all()
        periodic = db_session.query(Budget).filter(
            Budget.is_periodic.__eq__(True)
        ).order_by(Budget.name).all()
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        budgets = {}
        for b in db_session.query(Budget).all():
            k = b.name
            if b.is_income:
                k = '%s (i)' % b.name
            budgets[b.id] = k
        return render_template(
            'budgets.html',
            standing=standing,
            periodic=periodic,
            budget_id=budget_id,
            accts=accts,
            budgets=budgets
        )


class BudgetAjax(MethodView):
    """
    Handle GET /ajax/budget/<int:budget_id> endpoint.
    """

    def get(self, budget_id):
        budget = db_session.query(Budget).get(budget_id)
        return jsonify(budget.as_dict)


class BudgetFormHandler(FormHandlerView):
    """
    Handle POST /forms/budget
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
        have_errors = False
        errors = {k: [] for k in data.keys()}
        if data.get('name', '').strip() == '':
            errors['name'].append('Name cannot be empty')
            have_errors = True
        if (
            data['is_periodic'] == 'true' and
            data['starting_balance'].strip() == ''
        ):
            errors['starting_balances'].append(
                'Starting balance must be specified for periodic budgets.'
            )
            have_errors = True
        if (
            data['is_periodic'] == 'false' and
            data['current_balance'].strip() == ''
        ):
            errors['current_balances'].append(
                'Current balance must be specified for standing budgets.'
            )
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
        if 'id' in data and data['id'].strip() != '':
            # updating an existing budget
            budget = db_session.query(Budget).get(int(data['id']))
            if budget is None:
                raise RuntimeError("Error: no Budget with ID %s" % data['id'])
            action = 'updating Budget ' + data['id']
        else:
            budget = Budget()
            action = 'creating new Budget'
        budget.name = data['name'].strip()
        budget.description = data['description'].strip()
        if data['is_periodic'] == 'true':
            budget.is_periodic = True
            budget.starting_balance = data['starting_balance']
        else:
            budget.is_periodic = False
            budget.current_balance = data['current_balance']
        if data['is_active'] == 'true':
            budget.is_active = True
        else:
            budget.is_active = False
        if data['is_income'] == 'true':
            budget.is_income = True
        else:
            budget.is_income = False
        if data['omit_from_graphs'] == 'true':
            budget.omit_from_graphs = True
        else:
            budget.omit_from_graphs = False
        logger.info('%s: %s', action, budget.as_dict)
        db_session.add(budget)
        db_session.commit()
        return 'Successfully saved Budget %d in database.' % budget.id


class BudgetTxfrFormHandler(FormHandlerView):
    """
    Handle POST /forms/budget_transfer
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
        have_errors = False
        errors = {k: [] for k in data.keys()}
        if data['date'].strip() == '':
            errors['date'].append('Transactions must have a date')
            have_errors = True
        else:
            try:
                datetime.strptime(data['date'], '%Y-%m-%d').date()
            except Exception:
                errors['date'].append(
                    'Date "%s" is not valid (YYYY-MM-DD)' % data['date']
                )
                have_errors = True
        if float(data['amount']) == 0:
            errors['amount'].append('Amount cannot be zero')
            have_errors = True
        if float(data['amount']) < 0:
            errors['amount'].append('Amount cannot be negative')
            have_errors = True
        if data['account'] == 'None':
            errors['account'].append('Transactions must have an account')
            have_errors = True
        if data['from_budget'] == 'None':
            errors['from_budget'].append('from_budget cannot be empty')
            have_errors = True
        to_budget = db_session.query(Budget).get(int(data['to_budget']))
        if to_budget is None:
            errors['to_budget'].append('to_budget ID does not exist')
            have_errors = True
        if data['to_budget'] == 'None':
            errors['to_budget'].append('to_budget cannot be empty')
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
        # get the data
        trans_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        amt = float(data['amount'])
        acct = db_session.query(Account).get(int(data['account']))
        if acct is None:
            raise RuntimeError(
                "Error: no Account with ID %s" % data['account']
            )
        from_budget = db_session.query(Budget).get(int(data['from_budget']))
        if from_budget is None:
            raise RuntimeError(
                "Error: no Budget with ID %s" % data['from_budget']
            )
        to_budget = db_session.query(Budget).get(int(data['to_budget']))
        if to_budget is None:
            raise RuntimeError(
                "Error: no Budget with ID %s" % data['to_budget']
            )
        notes = data['notes'].strip()
        desc = 'Budget Transfer - %s from %s (%d) to %s (%d)' % (
            amt, from_budget.name, from_budget.id, to_budget.name,
            to_budget.id
        )
        logger.info(desc)
        res = do_budget_transfer(db_session, trans_date, amt, acct,
                                 from_budget, to_budget, notes=notes)
        db_session.commit()
        return 'Successfully saved Transactions %d and %d in database.' % (
            res[0].id, res[1].id
        )


class BudgetSpendingChartView(MethodView):
    """
    Handle GET /ajax/chart-data/budget-spending/<str:aggregation> endpoint.
    """

    def get(self, aggregation):
        if aggregation == 'by-pay-period':
            return self._by_pay_period()
        elif aggregation == 'by-month':
            return self._by_month()
        raise RuntimeError('Unknown aggregation type: %s' % aggregation)

    def _by_pay_period(self):
        min_txn = db_session.query(Transaction).order_by(
            Transaction.date.asc()
        ).first()
        budget_names = self._budget_names()
        logger.debug('budget_names=%s', budget_names)
        records = []
        budgets_present = set()
        pp = BiweeklyPayPeriod.period_for_date(min_txn.date, db_session)
        dt_now = dtnow().date()
        while pp.end_date <= dt_now:
            sums = pp.budget_sums
            logger.debug('sums=%s', sums)
            records.append({
                budget_names[y]: sums[y]['spent'] for y in sums.keys()
                if y in budget_names
            })
            records[-1]['date'] = pp.start_date.strftime('%Y-%m-%d')
            budgets_present.update(
                [budget_names[y] for y in sums.keys() if y in budget_names]
            )
            pp = pp.next
        res = {
            'data': records,
            'keys': sorted(list(budgets_present))
        }
        return jsonify(res)

    def _by_month(self):
        dt_now = dtnow().date()
        budget_names = self._budget_names()
        logger.debug('budget_names=%s', budget_names)
        records = {}
        budgets_present = set()
        for t in db_session.query(Transaction).filter(
            Transaction.budget.has(is_income=False),
            Transaction.date.__le__(dt_now)
        ).all():
            if t.budget_id not in budget_names:
                continue
            budgets_present.add(t.budget.name)
            ds = t.date.strftime('%Y-%m')
            if ds not in records:
                records[ds] = {'date': ds}
            if t.budget.name not in records[ds]:
                records[ds][t.budget.name] = Decimal('0')
            records[ds][t.budget.name] += t.actual_amount
        result = [records[k] for k in sorted(records.keys())]
        res = {
            'data': result,
            'keys': sorted(list(budgets_present))
        }
        return jsonify(res)

    def _budget_names(self):
        return {
            x.id: x.name for x in db_session.query(Budget).filter(
                Budget.is_income.__eq__(False),
                Budget.omit_from_graphs.__eq__(False)
            ).all()
        }


app.add_url_rule('/budgets', view_func=BudgetsView.as_view('budgets_view'))
app.add_url_rule(
    '/budgets/<int:budget_id>',
    view_func=OneBudgetView.as_view('one_budget_view')
)
app.add_url_rule(
    '/ajax/budget/<int:budget_id>',
    view_func=BudgetAjax.as_view('budget_ajax')
)
app.add_url_rule(
    '/forms/budget',
    view_func=BudgetFormHandler.as_view('budget_form')
)
app.add_url_rule(
    '/forms/budget_transfer',
    view_func=BudgetTxfrFormHandler.as_view('budget_transfer_form')
)
app.add_url_rule(
    '/ajax/chart-data/budget-spending/<string:aggregation>',
    view_func=BudgetSpendingChartView.as_view('budget_spending_chart_view')
)
