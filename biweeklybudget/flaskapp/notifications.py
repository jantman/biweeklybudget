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

from sqlalchemy import func
from locale import currency

from biweeklybudget.db import db_session
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.ofx_transaction import OFXTransaction


class NotificationsController(object):

    @staticmethod
    def num_stale_accounts():
        """
        Return the number of accounts with stale data.

        @TODO This is a hack because I just cannot figure out how to do this
        natively in SQLAlchemy.

        :return: count of accounts with stale data
        :rtype: int
        """
        return sum(
            1 if a.is_stale else 0 for a in db_session.query(
                Account).filter(Account.is_active.__eq__(True)).all()
        )

    @staticmethod
    def budget_account_sum():
        """
        Return the sum of current balances for all is_budget_source accounts.

        :return: Combined balance of all budget source accounts
        :rtype: float
        """
        sum = 0
        for acct in db_session.query(Account).filter(
                Account.is_budget_source.__eq__(True),
                Account.is_active.__eq__(True)
        ):
            if acct.balance is not None:
                sum += float(acct.balance.ledger)
        return sum

    @staticmethod
    def standing_budgets_sum():
        """
        Return the sum of current balances of all standing budgets.

        :return: sum of current balances of all standing budgets
        :rtype: float
        """
        res = db_session.query(func.sum(Budget.current_balance)).filter(
            Budget.is_periodic.__eq__(False),
            Budget.is_active.__eq__(True)
        ).all()[0][0]
        if res is None:
            return 0
        return float(res)

    @staticmethod
    def num_unreconciled_ofx():
        """
        Return the number of unreconciled OFXTransactions.

        :return: number of unreconciled OFXTransactions
        :rtype: int
        """
        return OFXTransaction.unreconciled(db_session).count()

    @staticmethod
    def get_notifications():
        """
        Return all notifications that should be displayed at the top of pages,
        as a list in the order they should appear. Each list item is a dict
        with keys "classes" and "content", where classes is the string that
        should appear in the notification div's "class" attribute, and content
        is the string content of the div.
        """
        res = []
        num_stale = NotificationsController.num_stale_accounts()
        if num_stale > 0:
            a = 'Accounts'
            if num_stale == 1:
                a = 'Account'
            res.append({
                'classes': 'alert alert-danger',
                'content': '%d %s with stale data. <a href="/accounts" '
                           'class="alert-link">View Accounts</a>.' % (num_stale,
                                                                      a)
            })
        accounts_bal = NotificationsController.budget_account_sum()
        standing_bal = NotificationsController.standing_budgets_sum()
        if accounts_bal < standing_bal:
            res.append({
                'classes': 'alert alert-danger',
                'content': 'Combined balance of all <a href="/accounts">'
                           'budget-funding accounts</a> '
                           '(%s) is less than balance of all <a href='
                           '"/budgets">standing budgets</a> (%s)!'
                           '' % (
                               currency(accounts_bal, grouping=True),
                               currency(standing_bal, grouping=True)
                           )
            })
        unreconciled_ofx = NotificationsController.num_unreconciled_ofx()
        if unreconciled_ofx > 0:
            res.append({
                'classes': 'alert alert-warning unreconciled-alert',
                'content': '%s <a href="/reconcile" class="alert-link">'
                           'Unreconciled OFXTransactions'
                           '</a>.' % unreconciled_ofx
            })
        return res
