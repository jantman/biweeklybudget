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
from biweeklybudget.models.dbsetting import DBSetting


@pytest.mark.acceptance
class TestCreditPayoffs(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/accounts/credit-payoff')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'Credit Card Payoffs - BiweeklyBudget'

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
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestSettings(AcceptanceHelper):

    def test_00_verify_db(self, testdb):
        b = testdb.query(DBSetting).get('credit-payoff')
        assert b is None

    def foo(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        assert selenium.find_element_by_id(
            'active-remaining-cost').get_attribute('innerHTML') == '$77.77'
        assert selenium.find_element_by_id(
            'active-total-cost').get_attribute('innerHTML') == '$2,546.89'
        table = selenium.find_element_by_id('table-projects')
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        assert htmls == [
            [
                '<a href="/projects/1">P1</a>',
                '$2,546.89',
                '$77.77',
                'yes <a onclick="deactivateProject(1);" href="#">'
                '(deactivate)</a>',
                'ProjectOne'
            ],
            [
                '<a href="/projects/2">P2</a>',
                '$0.00',
                '$0.00',
                'yes <a onclick="deactivateProject(2);" href="#">'
                '(deactivate)</a>',
                'ProjectTwo'
            ],
            [
                '<a href="/projects/3">P3Inactive</a>',
                '$5.34',
                '$3.00',
                'NO <a onclick="activateProject(3);" href="#">'
                '(activate)</a>',
                'ProjectThreeInactive'
            ]
        ]
