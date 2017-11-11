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

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.txn_reconcile import TxnReconcile
from selenium.webdriver.support.ui import Select
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.utils import dtnow


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestBudgets(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/budgets')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'Budgets - BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element_by_id('side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_notifications(self, selenium):
        div = selenium.find_element_by_id('notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'

    def test_initial_data(self, selenium):
        ptable = selenium.find_element_by_id('table-periodic-budgets')
        ptexts = self.tbody2textlist(ptable)
        stable = selenium.find_element_by_id('table-standing-budgets')
        stexts = self.tbody2textlist(stable)
        assert ptexts == [
            ['yes', 'Income (7) (income)', '$2,345.67'],
            ['yes', 'Periodic1 (1)', '$100.00'],
            ['yes', 'Periodic2 (2)', '$234.00'],
            ['NO', 'Periodic3 Inactive (3)', '$10.23']
        ]
        assert stexts == [
            ['yes', 'Standing1 (4)', '$1,284.23'],
            ['yes', 'Standing2 (5)', '$9,482.29'],
            ['NO', 'Standing3 Inactive (6)', '-$92.29']
        ]
        pelems = self.tbody2elemlist(ptable)
        selems = self.tbody2elemlist(stable)
        assert pelems[2][1].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(2, null)">' \
                            'Periodic2 (2)</a>'
        assert pelems[0][1].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(7, null)">' \
                            'Income (7)</a> <em class="text-success">' \
                            '(income)</em>'
        assert selems[0][1].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(4, null)">' \
                            'Standing1 (4)</a>'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestBudgetModals(AcceptanceHelper):

    def test_00_budget_modal_verify_db(self, testdb):
        b = testdb.query(Budget).get(1)
        assert b is not None
        assert b.name == 'Periodic1'
        assert b.is_periodic is True
        assert b.description == 'P1desc'
        assert b.starting_balance == 100.00
        assert b.is_active is True
        assert b.is_income is False
        assert b.omit_from_graphs is False

    def test_01_budget_modal_populate_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath('//a[text()="Periodic1 (1)"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Budget 1'
        assert selenium.find_element_by_id('budget_frm_name').get_attribute(
            'value') == 'Periodic1'
        assert selenium.find_element_by_id(
            'budget_frm_type_periodic').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_type_standing').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_description').get_attribute('value') == 'P1desc'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance').get_attribute('value') == '100'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance_group').is_displayed()
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_current_balance_group').is_displayed() is False
        assert selenium.find_element_by_id('budget_frm_active').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False

    def test_02_budget_modal_update_modal(self, base_url, selenium):
        # Fill in the form
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath('//a[text()="Periodic1 (1)"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        name = selenium.find_element_by_id('budget_frm_name')
        name.clear()
        name.send_keys('EditedPeriodic1')
        desc = selenium.find_element_by_id('budget_frm_description')
        desc.clear()
        desc.send_keys('EditedP1desc')
        sb = selenium.find_element_by_id('budget_frm_starting_balance')
        assert sb.is_displayed()
        sb.clear()
        sb.send_keys('2345.67')
        selenium.find_element_by_id('budget_frm_active').click()
        assert selenium.find_element_by_id(
            'budget_frm_active').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Budget 1 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-periodic-budgets')
        # test that updated budget was removed from the page
        ptable = selenium.find_element_by_id('table-periodic-budgets')
        pelems = self.tbody2elemlist(ptable)
        assert pelems[0][1].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(1, null)">' \
                            'EditedPeriodic1 (1)</a>'

    def test_03_budget_modal_verify_db(self, testdb):
        b = testdb.query(Budget).get(1)
        assert b is not None
        assert b.name == 'EditedPeriodic1'
        assert b.is_periodic is True
        assert b.description == 'EditedP1desc'
        assert float(b.starting_balance) == 2345.6700
        assert b.is_active is False
        assert b.is_income is False
        assert b.omit_from_graphs is False

    def test_10_populate_edit_periodic_2_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath('//a[text()="Periodic2 (2)"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Budget 2'
        assert selenium.find_element_by_id('budget_frm_name').get_attribute(
            'value') == 'Periodic2'
        assert selenium.find_element_by_id(
            'budget_frm_type_periodic').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_type_standing').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_description').get_attribute('value') == 'P2desc'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance').get_attribute('value') == '234'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance_group').is_displayed()
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_current_balance_group').is_displayed() is False
        assert selenium.find_element_by_id('budget_frm_active').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False

    def test_11_populate_edit_periodic_3_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath(
            '//a[text()="Periodic3 Inactive (3)"]'
        )
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Budget 3'
        assert selenium.find_element_by_id('budget_frm_name').get_attribute(
            'value') == 'Periodic3 Inactive'
        assert selenium.find_element_by_id(
            'budget_frm_type_periodic').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_type_standing').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_description').get_attribute('value') == 'P3desc'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance').get_attribute('value') == '10.23'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance_group').is_displayed()
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_current_balance_group').is_displayed() is False
        assert selenium.find_element_by_id(
            'budget_frm_active').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False

    def test_12_populate_edit_standing_1_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath('//a[text()="Standing1 (4)"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Budget 4'
        assert selenium.find_element_by_id('budget_frm_name').get_attribute(
            'value') == 'Standing1'
        assert selenium.find_element_by_id(
            'budget_frm_type_periodic').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_type_standing').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_description').get_attribute('value') == 'S1desc'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance_group').is_displayed() is False
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == '1284.23'
        assert selenium.find_element_by_id(
            'budget_frm_current_balance_group').is_displayed()
        assert selenium.find_element_by_id('budget_frm_active').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is True

    def test_13_populate_edit_standing_2_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath('//a[text()="Standing2 (5)"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Budget 5'
        assert selenium.find_element_by_id('budget_frm_name').get_attribute(
            'value') == 'Standing2'
        assert selenium.find_element_by_id(
            'budget_frm_type_periodic').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_type_standing').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_description').get_attribute('value') == 'S2desc'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance_group').is_displayed() is False
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == '9482.29'
        assert selenium.find_element_by_id(
            'budget_frm_current_balance_group').is_displayed()
        assert selenium.find_element_by_id('budget_frm_active').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False

    def test_14_populate_edit_standing_3_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath(
            '//a[text()="Standing3 Inactive (6)"]'
        )
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Budget 6'
        assert selenium.find_element_by_id('budget_frm_name').get_attribute(
            'value') == 'Standing3 Inactive'
        assert selenium.find_element_by_id(
            'budget_frm_type_periodic').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_type_standing').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_description').get_attribute('value') == 'S3desc'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance_group').is_displayed() is False
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == '-92.29'
        assert selenium.find_element_by_id(
            'budget_frm_current_balance_group').is_displayed()
        assert selenium.find_element_by_id(
            'budget_frm_active').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False

    def test_20_income_verify_db(self, testdb):
        b = testdb.query(Budget).get(7)
        assert b is not None
        assert b.name == 'Income'
        assert b.is_periodic is True
        assert b.description == 'IncomeDesc'
        assert float(b.starting_balance) == 2345.67
        assert b.is_active is True
        assert b.is_income is True
        assert b.omit_from_graphs is True

    def test_21_populate_income_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath('//a[text()="Income (7)"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Budget 7'
        assert selenium.find_element_by_id('budget_frm_name').get_attribute(
            'value') == 'Income'
        assert selenium.find_element_by_id(
            'budget_frm_type_periodic').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_type_standing').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_description').get_attribute('value') == 'IncomeDesc'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance').get_attribute('value') == '2345.67'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance_group').is_displayed()
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_current_balance_group').is_displayed() is False
        assert selenium.find_element_by_id('budget_frm_active').is_selected()
        assert selenium.find_element_by_id('budget_frm_income').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is True

    def test_22_update_income_modal(self, base_url, selenium):
        # Fill in the form
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_xpath('//a[text()="Income (7)"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        name = selenium.find_element_by_id('budget_frm_name')
        name.clear()
        name.send_keys('EditedIncome')
        desc = selenium.find_element_by_id('budget_frm_description')
        desc.send_keys('edited')
        sb = selenium.find_element_by_id('budget_frm_starting_balance')
        assert sb.is_displayed()
        sb.clear()
        sb.send_keys('123.45')
        selenium.find_element_by_id('budget_frm_active').click()
        assert selenium.find_element_by_id(
            'budget_frm_active').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is True
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is True
        selenium.find_element_by_id('budget_frm_omit_from_graphs').click()
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Budget 7 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-periodic-budgets')
        # test that updated budget was removed from the page
        ptable = selenium.find_element_by_id('table-periodic-budgets')
        pelems = self.tbody2elemlist(ptable)
        assert pelems[0][1].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(7, null)">' \
                            'EditedIncome (7)</a> ' \
                            '<em class="text-success">(income)</em>'

    def test_23_verify_income_db(self, testdb):
        b = testdb.query(Budget).get(7)
        assert b is not None
        assert b.name == 'EditedIncome'
        assert b.is_periodic is True
        assert b.description == 'IncomeDescedited'
        assert float(b.starting_balance) == 123.45
        assert b.is_active is False
        assert b.is_income is True
        assert b.omit_from_graphs is False

    def test_31_populate_direct_url_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets/1')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Budget 1'
        assert selenium.find_element_by_id('budget_frm_name').get_attribute(
            'value') == 'EditedPeriodic1'
        assert selenium.find_element_by_id(
            'budget_frm_type_periodic').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_type_standing').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_description').get_attribute('value') == 'EditedP1desc'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance').get_attribute('value') == '2345.67'
        assert selenium.find_element_by_id(
            'budget_frm_starting_balance_group').is_displayed()
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_current_balance_group').is_displayed() is False
        assert selenium.find_element_by_id(
            'budget_frm_active').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False

    def test_41_add_standing_modal(self, base_url, selenium):
        # Fill in the form
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_id('btn_add_budget')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        name = selenium.find_element_by_id('budget_frm_name')
        name.clear()
        name.send_keys('NewStanding')
        standing = selenium.find_element_by_id('budget_frm_type_standing')
        standing.click()
        desc = selenium.find_element_by_id('budget_frm_description')
        desc.clear()
        desc.send_keys('Newly Added Standing')
        sb = selenium.find_element_by_id('budget_frm_current_balance')
        assert sb.is_displayed()
        sb.clear()
        sb.send_keys('6789.12')
        assert selenium.find_element_by_id(
            'budget_frm_active').is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_income').is_selected() is False
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Budget 8 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-periodic-budgets')
        # test that updated budget was removed from the page
        stable = selenium.find_element_by_id('table-standing-budgets')
        selems = self.tbody2elemlist(stable)
        assert selems[0][1].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(8, null)">' \
                            'NewStanding (8)</a>'

    def test_41_add_standing_verify_db(self, testdb):
        b = testdb.query(Budget).get(8)
        assert b is not None
        assert b.name == 'NewStanding'
        assert b.is_periodic is False
        assert b.description == 'Newly Added Standing'
        assert float(b.current_balance) == 6789.12
        assert b.is_active is True
        assert b.is_income is False
        assert b.omit_from_graphs is False

    def test_51_add_income_modal(self, base_url, selenium):
        # Fill in the form
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element_by_id('btn_add_budget')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        name = selenium.find_element_by_id('budget_frm_name')
        name.clear()
        name.send_keys('NewIncome')
        periodic = selenium.find_element_by_id('budget_frm_type_periodic')
        periodic.click()
        desc = selenium.find_element_by_id('budget_frm_description')
        desc.clear()
        desc.send_keys('Newly Added Income')
        sb = selenium.find_element_by_id('budget_frm_starting_balance')
        assert sb.is_displayed()
        sb.clear()
        sb.send_keys('123.45')
        assert selenium.find_element_by_id(
            'budget_frm_active').is_selected()
        income = selenium.find_element_by_id('budget_frm_income')
        income.click()
        assert income.is_selected()
        assert selenium.find_element_by_id(
            'budget_frm_omit_from_graphs').is_selected() is False
        selenium.find_element_by_id('budget_frm_omit_from_graphs').click()
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Budget 9 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-periodic-budgets')
        # test that updated budget was removed from the page
        stable = selenium.find_element_by_id('table-periodic-budgets')
        selems = self.tbody2elemlist(stable)
        assert selems[2][1].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(9, null)">' \
                            'NewIncome (9)</a> <em class="text-success">' \
                            '(income)</em>'

    def test_52_add_income_verify_db(self, testdb):
        b = testdb.query(Budget).get(9)
        assert b is not None
        assert b.name == 'NewIncome'
        assert b.is_periodic is True
        assert b.description == 'Newly Added Income'
        assert float(b.starting_balance) == 123.45
        assert b.is_active is True
        assert b.is_income is True
        assert b.omit_from_graphs is True


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestBudgetTransfer(AcceptanceHelper):

    def test_1_verify_db(self, testdb):
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 3
        max_r = max([
            t.id for t in testdb.query(TxnReconcile).all()
        ])
        assert max_r == 1

    def test_2_transfer_modal(self, base_url, selenium):
        # Fill in the form
        self.get(selenium, base_url + '/budgets')
        # test that updated budget was removed from the page
        stable = selenium.find_element_by_id('table-standing-budgets')
        stexts = self.tbody2textlist(stable)
        assert stexts[1] == ['yes', 'Standing2 (5)', '$9,482.29']
        ptable = selenium.find_element_by_id('table-periodic-budgets')
        ptexts = self.tbody2textlist(ptable)
        assert ptexts[2] == ['yes', 'Periodic2 (2)', '$234.00']
        link = selenium.find_element_by_id('btn_budget_txfr')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Budget Transfer'
        assert body.find_element_by_id(
            'budg_txfr_frm_date').get_attribute('value') == dtnow(
            ).strftime('%Y-%m-%d')
        amt = body.find_element_by_id('budg_txfr_frm_amount')
        amt.clear()
        amt.send_keys('123.45')
        acct_sel = Select(body.find_element_by_id('budg_txfr_frm_account'))
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
        from_budget_sel = Select(
            body.find_element_by_id('budg_txfr_frm_from_budget')
        )
        opts = []
        for o in from_budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['3', 'Periodic3 Inactive'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['6', 'Standing3 Inactive'],
            ['7', 'Income (i)']
        ]
        assert from_budget_sel.first_selected_option.get_attribute(
            'value') == 'None'
        from_budget_sel.select_by_value('2')
        to_budget_sel = Select(
            body.find_element_by_id('budg_txfr_frm_to_budget')
        )
        opts = []
        for o in from_budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['3', 'Periodic3 Inactive'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['6', 'Standing3 Inactive'],
            ['7', 'Income (i)']
        ]
        assert to_budget_sel.first_selected_option.get_attribute(
            'value') == 'None'
        to_budget_sel.select_by_value('5')
        notes = selenium.find_element_by_id('budg_txfr_frm_notes')
        notes.clear()
        notes.send_keys('Budget Transfer Notes')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transactions 4 and 5' \
                                 ' in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-standing-budgets')
        # test that updated budget was removed from the page
        stable = selenium.find_element_by_id('table-standing-budgets')
        stexts = self.tbody2textlist(stable)
        assert stexts[1] == ['yes', 'Standing2 (5)', '$9,605.74']
        ptable = selenium.find_element_by_id('table-periodic-budgets')
        ptexts = self.tbody2textlist(ptable)
        assert ptexts[2] == ['yes', 'Periodic2 (2)', '$234.00']

    def test_3_verify_db(self, testdb):
        desc = 'Budget Transfer - 123.45 from Periodic2 (2) to Standing2 (5)'
        t1 = testdb.query(Transaction).get(4)
        assert t1.date == dtnow().date()
        assert float(t1.actual_amount) == 123.45
        assert float(t1.budgeted_amount) == 123.45
        assert t1.description == desc
        assert t1.notes == 'Budget Transfer Notes'
        assert t1.account_id == 1
        assert t1.scheduled_trans_id is None
        assert t1.budget_id == 2
        rec1 = testdb.query(TxnReconcile).get(2)
        assert rec1.txn_id == 4
        assert rec1.ofx_fitid is None
        assert rec1.ofx_account_id is None
        assert rec1.note == desc
        t2 = testdb.query(Transaction).get(5)
        assert t2.date == dtnow().date()
        assert float(t2.actual_amount) == -123.45
        assert float(t2.budgeted_amount) == -123.45
        assert t2.description == desc
        assert t2.notes == 'Budget Transfer Notes'
        assert t2.account_id == 1
        assert t2.scheduled_trans_id is None
        assert t2.budget_id == 5
        rec2 = testdb.query(TxnReconcile).get(3)
        assert rec2.txn_id == 5
        assert rec2.ofx_fitid is None
        assert rec2.ofx_account_id is None
        assert rec2.note == desc


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestBudgetTransferStoP(AcceptanceHelper):

    def test_1_verify_db(self, testdb):
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 3
        max_r = max([
            t.id for t in testdb.query(TxnReconcile).all()
        ])
        assert max_r == 1

    def test_2_transfer_modal(self, base_url, selenium, testdb):
        # Fill in the form
        self.get(selenium, base_url + '/budgets')
        # test that updated budget was removed from the page
        stable = selenium.find_element_by_id('table-standing-budgets')
        stexts = self.tbody2textlist(stable)
        assert stexts[1] == ['yes', 'Standing2 (5)', '$9,482.29']
        ptable = selenium.find_element_by_id('table-periodic-budgets')
        ptexts = self.tbody2textlist(ptable)
        assert ptexts[2] == ['yes', 'Periodic2 (2)', '$234.00']
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), testdb)
        assert float(pp.budget_sums[2]['allocated']) == 222.22
        assert float(pp.budget_sums[2]['budget_amount']) == 234.0
        assert "%.2f" % float(pp.budget_sums[2]['remaining']) == '11.78'
        assert float(pp.budget_sums[2]['spent']) == 222.22
        assert float(pp.budget_sums[2]['trans_total']) == 222.22
        link = selenium.find_element_by_id('btn_budget_txfr')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Budget Transfer'
        assert body.find_element_by_id(
            'budg_txfr_frm_date').get_attribute('value') == dtnow(
            ).strftime('%Y-%m-%d')
        amt = body.find_element_by_id('budg_txfr_frm_amount')
        amt.clear()
        amt.send_keys('123.45')
        acct_sel = Select(body.find_element_by_id('budg_txfr_frm_account'))
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
        from_budget_sel = Select(
            body.find_element_by_id('budg_txfr_frm_from_budget')
        )
        opts = []
        for o in from_budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['3', 'Periodic3 Inactive'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['6', 'Standing3 Inactive'],
            ['7', 'Income (i)']
        ]
        assert from_budget_sel.first_selected_option.get_attribute(
            'value') == 'None'
        from_budget_sel.select_by_value('5')
        to_budget_sel = Select(
            body.find_element_by_id('budg_txfr_frm_to_budget')
        )
        opts = []
        for o in from_budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['3', 'Periodic3 Inactive'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['6', 'Standing3 Inactive'],
            ['7', 'Income (i)']
        ]
        assert to_budget_sel.first_selected_option.get_attribute(
            'value') == 'None'
        to_budget_sel.select_by_value('2')
        notes = selenium.find_element_by_id('budg_txfr_frm_notes')
        notes.clear()
        notes.send_keys('Budget Transfer Notes')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transactions 4 and 5' \
                                 ' in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-standing-budgets')
        # test that updated budget was removed from the page
        stable = selenium.find_element_by_id('table-standing-budgets')
        stexts = self.tbody2textlist(stable)
        assert stexts[1] == ['yes', 'Standing2 (5)', '$9,358.84']
        ptable = selenium.find_element_by_id('table-periodic-budgets')
        ptexts = self.tbody2textlist(ptable)
        assert ptexts[2] == ['yes', 'Periodic2 (2)', '$234.00']

    def test_3_verify_db(self, testdb):
        d = dtnow().date()
        pp = BiweeklyPayPeriod.period_for_date(d, testdb)
        print('Found period for %s: %s' % (d, pp))
        assert float(pp.budget_sums[2]['allocated']) == 98.77
        assert float(pp.budget_sums[2]['budget_amount']) == 234.0
        # ugh, floating point issues...
        assert "%.2f" % pp.budget_sums[2]['remaining'] == '135.23'
        assert float(pp.budget_sums[2]['spent']) == 98.77
        assert float(pp.budget_sums[2]['trans_total']) == 98.77
        desc = 'Budget Transfer - 123.45 from Standing2 (5) to Periodic2 (2)'
        t1 = testdb.query(Transaction).get(4)
        assert t1.date == dtnow().date()
        assert float(t1.actual_amount) == 123.45
        assert float(t1.budgeted_amount) == 123.45
        assert t1.description == desc
        assert t1.notes == 'Budget Transfer Notes'
        assert t1.account_id == 1
        assert t1.scheduled_trans_id is None
        assert t1.budget_id == 5
        rec1 = testdb.query(TxnReconcile).get(2)
        assert rec1.txn_id == 4
        assert rec1.ofx_fitid is None
        assert rec1.ofx_account_id is None
        assert rec1.note == desc
        t2 = testdb.query(Transaction).get(5)
        assert t2.date == dtnow().date()
        assert float(t2.actual_amount) == -123.45
        assert float(t2.budgeted_amount) == -123.45
        assert t2.description == desc
        assert t2.notes == 'Budget Transfer Notes'
        assert t2.account_id == 1
        assert t2.scheduled_trans_id is None
        assert t2.budget_id == 2
        rec2 = testdb.query(TxnReconcile).get(3)
        assert rec2.txn_id == 5
        assert rec2.ofx_fitid is None
        assert rec2.ofx_account_id is None
        assert rec2.note == desc
