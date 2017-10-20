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
from copy import deepcopy
import pytest

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.budget_balancer import (
    BudgetBalancer, BudgetBalancePlanError, do_budget_transfer
)
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.account import Account

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


class BudgetBalanceSetup(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.pp = Mock(spec_set=BiweeklyPayPeriod)
        type(self.pp).start_date = date(2017, 1, 1)
        type(self.pp).end_date = date(2017, 1, 13)
        self.standing = Mock(spec_set=Budget, is_periodic=False)
        type(self.standing).id = 9
        type(self.standing).name = 'standingBudget'
        self.periodic = Mock(spec_set=Budget, is_periodic=True)
        type(self.periodic).id = 22
        type(self.periodic).name = 'periodic22'
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

        def se_get_budget(budg_id):
            if budg_id == 1:
                return self.budg1
            if budg_id == 2:
                return self.budg2
            if budg_id == 3:
                return self.budg3
            if budg_id == 22:
                return self.periodic
            if budg_id == 9:
                return self.standing

        self.mock_sess.query.return_value.get.side_effect = se_get_budget
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(
                self.mock_sess, self.pp, self.standing, self.periodic
            )


class TestDoBudgetTransfer(BudgetBalanceSetup):

    def test_simple(self):
        t1 = Mock()
        t2 = Mock()
        tr1 = Mock()
        tr2 = Mock()
        acct = Mock()
        desc = 'Budget Transfer - 123.45 from one (1) to standingBudget (9)'
        with patch('%s.Transaction' % pbm, autospec=True) as mock_t:
            with patch('%s.TxnReconcile' % pbm, autospec=True) as mock_tr:
                mock_t.side_effect = [t1, t2]
                mock_tr.side_effect = [tr1, tr2]
                res = do_budget_transfer(
                    self.mock_sess,
                    self.pp.start_date,
                    Decimal('123.45'),
                    acct,
                    self.budg1,
                    self.standing,
                    notes='foo'
                )
        assert res == [t1, t2]
        assert mock_t.mock_calls == [
            call(
                date=self.pp.start_date,
                actual_amount=Decimal('123.45'),
                budgeted_amount=Decimal('123.45'),
                description=desc,
                account=acct,
                budget=self.budg1,
                notes='foo'
            ),
            call(
                date=self.pp.start_date,
                actual_amount=Decimal('-123.45'),
                budgeted_amount=Decimal('-123.45'),
                description=desc,
                account=acct,
                budget=self.standing,
                notes='foo'
            )
        ]
        assert mock_tr.mock_calls == [
            call(transaction=t1, note=desc),
            call(transaction=t2, note=desc)
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Account),
            call.query().get(1),
            call.add(t1),
            call.add(t2),
            call.add(tr1),
            call.add(tr2)
        ]


class TestInit(BudgetBalanceSetup):

    def test_init(self):
        self.mock_sess.reset_mock()
        with patch('%s._budgets_to_balance' % pb) as mock_budgets:
            mock_budgets.return_value = self.budgets
            self.cls = BudgetBalancer(
                self.mock_sess, self.pp, self.standing, self.periodic
            )
        assert self.cls._db == self.mock_sess
        assert self.cls._payperiod == self.pp
        assert self.cls._standing == self.standing
        assert self.cls._budgets == self.budgets
        assert self.mock_sess.mock_calls == [
            call.query(Account),
            call.query().get(1)
        ]
        assert self.cls._account == self.budg1
        assert self.cls._periodic == self.periodic


