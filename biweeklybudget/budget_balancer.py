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
import json
from decimal import Decimal

from biweeklybudget.flaskapp.jsonencoder import MagicJSONEncoder
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.account import Account
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.utils import dtnow
from biweeklybudget.settings import DEFAULT_ACCOUNT_ID

logger = logging.getLogger(__name__)


def do_budget_transfer(db_sess, txn_date, amount, account,
                       from_budget, to_budget, notes=None):
    """
    Transfer a given amount from ``from_budget`` to ``to_budget`` on
    ``txn_date``. This method does NOT commit database changes. There are places
    where we rely on this function not committing changes.

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


class BudgetBalancePlanError(Exception):

    def __init__(self, expected, actual):
        msg = 'Attempted to apply payperiod budget balancing, but planned ' \
              'transfers did not match the user-approved plan.'
        message = '%s User-Approved: %s\nCurrent plan: %s' % (
            msg, expected, actual
        )
        super(BudgetBalancePlanError, self).__init__(message)
        self.expected = expected
        self.actual = actual
        self.description = msg


class BudgetBalancer(object):
    """
    Class to encapsulate logic for balancing budgets in a pay period.
    """

    def __init__(self, db_sess, payperiod, standing_budget, periodic_budget):
        """
        Initialize BudgetBalancer.

        :param db_sess: active database session to use for queries
        :type db_sess: sqlalchemy.orm.session.Session
        :param payperiod: pay period to balance
        :type payperiod: biweeklybudget.biweeklypayperiod.BiweeklyPayPeriod
        :param standing_budget: Standing Budget to use as source for additional
          funds to make up shortfalls, or destination of surplus funds.
        :type standing_budget: biweeklybudget.models.budget_model.Budget
        :param periodic_budget: Periodic Budget to transfer any remaining
          funds for the overall payperiod to, after other budgets are balanced.
        :type periodic_budget: biweeklybudget.models.budget_model.Budget
        """
        self._db = db_sess
        self._payperiod = payperiod
        self._standing = standing_budget
        self._periodic = periodic_budget
        self._account = self._db.query(Account).get(DEFAULT_ACCOUNT_ID)
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
            "before" and "after", to values of the remaining amount, and "name"
          - "standing_before" - float, beginning balance of standing budget
          - "standing_after" - float, ending balance of standing budget

        :return: Plan for how to balance budgets in the pay period
        :rtype: dict
        """
        logger.info('Begin planning budget balance.')
        result = {
            'pp_start_date': self._payperiod.start_date.strftime('%Y-%m-%d'),
            'transfers': [],
            'budgets': {},
            'standing_before': self._standing.current_balance,
            'standing_id': self._standing.id,
            'standing_name': self._standing.name,
            'periodic_overage_id': self._periodic.id,
            'periodic_overage_name': self._periodic.name
        }
        # get dict of budget ID to remaining amount
        to_balance = {}
        for budg_id, data in self._payperiod.budget_sums.items():
            if budg_id not in self._budgets.keys():
                continue
            if data['remaining'] == 0:
                continue
            to_balance[budg_id] = data['remaining']
            result['budgets'][budg_id] = {
                'before': data['remaining'],
                'name': self._budgets[budg_id].name
            }
        logger.info(
            'Beginning budget balances from PayPeriod: %s',
            [
                '%s(%d)=%s' % (
                    self._budgets[x].name, x, result['budgets'][x]['before']
                ) for x in result['budgets'].keys()
            ]
        )
        logger.info(
            'Beginning standing budget balance: %s',
            self._standing.current_balance
        )
        # ok, figure out the transfers we need to make...
        after, transfers, st_bal = self._do_plan_transfers(
            to_balance, [], self._standing.current_balance
        )
        logger.info(
            'Before balancing with standing budget, standing balance=%s '
            'transfers=%s, budget ending balances=%s', st_bal, transfers, after
        )
        # ok, now handle the standing budget stuff...
        after, transfers, st_bal = self._do_plan_standing_txfr(
            after, transfers, st_bal
        )
        result['transfers'] = transfers
        logger.info(
            'Budget transfers: \n%s',
            "\n".join(
                ['%d from %d to %d' % (x[2], x[0], x[1]) for x in transfers]
            )
        )
        result['standing_after'] = st_bal
        logger.info('Ending standing budget balance: %s', st_bal)
        for budg_id, budg_remain in after.items():
            result['budgets'][budg_id]['after'] = budg_remain
        logger.info(
            'Ending budget balances after balancing: %s',
            [
                '%s(%d)=%s' % (
                    self._budgets[x].name, x, result['budgets'][x]['after']
                ) for x in result['budgets'].keys()
            ]
        )
        res = self._do_overall_balance(result)
        self._db.rollback()
        return res

    def _do_overall_balance(self, result):
        """
        Given the :py:meth:`~.plan` result after balancing all periodic budgets,
        ensure that the overall PayPeriod remaining amount is zero. If not,
        transfer between `self._standing` and `self._periodic` to make that so.

        :param result: result from :py:meth:`~.plan`
        :type result: dict
        :return: same return value as :py:meth:`~.plan`, possibly with
          an additional transfer.
        :rtype: dict
        """
        # Make the transfers, to be rolled back later.
        before_sums = self._payperiod.budget_sums
        txns = []
        for txfr in result['transfers']:
            from_id, to_id, amt = txfr
            txns.extend(
                do_budget_transfer(
                    self._db, self._payperiod.end_date, amt, self._account,
                    self._db.query(Budget).get(from_id),
                    self._db.query(Budget).get(to_id),
                    notes='added by BudgetBalancer'
                )
            )
        self._db.flush()
        self._payperiod.clear_cache()
        bsums = self._payperiod.budget_sums
        osums = self._payperiod.overall_sums
        logger.debug('After balancing, PayPeriod budget sums: %s', bsums)
        logger.debug('After balancing, PayPeriod overall sums: %s', osums)
        for budg_id in self._budgets.keys():
            if bsums[budg_id]['remaining'] != Decimal('0'):
                self._db.rollback()
                raise RuntimeError(
                    'ERROR: expected budget %d remaining sum to be 0 after '
                    'balancing, but was %s' % (
                        budg_id, bsums[budg_id]['remaining']
                    )
                )
        overall_remain = osums['remaining']
        logger.info(
            'After balancing all budgets, overall PayPeriod remaining sum is '
            '%s', overall_remain
        )
        if overall_remain < Decimal('0'):
            logger.info(
                'PayPeriod overall remaining sum is negative; transferring '
                '%s from standing budget.', overall_remain
            )
            if abs(overall_remain) > result['standing_after']:
                overall_remain = Decimal('-1') * result['standing_after']
                logger.warning(
                    'WARNING: Standing budget balance insufficient to cover '
                    'all %s overage; using all of it', osums['remaining']
                )
            txns.extend(
                do_budget_transfer(
                    self._db, self._payperiod.end_date, abs(overall_remain),
                    self._account,
                    self._standing, self._periodic,
                    notes='added by BudgetBalancer'
                )
            )
            result['transfers'].append(
                [self._standing.id, self._periodic.id, abs(overall_remain)]
            )
            result['standing_after'] += overall_remain
            if self._periodic.id not in result['budgets']:
                result['budgets'][self._periodic.id] = {
                    'before': before_sums[self._periodic.id]['remaining'],
                    'after': before_sums[self._periodic.id]['remaining'],
                    'name': self._periodic.name
                }
            result['budgets'][self._periodic.id]['after'] += overall_remain
        elif overall_remain > Decimal('0'):
            logger.info(
                'PayPeriod overall remaining sum is positive; transferring '
                '%s to standing budget.', osums['remaining']
            )
            txns.extend(
                do_budget_transfer(
                    self._db, self._payperiod.end_date, abs(osums['remaining']),
                    self._account,
                    self._periodic, self._standing,
                    notes='added by BudgetBalancer'
                )
            )
            result['transfers'].append(
                [self._periodic.id, self._standing.id, abs(osums['remaining'])]
            )
            result['standing_after'] += overall_remain
            if self._periodic.id not in result['budgets']:
                result['budgets'][self._periodic.id] = {
                    'before': before_sums[self._periodic.id]['remaining'],
                    'after': before_sums[self._periodic.id]['remaining'],
                    'name': self._periodic.name
                }
            result['budgets'][self._periodic.id]['after'] += overall_remain
        self._db.rollback()
        return result

    def _do_plan_standing_txfr(self, id_to_remain, transfers, standing_bal):
        """
        Given a dictionary of budget IDs to remaining amounts, that have already
        been balanced as much as possible using the remaining amounts of each
        budget, use the Standing Budget to balance them all to zero.

        The arguments of this function are the final return value from
        :py:meth:`~._do_plan_transfers`.

        Transfers is a list of lists, each inner list describing a budget
        transfer and having 3 items: "from_id", "to_id" and "amount".

        :param id_to_remain: Budget ID to remaining balance
        :type id_to_remain: dict
        :param transfers: list of transfer dicts for transfers made so far
        :type transfers: list
        :param standing_bal: balance of the standing budget
        :type standing_bal: decimal.Decimal
        :return: tuple of new id_to_remain, transfers, standing_bal
        :rtype: tuple
        """
        # id_to_remain must be either all >= 0 or all <= 0
        if min(id_to_remain.values()) >= 0:
            # all positive
            logger.debug(
                'Balancing periodic budgets with standing; overall periodic sum'
                ' is positive'
            )

            def keyfunc():
                return max(id_to_remain, key=id_to_remain.get)
        else:
            # all negative
            logger.debug(
                'Balancing periodic budgets with standing; overall periodic sum'
                ' is negative'
            )

            def keyfunc():
                return min(id_to_remain, key=id_to_remain.get)
        while sum(id_to_remain.values()) != 0 and standing_bal > 0:
            logger.debug(
                'Looping to reconcile periodic with standing; standing bal=%s,'
                ' id_to_remain=%s, transfers=%s', standing_bal, id_to_remain,
                transfers
            )
            k = keyfunc()
            v = id_to_remain[k]
            if v > 0:
                transfers.append([k, self._standing.id, v])
                standing_bal += v
                id_to_remain[k] = 0
                continue
            # v < 0; transfer FROM standing TO periodic
            if abs(v) < standing_bal:
                # ok, we have enough to cover it
                transfers.append([self._standing.id, k, abs(v)])
                standing_bal += v
                id_to_remain[k] = 0
                continue
            # we do NOT have enough in standing to cover it
            transfers.append([self._standing.id, k, standing_bal])
            id_to_remain[k] += standing_bal
            standing_bal = 0
        return id_to_remain, transfers, standing_bal

    def _do_plan_transfers(self, id_to_remain, transfers, standing_bal):
        """
        Given a dictionary of budget IDs to remaining amounts, figure out
        what Budget Transfers to make to bring all remaining balances to zero.
        Works recursively.

        Transfers is a list of lists, each inner list describing a budget
        transfer and having 3 items: "from_id", "to_id" and "amount".

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

    def apply(self, plan_result, from_json=True):
        """
        Run a new plan for balancing budgets. Assuming it matches
        ``plan_result``, perform the specified actions to balance budgets.

        :param plan_result: the output of :py:meth:`~.plan`; only apply the
          transfers if it is still valid.
        :type plan_result: dict
        :param from_json: Whether or not the plan_result was JSON serialized.
        :type from_json: bool
        :return: list of Transaction objects created for budget transfers
        :rtype: list
        """
        actual = self.plan()
        if from_json:
            # need to convert to the same types we'd see from JSON (POST)
            actual = json.loads(json.dumps(actual, cls=MagicJSONEncoder))
        if plan_result != actual:
            raise BudgetBalancePlanError(plan_result, actual)
        txns = []
        for txfr in actual['transfers']:
            from_id, to_id, amt = txfr
            txns.extend(
                do_budget_transfer(
                    self._db, self._payperiod.end_date, amt, self._account,
                    self._db.query(Budget).get(from_id),
                    self._db.query(Budget).get(to_id),
                    notes='added by BudgetBalancer'
                )
            )
        self._db.flush()
        self._db.commit()
        return txns
