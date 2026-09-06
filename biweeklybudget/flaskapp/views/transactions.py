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

import logging
from flask.views import MethodView
from flask import render_template, jsonify, request
from datatables import DataTable
from copy import copy
from datetime import datetime
from decimal import Decimal

from biweeklybudget.db import db_session
from biweeklybudget.flaskapp.app import app
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.budget_transaction import BudgetTransaction
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.flaskapp.views.searchableajaxview import SearchableAjaxView
from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView
from biweeklybudget.utils import (
    parse_currency, CurrencyParseError, dtnow
)
from biweeklybudget.credit_payment import CreditPaymentAttribution

logger = logging.getLogger(__name__)


class TransactionsView(MethodView):

    def get(self):
        """
        Render the GET /transactions view using the ``transactions.html``
        template.
        """
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        # Only credit accounts may be paid; restricting the list here is what
        # makes the "Credit Card Payment For" select correct by construction.
        # TransactionFormHandler.validate() enforces the same rule, because the
        # form endpoint is reachable without the select.
        credit_accts = {
            a.name: a.id
            for a in Account.active_credit_accounts(db_session).all()
        }
        budgets = {}
        active_budgets = {}
        for b in db_session.query(Budget).all():
            if b.is_income:
                bname = '%s (income)' % b.name
            else:
                bname = b.name
            budgets[bname] = b.id
            if b.is_active:
                active_budgets[bname] = b.id
        return render_template(
            'transactions.html',
            accts=accts,
            credit_accts=credit_accts,
            budgets=budgets,
            active_budgets=active_budgets
        )


