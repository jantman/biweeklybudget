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
from datetime import timedelta, date
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from decimal import Decimal
from time import sleep

from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.scheduled_transaction import ScheduledTransaction


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestSchedTrans(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')

    def test_heading(self, selenium):
        heading = selenium.find_element(By.CLASS_NAME, 'navbar-brand')
        assert heading.text == 'Scheduled Transactions - BiweeklyBudget'

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
class TestSchedTransDefault(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.dt = dtnow()
        self.get(selenium, base_url + '/scheduled')

    def test_table(self, selenium):
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = self.tbody2textlist(table)
        # Extract just the descriptions and types for verification
        descriptions = [t[4] for t in texts]
        # Verify all expected transactions are present
        expected_descriptions = ['ST1', 'ST2', 'ST3', 'ST4', 'ST5', 'ST6']
        for desc in expected_descriptions:
            assert desc in descriptions, f'{desc} not found in table'

    def test_filter_opts(self, selenium):
        self.get(selenium, self.baseurl + '/scheduled')
        acct_filter = Select(selenium.find_element(By.ID, 'type_filter'))
        # find the options
        opts = []
        for o in acct_filter.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['date', 'Date'],
            ['monthly', 'Monthly'],
            ['per period', 'Per Period'],
            ['weekly', 'Weekly'],
            ['annual', 'Annual']
        ]

    def test_filter(self, selenium):
        self.get(selenium, self.baseurl + '/scheduled')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-scheduled-txn')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[4] for t in texts]
        # check all 6 transactions are present
        assert len(trans) == 6
        type_filter = Select(selenium.find_element(By.ID, 'type_filter'))
        # select Monthly
        type_filter.select_by_value('monthly')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-scheduled-txn')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[4] for t in texts]
        assert set(trans) == {'ST2', 'ST5'}
        # select back to all
        type_filter.select_by_value('None')
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-scheduled-txn')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[4] for t in texts]
        assert len(trans) == 6

    def test_search(self, selenium):
        self.get(selenium, self.baseurl + '/scheduled')
        search = self.retry_stale(
            lambda: selenium.find_element(By.XPATH, '//input[@type="search"]')
        )
        search.send_keys('ST3')
        sleep(3)  # yeah, yeah, I know...
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-scheduled-txn')
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[4] for t in texts]
        # check sanity
        assert trans == ['ST3']


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestSchedTransModalPerPeriod(AcceptanceHelper):

    def test_0_verify_db(self, testdb):
        t = testdb.query(ScheduledTransaction).get(3)
        assert t is not None
        assert t.description == 'ST3'
        assert t.num_per_period == 1
        assert t.date is None
        assert t.day_of_month is None
        assert t.amount == Decimal('-333.33')
        assert t.account_id == 2
        assert t.budget_id == 4
        assert t.notes == 'notesST3'
        assert t.is_active is True

    def test_1_modal_on_click(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.XPATH, '//a[text()="ST3"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Scheduled Transaction 3'
        assert body.find_element(By.ID,
                                 'sched_frm_id').get_attribute('value') == '3'
        assert body.find_element(By.ID,
                                 'sched_frm_description').get_attribute('value') == 'ST3'
        assert body.find_element(By.ID,
                                 'sched_frm_type_monthly').is_selected() is False
        assert body.find_element(By.ID,
                                 'sched_frm_type_date').is_selected() is False
        assert body.find_element(By.ID,
                                 'sched_frm_type_per_period').is_selected()
        assert body.find_element(By.ID,
                                 'sched_frm_num_per_period').get_attribute('value') == '1'
        assert body.find_element(By.ID,
                                 'sched_frm_amount').get_attribute('value') == '-333.33'
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
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
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        opts = []
        for o in budget_sel.options:
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
        assert budget_sel.first_selected_option.get_attribute('value') == '4'
        assert selenium.find_element(By.ID, 'sched_frm_active').is_selected()


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestSchedTransMonthlyURL(AcceptanceHelper):

    def test_0_verify_db(self, testdb):
        t = testdb.query(ScheduledTransaction).get(2)
        assert t is not None
        assert t.description == 'ST2'
        assert t.num_per_period is None
        assert t.date is None
        assert t.day_of_month == 4
        assert t.amount == Decimal('222.22')
        assert t.account_id == 1
        assert t.budget_id == 2
        assert t.notes == 'notesST2'
        assert t.is_active is True

    def test_1_modal_from_url(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled/2')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Scheduled Transaction 2'
        assert body.find_element(By.ID,
                                 'sched_frm_id').get_attribute('value') == '2'
        assert body.find_element(By.ID,
                                 'sched_frm_description').get_attribute('value') == 'ST2'
        assert body.find_element(By.ID,
                                 'sched_frm_type_monthly').is_selected()
        assert body.find_element(By.ID,
                                 'sched_frm_type_date').is_selected() is False
        assert body.find_element(By.ID,
                                 'sched_frm_type_per_period').is_selected() is False
        assert body.find_element(By.ID,
                                 'sched_frm_day_of_month').get_attribute('value') == '4'
        assert body.find_element(By.ID,
                                 'sched_frm_amount').get_attribute('value') == '222.22'
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        assert budget_sel.first_selected_option.get_attribute('value') == '2'
        assert selenium.find_element(By.ID, 'sched_frm_active').is_selected()


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestSchedTransModal(AcceptanceHelper):

    def test_00_edit_date_inactive_verify_db(self, testdb):
        t = testdb.query(ScheduledTransaction).get(4)
        assert t is not None
        assert t.description == 'ST4'
        assert t.num_per_period is None
        assert t.date == (
            dtnow() + timedelta(days=5)
        ).date()
        assert t.day_of_month is None
        assert t.amount == Decimal('444.44')
        assert t.account_id == 1
        assert t.budget_id == 1
        assert t.notes == 'notesST4'
        assert t.is_active is False

    def test_01_edit_date_inactive_modal_from_url(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled/4')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Scheduled Transaction 4'
        assert body.find_element(By.ID,
                                 'sched_frm_id').get_attribute('value') == '4'
        assert body.find_element(By.ID,
                                 'sched_frm_description').get_attribute('value') == 'ST4'
        assert body.find_element(By.ID,
                                 'sched_frm_type_monthly').is_selected() is False
        assert body.find_element(By.ID,
                                 'sched_frm_type_date').is_selected()
        assert body.find_element(By.ID,
                                 'sched_frm_type_per_period').is_selected() is False
        assert body.find_element(By.ID,
                                 'sched_frm_date').get_attribute('value') == (
            dtnow() + timedelta(days=5)).strftime('%Y-%m-%d')
        assert body.find_element(By.ID,
                                 'sched_frm_amount').get_attribute('value') == '444.44'
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        assert budget_sel.first_selected_option.get_attribute('value') == '1'
        assert selenium.find_element(By.ID,
                                     'sched_frm_active').is_selected() is False

    def test_02_edit_date_inactive_modal_edit(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled/4')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        desc = body.find_element(By.ID, 'sched_frm_description')
        desc.send_keys('edited')
        _type = body.find_element(By.ID, 'sched_frm_type_date')
        _type.click()
        date_input = body.find_element(By.ID, 'sched_frm_date')
        date_input.clear()
        date_input.send_keys((dtnow() + timedelta(days=1)).strftime('%Y-%m-%d'))
        amt = body.find_element(By.ID, 'sched_frm_amount')
        amt.clear()
        amt.send_keys('123.45')
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        acct_sel.select_by_value('2')
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        budget_sel.select_by_value('4')
        is_active = selenium.find_element(By.ID, 'sched_frm_active')
        is_active.click()
        assert is_active.is_selected()
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved ScheduledTransaction 4 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that updated budget was removed from the page
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = self.tbody2textlist(table)
        # sort order changes when we make this active
        assert texts[2][0] == 'yes'
        assert texts[2][4] == 'ST4edited'

    def test_03_edit_date_inactive_verify_db(self, testdb):
        t = testdb.query(ScheduledTransaction).get(4)
        assert t is not None
        assert t.description == 'ST4edited'
        assert t.num_per_period is None
        assert t.date == (
            dtnow() + timedelta(days=1)
        ).date()
        assert t.day_of_month is None
        assert t.amount == Decimal('123.45')
        assert t.account_id == 2
        assert t.budget_id == 4
        assert t.notes == 'notesST4'
        assert t.is_active is True

    def test_10_add_date_modal_on_click(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.ID, 'btn_add_sched')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Scheduled Transaction'
        desc = body.find_element(By.ID, 'sched_frm_description')
        desc.send_keys('NewST7')
        _type = body.find_element(By.ID, 'sched_frm_type_date')
        _type.click()
        date_input = body.find_element(By.ID, 'sched_frm_date')
        assert date_input.is_displayed()
        # BEGIN select the 15th of this month from the popup
        dnow = dtnow()
        expected_date = date(year=dnow.year, month=dnow.month, day=15)
        date_input.click()
        date_number = body.find_element(By.XPATH,
                                        '//td[@class="day" and text()="15"]'
                                        )
        date_number.click()
        # END date chooser popup
        assert date_input.get_attribute(
            'value') == expected_date.strftime('%Y-%m-%d')
        amt = body.find_element(By.ID, 'sched_frm_amount')
        amt.send_keys('123.45')
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        acct_sel.select_by_value('1')
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        budget_sel.select_by_value('1')
        is_active = selenium.find_element(By.ID, 'sched_frm_active')
        assert is_active.is_selected()
        notes = body.find_element(By.ID, 'sched_frm_notes')
        notes.send_keys('foo bar baz')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved ScheduledTransaction 7 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that updated budget was removed from the page
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = [y[4] for y in self.tbody2textlist(table)]
        assert 'NewST7' in texts

    def test_13_add_date_verify_db(self, testdb):
        t = testdb.query(ScheduledTransaction).get(7)
        assert t is not None
        assert t.description == 'NewST7'
        assert t.num_per_period is None
        dnow = dtnow()
        assert t.date == date(year=dnow.year, month=dnow.month, day=15)
        assert t.day_of_month is None
        assert t.amount == Decimal('123.45')
        assert t.account_id == 1
        assert t.budget_id == 1
        assert t.notes == 'foo bar baz'
        assert t.is_active is True

    def test_21_add_monthly_modal_on_click(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.ID, 'btn_add_sched')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Scheduled Transaction'
        desc = body.find_element(By.ID, 'sched_frm_description')
        desc.send_keys('NewST8Monthly')
        _type = body.find_element(By.ID, 'sched_frm_type_monthly')
        _type.click()
        day_input = body.find_element(By.ID, 'sched_frm_day_of_month')
        assert day_input.is_displayed()
        day_input.send_keys('4')
        amt = body.find_element(By.ID, 'sched_frm_amount')
        amt.send_keys('123.45')
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        acct_sel.select_by_value('2')
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        budget_sel.select_by_value('2')
        is_active = selenium.find_element(By.ID, 'sched_frm_active')
        assert is_active.is_selected()
        notes = body.find_element(By.ID, 'sched_frm_notes')
        notes.send_keys('foo bar baz')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved ScheduledTransaction 8 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that updated budget was removed from the page
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = [y[4] for y in self.tbody2textlist(table)]
        assert 'NewST8Monthly' in texts

    def test_23_add_monthly_verify_db(self, testdb):
        t = testdb.query(ScheduledTransaction).get(8)
        assert t is not None
        assert t.description == 'NewST8Monthly'
        assert t.num_per_period is None
        assert t.date is None
        assert t.day_of_month == 4
        assert t.amount == Decimal('123.45')
        assert t.account_id == 2
        assert t.budget_id == 2
        assert t.notes == 'foo bar baz'
        assert t.is_active is True

    def test_31_add_per_period_modal_on_click(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.ID, 'btn_add_sched')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Scheduled Transaction'
        desc = body.find_element(By.ID, 'sched_frm_description')
        desc.send_keys('NewST9PerPeriod')
        _type = body.find_element(By.ID, 'sched_frm_type_per_period')
        _type.click()
        date_input = body.find_element(By.ID, 'sched_frm_num_per_period')
        assert date_input.is_displayed()
        date_input.send_keys('2')
        amt = body.find_element(By.ID, 'sched_frm_amount')
        amt.send_keys('123.45')
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        acct_sel.select_by_value('1')
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        budget_sel.select_by_value('1')
        is_active = selenium.find_element(By.ID, 'sched_frm_active')
        assert is_active.is_selected()
        notes = body.find_element(By.ID, 'sched_frm_notes')
        notes.send_keys('foo bar baz')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved ScheduledTransaction 9 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that updated budget was removed from the page
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = [y[4] for y in self.tbody2textlist(table)]
        assert 'NewST9PerPeriod' in texts

    def test_33_add_per_period_verify_db(self, testdb):
        t = testdb.query(ScheduledTransaction).get(9)
        assert t is not None
        assert t.description == 'NewST9PerPeriod'
        assert t.num_per_period == 2
        assert t.date is None
        assert t.day_of_month is None
        assert t.amount == Decimal('123.45')
        assert t.account_id == 1
        assert t.budget_id == 1
        assert t.notes == 'foo bar baz'
        assert t.is_active is True

    def test_41_add_income_modal_on_click(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.ID, 'btn_add_sched')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Scheduled Transaction'
        desc = body.find_element(By.ID, 'sched_frm_description')
        desc.send_keys('NewST10PerPeriod')
        _type = body.find_element(By.ID, 'sched_frm_type_per_period')
        _type.click()
        date_input = body.find_element(By.ID, 'sched_frm_num_per_period')
        assert date_input.is_displayed()
        date_input.send_keys('1')
        amt = body.find_element(By.ID, 'sched_frm_amount')
        amt.send_keys('123.45')
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        assert acct_sel.first_selected_option.get_attribute('value') == '1'
        acct_sel.select_by_value('1')
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        budget_sel.select_by_value('7')
        is_active = selenium.find_element(By.ID, 'sched_frm_active')
        assert is_active.is_selected()
        notes = body.find_element(By.ID, 'sched_frm_notes')
        notes.send_keys('foo bar baz')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved ScheduledTransaction 10 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that updated budget was removed from the page
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = [y[4] for y in self.tbody2textlist(table)]
        assert 'NewST10PerPeriod' in texts

    def test_43_add_income_verify_db(self, testdb):
        t = testdb.query(ScheduledTransaction).get(10)
        assert t is not None
        assert t.description == 'NewST10PerPeriod'
        assert t.num_per_period == 1
        assert t.date is None
        assert t.day_of_month is None
        assert t.amount == Decimal('123.45')
        assert t.account_id == 1
        assert t.budget_id == 7
        assert t.notes == 'foo bar baz'
        assert t.is_active is True

    def test_44_add_income_table(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = self.tbody2textlist(table)
        elems = self.tbody2elemlist(table)
        assert texts[1] == [
            'yes',
            'per period',
            '1 per period',
            '$123.45',
            'NewST10PerPeriod',
            'BankOne (1)',
            'Income (income) (7)'
        ]
        assert elems[1][4].get_attribute('innerHTML') == '' \
            '<a href="javascript:schedModal(10, mytable)">NewST10PerPeriod</a>'
        assert elems[1][5].get_attribute('innerHTML') == '' \
            '<a href="/accounts/1">BankOne (1)</a>'
        assert elems[1][6].get_attribute('innerHTML') == '' \
            '<a href="/budgets/7">Income (income) (7)</a>'

    def test_50_sales_tax_verify_db(self, testdb):
        """Verify initial sales_tax values in database"""
        t = testdb.query(ScheduledTransaction).get(1)
        assert t is not None
        assert t.description == 'ST1'
        assert t.sales_tax == Decimal('1.23')

    def test_51_sales_tax_edit_modal(self, base_url, selenium):
        """Test editing sales_tax value in modal"""
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled/1')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Scheduled Transaction 1'
        # verify sales_tax field is present and populated
        sales_tax_elem = body.find_element(By.ID, 'sched_frm_sales_tax')
        assert sales_tax_elem.get_attribute('value') == '1.23'
        # change sales_tax value
        sales_tax_elem.clear()
        sales_tax_elem.send_keys('9.87')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved ScheduledTransaction 1 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)

    def test_52_sales_tax_verify_db_after_edit(self, testdb):
        """Verify sales_tax was updated in database"""
        t = testdb.query(ScheduledTransaction).get(1)
        assert t is not None
        assert t.description == 'ST1'
        assert t.sales_tax == Decimal('9.87')

    def test_53_sales_tax_add_with_sales_tax(self, base_url, selenium):
        """Test adding new scheduled transaction with sales_tax"""
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.ID, 'btn_add_sched')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Scheduled Transaction'
        desc = body.find_element(By.ID, 'sched_frm_description')
        desc.send_keys('NewSTWithSalesTax')
        _type = body.find_element(By.ID, 'sched_frm_type_monthly')
        _type.click()
        dom = body.find_element(By.ID, 'sched_frm_day_of_month')
        dom.send_keys('15')
        amt = body.find_element(By.ID, 'sched_frm_amount')
        amt.send_keys('250.00')
        sales_tax = body.find_element(By.ID, 'sched_frm_sales_tax')
        sales_tax.send_keys('12.50')
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        acct_sel.select_by_value('1')
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        budget_sel.select_by_value('1')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved ScheduledTransaction 11 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)

    def test_54_sales_tax_verify_db_after_add(self, testdb):
        """Verify new scheduled transaction with sales_tax in database"""
        t = testdb.query(ScheduledTransaction).get(11)
        assert t is not None
        assert t.description == 'NewSTWithSalesTax'
        assert t.amount == Decimal('250.00')
        assert t.sales_tax == Decimal('12.50')
        assert t.day_of_month == 15

    def test_60_add_weekly_modal_on_click(self, base_url, selenium):
        """Test adding a new weekly scheduled transaction via modal"""
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.ID, 'btn_add_sched')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Scheduled Transaction'
        desc = body.find_element(By.ID, 'sched_frm_description')
        desc.send_keys('NewWeeklyTest')
        _type = body.find_element(By.ID, 'sched_frm_type_weekly')
        _type.click()
        day_of_week_sel = Select(body.find_element(By.ID, 'sched_frm_day_of_week'))
        assert day_of_week_sel.first_selected_option.text == 'Monday'
        day_of_week_sel.select_by_value('2')  # Wednesday
        amt = body.find_element(By.ID, 'sched_frm_amount')
        amt.send_keys('75.50')
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        acct_sel.select_by_value('1')
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        budget_sel.select_by_value('1')
        notes = body.find_element(By.ID, 'sched_frm_notes')
        notes.send_keys('weekly test notes')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert 'Successfully saved ScheduledTransaction' in x.text.strip()
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that the new transaction appears in the table
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = [y[4] for y in self.tbody2textlist(table)]
        assert 'NewWeeklyTest' in texts

    def test_61_add_weekly_verify_db(self, testdb):
        """Verify new weekly scheduled transaction in database"""
        t = testdb.query(ScheduledTransaction).filter(
            ScheduledTransaction.description == 'NewWeeklyTest'
        ).first()
        assert t is not None
        assert t.description == 'NewWeeklyTest'
        assert t.num_per_period is None
        assert t.date is None
        assert t.day_of_month is None
        assert t.day_of_week == 2  # Wednesday
        assert t.annual_month is None
        assert t.annual_day is None
        assert t.amount == Decimal('75.50')
        assert t.account_id == 1
        assert t.budget_id == 1
        assert t.notes == 'weekly test notes'
        assert t.is_active is True

    def test_70_add_annual_modal_on_click(self, base_url, selenium):
        """Test adding a new annual scheduled transaction via modal"""
        self.baseurl = base_url
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.ID, 'btn_add_sched')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Scheduled Transaction'
        desc = body.find_element(By.ID, 'sched_frm_description')
        desc.send_keys('NewAnnualTest')
        _type = body.find_element(By.ID, 'sched_frm_type_annual')
        _type.click()
        month_sel = Select(body.find_element(By.ID, 'sched_frm_annual_month'))
        month_sel.select_by_value('7')  # July
        day_input = body.find_element(By.ID, 'sched_frm_annual_day')
        day_input.send_keys('4')  # July 4th
        amt = body.find_element(By.ID, 'sched_frm_amount')
        amt.send_keys('500.00')
        acct_sel = Select(body.find_element(By.ID, 'sched_frm_account'))
        acct_sel.select_by_value('2')
        budget_sel = Select(body.find_element(By.ID, 'sched_frm_budget'))
        budget_sel.select_by_value('4')
        notes = body.find_element(By.ID, 'sched_frm_notes')
        notes.send_keys('annual test notes')
        # submit the form
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert 'Successfully saved ScheduledTransaction' in x.text.strip()
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that the new transaction appears in the table
        table = selenium.find_element(By.ID, 'table-scheduled-txn')
        texts = [y[4] for y in self.tbody2textlist(table)]
        assert 'NewAnnualTest' in texts

    def test_71_add_annual_verify_db(self, testdb):
        """Verify new annual scheduled transaction in database"""
        t = testdb.query(ScheduledTransaction).filter(
            ScheduledTransaction.description == 'NewAnnualTest'
        ).first()
        assert t is not None
        assert t.description == 'NewAnnualTest'
        assert t.num_per_period is None
        assert t.date is None
        assert t.day_of_month is None
        assert t.day_of_week is None
        assert t.annual_month == 7  # July
        assert t.annual_day == 4
        assert t.amount == Decimal('500.00')
        assert t.account_id == 2
        assert t.budget_id == 4
        assert t.notes == 'annual test notes'
        assert t.is_active is True


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestSchedTransWeekly(AcceptanceHelper):
    """Test viewing weekly scheduled transactions via modal"""

    def test_0_create_weekly(self, testdb):
        """Create a weekly scheduled transaction for testing"""
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(1)
        st = ScheduledTransaction(
            account=acct,
            budget=budget,
            amount=Decimal('77.77'),
            day_of_week=0,  # Monday
            description='TestWeekly',
            is_active=False
        )
        testdb.add(st)
        testdb.flush()
        testdb.commit()
        self.weekly_id = st.id

    def test_1_verify_db(self, testdb):
        """Verify the weekly transaction was created"""
        t = testdb.query(ScheduledTransaction).filter(
            ScheduledTransaction.description == 'TestWeekly'
        ).first()
        assert t is not None
        assert t.day_of_week == 0  # Monday
        assert t.amount == Decimal('77.77')
        assert t.is_active is False

    def test_2_modal_on_click(self, base_url, selenium, testdb):
        """Test that clicking a weekly transaction opens the modal correctly"""
        self.baseurl = base_url
        t = testdb.query(ScheduledTransaction).filter(
            ScheduledTransaction.description == 'TestWeekly'
        ).first()
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.XPATH, '//a[text()="TestWeekly"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == f'Edit Scheduled Transaction {t.id}'
        assert body.find_element(By.ID,
                                 'sched_frm_id').get_attribute('value') == str(t.id)
        assert body.find_element(By.ID,
                                 'sched_frm_description').get_attribute(
                                     'value') == 'TestWeekly'
        assert body.find_element(By.ID,
                                 'sched_frm_type_weekly').is_selected()
        day_of_week_sel = Select(body.find_element(By.ID,
                                                   'sched_frm_day_of_week'))
        assert day_of_week_sel.first_selected_option.get_attribute(
            'value') == '0'
        assert day_of_week_sel.first_selected_option.text == 'Monday'
        assert body.find_element(By.ID,
                                 'sched_frm_amount').get_attribute(
                                     'value') == '77.77'
        assert not selenium.find_element(
            By.ID, 'sched_frm_active').is_selected()


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestSchedTransAnnual(AcceptanceHelper):
    """Test viewing annual scheduled transactions via modal"""

    def test_0_create_annual(self, testdb):
        """Create an annual scheduled transaction for testing"""
        acct = testdb.query(Account).get(1)
        budget = testdb.query(Budget).get(2)
        st = ScheduledTransaction(
            account=acct,
            budget=budget,
            amount=Decimal('99.99'),
            annual_month=4,  # April
            annual_day=15,
            description='TestAnnual',
            is_active=False
        )
        testdb.add(st)
        testdb.flush()
        testdb.commit()
        self.annual_id = st.id

    def test_1_verify_db(self, testdb):
        """Verify the annual transaction was created"""
        t = testdb.query(ScheduledTransaction).filter(
            ScheduledTransaction.description == 'TestAnnual'
        ).first()
        assert t is not None
        assert t.annual_month == 4  # April
        assert t.annual_day == 15
        assert t.amount == Decimal('99.99')
        assert t.is_active is False

    def test_2_modal_on_click(self, base_url, selenium, testdb):
        """Test that clicking an annual transaction opens the modal correctly"""
        self.baseurl = base_url
        t = testdb.query(ScheduledTransaction).filter(
            ScheduledTransaction.description == 'TestAnnual'
        ).first()
        self.get(selenium, base_url + '/scheduled')
        link = selenium.find_element(By.XPATH, '//a[text()="TestAnnual"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == f'Edit Scheduled Transaction {t.id}'
        assert body.find_element(By.ID,
                                 'sched_frm_id').get_attribute('value') == str(t.id)
        assert body.find_element(By.ID,
                                 'sched_frm_description').get_attribute(
                                     'value') == 'TestAnnual'
        assert body.find_element(By.ID,
                                 'sched_frm_type_annual').is_selected()
        month_sel = Select(body.find_element(By.ID, 'sched_frm_annual_month'))
        assert month_sel.first_selected_option.get_attribute('value') == '4'
        assert month_sel.first_selected_option.text == 'April'
        assert body.find_element(By.ID,
                                 'sched_frm_annual_day').get_attribute(
                                     'value') == '15'
        assert body.find_element(By.ID,
                                 'sched_frm_amount').get_attribute(
                                     'value') == '99.99'
        assert not selenium.find_element(
            By.ID, 'sched_frm_active').is_selected()
