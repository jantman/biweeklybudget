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
from datetime import date
from decimal import Decimal

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.scheduled_transaction import ScheduledTransaction
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch
else:
    from unittest.mock import patch

pbm = 'biweeklybudget.biweeklypayperiod'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
class TestSchedTransOrderingAndPeriodAssignment(AcceptanceHelper):

    def test_0_clean_transactions(self, testdb):
        testdb.query(Transaction).delete(synchronize_session='fetch')
        num_rows = testdb.query(
            ScheduledTransaction).delete(synchronize_session='fetch')
        assert num_rows == 6
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_1_confirm_pay_period_start(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 10), testdb
        )
        assert pp.start_date == date(2017, 4, 7)

    def test_2_add_data(self, testdb):
        acct = testdb.query(Account).get(1)
        budg = testdb.query(Budget).get(1)
        for daynum in range(1, 29):
            testdb.add(ScheduledTransaction(
                amount=123.45,
                description='ST_day_%d' % daynum,
                account=acct,
                budget=budg,
                day_of_month=daynum
            ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_3_previous_pay_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 1), testdb
        )
        assert pp.start_date == date(2017, 3, 24)
        all_trans = pp.transactions_list
        all_monthly = [x for x in all_trans if x['sched_type'] == 'monthly']
        assert len(all_monthly) == 11
        # note monthly scheduled must have a day number <= 28
        assert all_monthly[0]['date'] == date(2017, 3, 24)
        assert all_monthly[1]['date'] == date(2017, 3, 25)
        assert all_monthly[2]['date'] == date(2017, 3, 26)
        assert all_monthly[3]['date'] == date(2017, 3, 27)
        assert all_monthly[4]['date'] == date(2017, 3, 28)
        assert all_monthly[5]['date'] == date(2017, 4, 1)
        assert all_monthly[6]['date'] == date(2017, 4, 2)
        assert all_monthly[7]['date'] == date(2017, 4, 3)
        assert all_monthly[8]['date'] == date(2017, 4, 4)
        assert all_monthly[9]['date'] == date(2017, 4, 5)
        assert all_monthly[10]['date'] == date(2017, 4, 6)

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_4_current_pay_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 13), testdb
        )
        assert pp.start_date == date(2017, 4, 7)
        all_trans = pp.transactions_list
        all_monthly = [x for x in all_trans if x['sched_type'] == 'monthly']
        assert len(all_monthly) == 14
        assert all_monthly[0]['date'] == date(2017, 4, 7)
        assert all_monthly[1]['date'] == date(2017, 4, 8)
        assert all_monthly[2]['date'] == date(2017, 4, 9)
        assert all_monthly[3]['date'] == date(2017, 4, 10)
        assert all_monthly[4]['date'] == date(2017, 4, 11)
        assert all_monthly[5]['date'] == date(2017, 4, 12)
        assert all_monthly[6]['date'] == date(2017, 4, 13)
        assert all_monthly[7]['date'] == date(2017, 4, 14)
        assert all_monthly[8]['date'] == date(2017, 4, 15)
        assert all_monthly[9]['date'] == date(2017, 4, 16)
        assert all_monthly[10]['date'] == date(2017, 4, 17)
        assert all_monthly[11]['date'] == date(2017, 4, 18)
        assert all_monthly[12]['date'] == date(2017, 4, 19)
        assert all_monthly[13]['date'] == date(2017, 4, 20)

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_5_next_pay_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 5, 4), testdb
        )
        assert pp.start_date == date(2017, 4, 21)
        all_trans = pp.transactions_list
        all_monthly = [x for x in all_trans if x['sched_type'] == 'monthly']
        assert len(all_monthly) == 12
        # note monthly scheduled must have a day number <= 28
        assert all_monthly[0]['date'] == date(2017, 4, 21)
        assert all_monthly[1]['date'] == date(2017, 4, 22)
        assert all_monthly[2]['date'] == date(2017, 4, 23)
        assert all_monthly[3]['date'] == date(2017, 4, 24)
        assert all_monthly[4]['date'] == date(2017, 4, 25)
        assert all_monthly[5]['date'] == date(2017, 4, 26)
        assert all_monthly[6]['date'] == date(2017, 4, 27)
        assert all_monthly[7]['date'] == date(2017, 4, 28)
        assert all_monthly[8]['date'] == date(2017, 5, 1)
        assert all_monthly[9]['date'] == date(2017, 5, 2)
        assert all_monthly[10]['date'] == date(2017, 5, 3)
        assert all_monthly[11]['date'] == date(2017, 5, 4)


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
class TestTransFromSchedTrans(AcceptanceHelper):

    def test_0_clean_transactions(self, testdb):
        testdb.query(Transaction).delete(synchronize_session='fetch')
        num_rows = testdb.query(
            ScheduledTransaction).delete(synchronize_session='fetch')
        assert num_rows == 6
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_1_confirm_pay_period_start(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 10), testdb
        )
        assert pp.start_date == date(2017, 4, 7)

    def test_2_add_data(self, testdb):
        acct = testdb.query(Account).get(1)
        budg = testdb.query(Budget).get(1)
        st_daynum = ScheduledTransaction(
            amount=111.11,
            description='ST_day_9',
            account=acct,
            budget=budg,
            day_of_month=9
        )
        testdb.add(st_daynum)
        t_daynum = Transaction(
            actual_amount=111.33,
            budgeted_amount=111.11,
            date=date(2017, 4, 9),
            description='Trans_ST_day_9',
            account=acct,
            budget=budg,
            scheduled_trans=st_daynum,
        )
        testdb.add(t_daynum)
        st_pp1 = ScheduledTransaction(
            amount=222.22,
            description='ST_pp_1',
            account=acct,
            budget=budg,
            num_per_period=1
        )
        testdb.add(st_pp1)
        st_pp3 = ScheduledTransaction(
            amount=333.33,
            description='ST_pp_3',
            account=acct,
            budget=budg,
            num_per_period=3
        )
        testdb.add(st_pp3)
        t_pp3A = Transaction(
            actual_amount=333.33,
            budgeted_amount=333.33,
            date=date(2017, 4, 14),
            description='Trans_ST_pp_3_A',
            account=acct,
            budget=budg,
            scheduled_trans=st_pp3,
        )
        testdb.add(t_pp3A)
        t_pp3B = Transaction(
            actual_amount=333.33,
            budgeted_amount=333.33,
            date=date(2017, 4, 15),
            description='Trans_ST_pp_3_B',
            account=acct,
            budget=budg,
            scheduled_trans=st_pp3
        )
        testdb.add(t_pp3B)
        st_date = ScheduledTransaction(
            amount=444.44,
            description='ST_date',
            account=acct,
            budget=budg,
            date=date(2017, 4, 12)
        )
        testdb.add(st_date)
        t_date = Transaction(
            actual_amount=444.44,
            budgeted_amount=444.44,
            date=date(2017, 4, 12),
            description='Trans_ST_date',
            account=acct,
            budget=budg,
            scheduled_trans=st_date
        )
        testdb.add(t_date)
        t_foo = Transaction(
            actual_amount=555.55,
            date=date(2017, 4, 8),
            description='Trans_foo',
            account=acct,
            budget=budg
        )
        testdb.add(t_foo)
        t_bar = Transaction(
            actual_amount=666.66,
            date=date(2017, 4, 16),
            description='Trans_bar',
            account=acct,
            budget=budg
        )
        testdb.add(t_bar)
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_3_ignore_scheduled_converted_to_real_trans(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 7), testdb
        )
        assert pp.start_date == date(2017, 4, 7)
        all_trans = pp.transactions_list
        assert all_trans == [
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('222.2200'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': None,
                'date': None,
                'description': 'ST_pp_1',
                'id': 8,
                'sched_trans_id': None,
                'sched_type': 'per period',
                'type': 'ScheduledTransaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('333.3300'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': None,
                'date': None,
                'description': 'ST_pp_3',
                'id': 9,
                'sched_trans_id': None,
                'sched_type': 'per period',
                'type': 'ScheduledTransaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': 555.55,
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': None,
                'date': date(2017, 4, 8),
                'description': 'Trans_foo',
                'id': 8,
                'sched_trans_id': None,
                'sched_type': None,
                'type': 'Transaction'
            },
            # ST7 (ST_day_9)
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': 111.33,
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': 111.11,
                'date': date(2017, 4, 9),
                'description': 'Trans_ST_day_9',
                'id': 4,
                'sched_trans_id': 7,
                'sched_type': None,
                'type': 'Transaction'
            },
            # ST10 (ST_date)
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': 444.44,
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': 444.44,
                'date': date(2017, 4, 12),
                'description': 'Trans_ST_date',
                'id': 7,
                'sched_trans_id': 10,
                'sched_type': None,
                'type': 'Transaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': 333.33,
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': 333.33,
                'date': date(2017, 4, 14),
                'description': 'Trans_ST_pp_3_A',
                'id': 5,
                'sched_trans_id': 9,
                'sched_type': None,
                'type': 'Transaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': 333.33,
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': 333.33,
                'date': date(2017, 4, 15),
                'description': 'Trans_ST_pp_3_B',
                'id': 6,
                'sched_trans_id': 9,
                'sched_type': None,
                'type': 'Transaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': 666.66,
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': None,
                'date': date(2017, 4, 16),
                'description': 'Trans_bar',
                'id': 9,
                'sched_trans_id': None,
                'sched_type': None,
                'type': 'Transaction'
            }
        ]
