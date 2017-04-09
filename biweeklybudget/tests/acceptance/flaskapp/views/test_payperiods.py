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
from dateutil.relativedelta import relativedelta

from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.settings import PAY_PERIOD_START_DATE
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod


@pytest.mark.acceptance
class DONOTTestPayPeriods(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url + '/scheduled')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'Scheduled Transactions - BiweeklyBudget'

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
class TestFindPayPeriod(AcceptanceHelper):

    def test_input_date(self, base_url, selenium):
        selenium.get(base_url + '/payperiods')
        i = selenium.find_element_by_id('payperiod_date_input')
        i.clear()
        start_date = PAY_PERIOD_START_DATE
        print("PayPeriod start date: %s" % start_date)
        send_date = start_date + timedelta(days=4)
        i.send_keys(send_date.strftime('%Y-%m-%d'))
        selenium.find_element_by_id('payperiod-go-button').click()
        self.wait_for_load_complete(selenium)
        assert selenium.current_url == \
            base_url + '/payperiod/' + start_date.strftime('%Y-%m-%d')

    def test_input_calendar(self, base_url, selenium):
        selenium.get(base_url + '/payperiods')
        start_date = PAY_PERIOD_START_DATE
        print("PayPeriod start date: %s" % start_date)
        send_date = start_date + timedelta(days=4)
        cal = selenium.find_element_by_id('cal2')
        daysdiv = selenium.find_element_by_xpath(
            '//div[@id="cal2"]//div[@class="datepicker-days"]'
        )
        tbl = daysdiv.find_elements_by_tag_name('table')[0]
        # month
        assert tbl.find_elements_by_tag_name(
            'thead')[0].find_elements_by_tag_name(
            'tr')[1].find_elements_by_tag_name('th')[1].text == \
            dtnow().strftime('%B %Y')
        tbody = tbl.find_elements_by_tag_name('tbody')[0]
        print('Looking for datepicker TD for date %s' % send_date)
        for e in tbody.find_elements_by_tag_name('td'):
            if e.get_attribute('class') != 'day':
                continue
            if e.text.strip() == str(send_date.day):
                parent = e.find_element_by_xpath('..')
                print("Found date TD: %s - parent: %s" % (
                    e.get_attribute('innerHTML'),
                    parent.get_attribute('innerHTML')
                ))
                e.click()
                break
        else:
            raise RuntimeError("Unable to find td for date %d", send_date.day)
        self.wait_for_load_complete(selenium)
        assert selenium.current_url == \
            base_url + '/payperiod/' + start_date.strftime('%Y-%m-%d')

    def test_input_calendar_future(self, base_url, selenium):
        selenium.get(base_url + '/payperiods')
        start_date = PAY_PERIOD_START_DATE
        print("PayPeriod start date: %s" % start_date)
        send_date = start_date + relativedelta(months=3)
        send_date = send_date.replace(day=3)
        send_pp = BiweeklyPayPeriod.period_for_date(send_date, None)
        cal = selenium.find_element_by_id('cal2')
        daysdiv = selenium.find_element_by_xpath(
            '//div[@id="cal2"]//div[@class="datepicker-days"]'
        )
        tbl = daysdiv.find_elements_by_tag_name('table')[0]
        thead = tbl.find_elements_by_tag_name('thead')[0]
        # month
        assert thead.find_elements_by_tag_name(
            'tr')[1].find_elements_by_tag_name('th')[1].text == \
            dtnow().strftime('%B %Y')
        tbody = tbl.find_elements_by_tag_name('tbody')[0]
        print('Advancing by 3 months')
        next_link = thead.find_element_by_xpath('//th[@class="next"]')
        next_link.click()
        self.wait_for_jquery_done(selenium)
        next_link.click()
        self.wait_for_jquery_done(selenium)
        next_link.click()
        self.wait_for_jquery_done(selenium)
        print('Looking for datepicker TD for date %s' % send_date)
        for e in tbody.find_elements_by_tag_name('td'):
            if e.get_attribute('class') != 'day':
                continue
            if e.text.strip() == str(send_date.day):
                parent = e.find_element_by_xpath('..')
                print("Found date TD: %s - parent: %s" % (
                    e.get_attribute('innerHTML'),
                    parent.get_attribute('innerHTML')
                ))
                e.click()
                break
        else:
            raise RuntimeError("Unable to find td for date %d", send_date.day)
        self.wait_for_load_complete(selenium)
        assert selenium.current_url == \
            base_url + '/payperiod/' + send_pp.start_date.strftime('%Y-%m-%d')
