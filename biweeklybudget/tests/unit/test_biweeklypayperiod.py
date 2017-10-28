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
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.scheduled_transaction import ScheduledTransaction
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.tests.unit_helpers import binexp_to_dict
from biweeklybudget.utils import dtnow

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call, DEFAULT
else:
    from unittest.mock import Mock, patch, call, DEFAULT

pbm = 'biweeklybudget.biweeklypayperiod'
pb = '%s.BiweeklyPayPeriod' % pbm


class TestInit(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_init(self):
        cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)
        assert cls._start_date == date(2017, 3, 17)
        assert cls._end_date == date(2017, 3, 30)
        assert cls._db == self.mock_sess
        assert cls._data_cache == {}

    def test_init_datetime(self):
        cls = BiweeklyPayPeriod(datetime(2017, 3, 17), self.mock_sess)
        assert cls._start_date == date(2017, 3, 17)
        assert cls._end_date == date(2017, 3, 30)
        assert cls._db == self.mock_sess
        assert cls._data_cache == {}


class TestProperties(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_period_interval(self):
        assert self.cls.period_interval == timedelta(days=14)

    def test_period_length(self):
        assert self.cls.period_length == timedelta(days=13)

    def test_start_date(self):
        assert self.cls.start_date == date(2017, 3, 17)

    def test_end_date(self):
        assert self.cls.end_date == date(2017, 3, 30)

    def test_next(self):
        assert self.cls.next == BiweeklyPayPeriod(
            date(2017, 3, 31), self.mock_sess)

    def test_previous(self):
        assert self.cls.previous == BiweeklyPayPeriod(
            date(2017, 3, 3), self.mock_sess)


class TestMagicMethods(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_repr(self):
        assert str(self.cls) == '<BiweeklyPayPeriod(2017-03-17)>'

    @pytest.mark.skipif(sys.version_info[0] >= 3, reason='py2 only')
    def test_ordering_py27(self):
        assert self.cls < BiweeklyPayPeriod(date(2017, 4, 16), self.mock_sess)
        assert self.cls > BiweeklyPayPeriod(date(2017, 2, 13), self.mock_sess)
        assert self.cls == BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)
        self.cls < 2
        self.cls.__eq__(2)

    @pytest.mark.skipif(sys.version_info[0] < 3, reason='py3 only')
    def test_ordering_py3(self):
        assert self.cls < BiweeklyPayPeriod(date(2017, 4, 16), self.mock_sess)
        assert self.cls > BiweeklyPayPeriod(date(2017, 2, 13), self.mock_sess)
        assert self.cls == BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)
        with pytest.raises(TypeError):
            self.cls < 2
        self.cls.__eq__(2)


class TestForDate(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 3, 17))
    def test_period_for_date(self):
        assert BiweeklyPayPeriod.period_for_date(
            date(2017, 3, 16), self.mock_sess) == BiweeklyPayPeriod(
            date(2017, 3, 3), self.mock_sess)
        assert BiweeklyPayPeriod.period_for_date(
            date(2017, 3, 17), self.mock_sess) == BiweeklyPayPeriod(
            date(2017, 3, 17), self.mock_sess)
        assert BiweeklyPayPeriod.period_for_date(
            date(2017, 3, 18), self.mock_sess) == BiweeklyPayPeriod(
            date(2017, 3, 17), self.mock_sess)
        assert BiweeklyPayPeriod.period_for_date(
            date(2017, 3, 30), self.mock_sess) == BiweeklyPayPeriod(
            date(2017, 3, 17), self.mock_sess)
        assert BiweeklyPayPeriod.period_for_date(
            date(2017, 3, 31), self.mock_sess) == BiweeklyPayPeriod(
            date(2017, 3, 31), self.mock_sess)
        assert BiweeklyPayPeriod.period_for_date(
            date(2017, 1, 21), self.mock_sess) == BiweeklyPayPeriod(
            date(2017, 1, 20), self.mock_sess)
        assert BiweeklyPayPeriod.period_for_date(
            date(2017, 5, 2), self.mock_sess) == BiweeklyPayPeriod(
            date(2017, 4, 28), self.mock_sess)


