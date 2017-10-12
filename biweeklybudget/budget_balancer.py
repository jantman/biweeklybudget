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

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.utils import dtnow

logger = logging.getLogger(__name__)


class BudgetBalancer(object):
    """
    Class to encapsulate logic for balancing budgets in a pay period.
    """

    def __init__(self, db_sess, payperiod):
        """

        :param db_sess: active database session to use for queries
        :type db_sess: sqlalchemy.orm.session.Session
        :param payperiod: pay period to balance
        :type payperiod: biweeklybudget.biweeklypayperiod.BiweeklyPayPeriod
        """
        self._db = db_sess
        self._payperiod = payperiod
        assert payperiod.end_date < dtnow.date()

    def plan(self):
        """
        Plan out balancing the budgets for the pay period. Return a dict with
        three top-level keys: "before", "after", and "transfers". Before and
        after are each dicts of Budget ID to Remaining amount, before and after
        balancing, respectively. "Transfers" is a list of dicts describing the
        transfers that will be made to achieve the end result. Each has keys
        "from_id", "from_amount", "to_id" and "to_amount".

        :return: Plan for how to balance budgets in the pay period
        :rtype: dict
        """
        return {'foo': 'bar'}

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