class TestBudgetsToBalance(BudgetBalanceSetup):

    def test_budgets_to_balance(self):
        b1 = Mock(spec_set=Budget, id=1, name='One')
        b2 = Mock(spec_set=Budget, id=2, name='Two')
        b3 = Mock(spec_set=Budget, id=3, name='Three')
        self.mock_sess.query.return_value.filter.\
            return_value.all.return_value = [b1, b2, b3]
        assert self.cls._budgets_to_balance() == {
            1: b1, 2: b2, 3: b3
        }
        assert len(self.mock_sess.mock_calls) == 5
        assert self.mock_sess.mock_calls[0] == call.query(Account)
        assert self.mock_sess.mock_calls[1] == call.query().get(1)
        assert self.mock_sess.mock_calls[2] == call.query(Budget)
        assert self.mock_sess.mock_calls[3][0] == 'query().filter'
        assert len(self.mock_sess.mock_calls[3][1]) == 3
        assert str(self.mock_sess.mock_calls[3][1][0]) == str(
            Budget.is_periodic.__eq__(True)
        )
        assert str(self.mock_sess.mock_calls[3][1][1]) == str(
            Budget.is_active.__eq__(True)
        )
        assert str(self.mock_sess.mock_calls[3][1][2]) == str(
            Budget.skip_balance.__eq__(False)
        )
        assert self.mock_sess.mock_calls[4] == call.query().filter().all()


class TestPlan(BudgetBalanceSetup):

    def test_simple(self):
        type(self.standing).current_balance = Decimal('123.45')
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('100')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('-100')},
            4: {'remaining': Decimal('986.34')}
        })
        to_balance = {1: Decimal('100'), 3: Decimal('-100')}

        def se_dob(klass, r):
            return r

        with patch('%s._do_plan_transfers' % pb, autospec=True) as mock_dpt:
            with patch(
                '%s._do_plan_standing_txfr' % pb, autospec=True
            ) as m_dpst:
                with patch(
                    '%s._do_overall_balance' % pb, autospec=True
                ) as mock_dob:
                    mock_dob.side_effect = se_dob
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
            'standing_after': Decimal('26.87'),
            'periodic_overage_id': 22,
            'periodic_overage_name': 'periodic22'
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
        assert mock_dob.mock_calls == [call(self.cls, result)]


