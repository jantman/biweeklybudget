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
from decimal import Decimal
from datetime import datetime
import json
import re

from biweeklybudget.flaskapp.app import app
from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.plaid_accounts import PlaidAccount
from biweeklybudget.models.plaid_items import PlaidItem
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.db import db_session
from biweeklybudget.interest import (
    INTEREST_CALCULATION_NAMES, MIN_PAYMENT_FORMULA_NAMES
)

logger = logging.getLogger(__name__)

RE_FIELD_NAMES = [
    're_interest_charge',
    're_interest_paid',
    're_payment',
    're_late_fee',
    're_other_fee'
]


class AccountsView(MethodView):
    """
    Render the GET /accounts view using the ``accounts.html`` template.
    """

    def get(self):
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
        pa: PlaidAccount
        plaid_accts = {
            f'{pa.plaid_item.institution_name} / {pa.name} ({pa.mask})':
                f'{pa.item_id},{pa.account_id}'
            for pa in db_session.query(PlaidAccount).all()
        }
        return render_template(
            'accounts.html',
            bank_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Bank,
                Account.is_active == True).all(),  # noqa
            credit_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Credit,
                Account.is_active == True).all(),  # noqa
            investment_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Investment,
                Account.is_active == True).all(),  # noqa
            interest_class_names=INTEREST_CALCULATION_NAMES.keys(),
            min_pay_class_names=MIN_PAYMENT_FORMULA_NAMES.keys(),
            accts=accts,
            budgets=budgets,
            active_budgets=active_budgets,
            plaid_accounts=plaid_accts
        )


class OneAccountView(MethodView):
    """
    Render the /accounts/<int:acct_id> view using the ``account.html``
    template.
    """

    def get(self, acct_id):
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
        pa: PlaidAccount
        plaid_accts = {
            f'{pa.plaid_item.institution_name} / {pa.name} ({pa.mask})':
                f'{pa.item_id},{pa.account_id}'
            for pa in db_session.query(PlaidAccount).all()
        }
        return render_template(
            'accounts.html',
            bank_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Bank,
                Account.is_active == True).all(),  # noqa
            credit_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Credit,
                Account.is_active == True).all(),  # noqa
            investment_accounts=db_session.query(Account).filter(
                Account.acct_type == AcctType.Investment,
                Account.is_active == True).all(),  # noqa
            account_id=acct_id,
            interest_class_names=INTEREST_CALCULATION_NAMES.keys(),
            min_pay_class_names=MIN_PAYMENT_FORMULA_NAMES.keys(),
            accts=accts,
            budgets=budgets,
            active_budgets=active_budgets,
            plaid_accounts=plaid_accts
        )


class AccountAjax(MethodView):
    """
    Handle GET /ajax/account/<int:account_id> endpoint.
    """

    def get(self, account_id):
        acct = db_session.query(Account).get(account_id)
        return jsonify(acct.as_dict)


