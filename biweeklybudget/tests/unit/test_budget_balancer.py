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
from datetime import date
from sqlalchemy.orm.session import Session
from decimal import Decimal

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.budget_balancer import BudgetBalancer
from biweeklybudget.models.budget_model import Budget

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call, PropertyMock
else:
    from unittest.mock import Mock, patch, call, PropertyMock

pbm = 'biweeklybudget.budget_balancer'
pb = '%s.BudgetBalancer' % pbm


class TestInit(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.pp = Mock(spec_set=BiweeklyPayPeriod)
        type(self.pp).start_date = date(2017, 1, 1)
        type(self.pp).end_date = date(2017, 1, 13)
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
        self.pp = Mock(spec_set=BiweeklyPayPeriod)
        type(self.pp).start_date = date(2017, 1, 1)
        type(self.pp).end_date = date(2017, 1, 13)
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
        self.pp = Mock(spec_set=BiweeklyPayPeriod)
        type(self.pp).start_date = date(2017, 1, 1)
        type(self.pp).end_date = date(2017, 1, 13)
        self.standing = Mock(spec_set=Budget, is_periodic=False)
        type(self.standing).id = 9
        type(self.standing).name = 'standingBudget'
        self.budg1 = Mock(spec_set=Budget)
        type(self.budg1).id = 1
        type(self.budg1).name = 'one'
        self.budg2 = Mock(spec_set=Budget)
        type(self.budg2).id = 2
        type(self.budg2).name = 'two'
        self.budg3 = Mock(spec_set=Budget)
        type(self.budg3).id = 3
        type(self.budg3).name = 'three'
        self.budgets = {1: self.budg1, 2: self.budg2, 3: self.budg3}
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(self.mock_sess, self.pp, self.standing)

    def test_simple(self):
        type(self.standing).current_balance = Decimal('123.45')
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('100')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('-100')},
            4: {'remaining': Decimal('986.34')}
        })
        to_balance = {1: Decimal('100'), 3: Decimal('-100')}
        with patch('%s._do_plan_transfers' % pb, autospec=True) as mock_dpt:
            with patch(
                '%s._do_plan_standing_txfr' % pb, autospec=True
            ) as m_dpst:
                mock_dpt.return_value = (
                    {1: Decimal('1'), 3: Decimal('-1')},
                    [
                        [1, 3, Decimal('99')]
                    ],
                    Decimal('123.67')
                )
                m_dpst.return_value = (
                    {1: Decimal('0'), 3: Decimal('-0')},
                    [
                        [1, 3, Decimal('99')],
                        [1, 9, Decimal('1')],
                        [9, 3, Decimal('10')]
                    ],
                    Decimal('26.87')
                )
                result = self.cls.plan()
        assert result == {
            'pp_start_date': '2017-01-01',
            'transfers': [
                [1, 3, Decimal('99')],
                [1, 9, Decimal('1')],
                [9, 3, Decimal('10')]
            ],
            'budgets': {
                1: {
                    'before': Decimal('100'),
                    'after': Decimal('0'),
                    'name': 'one'
                },
                3: {
                    'before': Decimal('-100'),
                    'after': Decimal('-0'),
                    'name': 'three'
                }
            },
            'standing_before': Decimal('123.45'),
            'standing_id': 9,
            'standing_name': 'standingBudget',
            'standing_after': Decimal('26.87')
        }
        assert mock_dpt.mock_calls == [
            call(self.cls, to_balance, [], Decimal('123.45'))
        ]
        assert m_dpst.mock_calls == [
            call(
                self.cls,
                {1: 1, 3: Decimal('-1')},
                [[1, 3, Decimal('99')]],
                Decimal('123.67')
            )
        ]


