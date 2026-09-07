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
from datetime import timedelta, date, datetime
from pytz import UTC
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from decimal import Decimal
import requests

from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.settings import PAY_PERIOD_START_DATE


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestTransactions(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')

    def test_heading(self, selenium):
        heading = selenium.find_element(By.CLASS_NAME, 'navbar-brand')
        assert heading.text == 'Transactions - BiweeklyBudget'

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
class TestTransactionsDefault(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.dt = dtnow()
        self.get(selenium, base_url + '/transactions')

    def test_table(self, selenium):
        table = selenium.find_element(By.ID, 'table-transactions')
        texts = self.tbody2textlist(table)
        elems = self.tbody2elemlist(table)
        assert texts == [
            [
                (self.dt + timedelta(days=4)).date().strftime('%Y-%m-%d'),
                '$111.13',
                'T1foo',
                'BankOne (1)',
                'Periodic1 (1)',
                'Yes (1)',
                '$111.11',
                '',
                'Yes (1)'
            ],
            [
                self.dt.date().strftime('%Y-%m-%d'),
                '-$333.33',
                'T2',
                'BankTwoStale (2)',
                'Standing1 (4)',
                'Yes (3)',
                '',
                '',
                ''
            ],
            [
                (self.dt - timedelta(days=2)).date().strftime('%Y-%m-%d'),
                '$222.22',
                'T3',
                'CreditOne (3)',
                'Periodic2 (2)',
                '',
                '',
                '$12.34',
                ''
            ],
            [
                (self.dt - timedelta(days=35)).date().strftime('%Y-%m-%d'),
                '$322.32',
                'T4split',
                'CreditOne (3)',
                'Periodic2 (2) ($222.22)\nPeriodic1 (1) ($100.10)',
                '',
                '',
                '$34.56',
                ''
            ]
        ]
        linkcols = [
            [
                c[2].get_attribute('innerHTML'),
                c[3].get_attribute('innerHTML'),
                c[4].get_attribute('innerHTML'),
                c[5].get_attribute('innerHTML'),
                c[8].get_attribute('innerHTML')
            ]
            for c in elems
        ]
        assert len(linkcols) == 4
        assert linkcols[0] == [
            '<a href="javascript:transModal(1, mytable)">T1foo</a>',
            '<a href="/accounts/1">BankOne (1)</a>',
            '<a href="/budgets/1">Periodic1 (1)</a>',
            '<a href="/scheduled/1">Yes (1)</a>',
            '<a href="javascript:txnReconcileModal(1)">Yes (1)</a>'
        ]
        assert linkcols[1] == [
            '<a href="javascript:transModal(2, mytable)">T2</a>',
            '<a href="/accounts/2">BankTwoStale (2)</a>',
            '<a href="/budgets/4">Standing1 (4)</a>',
            '<a href="/scheduled/3">Yes (3)</a>',
            '&nbsp;'
        ]
        assert linkcols[2] == [
            '<a href="javascript:transModal(3, mytable)">T3</a>',
            '<a href="/accounts/3">CreditOne (3)</a>',
            '<a href="/budgets/2">Periodic2 (2)</a>',
            '&nbsp;',
            '&nbsp;'
        ]
        assert linkcols[3] == [
            '<a href="javascript:transModal(4, mytable)">T4split</a>',
            '<a href="/accounts/3">CreditOne (3)</a>',
            '<a href="/budgets/2">Periodic2 (2) ($222.22)</a><br>'
            '<a href="/budgets/1">Periodic1 (1) ($100.10)</a>',
            '&nbsp;',
            '&nbsp;'
        ]

    def test_acct_filter_opts(self, selenium):
        self.get(selenium, self.baseurl + '/transactions')
        acct_filter = Select(selenium.find_element(By.ID, 'account_filter'))
        # find the options
        opts = []
        for o in acct_filter.options:
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

    def test_acct_filter(self, selenium):
        p1trans = [
            'T1foo',
            'T2',
            'T3',
            'T4split'
        ]
        self.get(selenium, self.baseurl + '/transactions')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-transactions')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[2] for t in texts]
        # check sanity
        assert trans == p1trans
        acct_filter = Select(selenium.find_element(By.ID, 'account_filter'))
        # select BankOne (1)
        acct_filter.select_by_value('1')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-transactions')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[2] for t in texts]
        assert trans == ['T1foo']
        # select back to all
        acct_filter.select_by_value('None')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-transactions')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[2] for t in texts]
        assert trans == p1trans

    def test_budg_filter_opts(self, selenium):
        self.get(selenium, self.baseurl + '/transactions')
        budg_filter = Select(selenium.find_element(By.ID, 'budget_filter'))
        # find the options
        opts = []
        for o in budg_filter.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['3', 'Periodic3 Inactive'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['6', 'Standing3 Inactive']
        ]

    def test_budg_filter(self, selenium):
        p1trans = [
            'T1foo',
            'T2',
            'T3',
            'T4split'
        ]
        self.get(selenium, self.baseurl + '/transactions')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-transactions')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[2] for t in texts]
        # check sanity
        assert trans == p1trans
        budg_filter = Select(selenium.find_element(By.ID, 'budget_filter'))
        # select Periodic2 (2)
        budg_filter.select_by_value('2')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-transactions')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[2] for t in texts]
        assert trans == ['T3', 'T4split']
        # select Standing1 (4)
        budg_filter.select_by_value('4')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-transactions')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[2] for t in texts]
        assert trans == ['T2']
        # select back to all
        budg_filter.select_by_value('None')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-transactions')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[2] for t in texts]
        assert trans == p1trans

    def test_search(self, selenium):
        self.get(selenium, self.baseurl + '/transactions')
        search = self.retry_stale(
            lambda: selenium.find_element(By.XPATH, '//input[@type="search"]')
        )
        search.send_keys('foo')
        self.wait_for_jquery_done(selenium)
        # Wait for DataTables search to filter results (has debounce delay)
        self.wait_for_datatable_rows(selenium, 'table-transactions', 1)
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-transactions')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[2] for t in texts]
        # check sanity
        assert trans == ['T1foo']


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestTransModalByURL(AcceptanceHelper):

    def test_0_verify_db(self, testdb):
        t = testdb.query(Transaction).get(3)
        assert t is not None
        assert t.description == 'T3'
        assert t.date == (dtnow() - timedelta(days=2)).date()
        assert t.actual_amount == Decimal('222.22')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 3
        assert t.scheduled_trans_id is None
        assert t.notes == 'notesT3'
        assert len(t.budget_transactions) == 1
        assert t.budget_transactions[0].budget_id == 2
        assert t.budget_transactions[0].amount == Decimal('222.22')
        assert t.sales_tax == Decimal('12.34')

    def test_1_modal(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions/3')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 3'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '3'
        assert body.find_element(By.ID,
                                 'trans_frm_date').get_attribute('value') == (
            dtnow() - timedelta(days=2)).date().strftime('%Y-%m-%d')
        assert body.find_element(By.ID,
                                 'trans_frm_amount').get_attribute('value') == '222.22'
        assert body.find_element(By.ID,
                                 'trans_frm_sales_tax').get_attribute('value') == '12.34'
        assert body.find_element(By.ID,
                                 'trans_frm_description').get_attribute('value') == 'T3'
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        opts = []
        for o in acct_sel.options:
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
        assert acct_sel.first_selected_option.get_attribute('value') == '3'
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '2'
        assert selenium.find_element(By.ID,
                                     'trans_frm_notes').get_attribute('value') == 'notesT3'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestTransModal(AcceptanceHelper):

    def test_00_simple_modal_verify_db(self, testdb):
        t = testdb.query(Transaction).get(2)
        assert t is not None
        assert t.description == 'T2'
        assert t.date == dtnow().date()
        assert t.actual_amount == Decimal('-333.33')
        assert t.budgeted_amount == Decimal('-333.33')
        assert t.planned_budget_id == 4
        assert t.account_id == 2
        assert t.scheduled_trans_id == 3
        assert t.notes == 'notesT2'
        assert t.sales_tax == Decimal('0.0')
        assert len(t.budget_transactions) == 1
        assert t.budget_transactions[0].budget_id == 4
        assert t.budget_transactions[0].amount == Decimal('-333.33')
        assert testdb.query(Budget).get(4).current_balance == Decimal('1284.23')
        assert testdb.query(Budget).get(5).current_balance == Decimal('9482.29')

    def test_01_simple_modal_modal_on_click(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="T2"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 2'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '2'
        assert body.find_element(By.ID,
                                 'trans_frm_date').get_attribute('value') == dtnow().date(
        ).strftime('%Y-%m-%d')
        assert body.find_element(By.ID,
                                 'trans_frm_amount').get_attribute('value') == '-333.33'
        assert body.find_element(By.ID,
                                 'trans_frm_sales_tax').get_attribute('value') == '0'
        assert body.find_element(By.ID,
                                 'trans_frm_description').get_attribute('value') == 'T2'
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        opts = []
        for o in acct_sel.options:
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
        assert acct_sel.first_selected_option.get_attribute('value') == '2'
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '4'
        assert selenium.find_element(By.ID,
                                     'trans_frm_notes').get_attribute('value') == 'notesT2'

    def test_02_simple_modal_modal_edit(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="T2"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 2'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '2'
        d = body.find_element(By.ID, 'trans_frm_date')
        d.clear()
        d.send_keys(
            (dtnow() - timedelta(days=3)).date().strftime('%Y-%m-%d')
        )
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys('-123.45')
        desc = body.find_element(By.ID, 'trans_frm_description')
        desc.send_keys('edited')
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        acct_sel.select_by_value('4')
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        budget_sel.select_by_value('5')
        notes = selenium.find_element(By.ID, 'trans_frm_notes')
        notes.send_keys('edited')
        tax = body.find_element(By.ID, 'trans_frm_sales_tax')
        tax.clear()
        tax.send_keys('45.67')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 2 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that updated budget was removed from the page
        table = selenium.find_element(By.ID, 'table-transactions')
        texts = [y[2] for y in self.tbody2textlist(table)]
        assert 'T2edited' in texts

    def test_03_simple_modal_verify_db(self, testdb):
        t = testdb.query(Transaction).get(2)
        assert t is not None
        assert t.description == 'T2edited'
        assert t.date == (dtnow() - timedelta(days=3)).date()
        assert t.actual_amount == Decimal('-123.45')
        assert t.budgeted_amount == Decimal('-333.33')
        assert t.account_id == 4
        assert t.planned_budget_id == 4
        assert t.scheduled_trans_id == 3
        assert t.notes == 'notesT2edited'
        assert t.sales_tax == Decimal('45.67')
        assert len(t.budget_transactions) == 1
        assert t.budget_transactions[0].budget_id == 5
        assert t.budget_transactions[0].amount == Decimal('-123.45')
        assert testdb.query(Budget).get(4).current_balance == Decimal('950.90')
        assert testdb.query(Budget).get(5).current_balance == Decimal('9605.74')

    def test_10_cant_edit_reconciled_verify_db(self, testdb):
        t = testdb.query(Transaction).get(1)
        assert t is not None
        assert t.description == 'T1foo'
        assert t.date == (dtnow() + timedelta(days=4)).date()
        assert t.actual_amount == Decimal('111.13')
        assert t.budgeted_amount == Decimal('111.11')
        assert t.account_id == 1
        assert t.planned_budget_id == 1
        assert t.scheduled_trans_id == 1
        assert t.notes == 'notesT1'
        assert len(t.budget_transactions) == 1
        assert t.budget_transactions[0].budget_id == 1
        assert t.budget_transactions[0].amount == Decimal('111.13')

    def test_11_cant_edit_reconciled_modal_on_click(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="T1foo"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 1'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '1'
        assert body.find_element(By.ID,
                                 'trans_frm_date').get_attribute('value') == (
            dtnow() + timedelta(days=4)).date().strftime('%Y-%m-%d')
        assert body.find_element(By.ID,
                                 'trans_frm_amount').get_attribute('value') == '111.13'
        assert body.find_element(By.ID,
                                 'trans_frm_description').get_attribute('value') == 'T1foo'
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        opts = []
        for o in acct_sel.options:
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
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '1'
        assert selenium.find_element(By.ID,
                                     'trans_frm_notes').get_attribute('value') == 'notesT1'

    def test_12_cant_edit_reconciled_modal_edit(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="T1foo"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 1'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '1'
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-danger' in x.get_attribute('class')
        assert x.text.strip() == 'Server Error: Transaction 1 is already ' \
                                 'reconciled; cannot be edited.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)

    def test_22_modal_add(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.ID, 'btn_add_trans')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Transaction'
        date_input = body.find_element(By.ID, 'trans_frm_date')
        # BEGIN select the 15th of this month from the popup
        dnow = dtnow()
        expected_date = date(year=dnow.year, month=dnow.month, day=15)
        date_input.click()
        date_number = body.find_element(By.XPATH,
                                        '//td[@class="day" and text()="15"]'
                                        )
        date_number.click()
        assert date_input.get_attribute(
            'value') == expected_date.strftime('%Y-%m-%d')
        # END date chooser popup
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys('123.45')
        desc = body.find_element(By.ID, 'trans_frm_description')
        desc.send_keys('NewTrans5')
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        acct_sel.select_by_value('1')
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        budget_sel.select_by_value('2')
        notes = selenium.find_element(By.ID, 'trans_frm_notes')
        notes.send_keys('NewTransNotes')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 5 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that new trans was added to the table
        table = selenium.find_element(By.ID, 'table-transactions')
        texts = [y[2] for y in self.tbody2textlist(table)]
        assert 'NewTrans5' in texts

    def test_23_modal_add_verify_db(self, testdb):
        t = testdb.query(Transaction).get(5)
        assert t is not None
        assert t.description == 'NewTrans5'
        dnow = dtnow()
        assert t.date == date(year=dnow.year, month=dnow.month, day=15)
        assert t.actual_amount == Decimal('123.45')
        assert t.budgeted_amount is None
        assert t.account_id == 1
        assert t.planned_budget_id is None
        assert t.scheduled_trans_id is None
        assert t.notes == 'NewTransNotes'
        assert t.sales_tax == Decimal('0.0')
        assert len(t.budget_transactions) == 1
        assert t.budget_transactions[0].budget_id == 2
        assert t.budget_transactions[0].amount == Decimal('123.45')

    def test_31_verify_index_budgets_table(self, base_url, selenium):
        self.get(selenium, base_url + '/')
        stable = selenium.find_element(By.ID, 'table-standing-budgets')
        stexts = self.tbody2textlist(stable)
        assert stexts == [
            ['Standing1 (4)', '$950.90'],
            ['Standing2 (5)', '$9,605.74']
        ]

    def test_32_modal_add(self, base_url, selenium):
        """Test that updating a transaction against a standing budget actually
            updates the balance on the standing budget."""
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.ID, 'btn_add_trans')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Transaction'
        date_input = body.find_element(By.ID, 'trans_frm_date')
        assert date_input.get_attribute(
            'value') == dtnow().strftime('%Y-%m-%d')
        # END date chooser popup
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys('345.67')
        desc = body.find_element(By.ID, 'trans_frm_description')
        desc.send_keys('NewTrans6')
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        acct_sel.select_by_value('1')
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        budget_sel.select_by_value('5')
        notes = selenium.find_element(By.ID, 'trans_frm_notes')
        notes.send_keys('NewTransNotes')
        tax = selenium.find_element(By.ID, 'trans_frm_sales_tax')
        tax.send_keys('67.89')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 6 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that new trans was added to the table
        table = selenium.find_element(By.ID, 'table-transactions')
        texts = [y[2] for y in self.tbody2textlist(table)]
        assert 'NewTrans6' in texts

    def test_33_verify_db(self, testdb):
        t = testdb.query(Transaction).get(6)
        assert t is not None
        assert t.description == 'NewTrans6'
        assert t.date == dtnow().date()
        assert t.actual_amount == Decimal('345.67')
        assert t.budgeted_amount is None
        assert t.account_id == 1
        assert t.planned_budget_id is None
        assert t.scheduled_trans_id is None
        assert t.notes == 'NewTransNotes'
        assert t.sales_tax == Decimal('67.89')
        assert len(t.budget_transactions) == 1
        assert t.budget_transactions[0].budget_id == 5
        assert t.budget_transactions[0].amount == Decimal('345.67')

    def test_34_verify_index_budgets_table(self, base_url, selenium):
        self.get(selenium, base_url + '/')
        stable = selenium.find_element(By.ID, 'table-standing-budgets')
        stexts = self.tbody2textlist(stable)
        assert stexts == [
            ['Standing1 (4)', '$950.90'],
            ['Standing2 (5)', '$9,260.07']
        ]

    def test_40_simple_modal_verify_db(self, testdb):
        assert testdb.query(Budget).get(4).current_balance == Decimal('950.90')
        assert testdb.query(Budget).get(5).current_balance == Decimal('9260.07')

    def test_41_modal_edit_change_between_standing(self, base_url, selenium):
        """
        test moving a transaction from one standing budget to another.
        this is as much a test of biweeklybudget.db_event_handlers as the
        transactions view.
        """
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="NewTrans6"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 6'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '6'
        amt = body.find_element(By.ID, 'trans_frm_amount')
        assert amt.get_attribute('value') == '345.67'
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        assert budget_sel.first_selected_option.get_attribute('value') == '5'
        budget_sel.select_by_value('4')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 6 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()

    def test_42_simple_modal_verify_db(self, testdb):
        t = testdb.query(Transaction).get(6)
        assert t is not None
        assert t.description == 'NewTrans6'
        assert t.date == dtnow().date()
        assert t.actual_amount == Decimal('345.67')
        assert t.budgeted_amount is None
        assert t.account_id == 1
        assert t.planned_budget_id is None
        assert t.scheduled_trans_id is None
        assert t.notes == 'NewTransNotes'
        assert len(t.budget_transactions) == 1
        assert t.budget_transactions[0].budget_id == 4
        assert t.budget_transactions[0].amount == Decimal('345.67')
        assert testdb.query(Budget).get(4).current_balance == Decimal('605.23')
        assert testdb.query(Budget).get(5).current_balance == Decimal('9605.74')


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestTransModalDoesNotShowInactiveBudgets(AcceptanceHelper):

    def test_00_add_transactions(self, testdb):
        # Transaction 5 - split with active and inactive
        testdb.add(Transaction(
            account_id=1,
            budget_amounts={
                testdb.query(Budget).get(1): Decimal('100.10'),
                testdb.query(Budget).get(2): Decimal('102.11'),
                testdb.query(Budget).get(3): Decimal('120.11')
            },
            date=dtnow().date(),
            description='InactiveBudgets1',
            notes='InactiveBudgets Txn1'
        ))
        # Transaction 6 - Active only
        testdb.add(Transaction(
            account_id=1,
            budget_amounts={
                testdb.query(Budget).get(1): Decimal('322.32')
            },
            date=dtnow().date(),
            description='InactiveBudgets2',
            notes='InactiveBudgets Txn2'
        ))
        # Transaction 7 - Inactive only
        testdb.add(Transaction(
            account_id=1,
            budget_amounts={
                testdb.query(Budget).get(3): Decimal('322.32')
            },
            date=dtnow().date(),
            description='InactiveBudgets3',
            notes='InactiveBudgets Txn3'
        ))
        testdb.commit()

    def test_01_verify_db(self, testdb):
        # Transaction 5 - split with active and inactive
        t = testdb.query(Transaction).get(5)
        assert t is not None
        assert t.description == 'InactiveBudgets1'
        assert t.date == dtnow().date()
        assert t.actual_amount == Decimal('322.32')
        assert t.account_id == 1
        assert t.notes == 'InactiveBudgets Txn1'
        assert len(t.budget_transactions) == 3
        assert {x.budget_id: x.amount for x in t.budget_transactions} == {
            1: Decimal('100.10'),
            2: Decimal('102.11'),
            3: Decimal('120.11')
        }
        # Transaction 6 - Active only
        t = testdb.query(Transaction).get(6)
        assert t is not None
        assert t.description == 'InactiveBudgets2'
        assert t.date == dtnow().date()
        assert t.actual_amount == Decimal('322.32')
        assert t.account_id == 1
        assert t.notes == 'InactiveBudgets Txn2'
        assert len(t.budget_transactions) == 1
        assert {x.budget_id: x.amount for x in t.budget_transactions} == {
            1: Decimal('322.32')
        }
        # Transaction 7 - Inactive only
        t = testdb.query(Transaction).get(7)
        assert t is not None
        assert t.description == 'InactiveBudgets3'
        assert t.date == dtnow().date()
        assert t.actual_amount == Decimal('322.32')
        assert t.account_id == 1
        assert t.notes == 'InactiveBudgets Txn3'
        assert len(t.budget_transactions) == 1
        assert {x.budget_id: x.amount for x in t.budget_transactions} == {
            3: Decimal('322.32')
        }

    def test_02_modal_populate_split(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="InactiveBudgets1"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 5'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '5'
        # assert budget split items are shown and checkbox is checked
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed()
        # there should be three split budget input groups
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 3
        # BUDGET 0
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget_0'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['3', 'Periodic3 Inactive']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '3'
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_0').get_attribute('value') == '120.11'
        # BUDGET 1
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget_1'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '2'
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_1').get_attribute('value') == '102.11'
        # BUDGET 2
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget_2'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '1'
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_2').get_attribute('value') == '100.1'

    def test_03_modal_populate_nonsplit_active(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="InactiveBudgets2"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 6'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '6'
        # NOT Split Budget
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed() is False
        amt = body.find_element(By.ID, 'trans_frm_amount')
        assert amt.get_attribute('value') == '322.32'
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        assert budget_sel.first_selected_option.get_attribute('value') == '1'
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]

    def test_04_modal_populate_nonsplit_inactive(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="InactiveBudgets3"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 7'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '7'
        # NOT Split Budget
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed() is False
        amt = body.find_element(By.ID, 'trans_frm_amount')
        assert amt.get_attribute('value') == '322.32'
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        assert budget_sel.first_selected_option.get_attribute('value') == '3'
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['3', 'Periodic3 Inactive']
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
@pytest.mark.incremental
class TestTransReconciledModal(AcceptanceHelper):

    def test_0_verify_db(self, testdb):
        t = testdb.query(TxnReconcile).get(1)
        assert t.ofx_account_id == 1
        assert t.ofx_fitid == 'BankOne.0.1'
        assert t.txn_id == 1
        assert t.rule_id is None
        assert t.note == 'reconcile notes'
        assert t.reconciled_at == datetime(2017, 4, 10, 8, 9, 11, tzinfo=UTC)

    def test_1_modal(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH,
                                     '//a[@href="javascript:txnReconcileModal(1)"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Transaction Reconcile 1'
        dl = body.find_element(By.TAG_NAME, 'dl')
        assert dl.get_attribute('innerHTML') == '\n' \
            '<dt>Date Reconciled</dt><dd>2017-04-10 08:09:11 UTC</dd>\n' \
            '<dt>Note</dt><dd>reconcile notes</dd>\n' \
            '<dt>Rule</dt><dd>null</dd>\n'
        trans_tbl = body.find_element(By.ID, 'txnReconcileModal-trans')
        trans_texts = self.tbody2textlist(trans_tbl)
        assert trans_texts == [
            ['Transaction'],
            [
                'Date',
                (dtnow() + timedelta(days=4)).strftime('%Y-%m-%d')
            ],
            ['Amount', '$111.13'],
            ['Budgeted Amount', '$111.11'],
            ['Description', 'T1foo'],
            ['Account', 'BankOne (1)'],
            ['Budget', 'Periodic1 (1)'],
            ['Notes', 'notesT1'],
            ['Scheduled?', 'Yes (1)']
        ]
        trans_elems = self.tbody2elemlist(trans_tbl)
        assert trans_elems[5][1].get_attribute('innerHTML') == '<a href=' \
            '"/accounts/1">BankOne (1)</a>'
        assert trans_elems[6][1].get_attribute('innerHTML') == '<a href=' \
            '"/budgets/1">Periodic1 (1)</a>'
        assert trans_elems[8][1].get_attribute('innerHTML') == '<a href=' \
            '"/scheduled/1">Yes (1)</a>'
        ofx_tbl = body.find_element(By.ID, 'txnReconcileModal-ofx')
        ofx_texts = self.tbody2textlist(ofx_tbl)
        assert ofx_texts == [
            ['OFX Transaction'],
            ['Account', 'BankOne (1)'],
            ['FITID', 'BankOne.0.1'],
            ['Date Posted', (dtnow() - timedelta(days=6)).strftime('%Y-%m-%d')],
            ['Amount', '-$20.00'],
            ['Name', 'Late Fee'],
            ['Memo', ''],
            ['Type', 'Debit'],
            ['Description', ''],
            ['Notes', ''],
            ['Checknum', ''],
            ['MCC', ''],
            ['SIC', ''],
            ['OFX Statement'],
            ['ID', '1'],
            ['Date', (dtnow() - timedelta(hours=46)).strftime('%Y-%m-%d')],
            ['Filename', '/stmt/BankOne/0'],
            [
                'File mtime',
                (dtnow() - timedelta(hours=46)).strftime('%Y-%m-%d')
            ],
            ['Ledger Balance', '$12,345.67']
        ]
        ofx_elems = self.tbody2elemlist(ofx_tbl)
        assert ofx_elems[1][1].get_attribute('innerHTML') == '<a href=' \
            '"/accounts/1">BankOne (1)</a>'

    def test_2_split_trans(self, testdb):
        b1 = testdb.query(Budget).get(1)  # Periodic1
        b2 = testdb.query(Budget).get(2)  # Periodic2
        t = testdb.query(Transaction).get(1)
        t.set_budget_amounts({
            b1: Decimal('110.02'),
            b2: Decimal('1.11')
        })
        testdb.commit()

    def test_3_split_trans_modal(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH,
                                     '//a[@href="javascript:txnReconcileModal(1)"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Transaction Reconcile 1'
        dl = body.find_element(By.TAG_NAME, 'dl')
        assert dl.get_attribute('innerHTML') == '\n' \
            '<dt>Date Reconciled</dt><dd>2017-04-10 08:09:11 UTC</dd>\n' \
            '<dt>Note</dt><dd>reconcile notes</dd>\n' \
            '<dt>Rule</dt><dd>null</dd>\n'
        trans_tbl = body.find_element(By.ID, 'txnReconcileModal-trans')
        trans_texts = self.tbody2textlist(trans_tbl)
        assert trans_texts == [
            ['Transaction'],
            [
                'Date',
                (dtnow() + timedelta(days=4)).strftime('%Y-%m-%d')
            ],
            ['Amount', '$111.13'],
            ['Budgeted Amount', '$111.11'],
            ['Description', 'T1foo'],
            ['Account', 'BankOne (1)'],
            ['Budget', 'Periodic1 (1) ($110.02)\nPeriodic2 (2) ($1.11)'],
            ['Notes', 'notesT1'],
            ['Scheduled?', 'Yes (1)']
        ]
        trans_elems = self.tbody2elemlist(trans_tbl)
        assert trans_elems[5][1].get_attribute('innerHTML') == '<a href=' \
            '"/accounts/1">BankOne (1)</a>'
        assert trans_elems[6][1].get_attribute('innerHTML') == '<a href=' \
            '"/budgets/1">Periodic1 (1) ($110.02)</a><br><a href=' \
            '"/budgets/2">Periodic2 (2) ($1.11)</a>'
        assert trans_elems[8][1].get_attribute('innerHTML') == '<a href=' \
            '"/scheduled/1">Yes (1)</a>'
        ofx_tbl = body.find_element(By.ID, 'txnReconcileModal-ofx')
        ofx_texts = self.tbody2textlist(ofx_tbl)
        assert ofx_texts == [
            ['OFX Transaction'],
            ['Account', 'BankOne (1)'],
            ['FITID', 'BankOne.0.1'],
            ['Date Posted', (dtnow() - timedelta(days=6)).strftime('%Y-%m-%d')],
            ['Amount', '-$20.00'],
            ['Name', 'Late Fee'],
            ['Memo', ''],
            ['Type', 'Debit'],
            ['Description', ''],
            ['Notes', ''],
            ['Checknum', ''],
            ['MCC', ''],
            ['SIC', ''],
            ['OFX Statement'],
            ['ID', '1'],
            ['Date', (dtnow() - timedelta(hours=46)).strftime('%Y-%m-%d')],
            ['Filename', '/stmt/BankOne/0'],
            [
                'File mtime',
                (dtnow() - timedelta(hours=46)).strftime('%Y-%m-%d')
            ],
            ['Ledger Balance', '$12,345.67']
        ]
        ofx_elems = self.tbody2elemlist(ofx_tbl)
        assert ofx_elems[1][1].get_attribute('innerHTML') == '<a href=' \
            '"/accounts/1">BankOne (1)</a>'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestTransModalBudgetSplits(AcceptanceHelper):

    def test_01_verify_db(self, testdb):
        t = testdb.query(Transaction).get(4)
        assert t is not None
        assert t.description == 'T4split'
        assert t.date == (dtnow() - timedelta(days=35)).date()
        assert t.actual_amount == Decimal('322.32')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 3
        assert t.scheduled_trans_id is None
        assert t.notes == 'notesT4split'
        assert t.sales_tax == Decimal('34.56')
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            1: Decimal('100.10'),
            2: Decimal('222.22')
        }

    def test_02_resave_transaction(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'id': '4',
                'date': (dtnow() - timedelta(days=35)).strftime('%Y-%m-%d'),
                'amount': '322.32',
                'description': 'T4split',
                'notes': 'notesT4split',
                'account': '3',
                'budgets': {
                    '2': '222.22',
                    '1': '100.10'
                },
                'sales_tax': '34.56'
            }
        )
        assert res.status_code == 200
        assert res.json() == {
            'success': True,
            'success_message': 'Successfully saved Transaction 4  in database.',
            'trans_id': 4
        }

    def test_03_verify_db(self, testdb):
        t = testdb.query(Transaction).get(4)
        assert t is not None
        assert t.description == 'T4split'
        assert t.date == (dtnow() - timedelta(days=35)).date()
        assert t.actual_amount == Decimal('322.32')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 3
        assert t.scheduled_trans_id is None
        assert t.notes == 'notesT4split'
        assert t.sales_tax == Decimal('34.56')
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            1: Decimal('100.10'),
            2: Decimal('222.22')
        }

    def test_10_backend_validation_amounts(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'id': '4',
                'date': (dtnow() - timedelta(days=35)).strftime('%Y-%m-%d'),
                'amount': '322.32',
                'description': 'T4split',
                'notes': 'notesT4split',
                'account': '3',
                'budgets': {
                    '2': '422.32'
                },
                'sales_tax': '34.56'
            }
        )
        assert res.status_code == 200
        assert res.json() == {
            'success': False,
            'errors': {
                'account': [],
                'amount': [],
                'budgets': [
                    'Sum of all budget amounts (422.32) must equal '
                    'Transaction amount (322.32).'
                ],
                'date': [],
                'description': [],
                'id': [],
                'notes': [],
                'sales_tax': []
            }
        }

    def test_11_backend_validation_amounts(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'id': '4',
                'date': (dtnow() - timedelta(days=35)).strftime('%Y-%m-%d'),
                'amount': '322.32',
                'description': 'T4split',
                'notes': 'notesT4split',
                'account': '3',
                'budgets': {
                    '1': '222.32',
                    '2': '200.12'
                },
                'sales_tax': '34.56'
            }
        )
        assert res.status_code == 200
        assert res.json() == {
            'success': False,
            'errors': {
                'account': [],
                'amount': [],
                'budgets': [
                    'Sum of all budget amounts (422.44) must equal '
                    'Transaction amount (322.32).'
                ],
                'date': [],
                'description': [],
                'id': [],
                'notes': [],
                'sales_tax': []
            }
        }

    def test_12_backend_validation_no_budgets(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'id': '4',
                'date': (dtnow() - timedelta(days=35)).strftime('%Y-%m-%d'),
                'amount': '322.32',
                'description': 'T4split',
                'notes': 'notesT4split',
                'account': '3',
                'budgets': {},
                'sales_tax': '34.56'
            }
        )
        assert res.status_code == 200
        assert res.json() == {
            'success': False,
            'errors': {
                'account': [],
                'amount': [],
                'budgets': [
                    'Transactions must have a budget.'
                ],
                'date': [],
                'description': [],
                'id': [],
                'notes': [],
                'sales_tax': []
            }
        }

    def test_13_backend_validation_invalid_budget_id(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': (dtnow() - timedelta(days=35)).strftime('%Y-%m-%d'),
                'amount': '322.32',
                'description': 'T4split',
                'notes': 'notesT4split',
                'account': '3',
                'budgets': {'99': '322.32'},
                'sales_tax': '34.56'
            }
        )
        assert res.status_code == 200
        assert res.json() == {
            'success': False,
            'errors': {
                'account': [],
                'amount': [],
                'budgets': [
                    'Budget "99" is invalid.'
                ],
                'date': [],
                'description': [],
                'notes': [],
                'sales_tax': []
            }
        }

    def test_14_backend_validation_inactive_budget(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': (dtnow() - timedelta(days=35)).strftime('%Y-%m-%d'),
                'amount': '322.32',
                'description': 'T4split',
                'notes': 'notesT4split',
                'account': '3',
                'budgets': {'3': '322.32'},
                'sales_tax': '34.56'
            }
        )
        assert res.status_code == 200
        assert res.json() == {
            'success': False,
            'errors': {
                'account': [],
                'amount': [],
                'budgets': [
                    'New transactions cannot use an inactive budget '
                    '(Periodic3 Inactive).'
                ],
                'date': [],
                'description': [],
                'notes': [],
                'sales_tax': []
            }
        }

    def validation_count_increased(self, driver, previous):
        c = driver.execute_script('return validation_count;')
        return c > previous

    def assert_budget_split_has_error(self, driver, msg):
        # get validate count
        c = driver.execute_script('return validation_count;')
        # change focus
        driver.find_element(By.ID, 'trans_frm_description').click()
        # wait for validate count to increase
        try:
            WebDriverWait(driver, 5).until(
                lambda x: self.validation_count_increased(driver, c)
            )
        except TimeoutException:
            pass
        assert driver.find_element(By.ID, 'budget-split-feedback').text == msg
        assert driver.find_element(By.ID,
                                   'modalSaveButton').is_enabled() is False

    def assert_budget_split_does_not_have_error(self, driver):
        # get validate count
        c = driver.execute_script('return validation_count;')
        # change focus
        driver.find_element(By.ID, 'trans_frm_description').click()
        # wait for validate count to increase
        try:
            WebDriverWait(driver, 5).until(
                lambda x: self.validation_count_increased(driver, c)
            )
        except TimeoutException:
            pass
        assert driver.find_element(By.ID, 'budget-split-feedback').text == ''
        assert driver.find_element(By.ID, 'modalSaveButton').is_enabled()

    def test_20_modal_frontend_validation(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.ID, 'btn_add_trans')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Transaction'
        # set an amount
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys('200.22')
        # assert budget split items are hidden and checkbox is unchecked
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed()
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed() is False
        # check the budget split checkbox
        selenium.find_element(By.ID, 'trans_frm_is_split').click()
        # assert budget split items are shown and checkbox is checked
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed()
        # there should be two split budget input groups
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 2
        self.assert_budget_split_does_not_have_error(selenium)
        # Select 2 different budgets and valid amounts
        Select(
            body.find_element(By.ID, 'trans_frm_budget_0')).select_by_value('1')
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_0')
        tmp.clear()
        tmp.send_keys('100')
        Select(
            body.find_element(By.ID, 'trans_frm_budget_1')).select_by_value('2')
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_1')
        tmp.clear()
        tmp.send_keys('100.22')
        self.assert_budget_split_does_not_have_error(selenium)
        # change one amount
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_1')
        tmp.clear()
        tmp.send_keys('100.00')
        self.assert_budget_split_has_error(
            selenium,
            'Error: Sum of budget allocations (200.0000) must equal '
            'transaction amount (200.2200).'
        )
        # fix the amount
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_1')
        tmp.clear()
        tmp.send_keys('100.22')
        self.assert_budget_split_does_not_have_error(selenium)
        # change one budget to the same as the other
        Select(
            body.find_element(By.ID, 'trans_frm_budget_1')).select_by_value('1')
        self.assert_budget_split_has_error(
            selenium,
            'Error: A given budget may only be specified once.'
        )
        # fix the budget
        Select(
            body.find_element(By.ID, 'trans_frm_budget_1')).select_by_value('2')
        self.assert_budget_split_does_not_have_error(selenium)
        # click "Add Budget" link
        self.try_click(
            selenium, selenium.find_element(By.ID, 'trans_frm_add_budget_link')
        )
        # there should be three split budget input groups
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 3
        # decrease an amount in one of the previous groups
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_1')
        tmp.clear()
        tmp.send_keys('50.11')
        self.assert_budget_split_has_error(
            selenium,
            'Error: Sum of budget allocations (150.1100) must equal '
            'transaction amount (200.2200).'
        )
        # add difference to amount in the third budget group
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_2')
        tmp.clear()
        tmp.send_keys('50.11')
        self.assert_budget_split_does_not_have_error(selenium)
        # select budget in third group, same as second
        Select(
            body.find_element(By.ID, 'trans_frm_budget_2')).select_by_value('2')
        self.assert_budget_split_has_error(
            selenium,
            'Error: A given budget may only be specified once.'
        )
        # change budget in third group to a unique one
        Select(
            body.find_element(By.ID, 'trans_frm_budget_2')).select_by_value('4')
        self.assert_budget_split_does_not_have_error(selenium)
        # uncheck the Budget Split checkbox
        selenium.find_element(By.ID, 'trans_frm_is_split').click()
        # assert budget split items are hidden and checkbox is unchecked
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed()
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed() is False

    def test_30_verify_db_before(self, testdb):
        t = testdb.query(Transaction).get(4)
        assert t is not None
        assert t.description == 'T4split'
        assert t.date == (dtnow() - timedelta(days=35)).date()
        assert t.actual_amount == Decimal('322.32')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 3
        assert t.scheduled_trans_id is None
        assert t.notes == 'notesT4split'
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            1: Decimal('100.10'),
            2: Decimal('222.22')
        }
        assert max([
            tx.id for tx in testdb.query(Transaction).all()
        ]) == 4

    def test_31_split_2_modal_populate(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="T4split"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 4'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '4'
        assert body.find_element(By.ID,
                                 'trans_frm_date').get_attribute('value') == (
                dtnow() - timedelta(days=35)
            ).strftime('%Y-%m-%d')
        assert body.find_element(By.ID,
                                 'trans_frm_amount').get_attribute('value') == '322.32'
        assert body.find_element(By.ID,
                                 'trans_frm_description').get_attribute('value') == 'T4split'
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        opts = []
        for o in acct_sel.options:
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
        assert acct_sel.first_selected_option.get_attribute('value') == '3'
        # Split Budget
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed()
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 2
        # BUDGET 0
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget_0'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '2'
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_0').get_attribute('value') == '222.22'
        # BUDGET 1
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget_1'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '1'
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_1').get_attribute('value') == '100.1'
        assert selenium.find_element(By.ID,
                                     'trans_frm_notes').get_attribute('value') == 'notesT4split'

    def test_32_new_split_trans(self, base_url, selenium, testdb):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.ID, 'btn_add_trans')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Transaction'
        date_input = body.find_element(By.ID, 'trans_frm_date')
        assert date_input.get_attribute(
            'value') == dtnow().strftime('%Y-%m-%d')
        # END date chooser popup
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys('375.00')
        desc = body.find_element(By.ID, 'trans_frm_description')
        desc.send_keys('NewTrans5')
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        acct_sel.select_by_value('1')
        # check the budget split checkbox
        selenium.find_element(By.ID, 'trans_frm_is_split').click()
        # assert budget split items are shown and checkbox is checked
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed()
        # there should be two split budget input groups
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 2
        # set the budgets and amounts
        Select(
            body.find_element(By.ID, 'trans_frm_budget_0')).select_by_value('1')
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_0')
        tmp.clear()
        tmp.send_keys('100.00')
        Select(
            body.find_element(By.ID, 'trans_frm_budget_1')).select_by_value('2')
        # the next value should be populated automatically
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_1').get_attribute('value') == '275.00'
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_1')
        tmp.clear()
        tmp.send_keys('200')
        # change focus
        body.find_element(By.ID, 'trans_frm_budget_amount_0').send_keys('')
        # add a row
        self.try_click(
            selenium, selenium.find_element(By.ID, 'trans_frm_add_budget_link')
        )
        # there should be three split budget input groups
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 3
        # the amount should be populated automatically
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_2').get_attribute('value') == '75.00'
        # fill in the third row
        Select(
            body.find_element(By.ID, 'trans_frm_budget_2')).select_by_value('4')
        self.assert_budget_split_does_not_have_error(selenium)
        notes = selenium.find_element(By.ID, 'trans_frm_notes')
        notes.send_keys('NewSplitTransNotes')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 5 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that new trans was added to the table
        table = selenium.find_element(By.ID, 'table-transactions')
        texts = [y[2] for y in self.tbody2textlist(table)]
        assert 'NewTrans5' in texts
        t = testdb.query(Transaction).get(5)
        assert t is not None
        assert t.description == 'NewTrans5'
        assert t.date == dtnow().date()
        assert t.actual_amount == Decimal('375')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 1
        assert t.scheduled_trans_id is None
        assert t.notes == 'NewSplitTransNotes'
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            1: Decimal('100'),
            2: Decimal('200'),
            4: Decimal('75')
        }
        assert max([
            tx.id for tx in testdb.query(Transaction).all()
        ]) == 5

    def test_33_change_split_trans(self, base_url, selenium, testdb):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="NewTrans5"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 5'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '5'
        assert body.find_element(By.ID,
                                 'trans_frm_date'
                                 ).get_attribute('value') == dtnow().strftime('%Y-%m-%d')
        assert body.find_element(By.ID,
                                 'trans_frm_amount').get_attribute('value') == '375'
        assert body.find_element(By.ID,
                                 'trans_frm_description').get_attribute('value') == 'NewTrans5'
        acct_sel = Select(body.find_element(By.ID, 'trans_frm_account'))
        opts = []
        for o in acct_sel.options:
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
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        # Split Budget
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed()
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 3
        # BUDGET 0
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget_0'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '2'
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_0').get_attribute('value') == '200'
        # BUDGET 1
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget_1'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '1'
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_1').get_attribute('value') == '100'
        # BUDGET 2
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget_2'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['7', 'Income (income)'],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2']
        ]
        assert budget_sel.first_selected_option.get_attribute('value') == '4'
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_2').get_attribute('value') == '75'
        elem = selenium.find_element(By.ID, 'trans_frm_notes')
        assert elem.get_attribute('value') == 'NewSplitTransNotes'
        # Ok, now edit it...
        Select(body.find_element(By.ID,
                                 'trans_frm_budget_1')).select_by_value('None')
        body.find_element(By.ID, 'trans_frm_budget_amount_1').clear()
        budget_amt = body.find_element(By.ID, 'trans_frm_budget_amount_0')
        budget_amt.clear()
        budget_amt.send_keys('300')
        self.assert_budget_split_does_not_have_error(selenium)
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 5 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that new trans was added to the table
        table = selenium.find_element(By.ID, 'table-transactions')
        texts = [y[2] for y in self.tbody2textlist(table)]
        assert 'NewTrans5' in texts
        t = testdb.query(Transaction).get(5)
        assert t is not None
        assert t.description == 'NewTrans5'
        assert t.date == dtnow().date()
        assert t.actual_amount == Decimal('375')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 1
        assert t.scheduled_trans_id is None
        assert t.notes == 'NewSplitTransNotes'
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            2: Decimal('300'),
            4: Decimal('75')
        }
        assert max([
            tx.id for tx in testdb.query(Transaction).all()
        ]) == 5

    def test_34_existing_trans_to_split(self, base_url, selenium, testdb):
        t = testdb.query(Transaction).get(3)
        assert t is not None
        assert t.description == 'T3'
        assert t.date == (dtnow() - timedelta(days=2)).date()
        assert t.actual_amount == Decimal('222.22')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 3
        assert t.scheduled_trans_id is None
        assert t.notes == 'notesT3'
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            2: Decimal('222.22')
        }
        assert max([
            tx.id for tx in testdb.query(Transaction).all()
        ]) == 5
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="T3"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 3'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '3'
        assert body.find_element(By.ID,
                                 'trans_frm_date').get_attribute('value') == (
                dtnow() - timedelta(days=2)
            ).strftime('%Y-%m-%d')
        assert body.find_element(By.ID,
                                 'trans_frm_amount').get_attribute('value') == '222.22'
        # NOT Split Budget
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed() is False
        # Ok, click to split it...
        self.try_click(
            selenium, selenium.find_element(By.ID, 'trans_frm_is_split')
        )
        # Should be split now...
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected()
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed()
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 2
        # Verify that initial budget was set
        assert Select(
            body.find_element(By.ID, 'trans_frm_budget_0')
        ).first_selected_option.get_attribute('value') == '2'
        # Verify that amount has been set
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_0').get_attribute('value') == '222.22'
        # Set the amount
        budget_amt = body.find_element(By.ID, 'trans_frm_budget_amount_0')
        budget_amt.clear()
        budget_amt.send_keys('100.02')
        # select the second budget
        Select(body.find_element(By.ID,
                                 'trans_frm_budget_1')).select_by_value('4')
        # Verify that second amount is set
        assert body.find_element(By.ID,
                                 'trans_frm_budget_amount_1').get_attribute('value') == '122.20'
        self.assert_budget_split_does_not_have_error(selenium)
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 3 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)

    def test_35_verify_db(self, testdb):
        t = testdb.query(Transaction).get(3)
        assert t is not None
        assert t.description == 'T3'
        assert t.date == (dtnow() - timedelta(days=2)).date()
        assert t.actual_amount == Decimal('222.22')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 3
        assert t.scheduled_trans_id is None
        assert t.notes == 'notesT3'
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            2: Decimal('100.02'),
            4: Decimal('122.20')
        }
        assert max([
            tx.id for tx in testdb.query(Transaction).all()
        ]) == 5

    def test_36_existing_split_trans_to_not(self, base_url, selenium, testdb):
        t = testdb.query(Transaction).get(3)
        assert t is not None
        assert t.description == 'T3'
        assert t.date == (dtnow() - timedelta(days=2)).date()
        assert t.actual_amount == Decimal('222.22')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 3
        assert t.scheduled_trans_id is None
        assert t.notes == 'notesT3'
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            2: Decimal('100.02'),
            4: Decimal('122.20')
        }
        assert max([
            tx.id for tx in testdb.query(Transaction).all()
        ]) == 5
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="T3"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 3'
        assert body.find_element(By.ID,
                                 'trans_frm_id').get_attribute('value') == '3'
        assert body.find_element(By.ID,
                                 'trans_frm_date').get_attribute('value') == (
                       dtnow() - timedelta(days=2)
               ).strftime('%Y-%m-%d')
        assert body.find_element(By.ID,
                                 'trans_frm_amount').get_attribute('value') == '222.22'
        # Should be split...
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected()
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed()
        assert len(
            selenium.find_elements(By.CLASS_NAME, 'budget_split_row')
        ) == 2
        # Ok, click to un-split it...
        self.try_click(
            selenium, selenium.find_element(By.ID, 'trans_frm_is_split')
        )
        # NOT Split Budget
        assert selenium.find_element(By.ID,
                                     'trans_frm_is_split').is_selected() is False
        assert selenium.find_element(By.ID,
                                     'trans_frm_budget_group').is_displayed() is True
        assert selenium.find_element(By.ID,
                                     'trans_frm_split_budget_container').is_displayed() is False
        # Ok, now edit it...
        budget_sel = Select(body.find_element(By.ID, 'trans_frm_budget'))
        budget_sel.select_by_value('2')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 3 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)

    def test_37_verify_db(self, testdb):
        t = testdb.query(Transaction).get(3)
        assert t is not None
        assert t.description == 'T3'
        assert t.date == (dtnow() - timedelta(days=2)).date()
        assert t.actual_amount == Decimal('222.22')
        assert t.budgeted_amount is None
        assert t.planned_budget_id is None
        assert t.account_id == 3
        assert t.scheduled_trans_id is None
        assert t.notes == 'notesT3'
        assert {bt.budget_id: bt.amount for bt in t.budget_transactions} == {
            2: Decimal('222.22')
        }
        assert max([
            tx.id for tx in testdb.query(Transaction).all()
        ]) == 5


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestTransModalCurrencyNormalization(AcceptanceHelper):
    """
    Browser tests for currency input normalization; GitHub issue #323.

    Entering ``1,234.56`` used to produce a 500 Internal Server Error, and a
    bare ``123`` used to be rejected as an invalid value.
    """

    def _add_transaction(self, base_url, selenium, amount, description,
                         sales_tax=None):
        """
        Fill and submit the Add Transaction modal with the given amount, and
        return the text of the first div in the modal body afterwards.
        """
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.ID, 'btn_add_trans')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Transaction'
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys(amount)
        desc = body.find_element(By.ID, 'trans_frm_description')
        desc.send_keys(description)
        Select(
            body.find_element(By.ID, 'trans_frm_account')
        ).select_by_value('1')
        Select(
            body.find_element(By.ID, 'trans_frm_budget')
        ).select_by_value('1')
        if sales_tax is not None:
            tax = body.find_element(By.ID, 'trans_frm_sales_tax')
            tax.clear()
            tax.send_keys(sales_tax)
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        _, _, body = self.get_modal_parts(selenium)
        return body

    def test_01_comma_separated_amount(self, base_url, selenium):
        """Entering "1,234.56" must save, not raise a 500."""
        body = self._add_transaction(
            base_url, selenium, '1,234.56', 'CommaAmount'
        )
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')

    def test_02_verify_comma_separated_amount(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CommaAmount')
        ).one()
        assert t.actual_amount == Decimal('1234.56')
        assert t.budget_transactions[0].amount == Decimal('1234.56')

    def test_03_bare_integer_amount(self, base_url, selenium):
        """Entering "123" must save; it used to require "123.0"."""
        body = self._add_transaction(
            base_url, selenium, '123', 'BareInteger', sales_tax='7'
        )
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')

    def test_04_verify_bare_integer_amount(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('BareInteger')
        ).one()
        assert t.actual_amount == Decimal('123')
        assert t.sales_tax == Decimal('7')

    def test_05_currency_symbol_amount(self, base_url, selenium):
        body = self._add_transaction(
            base_url, selenium, '$1,234.56', 'SymbolAmount'
        )
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')

    def test_06_verify_currency_symbol_amount(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('SymbolAmount')
        ).one()
        assert t.actual_amount == Decimal('1234.56')

    def test_07_space_separated_amount(self, base_url, selenium):
        body = self._add_transaction(
            base_url, selenium, ' 1 234.56 ', 'SpaceAmount'
        )
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')

    def test_08_verify_space_separated_amount(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('SpaceAmount')
        ).one()
        assert t.actual_amount == Decimal('1234.56')

    def test_09_parenthesized_negative_amount(self, base_url, selenium):
        body = self._add_transaction(
            base_url, selenium, '(1,234.56)', 'ParenAmount'
        )
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')

    def test_10_verify_parenthesized_negative_amount(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('ParenAmount')
        ).one()
        assert t.actual_amount == Decimal('-1234.56')

    def test_20_invalid_amount_shows_field_error(self, base_url, selenium):
        """Malformed input must produce a field error, never a 500."""
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.ID, 'btn_add_trans')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys('abc')
        desc = body.find_element(By.ID, 'trans_frm_description')
        desc.send_keys('ShouldNotBeSaved')
        Select(
            body.find_element(By.ID, 'trans_frm_account')
        ).select_by_value('1')
        Select(
            body.find_element(By.ID, 'trans_frm_budget')
        ).select_by_value('1')
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        _, _, body = self.get_modal_parts(selenium)
        # the modal is still the form, not a success alert
        assert 'Invalid amount: "abc"' in body.text
        assert 'alert-success' not in body.get_attribute('innerHTML')

    def test_21_verify_invalid_amount_not_saved(self, testdb):
        assert testdb.query(Transaction).filter(
            Transaction.description.__eq__('ShouldNotBeSaved')
        ).all() == []

    def test_30_post_comma_amount_is_not_a_server_error(self, base_url):
        """
        The reported bug, at the HTTP level: this used to be a 500.
        """
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '1,234.56',
                'description': 'PostedCommaAmount',
                'notes': '',
                'account': '1',
                'budgets': {'1': '1,234.56'},
                'sales_tax': ''
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True

    def test_31_verify_posted_comma_amount(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('PostedCommaAmount')
        ).one()
        assert t.actual_amount == Decimal('1234.56')
        assert t.budget_transactions[0].amount == Decimal('1234.56')

    @pytest.mark.parametrize(
        'amount', ['abc', '1.2.3', '10,00', '1,23,4.56']
    )
    def test_32_post_invalid_amount_is_not_a_server_error(
        self, base_url, amount
    ):
        """
        Ambiguous grouping such as "10,00" must be rejected rather than
        silently read as 1000.
        """
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': amount,
                'description': 'InvalidPost',
                'notes': '',
                'account': '1',
                'budgets': {'1': amount},
                'sales_tax': ''
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['amount'] == ['Invalid amount: "%s"' % amount]

    def test_33_verify_invalid_posts_not_saved(self, testdb):
        assert testdb.query(Transaction).filter(
            Transaction.description.__eq__('InvalidPost')
        ).all() == []


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestTransModalSplitCurrencyNormalization(AcceptanceHelper):
    """
    Browser tests for the client-side currency parser used by budget split
    validation; GitHub issue #323. ``parseFloat('1,234.56')`` is ``1``, so
    before this change the in-browser check disabled Save and the user could
    never reach the server.
    """

    def test_01_split_validation_accepts_separators(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.ID, 'btn_add_trans')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys('1,234.56')
        desc = body.find_element(By.ID, 'trans_frm_description')
        desc.send_keys('SplitCommaAmount')
        Select(
            body.find_element(By.ID, 'trans_frm_account')
        ).select_by_value('1')
        selenium.find_element(By.ID, 'trans_frm_is_split').click()
        Select(
            body.find_element(By.ID, 'trans_frm_budget_0')
        ).select_by_value('1')
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_0')
        tmp.clear()
        tmp.send_keys('1,000.00')
        Select(
            body.find_element(By.ID, 'trans_frm_budget_1')
        ).select_by_value('2')
        tmp = body.find_element(By.ID, 'trans_frm_budget_amount_1')
        tmp.clear()
        tmp.send_keys('234.56')
        # blur the last field so the split validation runs
        body.find_element(By.ID, 'trans_frm_description').click()
        self.wait_for_jquery_done(selenium)
        assert selenium.find_element(
            By.ID, 'budget-split-feedback'
        ).text == ''
        assert selenium.find_element(By.ID, 'modalSaveButton').is_enabled()
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')

    def test_02_verify_split_amounts(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('SplitCommaAmount')
        ).one()
        assert t.actual_amount == Decimal('1234.56')
        assert {
            bt.budget_id: bt.amount for bt in t.budget_transactions
        } == {
            1: Decimal('1000.00'),
            2: Decimal('234.56')
        }

    def test_10_split_remainder_autofill_uses_normalized_amount(
        self, base_url, selenium
    ):
        """
        Selecting a budget auto-fills the remainder. With parseFloat, a
        transaction amount of "1,234.56" made the remainder 1.00.
        """
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.ID, 'btn_add_trans')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        amt = body.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys('1,234.56')
        selenium.find_element(By.ID, 'trans_frm_is_split').click()
        Select(
            body.find_element(By.ID, 'trans_frm_budget_0')
        ).select_by_value('1')
        self.wait_for_jquery_done(selenium)
        assert body.find_element(
            By.ID, 'trans_frm_budget_amount_0'
        ).get_attribute('value') == '1234.56'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestTransModalNoBudgetImpactAndCreditPayment(AcceptanceHelper):
    """
    The "No Budget Impact?" checkbox and the "Credit Card Payment For" select
    on the Add/Edit Transaction modal. GitHub issues #210 and #319.

    Sample data accounts: 1 BankOne (Bank), 2 BankTwoStale (Bank),
    3 CreditOne (Credit), 4 CreditTwo (Credit), 5 InvestmentOne (Investment),
    6 DisabledBank (Bank, inactive).
    """

    def test_00_add_transactions(self, testdb):
        # Transaction 5 - an ordinary transaction, neither field set
        testdb.add(Transaction(
            account_id=1,
            budget_amounts={testdb.query(Budget).get(1): Decimal('11.11')},
            date=dtnow().date(),
            description='NBIOrdinary'
        ))
        # Transaction 6 - explicitly no budget impact
        testdb.add(Transaction(
            account_id=1,
            budget_amounts={testdb.query(Budget).get(1): Decimal('22.22')},
            date=dtnow().date(),
            description='NBIStatementCredit',
            no_budget_impact=True
        ))
        # Transaction 7 - a payment toward CreditOne
        testdb.add(Transaction(
            account_id=1,
            budget_amounts={testdb.query(Budget).get(1): Decimal('33.33')},
            date=dtnow().date(),
            description='NBICardPayment',
            credit_payment_acct_id=3
        ))
        testdb.commit()

    def test_01_verify_db(self, testdb):
        t = testdb.query(Transaction).get(5)
        assert t.no_budget_impact is False
        assert t.credit_payment_acct_id is None
        assert t.is_excluded_from_budget is False
        t = testdb.query(Transaction).get(6)
        assert t.no_budget_impact is True
        assert t.credit_payment_acct_id is None
        assert t.is_excluded_from_budget is True
        t = testdb.query(Transaction).get(7)
        # Setting the credit account alone excludes the transaction, without
        # no_budget_impact being set separately (spec FR-011).
        assert t.no_budget_impact is False
        assert t.credit_payment_acct_id == 3
        assert t.is_excluded_from_budget is True
        assert t.credit_payment_acct.name == 'CreditOne'

    def test_02_credit_select_offers_credit_accounts_only(
        self, base_url, selenium
    ):
        """Spec FR-010: the select offers credit accounts and no others, plus
        an explicit empty default."""
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="NBIOrdinary"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        sel = Select(
            body.find_element(By.ID, 'trans_frm_credit_payment_acct')
        )
        opts = [
            [o.get_attribute('value'), o.text] for o in sel.options
        ]
        assert opts == [
            ['None', ''],
            ['3', 'CreditOne'],
            ['4', 'CreditTwo']
        ]
        assert sel.first_selected_option.get_attribute('value') == 'None'
        assert body.find_element(
            By.ID, 'trans_frm_no_budget_impact'
        ).is_selected() is False

    def test_03_modal_populates_no_budget_impact(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(
            By.XPATH, '//a[text()="NBIStatementCredit"]'
        )
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 6'
        assert body.find_element(
            By.ID, 'trans_frm_no_budget_impact'
        ).is_selected() is True
        sel = Select(
            body.find_element(By.ID, 'trans_frm_credit_payment_acct')
        )
        assert sel.first_selected_option.get_attribute('value') == 'None'

    def test_04_modal_populates_credit_payment(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element(By.XPATH, '//a[text()="NBICardPayment"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 7'
        sel = Select(
            body.find_element(By.ID, 'trans_frm_credit_payment_acct')
        )
        assert sel.first_selected_option.get_attribute('value') == '3'
        # The checkbox shows the user's own choice, which was never made; the
        # exclusion comes from the credit account designation.
        assert body.find_element(
            By.ID, 'trans_frm_no_budget_impact'
        ).is_selected() is False

    def test_05_transactions_table_marks_excluded(self, base_url, selenium):
        """Spec FR-007: excluded transactions are visually distinguished."""
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        # 4 transactions from the sample data plus the 3 added by test_00
        self.wait_for_datatable_rows(selenium, 'table-transactions', 7)
        table = selenium.find_element(By.ID, 'table-transactions')
        # description is the third column; the marker renders inline after it
        descriptions = [row[2] for row in self.tbody2textlist(table)]

        def cell_for(desc):
            matches = [d for d in descriptions if d.startswith(desc)]
            assert len(matches) == 1, \
                'expected exactly one row for %s, got %s' % (desc, matches)
            return matches[0]

        assert cell_for('NBICardPayment') == \
            'NBICardPayment (payment for CreditOne; no budget impact)'
        assert cell_for('NBIStatementCredit') == \
            'NBIStatementCredit (no budget impact)'
        assert cell_for('NBIOrdinary') == 'NBIOrdinary'

    def test_06_backend_persists_both_fields(self, base_url, testdb):
        """Spec SC-003: recording a payment takes one entry, with no
        offsetting transaction."""
        before = testdb.query(Transaction).count()
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '123.45',
                'description': 'NewCardPayment',
                'notes': '',
                'account': '1',
                'budgets': {'1': '123.45'},
                'sales_tax': '0.0',
                'no_budget_impact': False,
                'credit_payment_acct': '4'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True
        # This session began its read transaction before the POST, so under
        # REPEATABLE READ it cannot see the app's committed write until the
        # transaction ends and a new snapshot is taken.
        testdb.rollback()
        testdb.expire_all()
        assert testdb.query(Transaction).count() == before + 1
        t = testdb.query(Transaction).get(res.json()['trans_id'])
        assert t.description == 'NewCardPayment'
        assert t.credit_payment_acct_id == 4
        assert t.no_budget_impact is False
        assert t.is_excluded_from_budget is True

    def test_07_backend_persists_no_budget_impact(self, base_url, testdb):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '55.55',
                'description': 'NewStatementCredit',
                'notes': '',
                'account': '1',
                'budgets': {'1': '55.55'},
                'sales_tax': '0.0',
                'no_budget_impact': True,
                'credit_payment_acct': 'None'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True
        testdb.expire_all()
        t = testdb.query(Transaction).get(res.json()['trans_id'])
        assert t.no_budget_impact is True
        assert t.credit_payment_acct_id is None
        assert t.is_excluded_from_budget is True

    def test_08_backend_clearing_credit_acct_restores_impact(
        self, base_url, testdb
    ):
        """Spec FR-014."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('NewCardPayment')
        ).one()
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'id': str(t.id),
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '123.45',
                'description': 'NewCardPayment',
                'notes': '',
                'account': '1',
                'budgets': {'1': '123.45'},
                'sales_tax': '0.0',
                'no_budget_impact': False,
                'credit_payment_acct': 'None'
            }
        )
        assert res.status_code == 200
        assert res.json()['success'] is True
        testdb.rollback()
        testdb.expire_all()
        t = testdb.query(Transaction).get(t.id)
        assert t.credit_payment_acct_id is None
        assert t.no_budget_impact is False
        assert t.is_excluded_from_budget is False

    def test_09_backend_rejects_non_credit_account(self, base_url):
        """Spec FR-015: the form endpoint is reachable without the restricted
        select, so it must enforce the account type itself. Account 1 is a
        Bank account."""
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '10.00',
                'description': 'BadCreditAcct',
                'notes': '',
                'account': '1',
                'budgets': {'1': '10.00'},
                'sales_tax': '0.0',
                'no_budget_impact': False,
                'credit_payment_acct': '1'
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['credit_payment_acct'] == [
            'BankOne is not a credit account; only credit accounts can be '
            'paid.'
        ]

    def test_10_backend_rejects_unknown_account(self, base_url):
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '10.00',
                'description': 'BadCreditAcct2',
                'notes': '',
                'account': '1',
                'budgets': {'1': '10.00'},
                'sales_tax': '0.0',
                'no_budget_impact': False,
                'credit_payment_acct': '98765'
            }
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['credit_payment_acct'] == [
            'Account "98765" is invalid.'
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestCreditPaymentInfoAjax(AcceptanceHelper):
    """
    The GET /ajax/credit-payment-info endpoint that drives the modal's payment
    information panel. GitHub issue #210, User Story 3.

    This class builds its own credit account and charges rather than asserting
    against the shared sample data, so the expected numbers are the ones the
    spec states and cannot be shifted by whatever other test classes have done
    to the sample data before this one runs.

    With PAY_PERIOD_START_DATE as the start of the currently-open period, the
    account gets $400.00 of charges in the preceding, closed period and $150.00
    in the open one -- the scenario in User Story 3.
    """

    @property
    def closed_charge_date(self):
        return PAY_PERIOD_START_DATE - timedelta(days=7)

    @property
    def open_charge_date(self):
        return PAY_PERIOD_START_DATE + timedelta(days=1)

    def test_00_add_card_and_charges(self, testdb):
        card = Account(
            description='Payment info test card',
            name='InfoCard',
            acct_type=AcctType.Credit,
            credit_limit=Decimal('2000.00')
        )
        testdb.add(card)
        testdb.flush()
        budget = testdb.query(Budget).get(1)
        testdb.add(Transaction(
            date=self.closed_charge_date,
            budget_amounts={budget: Decimal('400.00')},
            description='InfoCard closed period charges',
            account=card
        ))
        testdb.add(Transaction(
            date=self.open_charge_date,
            budget_amounts={budget: Decimal('150.00')},
            description='InfoCard open period charges',
            account=card
        ))
        testdb.flush()
        testdb.commit()
        self.__class__.card_id = card.id

    def _get(self, base_url, amount, **extra):
        params = {
            'account_id': str(self.card_id),
            'amount': amount,
            'date': dtnow().strftime('%Y-%m-%d')
        }
        params.update(extra)
        return requests.get(
            base_url + '/ajax/credit-payment-info', params=params
        )

    def test_01_payment_of_400(self, base_url):
        """Spec US3 scenario 1: the whole 400.00 settles closed-period charges
        and nothing applies to the open period."""
        res = self._get(base_url, '400.00')
        assert res.status_code == 200
        j = res.json()
        assert j['account_name'] == 'InfoCard'
        assert j['amount'] == 400.0
        assert j['total_unpaid'] == 550.0
        assert j['total_attributed'] == 400.0
        assert j['excess'] == 0.0
        assert j['pays_itself'] is False
        assert j['warnings'] == []
        assert [
            [p['is_closed'], p['attributed']] for p in j['periods']
        ] == [[True, 400.0], [False, 0.0]]

    def test_02_payment_of_500(self, base_url):
        """Spec US3 scenario 2: 400.00 settles the closed period, 100.00
        applies to the open one, and there is no warning."""
        j = self._get(base_url, '500.00').json()
        assert j['total_attributed'] == 500.0
        assert j['excess'] == 0.0
        assert j['warnings'] == []
        assert [
            [p['is_closed'], p['attributed']] for p in j['periods']
        ] == [[True, 400.0], [False, 100.0]]

    def test_03_payment_of_600_warns(self, base_url):
        """Spec US3 scenario 3 / SC-004: the warning states the excess."""
        j = self._get(base_url, '600.00').json()
        assert j['total_unpaid'] == 550.0
        assert j['total_attributed'] == 550.0
        assert j['excess'] == 50.0
        assert j['warnings'] == [
            'This payment exceeds the $550.00 of unpaid charges recorded for '
            'InfoCard by $50.00. This usually means charges are missing from '
            'your records, or were recorded against the wrong account.'
        ]

    def test_04_pays_itself_warns(self, base_url):
        """Spec FR-022."""
        j = self._get(
            base_url, '100.00', payer_account_id=str(self.card_id)
        ).json()
        assert j['pays_itself'] is True
        assert j['warnings'] == [
            'This transaction is recorded against InfoCard and is also marked '
            'as a payment toward InfoCard. A payment should be recorded '
            'against the account the money came from.'
        ]

    def test_05_prior_payment_reduces_unpaid(self, base_url, testdb):
        """A payment already recorded toward the card is subtracted, so the
        next payment is measured against what is left."""
        budget = testdb.query(Budget).get(1)
        testdb.add(Transaction(
            date=dtnow().date(),
            budget_amounts={budget: Decimal('400.00')},
            description='InfoCard earlier payment',
            account_id=1,
            credit_payment_acct_id=self.card_id
        ))
        testdb.flush()
        testdb.commit()
        j = self._get(base_url, '150.00').json()
        assert j['total_unpaid'] == 150.0
        assert j['total_attributed'] == 150.0
        assert j['excess'] == 0.0
        assert j['warnings'] == []

    def test_06_editing_excludes_self(self, base_url, testdb):
        """Spec US3 scenario 6 / FR-019: reopening a saved payment must not
        count it against itself."""
        txn = testdb.query(Transaction).filter(
            Transaction.description.__eq__('InfoCard earlier payment')
        ).one()
        j = self._get(base_url, '400.00', txn_id=str(txn.id)).json()
        assert j['total_unpaid'] == 550.0
        assert j['total_attributed'] == 400.0
        assert j['excess'] == 0.0
        assert j['warnings'] == []

    def test_07_non_credit_account_rejected(self, base_url):
        res = requests.get(
            base_url + '/ajax/credit-payment-info',
            params={'account_id': '1', 'amount': '100.00'}
        )
        assert res.status_code == 400
        assert res.json() == {'error': 'BankOne is not a credit account.'}

    def test_08_unknown_account_rejected(self, base_url):
        res = requests.get(
            base_url + '/ajax/credit-payment-info',
            params={'account_id': '98765', 'amount': '100.00'}
        )
        assert res.status_code == 400
        assert res.json() == {
            'error': 'Invalid or missing account_id: 98765'
        }

    def test_09_missing_amount_rejected(self, base_url):
        res = requests.get(
            base_url + '/ajax/credit-payment-info',
            params={'account_id': str(self.card_id)}
        )
        assert res.status_code == 400
        assert 'Invalid or missing amount' in res.json()['error']

    def test_10_bad_date_rejected(self, base_url):
        res = requests.get(
            base_url + '/ajax/credit-payment-info',
            params={
                'account_id': str(self.card_id),
                'amount': '1.00',
                'date': 'notadate'
            }
        )
        assert res.status_code == 400
        assert res.json() == {
            'error': 'Date "notadate" is not valid (YYYY-MM-DD)'
        }

    def test_11_currency_formatted_amount_accepted(self, base_url):
        """The modal sends whatever the user typed; the endpoint normalizes it
        the same way the form does. See GitHub issue #323."""
        j = self._get(base_url, '1,234.56').json()
        assert j['amount'] == 1234.56


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestTransModalCreditPaymentPanel(AcceptanceHelper):
    """
    The payment information panel inside the Add/Edit Transaction modal.
    GitHub issue #210, User Story 3.

    Builds its own card, as TestCreditPaymentInfoAjax does and for the same
    reason: $400.00 of charges in the closed period and $150.00 in the open
    one, so the panel's numbers are the spec's.
    """

    def test_00_add_card_and_charges(self, testdb):
        card = Account(
            description='Panel test card',
            name='PanelCard',
            acct_type=AcctType.Credit,
            credit_limit=Decimal('2000.00')
        )
        testdb.add(card)
        testdb.flush()
        budget = testdb.query(Budget).get(1)
        testdb.add(Transaction(
            date=PAY_PERIOD_START_DATE - timedelta(days=7),
            budget_amounts={budget: Decimal('400.00')},
            description='PanelCard closed period charges',
            account=card
        ))
        testdb.add(Transaction(
            date=PAY_PERIOD_START_DATE + timedelta(days=1),
            budget_amounts={budget: Decimal('150.00')},
            description='PanelCard open period charges',
            account=card
        ))
        testdb.flush()
        testdb.commit()

    def test_01_panel_hidden_until_card_selected(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        selenium.find_element(By.ID, 'btn_add_trans').click()
        self.wait_for_modal_shown(selenium)
        assert selenium.find_element(
            By.ID, 'trans_frm_credit_payment_info'
        ).is_displayed() is False

    def _open_modal_with(self, selenium, base_url, amount):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        selenium.find_element(By.ID, 'btn_add_trans').click()
        self.wait_for_modal_shown(selenium)
        amt = selenium.find_element(By.ID, 'trans_frm_amount')
        amt.clear()
        amt.send_keys(amount)
        Select(
            selenium.find_element(By.ID, 'trans_frm_credit_payment_acct')
        ).select_by_visible_text('PanelCard')

    def test_02_panel_shows_breakdown(self, base_url, selenium):
        self._open_modal_with(selenium, base_url, '400.00')
        self.wait_for_id(selenium, 'credit_payment_periods')
        panel = selenium.find_element(By.ID, 'trans_frm_credit_payment_info')
        assert panel.is_displayed() is True
        assert '$400.00 of $400.00 settles recorded charges' in panel.text
        assert '$550.00 of unpaid charges' in panel.text
        assert 'closed' in panel.text
        assert 'open' in panel.text
        assert len(
            panel.find_elements(By.ID, 'credit_payment_warning_0')
        ) == 0

    def test_03_panel_warns_and_save_stays_enabled(self, base_url, selenium):
        """Spec US3 scenario 5 / FR-021: the warning is advisory. Save must
        stay enabled so a payment the person knows to be correct can still be
        recorded."""
        self._open_modal_with(selenium, base_url, '600.00')
        self.wait_for_id(selenium, 'credit_payment_warning_0')
        warning = selenium.find_element(By.ID, 'credit_payment_warning_0')
        assert 'exceeds the $550.00 of unpaid charges' in warning.text
        assert 'by $50.00' in warning.text
        assert selenium.find_element(
            By.ID, 'modalSaveButton'
        ).is_enabled() is True


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestTransactionFormNameOrId(AcceptanceHelper):
    """
    ``POST /forms/transaction`` accepting Accounts and Budgets by name as well
    as by ID, so that external tooling that only knows the names shown in the
    UI can use it. GitHub issue #322.

    The sample data these assert against: Account 1 is ``BankOne`` (Bank),
    Account 3 is ``CreditOne`` (Credit); Budget 1 is ``Periodic1`` (active),
    Budget 3 is ``Periodic3 Inactive``.
    """

    def _post(self, base_url, **overrides):
        payload = {
            'date': dtnow().strftime('%Y-%m-%d'),
            'amount': '10.00',
            'description': 'NameOrId',
            'notes': '',
            'account': 'BankOne',
            'budgets': {'Periodic1': '10.00'}
        }
        payload.update(overrides)
        return requests.post(base_url + '/forms/transaction', json=payload)

    def _created(self, res, testdb):
        """Assert success and return the created Transaction, freshly read."""
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is True, j
        # this session began its read transaction before the POST, so under
        # REPEATABLE READ it cannot see the app's committed write until the
        # transaction ends and a new snapshot is taken
        testdb.rollback()
        testdb.expire_all()
        return testdb.query(Transaction).get(j['trans_id'])

    def test_01_account_and_budget_by_name(self, base_url, testdb):
        """FR-001, FR-002: the headline case, no numeric IDs anywhere."""
        res = self._post(base_url, description='NameOrIdBothNames')
        t = self._created(res, testdb)
        assert t.description == 'NameOrIdBothNames'
        assert t.account_id == 1
        assert {
            bt.budget_id: bt.amount for bt in t.budget_transactions
        } == {1: Decimal('10.00')}

    def test_02_mixed_id_account_and_name_budget(self, base_url, testdb):
        """FR-008: IDs and names may be mixed within one request."""
        res = self._post(
            base_url, description='NameOrIdMixed', account='1',
            budgets={'Periodic1': '10.00'}
        )
        t = self._created(res, testdb)
        assert t.account_id == 1
        assert [bt.budget_id for bt in t.budget_transactions] == [1]

    def test_03_mixed_name_account_and_id_budget(self, base_url, testdb):
        res = self._post(
            base_url, description='NameOrIdMixed2', account='BankOne',
            budgets={'1': '10.00'}
        )
        t = self._created(res, testdb)
        assert t.account_id == 1
        assert [bt.budget_id for bt in t.budget_transactions] == [1]

    def test_04_ids_only_still_work(self, base_url, testdb):
        """FR-008: the web UI's own request shape is unaffected."""
        res = self._post(
            base_url, description='NameOrIdIdsOnly', account='1',
            budgets={'1': '10.00'}
        )
        t = self._created(res, testdb)
        assert t.account_id == 1
        assert [bt.budget_id for bt in t.budget_transactions] == [1]

    def test_05_names_are_case_and_whitespace_insensitive(
        self, base_url, testdb
    ):
        """FR-005."""
        res = self._post(
            base_url, description='NameOrIdSloppy', account='  bankONE ',
            budgets={' PERIODIC1  ': '10.00'}
        )
        t = self._created(res, testdb)
        assert t.account_id == 1
        assert [bt.budget_id for bt in t.budget_transactions] == [1]

    def test_06_split_across_budgets_by_name(self, base_url, testdb):
        res = self._post(
            base_url, description='NameOrIdSplit', amount='30.00',
            budgets={'Periodic1': '10.00', 'Periodic2': '20.00'}
        )
        t = self._created(res, testdb)
        assert {
            bt.budget_id: bt.amount for bt in t.budget_transactions
        } == {1: Decimal('10.00'), 2: Decimal('20.00')}

    def test_07_credit_payment_acct_by_name(self, base_url, testdb):
        """FR-003."""
        res = self._post(
            base_url, description='NameOrIdCardPayment',
            credit_payment_acct='CreditOne'
        )
        t = self._created(res, testdb)
        assert t.credit_payment_acct_id == 3

    def test_08_credit_payment_acct_none_still_means_none(
        self, base_url, testdb
    ):
        """The empty sentinel must not be resolved as a name."""
        res = self._post(
            base_url, description='NameOrIdNoCardPayment',
            credit_payment_acct='None'
        )
        t = self._created(res, testdb)
        assert t.credit_payment_acct_id is None

    def test_09_update_existing_transaction_by_name(self, base_url, testdb):
        """Resolution behaves identically on the update path."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('NameOrIdBothNames')
        ).one()
        res = self._post(
            base_url, id=str(t.id), description='NameOrIdUpdated',
            amount='11.00', account='BankTwoStale',
            budgets={'Periodic2': '11.00'}
        )
        t = self._created(res, testdb)
        assert t.description == 'NameOrIdUpdated'
        assert t.account_id == 2
        assert [bt.budget_id for bt in t.budget_transactions] == [2]

    def test_10_notes_and_sales_tax_may_be_omitted(self, base_url, testdb):
        """Both are documented as optional but used to 500 when absent; an
        external caller has no reason to send an empty string for a field it
        does not use."""
        res = requests.post(
            base_url + '/forms/transaction',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': '10.00',
                'description': 'NameOrIdNoOptionalFields',
                'account': 'BankOne',
                'budgets': {'Periodic1': '10.00'}
            }
        )
        t = self._created(res, testdb)
        assert t.notes == ''
        assert t.sales_tax == Decimal('0.0')

    def test_20_unknown_account_name_rejected(self, base_url, testdb):
        """FR-006: quote the offending value, and write nothing."""
        before = testdb.query(Transaction).count()
        res = self._post(
            base_url, description='NameOrIdBadAcct', account='No Such Account'
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['account'] == [
            'Account "No Such Account" is invalid.'
        ]
        testdb.rollback()
        testdb.expire_all()
        assert testdb.query(Transaction).count() == before

    def test_21_unknown_budget_name_rejected(self, base_url, testdb):
        before = testdb.query(Transaction).count()
        res = self._post(
            base_url, description='NameOrIdBadBudget',
            budgets={'No Such Budget': '10.00'}
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['budgets'] == [
            'Budget "No Such Budget" is invalid.'
        ]
        testdb.rollback()
        testdb.expire_all()
        assert testdb.query(Transaction).count() == before

    def test_22_unknown_credit_payment_acct_name_rejected(self, base_url):
        res = self._post(
            base_url, description='NameOrIdBadCPA',
            credit_payment_acct='No Such Card'
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['credit_payment_acct'] == [
            'Account "No Such Card" is invalid.'
        ]

    def test_23_partial_name_is_not_a_match(self, base_url):
        """FR-005: exact matching only. A near miss must fail loudly rather
        than land on the wrong budget."""
        res = self._post(
            base_url, description='NameOrIdPartial',
            budgets={'Periodic': '10.00'}
        )
        assert res.json()['errors']['budgets'] == [
            'Budget "Periodic" is invalid.'
        ]

    def test_24_income_display_suffix_is_not_the_name(self, base_url):
        """The UI labels income budgets "Income (income)"; the name is
        "Income". Documented, not special-cased."""
        res = self._post(
            base_url, description='NameOrIdIncomeSuffix',
            budgets={'Income (income)': '10.00'}
        )
        assert res.json()['errors']['budgets'] == [
            'Budget "Income (income)" is invalid.'
        ]

    def test_25_inactive_budget_by_name_still_rejected(self, base_url):
        """FR-007: resolving by name does not weaken any existing rule."""
        res = self._post(
            base_url, description='NameOrIdInactive',
            budgets={'Periodic3 Inactive': '10.00'}
        )
        assert res.json()['errors']['budgets'] == [
            'New transactions cannot use an inactive budget '
            '(Periodic3 Inactive).'
        ]

    def test_26_non_credit_account_by_name_still_rejected(self, base_url):
        """FR-007."""
        res = self._post(
            base_url, description='NameOrIdNonCredit',
            credit_payment_acct='BankOne'
        )
        assert res.json()['errors']['credit_payment_acct'] == [
            'BankOne is not a credit account; only credit accounts can be '
            'paid.'
        ]

    def test_27_duplicate_budget_reference_rejected(self, base_url, testdb):
        """Rule R7: two keys denoting one Budget would silently collapse into
        one allocation, so the request is refused instead."""
        before = testdb.query(Transaction).count()
        res = self._post(
            base_url, description='NameOrIdDupBudget', amount='20.00',
            budgets={'1': '10.00', 'Periodic1': '10.00'}
        )
        assert res.status_code == 200
        j = res.json()
        assert j['success'] is False
        assert j['errors']['budgets'] == [
            'Budget Periodic1 specified more than once.'
        ]
        testdb.rollback()
        testdb.expire_all()
        assert testdb.query(Transaction).count() == before

    def test_30_add_numerically_named_budget(self, testdb):
        """Set up the digits-first precedence tests below: a Budget whose name
        is the decimal string of a *different* Budget's ID."""
        testdb.add(Budget(
            name='2',
            is_periodic=True,
            description='Budget literally named "2"',
            starting_balance=Decimal('100.00')
        ))
        testdb.add(Budget(
            name='99999',
            is_periodic=True,
            description='Budget literally named "99999"',
            starting_balance=Decimal('100.00')
        ))
        testdb.flush()
        testdb.commit()

    def test_31_digits_resolve_to_the_id_not_the_name(
        self, base_url, testdb
    ):
        """Rule R2: Budget 2 exists, and a different Budget is named "2".
        The ID wins."""
        res = self._post(
            base_url, description='NameOrIdDigitsAreIds',
            budgets={'2': '10.00'}
        )
        t = self._created(res, testdb)
        assert [bt.budget_id for bt in t.budget_transactions] == [2]

    def test_32_digits_fall_back_to_name_when_no_such_id(
        self, base_url, testdb
    ):
        """Rule R3: no Budget has ID 99999, so the Budget *named* "99999"
        stays reachable."""
        named = testdb.query(Budget).filter(
            Budget.name.__eq__('99999')
        ).one()
        assert named.id != 99999
        res = self._post(
            base_url, description='NameOrIdDigitsFallBack',
            budgets={'99999': '10.00'}
        )
        t = self._created(res, testdb)
        assert [bt.budget_id for bt in t.budget_transactions] == [named.id]