class TestDoOverallBalance(BudgetBalanceSetup):

    def test_budget_remaining_not_zero(self):
        self.mock_sess.reset_mock()
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('100')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('-100')},
            4: {'remaining': Decimal('986.34')}
        })
        type(self.pp).overall_sums = PropertyMock(return_value={
            'remaining': Decimal('0')
        })
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        t5 = Mock(id=5, name='t5')
        t6 = Mock(id=6, name='t6')
        plan_result = {
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
            'standing_after': Decimal('26.87'),
            'periodic_overage_id': 22,
            'periodic_overage_name': 'periodic22'
        }
        with patch('%s.do_budget_transfer' % pbm, autospec=True) as mock_dbt:
            mock_dbt.side_effect = [[t1, t2], [t3, t4], [t5, t6]]
            with pytest.raises(RuntimeError) as ex:
                self.cls._do_overall_balance(plan_result)
        assert str(ex.value) == 'ERROR: expected budget 1 remaining sum to ' \
                                'be 0 after balancing, but was 100'
        assert mock_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('99'),
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('1'),
                self.cls._account, self.budg1, self.standing,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('10'),
                self.cls._account, self.standing, self.budg3,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.pp.mock_calls == [
            call.clear_cache()
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.rollback()
        ]

    def test_overall_remaining_zero(self):
        self.mock_sess.reset_mock()
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('0')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('0')},
            4: {'remaining': Decimal('0')}
        })
        type(self.pp).overall_sums = PropertyMock(return_value={
            'remaining': Decimal('0')
        })
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        t5 = Mock(id=5, name='t5')
        t6 = Mock(id=6, name='t6')
        plan_result = {
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
            'standing_after': Decimal('26.87'),
            'periodic_overage_id': 22,
            'periodic_overage_name': 'periodic22'
        }
        with patch('%s.do_budget_transfer' % pbm, autospec=True) as mock_dbt:
            mock_dbt.side_effect = [[t1, t2], [t3, t4], [t5, t6]]
            result = self.cls._do_overall_balance(plan_result)
        assert result == plan_result
        assert mock_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('99'),
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('1'),
                self.cls._account, self.budg1, self.standing,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('10'),
                self.cls._account, self.standing, self.budg3,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.pp.mock_calls == [
            call.clear_cache()
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.rollback()
        ]

    def test_overall_remaining_negative(self):
        type(self.standing).current_balance = Decimal('1023.45')
        self.mock_sess.reset_mock()
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('0')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('0')},
            4: {'remaining': Decimal('0')},
            22: {'remaining': Decimal('10.10')}
        })
        type(self.pp).overall_sums = PropertyMock(return_value={
            'remaining': Decimal('-456.78')
        })
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        t5 = Mock(id=5, name='t5')
        t6 = Mock(id=6, name='t6')
        t7 = Mock(id=7, name='t7')
        t8 = Mock(id=8, name='t8')
        plan_result = {
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
            'standing_before': Decimal('1023.45'),
            'standing_id': 9,
            'standing_name': 'standingBudget',
            'standing_after': Decimal('987.65'),
            'periodic_overage_id': 22,
            'periodic_overage_name': 'periodic22'
        }
        expected = deepcopy(plan_result)
        expected['transfers'].append(
            [self.standing.id, self.periodic.id, Decimal('456.78')]
        )
        expected['standing_after'] = Decimal('530.87')
        expected['budgets'][22] = {
            'before': Decimal('10.10'),
            'after': Decimal('-446.68'),
            'name': 'periodic22'
        }
        with patch('%s.do_budget_transfer' % pbm, autospec=True) as mock_dbt:
            mock_dbt.side_effect = [[t1, t2], [t3, t4], [t5, t6], [t7, t8]]
            result = self.cls._do_overall_balance(plan_result)
        assert result == expected
        assert mock_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('99'),
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('1'),
                self.cls._account, self.budg1, self.standing,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('10'),
                self.cls._account, self.standing, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('456.78'),
                self.cls._account, self.standing, self.periodic,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.pp.mock_calls == [
            call.clear_cache()
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.rollback()
        ]

    def test_overall_remaining_negative_less_than_standing(self):
        type(self.standing).current_balance = Decimal('123.45')
        self.mock_sess.reset_mock()
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('0')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('0')},
            4: {'remaining': Decimal('0')},
            22: {'remaining': Decimal('10.10')}
        })
        type(self.pp).overall_sums = PropertyMock(return_value={
            'remaining': Decimal('-456.78')
        })
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        t5 = Mock(id=5, name='t5')
        t6 = Mock(id=6, name='t6')
        t7 = Mock(id=7, name='t7')
        t8 = Mock(id=8, name='t8')
        plan_result = {
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
            'standing_after': Decimal('123.45'),
            'periodic_overage_id': 22,
            'periodic_overage_name': 'periodic22'
        }
        expected = deepcopy(plan_result)
        expected['transfers'].append(
            [self.standing.id, self.periodic.id, Decimal('123.45')]
        )
        expected['standing_after'] = Decimal('0')
        expected['budgets'][22] = {
            'before': Decimal('10.10'),
            'after': Decimal('-113.35'),
            'name': 'periodic22'
        }
        with patch('%s.do_budget_transfer' % pbm, autospec=True) as mock_dbt:
            mock_dbt.side_effect = [[t1, t2], [t3, t4], [t5, t6], [t7, t8]]
            result = self.cls._do_overall_balance(plan_result)
        assert result == expected
        assert mock_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('99'),
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('1'),
                self.cls._account, self.budg1, self.standing,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('10'),
                self.cls._account, self.standing, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('123.45'),
                self.cls._account, self.standing, self.periodic,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.pp.mock_calls == [
            call.clear_cache()
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.rollback()
        ]

    def test_overall_remaining_negative_periodic_in_budgets(self):
        type(self.standing).current_balance = Decimal('1023.45')
        self.mock_sess.reset_mock()
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('0')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('0')},
            4: {'remaining': Decimal('0')},
            22: {'remaining': Decimal('10.10')}
        })
        type(self.pp).overall_sums = PropertyMock(return_value={
            'remaining': Decimal('-456.78')
        })
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        t5 = Mock(id=5, name='t5')
        t6 = Mock(id=6, name='t6')
        t7 = Mock(id=7, name='t7')
        t8 = Mock(id=8, name='t8')
        plan_result = {
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
                },
                22: {
                    'before': Decimal('10.10'),
                    'after': Decimal('10.10'),
                    'name': 'periodic22'
                }
            },
            'standing_before': Decimal('1023.45'),
            'standing_id': 9,
            'standing_name': 'standingBudget',
            'standing_after': Decimal('987.65'),
            'periodic_overage_id': 22,
            'periodic_overage_name': 'periodic22'
        }
        expected = deepcopy(plan_result)
        expected['transfers'].append(
            [self.standing.id, self.periodic.id, Decimal('456.78')]
        )
        expected['standing_after'] = Decimal('530.87')
        expected['budgets'][22] = {
            'before': Decimal('10.10'),
            'after': Decimal('-446.68'),
            'name': 'periodic22'
        }
        with patch('%s.do_budget_transfer' % pbm, autospec=True) as mock_dbt:
            mock_dbt.side_effect = [[t1, t2], [t3, t4], [t5, t6], [t7, t8]]
            result = self.cls._do_overall_balance(plan_result)
        assert result == expected
        assert mock_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('99'),
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('1'),
                self.cls._account, self.budg1, self.standing,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('10'),
                self.cls._account, self.standing, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('456.78'),
                self.cls._account, self.standing, self.periodic,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.pp.mock_calls == [
            call.clear_cache()
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.rollback()
        ]

    def test_overall_remaining_positive(self):
        self.mock_sess.reset_mock()
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('0')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('0')},
            4: {'remaining': Decimal('0')},
            22: {'remaining': Decimal('0')}
        })
        type(self.pp).overall_sums = PropertyMock(return_value={
            'remaining': Decimal('789.12')
        })
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        t5 = Mock(id=5, name='t5')
        t6 = Mock(id=6, name='t6')
        t7 = Mock(id=7, name='t7')
        t8 = Mock(id=8, name='t8')
        plan_result = {
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
            'standing_after': Decimal('26.87'),
            'periodic_overage_id': 22,
            'periodic_overage_name': 'periodic22'
        }
        expected = deepcopy(plan_result)
        expected['transfers'].append(
            [self.periodic.id, self.standing.id, Decimal('789.12')]
        )
        expected['standing_after'] = Decimal('912.57')
        expected['budgets'][22] = {
            'before': Decimal('0'),
            'after': Decimal('-789.12'),
            'name': 'periodic22'
        }
        with patch('%s.do_budget_transfer' % pbm, autospec=True) as mock_dbt:
            mock_dbt.side_effect = [[t1, t2], [t3, t4], [t5, t6], [t7, t8]]
            result = self.cls._do_overall_balance(plan_result)
        assert result == plan_result
        assert mock_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('99'),
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('1'),
                self.cls._account, self.budg1, self.standing,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('10'),
                self.cls._account, self.standing, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('789.12'),
                self.cls._account, self.periodic, self.standing,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.pp.mock_calls == [
            call.clear_cache()
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.rollback()
        ]

    def test_overall_remaining_positive_periodic_in_budgets(self):
        self.mock_sess.reset_mock()
        type(self.pp).budget_sums = PropertyMock(return_value={
            1: {'remaining': Decimal('0')},
            2: {'remaining': Decimal('0')},
            3: {'remaining': Decimal('0')},
            4: {'remaining': Decimal('0')},
            22: {'remaining': Decimal('0')}
        })
        type(self.pp).overall_sums = PropertyMock(return_value={
            'remaining': Decimal('789.12')
        })
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        t5 = Mock(id=5, name='t5')
        t6 = Mock(id=6, name='t6')
        t7 = Mock(id=7, name='t7')
        t8 = Mock(id=8, name='t8')
        plan_result = {
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
                },
                22: {
                    'before': Decimal('0'),
                    'after': Decimal('0'),
                    'name': 'periodic22'
                }
            },
            'standing_before': Decimal('123.45'),
            'standing_id': 9,
            'standing_name': 'standingBudget',
            'standing_after': Decimal('26.87'),
            'periodic_overage_id': 22,
            'periodic_overage_name': 'periodic22'
        }
        expected = deepcopy(plan_result)
        expected['transfers'].append(
            [self.periodic.id, self.standing.id, Decimal('789.12')]
        )
        expected['standing_after'] = Decimal('912.57')
        expected['budgets'][22] = {
            'before': Decimal('0'),
            'after': Decimal('-789.12'),
            'name': 'periodic22'
        }
        with patch('%s.do_budget_transfer' % pbm, autospec=True) as mock_dbt:
            mock_dbt.side_effect = [[t1, t2], [t3, t4], [t5, t6], [t7, t8]]
            result = self.cls._do_overall_balance(plan_result)
        assert result == plan_result
        assert mock_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('99'),
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('1'),
                self.cls._account, self.budg1, self.standing,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('10'),
                self.cls._account, self.standing, self.budg3,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('789.12'),
                self.cls._account, self.periodic, self.standing,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.pp.mock_calls == [
            call.clear_cache()
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(9),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.rollback()
        ]


