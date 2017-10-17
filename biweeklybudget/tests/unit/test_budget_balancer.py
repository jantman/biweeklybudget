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

import sys
import pytest
from datetime import datetime, date, timedelta
from sqlalchemy.orm.session import Session
from sqlalchemy import asc
from decimal import Decimal

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.budget_balancer import BudgetBalancer
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.tests.unit_helpers import binexp_to_dict

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call, DEFAULT
else:
    from unittest.mock import Mock, patch, call, DEFAULT

pbm = 'biweeklybudget.budget_balancer'
pb = '%s.BudgetBalancer' % pbm


class TestInit(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.pp = BiweeklyPayPeriod(date(2017, 1, 1), self.mock_sess)
        self.standing = Mock(spec_set=Budget, is_periodic=False)
        type(self.standing).id = 9
        type(self.standing).name = 'standingBudget'
        self.budgets = {1: 'one'}
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(self.mock_sess, self.pp, self.standing)

    def test_init(self):
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(self.mock_sess, self.pp, self.standing)
        assert self.cls._db == self.mock_sess
        assert self.cls._payperiod == self.pp
        assert self.cls._standing == self.standing
        assert self.cls._budgets == self.budgets


class TestBudgetsToBalance(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.pp = BiweeklyPayPeriod(date(2017, 1, 1), self.mock_sess)
        self.standing = Mock(spec_set=Budget, is_periodic=False)
        type(self.standing).id = 9
        type(self.standing).name = 'standingBudget'
        self.budgets = {1: 'one'}
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(self.mock_sess, self.pp, self.standing)

    def test_budgets_to_balance(self):
        b1 = Mock(spec_set=Budget, id=1, name='One')
        b2 = Mock(spec_set=Budget, id=2, name='Two')
        b3 = Mock(spec_set=Budget, id=3, name='Three')
        self.mock_sess.query.return_value.filter.\
            return_value.all.return_value = [b1, b2, b3]
        assert self.cls._budgets_to_balance() == {
            1: b1, 2: b2, 3: b3
        }
        assert len(self.mock_sess.mock_calls) == 3
        assert self.mock_sess.mock_calls[0] == call.query(Budget)
        assert self.mock_sess.mock_calls[1][0] == 'query().filter'
        assert len(self.mock_sess.mock_calls[1][1]) == 3
        assert str(self.mock_sess.mock_calls[1][1][0]) == str(
            Budget.is_periodic.__eq__(True)
        )
        assert str(self.mock_sess.mock_calls[1][1][1]) == str(
            Budget.is_active.__eq__(True)
        )
        assert str(self.mock_sess.mock_calls[1][1][2]) == str(
            Budget.skip_balance.__eq__(False)
        )
        assert self.mock_sess.mock_calls[2] == call.query().filter().all()


class TestPlan(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.pp = BiweeklyPayPeriod(date(2017, 1, 1), self.mock_sess)
        self.standing = Mock(spec_set=Budget, is_periodic=False)
        type(self.standing).id = 9
        type(self.standing).name = 'standingBudget'
        self.budgets = {1: 'one'}
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(self.mock_sess, self.pp, self.standing)
