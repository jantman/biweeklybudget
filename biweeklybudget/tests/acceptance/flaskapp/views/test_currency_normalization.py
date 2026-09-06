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

import pytest
import requests
from decimal import Decimal
from datetime import timedelta

from biweeklybudget.utils import dtnow
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.projects import BoMItem
from biweeklybudget.models.fuel import FuelFill
from biweeklybudget.models.scheduled_transaction import ScheduledTransaction
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.dbsetting import DBSetting


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestCurrencyNormalizationAcrossForms(AcceptanceHelper):
    """
    Every currency input in the application must accept common formatting;
    GitHub issue #323. This covers the forms whose client-side behavior is not
    itself affected by the change - the Transaction modal, which is, has
    dedicated browser tests in ``test_transactions.py``.

    Each test posts a separator-formatted value to a real form endpoint over
    HTTP and asserts the value actually persisted.
    """

    def test_01_budget_starting_balance(self, base_url):
        res = requests.post(
            base_url + '/forms/budget',
            json={
                'id': '',
                'name': 'CommaBudget',
                'description': 'comma',
                'is_periodic': True,
                'starting_balance': '$1,234.56',
                'current_balance': '',
                'is_active': True,
                'is_income': False,
                'omit_from_graphs': False
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_02_verify_budget_starting_balance(self, testdb):
        b = testdb.query(Budget).filter(
            Budget.name.__eq__('CommaBudget')
        ).one()
        assert b.starting_balance == Decimal('1234.56')

    def test_03_budget_bare_integer_balance(self, base_url):
        res = requests.post(
            base_url + '/forms/budget',
            json={
                'id': '',
                'name': 'IntBudget',
                'description': 'int',
                'is_periodic': False,
                'starting_balance': '',
                'current_balance': '1234',
                'is_active': True,
                'is_income': False,
                'omit_from_graphs': False
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_04_verify_budget_bare_integer_balance(self, testdb):
        b = testdb.query(Budget).filter(
            Budget.name.__eq__('IntBudget')
        ).one()
        assert b.current_balance == Decimal('1234')

    def test_05_budget_invalid_balance(self, base_url):
        res = requests.post(
            base_url + '/forms/budget',
            json={
                'id': '',
                'name': 'BadBudget',
                'description': 'bad',
                'is_periodic': True,
                'starting_balance': '10,00',
                'current_balance': '',
                'is_active': True,
                'is_income': False,
                'omit_from_graphs': False
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors'] == {
            'starting_balance': ['Invalid amount: "10,00"']
        }

    def test_06_verify_invalid_budget_not_saved(self, testdb):
        assert testdb.query(Budget).filter(
            Budget.name.__eq__('BadBudget')
        ).all() == []

    def test_10_budget_transfer(self, base_url):
        res = requests.post(
            base_url + '/forms/budget_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '$1,234.56',
                'notes': 'BudgetTransferComma',
                'account': '1',
                'from_budget': '4',
                'to_budget': '5'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_11_verify_budget_transfer(self, testdb):
        txns = testdb.query(Transaction).filter(
            Transaction.notes.__eq__('BudgetTransferComma')
        ).all()
        assert len(txns) == 2
        assert sorted([t.actual_amount for t in txns]) == [
            Decimal('-1234.56'), Decimal('1234.56')
        ]

    def test_20_account_transfer(self, base_url):
        res = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '1 234.56',
                'notes': 'AcctTransferSpace',
                'budget': '1',
                'from_account': '1',
                'to_account': '2'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_21_verify_account_transfer(self, testdb):
        txns = testdb.query(Transaction).filter(
            Transaction.notes.__eq__('AcctTransferSpace')
        ).all()
        assert len(txns) == 2
        assert sorted([t.actual_amount for t in txns]) == [
            Decimal('-1234.56'), Decimal('1234.56')
        ]

    def test_30_account_credit_limit_and_rates(self, base_url, testdb):
        acct = testdb.query(Account).get(3)
        res = requests.post(
            base_url + '/forms/account',
            json={
                'id': '3',
                'name': acct.name,
                'description': acct.description or '',
                'acct_type': 'Credit',
                'ofx_cat_memo_to_name': False,
                'vault_creds_path': '',
                'ofxgetter_config_json': '',
                'negate_ofx_amounts': False,
                'reconcile_trans': True,
                're_interest_charge': '',
                're_interest_paid': '',
                're_payment': '',
                're_late_fee': '',
                're_other_fee': '',
                'credit_limit': '$12,345',
                'apr': '0.1000',
                'prime_rate_margin': '0.0050',
                'interest_class_name': 'AdbCompoundedDaily',
                'min_payment_class_name': 'MinPaymentAmEx',
                'is_active': True,
                'plaid_account': 'null,null'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_31_verify_account_credit_limit(self, testdb):
        acct = testdb.query(Account).get(3)
        assert acct.credit_limit == Decimal('12345')

    def test_40_bom_item_bare_integer_unit_cost(self, base_url):
        res = requests.post(
            base_url + '/forms/bom_item',
            json={
                'id': '',
                'project_id': '1',
                'name': 'IntCostItem',
                'notes': '',
                'quantity': '2',
                'unit_cost': '40',
                'url': '',
                'is_active': True
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_41_verify_bom_item_bare_integer_unit_cost(self, testdb):
        item = testdb.query(BoMItem).filter(
            BoMItem.name.__eq__('IntCostItem')
        ).one()
        assert item.unit_cost == Decimal('40')

    def test_42_bom_item_comma_unit_cost(self, base_url):
        res = requests.post(
            base_url + '/forms/bom_item',
            json={
                'id': '',
                'project_id': '1',
                'name': 'CommaCostItem',
                'notes': '',
                'quantity': '1',
                'unit_cost': '$1,234.56',
                'url': '',
                'is_active': True
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_43_verify_bom_item_comma_unit_cost(self, testdb):
        item = testdb.query(BoMItem).filter(
            BoMItem.name.__eq__('CommaCostItem')
        ).one()
        assert item.unit_cost == Decimal('1234.56')

    def test_44_bom_item_invalid_unit_cost(self, base_url):
        res = requests.post(
            base_url + '/forms/bom_item',
            json={
                'id': '',
                'project_id': '1',
                'name': 'BadCostItem',
                'notes': '',
                'quantity': '1',
                'unit_cost': 'abc',
                'url': '',
                'is_active': True
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors'] == {'unit_cost': ['Invalid amount: "abc"']}

    def test_50_fuel_fill_bare_integers(self, base_url):
        res = requests.post(
            base_url + '/forms/fuel',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'vehicle': '1',
                'odometer_miles': '1111',
                'reported_miles': '100',
                'level_before': '10',
                'level_after': '100',
                'fill_location': 'IntFill',
                'cost_per_gallon': '3',
                'total_cost': '30',
                'gallons': '10',
                'reported_mpg': '10',
                'notes': '',
                'add_trans': False,
                'account': 'None',
                'budget': 'None'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_51_verify_fuel_fill_bare_integers(self, testdb):
        f = testdb.query(FuelFill).filter(
            FuelFill.fill_location.__eq__('IntFill')
        ).one()
        assert f.cost_per_gallon == Decimal('3')
        assert f.total_cost == Decimal('30')
        assert f.gallons == Decimal('10')
        assert f.reported_mpg == Decimal('10')

    def test_52_fuel_fill_comma_total(self, base_url):
        res = requests.post(
            base_url + '/forms/fuel',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'vehicle': '1',
                'odometer_miles': '1211',
                'reported_miles': '100',
                'level_before': '10',
                'level_after': '100',
                'fill_location': 'CommaFill',
                'cost_per_gallon': '$3.50',
                'total_cost': '$1,234.56',
                'gallons': '10.5',
                'reported_mpg': '10.5',
                'notes': '',
                'add_trans': False,
                'account': 'None',
                'budget': 'None'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_53_verify_fuel_fill_comma_total(self, testdb):
        f = testdb.query(FuelFill).filter(
            FuelFill.fill_location.__eq__('CommaFill')
        ).one()
        assert f.total_cost == Decimal('1234.56')
        assert f.cost_per_gallon == Decimal('3.50')

    def test_54_fuel_fill_invalid_gallons_uses_number_wording(self, base_url):
        res = requests.post(
            base_url + '/forms/fuel',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'vehicle': '1',
                'odometer_miles': '1311',
                'reported_miles': '100',
                'level_before': '10',
                'level_after': '100',
                'fill_location': 'BadFill',
                'cost_per_gallon': '3',
                'total_cost': '30',
                'gallons': 'abc',
                'reported_mpg': '10',
                'notes': '',
                'add_trans': False,
                'account': 'None',
                'budget': 'None'
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors'] == {'gallons': ['Invalid number: "abc"']}

    def test_55_verify_invalid_fuel_fill_not_saved(self, testdb):
        assert testdb.query(FuelFill).filter(
            FuelFill.fill_location.__eq__('BadFill')
        ).all() == []

    def test_60_scheduled_transaction(self, base_url):
        res = requests.post(
            base_url + '/forms/scheduled',
            json={
                'id': '',
                'description': 'CommaSched',
                'type': 'monthly',
                'day_of_month': '4',
                'amount': '$1,234.56',
                'sales_tax': '89',
                'account': '1',
                'budget': '1',
                'notes': '',
                'is_active': True
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_61_verify_scheduled_transaction(self, testdb):
        st = testdb.query(ScheduledTransaction).filter(
            ScheduledTransaction.description.__eq__('CommaSched')
        ).one()
        assert st.amount == Decimal('1234.56')
        assert st.sales_tax == Decimal('89')

    def test_62_scheduled_transaction_invalid_amount(self, base_url):
        res = requests.post(
            base_url + '/forms/scheduled',
            json={
                'id': '',
                'description': 'BadSched',
                'type': 'monthly',
                'day_of_month': '4',
                'amount': '1,23,4.56',
                'sales_tax': '',
                'account': '1',
                'budget': '1',
                'notes': '',
                'is_active': True
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors'] == {'amount': ['Invalid amount: "1,23,4.56"']}

    def test_63_verify_invalid_scheduled_not_saved(self, testdb):
        assert testdb.query(ScheduledTransaction).filter(
            ScheduledTransaction.description.__eq__('BadSched')
        ).all() == []

    def test_70_payoff_settings_normalized_on_write(self, base_url):
        res = requests.post(
            base_url + '/settings/credit-payoff',
            json={
                'increases': [
                    {
                        'enabled': True,
                        'date': (
                            dtnow() + timedelta(days=30)
                        ).strftime('%Y-%m-%d'),
                        'amount': '$1,234.56'
                    }
                ],
                'onetimes': [
                    {
                        'enabled': True,
                        'date': (
                            dtnow() + timedelta(days=60)
                        ).strftime('%Y-%m-%d'),
                        'amount': '2,000'
                    }
                ]
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_71_verify_payoff_settings_stored_canonical(self, testdb):
        import json
        setting = testdb.query(DBSetting).get('credit-payoff')
        val = json.loads(setting.value)
        assert val['increases'][0]['amount'] == '1234.56'
        assert val['onetimes'][0]['amount'] == '2000'
        # the stored value must be directly parseable, because the credit
        # payoff page re-parses it while rendering
        assert Decimal(val['increases'][0]['amount']) == Decimal('1234.56')

    def test_72_payoff_settings_invalid_amount(self, base_url):
        res = requests.post(
            base_url + '/settings/credit-payoff',
            json={
                'increases': [
                    {
                        'enabled': True,
                        'date': (
                            dtnow() + timedelta(days=30)
                        ).strftime('%Y-%m-%d'),
                        'amount': '10,00'
                    }
                ],
                'onetimes': []
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['error_message'] == 'Invalid amount: "10,00"'

    def test_73_verify_payoff_settings_unchanged(self, testdb):
        import json
        setting = testdb.query(DBSetting).get('credit-payoff')
        val = json.loads(setting.value)
        # still the value stored by test_70, not the rejected one
        assert val['increases'][0]['amount'] == '1234.56'

    def test_80_sched_to_trans(self, base_url, testdb):
        st = testdb.query(ScheduledTransaction).get(1)
        pp = BiweeklyPayPeriod.period_for_date(dtnow().date(), testdb)
        res = requests.post(
            base_url + '/forms/sched_to_trans',
            json={
                'id': str(st.id),
                'payperiod_start_date': pp.start_date.strftime('%Y-%m-%d'),
                'date': pp.start_date.strftime('%Y-%m-%d'),
                'amount': '$1,234.56',
                'sales_tax': '89',
                'description': 'SchedToTransComma',
                'notes': ''
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_81_verify_sched_to_trans(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('SchedToTransComma')
        ).one()
        assert t.actual_amount == Decimal('1234.56')
        assert t.sales_tax == Decimal('89')

    def test_82_sched_to_trans_invalid_amount(self, base_url, testdb):
        st = testdb.query(ScheduledTransaction).get(1)
        pp = BiweeklyPayPeriod.period_for_date(dtnow().date(), testdb)
        res = requests.post(
            base_url + '/forms/sched_to_trans',
            json={
                'id': str(st.id),
                'payperiod_start_date': pp.start_date.strftime('%Y-%m-%d'),
                'date': pp.start_date.strftime('%Y-%m-%d'),
                'amount': '1.2.3',
                'sales_tax': '',
                'description': 'SchedToTransBad',
                'notes': ''
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors'] == {'amount': ['Invalid amount: "1.2.3"']}

    def test_83_verify_invalid_sched_to_trans_not_saved(self, testdb):
        assert testdb.query(Transaction).filter(
            Transaction.description.__eq__('SchedToTransBad')
        ).all() == []

    def test_90_skip_sched_trans(self, base_url, testdb):
        st = testdb.query(ScheduledTransaction).get(2)
        pp = BiweeklyPayPeriod.period_for_date(dtnow().date(), testdb)
        res = requests.post(
            base_url + '/forms/skip_sched_trans',
            json={
                'id': str(st.id),
                'payperiod_start_date': pp.start_date.strftime('%Y-%m-%d'),
                'date': pp.start_date.strftime('%Y-%m-%d'),
                'amount': '1,234.56',
                'description': 'SkipSchedComma',
                'notes': 'SkipSchedComma'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_91_verify_skip_sched_trans(self, testdb):
        # the skip record is always created with a zero amount; what matters
        # here is that the comma-formatted amount passed validation instead of
        # raising out of validate()
        assert testdb.query(Transaction).filter(
            Transaction.notes.__eq__('SkipSchedComma')
        ).one() is not None

    def test_92_skip_sched_trans_invalid_amount(self, base_url, testdb):
        st = testdb.query(ScheduledTransaction).get(3)
        pp = BiweeklyPayPeriod.period_for_date(dtnow().date(), testdb)
        res = requests.post(
            base_url + '/forms/skip_sched_trans',
            json={
                'id': str(st.id),
                'payperiod_start_date': pp.start_date.strftime('%Y-%m-%d'),
                'date': pp.start_date.strftime('%Y-%m-%d'),
                'amount': '10,00',
                'description': 'SkipSchedBad',
                'notes': 'SkipSchedBad'
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors'] == {'amount': ['Invalid amount: "10,00"']}


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestCurrencyNormalizationDoesNotChangeExistingBehavior(AcceptanceHelper):
    """
    Normalization widens what is accepted; it must not narrow it, and it must
    not disturb each field's existing blank-value semantics (FR-010).
    """

    def test_blank_optional_currency_field_still_allowed(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '100.00',
                'description': 'BlankSalesTax',
                'notes': '',
                'account': '1',
                'budgets': {'1': '100.00'},
                'sales_tax': ''
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_zero_amount_still_rejected(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '0',
                'description': 'ZeroAmount',
                'notes': '',
                'account': '1',
                'budgets': {'1': '0'},
                'sales_tax': ''
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['amount'] == ['Amount cannot be zero']

    def test_negative_zero_still_counts_as_zero(self, base_url):
        # "-0.00" normalizes to 0.00, so the zero check must still fire
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '-0.00',
                'description': 'NegZeroAmount',
                'notes': '',
                'account': '1',
                'budgets': {'1': '-0.00'},
                'sales_tax': ''
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['amount'] == ['Amount cannot be zero']

    def test_empty_required_amount_is_not_a_server_error(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '',
                'description': 'EmptyAmount',
                'notes': '',
                'account': '1',
                'budgets': {'1': ''},
                'sales_tax': ''
            }
        )
        # a blank required amount is left for validate() to handle; whatever
        # it decides, it must not be a 500
        assert res.status_code == 200
        assert res.json()['success'] is False
