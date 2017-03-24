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


@pytest.mark.acceptance
class TestBaseTemplateNavigation(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, testdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url)

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element_by_id('side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_nav_links(self, selenium):
        nav = selenium.find_element_by_xpath(
            "//div[contains(@class, 'sidebar-nav')]/ul"
        )
        navlinks = []
        for li in nav.find_elements_by_xpath("//li/a"):
            if li.text.strip() == '':
                continue
            navlinks.append(
                (self.relurl(li.get_attribute('href')), li.text)
            )
        assert navlinks == [
            ('/', 'Home'),
            ('/payperiods', 'Pay Periods'),
            ('/accounts', 'Accounts'),
            ('/ofx', 'OFX'),
            ('/transactions', 'Transactions'),
            ('/reconcile', 'Reconcile'),
            ('/budgets', 'Budgets'),
            ('/scheduled', 'Scheduled'),
            ('https://github.com/jantman/biweeklybudget',
             'biweeklybudget is AGPLv3+ Free Software'),
            ('http://biweeklybudget.readthedocs.io/en/latest/', 'Docs')
        ]


@pytest.mark.acceptance
class TestBaseTemplateNotifications(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, testdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url)

    def test_notifications(self, selenium):
        div = selenium.find_element_by_id('notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'

    def test_stale_accounts(self, selenium):
        div = selenium.find_elements_by_xpath(
            "//div[@id='notifications-row']/div/div"
        )[0]
        assert div.text == '2 Accounts with stale data. View Accounts.'
        a = div.find_element_by_tag_name('a')
        assert self.relurl(a.get_attribute('href')) == '/accounts'
        assert a.text == 'View Accounts'

    def test_unreconciled_transactions(self, selenium):
        div = selenium.find_elements_by_xpath(
            "//div[@id='notifications-row']/div/div"
        )[1]
        assert div.text == 'XX Unreconciled Transactions. (EXAMPLE) Alert Link.'
        a = div.find_element_by_tag_name('a')
        assert self.relurl(a.get_attribute('href')) == '/reconcile'
        assert a.text == 'Alert Link'
