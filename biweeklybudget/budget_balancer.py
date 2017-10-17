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
from copy import deepcopy

from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.account import Account
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.utils import dtnow

logger = logging.getLogger(__name__)


def do_budget_transfer(db_sess, txn_date, amount, account,
                       from_budget, to_budget, notes=None):
    """
    Transfer a given amount from ``from_budget`` to ``to_budget`` on
    ``txn_date``. This method does NOT commit database changes.

    :param db_sess: active database session to use for queries
    :type db_sess: sqlalchemy.orm.session.Session
    :param txn_date: date to make the transfer Transactions on
    :type txn_date: datetime.date
    :param amount: amount of money to transfer
    :type amount: float
    :param account:
    :type account: biweeklybudget.models.account.Account
    :param from_budget:
    :type from_budget: biweeklybudget.models.budget_model.Budget
    :param to_budget:
    :type to_budget: biweeklybudget.models.budget_model.Budget
    :param notes: Notes to add to the Transaction
    :type notes: str
    :return: list of Transactions created for the transfer
    :rtype: :py:obj:`list` of :py:class:`~.Transaction` objects
    """
    desc = 'Budget Transfer - %s from %s (%d) to %s (%d)' % (
        amount, from_budget.name, from_budget.id, to_budget.name,
        to_budget.id
    )
    logger.info(desc)
    t1 = Transaction(
        date=txn_date,
        actual_amount=amount,
        budgeted_amount=amount,
        description=desc,
        account=account,
        budget=from_budget,
        notes=notes
    )
    db_sess.add(t1)
    t2 = Transaction(
        date=txn_date,
        actual_amount=(-1 * amount),
        budgeted_amount=(-1 * amount),
        description=desc,
        account=account,
        budget=to_budget,
        notes=notes
    )
    db_sess.add(t2)
    db_sess.add(TxnReconcile(
        transaction=t1,
        note=desc
    ))
    db_sess.add(TxnReconcile(
        transaction=t2,
        note=desc
    ))
    return [t1, t2]