class TestFilterQuery(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_filter_query(self):
        q = Mock()
        res = self.cls.filter_query(q, OFXTransaction.date_posted)
        assert len(q.mock_calls) == 1
        kall = q.mock_calls[0]
        assert kall[0] == 'filter'
        a = OFXTransaction.date_posted >= self.cls.start_date
        b = OFXTransaction.date_posted <= self.cls.end_date
        assert kall[1][0].compare(a) is True
        assert kall[1][1].compare(b) is True
        assert res == q.filter.return_value


class TestTransactions(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_transactions(self):
        mock_res = Mock()
        with patch('%s.filter_query' % pb, autospec=True) as mock_filter:
            mock_filter.return_value = mock_res
            res = self.cls._transactions()
        assert res == mock_res
        assert mock_filter.mock_calls == [
            call(self.cls, self.mock_sess.query.return_value, Transaction.date)
        ]
        assert self.mock_sess.mock_calls == [
            call.query(Transaction)
        ]


class TestSTDate(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_scheduled_transactions_date(self):
        mock_res = Mock()
        with patch('%s.filter_query' % pb, autospec=True) as mock_filter:
            mock_filter.return_value = mock_res
            res = self.cls._scheduled_transactions_date()
        assert res == mock_res
        assert mock_filter.mock_calls == [
            call(
                self.cls,
                self.mock_sess.query.return_value.filter.return_value,
                ScheduledTransaction.date
            )
        ]
        assert len(self.mock_sess.mock_calls) == 2
        assert self.mock_sess.mock_calls[0] == call.query(ScheduledTransaction)
        assert self.mock_sess.mock_calls[1][0] == 'query().filter'
        expected = ScheduledTransaction.is_active.__eq__(True)
        assert str(expected) == str(
            self.mock_sess.mock_calls[1][1][0]
        )


class TestSTPeriod(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_scheduled_transactions_per_period(self):
        res = self.cls._scheduled_transactions_per_period()
        frv = self.mock_sess.query.return_value.filter.return_value
        assert res == frv.order_by.return_value
        assert len(self.mock_sess.mock_calls) == 3
        assert self.mock_sess.mock_calls[0] == call.query(ScheduledTransaction)
        kall = self.mock_sess.mock_calls[1]
        assert kall[0] == 'query().filter'
        expected = ScheduledTransaction.schedule_type.__eq__('per period')
        assert binexp_to_dict(expected) == binexp_to_dict(kall[1][0])
        kall = self.mock_sess.mock_calls[2]
        assert kall[0] == 'query().filter().order_by'
        assert str(kall[1][0]) == str(asc(ScheduledTransaction.num_per_period))
        assert str(kall[1][1]) == str(asc(ScheduledTransaction.amount))


class TestSTMonthly(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)

    def test_contiguous(self):
        cls = BiweeklyPayPeriod(date(2017, 3, 2), self.mock_sess)
        res = cls._scheduled_transactions_monthly()
        assert res == self.mock_sess.query.return_value.filter.return_value
        assert len(self.mock_sess.mock_calls) == 2
        assert self.mock_sess.mock_calls[0] == call.query(ScheduledTransaction)
        kall = self.mock_sess.mock_calls[1]
        assert kall[0] == 'query().filter'
        expected = [
            ScheduledTransaction.schedule_type.__eq__('monthly'),
            ScheduledTransaction.is_active.__eq__(True),
            ScheduledTransaction.day_of_month.__le__(15),
            ScheduledTransaction.day_of_month.__ge__(2)
        ]
        assert binexp_to_dict(kall[1][0]) == binexp_to_dict(expected[0])
        assert str(kall[1][1]) == str(expected[1])
        assert binexp_to_dict(kall[1][2]) == binexp_to_dict(expected[2])
        assert binexp_to_dict(kall[1][3]) == binexp_to_dict(expected[3])

    def test_crossmonth(self):
        cls = BiweeklyPayPeriod(date(2017, 3, 24), self.mock_sess)
        mock_or_result = Mock()
        with patch('%s.or_' % pbm) as mock_or:
            mock_or.return_value = mock_or_result
            res = cls._scheduled_transactions_monthly()
        assert res == self.mock_sess.query.return_value.filter.return_value
        assert len(self.mock_sess.mock_calls) == 2
        assert self.mock_sess.mock_calls[0] == call.query(ScheduledTransaction)
        kall = self.mock_sess.mock_calls[1]
        assert kall[0] == 'query().filter'
        expected = ScheduledTransaction.schedule_type.__eq__('monthly')
        assert binexp_to_dict(kall[1][0]) == binexp_to_dict(expected)
        assert str(kall[1][1]) == str(
            ScheduledTransaction.is_active.__eq__(True)
        )
        assert kall[1][2] == mock_or_result
        kall = mock_or.mock_calls[0]
        assert len(mock_or.mock_calls) == 1
        expected = [
            ScheduledTransaction.day_of_month.__le__(6),
            ScheduledTransaction.day_of_month.__ge__(24)
        ]
        for idx, exp in enumerate(expected):
            assert binexp_to_dict(kall[1][idx]) == binexp_to_dict(exp)


class TestTransactionsList(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_simple(self):
        m = Mock()
        self.cls._data_cache = {'all_trans_list': m}
        assert self.cls.transactions_list == m


class TestBudgetSums(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_simple(self):
        m = Mock()
        self.cls._data_cache = {'budget_sums': m}
        assert self.cls.budget_sums == m


class TestOverallSums(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_simple(self):
        m = Mock()
        self.cls._data_cache = {'overall_sums': m}
        assert self.cls.overall_sums == m


class TestIncomeBudgetIDs(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 7), self.mock_sess)

    def test_no_cache(self):
        self.cls._income_budget_id_list = None
        budgets = [
            Mock(spec_set=Budget, is_income=True, id=2),
            Mock(spec_set=Budget, is_income=True, id=4)
        ]
        self.mock_sess.query.return_value.filter.return_value.all.return_value \
            = budgets
        assert self.cls._income_budget_ids == [2, 4]
        assert self.cls._income_budget_id_list == [2, 4]
        assert len(self.mock_sess.mock_calls) == 3
        assert self.mock_sess.mock_calls[0] == call.query(Budget)
        kall = self.mock_sess.mock_calls[1]
        assert kall[0] == 'query().filter'
        assert str(kall[1][0]) == str(Budget.is_income.__eq__(True))
        assert self.mock_sess.mock_calls[2] == call.query().filter().all()

    def test_cache(self):
        self.cls._income_budget_id_list = [1, 2]
        budgets = [
            Mock(spec_set=Budget, is_income=False, id=1),
            Mock(spec_set=Budget, is_income=True, id=2),
            Mock(spec_set=Budget, is_income=False, id=3),
            Mock(spec_set=Budget, is_income=True, id=4)
        ]
        self.mock_sess.query.return_value.filter.return_value.all.return_value \
            = budgets
        assert self.cls._income_budget_ids == [1, 2]
        assert self.cls._income_budget_id_list == [1, 2]
        assert len(self.mock_sess.mock_calls) == 0


class TestData(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_initial(self):
        mock_t = Mock()
        mock_std = Mock()
        mock_stpp = Mock()
        mock_stm = Mock()
        mock_mct = Mock()
        mock_mbs = Mock()
        mock_mos = Mock()
        with patch.multiple(
            pb,
            autospec=True,
            _transactions=DEFAULT,
            _scheduled_transactions_date=DEFAULT,
            _scheduled_transactions_per_period=DEFAULT,
            _scheduled_transactions_monthly=DEFAULT,
            _make_combined_transactions=DEFAULT,
            _make_budget_sums=DEFAULT,
            _make_overall_sums=DEFAULT
        ) as mocks:
            mocks['_transactions'].return_value.all.return_value = mock_t
            mocks['_scheduled_transactions_date'
                  ''].return_value.all.return_value = mock_std
            mocks['_scheduled_transactions_per_period'
                  ''].return_value.all.return_value = mock_stpp
            mocks['_scheduled_transactions_monthly'
                  ''].return_value.all.return_value = mock_stm
            mocks['_make_combined_transactions'].return_value = mock_mct
            mocks['_make_budget_sums'].return_value = mock_mbs
            mocks['_make_overall_sums'].return_value = mock_mos
            res = self.cls._data
        assert res == {
            'transactions': mock_t,
            'st_date': mock_std,
            'st_per_period': mock_stpp,
            'st_monthly': mock_stm,
            'all_trans_list': mock_mct,
            'budget_sums': mock_mbs,
            'overall_sums': mock_mos
        }
        assert mocks['_transactions'].mock_calls == [
            call(self.cls), call().all()
        ]
        assert mocks['_scheduled_transactions_date'].mock_calls == [
            call(self.cls), call().all()
        ]
        assert mocks['_scheduled_transactions_per_period'].mock_calls == [
            call(self.cls), call().all()
        ]
        assert mocks['_scheduled_transactions_monthly'].mock_calls == [
            call(self.cls), call().all()
        ]
        assert mocks['_make_combined_transactions'].mock_calls == [
            call(self.cls)
        ]
        assert mocks['_make_budget_sums'].mock_calls == [
            call(self.cls)
        ]
        assert mocks['_make_overall_sums'].mock_calls == [
            call(self.cls)
        ]

    def test_cached(self):
        mock_t = Mock()
        mock_std = Mock()
        mock_stpp = Mock()
        mock_stm = Mock()
        mock_mct = Mock()
        mock_mbs = Mock()
        mock_mos = Mock()
        with patch.multiple(
            pb,
            autospec=True,
            _transactions=DEFAULT,
            _scheduled_transactions_date=DEFAULT,
            _scheduled_transactions_per_period=DEFAULT,
            _scheduled_transactions_monthly=DEFAULT,
            _make_combined_transactions=DEFAULT,
            _make_budget_sums=DEFAULT,
            _make_overall_sums=DEFAULT
        ) as mocks:
            mocks['_transactions'].return_value.all.return_value = mock_t
            mocks['_scheduled_transactions_date'
                  ''].return_value.all.return_value = mock_std
            mocks['_scheduled_transactions_per_period'
                  ''].return_value.all.return_value = mock_stpp
            mocks['_scheduled_transactions_monthly'
                  ''].return_value.all.return_value = mock_stm
            mocks['_make_combined_transactions'].return_value = mock_mct
            mocks['_make_budget_sums'].return_value = mock_mbs
            mocks['_make_overall_sums'].return_value = mock_mos
            self.cls._data_cache = {'foo': 'bar'}
            res = self.cls._data
        assert res == {'foo': 'bar'}
        assert mocks['_transactions'].mock_calls == []
        assert mocks['_scheduled_transactions_date'].mock_calls == []
        assert mocks['_scheduled_transactions_per_period'].mock_calls == []
        assert mocks['_scheduled_transactions_monthly'].mock_calls == []
        assert mocks['_make_combined_transactions'].mock_calls == []
        assert mocks['_make_budget_sums'].mock_calls == []
        assert mocks['_make_overall_sums'].mock_calls == []


class TestMakeCombinedTransactions(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_all(self):

        def se_trans_dict(_, t):
            if t._mock_name.startswith('per_period'):
                return {'name': t._mock_name, 'amount': t.amount}
            print(t)
            return {
                'date': date(year=2017, month=3, day=t.day),
                'name': t._mock_name,
                'amount': t.amount
            }

        mock_per_periodA = Mock(num_per_period=1, name='per_period_A', amount=8)
        mock_per_periodB = Mock(num_per_period=3, name='per_period_B', amount=9)
        self.cls._data_cache = {
            'transactions': [
                Mock(name='t1', day=1, scheduled_trans_id=1, amount=1),
                Mock(name='t2', day=4, scheduled_trans_id=None, amount=2),
                Mock(name='t3', day=6, scheduled_trans_id=2, amount=3)
            ],
            'st_date': [
                Mock(name='std1', day=2, id=1, amount=4),
                Mock(name='std2', day=5, amount=5)
            ],
            'st_monthly': [
                Mock(name='stm1', day=3, amount=6),
                Mock(name='stm2', day=6, id=2, amount=7)
            ],
            'st_per_period': [
                mock_per_periodA,
                mock_per_periodB
            ]
        }
        with patch('%s._trans_dict' % pb, autospec=True) as mock_t_dict:
            mock_t_dict.side_effect = se_trans_dict
            res = self.cls._make_combined_transactions()
        assert res == [
            {'name': 'per_period_A', 'amount': 8},
            {'name': 'per_period_B', 'amount': 9},
            {'name': 'per_period_B', 'amount': 9},
            {'name': 'per_period_B', 'amount': 9},
            {
                'name': 't1',
                'date': date(year=2017, month=3, day=1),
                'amount': 1
            },
            {
                'name': 'stm1',
                'date': date(year=2017, month=3, day=3),
                'amount': 6
            },
            {
                'name': 't2',
                'date': date(year=2017, month=3, day=4),
                'amount': 2
            },
            {
                'name': 'std2',
                'date': date(year=2017, month=3, day=5),
                'amount': 5
            },
            {
                'name': 't3',
                'date': date(2017, 3, 6),
                'amount': 3
            }
        ]


class TestMakeBudgetSums(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 7), self.mock_sess)

    def test_scheduled_income(self):
        self.cls._data_cache = {
            'all_trans_list': [
                {
                    'type': 'ScheduledTransaction',
                    'amount': Decimal('11.11'),
                    'budgeted_amount': None,
                    'budget_id': 1
                },
                {
                    'type': 'Transaction',
                    'amount': Decimal('22.22'),
                    'budgeted_amount': None,
                    'budget_id': 1
                },
                {
                    'type': 'Transaction',
                    'amount': Decimal('22.22'),
                    'budgeted_amount': Decimal('20.20'),
                    'budget_id': 1
                },
                {
                    'type': 'Transaction',
                    'amount': Decimal('33.33'),
                    'budgeted_amount': Decimal('33.33'),
                    'budget_id': 2
                },
                {
                    'type': 'ScheduledTransaction',
                    'amount': Decimal('-1234.56'),
                    'budgeted_amount': Decimal('-1234.56'),
                    'budget_id': 4
                }
            ]
        }
        budgets = [
            Mock(
                spec_set=Budget, starting_balance=Decimal('123.45'), id=1,
                is_income=False
            ),
            Mock(
                spec_set=Budget, starting_balance=Decimal('456.78'), id=2,
                is_income=False
            ),
            Mock(
                spec_set=Budget, starting_balance=Decimal('789.10'), id=3,
                is_income=False
            ),
            Mock(
                spec_set=Budget, starting_balance=Decimal('0'), id=4,
                is_income=True
            )
        ]
        self.mock_sess.query.return_value.filter.return_value.all.return_value \
            = budgets
        res = self.cls._make_budget_sums()
        assert res == {
            1: {
                'budget_amount': Decimal('123.45'),
                'allocated': Decimal('53.53'),
                'spent': Decimal('44.44'),
                'trans_total': Decimal('55.55'),
                'is_income': False,
                'remaining': Decimal('67.90')
            },
            2: {
                'budget_amount': Decimal('456.78'),
                'allocated': Decimal('33.33'),
                'spent': Decimal('33.33'),
                'trans_total': Decimal('33.33'),
                'is_income': False,
                'remaining': Decimal('423.45')
            },
            3: {
                'budget_amount': Decimal('789.10'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': False,
                'remaining': Decimal('789.10')
            },
            4: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('-1234.56'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('-1234.56'),
                'is_income': True,
                'remaining': Decimal('1234.56')
            }
        }
        assert len(self.mock_sess.mock_calls) == 3
        assert self.mock_sess.mock_calls[0] == call.query(Budget)
        kall = self.mock_sess.mock_calls[1]
        assert kall[0] == 'query().filter'
        expected = [
            Budget.is_active.__eq__(True),
            Budget.is_periodic.__eq__(True)
        ]
        for idx, exp in enumerate(expected):
            assert str(kall[1][idx]) == str(expected[idx])
        assert self.mock_sess.mock_calls[2] == call.query().filter().all()

    def test_actual_income(self):
        self.cls._data_cache = {
            'all_trans_list': [
                {
                    'type': 'ScheduledTransaction',
                    'amount': Decimal('11.11'),
                    'budgeted_amount': None,
                    'budget_id': 1
                },
                {
                    'type': 'Transaction',
                    'amount': Decimal('22.22'),
                    'budgeted_amount': None,
                    'budget_id': 1
                },
                {
                    'type': 'Transaction',
                    'amount': Decimal('22.22'),
                    'budgeted_amount': Decimal('20.20'),
                    'budget_id': 1
                },
                {
                    'type': 'Transaction',
                    'amount': Decimal('33.33'),
                    'budgeted_amount': Decimal('33.33'),
                    'budget_id': 2
                },
                {
                    'type': 'Transaction',
                    'amount': Decimal('-1234.56'),
                    'budgeted_amount': Decimal('-1234.56'),
                    'budget_id': 4
                }
            ]
        }
        budgets = [
            Mock(
                spec_set=Budget, starting_balance=Decimal('123.45'), id=1,
                is_income=False
            ),
            Mock(
                spec_set=Budget, starting_balance=Decimal('456.78'), id=2,
                is_income=False
            ),
            Mock(
                spec_set=Budget, starting_balance=Decimal('789.10'), id=3,
                is_income=False
            ),
            Mock(
                spec_set=Budget, starting_balance=Decimal('0'), id=4,
                is_income=True
            )
        ]
        self.mock_sess.query.return_value.filter.return_value.all.return_value \
            = budgets
        res = self.cls._make_budget_sums()
        assert res == {
            1: {
                'budget_amount': Decimal('123.45'),
                'allocated': Decimal('53.53'),
                'spent': Decimal('44.44'),
                'trans_total': Decimal('55.55'),
                'is_income': False,
                'remaining': Decimal('67.90')
            },
            2: {
                'budget_amount': Decimal('456.78'),
                'allocated': Decimal('33.33'),
                'spent': Decimal('33.33'),
                'trans_total': Decimal('33.33'),
                'is_income': False,
                'remaining': Decimal('423.45')
            },
            3: {
                'budget_amount': Decimal('789.10'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': False,
                'remaining': Decimal('789.10')
            },
            4: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('-1234.56'),
                'spent': Decimal('-1234.56'),
                'trans_total': Decimal('-1234.56'),
                'is_income': True,
                'remaining': Decimal('1234.56')
            }
        }
        assert len(self.mock_sess.mock_calls) == 3
        assert self.mock_sess.mock_calls[0] == call.query(Budget)
        kall = self.mock_sess.mock_calls[1]
        assert kall[0] == 'query().filter'
        expected = [
            Budget.is_active.__eq__(True),
            Budget.is_periodic.__eq__(True)
        ]
        for idx, exp in enumerate(expected):
            assert str(kall[1][idx]) == str(expected[idx])
        assert self.mock_sess.mock_calls[2] == call.query().filter().all()


class TestMakeOverallSums(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)

    def test_past(self):
        cls = BiweeklyPayPeriod(date(2017, 3, 7), self.mock_sess)
        assert cls.is_in_past is True
        cls._data_cache['budget_sums'] = {
            1: {
                'budget_amount': Decimal('123.45'),
                'allocated': Decimal('53.53'),
                'spent': Decimal('44.44'),
                'trans_total': Decimal('55.55'),
                'is_income': False
            },
            2: {
                'budget_amount': Decimal('10.00'),
                'allocated': Decimal('33.33'),
                'spent': Decimal('33.33'),
                'trans_total': Decimal('33.33'),
                'is_income': False
            },
            3: {
                'budget_amount': Decimal('789.10'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': False
            },
            4: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('-1192.56'),
                'spent': Decimal('-254.38'),
                'trans_total': Decimal('-1234.56'),
                'is_income': True
            }
        }
        assert cls._make_overall_sums() == {
            'allocated': Decimal('945.88'),
            'spent': Decimal('77.77'),
            'income': Decimal('1234.56'),
            'remaining': Decimal('1156.79')
        }

    def test_current(self):
        cls = BiweeklyPayPeriod(
            dtnow().date() - timedelta(days=4), self.mock_sess
        )
        assert cls.is_in_past is False
        cls._data_cache['budget_sums'] = {
            1: {
                'budget_amount': Decimal('123.45'),
                'allocated': Decimal('53.53'),
                'spent': Decimal('44.44'),
                'trans_total': Decimal('55.55'),
                'is_income': False
            },
            2: {
                'budget_amount': Decimal('10.00'),
                'allocated': Decimal('33.33'),
                'spent': Decimal('33.33'),
                'trans_total': Decimal('33.33'),
                'is_income': False
            },
            3: {
                'budget_amount': Decimal('789.10'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': False
            },
            4: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('-1192.56'),
                'spent': Decimal('-254.38'),
                'trans_total': Decimal('-1234.56'),
                'is_income': True
            }
        }
        assert cls._make_overall_sums() == {
            'allocated': Decimal('945.88'),
            'spent': Decimal('77.77'),
            'income': Decimal('1234.56'),
            'remaining': Decimal('288.68')
        }

    def test_future(self):
        cls = BiweeklyPayPeriod(
            dtnow().date() + timedelta(days=24), self.mock_sess
        )
        assert cls.is_in_past is False
        cls._data_cache['budget_sums'] = {
            1: {
                'budget_amount': Decimal('123.45'),
                'allocated': Decimal('53.53'),
                'spent': Decimal('44.44'),
                'trans_total': Decimal('55.55'),
                'is_income': False
            },
            2: {
                'budget_amount': Decimal('10.00'),
                'allocated': Decimal('33.33'),
                'spent': Decimal('33.33'),
                'trans_total': Decimal('33.33'),
                'is_income': False
            },
            3: {
                'budget_amount': Decimal('789.10'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': False
            },
            4: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('-1192.56'),
                'spent': Decimal('-254.38'),
                'trans_total': Decimal('-1234.56'),
                'is_income': True
            }
        }
        assert cls._make_overall_sums() == {
            'allocated': Decimal('945.88'),
            'spent': Decimal('77.77'),
            'income': Decimal('1234.56'),
            'remaining': Decimal('288.68')
        }


class TestTransDict(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_transaction(self):
        m = Mock(spec_set=Transaction)
        m_dst_res = Mock()
        m_dt_res = Mock()
        with patch('%s._dict_for_sched_trans' % pb, autospec=True) as m_dst:
            with patch('%s._dict_for_trans' % pb, autospec=True) as m_dt:
                m_dst.return_value = m_dst_res
                m_dt.return_value = m_dt_res
                res = self.cls._trans_dict(m)
        assert res == m_dt_res
        assert m_dt.mock_calls == [call(self.cls, m)]
        assert m_dst.mock_calls == []

    def test_scheduledtransaction(self):
        m = Mock(spec_set=ScheduledTransaction)
        m_dst_res = Mock()
        m_dt_res = Mock()
        with patch('%s._dict_for_sched_trans' % pb, autospec=True) as m_dst:
            with patch('%s._dict_for_trans' % pb, autospec=True) as m_dt:
                m_dst.return_value = m_dst_res
                m_dt.return_value = m_dt_res
                res = self.cls._trans_dict(m)
        assert res == m_dst_res
        assert m_dt.mock_calls == []
        assert m_dst.mock_calls == [call(self.cls, m)]


class TestDictForTrans(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 17), self.mock_sess)

    def test_simple(self):
        m_account = Mock(name='foo')
        type(m_account).name = 'foo'
        m_budget = Mock(name='bar')
        type(m_budget).name = 'bar'
        m = Mock(
            spec_set=Transaction,
            id=123,
            date=date(year=2017, month=7, day=15),
            scheduled_trans_id=567,
            description='desc',
            actual_amount=Decimal('123.45'),
            budgeted_amount=Decimal('120.00'),
            account_id=2,
            account=m_account,
            budget_id=3,
            budget=m_budget
        )
        type(m).reconcile = None
        assert self.cls._dict_for_trans(m) == {
            'type': 'Transaction',
            'id': 123,
            'date': date(year=2017, month=7, day=15),
            'sched_type': None,
            'sched_trans_id': 567,
            'description': 'desc',
            'amount': Decimal('123.45'),
            'budgeted_amount': Decimal('120.00'),
            'account_id': 2,
            'account_name': 'foo',
            'budget_id': 3,
            'budget_name': 'bar',
            'reconcile_id': None
        }

    def test_reconciled(self):
        m_account = Mock(name='foo')
        type(m_account).name = 'foo'
        m_budget = Mock(name='bar')
        type(m_budget).name = 'bar'
        m = Mock(
            spec_set=Transaction,
            id=123,
            date=date(year=2017, month=7, day=15),
            scheduled_trans_id=567,
            description='desc',
            actual_amount=Decimal('123.45'),
            budgeted_amount=Decimal('120.00'),
            account_id=2,
            account=m_account,
            budget_id=3,
            budget=m_budget
        )
        type(m).reconcile = Mock(id=2)
        assert self.cls._dict_for_trans(m) == {
            'type': 'Transaction',
            'id': 123,
            'date': date(year=2017, month=7, day=15),
            'sched_type': None,
            'sched_trans_id': 567,
            'description': 'desc',
            'amount': Decimal('123.45'),
            'budgeted_amount': Decimal('120.00'),
            'account_id': 2,
            'account_name': 'foo',
            'budget_id': 3,
            'budget_name': 'bar',
            'reconcile_id': 2
        }

    def test_budgeted_amount_none(self):
        m_account = Mock(name='foo')
        type(m_account).name = 'foo'
        m_budget = Mock(name='bar')
        type(m_budget).name = 'bar'
        m = Mock(
            spec_set=Transaction,
            id=123,
            date=date(year=2017, month=7, day=15),
            scheduled_trans_id=567,
            description='desc',
            actual_amount=Decimal('123.45'),
            budgeted_amount=None,
            account_id=2,
            account=m_account,
            budget_id=3,
            budget=m_budget
        )
        type(m).reconcile = None
        assert self.cls._dict_for_trans(m) == {
            'type': 'Transaction',
            'id': 123,
            'date': date(year=2017, month=7, day=15),
            'sched_type': None,
            'sched_trans_id': 567,
            'description': 'desc',
            'amount': Decimal('123.45'),
            'budgeted_amount': None,
            'account_id': 2,
            'account_name': 'foo',
            'budget_id': 3,
            'budget_name': 'bar',
            'reconcile_id': None
        }


class TestDictForSchedTrans(object):

    def setup(self):
        self.mock_sess = Mock(spec_set=Session)
        self.cls = BiweeklyPayPeriod(date(2017, 3, 7), self.mock_sess)
        m_account = Mock(name='foo')
        type(m_account).name = 'foo'
        m_budget = Mock(name='bar')
        type(m_budget).name = 'bar'
        self.m_st = Mock(
            spec_set=ScheduledTransaction,
            id=123,
            description='desc',
            amount=Decimal('123.45'),
            account_id=2,
            account=m_account,
            budget_id=3,
            budget=m_budget
        )

    def test_date(self):
        type(self.m_st).schedule_type = 'date'
        type(self.m_st).date = date(year=2017, month=7, day=15)
        assert self.cls._dict_for_sched_trans(self.m_st) == {
            'type': 'ScheduledTransaction',
            'id': 123,
            'date': date(year=2017, month=7, day=15),
            'sched_type': 'date',
            'sched_trans_id': None,
            'description': 'desc',
            'amount': Decimal('123.45'),
            'budgeted_amount': None,
            'account_id': 2,
            'account_name': 'foo',
            'budget_id': 3,
            'budget_name': 'bar',
            'reconcile_id': None
        }

    def test_per_period(self):
        type(self.m_st).schedule_type = 'per period'
        assert self.cls._dict_for_sched_trans(self.m_st) == {
            'type': 'ScheduledTransaction',
            'id': 123,
            'date': None,
            'sched_type': 'per period',
            'sched_trans_id': None,
            'description': 'desc',
            'amount': Decimal('123.45'),
            'budgeted_amount': None,
            'account_id': 2,
            'account_name': 'foo',
            'budget_id': 3,
            'budget_name': 'bar',
            'reconcile_id': None
        }

    def test_day_of_month_single_month(self):
        type(self.m_st).schedule_type = 'monthly'
        type(self.m_st).day_of_month = 9
        assert self.cls._dict_for_sched_trans(self.m_st) == {
            'type': 'ScheduledTransaction',
            'id': 123,
            'date': date(year=2017, month=3, day=9),
            'sched_type': 'monthly',
            'sched_trans_id': None,
            'description': 'desc',
            'amount': Decimal('123.45'),
            'budgeted_amount': None,
            'account_id': 2,
            'account_name': 'foo',
            'budget_id': 3,
            'budget_name': 'bar',
            'reconcile_id': None
        }

    def test_day_of_month_cross_month_before(self):
        type(self.m_st).schedule_type = 'monthly'
        type(self.m_st).day_of_month = 28
        cls = BiweeklyPayPeriod(date(2017, 3, 26), self.mock_sess)
        assert cls._dict_for_sched_trans(self.m_st) == {
            'type': 'ScheduledTransaction',
            'id': 123,
            'date': date(year=2017, month=3, day=28),
            'sched_type': 'monthly',
            'sched_trans_id': None,
            'description': 'desc',
            'amount': Decimal('123.45'),
            'budgeted_amount': None,
            'account_id': 2,
            'account_name': 'foo',
            'budget_id': 3,
            'budget_name': 'bar',
            'reconcile_id': None
        }

    def test_day_of_month_cross_month_after(self):
        type(self.m_st).schedule_type = 'monthly'
        type(self.m_st).day_of_month = 4
        cls = BiweeklyPayPeriod(date(2017, 3, 26), self.mock_sess)
        assert cls._dict_for_sched_trans(self.m_st) == {
            'type': 'ScheduledTransaction',
            'id': 123,
            'date': date(year=2017, month=4, day=4),
            'sched_type': 'monthly',
            'sched_trans_id': None,
            'description': 'desc',
            'amount': Decimal('123.45'),
            'budgeted_amount': None,
            'account_id': 2,
            'account_name': 'foo',
            'budget_id': 3,
            'budget_name': 'bar',
            'reconcile_id': None
        }