class TestDoPlanStandingTxfr(BudgetBalanceSetup):

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


class TestDoPlanTransfers(BudgetBalanceSetup):

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


class TestApply(BudgetBalanceSetup):

    def test_from_json(self):
        plan_result = {
            'transfers': [
                [1, 2, 92.34],
                [1, 3, -84.32]
            ]
        }
        actual = deepcopy(plan_result)
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        # need to patch db.query.get to return Budget object
        with patch('%s.plan' % pb, autospec=True) as mock_plan:
            with patch('%s.do_budget_transfer' % pbm, autospec=True) as m_dbt:
                mock_plan.return_value = actual
                m_dbt.side_effect = [[t1, t2], [t3, t4]]
                res = self.cls.apply(plan_result)
        assert res == [t1, t2, t3, t4]
        assert mock_plan.mock_calls == [call(self.cls)]
        assert m_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), 92.34,
                self.cls._account, self.budg1, self.budg2,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), -84.32,
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Account),
            call.query().get(1),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(2),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.commit()
        ]

    def test_not_from_json(self):
        plan_result = {
            'transfers': [
                [1, 2, Decimal('92.34')],
                [1, 3, Decimal('-84.32')]
            ]
        }
        actual = deepcopy(plan_result)
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        # need to patch db.query.get to return Budget object
        with patch('%s.plan' % pb, autospec=True) as mock_plan:
            with patch('%s.do_budget_transfer' % pbm, autospec=True) as m_dbt:
                mock_plan.return_value = actual
                m_dbt.side_effect = [[t1, t2], [t3, t4]]
                res = self.cls.apply(plan_result, from_json=False)
        assert res == [t1, t2, t3, t4]
        assert mock_plan.mock_calls == [call(self.cls)]
        assert m_dbt.mock_calls == [
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('92.34'),
                self.cls._account, self.budg1, self.budg2,
                notes='added by BudgetBalancer'
            ),
            call(
                self.mock_sess, date(2017, 1, 13), Decimal('-84.32'),
                self.cls._account, self.budg1, self.budg3,
                notes='added by BudgetBalancer'
            )
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Account),
            call.query().get(1),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(2),
            call.query(Budget),
            call.query().get(1),
            call.query(Budget),
            call.query().get(3),
            call.flush(),
            call.commit()
        ]

    def test_no_match(self):
        plan_result = {
            'transfers': [
                [1, 2, Decimal('92.34')],
                [1, 3, Decimal('-84.32')],
                [1, 2, Decimal('102.34')]
            ]
        }
        actual = {
            'transfers': [
                [1, 2, Decimal('92.34')],
                [1, 3, Decimal('-84.32')]
            ]
        }
        t1 = Mock(id=1, name='t1')
        t2 = Mock(id=2, name='t2')
        t3 = Mock(id=3, name='t3')
        t4 = Mock(id=4, name='t4')
        # need to patch db.query.get to return Budget object
        with patch('%s.plan' % pb, autospec=True) as mock_plan:
            with patch('%s.do_budget_transfer' % pbm, autospec=True) as m_dbt:
                mock_plan.return_value = actual
                m_dbt.side_effect = [[t1, t2], [t3, t4]]
                with pytest.raises(BudgetBalancePlanError) as ex:
                    self.cls.apply(plan_result, from_json=False)
        assert ex.value.actual == actual
        assert ex.value.expected == plan_result
        assert mock_plan.mock_calls == [call(self.cls)]
        assert m_dbt.mock_calls == []
        assert self.mock_sess.mock_calls == [
            call.query(Account),
            call.query().get(1),
        ]
