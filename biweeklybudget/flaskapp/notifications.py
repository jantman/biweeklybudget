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

from biweeklybudget.cashposition import CashPosition
from biweeklybudget.db import db_session
from biweeklybudget.utils import fmt_currency
from biweeklybudget.models.account import Account
from biweeklybudget.models.ofx_transaction import OFXTransaction

logger = logging.getLogger(__name__)


class NotificationsController(object):

    @staticmethod
    def num_stale_accounts(sess=None):
        """
        Return the number of accounts with stale data.

        @TODO This is a hack because I just cannot figure out how to do this
        natively in SQLAlchemy.

        :return: count of accounts with stale data
        :rtype: int
        """
        if sess is None:
            sess = db_session
        return sum(
            1 if a.is_stale else 0 for a in sess.query(
                Account).filter(Account.is_active.__eq__(True)).all()
        )

    @staticmethod
    def budget_account_sum(sess=None):
        """
        Return the sum of current balances for all is_budget_source accounts.

        Delegates to :py:attr:`~.CashPosition.budget_account_ledger`. The
        arithmetic behind this banner lives in
        :py:class:`~biweeklybudget.cashposition.CashPosition` so that the
        banner and the Cash Position page cannot report different numbers;
        two implementations of one calculation, free to drift apart, is
        precisely what GitHub issue #320 turned out to be. See issue #321.

        :return: Combined balance of all budget source accounts
        :rtype: decimal.Decimal
        """
        if sess is None:
            sess = db_session
        return CashPosition(sess).budget_account_ledger

    @staticmethod
    def credit_account_sum(sess=None):
        """
        Return the sum of current balances for all active credit accounts.

        Credit account ledger balances are stored *negative* when money is
        owed, so the value returned here is negative in the ordinary case and
        is *added* to :py:meth:`~.budget_account_sum` to arrive at the funds
        actually available. Do not negate it and do not take its absolute
        value: a credit account carrying a positive balance -- an overpaid
        card, or one holding a statement credit larger than its balance --
        really does hold money that is available to spend, and applying the
        recorded balance with its own sign gets that case right for free.
        See GitHub issue #320.

        Delegates to :py:attr:`~.CashPosition.credit_balance`.

        :return: Combined balance of all active credit accounts, negative
          when money is owed
        :rtype: decimal.Decimal
        """
        if sess is None:
            sess = db_session
        return CashPosition(sess).credit_balance

    @staticmethod
    def budget_account_unreconciled(sess=None):
        """
        Return the sum of unreconciled txns for all is_budget_source accounts.

        Delegates to :py:attr:`~.CashPosition.unreconciled`.

        :return: Combined unreconciled amount of all budget source accounts
        :rtype: decimal.Decimal
        """
        if sess is None:
            sess = db_session
        return CashPosition(sess).unreconciled

    @staticmethod
    def standing_budgets_sum(sess=None):
        """
        Return the sum of current balances of all standing budgets.

        Delegates to :py:attr:`~.CashPosition.standing_total`. Note that with
        no standing budgets this now returns ``Decimal('0.0')`` where it
        previously returned the integer ``0``; the two compare equal, so
        callers and their tests are unaffected.

        :return: sum of current balances of all standing budgets
        :rtype: decimal.Decimal
        """
        if sess is None:
            sess = db_session
        return CashPosition(sess).standing_total

    @staticmethod
    def pp_sum(sess=None):
        """
        Return the overall allocated sum for the current payperiod minus the
        sum of all reconciled Transactions for the pay period.

        Delegates to
        :py:attr:`~.CashPosition.pay_period_allocated_unspent`.

        :return: overall allocated sum for the current pay period minus the sum
          of all reconciled Transactions for the pay period.
        :rtype: decimal.Decimal
        """
        if sess is None:
            sess = db_session
        return CashPosition(sess).pay_period_allocated_unspent

    @staticmethod
    def num_unreconciled_ofx(sess=None):
        """
        Return the number of unreconciled OFXTransactions.

        :return: number of unreconciled OFXTransactions
        :rtype: int
        """
        if sess is None:
            sess = db_session
        return OFXTransaction.unreconciled(sess).count()

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
        credit_bal = NotificationsController.credit_account_sum()
        unrec_amt = NotificationsController.budget_account_unreconciled()
        standing_bal = NotificationsController.standing_budgets_sum()
        curr_pp = NotificationsController.pp_sum()
        logger.info(
            'accounts_bal=%s credit_bal=%s standing_bal=%s curr_pp=%s unrec=%s',
            accounts_bal, credit_bal, standing_bal, curr_pp, unrec_amt
        )
        # Money owed on a credit account is recorded as a negative balance, so
        # adding credit_bal here subtracts what is owed from the funds that are
        # actually available to spend. See GitHub issue #320.
        available = accounts_bal + credit_bal
        bal_sum = standing_bal + curr_pp + unrec_amt
        if available != bal_sum:
            if available < bal_sum:
                verb = 'is less than'
                classes = 'alert alert-danger'
            else:
                verb = 'is more than'
                classes = 'alert alert-info'
            res.append({
                'classes': classes,
                'content': 'Combined balance of all <a href="/accounts">'
                           'budget-funding accounts</a> less <a '
                           'href="/accounts">credit account balances</a> '
                           '(%s) %s all allocated funds total of '
                           '%s (%s <a href="/budgets">standing budgets</a>; '
                           '%s <a href="/pay_period_for">current pay period '
                           'allocated but unspent</a>; %s <a '
                           'href="/reconcile">unreconciled</a>)!'
                           '' % (
                               fmt_currency(available),
                               verb,
                               fmt_currency(bal_sum),
                               fmt_currency(standing_bal),
                               fmt_currency(curr_pp),
                               fmt_currency(unrec_amt)
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
