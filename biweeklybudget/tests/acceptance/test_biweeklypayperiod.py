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
from datetime import date, datetime
from pytz import UTC
from decimal import Decimal

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.scheduled_transaction import ScheduledTransaction
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.tests.conftest import engine
from biweeklybudget.tests.sqlhelpers import restore_mysqldump

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
@pytest.mark.incremental
class TestSchedTransOrderingAndPeriodAssignment(AcceptanceHelper):

    def find_income_trans_id(self, db):
        return db.query(ScheduledTransaction).filter(
            ScheduledTransaction.description.__eq__('Income')
        ).one().id

    def test_0_clean_transactions(self, testdb):
        testdb.query(TxnReconcile).delete(synchronize_session='fetch')
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
        inc_budg = testdb.query(Budget).get(7)
        for daynum in range(1, 29):
            testdb.add(ScheduledTransaction(
                amount=123.45,
                description='ST_day_%d' % daynum,
                account=acct,
                budget=budg,
                day_of_month=daynum
            ))
        testdb.add(ScheduledTransaction(
            amount=-1000.00,
            description='Income',
            account=acct,
            budget=inc_budg,
            num_per_period=1
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
    def test_4_income_trans_is_first_previous_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 1), testdb
        )
        all_trans = pp.transactions_list
        income_id = self.find_income_trans_id(testdb)
        assert income_id is not None
        assert all_trans[0]['id'] == income_id

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_5_current_pay_period(self, testdb):
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
    def test_6_income_trans_is_first_current_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 13), testdb
        )
        all_trans = pp.transactions_list
        income_id = self.find_income_trans_id(testdb)
        assert income_id is not None
        assert all_trans[0]['id'] == income_id

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_7_next_pay_period(self, testdb):
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

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_8_income_trans_is_first_next_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 5, 4), testdb
        )
        all_trans = pp.transactions_list
        income_id = self.find_income_trans_id(testdb)
        assert income_id is not None
        assert all_trans[0]['id'] == income_id


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestTransFromSchedTrans(AcceptanceHelper):

    def test_0_clean_transactions(self, testdb):
        testdb.query(TxnReconcile).delete(synchronize_session='fetch')
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
        testdb.add(TxnReconcile(
            note='foo',
            transaction=t_daynum
        ))
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
                'amount': Decimal('222.22'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': None,
                'date': None,
                'description': 'ST_pp_1',
                'id': 8,
                'sched_trans_id': None,
                'sched_type': 'per period',
                'type': 'ScheduledTransaction',
                'reconcile_id': None
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('333.33'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': None,
                'date': None,
                'description': 'ST_pp_3',
                'id': 9,
                'sched_trans_id': None,
                'sched_type': 'per period',
                'type': 'ScheduledTransaction',
                'reconcile_id': None
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('555.55'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': None,
                'date': date(2017, 4, 8),
                'description': 'Trans_foo',
                'id': 8,
                'sched_trans_id': None,
                'sched_type': None,
                'type': 'Transaction',
                'reconcile_id': None
            },
            # ST7 (ST_day_9)
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('111.33'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': Decimal('111.11'),
                'date': date(2017, 4, 9),
                'description': 'Trans_ST_day_9',
                'id': 4,
                'sched_trans_id': 7,
                'sched_type': None,
                'type': 'Transaction',
                'reconcile_id': 2
            },
            # ST10 (ST_date)
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('444.44'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': Decimal('444.44'),
                'date': date(2017, 4, 12),
                'description': 'Trans_ST_date',
                'id': 7,
                'sched_trans_id': 10,
                'sched_type': None,
                'type': 'Transaction',
                'reconcile_id': None
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('333.33'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': Decimal('333.33'),
                'date': date(2017, 4, 14),
                'description': 'Trans_ST_pp_3_A',
                'id': 5,
                'sched_trans_id': 9,
                'sched_type': None,
                'type': 'Transaction',
                'reconcile_id': None
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('333.33'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': Decimal('333.33'),
                'date': date(2017, 4, 15),
                'description': 'Trans_ST_pp_3_B',
                'id': 6,
                'sched_trans_id': 9,
                'sched_type': None,
                'type': 'Transaction',
                'reconcile_id': None
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('666.66'),
                'budget_id': 1,
                'budget_name': 'Periodic1',
                'budgeted_amount': None,
                'date': date(2017, 4, 16),
                'description': 'Trans_bar',
                'id': 9,
                'sched_trans_id': None,
                'sched_type': None,
                'type': 'Transaction',
                'reconcile_id': None
            }
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestSums(AcceptanceHelper):

    def test_0_clean_db(self, dump_file_path):
        # clean the database; empty schema
        restore_mysqldump(dump_file_path, engine, with_data=False)

    def test_1_add_account(self, testdb):
        a = Account(
            description='First Bank Account',
            name='BankOne',
            ofx_cat_memo_to_name=True,
            ofxgetter_config_json='{"foo": "bar"}',
            vault_creds_path='secret/foo/bar/BankOne',
            acct_type=AcctType.Bank
        )
        testdb.add(a)
        a.set_balance(
            overall_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC),
            ledger=1.0,
            ledger_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC)
        )
        testdb.flush()
        testdb.commit()

    def test_2_add_budgets(self, testdb):
        testdb.add(Budget(
            name='1Standing',
            is_periodic=False,
            description='1Standing',
            current_balance=987.65
        ))
        testdb.add(Budget(
            name='2Income',
            is_periodic=True,
            description='2Income',
            starting_balance=123.45,
            is_income=True
        ))
        testdb.add(Budget(
            name='3Income',
            is_periodic=True,
            description='2Income',
            starting_balance=0.0,
            is_income=True
        ))
        testdb.add(Budget(
            name='4Periodic',
            is_periodic=True,
            description='4Periodic',
            starting_balance=500.00
        ))
        testdb.add(Budget(
            name='5Periodic',
            is_periodic=True,
            description='5Periodic',
            starting_balance=100.00
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_3_add_transactions(self, testdb):
        acct = testdb.query(Account).get(1)
        budgets = {x.id: x for x in testdb.query(Budget).all()}
        # Budget 3 Income Transaction
        testdb.add(Transaction(
            date=date(2017, 4, 7),
            actual_amount=100.00,
            budgeted_amount=100.00,
            description='B3 Income',
            account=acct,
            budget=budgets[3]
        ))
        # Budget 3 Income ST
        testdb.add(ScheduledTransaction(
            amount=99.00,
            description='B3 Income ST',
            account=acct,
            budget=budgets[3],
            num_per_period=1
        ))
        # Budget 4 allocated greater than budgeted (500.00)
        testdb.add(ScheduledTransaction(
            amount=250.00,
            description='B4 ST',
            account=acct,
            budget=budgets[4],
            date=date(2017, 4, 10)
        ))
        testdb.add(Transaction(
            date=date(2017, 4, 11),
            actual_amount=250.00,
            description='B4 T no budgeted',
            account=acct,
            budget=budgets[4]
        ))
        testdb.add(Transaction(
            date=date(2017, 4, 12),
            actual_amount=600.00,
            budgeted_amount=500.00,
            description='B4 T budgeted',
            account=acct,
            budget=budgets[4]
        ))
        # Budget 5 budgeted greater than allocated (100)
        testdb.add(ScheduledTransaction(
            amount=2.00,
            description='B5 ST',
            account=acct,
            budget=budgets[5],
            day_of_month=9
        ))
        testdb.add(Transaction(
            date=date(2017, 4, 13),
            description='B5 T',
            actual_amount=3.00,
            budgeted_amount=1.00,
            account=acct,
            budget=budgets[5]
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_4_budget_sums(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 10), testdb
        )
        assert pp._data['budget_sums'] == {
            2: {
                'budget_amount': Decimal('123.45'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': True,
                'remaining': Decimal('123.45')
            },
            3: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('199.0'),
                'spent': Decimal('100.0'),
                'trans_total': Decimal('199.0'),
                'is_income': True,
                'remaining': Decimal('199.0')
            },
            4: {
                'budget_amount': Decimal('500.00'),
                'allocated': Decimal('1000.0'),
                'spent': Decimal('850.0'),
                'trans_total': Decimal('1100.0'),
                'is_income': False,
                'remaining': Decimal('-600.0')
            },
            5: {
                'budget_amount': Decimal('100.0'),
                'allocated': Decimal('3.0'),
                'spent': Decimal('3.0'),
                'trans_total': Decimal('5.0'),
                'is_income': False,
                'remaining': Decimal('95.0')
            }
        }

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_5_overall_sums(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 10), testdb
        )
        assert pp._data['overall_sums'] == {
            'allocated': Decimal('1100.0'),
            'spent': Decimal('853.0'),
            'income': Decimal('322.45'),
            'remaining': Decimal('-530.55')
        }

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_6_transaction_list_ordering(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 10), testdb
        )
        type_id = [[x['type'], x['id']] for x in pp.transactions_list]
        assert type_id == [
            ['ScheduledTransaction', 1],
            ['Transaction', 1],
            ['ScheduledTransaction', 3],
            ['ScheduledTransaction', 2],
            ['Transaction', 2],
            ['Transaction', 3],
            ['Transaction', 4]
        ]

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_7_spent_greater_than_allocated(self, testdb):
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(5)
        testdb.add(Transaction(
            date=date(2017, 4, 13),
            description='B6 T',
            actual_amount=2032.0,
            budgeted_amount=32.0,
            account=acct,
            budget=budget
        ))
        testdb.flush()
        testdb.commit()
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 10), testdb
        )
        assert pp._data['budget_sums'] == {
            2: {
                'budget_amount': Decimal('123.45'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': True,
                'remaining': Decimal('123.45')
            },
            3: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('199.0'),
                'spent': Decimal('100.0'),
                'trans_total': Decimal('199.0'),
                'is_income': True,
                'remaining': Decimal('199.0')
            },
            4: {
                'budget_amount': Decimal('500.00'),
                'allocated': Decimal('1000.0'),
                'spent': Decimal('850.0'),
                'trans_total': Decimal('1100.0'),
                'is_income': False,
                'remaining': Decimal('-600.0')
            },
            5: {
                'budget_amount': Decimal('100.0'),
                'allocated': Decimal('35.0'),
                'spent': Decimal('2035.0'),
                'trans_total': Decimal('2037.0'),
                'is_income': False,
                'remaining': Decimal('-1937.0')
            }
        }
        assert pp._data['overall_sums'] == {
            'allocated': Decimal('1100.0'),
            'spent': Decimal('2885.0'),
            'income': Decimal('322.45'),
            'remaining': Decimal('-2562.55')
        }

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_8_sums_for_empty_period(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2020, 4, 9), testdb
        )
        assert pp._data['budget_sums'] == {
            2: {
                'budget_amount': Decimal('123.45'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': True,
                'remaining': Decimal('123.45')
            },
            3: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('99.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('99.0'),
                'is_income': True,
                'remaining': Decimal('99.0')
            },
            4: {
                'budget_amount': Decimal('500.00'),
                'allocated': Decimal('0.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('0.0'),
                'is_income': False,
                'remaining': Decimal('500.0')
            },
            5: {
                'budget_amount': Decimal('100.0'),
                'allocated': Decimal('2.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('2.0'),
                'is_income': False,
                'remaining': Decimal('98.0')
            }
        }
        assert pp._data['overall_sums'] == {
            'allocated': Decimal('600.0'),
            'income': Decimal('222.45'),
            'remaining': Decimal('-377.55'),
            'spent': Decimal('0.0')
        }
