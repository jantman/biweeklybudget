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
from flask import render_template, jsonify, request
from datatables import DataTable
from copy import copy
from datetime import datetime

from biweeklybudget.db import db_session
from biweeklybudget.flaskapp.app import app
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.flaskapp.views.searchableajaxview import SearchableAjaxView
from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView

logger = logging.getLogger(__name__)


class TransactionsView(MethodView):

    def get(self):
        """
        Render the GET /transactions view using the ``transactions.html``
        template.
        """
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        budgets = {}
        for b in db_session.query(Budget).all():
            if b.is_income:
                budgets['%s (income)' % b.name] = b.id
            else:
                budgets[b.name] = b.id
        return render_template(
            'transactions.html',
            accts=accts,
            budgets=budgets
        )


class OneTransactionView(MethodView):

    def get(self, trans_id):
        """
        Render the GET /transactions/<int:trans_id> view using the
        ``transactions.html`` template.
        """
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        budgets = {}
        for b in db_session.query(Budget).all():
            if b.is_income:
                budgets['%s (income)' % b.name] = b.id
            else:
                budgets[b.name] = b.id
        return render_template(
            'transactions.html',
            accts=accts,
            budgets=budgets,
            trans_id=trans_id
        )


class TransactionsAjax(SearchableAjaxView):
    """
    Handle GET /ajax/transactions endpoint.
    """

    def _filterhack(self, qs, s, args):
        """
        DataTables 1.10.12 has built-in support for filtering based on a value
        in a specific column; when this is done, the filter value is set in
        ``columns[N][search][value]`` where N is the column number. However,
        the python datatables package used here only supports the global
        ``search[value]`` input, not the per-column one.

        However, the DataTable search is implemented by passing a callable
        to ``table.searchable()`` which takes two arguments, the current Query
        that's being built, and the user's ``search[value]`` input; this must
        then return a Query object with the search applied.

        In python datatables 0.4.9, this code path is triggered on
        ``if callable(self.search_func) and search.get("value", None):``

        As such, we can "trick" the table to use per-column searching (currently
        only if global searching is not being used) by examining the per-column
        search values in the request, and setting the search function to one
        (this method) that uses those values instead of the global
        ``search[value]``.

        :param qs: Query currently being built
        :type qs: ``sqlalchemy.orm.query.Query``
        :param s: user search value
        :type s: str
        :param args: args
        :type args: dict
        :return: Query with searching applied
        :rtype: ``sqlalchemy.orm.query.Query``
        """
        # Ok, build our filter...
        acct_filter = args['columns'][3]['search']['value']
        if acct_filter != '' and acct_filter != 'None':
            qs = qs.filter(Transaction.account_id == acct_filter)
        budg_filter = args['columns'][4]['search']['value']
        if budg_filter != '' and budg_filter != 'None':
            qs = qs.filter(Transaction.budget_id == budg_filter)
        # search
        if s != '' and s != 'FILTERHACK':
            if len(s) < 3:
                return qs
            s = '%' + s + '%'
            qs = qs.filter(Transaction.description.like(s))
        return qs

    def get(self):
        """
        Render and return JSON response for GET /ajax/ofx
        """
        args = request.args.to_dict()
        args_dict = self._args_dict(args)
        if self._have_column_search(args_dict) and args['search[value]'] == '':
            args['search[value]'] = 'FILTERHACK'
        table = DataTable(
            args, Transaction, db_session.query(Transaction),
            [
                (
                    'date',
                    lambda i: i.date.strftime('%Y-%m-%d')
                ),
                (
                    'amount',
                    'actual_amount',
                    lambda a: float(a.actual_amount)
                ),
                'description',
                (
                    'account',
                    'account.name',
                    lambda i: "{} ({})".format(i.name, i.id)
                ),
                (
                    'budget',
                    'budget.name',
                    lambda i: "{} {}({})".format(
                        i.name,
                        '(income) ' if i.is_income else '',
                        i.id
                    )
                ),
                (
                    'scheduled',
                    'scheduled_trans_id'
                ),
                (
                    'budgeted_amount'
                ),
                (
                    'reconcile_id',
                    'reconcile',
                    lambda i: None if i.reconcile is None else i.reconcile.id
                )
            ]
        )
        table.add_data(
            acct_id=lambda o: o.account_id,
            budget_id=lambda o: o.budget_id,
            id=lambda o: o.id
        )
        if args['search[value]'] != '':
            table.searchable(lambda qs, s: self._filterhack(qs, s, args_dict))
        return jsonify(table.json())


class OneTransactionAjax(MethodView):
    """
    Handle GET /ajax/transactions/<int:trans_id> endpoint.
    """

    def get(self, trans_id):
        t = db_session.query(Transaction).get(trans_id)
        d = copy(t.as_dict)
        d['account_name'] = t.account.name
        d['budget_name'] = t.budget.name
        return jsonify(d)


class TransactionFormHandler(FormHandlerView):
    """
    Handle POST /forms/transaction
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
        if data.get('description', '').strip() == '':
            errors['description'].append('Description cannot be empty')
            have_errors = True
        if float(data['amount']) == 0:
            errors['amount'].append('Amount cannot be zero')
            have_errors = True
        if data['account'] == 'None':
            errors['account'].append('Transactions must have an account')
            have_errors = True
        if data['budget'] == 'None':
            errors['budget'].append('Transactions must have a budget')
            have_errors = True
        if data['date'].strip() == '':
            errors['date'].append('Transactions must have a date')
            have_errors = True
        try:
            datetime.strptime(data['date'], '%Y-%m-%d').date()
        except Exception:
            errors['date'].append(
                'Date "%s" is not valid (YYYY-MM-DD)' % data['date']
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
            trans = db_session.query(Transaction).get(int(data['id']))
            if trans is None:
                raise RuntimeError("Error: no Transaction with ID "
                                   "%s" % data['id'])
            if trans.reconcile is not None:
                raise RuntimeError(
                    "Transaction %d is already reconciled; cannot be edited."
                    "" % trans.id
                )
            action = 'updating Transaction ' + data['id']
        else:
            trans = Transaction()
            action = 'creating new Transaction'
        budg = db_session.query(Budget).get(int(data['budget']))
        trans.description = data['description'].strip()
        trans.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        trans.actual_amount = float(data['amount'])
        trans.account_id = int(data['account'])
        trans.budget = budg
        trans.notes = data['notes'].strip()
        logger.info('%s: %s', action, trans.as_dict)
        db_session.add(trans)
        db_session.commit()
        return {
            'success_message': 'Successfully saved Transaction %d '
                               'in database.' % trans.id,
            'success': True,
            'trans_id': trans.id
        }


app.add_url_rule(
    '/transactions',
    view_func=TransactionsView.as_view('transactions_view')
)
app.add_url_rule(
    '/transactions/<int:trans_id>',
    view_func=OneTransactionView.as_view('one_transaction_view')
)
app.add_url_rule(
    '/ajax/transactions',
    view_func=TransactionsAjax.as_view('transactions_ajax')
)
app.add_url_rule(
    '/ajax/transactions/<int:trans_id>',
    view_func=OneTransactionAjax.as_view('one_transaction_ajax')
)
app.add_url_rule(
    '/forms/transaction',
    view_func=TransactionFormHandler.as_view('transaction_form')
)
