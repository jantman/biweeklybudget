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
from datetime import datetime, timedelta
from pytz import UTC
from decimal import Decimal

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
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
        heading = selenium.find_element(By.CLASS_NAME, 'navbar-brand')
        assert heading.text == 'BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element(By.ID, 'side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_notifications(self, selenium):
        div = selenium.find_element(By.ID, 'notifications-row')
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
        table = selenium.find_element(By.XPATH,
                                      "//div[@id='panel-bank-accounts']//table"
                                      )
        assert self.thead2list(table) == [
            'Account', 'Balance', 'Unreconciled', 'Difference'
        ]
        assert self.tbody2textlist(table) == [
            ['BankOne', '$12,789.01 (14 hours ago)', '$0.00', '$12,789.01'],
            ['BankTwoStale', '$100.23 (a month ago)', '-$333.33', '$433.56']
        ]
        links = []
        tbody = table.find_element(By.TAG_NAME, 'tbody')
        for tr in tbody.find_elements(By.TAG_NAME, 'tr'):
            td = tr.find_elements(By.TAG_NAME, 'td')[0]
            links.append(td.get_attribute('innerHTML'))
        assert links == [
            '<a href="/accounts/1">BankOne</a>',
            '<a href="/accounts/2">BankTwoStale</a>',
        ]

    def test_bank_stale_span(self, selenium):
        tbody = selenium.find_element(By.XPATH,
                                      "//div[@id='panel-bank-accounts']//table/tbody"
                                      )
        rows = tbody.find_elements(By.TAG_NAME, 'tr')
        bankTwoStale_bal_td = rows[1].find_elements(By.TAG_NAME, 'td')[1]
        bal_span = bankTwoStale_bal_td.find_elements(By.TAG_NAME, 'span')[1]
        assert bal_span.text == '(a month ago)'
        assert bal_span.get_attribute('class') == 'data_age text-danger'

    def test_credit_table(self, selenium):
        table = selenium.find_element(By.XPATH,
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
        tbody = table.find_element(By.TAG_NAME, 'tbody')
        for tr in tbody.find_elements(By.TAG_NAME, 'tr'):
            td = tr.find_elements(By.TAG_NAME, 'td')[0]
            links.append(td.get_attribute('innerHTML'))
        assert links == [
            '<a href="/accounts/3">CreditOne</a>',
            '<a href="/accounts/4">CreditTwo</a>',
        ]

    def test_investment_table(self, selenium):
        table = selenium.find_element(By.XPATH,
                                      "//div[@id='panel-investment']//table"
                                      )
        assert self.thead2list(table) == ['Account', 'Value']
        assert self.tbody2textlist(table) == [
            ['InvestmentOne', '$10,362.91 (13 days ago)']
        ]
        links = []
        tbody = table.find_element(By.TAG_NAME, 'tbody')
        for tr in tbody.find_elements(By.TAG_NAME, 'tr'):
            td = tr.find_elements(By.TAG_NAME, 'td')[0]
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
        stable = selenium.find_element(By.ID, 'table-standing-budgets')
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
        table = selenium.find_element(By.ID, 'pay-period-table')
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
        tbody = table.find_element(By.TAG_NAME, 'tbody')
        trs = tbody.find_elements(By.TAG_NAME, 'tr')
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
        btable = selenium.find_element(By.ID, 'table-accounts-bank')
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
                '$100.23 (a month ago)',
                '-$333.33',
                '$433.56'
            ]
        ]
        itable = selenium.find_element(By.ID, 'table-accounts-investment')
        itexts = self.tbody2textlist(itable)
        assert itexts == [
            [
                'InvestmentOne',
                '$10,362.91 (13 days ago)'
            ]
        ]
        # open the modal to do a transfer
        link = selenium.find_element(By.ID, 'btn_acct_txfr_bank')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Account Transfer'
        assert body.find_element(By.ID,
                                 'acct_txfr_frm_date').get_attribute('value') == dtnow(
            ).strftime('%Y-%m-%d')
        amt = body.find_element(By.ID, 'acct_txfr_frm_amount')
        amt.clear()
        amt.send_keys('123.45')
        budget_sel = Select(
            body.find_element(By.ID, 'acct_txfr_frm_budget')
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
            body.find_element(By.ID, 'acct_txfr_frm_from_account')
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
            body.find_element(By.ID, 'acct_txfr_frm_to_account')
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
        notes = selenium.find_element(By.ID, 'acct_txfr_frm_notes')
        notes.clear()
        notes.send_keys('Account Transfer Notes')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transactions 5 and 6' \
                                 ' in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-accounts-bank')
        # ensure that the page content updated after refreshing
        btable = selenium.find_element(By.ID, 'table-accounts-bank')
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
                '$100.23 (a month ago)',
                '-$456.78',
                '$557.01'
            ]
        ]
        itable = selenium.find_element(By.ID, 'table-accounts-investment')
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


