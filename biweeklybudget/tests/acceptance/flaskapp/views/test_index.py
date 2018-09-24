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
from datetime import datetime, timedelta
from pytz import UTC
from decimal import Decimal

from selenium.webdriver.support.ui import Select
from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.tests.sqlhelpers import restore_mysqldump
from biweeklybudget.tests.conftest import get_db_engine
from biweeklybudget.models import *
from biweeklybudget.settings import PAY_PERIOD_START_DATE
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestIndexNavigation(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element_by_id('side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_notifications(self, selenium):
        div = selenium.find_element_by_id('notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestIndexAccounts(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)

    def test_bank_table(self, selenium):
        table = selenium.find_element_by_xpath(
            "//div[@id='panel-bank-accounts']//table"
        )
        assert self.thead2list(table) == [
            'Account', 'Balance', 'Unreconciled', 'Difference'
        ]
        assert self.tbody2textlist(table) == [
            ['BankOne', '$12,789.01 (14 hours ago)', '$0.00', '$12,789.01'],
            ['BankTwoStale', '$100.23 (18 days ago)', '-$333.33', '$433.56']
        ]
        links = []
        tbody = table.find_element_by_tag_name('tbody')
        for tr in tbody.find_elements_by_tag_name('tr'):
            td = tr.find_elements_by_tag_name('td')[0]
            links.append(td.get_attribute('innerHTML'))
        assert links == [
            '<a href="/accounts/1">BankOne</a>',
            '<a href="/accounts/2">BankTwoStale</a>',
        ]

    def test_bank_stale_span(self, selenium):
        tbody = selenium.find_element_by_xpath(
            "//div[@id='panel-bank-accounts']//table/tbody"
        )
        rows = tbody.find_elements_by_tag_name('tr')
        bankTwoStale_bal_td = rows[1].find_elements_by_tag_name('td')[1]
        bal_span = bankTwoStale_bal_td.find_elements_by_tag_name('span')[1]
        assert bal_span.text == '(18 days ago)'
        assert bal_span.get_attribute('class') == 'data_age text-danger'

    def test_credit_table(self, selenium):
        table = selenium.find_element_by_xpath(
            "//div[@id='panel-credit-cards']//table"
        )
        assert self.thead2list(table) == [
            'Account', 'Balance', 'Available', 'Avail - Unrec'
        ]
        assert self.tbody2textlist(table) == [
            ['CreditOne', '-$952.06 (13 hours ago)', '$1,047.94', '$503.40'],
            ['CreditTwo', '-$5,498.65 (a day ago)', '$1.35', '$1.35']
        ]
        links = []
        tbody = table.find_element_by_tag_name('tbody')
        for tr in tbody.find_elements_by_tag_name('tr'):
            td = tr.find_elements_by_tag_name('td')[0]
            links.append(td.get_attribute('innerHTML'))
        assert links == [
            '<a href="/accounts/3">CreditOne</a>',
            '<a href="/accounts/4">CreditTwo</a>',
        ]

    def test_investment_table(self, selenium):
        table = selenium.find_element_by_xpath(
            "//div[@id='panel-investment']//table"
        )
        assert self.thead2list(table) == ['Account', 'Value']
        assert self.tbody2textlist(table) == [
            ['InvestmentOne', '$10,362.91 (13 days ago)']
        ]
        links = []
        tbody = table.find_element_by_tag_name('tbody')
        for tr in tbody.find_elements_by_tag_name('tr'):
            td = tr.find_elements_by_tag_name('td')[0]
            links.append(td.get_attribute('innerHTML'))
        assert links == [
            '<a href="/accounts/5">InvestmentOne</a>'
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestIndexBudgets(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/')

    def test_budgets_table(self, selenium):
        stable = selenium.find_element_by_id('table-standing-budgets')
        stexts = self.tbody2textlist(stable)
        assert stexts == [
            ['Standing1 (4)', '$1,284.23'],
            ['Standing2 (5)', '$9,482.29']
        ]
        selems = self.tbody2elemlist(stable)
        assert selems[0][0].get_attribute(
            'innerHTML') == '<a href="/budgets/4">' \
                            'Standing1 (4)</a>'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestIndexPayPeriods(AcceptanceHelper):

    def test_0_clean_db(self, dump_file_path):
        # clean the database; empty schema
        restore_mysqldump(dump_file_path, get_db_engine(), with_data=False)

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
            ledger=Decimal('1.0'),
            ledger_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC)
        )
        testdb.flush()
        testdb.commit()

    def test_2_add_budgets(self, testdb):
        testdb.add(Budget(
            name='1Income',
            is_periodic=True,
            description='1Income',
            starting_balance=Decimal('1000.00'),
            is_income=True
        ))
        testdb.add(Budget(
            name='2Periodic',
            is_periodic=True,
            description='2Periodic',
            starting_balance=Decimal('500.00')
        ))
        testdb.add(Budget(
            name='3Periodic',
            is_periodic=True,
            description='3Periodic',
            starting_balance=Decimal('0.00')
        ))
        testdb.flush()
        testdb.commit()

    def pay_periods(self, db):
        x = BiweeklyPayPeriod.period_for_date(
            (PAY_PERIOD_START_DATE - timedelta(days=2)), db
        )
        periods = []
        for i in range(0, 10):
            periods.append(x)
            x = x.next
        return periods

    def test_3_add_transactions(self, testdb):
        acct = testdb.query(Account).get(1)
        ibudget = testdb.query(Budget).get(1)
        e1budget = testdb.query(Budget).get(2)
        e2budget = testdb.query(Budget).get(3)
        periods = self.pay_periods(testdb)
        # previous pay period
        ppdate = periods[0].start_date
        t1 = Transaction(
            date=(ppdate + timedelta(days=1)),
            budget_amounts={ibudget: Decimal('100.00')},
            budgeted_amount=Decimal('100.00'),
            description='prev income',
            account=acct,
            planned_budget=ibudget
        )
        testdb.add(t1)
        t2 = Transaction(
            date=(ppdate + timedelta(days=2)),
            budget_amounts={e2budget: Decimal('250.00')},
            description='prev trans 1',
            account=acct
        )
        testdb.add(t2)
        t3 = Transaction(
            date=(ppdate + timedelta(days=3)),
            budget_amounts={e1budget: Decimal('600.00')},
            budgeted_amount=Decimal('500.00'),
            description='prev trans 2',
            account=acct,
            planned_budget=e1budget
        )
        testdb.add(t3)
        ppdate = periods[1].start_date
        t4 = Transaction(
            date=(ppdate + timedelta(days=1)),
            budget_amounts={ibudget: Decimal('1400.00')},
            budgeted_amount=Decimal('100.00'),
            description='prev income',
            account=acct,
            planned_budget=ibudget
        )
        testdb.add(t4)
        t5 = Transaction(
            date=(ppdate + timedelta(days=2)),
            budget_amounts={e2budget: Decimal('1850.00')},
            description='prev trans 1',
            account=acct
        )
        testdb.add(t5)
        t6 = Transaction(
            date=(ppdate + timedelta(days=3)),
            budget_amounts={e1budget: Decimal('600.00')},
            budgeted_amount=Decimal('500.00'),
            description='prev trans 2',
            account=acct,
            planned_budget=e1budget
        )
        testdb.add(t6)
        ppdate = periods[2].start_date
        t7 = Transaction(
            date=(ppdate + timedelta(days=1)),
            budget_amounts={ibudget: Decimal('1400.00')},
            budgeted_amount=Decimal('100.00'),
            description='prev income',
            account=acct,
            planned_budget=ibudget
        )
        testdb.add(t7)
        t8 = Transaction(
            date=(ppdate + timedelta(days=2)),
            budget_amounts={e2budget: Decimal('788.00')},
            description='prev trans 1',
            account=acct
        )
        testdb.add(t8)
        t9 = Transaction(
            date=(ppdate + timedelta(days=3)),
            budget_amounts={e1budget: Decimal('600.00')},
            budgeted_amount=Decimal('500.00'),
            description='prev trans 2',
            account=acct,
            planned_budget=e1budget
        )
        testdb.add(t9)
        ppdate = periods[3].start_date
        t10 = Transaction(
            date=(ppdate + timedelta(days=1)),
            budget_amounts={ibudget: Decimal('1400.00')},
            budgeted_amount=Decimal('100.00'),
            description='prev income',
            account=acct,
            planned_budget=ibudget
        )
        testdb.add(t10)
        t11 = Transaction(
            date=(ppdate + timedelta(days=2)),
            budget_amounts={e2budget: Decimal('2.00')},
            description='prev trans 1',
            account=acct
        )
        testdb.add(t11)
        t12 = Transaction(
            date=(ppdate + timedelta(days=3)),
            budget_amounts={e1budget: Decimal('600.00')},
            budgeted_amount=Decimal('500.00'),
            description='prev trans 2',
            account=acct,
            planned_budget=e1budget
        )
        testdb.add(t12)
        testdb.flush()
        testdb.commit()

    def test_4_confirm_sums(self, testdb):
        periods = self.pay_periods(testdb)
        assert periods[0].overall_sums == {
            'allocated': Decimal('750.0'),
            'spent': Decimal('850.0'),
            'income': Decimal('1000.0'),
            'remaining': Decimal('150.0')
        }
        assert periods[1].overall_sums == {
            'allocated': Decimal('2350.0'),
            'spent': Decimal('2450.0'),
            'income': Decimal('1400.0'),
            'remaining': Decimal('-1050.0')
        }
        assert periods[2].overall_sums == {
            'allocated': Decimal('1288.0'),
            'spent': Decimal('1388.0'),
            'income': Decimal('1400.0'),
            'remaining': Decimal('12.0')
        }
        assert periods[3].overall_sums == {
            'allocated': Decimal('502.0'),
            'spent': Decimal('602.0'),
            'income': Decimal('1400.0'),
            'remaining': Decimal('798.0')
        }

    def test_5_pay_periods_table(self, base_url, selenium, testdb):
        periods = self.pay_periods(testdb)
        self.get(selenium, base_url + '/')
        table = selenium.find_element_by_id('pay-period-table')
        texts = self.tbody2textlist(table)
        elems = self.tbody2elemlist(table)
        expected = [
            [
                periods[1].start_date.strftime('%Y-%m-%d') + ' (current)',
                '$2,350.00',
                '$2,450.00',
                '-$1,050.00'
            ],
            [
                periods[2].start_date.strftime('%Y-%m-%d'),
                '$1,288.00',
                '$1,388.00',
                '$12.00'
            ],
            [
                periods[3].start_date.strftime('%Y-%m-%d'),
                '$502.00',
                '$602.00',
                '$798.00'
            ]
        ]
        for i in range(4, 10):
            expected.append([
                periods[i].start_date.strftime('%Y-%m-%d'),
                '$500.00',
                '$0.00',
                '$500.00'
            ])
        assert texts == expected
        # test links
        links = [x[0].get_attribute('innerHTML') for x in elems]
        expected = []
        for idx, period in enumerate(periods):
            if idx == 0:
                continue
            dstr = period.start_date.strftime('%Y-%m-%d')
            s = '<a href="/payperiod/%s">%s</a>' % (dstr, dstr)
            if idx == 1:
                s += ' <em>(current)</em>'
            expected.append(s)
        assert links == expected
        # test red text for negative dollar amounts
        assert elems[0][3].get_attribute('innerHTML') == '<span ' \
            'class="text-danger">-$1,050.00</span>'
        # test highlighted row for current period
        tbody = table.find_element_by_tag_name('tbody')
        trs = tbody.find_elements_by_tag_name('tr')
        assert trs[0].get_attribute('class') == 'info'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestAccountTransfer(AcceptanceHelper):

    def test_01_verify_db(self, testdb):
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 4
        accts = {
            t.id: t for t in testdb.query(Account).all()
        }
        assert accts[1].acct_type == AcctType.Bank
        assert accts[1].balance.ledger == Decimal('12789.01')
        assert accts[1].unreconciled_sum == Decimal('0.0')
        assert accts[2].acct_type == AcctType.Bank
        assert accts[2].balance.ledger == Decimal('100.23')
        assert accts[2].unreconciled_sum == Decimal('-333.33')
        assert accts[3].acct_type == AcctType.Credit
        assert accts[4].acct_type == AcctType.Credit
        assert accts[5].acct_type == AcctType.Investment
        assert accts[5].balance.ledger == Decimal('10362.91')

    def test_02_transfer_modal(self, base_url, selenium):
        # Fill in the form
        self.get(selenium, base_url + '/')
        # check the table content on the page
        btable = selenium.find_element_by_id('table-accounts-bank')
        btexts = self.tbody2textlist(btable)
        assert btexts == [
            [
                'BankOne',
                '$12,789.01 (14 hours ago)',
                '$0.00',
                '$12,789.01'
            ],
            [
                'BankTwoStale',
                '$100.23 (18 days ago)',
                '-$333.33',
                '$433.56'
            ]
        ]
        itable = selenium.find_element_by_id('table-accounts-investment')
        itexts = self.tbody2textlist(itable)
        assert itexts == [
            [
                'InvestmentOne',
                '$10,362.91 (13 days ago)'
            ]
        ]
        # open the modal to do a transfer
        link = selenium.find_element_by_id('btn_acct_txfr_bank')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Account Transfer'
        assert body.find_element_by_id(
            'acct_txfr_frm_date').get_attribute('value') == dtnow(
            ).strftime('%Y-%m-%d')
        amt = body.find_element_by_id('acct_txfr_frm_amount')
        amt.clear()
        amt.send_keys('123.45')
        budget_sel = Select(
            body.find_element_by_id('acct_txfr_frm_budget')
        )
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['7', 'Income (i)']
        ]
        assert budget_sel.first_selected_option.get_attribute(
            'value') == 'None'
        budget_sel.select_by_value('2')
        from_acct_sel = Select(
            body.find_element_by_id('acct_txfr_frm_from_account')
        )
        opts = []
        for o in from_acct_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'BankOne'],
            ['2', 'BankTwoStale'],
            ['3', 'CreditOne'],
            ['4', 'CreditTwo'],
            ['6', 'DisabledBank'],
            ['5', 'InvestmentOne']
        ]
        assert from_acct_sel.first_selected_option.get_attribute(
            'value'
        ) == 'None'
        from_acct_sel.select_by_value('1')
        to_acct_sel = Select(
            body.find_element_by_id('acct_txfr_frm_to_account')
        )
        opts = []
        for o in to_acct_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'BankOne'],
            ['2', 'BankTwoStale'],
            ['3', 'CreditOne'],
            ['4', 'CreditTwo'],
            ['6', 'DisabledBank'],
            ['5', 'InvestmentOne']
        ]
        assert to_acct_sel.first_selected_option.get_attribute(
            'value'
        ) == 'None'
        to_acct_sel.select_by_value('2')
        notes = selenium.find_element_by_id('acct_txfr_frm_notes')
        notes.clear()
        notes.send_keys('Account Transfer Notes')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transactions 5 and 6' \
                                 ' in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-accounts-bank')
        # ensure that the page content updated after refreshing
        btable = selenium.find_element_by_id('table-accounts-bank')
        btexts = self.tbody2textlist(btable)
        assert btexts == [
            [
                'BankOne',
                '$12,789.01 (14 hours ago)',
                '$123.45',
                '$12,665.56'
            ],
            [
                'BankTwoStale',
                '$100.23 (18 days ago)',
                '-$456.78',
                '$557.01'
            ]
        ]
        itable = selenium.find_element_by_id('table-accounts-investment')
        itexts = self.tbody2textlist(itable)
        assert itexts == [
            [
                'InvestmentOne',
                '$10,362.91 (13 days ago)'
            ]
        ]

    def test_03_verify_db(self, testdb):
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 6
        desc = 'Account Transfer - 123.45 from BankOne (1) to BankTwoStale (2)'
        t2 = testdb.query(Transaction).get(5)
        assert t2.date == dtnow().date()
        assert t2.actual_amount == Decimal('123.45')
        assert t2.budgeted_amount == Decimal('123.45')
        assert t2.description == desc
        assert t2.notes == 'Account Transfer Notes'
        assert t2.account_id == 1
        assert t2.scheduled_trans_id is None
        assert len(t2.budget_transactions) == 1
        assert t2.budget_transactions[0].budget_id == 2
        assert t2.budget_transactions[0].amount == Decimal('123.45')
        t1 = testdb.query(Transaction).get(6)
        assert t1.date == dtnow().date()
        assert t1.actual_amount == Decimal('-123.45')
        assert t1.budgeted_amount == Decimal('-123.45')
        assert t1.description == desc
        assert t1.notes == 'Account Transfer Notes'
        assert t1.account_id == 2
        assert t1.scheduled_trans_id is None
        assert len(t1.budget_transactions) == 1
        assert t1.budget_transactions[0].budget_id == 2
        assert t1.budget_transactions[0].amount == Decimal('-123.45')
        acct1 = testdb.query(Account).get(1)
        assert acct1.balance.ledger == Decimal('12789.01')
        assert acct1.unreconciled_sum == Decimal('123.45')
        acct2 = testdb.query(Account).get(2)
        assert acct2.balance.ledger == Decimal('100.23')
        assert acct2.unreconciled_sum == Decimal('-456.78')
