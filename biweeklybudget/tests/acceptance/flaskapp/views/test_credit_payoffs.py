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
import re
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.dbsetting import DBSetting


def get_increases(selenium, form_ids):
    vals = {}
    id_re = re.compile(r'^payoff_increase_frm_(\d+)$')
    for frmid in form_ids:
        m = id_re.match(frmid)
        if m is None:
            continue
        _id = int(m.group(1))

        vals[_id] = {
            'enabled': selenium.find_element_by_id(
                'payoff_increase_frm_%s_enable' % _id
            ).is_selected(),
            'date': selenium.find_element_by_id(
                'payoff_increase_frm_%s_date' % _id
            ).get_attribute('value'),
            'amount': selenium.find_element_by_id(
                'payoff_increase_frm_%s_amt' % _id
            ).get_attribute('value')
        }
    return vals


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
@pytest.mark.usefixtures('testflask')
class TestNoSettings(AcceptanceHelper):

    def test_00_verify_db(self, testdb):
        b = testdb.query(DBSetting).get('credit-payoff')
        assert b is None

    def test_01_no_config(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        assert selenium.find_element_by_id(
            'payoff_frm_min_pymt').get_attribute('value') == '144.98'
        form_ids = [
            s.get_attribute('id')
            for s in selenium.find_elements_by_tag_name('form')
        ]
        assert sorted(form_ids) == [
            'min_payment_frm',
            'payoff_increase_frm_1'
        ]
        assert get_increases(selenium, form_ids) == {
            1: {
                'enabled': False,
                'date': '',
                'amount': ''
            }
        }

    def test_02_min_payment(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/credit-payoff')
        table = selenium.find_element_by_id('table_MinPaymentMethod')
        texts = self.tbody2textlist(table)
        assert texts == [
            ['CreditOne (3)', '2 years', '$963.21', '$11.15'],
            ['CreditTwo (4)', '14 years', '$8,764.66', '$3,266.01'],
            ['Totals', '14 years', '$9,727.87', '$3,277.16']
        ]
