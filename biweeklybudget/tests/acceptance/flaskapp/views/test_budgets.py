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
from selenium.webdriver.support.ui import Select

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper


@pytest.mark.acceptance
class TestBudgets(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, testdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url + '/budgets')

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
            ['Periodic1 (1)', '$100.00', ''],
            ['Periodic2 (2)', '$234.00', 'BankOne (1)']
        ]
        assert stexts == [
            ['Standing1 (4)', '$1,284.23', 'BankTwoStale (2)'],
            ['Standing2 (5)', '$9,482.29', '']
        ]
        pelems = self.tbody2elemlist(ptable)
        selems = self.tbody2elemlist(stable)
        assert pelems[1][0].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(2)">' \
                            'Periodic2 (2)</a>'
        assert pelems[1][2].get_attribute(
            'innerHTML') == '<a href="/accounts/1">BankOne (1)</a>'
        assert selems[0][0].get_attribute(
            'innerHTML') == '<a href="javascript:budgetModal(4)">' \
                            'Standing1 (4)</a>'
        assert selems[0][2].get_attribute(
            'innerHTML') == '<a href="/accounts/2">BankTwoStale (2)</a>'


@pytest.mark.acceptance
class TestEditPeriodic1(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, testdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url + '/budgets')

    def test_1_populate_modal(self, selenium):
        link = selenium.find_element_by_xpath('//a[text()="Periodic1 (1)"]')
        link.click()
        self.wait_for_modal_shown(selenium, 'budgetModalLabel')
        modal = selenium.find_element_by_id('budgetModal')
        title = selenium.find_element_by_id('budgetModalLabel')
        body = selenium.find_element_by_id('budgetModalBody')
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
            'budget_frm_group_starting_balance').is_displayed()
        assert selenium.find_element_by_id(
            'budget_frm_current_balance').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'budget_frm_group_current_balance').is_displayed() is False
        assert selenium.find_element_by_id('budget_frm_active').is_selected()
        sel = Select(selenium.find_element_by_id('budget_frm_account'))
        assert sel.first_selected_option.text == ''
