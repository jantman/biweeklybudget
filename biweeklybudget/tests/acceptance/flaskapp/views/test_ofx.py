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
from datetime import timedelta
from selenium.webdriver.support.ui import Select

from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper


@pytest.mark.acceptance
@pytest.mark.usefixtures("testdb", "testflask")
class TestOFX(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        selenium.get(base_url + '/ofx')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'OFX Transactions - BiweeklyBudget'

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
@pytest.mark.usefixtures("testdb", "testflask")
class TestOFXDefault(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.dt = dtnow()
        selenium.get(base_url + '/ofx')

    def test_table(self, selenium):
        table = selenium.find_element_by_id('table-ofx-txn')
        texts = self.tbody2textlist(table)
        elems = self.tbody2elemlist(table)
        assert texts[0] == [
            (self.dt - timedelta(hours=22)).strftime('%Y-%m-%d'),
            '$123.81',
            'CreditOne (3)',
            'Purchase',
            '123.81 Credit Purchase T1',
            '38328',
            'CreditOneT1Desc',
            'T1',
            '4',
            (self.dt - timedelta(hours=13)).strftime('%Y-%m-%d'),
            ''
        ]
        assert elems[0][2].get_attribute(
            'innerHTML') == '<a href="/accounts/3">CreditOne (3)</a>'
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['CreditOne (3)', 'T1'],
            ['CreditTwo (4)', '002'],
            ['BankOne (1)', 'BankOne.0.1'],
            ['CreditTwo (4)', '001'],
            ['BankOne (1)', 'BankOne.1.1'],
            ['BankOne (1)', 'BankOne.1.2'],
            ['BankOne (1)', 'BankOne.1.3'],
            ['BankOne (1)', 'BankOne.1.4'],
            ['BankOne (1)', 'BankOne.1.5'],
            ['BankOne (1)', 'BankOne.1.6']
        ]

    def test_paginate(self, selenium):
        selenium.get(self.baseurl + '/ofx')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['CreditOne (3)', 'T1'],
            ['CreditTwo (4)', '002'],
            ['BankOne (1)', 'BankOne.0.1'],
            ['CreditTwo (4)', '001'],
            ['BankOne (1)', 'BankOne.1.1'],
            ['BankOne (1)', 'BankOne.1.2'],
            ['BankOne (1)', 'BankOne.1.3'],
            ['BankOne (1)', 'BankOne.1.4'],
            ['BankOne (1)', 'BankOne.1.5'],
            ['BankOne (1)', 'BankOne.1.6']
        ]
        page2_link = selenium.find_element_by_xpath(
            '//li[@class="paginate_button "]/a[text()="2"]'
        )
        page2_link.click()
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['BankOne (1)', 'BankOne.1.7'],
            ['BankOne (1)', 'BankOne.1.8'],
            ['BankOne (1)', 'BankOne.1.9'],
            ['BankOne (1)', 'BankOne.1.10'],
            ['BankOne (1)', 'BankOne.1.11'],
            ['BankOne (1)', 'BankOne.1.12'],
            ['BankOne (1)', 'BankOne.1.13'],
            ['BankOne (1)', 'BankOne.1.14'],
            ['BankOne (1)', 'BankOne.1.15'],
            ['BankOne (1)', 'BankOne.1.16']
        ]

    def test_filter_opts(self, selenium):
        selenium.get(self.baseurl + '/ofx')
        acct_filter = Select(selenium.find_element_by_id('account_filter'))
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

    def test_filter(self, selenium):
        p1trans = [
            ['CreditOne (3)', 'T1'],
            ['CreditTwo (4)', '002'],
            ['BankOne (1)', 'BankOne.0.1'],
            ['CreditTwo (4)', '001'],
            ['BankOne (1)', 'BankOne.1.1'],
            ['BankOne (1)', 'BankOne.1.2'],
            ['BankOne (1)', 'BankOne.1.3'],
            ['BankOne (1)', 'BankOne.1.4'],
            ['BankOne (1)', 'BankOne.1.5'],
            ['BankOne (1)', 'BankOne.1.6']
        ]
        selenium.get(self.baseurl + '/ofx')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        # check sanity
        assert trans == p1trans
        acct_filter = Select(selenium.find_element_by_id('account_filter'))
        # select CreditTwo (4)
        acct_filter.select_by_value('4')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['CreditTwo (4)', '002'],
            ['CreditTwo (4)', '001']
        ]
        # select back to all
        acct_filter.select_by_value('None')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == p1trans
