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

from biweeklybudget.models import *
from biweeklybudget.models.account import AcctType
from biweeklybudget.utils import dtnow
from biweeklybudget.flaskapp.jsonencoder import MagicJSONEncoder
from datetime import timedelta, datetime
from pytz import UTC
from decimal import Decimal
import json


class SampleDataLoader(object):

    def __init__(self, db_session):
        self.db = db_session
        self.accounts = {}
        self.statements = {}
        self.budgets = {}
        self.scheduled_transactions = []
        self.transactions = {}
        self.plaid_items = {}
        self.plaid_accounts = {}
        self.dt = dtnow()

    def load(self):
        self._fuellog()
        self.db.flush()
        self.db.commit()
        for f in self.db.query(FuelFill).all():
            f.calculate_mpg()
        self.db.flush()
        self.db.commit()
        self.db.add(
            DBSetting(
                name='prime_rate',
                value=json.dumps({
                    'value': '0.0050',
                    'date': dtnow()
                }, cls=MagicJSONEncoder)
            )
        )
        self.plaid_items = self._plaid_items()
        self.plaid_accounts = self._plaid_accounts()
        self.db.flush()
        self.db.commit()
        self._projects()
        self.accounts = {
            'BankOne': self._bank_one(),
            'BankTwoStale': self._bank_two_stale(),
            'CreditOne': self._credit_one(),
            'CreditTwo': self._credit_two(),
            'InvestmentOne': self._investment_one(),
            'DisabledBank': self._disabled_bank()
        }
        self.budgets = self._budgets()
        self.scheduled_transactions = self._scheduled_transactions()
        self.transactions = self._transactions()
        self.db.add(TxnReconcile(
            ofx_trans=self.accounts['BankOne']['transactions'][0][1],
            transaction=self.transactions[0],
            note='reconcile notes',
            reconciled_at=datetime(2017, 4, 10, 8, 9, 11, tzinfo=UTC)
        ))
        self.db.flush()
        self.db.commit()

    def _plaid_items(self):
        res = {
            'PlaidItem1': PlaidItem(
                item_id='PlaidItem1',
                access_token='AccessToken1',
                institution_name='Inst1',
                last_updated=self.dt
            ),
            'PlaidItem2': PlaidItem(
                item_id='PlaidItem2',
                access_token='AccessToken2',
                institution_name='Inst2',
                last_updated=self.dt
            ),
        }
        for item in res.values():
            self.db.add(item)
        return res

    def _plaid_accounts(self):
        res = {
            'PlaidAcct1': PlaidAccount(
                item_id='PlaidItem1',
                account_id='PlaidAcct1',
                name='Acct1',
                mask='foo',
                account_type='depository',
                account_subtype='checking'
            ),
            'PlaidAcct2': PlaidAccount(
                item_id='PlaidItem1',
                account_id='PlaidAcct2',
                name='Acct2',
                mask='foo',
                account_type='credit',
                account_subtype='credit card'
            ),
            'PlaidAcct3': PlaidAccount(
                item_id='PlaidItem2',
                account_id='PlaidAcct3',
                name='Acct3',
                mask='foo',
                account_type='investment',
                account_subtype='401k'
            ),
            'PlaidAcct4': PlaidAccount(
                item_id='PlaidItem1',
                account_id='PlaidAcct4',
                name='Acct4',
                mask='foo4',
                account_type='depository',
                account_subtype='checking'
            ),
        }
        for item in res.values():
            self.db.add(item)
        return res

    def _budgets(self):
        res = {
            'Periodic1': Budget(
                name='Periodic1',
                is_periodic=True,
                description='P1desc',
                starting_balance=Decimal(100)
            ),
            'Periodic2': Budget(
                name='Periodic2',
                is_periodic=True,
                description='P2desc',
                starting_balance=Decimal(234)
            ),
            'Periodic3 Inactive': Budget(
                name='Periodic3 Inactive',
                is_periodic=True,
                description='P3desc',
                starting_balance=Decimal('10.23'),
                is_active=False
            ),
            'Standing1': Budget(
                name='Standing1',
                is_periodic=False,
                description='S1desc',
                current_balance=Decimal('1284.23'),
                omit_from_graphs=True
            ),
            'Standing2': Budget(
                name='Standing2',
                is_periodic=False,
                description='S2desc',
                current_balance=Decimal('9482.29')
            ),
            'Standing3 Inactive': Budget(
                name='Standing3 Inactive',
                is_periodic=False,
                description='S3desc',
                current_balance=Decimal('-92.29'),
                is_active=False
            ),
            'Income': Budget(
                name='Income',
                is_periodic=True,
                description='IncomeDesc',
                starting_balance=Decimal('2345.67'),
                is_income=True,
                omit_from_graphs=True
            )
        }
        for x in [
            'Periodic1', 'Periodic2', 'Periodic3 Inactive',
            'Standing1', 'Standing2', 'Standing3 Inactive',
            'Income'
        ]:
            self.db.add(res[x])
        return res

    def _scheduled_transactions(self):
        res = [
            ScheduledTransaction(
                amount=Decimal('111.11'),
                description='ST1',
                notes='notesST1',
                account=self.accounts['BankOne']['account'],
                budget=self.budgets['Periodic1'],
                date=(self.dt + timedelta(days=4)).date()
            ),
            ScheduledTransaction(
                amount=Decimal('222.22'),
                description='ST2',
                notes='notesST2',
                account=self.accounts['BankOne']['account'],
                budget=self.budgets['Periodic2'],
                day_of_month=4
            ),
            ScheduledTransaction(
                amount=Decimal('-333.33'),
                description='ST3',
                notes='notesST3',
                account=self.accounts['BankTwoStale']['account'],
                budget=self.budgets['Standing1'],
                num_per_period=1
            ),
            ScheduledTransaction(
                amount=Decimal('444.44'),
                description='ST4',
                notes='notesST4',
                account=self.accounts['BankOne']['account'],
                budget=self.budgets['Periodic1'],
                date=(self.dt + timedelta(days=5)).date(),
                is_active=False
            ),
            ScheduledTransaction(
                amount=Decimal('555.55'),
                description='ST5',
                notes='notesST5',
                account=self.accounts['BankOne']['account'],
                budget=self.budgets['Periodic2'],
                day_of_month=5,
                is_active=False
            ),
            ScheduledTransaction(
                amount=Decimal('666.66'),
                description='ST6',
                notes='notesST6',
                account=self.accounts['BankTwoStale']['account'],
                budget=self.budgets['Standing1'],
                num_per_period=3,
                is_active=False
            )
        ]
        for x in res:
            self.db.add(x)
        return res

    def _transactions(self):
        res = [
            Transaction(
                date=(self.dt + timedelta(days=4)).date(),
                budget_amounts={self.budgets['Periodic1']: Decimal('111.13')},
                budgeted_amount=Decimal('111.11'),
                description='T1foo',
                notes='notesT1',
                account=self.accounts['BankOne']['account'],
                scheduled_trans=self.scheduled_transactions[0],
                planned_budget=self.budgets['Periodic1']
            ),
            Transaction(
                date=self.dt.date(),
                budget_amounts={self.budgets['Standing1']: Decimal('-333.33')},
                budgeted_amount=Decimal('-333.33'),
                description='T2',
                notes='notesT2',
                account=self.accounts['BankTwoStale']['account'],
                scheduled_trans=self.scheduled_transactions[2],
                planned_budget=self.budgets['Standing1']
            ),
            Transaction(
                date=(self.dt - timedelta(days=2)).date(),
                budget_amounts={self.budgets['Periodic2']: Decimal('222.22')},
                description='T3',
                notes='notesT3',
                account=self.accounts['CreditOne']['account']
            ),
            Transaction(
                date=(self.dt - timedelta(days=35)).date(),
                budget_amounts={
                    self.budgets['Periodic2']: Decimal('222.22'),
                    self.budgets['Periodic1']: Decimal('100.10')
                },
                description='T4split',
                notes='notesT4split',
                account=self.accounts['CreditOne']['account']
            )
        ]
        for x in res:
            self.db.add(x)
        return res

    def _add_account(self, acct, statements, transactions):
        self.db.add(acct)
        for s in statements:
            self.db.add(s)
            acct.set_balance(
                overall_date=s.as_of,
                ledger=s.ledger_bal,
                ledger_date=s.ledger_bal_as_of,
                avail=s.avail_bal,
                avail_date=s.avail_bal_as_of
            )
        for s in transactions.keys():
            for t in transactions[s]:
                self.db.add(t)
        return {
            'account': acct,
            'statements': statements,
            'transactions': transactions
        }

    def _bank_one(self):
        acct = Account(
            description='First Bank Account',
            name='BankOne',
            ofx_cat_memo_to_name=True,
            ofxgetter_config_json='{"foo": "bar"}',
            vault_creds_path='secret/foo/bar/BankOne',
            acct_type=AcctType.Bank,
            re_interest_charge='^interest-charge',
            re_interest_paid='^interest-paid',
            re_payment='^(payment|thank you)',
            re_late_fee='^Late Fee',
            re_other_fee='^re-other-fee',
            plaid_item_id='PlaidItem1',
            plaid_account_id='PlaidAcct1',
        )
        statements = [
            OFXStatement(
                account=acct,
                filename='/stmt/BankOne/0',
                file_mtime=(self.dt - timedelta(hours=46)),
                currency='USD',
                bankid='BankOne',
                routing_number='11',
                acct_type='Checking',
                acctid='1111',
                type='Bank',
                as_of=(self.dt - timedelta(hours=46)),
                ledger_bal=Decimal('12345.67'),
                ledger_bal_as_of=(self.dt - timedelta(hours=46)),
                avail_bal=Decimal('12340.00'),
                avail_bal_as_of=(self.dt - timedelta(hours=46))
            ),
            OFXStatement(
                account=acct,
                filename='/stmt/BankOne/1',
                file_mtime=(self.dt - timedelta(hours=14)),
                currency='USD',
                bankid='BankOne',
                routing_number='11',
                acct_type='Checking',
                acctid='1111',
                type='Bank',
                as_of=(self.dt - timedelta(hours=14)),
                ledger_bal=Decimal('12789.01'),
                ledger_bal_as_of=(self.dt - timedelta(hours=14)),
                avail_bal=Decimal('12563.18'),
                avail_bal_as_of=(self.dt - timedelta(hours=14))
            )
        ]
        transactions = {
            0: [
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='BankOne.0.0',
                    trans_type='Credit',
                    date_posted=(self.dt - timedelta(days=7)),
                    amount=Decimal('1234.56'),
                    name='BankOne.0.0'
                ),
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='BankOne.0.1',
                    trans_type='Debit',
                    date_posted=(self.dt - timedelta(days=6)),
                    amount=Decimal('-20.00'),
                    name='Late Fee'
                )
            ],
            1: []
        }
        for x in range(1, 21):
            mult = 1
            if x % 2 == 0:
                mult = -1
            amt = (11 * x) * mult
            transactions[1].append(OFXTransaction(
                    account=acct,
                    statement=statements[1],
                    fitid='BankOne.1.%d' % x,
                    trans_type='Debit',
                    date_posted=(self.dt - timedelta(days=6, hours=x)),
                    amount=Decimal(amt),
                    name='Generated Trans %d' % x
            ))
        return self._add_account(acct, statements, transactions)

    def _bank_two_stale(self):
        acct = Account(
            description='Stale Bank Account',
            name='BankTwoStale',
            ofx_cat_memo_to_name=False,
            ofxgetter_config_json='{"foo": "baz"}',
            vault_creds_path='secret/foo/bar/BankTwo',
            acct_type=AcctType.Bank,
            is_active=True,
            negate_ofx_amounts=True
        )
        statements = [
            OFXStatement(
                account=acct,
                filename='/stmt/BankTwoStale/0',
                file_mtime=(self.dt - timedelta(days=18)),
                currency='USD',
                bankid='BankTwoStale',
                routing_number='22',
                acct_type='Savings',
                acctid='2222',
                type='Bank',
                as_of=(self.dt - timedelta(days=18)),
                ledger_bal=Decimal('100.23'),
                ledger_bal_as_of=(self.dt - timedelta(days=18))
            )
        ]
        transactions = {
            0: [
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='0',
                    trans_type='Debit',
                    date_posted=(self.dt - timedelta(days=23)),
                    amount=Decimal('432.19'),
                    name='Transfer to Other Account'
                ),
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='1',
                    trans_type='Interest',
                    date_posted=(self.dt - timedelta(days=22)),
                    amount=Decimal('0.23'),
                    name='Interest Paid',
                    memo='Some Date'
                )
            ]
        }
        return self._add_account(acct, statements, transactions)

    def _credit_one(self):
        acct = Account(
            description='First Credit Card, limit 2000',
            name='CreditOne',
            ofx_cat_memo_to_name=False,
            acct_type=AcctType.Credit,
            credit_limit=Decimal('2000.00'),
            is_active=True,
            prime_rate_margin=Decimal('0.0050'),
            negate_ofx_amounts=True,
            interest_class_name='AdbCompoundedDaily',
            min_payment_class_name='MinPaymentAmEx',
            re_interest_charge='^INTEREST CHARGED TO',
            re_payment='.*Online Payment, thank you.*',
            re_late_fee='^Late Fee',
            re_other_fee='^re-other-fee',
            plaid_item_id='PlaidItem1',
            plaid_account_id='PlaidAcct2',
        )
        statements = [
            OFXStatement(
                account=acct,
                filename='/stmt/CreditOne/3',
                file_mtime=(self.dt - timedelta(days=1)),
                currency='USD',
                bankid='CreditOne',
                acct_type='Credit',
                acctid='CreditOneAcctId',
                type='Credit',
                as_of=(self.dt - timedelta(days=1)),
                ledger_bal=Decimal('-435.29'),
                ledger_bal_as_of=(self.dt - timedelta(days=1)),
            ),
            OFXStatement(
                account=acct,
                filename='/stmt/CreditOne/1',
                file_mtime=(self.dt - timedelta(days=30, hours=13)),
                currency='USD',
                bankid='CreditOne',
                acct_type='Credit',
                acctid='CreditOneAcctId',
                type='Credit',
                as_of=(self.dt - timedelta(days=30, hours=13)),
                ledger_bal=Decimal('-876.54'),
                ledger_bal_as_of=(self.dt - timedelta(days=30, hours=13)),
            ),
            OFXStatement(
                account=acct,
                filename='/stmt/CreditOne/0',
                file_mtime=(self.dt - timedelta(hours=13)),
                currency='USD',
                bankid='CreditOne',
                acct_type='Credit',
                acctid='CreditOneAcctId',
                type='Credit',
                as_of=(self.dt - timedelta(hours=13)),
                ledger_bal=Decimal('-952.06'),
                ledger_bal_as_of=(self.dt - timedelta(hours=13)),
            )
        ]
        transactions = {
            0: [
                OFXTransaction(
                    account=acct,
                    statement=statements[2],
                    fitid='T1',
                    trans_type='Purchase',
                    date_posted=(self.dt - timedelta(hours=22)),
                    amount=Decimal('-123.81'),
                    name='123.81 Credit Purchase T1',
                    memo='38328',
                    description='CreditOneT1Desc',
                    checknum=123,
                    mcc='T1mcc',
                    sic='T1sic'
                ),
                OFXTransaction(
                    account=acct,
                    statement=statements[2],
                    fitid='T2',
                    trans_type='credit',
                    date_posted=(self.dt - timedelta(days=2)),
                    amount=Decimal('52.00'),
                    name='$52.00 Online Payment, thank you',
                    memo='38328',
                    description='CreditOneT2Desc'
                ),
                OFXTransaction(
                    account=acct,
                    statement=statements[2],
                    fitid='T3',
                    trans_type='debit',
                    date_posted=(self.dt - timedelta(hours=13)),
                    amount=Decimal('-16.25'),
                    name='INTEREST CHARGED TO STANDARD PUR',
                    memo='38328',
                    description='CreditOneT3Desc'
                )
            ],
            1: [
                OFXTransaction(
                    account=acct,
                    statement=statements[1],
                    fitid='T2-1',
                    trans_type='credit',
                    date_posted=(self.dt - timedelta(days=32)),
                    amount=Decimal('60.00'),
                    name='$60.00 Online Payment, thank you',
                    memo='38328',
                    description='CreditOneT2Desc'
                ),
                OFXTransaction(
                    account=acct,
                    statement=statements[1],
                    fitid='T2-2',
                    trans_type='debit',
                    date_posted=(self.dt - timedelta(days=30, hours=13)),
                    amount=Decimal('-25.94'),
                    name='INTEREST CHARGED TO STANDARD PUR',
                    memo='38328',
                    description='CreditOneT3Desc'
                )
            ]
        }
        return self._add_account(acct, statements, transactions)

    def _credit_two(self):
        acct = Account(
            description='Credit 2 limit 5500',
            name='CreditTwo',
            ofx_cat_memo_to_name=False,
            ofxgetter_config_json='',
            vault_creds_path='/foo/bar',
            acct_type=AcctType.Credit,
            credit_limit=Decimal(5500),
            is_active=True,
            apr=Decimal('0.1000'),
            interest_class_name='AdbCompoundedDaily',
            min_payment_class_name='MinPaymentDiscover'
        )
        statements = [
            OFXStatement(
                account=acct,
                filename='/stmt/CreditTwo/0',
                file_mtime=(self.dt - timedelta(hours=36)),
                currency='USD',
                bankid='CreditTwo',
                acct_type='Credit',
                acctid='',
                type='CreditCard',
                as_of=(self.dt - timedelta(hours=36)),
                ledger_bal=Decimal('-5498.65'),
                ledger_bal_as_of=(self.dt - timedelta(hours=36))
            )
        ]
        transactions = {
            0: [
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='001',
                    trans_type='Purchase',
                    date_posted=(self.dt - timedelta(hours=36)),
                    amount=Decimal('28.53'),
                    name='Interest Charged',
                    memo=''
                ),
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='002',
                    trans_type='Credit',
                    date_posted=(self.dt - timedelta(days=5)),
                    amount=Decimal('-50.00'),
                    name='Online Payment - Thank You',
                    memo=''
                )
            ]
        }
        return self._add_account(acct, statements, transactions)

    def _investment_one(self):
        acct = Account(
            description='Investment One Stale',
            name='InvestmentOne',
            ofx_cat_memo_to_name=False,
            ofxgetter_config_json='',
            vault_creds_path='',
            acct_type=AcctType.Investment,
            is_active=True,
            reconcile_trans=False,
            plaid_item_id='PlaidItem2',
            plaid_account_id='PlaidAcct3',
        )
        statements = [
            OFXStatement(
                account=acct,
                filename='/stmt/InvOne/0',
                file_mtime=(self.dt - timedelta(days=13, hours=6)),
                currency='USD',
                acct_type='Retirement',
                brokerid='InvOneBroker',
                acctid='1000001',
                type='Investment',
                as_of=(self.dt - timedelta(days=13, hours=6)),
                ledger_bal=Decimal('10362.91'),
                ledger_bal_as_of=(self.dt - timedelta(days=13, hours=6))
            )
        ]
        return self._add_account(acct, statements, {})

    def _disabled_bank(self):
        acct = Account(
            description='Disabled Bank Account',
            name='DisabledBank',
            ofx_cat_memo_to_name=True,
            ofxgetter_config_json='{"bar": "baz"}',
            vault_creds_path='',
            acct_type=AcctType.Bank,
            is_active=False
        )
        statements = [
            OFXStatement(
                account=acct,
                filename='/stmt/DisabledBank/0',
                file_mtime=(self.dt - timedelta(days=41)),
                currency='USD',
                bankid='111DDD111',
                routing_number='111DDD111',
                acct_type='Savings',
                acctid='D1111111',
                type='Bank',
                as_of=(self.dt - timedelta(hours=46)),
                ledger_bal=Decimal('10.00'),
                ledger_bal_as_of=(self.dt - timedelta(days=41)),
                avail_bal=Decimal('10.00'),
                avail_bal_as_of=(self.dt - timedelta(days=41))
            )
        ]
        transactions = {
            0: [
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='001',
                    trans_type='Credit',
                    date_posted=(self.dt - timedelta(days=43)),
                    amount=Decimal('0.01'),
                    name='Interest Paid',
                    memo=''
                ),
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='002',
                    trans_type='Debit',
                    date_posted=(self.dt - timedelta(days=51)),
                    amount=Decimal('3218.87'),
                    name='ATM Withdrawal',
                    memo='Disabled002Memo',
                    description='Disabled002Desc'
                )
            ]
        }
        return self._add_account(acct, statements, transactions)

    def _example_bank(self):
        """Sample to copy"""
        acct = Account(
            description='',
            name='',
            ofx_cat_memo_to_name=False,
            ofxgetter_config_json='',
            vault_creds_path='',
            acct_type=AcctType.Bank,
            # credit_limit=0,
            is_active=True
        )
        statements = [
            OFXStatement(
                account=acct,
                filename='/stmt/BankOne/0',
                file_mtime=(self.dt - timedelta(hours=46)),
                currency='USD',
                bankid='',
                routing_number='',
                acct_type='',
                brokerid='',
                acctid='',
                type='',
                as_of=(self.dt - timedelta(hours=46)),
                ledger_bal=Decimal('12345.67'),
                ledger_bal_as_of=(self.dt - timedelta(hours=46)),
                avail_bal=Decimal('12340.00'),
                avail_bal_as_of=(self.dt - timedelta(hours=46))
            )
        ]
        transactions = {
            0: [
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='',
                    trans_type='',
                    date_posted=(self.dt - timedelta(days=7)),
                    amount=Decimal('1234.56'),
                    name='',
                    memo=''
                ),
                OFXTransaction(
                    account=acct,
                    statement=statements[0],
                    fitid='',
                    trans_type='',
                    date_posted=(self.dt - timedelta(days=7)),
                    amount=Decimal('1234.56'),
                    name='',
                    memo=''
                )
            ]
        }
        return self._add_account(acct, statements, transactions)

    def _fuellog(self):
        v1 = Vehicle(name='Veh1')
        self.db.add(v1)
        v2 = Vehicle(name='Veh2')
        self.db.add(v2)
        v3 = Vehicle(name='Veh3Inactive', is_active=False)
        self.db.add(v3)
        start_dt = dtnow()
        for veh_num, veh in {1: v1, 2: v2, 3: v3}.items():
            veh_str = 'v%d' % veh_num
            for i in range(0, 2):
                dt = start_dt + timedelta(days=i)
                self.db.add(FuelFill(
                    date=dt.date(),
                    vehicle=veh,
                    odometer_miles=(1000 + (i * 10) + veh_num),
                    reported_miles=(100 + (i * 10) + veh_num),
                    level_before=(i * 10) + veh_num,
                    level_after=(100 - (i * 10) - veh_num),
                    fill_location='fill_loc %s %d' % (veh_str, i),
                    cost_per_gallon=(
                        Decimal('2.0') + (i * Decimal('0.1')) +
                        (veh_num * Decimal('0.01'))
                    ),
                    total_cost=(
                        (
                            Decimal('2.0') + (i * Decimal('0.1')) +
                            (veh_num * Decimal('0.01'))
                        ) * (1 + i)
                    ),
                    gallons=(i * 10) + veh_num,
                    reported_mpg=(20 + i) + (veh_num * 0.1),
                    notes='notes %s %d' % (veh_str, i)
                ))

    def _projects(self):
        # P1 - Active=77.77 Total=2546.89
        p1 = Project(name='P1', notes='ProjectOne')
        self.db.add(p1)
        self.db.add(BoMItem(
            project=p1,
            name='P1Item1',
            notes='P1Item1Notes',
            unit_cost=Decimal('11.11')
        ))
        self.db.add(BoMItem(
            project=p1,
            name='P1Item2',
            notes='P1Item2Notes',
            unit_cost=Decimal('22.22'),
            quantity=3,
            url='http://item2.p1.com'
        ))
        self.db.add(BoMItem(
            project=p1,
            name='P1Item3',
            notes='P1Item3Notes',
            unit_cost=Decimal('1234.56'),
            quantity=2,
            url='http://item3.p1.com',
            is_active=False
        ))
        p2 = Project(name='P2', notes='ProjectTwo')
        self.db.add(p2)
        # P3 - Active=3.0 Total=5.34
        p3 = Project(
            name='P3Inactive', notes='ProjectThreeInactive', is_active=False
        )
        self.db.add(p3)
        self.db.add(BoMItem(
            project=p3,
            name='P3Item2',
            notes='P3Item2Notes',
            unit_cost=Decimal('1.0'),
            quantity=3,
            url='http://item2.p3.com'
        ))
        self.db.add(BoMItem(
            project=p3,
            name='P3Item3',
            notes='P3Item3Notes',
            unit_cost=Decimal('2.34'),
            url='http://item3.p3.com',
            is_active=False
        ))
