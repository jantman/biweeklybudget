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
from datetime import datetime, timedelta
from pytz import UTC
from decimal import Decimal

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.tests.conftest import get_db_engine
from biweeklybudget.tests.sqlhelpers import restore_mysqldump
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.ofx_statement import OFXStatement
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.flaskapp.notifications import NotificationsController
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.utils import dtnow
from biweeklybudget.models.txn_reconcile import TxnReconcile
from selenium.webdriver.common.by import By


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestBaseTemplateNavigation(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)

    def test_heading(self, selenium):
        heading = selenium.find_element(By.CLASS_NAME, 'navbar-brand')
        assert heading.text == 'BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element(By.ID, 'side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_nav_links(self, selenium):
        nav = selenium.find_element(By.XPATH,
                                    "//div[contains(@class, 'sidebar-nav')]/ul"
                                    )
        navlinks = []
        for li in nav.find_elements(By.XPATH, "//li/a"):
            if li.text.strip() == '':
                continue
            navlinks.append(
                (self.relurl(li.get_attribute('href')), li.text)
            )
        assert navlinks == [
            ('/', 'Home'),
            ('/payperiods', 'Pay Periods'),
            ('/accounts', 'Accounts'),
            ('/accounts/credit-payoff', 'Credit Payoffs'),
            ('/ofx', 'OFX'),
            ('/plaid-update', 'Plaid Update'),
            ('/transactions', 'Transactions'),
            ('/reconcile', 'Reconcile'),
            ('/budgets', 'Budgets'),
            ('/scheduled', 'Scheduled'),
            ('/fuel', 'Fuel Log'),
            ('/projects', 'Projects / BoM'),
            ('/help', 'Help/Docs/Code (AGPL)')
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestBaseTemplateNotifications(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)

    def test_notifications(self, selenium):
        div = selenium.find_element(By.ID, 'notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'

    def test_stale_accounts(self, selenium):
        div = selenium.find_elements(By.XPATH,
                                     "//div[@id='notifications-row']/div/div"
                                     )[0]
        assert div.text == '2 Accounts with stale data. View Accounts.'
        a = div.find_element(By.TAG_NAME, 'a')
        assert self.relurl(a.get_attribute('href')) == '/accounts'
        assert a.text == 'View Accounts'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestBaseTmplUnreconciledNotification(AcceptanceHelper):

    def test_0_clean_db(self, dump_file_path):
        # clean the database; empty schema
        restore_mysqldump(dump_file_path, get_db_engine(), with_data=False)

    def test_01_add(self, testdb):
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
        b = Budget(
            name='1Income',
            is_periodic=True,
            description='1Income',
            starting_balance=Decimal('0.0'),
            is_income=True
        )
        testdb.add(b)
        testdb.flush()
        testdb.commit()

    def test_02_notification_none(self, selenium, base_url):
        self.get(selenium, base_url)
        assert 'unreconciled-alert' not in selenium.page_source
        assert 'Unreconciled Transactions' not in selenium.page_source

    def test_03_add_ofx(self, testdb):
        acct1 = testdb.query(Account).get(1)
        stmt1 = OFXStatement(
            account=acct1,
            filename='a1.ofx',
            file_mtime=datetime(2017, 4, 10, 12, 31, 42, tzinfo=UTC),
            as_of=datetime(2017, 4, 10, 12, 31, 42, tzinfo=UTC),
            currency='USD',
            acctid='1',
            bankid='b1',
            routing_number='r1'
        )
        testdb.add(stmt1)
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFX1',
            trans_type='Deposit',
            date_posted=datetime(2017, 4, 10, 12, 3, 4, tzinfo=UTC),
            amount=Decimal('-100.0'),
            name='ofx1-income'
        ))
        # matches Transaction 2
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFX2',
            trans_type='Debit',
            date_posted=datetime(2017, 4, 11, 12, 3, 4, tzinfo=UTC),
            amount=Decimal('250.0'),
            name='ofx2-trans1'
        ))
        # matches Transcation 3
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFX3',
            trans_type='Purchase',
            date_posted=datetime(2017, 4, 9, 12, 3, 4, tzinfo=UTC),
            amount=Decimal('-600.0'),
            name='ofx3-trans2-st1'
        ))
        testdb.flush()
        testdb.commit()

    def test_04_notification(self, selenium, base_url):
        self.baseurl = base_url
        self.get(selenium, base_url)
        div = selenium.find_element(By.CLASS_NAME, 'unreconciled-alert')
        assert div.text == '3 Unreconciled OFXTransactions.'
        assert div.get_attribute(
            'class'
        ) == 'alert alert-warning unreconciled-alert'
        a = div.find_element(By.TAG_NAME, 'a')
        assert self.relurl(a.get_attribute('href')) == '/reconcile'
        assert a.text == 'Unreconciled OFXTransactions'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestBudgetOverBalanceNotification(AcceptanceHelper):

    def test_0_update_db(self, testdb):
        b = testdb.query(Budget).get(4)
        b.current_balance = Decimal('123456.78')
        testdb.add(b)
        testdb.flush()
        testdb.commit()

    def test_1_confirm_db(self, testdb):
        b = testdb.query(Budget).get(4)
        assert b.current_balance == Decimal('123456.78')

    def test_2_confirm_pp(self, testdb):
        acct_bal = NotificationsController.budget_account_sum(testdb)
        assert acct_bal == Decimal('12889.24')
        stand_bal = NotificationsController.standing_budgets_sum(testdb)
        assert stand_bal == Decimal('132939.07')
        pp_bal = NotificationsController.pp_sum(testdb)
        assert pp_bal == Decimal('11.76')
        unrec_amt = NotificationsController.budget_account_unreconciled(testdb)
        assert unrec_amt == Decimal('-333.33')
        credit_bal = NotificationsController.credit_account_sum(testdb)
        assert credit_bal == Decimal('-6450.71')

    def test_3_notification(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)
        div = selenium.find_elements(By.XPATH,
                                     "//div[@id='notifications-row']/div/div"
                                     )[1]
        assert div.text == 'Combined balance of all budget-funding ' \
                           'accounts less credit account balances ' \
                           '($6,438.53) is less than all allocated funds ' \
                           'total of $132,617.50 ($132,939.07 standing ' \
                           'budgets; $11.76 current pay period allocated ' \
                           'but unspent; -$333.33 unreconciled)!'
        assert div.get_attribute('class') == 'alert alert-danger'
        a = div.find_elements(By.TAG_NAME, 'a')
        assert self.relurl(a[0].get_attribute('href')) == '/accounts'
        assert a[0].text == 'budget-funding accounts'
        assert self.relurl(a[1].get_attribute('href')) == '/accounts'
        assert a[1].text == 'credit account balances'
        assert self.relurl(a[2].get_attribute('href')) == '/budgets'
        assert a[2].text == 'standing budgets'
        assert self.relurl(a[3].get_attribute('href')) == '/pay_period_for'
        assert a[3].text == 'current pay period allocated but unspent'
        assert self.relurl(a[4].get_attribute('href')) == '/reconcile'
        assert a[4].text == 'unreconciled'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestPPOverBalanceNotification(AcceptanceHelper):

    def test_0_update_db(self, testdb):
        b = testdb.query(Budget).get(4)
        b.current_balance = Decimal('1617.56')
        testdb.add(b)
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(1)
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), testdb)
        tdate = pp.start_date + timedelta(days=2)
        stmt1 = OFXStatement(
            account=acct,
            filename='a1.ofx',
            file_mtime=dtnow(),
            as_of=dtnow(),
            currency='USD',
            acctid='1',
            bankid='b1',
            routing_number='r1'
        )
        testdb.add(stmt1)
        o = OFXTransaction(
            account=acct,
            statement=stmt1,
            fitid='OFX8',
            trans_type='Purchase',
            date_posted=dtnow(),
            amount=Decimal('-600.0'),
            name='ofx8-trans4'
        )
        testdb.add(o)
        t = Transaction(
            date=tdate,
            budget_amounts={budget: Decimal('600.00')},
            description='trans6',
            account=acct
        )
        testdb.add(t)
        testdb.add(TxnReconcile(transaction=t, ofx_trans=o))
        t2 = Transaction(
            date=tdate,
            budget_amounts={budget: Decimal('34000.00')},
            description='transFoo',
            account=acct
        )
        testdb.add(t2)
        testdb.flush()
        testdb.commit()

    def test_1_confirm_pp(self, testdb):
        acct_bal = NotificationsController.budget_account_sum(testdb)
        assert acct_bal == Decimal('12889.24')
        stand_bal = NotificationsController.standing_budgets_sum(testdb)
        assert stand_bal == Decimal('11099.85')
        pp_bal = NotificationsController.pp_sum(testdb)
        assert pp_bal == Decimal('11.76')
        unrec_amt = NotificationsController.budget_account_unreconciled(testdb)
        assert unrec_amt == Decimal('33666.67')
        credit_bal = NotificationsController.credit_account_sum(testdb)
        assert credit_bal == Decimal('-6450.71')

    def test_2_notification(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)
        div = selenium.find_elements(By.XPATH,
                                     "//div[@id='notifications-row']/div/div"
                                     )[1]
        assert div.text == 'Combined balance of all budget-funding ' \
                           'accounts less credit account balances ' \
                           '($6,438.53) is less than all allocated funds ' \
                           'total of $44,778.28 ($11,099.85 standing ' \
                           'budgets; $11.76 current pay period allocated ' \
                           'but unspent; $33,666.67 unreconciled)!'
        assert div.get_attribute('class') == 'alert alert-danger'
        a = div.find_elements(By.TAG_NAME, 'a')
        assert self.relurl(a[0].get_attribute('href')) == '/accounts'
        assert a[0].text == 'budget-funding accounts'
        assert self.relurl(a[1].get_attribute('href')) == '/accounts'
        assert a[1].text == 'credit account balances'
        assert self.relurl(a[2].get_attribute('href')) == '/budgets'
        assert a[2].text == 'standing budgets'
        assert self.relurl(a[3].get_attribute('href')) == '/pay_period_for'
        assert a[3].text == 'current pay period allocated but unspent'
        assert self.relurl(a[4].get_attribute('href')) == '/reconcile'
        assert a[4].text == 'unreconciled'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestUnderBalanceNotification(AcceptanceHelper):

    def test_0_update_db(self, testdb):
        testdb.query(Account).get(1).set_balance(
            ledger=Decimal('428890.24'),
            avail=Decimal('428890.24'),
            ledger_date=dtnow(),
            avail_date=dtnow(),
            overall_date=dtnow()
        )
        testdb.flush()
        testdb.commit()

    def test_1_confirm_db(self, testdb):
        a = testdb.query(Account).get(1)
        assert a.balance.ledger == Decimal('428890.24')
        assert a.balance.avail == Decimal('428890.24')

    def test_2_confirm_pp(self, testdb):
        acct_bal = NotificationsController.budget_account_sum(testdb)
        assert acct_bal == Decimal('428990.47')
        stand_bal = NotificationsController.standing_budgets_sum(testdb)
        assert stand_bal == Decimal('10766.52')
        pp_bal = NotificationsController.pp_sum(testdb)
        assert pp_bal == Decimal('11.76')
        unrec_amt = NotificationsController.budget_account_unreconciled(testdb)
        assert unrec_amt == Decimal('-333.33')
        credit_bal = NotificationsController.credit_account_sum(testdb)
        assert credit_bal == Decimal('-6450.71')

    def test_3_notification(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)
        div = selenium.find_elements(By.XPATH,
                                     "//div[@id='notifications-row']/div/div"
                                     )[1]
        assert div.text == 'Combined balance of all budget-funding ' \
                           'accounts less credit account balances ' \
                           '($422,539.76) is more than all allocated funds ' \
                           'total of $10,444.95 ($10,766.52 standing ' \
                           'budgets; $11.76 current pay period allocated ' \
                           'but unspent; -$333.33 unreconciled)!'
        assert div.get_attribute('class') == 'alert alert-info'
        a = div.find_elements(By.TAG_NAME, 'a')
        assert self.relurl(a[0].get_attribute('href')) == '/accounts'
        assert a[0].text == 'budget-funding accounts'
        assert self.relurl(a[1].get_attribute('href')) == '/accounts'
        assert a[1].text == 'credit account balances'
        assert self.relurl(a[2].get_attribute('href')) == '/budgets'
        assert a[2].text == 'standing budgets'
        assert self.relurl(a[3].get_attribute('href')) == '/pay_period_for'
        assert a[3].text == 'current pay period allocated but unspent'
        assert self.relurl(a[4].get_attribute('href')) == '/reconcile'
        assert a[4].text == 'unreconciled'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestCreditAccountSumAccountSelection(AcceptanceHelper):
    """
    Covers which accounts contribute to the credit deduction, against the real
    database rather than a mocked query. See GitHub issue #320 FR-002.

    The sample data holds two active credit accounts, CreditOne (-952.06) and
    CreditTwo (-5498.65), for a combined -6450.71.
    """

    def test_0_baseline(self, testdb):
        assert NotificationsController.credit_account_sum(
            testdb
        ) == Decimal('-6450.71')

    def test_1_inactive_credit_account_excluded(self, testdb):
        """
        An inactive credit account is not money the person still has to
        settle, and must not be deducted.
        """
        acct = Account(
            description='Closed Card',
            name='ClosedCard',
            ofx_cat_memo_to_name=False,
            acct_type=AcctType.Credit,
            is_active=False
        )
        testdb.add(acct)
        acct.set_balance(
            ledger=Decimal('-1000.00'),
            avail=Decimal('-1000.00'),
            ledger_date=dtnow(),
            avail_date=dtnow(),
            overall_date=dtnow()
        )
        testdb.flush()
        testdb.commit()
        assert NotificationsController.credit_account_sum(
            testdb
        ) == Decimal('-6450.71')

    def test_2_active_credit_account_included(self, testdb):
        """
        Activating that same account brings its balance into the deduction,
        proving the previous assertion turned on is_active and not on some
        other property of the account.
        """
        acct = testdb.query(Account).filter(
            Account.name.__eq__('ClosedCard')
        ).one()
        acct.is_active = True
        testdb.add(acct)
        testdb.flush()
        testdb.commit()
        assert NotificationsController.credit_account_sum(
            testdb
        ) == Decimal('-7450.71')

    def test_3_non_credit_accounts_excluded(self, testdb):
        """
        Bank, cash and investment balances are not credit balances; only the
        credit accounts are deducted, never the funding accounts that are
        already counted on the other side of the comparison.
        """
        acct = Account(
            description='Another Bank',
            name='AnotherBank',
            ofx_cat_memo_to_name=False,
            acct_type=AcctType.Bank,
            is_active=True
        )
        testdb.add(acct)
        acct.set_balance(
            ledger=Decimal('5000.00'),
            avail=Decimal('5000.00'),
            ledger_date=dtnow(),
            avail_date=dtnow(),
            overall_date=dtnow()
        )
        inv = Account(
            description='Another Investment',
            name='AnotherInvestment',
            ofx_cat_memo_to_name=False,
            acct_type=AcctType.Investment,
            is_active=True
        )
        testdb.add(inv)
        inv.set_balance(
            ledger=Decimal('90000.00'),
            avail=Decimal('90000.00'),
            ledger_date=dtnow(),
            avail_date=dtnow(),
            overall_date=dtnow()
        )
        testdb.flush()
        testdb.commit()
        assert NotificationsController.credit_account_sum(
            testdb
        ) == Decimal('-7450.71')

    def test_4_credit_account_without_balance(self, testdb):
        """
        A credit account that has never had a balance recorded contributes
        nothing, and must not stop the notification being produced (FR-003).
        """
        acct = Account(
            description='Brand New Card',
            name='BrandNewCard',
            ofx_cat_memo_to_name=False,
            acct_type=AcctType.Credit,
            is_active=True
        )
        testdb.add(acct)
        testdb.flush()
        testdb.commit()
        assert acct.balance is None
        assert NotificationsController.credit_account_sum(
            testdb
        ) == Decimal('-7450.71')

    def test_5_notification_still_rendered(self, base_url, selenium):
        """
        With a balance-less credit account present, the banner still renders
        (FR-003). The banner lives in the base template, so any page shows it.

        This deliberately uses /budgets rather than the index. The index page
        crashes outright on an *active* account that has no AccountBalance row
        at all: templates/index.html dereferences ``acct.balance.ledger`` in
        the credit accounts table with no None guard. That is a pre-existing
        limitation, unrelated to and untouched by this change, and fixing it
        is out of scope here -- but it means the index is the one page that
        cannot be used to prove this requirement.
        """
        self.baseurl = base_url
        self.get(selenium, base_url + '/budgets')
        divs = selenium.find_elements(
            By.XPATH, "//div[@id='notifications-row']/div/div"
        )
        contents = [d.text for d in divs]
        assert any(
            'less credit account balances' in c for c in contents
        ), contents


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestNoCashImpactNotification(AcceptanceHelper):
    """
    Regression coverage for the second defect in GitHub issue #320:
    transactions that move no real cash must not inflate the unreconciled
    figure the banner reports, and so must not shift the banner's verdict.

    The exclusion itself is not implemented here. It already exists, from the
    work for issues #210 and #319: ``Transaction.is_excluded_from_budget`` is
    true both for a transaction flagged ``no_budget_impact`` and for one that
    is a payment toward a credit account, and ``Account.unreconciled_sum``
    skips both. Nothing tied that to the banner, though, so a regression there
    would silently reintroduce an error of thousands of dollars for days at a
    time -- which is exactly what the issue describes. These tests are that
    tie.

    If they fail, the fault is in the exclusion code, not in the notification.
    """

    def test_0_baseline(self, testdb):
        assert NotificationsController.budget_account_unreconciled(
            testdb
        ) == Decimal('-333.33')

    def test_1_ordinary_unreconciled_counts(self, testdb):
        """
        An ordinary unreconciled transaction is real money leaving the
        account and must be counted, so the exclusions below are shown to be
        about the exclusion and not about unreconciled transactions in
        general.
        """
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(1)
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), testdb)
        testdb.add(Transaction(
            date=pp.start_date + timedelta(days=1),
            budget_amounts={budget: Decimal('250.00')},
            description='ordinary unreconciled',
            account=acct
        ))
        testdb.flush()
        testdb.commit()
        assert NotificationsController.budget_account_unreconciled(
            testdb
        ) == Decimal('-83.33')

    def test_2_no_budget_impact_excluded(self, testdb):
        """
        A no-budget-impact transaction -- the pseudo-transaction pattern the
        issue describes -- must not move the figure at all, however large.
        """
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(1)
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), testdb)
        testdb.add(Transaction(
            date=pp.start_date + timedelta(days=1),
            budget_amounts={budget: Decimal('2000.00')},
            description='pseudo-transaction',
            account=acct,
            no_budget_impact=True
        ))
        testdb.flush()
        testdb.commit()
        assert NotificationsController.budget_account_unreconciled(
            testdb
        ) == Decimal('-83.33')

    def test_3_credit_payment_excluded(self, testdb):
        """
        A payment toward a credit account is likewise excluded, without
        needing the flag set as well.
        """
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(1)
        card = Account.active_credit_accounts(testdb).first()
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), testdb)
        t = Transaction(
            date=pp.start_date + timedelta(days=1),
            budget_amounts={budget: Decimal('3000.00')},
            description='card payment',
            account=acct,
            credit_payment_acct=card
        )
        testdb.add(t)
        testdb.flush()
        testdb.commit()
        assert t.is_excluded_from_budget is True
        assert t.no_budget_impact is False
        assert NotificationsController.budget_account_unreconciled(
            testdb
        ) == Decimal('-83.33')

    def test_4_banner_reports_excluding_them(self, base_url, selenium):
        """
        The banner itself, not just the helper, reports the figure that
        excludes them: $5,000 of no-cash-impact transactions are outstanding,
        and the banner must still say -$83.33.
        """
        self.baseurl = base_url
        self.get(selenium, base_url + '/budgets')
        div = selenium.find_elements(
            By.XPATH, "//div[@id='notifications-row']/div/div"
        )[1]
        assert '-$83.33 unreconciled' in div.text
        assert '$2,000.00' not in div.text
        assert '$3,000.00' not in div.text

    def test_5_still_reconcilable(self, base_url, selenium):
        """
        Excluding these from the arithmetic must not hide them from
        reconciliation: both still appear in the reconcile view, and are
        still there to be reconciled (FR-010).
        """
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')
        self.wait_for_jquery_done(selenium)
        src = selenium.page_source
        assert 'pseudo-transaction' in src
        assert 'card payment' in src
        assert 'ordinary unreconciled' in src