class OneTransactionView(MethodView):

    def get(self, trans_id):
        """
        Render the GET /transactions/<int:trans_id> view using the
        ``transactions.html`` template.
        """
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        credit_accts = {
            a.name: a.id
            for a in Account.active_credit_accounts(db_session).all()
        }
        budgets = {}
        active_budgets = {}
        for b in db_session.query(Budget).all():
            if b.is_income:
                bname = '%s (income)' % b.name
            else:
                bname = b.name
            budgets[bname] = b.id
            if b.is_active:
                active_budgets[bname] = b.id
        return render_template(
            'transactions.html',
            accts=accts,
            credit_accts=credit_accts,
            budgets=budgets,
            trans_id=trans_id,
            active_budgets=active_budgets
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
            qs = qs.filter(
                Transaction.budget_transactions.any(
                    BudgetTransaction.budget_id.__eq__(budg_filter)
                )
            )
        # search
        if s != '' and s != 'FILTERHACK':
            if len(s) < 3:
                return qs
            s = '%' + s + '%'
            qs = qs.filter(Transaction.description.like(s))
        return qs

    def get(self):
        """
        Render and return JSON response for GET /ajax/transactions
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
                    'scheduled',
                    'scheduled_trans_id'
                ),
                (
                    'budgeted_amount'
                ),
                (
                    'sales_tax',
                    'sales_tax',
                    lambda a: float(a.sales_tax)
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
            no_budget_impact=lambda o: o.is_excluded_from_budget,
            credit_payment_acct_id=lambda o: o.credit_payment_acct_id,
            credit_payment_acct_name=lambda o: (
                None if o.credit_payment_acct is None
                else o.credit_payment_acct.name
            ),
            budgets=lambda o: [
                {
                    'name': bt.budget.name,
                    'id': bt.budget_id,
                    'amount': bt.amount,
                    'is_income': bt.budget.is_income
                }
                for bt in sorted(
                    o.budget_transactions, key=lambda x: x.amount,
                    reverse=True
                )
            ],
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
        # no_budget_impact comes through as_dict as the raw stored column, so
        # the modal's checkbox reflects the user's own choice rather than the
        # derived value; is_excluded_from_budget carries the derived answer.
        d['credit_payment_acct_name'] = (
            None if t.credit_payment_acct is None
            else t.credit_payment_acct.name
        )
        d['budgets'] = [
            {
                'name': bt.budget.name,
                'id': bt.budget_id,
                'amount': bt.amount,
                'is_income': bt.budget.is_income
            }
            for bt in sorted(
                t.budget_transactions, key=lambda x: x.amount,
                reverse=True
            )
        ]
        return jsonify(d)


class TransactionFormHandler(FormHandlerView):
    """
    Handle POST /forms/transaction
    """

    currency_fields = ['amount', 'sales_tax']

    def normalize_currency(self, data):
        """
        Normalize the currency fields, plus the per-budget split amounts.

        Budget split amounts arrive as a ``budgets`` hash of budget ID to
        amount, which :py:attr:`~.FormHandlerView.currency_fields` cannot
        address; they are normalized here so that :py:meth:`~.validate` can
        sum them. See GitHub issue #323.

        :param data: submitted form data; modified in place
        :type data: dict
        :return: hash of field name to list of error strings for that field;
          empty if every field was valid
        :rtype: dict
        """
        errors = super().normalize_currency(data)
        budgets = data.get('budgets', None)
        if not isinstance(budgets, dict):
            return errors
        for bid, amount in budgets.items():
            if not isinstance(amount, str) or amount.strip() == '':
                continue
            try:
                budgets[bid] = str(parse_currency(amount))
            except CurrencyParseError:
                errors.setdefault('budgets', []).append(
                    'Invalid amount: "%s"' % amount
                )
        return errors

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
        txn = None
        if 'id' in data and data['id'].strip() != '':
            # updating an existing budget
            txn = db_session.query(Transaction).get(int(data['id']))
        if data.get('description', '').strip() == '':
            errors['description'].append('Description cannot be empty')
            have_errors = True
        if Decimal(data['amount']) == Decimal('0'):
            errors['amount'].append('Amount cannot be zero')
            have_errors = True
        if data['account'] == 'None':
            errors['account'].append('Transactions must have an account')
            have_errors = True
        if len(data['budgets']) < 1:
            errors['budgets'].append('Transactions must have a budget.')
            have_errors = True
        else:
            budgets_total = Decimal('0.0')
            for bid, budg_amt in data['budgets'].items():
                budg = db_session.query(Budget).get(int(bid))
                budgets_total += Decimal(budg_amt)
                if budg is None:
                    errors['budgets'].append(
                        'Budget ID %s is invalid.' % bid
                    )
                    have_errors = True
                    continue
                if not budg.is_active and txn is None:
                    errors['budgets'].append(
                        'New transactions cannot use an inactive budget '
                        '(%s).' % budg.name
                    )
                    have_errors = True
                elif (
                    not budg.is_active and
                    budg.id not in [
                        x.budget_id for x in txn.budget_transactions
                    ]
                ):
                    errors['budgets'].append(
                        'Existing transactions cannot be changed to use an '
                        'inactive budget (%s).' % budg.name
                    )
                    have_errors = True
            if budgets_total != Decimal(data['amount']):
                errors['budgets'].append(
                    'Sum of all budget amounts (%s) must equal Transaction '
                    'amount (%s).' % (budgets_total, Decimal(data['amount']))
                )
                have_errors = True
        cp_acct = data.get('credit_payment_acct', 'None')
        if cp_acct is not None and str(cp_acct).strip() not in ['', 'None']:
            errors.setdefault('credit_payment_acct', [])
            try:
                cp_id = int(cp_acct)
            except (TypeError, ValueError):
                cp_id = None
            cp = None if cp_id is None else db_session.query(Account).get(cp_id)
            if cp is None:
                errors['credit_payment_acct'].append(
                    'Account ID %s is invalid.' % cp_acct
                )
                have_errors = True
            elif cp.acct_type != AcctType.Credit:
                errors['credit_payment_acct'].append(
                    '%s is not a credit account; only credit accounts can be '
                    'paid.' % cp.name
                )
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
        trans.description = data['description'].strip()
        trans.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        trans.account_id = int(data['account'])
        trans.notes = data['notes'].strip()
        if data['sales_tax'].strip() != '':
            trans.sales_tax = Decimal(data['sales_tax'])
        else:
            trans.sales_tax = Decimal('0.0')
        trans.no_budget_impact = data.get('no_budget_impact', False) in [
            True, 'true', 'True', 'on', '1'
        ]
        cp_acct = data.get('credit_payment_acct', 'None')
        if cp_acct is None or str(cp_acct).strip() in ['', 'None']:
            # Clearing the select must write NULL, not leave the previous
            # value: that is what lets a transaction resume counting against
            # its budget when it is no longer a credit card payment.
            trans.credit_payment_acct_id = None
        else:
            trans.credit_payment_acct_id = int(cp_acct)
        budg_amts = {}
        for bid, budg_amt in data['budgets'].items():
            budg = db_session.query(Budget).get(int(bid))
            budg_amts[budg] = Decimal(budg_amt)
        trans.set_budget_amounts(budg_amts)
        logger.info('%s: %s', action, trans.as_dict)
        db_session.add(trans)
        db_session.commit()
        return {
            'success_message': 'Successfully saved Transaction %d  in database.'
                               '' % trans.id,
            'success': True,
            'trans_id': trans.id
        }


class CreditPaymentInfoAjax(MethodView):
    """
    Handle GET /ajax/credit-payment-info endpoint.

    Given a credit account and a candidate payment amount, return a breakdown
    of which pay periods' charges that amount settles, plus any advisory
    warnings. Read-only, no side effects, safe to call on every keystroke.
    See GitHub issue #210 and :py:class:`~.CreditPaymentAttribution`.
    """

    def get(self):
        acct_id = request.args.get('account_id', None)
        try:
            acct = db_session.query(Account).get(int(acct_id))
        except (TypeError, ValueError):
            acct = None
        if acct is None:
            return jsonify({
                'error': 'Invalid or missing account_id: %s' % acct_id
            }), 400
        if acct.acct_type != AcctType.Credit:
            return jsonify({
                'error': '%s is not a credit account.' % acct.name
            }), 400
        try:
            amount = parse_currency(request.args.get('amount', ''))
        except CurrencyParseError:
            return jsonify({
                'error': 'Invalid or missing amount: %s' % request.args.get(
                    'amount', ''
                )
            }), 400
        date_s = request.args.get('date', None)
        if date_s is None or date_s.strip() == '':
            pmt_date = dtnow().date()
        else:
            try:
                pmt_date = datetime.strptime(date_s, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({
                    'error': 'Date "%s" is not valid (YYYY-MM-DD)' % date_s
                }), 400
        txn_id = request.args.get('txn_id', None)
        try:
            txn_id = int(txn_id)
        except (TypeError, ValueError):
            txn_id = None
        payer_id = request.args.get('payer_account_id', None)
        try:
            payer_id = int(payer_id)
        except (TypeError, ValueError):
            payer_id = None
        return jsonify(CreditPaymentAttribution(
            db_session, acct, amount, pmt_date,
            exclude_txn_id=txn_id, payer_account_id=payer_id
        ).as_dict)


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
    '/ajax/credit-payment-info',
    view_func=CreditPaymentInfoAjax.as_view('credit_payment_info_ajax')
)
app.add_url_rule(
    '/forms/transaction',
    view_func=TransactionFormHandler.as_view('transaction_form')
)