CHART_URL = '/ajax/chart-data/account-balances'


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestAcctBalanceChartData(AcceptanceHelper):
    """
    Tests for the ``days`` parameter added to the account balances chart
    endpoint for GitHub issue #279. These hit the endpoint directly; the chart
    UI that consumes it is covered by TestAcctBalanceChartRanges below.

    The acceptance test timestamp is 2017-07-28, and the sample data's balances
    run from 2017-06-27 to 2017-07-27, so the shipped 365-day default window
    covers all of it. That is deliberate: an installation with less history
    than the default window must be entirely unaffected by this feature
    (FR-013).
    """

    def test_response_shape_is_unchanged(self, base_url):
        r = requests.get(base_url + CHART_URL)
        assert r.status_code == 200
        data = r.json()
        # external scripts read this endpoint; the shape must not change
        assert sorted(data.keys()) == ['data', 'keys']
        assert data['keys'] == [
            'BankOne', 'BankTwoStale', 'CreditOne', 'CreditTwo',
            'DisabledBank', 'InvestmentOne'
        ]
        for row in data['data']:
            assert 'date' in row
            for k in data['keys']:
                assert k in row

    def test_dates_are_ascending_and_unique(self, base_url):
        dates = [
            x['date'] for x in requests.get(base_url + CHART_URL).json()['data']
        ]
        assert dates == sorted(dates)
        assert len(set(dates)) == len(dates)

    def test_default_window_covers_all_sample_data(self, base_url):
        # sample data is well inside the 365 day default, so nothing is cut
        dates = [
            x['date'] for x in requests.get(base_url + CHART_URL).json()['data']
        ]
        assert dates == [
            '2017-06-27', '2017-07-10', '2017-07-15', '2017-07-26',
            '2017-07-27'
        ]

    def test_days_zero_returns_all_history(self, base_url):
        default = requests.get(base_url + CHART_URL).json()
        allhist = requests.get(base_url + CHART_URL + '?days=0').json()
        assert allhist['data'] == default['data']

    def test_shorter_window_returns_fewer_dates(self, base_url):
        short = requests.get(base_url + CHART_URL + '?days=15').json()
        long_ = requests.get(base_url + CHART_URL + '?days=365').json()
        assert len(short['data']) < len(long_['data'])
        assert [x['date'] for x in short['data']] == [
            '2017-07-15', '2017-07-26', '2017-07-27'
        ]

    def test_window_always_ends_at_the_latest_balance(self, base_url):
        for days in ['', '?days=0', '?days=15', '?days=30', '?days=365']:
            data = requests.get(base_url + CHART_URL + days).json()['data']
            assert data[-1]['date'] == '2017-07-27', days

    @pytest.mark.parametrize('param', ['abc', '', '-1', '1.5', 'null'])
    def test_bad_days_falls_back_to_default(self, base_url, param):
        # FR-010: never a 4xx or a traceback where a chart should be
        r = requests.get(base_url + CHART_URL + '?days=' + param)
        assert r.status_code == 200
        assert r.json() == requests.get(base_url + CHART_URL).json()

    @pytest.mark.parametrize('param', ['999999', '99999999999', '36501'])
    def test_absurd_days_returns_all_history_not_a_500(self, base_url, param):
        """
        Regression guard for the OverflowError found in review of PR #331.

        A window start of ``now - timedelta(days=999999)`` falls below
        ``datetime.MINYEAR``, so the subtraction raised OverflowError and the
        endpoint answered a mistyped URL with an HTTP 500 rather than a chart.
        Such a window reaches back before every recorded balance, so all
        history is the honest answer as well as the safe one.
        """
        r = requests.get(base_url + CHART_URL + '?days=' + param)
        assert r.status_code == 200
        assert r.json() == requests.get(base_url + CHART_URL + '?days=0').json()

    def test_dormant_account_keeps_its_line(self, base_url):
        """
        The correctness guarantee that windowing most easily breaks (FR-011).

        BankTwoStale's only recorded balance is 2017-07-10, which is *before*
        the start of a 15 day window. Without the pre-window seed query it
        would have no value to carry forward and would be reported as null on
        every row -- which, on a chart of account balances, reads as the
        account having been emptied.
        """
        data = requests.get(base_url + CHART_URL + '?days=15').json()['data']
        assert [x['date'] for x in data] == [
            '2017-07-15', '2017-07-26', '2017-07-27'
        ]
        for row in data:
            assert row['BankTwoStale'] == 100.23, row['date']

    def test_account_with_no_prior_data_is_not_backfilled(self, base_url):
        """
        The inverse of the above: an account whose data begins part-way
        through the window must start where its data starts, not be
        back-filled onto dates when it had no recorded balance.
        """
        data = requests.get(base_url + CHART_URL + '?days=0').json()['data']
        assert data[0]['date'] == '2017-06-27'
        assert data[0]['BankOne'] is None
        assert data[3]['date'] == '2017-07-26'
        assert data[3]['BankOne'] == 12345.67


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestAcctBalanceChartLargeData(AcceptanceHelper):
    """
    The point cap is the whole reason this feature exists, and the sample data
    is far too small to exercise it: five balance dates against a cap of 300.
    These tests seed several years of synthetic daily balances so the bound is
    actually tested rather than merely asserted about data that could never
    reach it (SC-002, SC-003).

    ``class_refresh_db`` restores the database afterwards, so the seeded rows
    do not leak into any other test.
    """

    NUM_DAYS = 1100

    @pytest.fixture(autouse=True)
    def seed_balances(self, testdb):
        end = dtnow()
        for i in range(0, self.NUM_DAYS):
            d = end - timedelta(days=i)
            for acct_id in [1, 2, 3]:
                testdb.add(AccountBalance(
                    account_id=acct_id,
                    ledger=Decimal('1000.00') + Decimal(i),
                    ledger_date=d,
                    avail=Decimal('1000.00') + Decimal(i),
                    avail_date=d,
                    overall_date=d
                ))
        testdb.commit()

    def test_default_window_is_capped(self, base_url):
        data = requests.get(base_url + CHART_URL).json()['data']
        assert len(data) <= 300
        # and it really did have more than 300 dates to choose from
        assert len(data) > 100

    def test_all_history_is_capped(self, base_url):
        # days=0 is the one request whose date range is unbounded; the cap
        # must still hold, or the "zoom out" affordance is a trap
        data = requests.get(base_url + CHART_URL + '?days=0').json()['data']
        assert len(data) <= 300

    def test_capped_response_still_ends_at_the_present(self, base_url):
        expected = dtnow().strftime('%Y-%m-%d')
        for qs in ['', '?days=0', '?days=365']:
            data = requests.get(base_url + CHART_URL + qs).json()['data']
            assert data[-1]['date'] == expected, qs

    def test_capped_dates_stay_ascending_and_unique(self, base_url):
        dates = [
            x['date']
            for x in requests.get(base_url + CHART_URL + '?days=0').json()[
                'data'
            ]
        ]
        assert dates == sorted(dates)
        assert len(set(dates)) == len(dates)

    def test_point_count_does_not_grow_with_history(self, base_url, testdb):
        """
        SC-003: the volume of stored history must stop affecting how much the
        index page transfers and draws for its default view.
        """
        before = len(requests.get(base_url + CHART_URL).json()['data'])
        # add another two years of daily balances further into the past
        end = dtnow() - timedelta(days=self.NUM_DAYS)
        for i in range(0, 730):
            d = end - timedelta(days=i)
            testdb.add(AccountBalance(
                account_id=1, ledger=Decimal('5.00'), ledger_date=d,
                avail=Decimal('5.00'), avail_date=d, overall_date=d
            ))
        testdb.commit()
        after = len(requests.get(base_url + CHART_URL).json()['data'])
        assert after == before


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestAcctBalanceChartRanges(AcceptanceHelper):
    """
    Tests for the chart's date range selector, added for GitHub issue #279.
    """

    EXPECTED = [
        ('1m', '30'), ('3m', '90'), ('6m', '180'), ('1y', '365'),
        ('2y', '730'), ('5y', '1825'), ('All', '0')
    ]

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)

    def _buttons(self, selenium):
        return selenium.find_elements(
            By.CSS_SELECTOR, '#account-balance-chart-ranges button'
        )

    def test_range_buttons_present_in_order(self, selenium):
        btns = self._buttons(selenium)
        assert [
            (b.text, b.get_attribute('data-days')) for b in btns
        ] == self.EXPECTED

    def test_configured_default_is_the_active_button(self, selenium):
        # test_settings.py does not set ACCOUNT_BALANCE_CHART_DEFAULT_DAYS, so
        # the shipped default of 365 applies -- which is itself the check that
        # a settings module predating this feature keeps working untouched.
        active = [
            b for b in self._buttons(selenium) if 'active' in
            b.get_attribute('class').split()
        ]
        assert len(active) == 1
        assert active[0].text == '1y'

    def test_chart_renders_an_svg(self, selenium):
        chart = selenium.find_element(By.ID, 'account-balance-chart')
        assert len(chart.find_elements(By.TAG_NAME, 'svg')) == 1

    def test_nodata_message_is_hidden_when_there_is_data(self, selenium):
        nodata = selenium.find_element(
            By.ID, 'account-balance-chart-nodata'
        )
        assert nodata.is_displayed() is False

    def test_selecting_a_range_moves_active_and_redraws_in_place(
        self, selenium, base_url
    ):
        btns = {b.text: b for b in self._buttons(selenium)}
        btns['All'].click()
        self.wait_for_jquery_done(selenium)
        active = [
            b for b in self._buttons(selenium) if 'active' in
            b.get_attribute('class').split()
        ]
        assert len(active) == 1
        assert active[0].text == 'All'
        # no navigation: FR-008 requires an in-place redraw
        assert selenium.current_url.rstrip('/') == base_url.rstrip('/')
        # and the chart is still one chart, not a second drawn over the first
        chart = selenium.find_element(By.ID, 'account-balance-chart')
        assert len(chart.find_elements(By.TAG_NAME, 'svg')) == 1

    def test_narrowing_the_range_again(self, selenium):
        btns = {b.text: b for b in self._buttons(selenium)}
        btns['All'].click()
        self.wait_for_jquery_done(selenium)
        btns = {b.text: b for b in self._buttons(selenium)}
        btns['1m'].click()
        self.wait_for_jquery_done(selenium)
        active = [
            b for b in self._buttons(selenium) if 'active' in
            b.get_attribute('class').split()
        ]
        assert len(active) == 1
        assert active[0].text == '1m'
        chart = selenium.find_element(By.ID, 'account-balance-chart')
        assert len(chart.find_elements(By.TAG_NAME, 'svg')) == 1


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb')
class TestAcctBalanceChartSettings(AcceptanceHelper):
    """
    The two settings added for GitHub issue #279 must actually drive the
    endpoint, not merely exist beside constants baked into the code.

    These use the Flask test client rather than the live server, because the
    live server runs in a separate process where monkeypatching the settings
    module in this process would have no effect. The route, view and database
    are the real ones either way.
    """

    def _get(self, qs=''):
        from biweeklybudget.flaskapp.app import app
        with app.test_client() as c:
            return c.get(CHART_URL + qs).get_json()

    def test_max_points_is_read_from_settings(self, monkeypatch):
        from biweeklybudget.flaskapp.views import index as index_view
        assert len(self._get('?days=0')['data']) == 5
        monkeypatch.setattr(
            index_view.settings, 'ACCOUNT_BALANCE_CHART_MAX_POINTS', 3
        )
        data = self._get('?days=0')['data']
        assert len(data) == 3
        # the cap must never cost us the most recent balance
        assert data[-1]['date'] == '2017-07-27'

    def test_default_days_is_read_from_settings(self, monkeypatch):
        from biweeklybudget.flaskapp.views import index as index_view
        monkeypatch.setattr(
            index_view.settings, 'ACCOUNT_BALANCE_CHART_DEFAULT_DAYS', 15
        )
        # no days parameter: the configured default must be what applies
        assert [x['date'] for x in self._get()['data']] == [
            '2017-07-15', '2017-07-26', '2017-07-27'
        ]

    def test_default_days_of_zero_means_all_history(self, monkeypatch):
        from biweeklybudget.flaskapp.views import index as index_view
        monkeypatch.setattr(
            index_view.settings, 'ACCOUNT_BALANCE_CHART_DEFAULT_DAYS', 0
        )
        assert len(self._get()['data']) == 5

    def test_bad_days_falls_back_to_the_configured_default(self, monkeypatch):
        from biweeklybudget.flaskapp.views import index as index_view
        monkeypatch.setattr(
            index_view.settings, 'ACCOUNT_BALANCE_CHART_DEFAULT_DAYS', 15
        )
        assert self._get('?days=garbage') == self._get()
