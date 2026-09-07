"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016-2024 Jason Antman <http://www.jasonantman.com>

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
from biweeklybudget.models.budget_transaction import BudgetTransaction
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.tests.conftest import get_db_engine
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
        testdb.query(BudgetTransaction).delete(synchronize_session='fetch')
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
                amount=Decimal('123.45'),
                description='ST_day_%d' % daynum,
                account=acct,
                budget=budg,
                day_of_month=daynum
            ))
        testdb.add(ScheduledTransaction(
            amount=Decimal('-1000.00'),
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
        testdb.query(BudgetTransaction).delete(synchronize_session='fetch')
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
        budg2 = testdb.query(Budget).get(2)
        st_daynum = ScheduledTransaction(
            amount=Decimal('111.11'),
            description='ST_day_9',
            account=acct,
            budget=budg,
            day_of_month=9
        )
        testdb.add(st_daynum)
        t_daynum = Transaction(
            budget_amounts={budg: Decimal('111.33')},
            budgeted_amount=Decimal('111.11'),
            date=date(2017, 4, 9),
            description='Trans_ST_day_9',
            account=acct,
            planned_budget=budg,
            scheduled_trans=st_daynum,
        )
        testdb.add(t_daynum)
        testdb.add(TxnReconcile(
            note='foo',
            transaction=t_daynum
        ))
        st_pp1 = ScheduledTransaction(
            amount=Decimal('222.22'),
            description='ST_pp_1',
            account=acct,
            budget=budg,
            num_per_period=1
        )
        testdb.add(st_pp1)
        st_pp3 = ScheduledTransaction(
            amount=Decimal('333.33'),
            description='ST_pp_3',
            account=acct,
            budget=budg,
            num_per_period=3
        )
        testdb.add(st_pp3)
        t_pp3A = Transaction(
            budget_amounts={budg: Decimal('333.33')},
            budgeted_amount=Decimal('333.33'),
            date=date(2017, 4, 14),
            description='Trans_ST_pp_3_A',
            account=acct,
            planned_budget=budg,
            scheduled_trans=st_pp3,
        )
        testdb.add(t_pp3A)
        t_pp3B = Transaction(
            budget_amounts={budg: Decimal('333.33')},
            budgeted_amount=Decimal('333.33'),
            date=date(2017, 4, 15),
            description='Trans_ST_pp_3_B',
            account=acct,
            planned_budget=budg,
            scheduled_trans=st_pp3
        )
        testdb.add(t_pp3B)
        st_date = ScheduledTransaction(
            amount=Decimal('444.44'),
            description='ST_date',
            account=acct,
            budget=budg,
            date=date(2017, 4, 12)
        )
        testdb.add(st_date)
        t_date = Transaction(
            budget_amounts={budg: Decimal('444.44')},
            budgeted_amount=Decimal('444.44'),
            date=date(2017, 4, 12),
            description='Trans_ST_date',
            account=acct,
            planned_budget=budg,
            scheduled_trans=st_date
        )
        testdb.add(t_date)
        t_foo = Transaction(
            budget_amounts={budg: Decimal('555.55')},
            date=date(2017, 4, 8),
            description='Trans_foo',
            account=acct
        )
        testdb.add(t_foo)
        t_bar = Transaction(
            budget_amounts={
                budg: Decimal('666.66'),
                budg2: Decimal('100.00')
            },
            date=date(2017, 4, 16),
            description='Trans_bar',
            account=acct
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
                'budgeted_amount': None,
                'budgets': {
                    1: {'amount': Decimal('222.2200'), 'name': 'Periodic1'}
                },
                'date': None,
                'description': 'ST_pp_1',
                'id': 8,
                'no_budget_impact': False,
                'reconcile_id': None,
                'sched_trans_id': None,
                'sched_type': 'per period',
                'type': 'ScheduledTransaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('333.3300'),
                'budgeted_amount': None,
                'budgets': {
                    1: {'amount': Decimal('333.3300'), 'name': 'Periodic1'}
                },
                'date': None,
                'description': 'ST_pp_3',
                'id': 9,
                'no_budget_impact': False,
                'reconcile_id': None,
                'sched_trans_id': None,
                'sched_type': 'per period',
                'type': 'ScheduledTransaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('555.5500'),
                'budgeted_amount': None,
                'budgets': {
                    1: {'amount': Decimal('555.5500'), 'name': 'Periodic1'}
                },
                'date': date(2017, 4, 8),
                'description': 'Trans_foo',
                'id': 9,
                'planned_budget_id': None,
                'planned_budget_name': None,
                'no_budget_impact': False,
                'reconcile_id': None,
                'sched_trans_id': None,
                'sched_type': None,
                'type': 'Transaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('111.3300'),
                'budgeted_amount': Decimal('111.1100'),
                'budgets': {
                    1: {'amount': Decimal('111.3300'), 'name': 'Periodic1'}
                },
                'date': date(2017, 4, 9),
                'description': 'Trans_ST_day_9',
                'id': 5,
                'planned_budget_id': 1,
                'planned_budget_name': 'Periodic1',
                'no_budget_impact': False,
                'reconcile_id': 2,
                'sched_trans_id': 7,
                'sched_type': None,
                'type': 'Transaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('444.4400'),
                'budgeted_amount': Decimal('444.4400'),
                'budgets': {
                    1: {'amount': Decimal('444.4400'), 'name': 'Periodic1'}
                },
                'date': date(2017, 4, 12),
                'description': 'Trans_ST_date',
                'id': 8,
                'planned_budget_id': 1,
                'planned_budget_name': 'Periodic1',
                'no_budget_impact': False,
                'reconcile_id': None,
                'sched_trans_id': 10,
                'sched_type': None,
                'type': 'Transaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('333.3300'),
                'budgeted_amount': Decimal('333.3300'),
                'budgets': {
                    1: {'amount': Decimal('333.3300'), 'name': 'Periodic1'}
                },
                'date': date(2017, 4, 14),
                'description': 'Trans_ST_pp_3_A',
                'id': 6,
                'planned_budget_id': 1,
                'planned_budget_name': 'Periodic1',
                'no_budget_impact': False,
                'reconcile_id': None,
                'sched_trans_id': 9,
                'sched_type': None,
                'type': 'Transaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('333.3300'),
                'budgeted_amount': Decimal('333.3300'),
                'budgets': {
                    1: {'amount': Decimal('333.3300'), 'name': 'Periodic1'}
                },
                'date': date(2017, 4, 15),
                'description': 'Trans_ST_pp_3_B',
                'id': 7,
                'planned_budget_id': 1,
                'planned_budget_name': 'Periodic1',
                'no_budget_impact': False,
                'reconcile_id': None,
                'sched_trans_id': 9,
                'sched_type': None,
                'type': 'Transaction'
            },
            {
                'account_id': 1,
                'account_name': 'BankOne',
                'amount': Decimal('766.6600'),
                'budgeted_amount': None,
                'budgets': {
                    1: {'amount': Decimal('666.6600'), 'name': 'Periodic1'},
                    2: {'amount': Decimal('100.0000'), 'name': 'Periodic2'}
                },
                'date': date(2017, 4, 16),
                'description': 'Trans_bar',
                'id': 10,
                'planned_budget_id': None,
                'planned_budget_name': None,
                'no_budget_impact': False,
                'reconcile_id': None,
                'sched_trans_id': None,
                'sched_type': None,
                'type': 'Transaction'
            }
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestSums(AcceptanceHelper):

    def test_10_clean_db(self, dump_file_path):
        # clean the database; empty schema
        restore_mysqldump(dump_file_path, get_db_engine(), with_data=False)

    def test_11_add_account(self, testdb):
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
            ledger=Decimal('1.0'),
            ledger_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC)
        )
        testdb.flush()
        testdb.commit()

    def test_12_add_budgets(self, testdb):
        testdb.add(Budget(
            name='1Standing',
            is_periodic=False,
            description='1Standing',
            current_balance=Decimal('987.65')
        ))
        testdb.add(Budget(
            name='2Income',
            is_periodic=True,
            description='2Income',
            starting_balance=Decimal('123.45'),
            is_income=True
        ))
        testdb.add(Budget(
            name='3Income',
            is_periodic=True,
            description='2Income',
            starting_balance=Decimal('0.0'),
            is_income=True
        ))
        testdb.add(Budget(
            name='4Periodic',
            is_periodic=True,
            description='4Periodic',
            starting_balance=Decimal('500.00')
        ))
        testdb.add(Budget(
            name='5Periodic',
            is_periodic=True,
            description='5Periodic',
            starting_balance=Decimal('100.00')
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_13_add_transactions(self, testdb):
        acct = testdb.query(Account).get(1)
        budgets = {x.id: x for x in testdb.query(Budget).all()}
        # Budget 3 Income Transaction
        t1 = Transaction(
            date=date(2017, 4, 7),
            budget_amounts={
                budgets[3]: Decimal('100.00'),
                budgets[4]: Decimal('50.00')
            },
            budgeted_amount=Decimal('100.00'),
            description='B3 Income',
            account=acct
        )
        testdb.add(t1)
        # Budget 3 Income ST
        testdb.add(ScheduledTransaction(
            amount=Decimal('99.00'),
            description='B3 Income ST',
            account=acct,
            budget=budgets[3],
            num_per_period=1
        ))
        # Budget 4 allocated greater than budgeted (500.00)
        testdb.add(ScheduledTransaction(
            amount=Decimal('250.00'),
            description='B4 ST',
            account=acct,
            budget=budgets[4],
            date=date(2017, 4, 10)
        ))
        t2 = Transaction(
            date=date(2017, 4, 11),
            budget_amounts={budgets[4]: Decimal('250.00')},
            description='B4 T no budgeted',
            account=acct
        )
        testdb.add(t2)
        t3 = Transaction(
            date=date(2017, 4, 12),
            budget_amounts={budgets[4]: Decimal('600.00')},
            budgeted_amount=Decimal('500.00'),
            description='B4 T budgeted',
            account=acct,
            planned_budget=budgets[4]
        )
        testdb.add(t3)
        # Budget 5 budgeted greater than allocated (100)
        testdb.add(ScheduledTransaction(
            amount=Decimal('2.00'),
            description='B5 ST',
            account=acct,
            budget=budgets[5],
            day_of_month=9
        ))
        t4 = Transaction(
            date=date(2017, 4, 13),
            description='B5 T',
            budget_amounts={budgets[5]: Decimal('3.00')},
            budgeted_amount=Decimal('1.00'),
            account=acct,
            planned_budget=budgets[5]
        )
        testdb.add(t4)
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_14_budget_sums(self, testdb):
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
                'spent': Decimal('900.0'),
                'trans_total': Decimal('1150.0'),
                'is_income': False,
                'remaining': Decimal('-650.0')
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
    def test_15_overall_sums(self, testdb):
        pp = BiweeklyPayPeriod.period_for_date(
            date(2017, 4, 10), testdb
        )
        assert pp._data['overall_sums'] == {
            'allocated': Decimal('1100.0'),
            'spent': Decimal('903.0'),
            'income': Decimal('322.45'),
            'remaining': Decimal('-580.55')
        }

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_16_transaction_list_ordering(self, testdb):
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
    def test_17_spent_greater_than_allocated(self, testdb):
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(5)
        t = Transaction(
            date=date(2017, 4, 13),
            description='B6 T',
            budget_amounts={budget: Decimal('2032.0')},
            budgeted_amount=Decimal('32.0'),
            account=acct,
            planned_budget=budget
        )
        testdb.add(t)
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
                'spent': Decimal('900.0'),
                'trans_total': Decimal('1150.0'),
                'is_income': False,
                'remaining': Decimal('-650.0')
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
            'spent': Decimal('2935.0'),
            'income': Decimal('322.45'),
            'remaining': Decimal('-2612.55')
        }

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_18_sums_for_empty_period(self, testdb):
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

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_80_issue201_setup(self, testdb):
        budg = Budget(
            name='6Periodic',
            is_periodic=True,
            description='6Periodic',
            starting_balance=Decimal('0.00')
        )
        testdb.add(budg)
        acct = testdb.query(Account).get(1)
        testdb.add(ScheduledTransaction(
            amount=Decimal('2.00'),
            description='B6 ST4',
            account=acct,
            budget=budg,
            day_of_month=11
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_81_issue201_validate_setup(self, testdb):
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
            },
            6: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('2.0'),
                'spent': Decimal('0.0'),
                'trans_total': Decimal('2.0'),
                'is_income': False,
                'remaining': Decimal('-2.0')
            }
        }
        assert pp._data['overall_sums'] == {
            'allocated': Decimal('602.0'),
            'income': Decimal('222.45'),
            'remaining': Decimal('-379.55'),
            'spent': Decimal('0.0')
        }

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_82_issue201_st_to_trans(self, testdb):
        budg = testdb.query(Budget).get(6)
        st = testdb.query(ScheduledTransaction).get(4)
        testdb.add(Transaction(
            date=date(2020, 4, 14),
            description='B6 T6 from ST4',
            budget_amounts={
                budg: Decimal('200.00')
            },
            budgeted_amount=Decimal('2.00'),
            account=testdb.query(Account).get(1),
            planned_budget=budg,
            scheduled_trans=st
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_83_issue201_confirm(self, testdb):
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
            },
            6: {
                'budget_amount': Decimal('0.0'),
                'allocated': Decimal('2.0'),
                'spent': Decimal('200.0'),
                'trans_total': Decimal('200.0'),
                'is_income': False,
                'remaining': Decimal('-200.0')
            }
        }
        assert pp._data['overall_sums'] == {
            'allocated': Decimal('602.0'),
            'income': Decimal('222.45'),
            'remaining': Decimal('-577.55'),
            'spent': Decimal('200.0')
        }


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestCreditCardPaymentSums(AcceptanceHelper):
    """
    Pay period arithmetic for credit card payments; GitHub issue #210.

    A payment toward a credit account has zero budget impact. Every charge on
    the card is already budgeted on its own charge date, in its own pay period,
    so counting the payment that settles it would charge the same money against
    available income twice.

    Pay periods here start 2017-04-07 (patched below), so:

      * period N   = 2017-04-07 .. 2017-04-20
      * period N+1 = 2017-04-21 .. 2017-05-04
    """

    def test_10_clean_db(self, dump_file_path):
        restore_mysqldump(dump_file_path, get_db_engine(), with_data=False)

    def test_11_add_accounts(self, testdb):
        testdb.add(Account(
            description='Bank Account',
            name='BankOne',
            acct_type=AcctType.Bank
        ))
        testdb.add(Account(
            description='Credit Card',
            name='CreditOne',
            acct_type=AcctType.Credit,
            credit_limit=Decimal('2000.00')
        ))
        testdb.flush()
        testdb.commit()

    def test_12_add_budgets(self, testdb):
        testdb.add(Budget(
            name='1Periodic',
            is_periodic=True,
            description='1Periodic',
            starting_balance=Decimal('2000.00')
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_13_add_charges_and_payment(self, testdb):
        bank = testdb.query(Account).get(1)
        card = testdb.query(Account).get(2)
        budget = testdb.query(Budget).get(1)
        # Period N: 500.00 of charges on the card
        testdb.add(Transaction(
            date=date(2017, 4, 10),
            budget_amounts={budget: Decimal('500.00')},
            description='N charges on card',
            account=card
        ))
        # Period N+1: 300.00 of the card's own charges
        testdb.add(Transaction(
            date=date(2017, 4, 24),
            budget_amounts={budget: Decimal('300.00')},
            description='N+1 charges on card',
            account=card
        ))
        # Period N+1: a 500.00 payment from the bank account, settling the
        # charges made in period N.
        testdb.add(Transaction(
            date=date(2017, 4, 25),
            budget_amounts={budget: Decimal('500.00')},
            description='Payment toward CreditOne',
            account=bank,
            credit_payment_acct=card
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_14_payment_is_excluded(self, testdb):
        payment = testdb.query(Transaction).get(3)
        assert payment.credit_payment_acct_id == 2
        assert payment.no_budget_impact is False
        assert payment.is_excluded_from_budget is True

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_15_period_n_unchanged(self, testdb):
        """Period N is charged its own 500.00 and nothing else."""
        pp = BiweeklyPayPeriod(date(2017, 4, 7), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('500.00')
        assert pp.overall_sums['spent'] == Decimal('500.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_16_cross_period_payoff_counts_once(self, testdb):
        """
        Spec US2 scenario 1 / SC-001. Period N+1 must be charged only its own
        300.00 of purchases. Before this feature it was charged 800.00 -- its
        own charges plus the payment settling period N's charges -- which is
        the double-count the whole feature exists to remove.
        """
        pp = BiweeklyPayPeriod(date(2017, 4, 21), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('300.00')
        assert pp.budget_sums[1]['spent'] != Decimal('800.00')
        assert pp.budget_sums[1]['trans_total'] == Decimal('300.00')
        assert pp.budget_sums[1]['remaining'] == Decimal('1700.00')
        assert pp.overall_sums['spent'] == Decimal('300.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_17_payment_still_listed_in_period(self, testdb):
        """The payment must remain visible in the pay period's transaction
        list, marked as excluded, even though it moves no total."""
        pp = BiweeklyPayPeriod(date(2017, 4, 21), testdb)
        payments = [
            t for t in pp.transactions_list
            if t.get('description') == 'Payment toward CreditOne'
        ]
        assert len(payments) == 1
        assert payments[0]['no_budget_impact'] is True

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_18_same_period_payoff_counts_once(self, testdb):
        """
        Spec US2 scenario 2 / SC-002. A 200.00 charge and a 200.00 payment in
        the same pay period: the period is charged 200.00, not 400.00.
        """
        bank = testdb.query(Account).get(1)
        card = testdb.query(Account).get(2)
        budget = testdb.query(Budget).get(1)
        testdb.add(Transaction(
            date=date(2017, 5, 8),
            budget_amounts={budget: Decimal('200.00')},
            description='Same period charge',
            account=card
        ))
        testdb.add(Transaction(
            date=date(2017, 5, 10),
            budget_amounts={budget: Decimal('200.00')},
            description='Same period payment',
            account=bank,
            credit_payment_acct=card
        ))
        testdb.flush()
        testdb.commit()
        pp = BiweeklyPayPeriod(date(2017, 5, 5), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('200.00')
        assert pp.budget_sums[1]['spent'] != Decimal('400.00')
        assert pp.overall_sums['spent'] == Decimal('200.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_19_clearing_designation_restores_impact(self, testdb):
        """Spec FR-014: clearing the credit account designation makes the
        payment count against its budget again."""
        payment = testdb.query(Transaction).get(3)
        payment.credit_payment_acct_id = None
        testdb.flush()
        testdb.commit()
        pp = BiweeklyPayPeriod(date(2017, 4, 21), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('800.00')
        # ... and setting it again removes the impact once more
        payment = testdb.query(Transaction).get(3)
        payment.credit_payment_acct_id = 2
        testdb.flush()
        testdb.commit()
        pp = BiweeklyPayPeriod(date(2017, 4, 21), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('300.00')


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestNoBudgetImpactSums(AcceptanceHelper):
    """
    Pay period arithmetic and unreconciled sums for the general
    no-budget-impact designation; GitHub issue #319.
    """

    def test_10_clean_db(self, dump_file_path):
        restore_mysqldump(dump_file_path, get_db_engine(), with_data=False)

    def test_11_add_account_and_budget(self, testdb):
        a = Account(
            description='Bank Account',
            name='BankOne',
            acct_type=AcctType.Bank,
            reconcile_trans=True
        )
        testdb.add(a)
        testdb.add(Budget(
            name='Groceries',
            is_periodic=True,
            description='Groceries',
            starting_balance=Decimal('500.00')
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_12_add_ordinary_transaction(self, testdb):
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(1)
        testdb.add(Transaction(
            date=date(2017, 4, 10),
            budget_amounts={budget: Decimal('100.00')},
            description='Ordinary',
            account=acct
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_13_baseline(self, testdb):
        pp = BiweeklyPayPeriod(date(2017, 4, 7), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('100.00')
        assert pp.budget_sums[1]['remaining'] == Decimal('400.00')
        assert testdb.query(Account).get(1).unreconciled_sum == \
            Decimal('100.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_14_excluded_transaction_moves_nothing(self, testdb):
        """Spec US1 scenarios 1 and 2: the period still shows 100.00 spent and
        the account still shows 100.00 unreconciled."""
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(1)
        testdb.add(Transaction(
            date=date(2017, 4, 12),
            budget_amounts={budget: Decimal('40.00')},
            description='Statement credit',
            account=acct,
            no_budget_impact=True
        ))
        testdb.flush()
        testdb.commit()
        pp = BiweeklyPayPeriod(date(2017, 4, 7), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('100.00')
        assert pp.budget_sums[1]['allocated'] == Decimal('100.00')
        assert pp.budget_sums[1]['trans_total'] == Decimal('100.00')
        assert pp.budget_sums[1]['remaining'] == Decimal('400.00')
        assert pp.overall_sums['spent'] == Decimal('100.00')
        assert testdb.query(Account).get(1).unreconciled_sum == \
            Decimal('100.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_15_still_reconcilable(self, testdb):
        """Spec US1 scenarios 3 and 5: an excluded transaction is still
        offered for reconciliation. unreconciled_sum ignores it; the
        unreconciled *query* does not."""
        ids = [t.id for t in Transaction.unreconciled(testdb).all()]
        assert 2 in ids
        acct_ids = [t.id for t in testdb.query(Account).get(1).unreconciled]
        assert 2 in acct_ids

    @patch('%s.settings.PAY_PERIOD_START_DATE' % pbm, date(2017, 4, 7))
    def test_16_clearing_flag_restores_impact(self, testdb):
        """Spec US1 scenario 4: clearing the flag makes the totals rise by the
        transaction's amount; setting it again returns them."""
        t = testdb.query(Transaction).get(2)
        t.no_budget_impact = False
        testdb.flush()
        testdb.commit()
        pp = BiweeklyPayPeriod(date(2017, 4, 7), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('140.00')
        assert testdb.query(Account).get(1).unreconciled_sum == \
            Decimal('140.00')

        t = testdb.query(Transaction).get(2)
        t.no_budget_impact = True
        testdb.flush()
        testdb.commit()
        pp = BiweeklyPayPeriod(date(2017, 4, 7), testdb)
        assert pp.budget_sums[1]['spent'] == Decimal('100.00')
        assert testdb.query(Account).get(1).unreconciled_sum == \
            Decimal('100.00')