class TestDoPlanStandingTxfr(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.pp = Mock(spec_set=BiweeklyPayPeriod)
        type(self.pp).start_date = date(2017, 1, 1)
        type(self.pp).end_date = date(2017, 1, 13)
        self.standing = Mock(spec_set=Budget, is_periodic=False)
        type(self.standing).id = 9
        type(self.standing).name = 'standingBudget'
        self.budg1 = Mock(spec_set=Budget)
        type(self.budg1).id = 1
        type(self.budg1).name = 'one'
        self.budgets = {1: self.budg1}
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(self.mock_sess, self.pp, self.standing)

    def test_all_zeroed(self):
        result = self.cls._do_plan_standing_txfr(
            {1: Decimal('0'), 2: Decimal('0'), 6: Decimal('0')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('456')
        )
        assert result == (
            {1: Decimal('0'), 2: Decimal('0'), 6: Decimal('0')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('456')
        )

    def test_all_positive(self):
        result = self.cls._do_plan_standing_txfr(
            {1: Decimal('50'), 2: Decimal('0'), 6: Decimal('150')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('234.56')
        )
        assert result == (
            {1: Decimal('0'), 2: Decimal('0'), 6: Decimal('0')},
            [
                [1, 2, Decimal('3')],
                [2, 6, Decimal('345.67')],
                [6, 9, Decimal('150')],
                [1, 9, Decimal('50')]
            ],
            Decimal('434.56')
        )

    def test_negative_with_coverage(self):
        result = self.cls._do_plan_standing_txfr(
            {1: Decimal('-100'), 2: Decimal('-10'), 6: Decimal('0')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('456.93')
        )
        assert result == (
            {1: Decimal('0'), 2: Decimal('0'), 6: Decimal('0')},
            [
                [1, 2, Decimal('3')],
                [2, 6, Decimal('345.67')],
                [9, 1, Decimal('100')],
                [9, 2, Decimal('10')]
            ],
            Decimal('346.93')
        )

    def test_negative_without_coverage(self):
        result = self.cls._do_plan_standing_txfr(
            {1: Decimal('-60'), 2: Decimal('-356.78'), 6: Decimal('-90')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('456.78')
        )
        assert result == (
            {1: Decimal('-50'), 2: Decimal('0'), 6: Decimal('0')},
            [
                [1, 2, Decimal('3')],
                [2, 6, Decimal('345.67')],
                [9, 2, Decimal('356.78')],
                [9, 6, Decimal('90')],
                [9, 1, Decimal('10')]
            ],
            Decimal('0')
        )


class TestDoPlanTransfers(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.pp = Mock(spec_set=BiweeklyPayPeriod)
        type(self.pp).start_date = date(2017, 1, 1)
        type(self.pp).end_date = date(2017, 1, 13)
        self.standing = Mock(spec_set=Budget, is_periodic=False)
        type(self.standing).id = 9
        type(self.standing).name = 'standingBudget'
        self.budg1 = Mock(spec_set=Budget)
        type(self.budg1).id = 1
        type(self.budg1).name = 'one'
        self.budgets = {1: self.budg1}
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(self.mock_sess, self.pp, self.standing)

    def test_return_early_if_standing_zero(self):
        result = self.cls._do_plan_transfers(
            {1: Decimal('0'), 2: Decimal('234'), 6: Decimal('-948.38')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('-123')
        )
        assert result == (
            {1: Decimal('0'), 2: Decimal('234'), 6: Decimal('-948.38')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('-123')
        )

    def test_return_early_if_all_positive(self):
        result = self.cls._do_plan_transfers(
            {1: Decimal('0'), 2: Decimal('234'), 6: Decimal('948.38')},
            [],
            Decimal('1234.56')
        )
        assert result == (
            {1: Decimal('0'), 2: Decimal('234'), 6: Decimal('948.38')},
            [],
            Decimal('1234.56')
        )

    def test_return_early_if_all_negative(self):
        result = self.cls._do_plan_transfers(
            {1: Decimal('0'), 2: Decimal('-234'), 6: Decimal('-948.38')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('1234.56')
        )
        assert result == (
            {1: Decimal('0'), 2: Decimal('-234'), 6: Decimal('-948.38')},
            [[1, 2, Decimal('3')], [2, 6, Decimal('345.67')]],
            Decimal('1234.56')
        )

    def test_simple_no_recurse_max_equal_min(self):
        result = self.cls._do_plan_transfers(
            {1: Decimal('100.55'), 2: Decimal('0'), 6: Decimal('-100.55')},
            [],
            Decimal('1234.56')
        )
        assert result == (
            {1: Decimal('0'), 2: Decimal('0'), 6: Decimal('0')},
            [[1, 6, Decimal('100.55')]],
            Decimal('1234.56')
        )

    def test_simple_no_recurse_max_gt_min(self):
        result = self.cls._do_plan_transfers(
            {1: Decimal('200'), 2: Decimal('0'), 6: Decimal('-100')},
            [],
            Decimal('1234.56')
        )
        assert result == (
            {1: Decimal('100'), 2: Decimal('0'), 6: Decimal('0')},
            [[1, 6, Decimal('100')]],
            Decimal('1234.56')
        )

    def test_simple_no_recurse_max_lt_min(self):
        result = self.cls._do_plan_transfers(
            {1: Decimal('-200'), 2: Decimal('0'), 6: Decimal('100')},
            [],
            Decimal('1234.56')
        )
        assert result == (
            {1: Decimal('-100'), 2: Decimal('0'), 6: Decimal('0')},
            [[6, 1, Decimal('100')]],
            Decimal('1234.56')
        )