class AccountFormHandler(FormHandlerView):
    """
    Handle POST /forms/account
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
        try:
            hasattr(AcctType, data['acct_type'])
        except Exception:
            errors['acct_type'].append('"%s" is not a valid Account Type',
                                       data['acct_type'])
        if data['credit_limit'].strip() != '':
            errors = self._validate_decimal('credit_limit', data, errors)
        if data['apr'].strip() != '':
            errors = self._validate_decimal('apr', data, errors)
        if data['ofxgetter_config_json'].strip() != '':
            try:
                json.loads(data['ofxgetter_config_json'])
            except Exception:
                errors['ofxgetter_config_json'].append('Invalid JSON!')
        if data['prime_rate_margin'].strip() != '':
            errors = self._validate_decimal('prime_rate_margin', data, errors)
        if data['interest_class_name'] not in INTEREST_CALCULATION_NAMES:
            errors['interest_class_name'].append('Invalid interest class')
        if data['min_payment_class_name'] not in MIN_PAYMENT_FORMULA_NAMES:
            errors['min_payment_class_name'].append(
                'Invalid minimum payment class name'
            )
        if data['plaid_account'] != 'null,null':
            iid, aid = data['plaid_account'].split(',')
            acctid = 0
            if 'id' in data and data['id'].strip() != '':
                acctid = int(data['id'])
            existing = db_session.query(Account).filter(
                Account.plaid_item_id == self.fix_string(iid),
                Account.plaid_account_id == self.fix_string(aid),
                Account.id != acctid
            ).all()
            if existing:
                errors['plaid_account'].append(
                    'ERROR: This Plaid account is already used by the Account: '
                    f'{existing[0].name} ({existing[0].id}). Please remove it '
                    f'from that account before adding it to another.'
                )
        for f in RE_FIELD_NAMES:
            if data[f].strip() == '':
                continue
            try:
                re.compile(data[f])
            except Exception:
                errors[f].append('Invalid regular expression.')
        if have_errors:
            return errors
        for k, v in errors.items():
            if v:
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
        new_acct = False
        if 'id' in data and data['id'].strip() != '':
            # updating an existing account
            account = db_session.query(Account).get(int(data['id']))
            if account is None:
                raise RuntimeError("Error: no Account with ID %s" % data['id'])
            action = 'updating Account ' + data['id']
        else:
            new_acct = True
            account = Account()
            action = 'creating new Account'
        account.name = data['name'].strip()
        account.description = self.fix_string(data['description'])
        account.acct_type = getattr(AcctType, data['acct_type'])
        account.ofx_cat_memo_to_name = data['ofx_cat_memo_to_name']
        account.vault_creds_path = self.fix_string(data['vault_creds_path'])
        account.ofxgetter_config_json = self.fix_string(
            data['ofxgetter_config_json']
        )
        account.negate_ofx_amounts = data['negate_ofx_amounts']
        account.reconcile_trans = data['reconcile_trans']
        if account.acct_type == AcctType.Credit:
            if data['credit_limit'].strip() != '':
                account.credit_limit = Decimal(data['credit_limit'])
            else:
                account.credit_limit = None
            if data['apr'].strip() != '':
                account.apr = Decimal(data['apr'])
                if account.apr > Decimal('1'):
                    account.apr = account.apr * Decimal('0.01')
            else:
                account.apr = None
            if data['prime_rate_margin'].strip() != '':
                account.prime_rate_margin = Decimal(data['prime_rate_margin'])
                if account.prime_rate_margin > Decimal('1'):
                    account.prime_rate_margin = account.prime_rate_margin * \
                                                Decimal('0.01')
            else:
                account.prime_rate_margin = None
            account.interest_class_name = data['interest_class_name']
            account.min_payment_class_name = data['min_payment_class_name']
        account.is_active = data['is_active']
        for f in RE_FIELD_NAMES:
            data[f] = data[f].strip()
            if data[f] == '':
                data[f] = None
            setattr(account, f, data[f])
        if data['plaid_account'] == 'null,null':
            account.plaid_item_id = None
            account.plaid_account_id = None
        else:
            iid, aid = data['plaid_account'].split(',')
            account.plaid_item_id = self.fix_string(iid)
            account.plaid_account_id = self.fix_string(aid)
        logger.info('%s: %s', action, account.as_dict)
        db_session.add(account)
        db_session.commit()
        if new_acct:
            account.set_balance(ledger=Decimal('0'), avail=Decimal('0'))
            db_session.add(account)
            db_session.commit()
        return 'Successfully saved Account %d in database.' % account.id


class AccountTxfrFormHandler(FormHandlerView):
    """
    Handle POST /forms/account_transfer
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
        if data['budget'] == 'None':
            errors['budget'].append('Transactions must have a budget')
            have_errors = True
        if data['from_account'] == 'None':
            errors['from_account'].append('From Account cannot be empty')
            have_errors = True
        else:
            from_acct = db_session.query(Account).get(int(data['from_account']))
            if from_acct is None:
                errors['from_account'].append('from_account ID does not exist')
                have_errors = True
            else:
                if not from_acct.is_active:
                    errors['from_account'].append('From Account must be active')
                    have_errors = True
                if from_acct.acct_type not in AcctType.transferrable_types():
                    errors['from_account'].append(
                        'From Account type is not transferrable'
                    )
                    have_errors = True
        if data['to_account'] == 'None':
            errors['to_account'].append('To Account cannot be empty')
            have_errors = True
        else:
            to_acct = db_session.query(Account).get(int(data['to_account']))
            if to_acct is None:
                errors['to_account'].append('to_account ID does not exist')
                have_errors = True
            else:
                if not to_acct.is_active:
                    errors['to_account'].append('To Account must be active')
                    have_errors = True
                if to_acct.acct_type not in AcctType.transferrable_types():
                    errors['to_account'].append(
                        'To Account type is not transferrable'
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
        # get the data
        trans_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        amt = Decimal(data['amount'])
        from_acct = db_session.query(Account).get(int(data['from_account']))
        if from_acct is None:
            raise RuntimeError(
                "Error: no Account with ID %s" % data['from_account']
            )
        to_acct = db_session.query(Account).get(int(data['to_account']))
        if to_acct is None:
            raise RuntimeError(
                "Error: no Account with ID %s" % data['to_account']
            )
        budget = db_session.query(Budget).get(int(data['budget']))
        if budget is None:
            raise RuntimeError(
                "Error: no Budget with ID %s" % data['budget']
            )
        notes = data['notes'].strip()
        desc = 'Account Transfer - %s from %s (%d) to %s (%d)' % (
            amt, from_acct.name, from_acct.id, to_acct.name, to_acct.id
        )
        logger.info(desc)
        t1 = Transaction(
            date=trans_date,
            budget_amounts={budget: amt},
            budgeted_amount=amt,
            description=desc,
            account=from_acct,
            notes=notes,
            planned_budget=budget
        )
        db_session.add(t1)
        t2 = Transaction(
            date=trans_date,
            budget_amounts={budget: (-1 * amt)},
            budgeted_amount=(-1 * amt),
            description=desc,
            account=to_acct,
            notes=notes,
            planned_budget=budget
        )
        db_session.add(t2)
        t1.transfer = t2
        db_session.add(t1)
        t2.transfer = t1
        db_session.add(t2)
        db_session.commit()
        return 'Successfully saved Transactions %d and %d in database.' % (
            t1.id, t2.id
        )


app.add_url_rule('/accounts', view_func=AccountsView.as_view('accounts_view'))
app.add_url_rule(
    '/ajax/account/<int:account_id>',
    view_func=AccountAjax.as_view('account_ajax')
)
app.add_url_rule(
    '/accounts/<int:acct_id>',
    view_func=OneAccountView.as_view('account_view')
)
app.add_url_rule(
    '/forms/account',
    view_func=AccountFormHandler.as_view('account_form')
)
app.add_url_rule(
    '/forms/account_transfer',
    view_func=AccountTxfrFormHandler.as_view('account_transfer_form')
)
