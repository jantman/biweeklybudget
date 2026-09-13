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

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from selenium.webdriver.common.by import By


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestPlaidUpdateView(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/plaid-update')

    def test_1_heading(self, selenium):
        heading = selenium.find_element(By.CLASS_NAME, 'navbar-brand')
        assert heading.text == 'Plaid Update - BiweeklyBudget'

    def test_2_nav_menu(self, selenium):
        ul = selenium.find_element(By.ID, 'side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_3_notifications(self, selenium):
        div = selenium.find_element(By.ID, 'notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'

    def test_4_table(self, selenium):
        table = selenium.find_element(By.ID, 'table-items-plaid')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                'PlaidItem1',
                'Inst1 (None)',
                'Acct1 (foo), Acct2 (foo), Acct4 (foo4)',
                'now',
                'Update / Fix Item',
                'Refresh'
            ],
            [
                'PlaidItem2',
                'Inst2 (None)',
                'Acct3 (foo)',
                'now',
                'Update / Fix Item',
                'Refresh'
            ],
        ]

    def item_checkboxes(self, selenium):
        return selenium.find_elements(
            By.CSS_SELECTOR, '#table-update-plaid input.account-checkbox'
        )

    def assert_still_on_page(self, selenium):
        assert selenium.current_url == self.baseurl + '/plaid-update'
        assert selenium.find_element(By.ID, 'table-update-plaid') is not None

    def test_5_check_uncheck_links(self, selenium):
        panel = selenium.find_element(By.ID, 'panel-plaid-update')
        check = panel.find_element(By.ID, 'plaid_check_all')
        uncheck = panel.find_element(By.ID, 'plaid_uncheck_all')
        assert check.text == 'Check All'
        assert uncheck.text == 'Uncheck All'
        boxes = self.item_checkboxes(selenium)
        assert [b.get_attribute('id') for b in boxes] == [
            'item_PlaidItem1', 'item_PlaidItem2'
        ]
        assert all(b.is_selected() for b in boxes)

    def test_6_uncheck_all(self, selenium):
        selenium.find_element(By.ID, 'plaid_uncheck_all').click()
        self.assert_still_on_page(selenium)
        boxes = self.item_checkboxes(selenium)
        assert len(boxes) == 2
        assert not any(b.is_selected() for b in boxes)

    def test_7_uncheck_all_then_select_one(self, selenium):
        selenium.find_element(By.ID, 'plaid_uncheck_all').click()
        selenium.find_element(By.ID, 'item_PlaidItem2').click()
        self.assert_still_on_page(selenium)
        data = selenium.execute_script(
            "return $('#panel-plaid-update form').serialize();"
        )
        assert data == 'item_PlaidItem2=1'

    def test_8_check_all(self, selenium):
        one = selenium.find_element(By.ID, 'item_PlaidItem1')
        one.click()
        assert not one.is_selected()
        selenium.find_element(By.ID, 'plaid_check_all').click()
        self.assert_still_on_page(selenium)
        boxes = self.item_checkboxes(selenium)
        assert len(boxes) == 2
        assert all(b.is_selected() for b in boxes)
        selenium.find_element(By.ID, 'plaid_check_all').click()
        assert all(b.is_selected() for b in self.item_checkboxes(selenium))