class BudgetBalancer(object):
    """
    Class to encapsulate logic for balancing budgets in a pay period.
    """

    def __init__(self, db_sess, payperiod, standing_budget):
        """
        Initialize BudgetBalancer.

        :param db_sess: active database session to use for queries
        :type db_sess: sqlalchemy.orm.session.Session
        :param payperiod: pay period to balance
        :type payperiod: biweeklybudget.biweeklypayperiod.BiweeklyPayPeriod
        :param standing_budget: Standing Budget to use as source for additional
          funds to make up shortfalls, or destination of surplus funds.
        :type standing_budget: biweeklybudget.models.budget_model.Budget
        """
        self._db = db_sess
        self._payperiod = payperiod
        self._standing = standing_budget
        assert self._standing.is_periodic is False
        assert payperiod.end_date < dtnow().date()
        logger.debug(
            'Initialize BudgetBalancer for PayPeriod starting on %s, using '
            'Standing Budget "%s" (%d)', self._payperiod.start_date,
            self._standing.name, self._standing.id
        )
        # get candidate budgets for balancing (Periodic, Active, not skip)
        self._budgets = self._budgets_to_balance()
        logger.debug(
            'Candidate budgets for balancing: %s', list(self._budgets.keys())
        )

    def _budgets_to_balance(self):
        """
        Return a dict of ID to Budget objects, for Budgets that are candidates
        to balance.

        :return: dict of budget ID to budget objects
        :rtype: dict
        """
        res = {}
        for b in self._db.query(Budget).filter(
            Budget.is_periodic.__eq__(True),
            Budget.is_active.__eq__(True),
            Budget.skip_balance.__eq__(False)
        ).all():
            res[b.id] = b
        return res

    def plan(self):
        """
        Plan out balancing the budgets for the pay period. Return a dict with
        top-level keys:

          - "pp_start_date" (str, Y-m-d)
          - "transfers" - list of dicts describing the transfers that will be
            made to achieve the end result. Each has keys "from_id", "to_id" and
            "amount".
          - "budgets" - is a dict describing the budgets before and after
            balancing; keys are budget IDs and values are dicts with keys
            "before" and "after", to values of the remaining amount.
          - "standing_before" - float, beginning balance of standing budget
          - "standing_after" - float, ending balance of standing budget

        :return: Plan for how to balance budgets in the pay period
        :rtype: dict
        """
        logger.debug('Begin planning budget balance.')
        result = {
            'pp_start_date': self._payperiod.start_date.strftime('%Y-%m-%d'),
            'transfers': [],
            'budgets': {},
            'standing_before': self._standing.current_balance,
            'standing_id': self._standing.id,
            'standing_name': self._standing.name
        }
        # get dict of budget ID to remaining amount
        to_balance = {}
        for budg_id, data in self._payperiod.budget_sums.items():
            # @TODO - DEBUG
            logger.debug(
                'LOOP self._payperiod.budget_sums - id=%s data=%s',
                budg_id, data
            )
            # @TODO - END DEBUG
            if budg_id not in to_balance.keys():
                continue
            if data['remaining'] == 0:
                continue
            to_balance[budg_id] = data['remaining']
            result['budgets'][budg_id] = {'before': data['remaining']}
        # @TODO - REMOVE - DEBUGGING
        logger.debug('self._budgets=%s result=%s', self._budgets, result)
        # @TODO - END DEBUGGING
        logger.debug(
            'Beginning budget balances from PayPeriod: %s',
            [
                '%s(%d)=%s' % (
                    self._budgets[x].name, x, result['budgets'][x]['before']
                ) for x in result['budgets'].keys()
            ]
        )
        logger.debug(
            'Beginning standing budget balance: %s',
            self._standing.current_balance
        )
        # ok, figure out the transfers we need to make...
        after, transfers, st_bal = self._do_plan_transfers(
            to_balance, [], self._standing.current_balance
        )
        result['transfers'] = transfers
        logger.debug('Budget transfers: \n%s', "\n".join(transfers))
        result['standing_after'] = st_bal
        logger.debug('Ending standing budget balance: %s', st_bal)
        for budg_id, budg_remain in after.items():
            result['budgets'][budg_id]['after'] = budg_remain
        logger.debug(
            'Ending budget balances after balancing: %s',
            [
                '%s(%d)=%s' % (
                    self._budgets[x].name, x, result['budgets'][x]['after']
                ) for x in result['budgets'].keys()
            ]
        )
        return result

    def _do_plan_transfers(self, id_to_remain, transfers, standing_bal):
        """
        Given a dictionary of budget IDs to remaining amounts, figure out
        what Budget Transfers to make to bring all remaining balances to zero.
        Works recursively.

        :param id_to_remain: Budget ID to remaining balance
        :type id_to_remain: dict
        :param transfers: list of transfer dicts for transfers made so far
        :type transfers: list
        :param standing_bal: balance of the standing budget
        :type standing_bal: decimal.Decimal
        :return: tuple of new id_to_remain, transfers, standing_bal
        :rtype: tuple
        """
        logger.debug(
            'Call _do_plan_transfers; id_to_remain=%s standing_bal=%s '
            'transfers=%s', id_to_remain, standing_bal, transfers
        )
        if standing_bal < 0:
            # standing_bal is empty, done.
            return id_to_remain, transfers, standing_bal
        if (
            all(x >= 0 for x in id_to_remain.values()) or
            all(x <= 0 for x in id_to_remain.values())
        ):
            # either all positive/0 or all negative/0; done
            return id_to_remain, transfers, standing_bal
        min_k = min(id_to_remain, key=id_to_remain.get)
        max_k = max(id_to_remain, key=id_to_remain.get)
        min_v = id_to_remain[min_k]
        max_v = id_to_remain[max_k]
        if max_v < 0 or min_v > 0:
            return id_to_remain, transfers, standing_bal
        if max_v > abs(min_v):
            transfers.append([max_k, min_k, abs(min_v)])
            id_to_remain[max_k] = max_v - abs(min_v)
            id_to_remain[min_k] = 0
            return self._do_plan_transfers(
                id_to_remain, transfers, standing_bal
            )
        if max_v == abs(min_v):
            transfers.append([max_k, min_k, abs(min_v)])
            id_to_remain[max_k] = 0
            id_to_remain[min_k] = 0
            return self._do_plan_transfers(
                id_to_remain, transfers, standing_bal
            )
        # else max_v < abs(min_v)
        transfers.append([max_k, min_k, abs(max_v)])
        id_to_remain[max_k] = 0
        id_to_remain[min_k] = min_v + max_v
        return self._do_plan_transfers(
            id_to_remain, transfers, standing_bal
        )

    def apply(self, plan_result):
        """
        Run a new plan for balancing budgets. Assuming it matches
        ``plan_result``, perform the specified actions to balance budgets.

        :param plan_result: the output of :py:meth:`~.plan`; only apply the
          transfers if it is still valid.
        :type plan_result: dict
        :return: list of Transaction IDs created for budget transfers
        :rtype: list
        """
        return [0, 1]
