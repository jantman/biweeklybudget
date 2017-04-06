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

from biweeklybudget.flaskapp.app import app
from biweeklybudget.db import db_session
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView

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
        return render_template(
            'budgets.html',
            standing=standing,
            periodic=periodic
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
        return render_template(
            'budgets.html',
            standing=standing,
            periodic=periodic,
            budget_id=budget_id
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
        logger.info('%s: %s', action, budget.as_dict)
        db_session.add(budget)
        db_session.commit()
        return 'Successfully saved Budget %d in database.' % budget.id


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
