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

import pytest
from datetime import date

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.scheduled_transaction import ScheduledTransaction
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget import settings


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

    def test_1_set_pay_period_start(self):
        settings.PAY_PERIOD_START_DATE = date(2017, 4, 7)
        """
        Pay period start dates will be:
        2017-03-10
        2017-03-24
        2017-04-07
        2017-04-21
        2017-05-05
        2017-05-19
        """

    def test_2_confirm_pay_period_start(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 10), testdb
        )
        assert pp.start_date == date(2017, 4, 7)

    def test_3_add_data(self, testdb):
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

    def test_4_previous_pay_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 1), testdb
        )
        assert pp.start_date == date(2017, 3, 24)
        all_trans = pp._data['all_trans_list']
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

    def test_5_current_pay_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 13), testdb
        )
        assert pp.start_date == date(2017, 4, 7)
        all_trans = pp._data['all_trans_list']
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

    def test_6_next_pay_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 5, 4), testdb
        )
        assert pp.start_date == date(2017, 4, 21)
        all_trans = pp._data['all_trans_list']
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
