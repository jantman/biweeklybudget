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
from datetime import timedelta, date, datetime
from pytz import UTC
from selenium.webdriver.support.ui import Select

from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.fuel import FuelFill, Vehicle


@pytest.mark.acceptance
class TestFuel(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/fuel')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'Fuel Log - BiweeklyBudget'

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
class TestFuelLogView(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.dt = dtnow()
        self.get(selenium, base_url + '/fuel')

    def test_01_table(self, selenium):
        table = selenium.find_element_by_id('table-fuel-log')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                (self.dt + timedelta(days=1)).date().strftime('%Y-%m-%d'),
                'Veh1 (1)',
                '1,011',
                '111',
                '10',
                '11%',
                '89%',
                'fill_loc v1 1',
                '$2.11',
                '$4.22',
                '11.000',
                '21.1',
                '0.909',
                'notes v1 1'
            ],
            [
                (self.dt + timedelta(days=1)).date().strftime('%Y-%m-%d'),
                'Veh2 (2)',
                '1,012',
                '112',
                '10',
                '12%',
                '88%',
                'fill_loc v2 1',
                '$2.12',
                '$4.24',
                '12.000',
                '21.2',
                '0.833',
                'notes v2 1'
            ],
            [
                self.dt.date().strftime('%Y-%m-%d'),
                'Veh1 (1)',
                '1,001',
                '101',
                '',
                '1%',
                '99%',
                'fill_loc v1 0',
                '$2.01',
                '$2.01',
                '1.000',
                '20.1',
                '',
                'notes v1 0'
            ],
            [
                self.dt.date().strftime('%Y-%m-%d'),
                'Veh2 (2)',
                '1,002',
                '102',
                '',
                '2%',
                '98%',
                'fill_loc v2 0',
                '$2.02',
                '$2.02',
                '2.000',
                '20.2',
                '',
                'notes v2 0'
            ]
        ]

    def test_02_filter_opts(self, selenium):
        self.get(selenium, self.baseurl + '/fuel')
        veh_filter = Select(selenium.find_element_by_id('vehicle_filter'))
        # find the options
        opts = []
        for o in veh_filter.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'Veh1'],
            ['2', 'Veh2']
        ]

    def test_03_filter(self, selenium):
        p1odo = [
            '1,011',
            '1,012',
            '1,001',
            '1,002'
        ]
        self.get(selenium, self.baseurl + '/fuel')
        table = self.retry_stale(
            selenium.find_element_by_id,
            'table-fuel-log'
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        odo = [t[2] for t in texts]
        # check sanity
        assert odo == p1odo
        veh_filter = Select(selenium.find_element_by_id('vehicle_filter'))
        # select Veh1
        veh_filter.select_by_value('1')
        table = self.retry_stale(
            selenium.find_element_by_id,
            'table-fuel-log'
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        odo = [t[2] for t in texts]
        assert odo == ['1,011', '1,001']
        # select back to all
        veh_filter.select_by_value('None')
        table = self.retry_stale(
            selenium.find_element_by_id,
            'table-fuel-log'
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        odo = [t[2] for t in texts]
        # check sanity
        assert odo == p1odo

    def test_04_search(self, selenium):
        self.get(selenium, self.baseurl + '/fuel')
        search = self.retry_stale(
            selenium.find_element_by_xpath,
            '//input[@type="search"]'
        )
        search.send_keys('v1 1')
        self.wait_for_jquery_done(selenium)
        table = self.retry_stale(
            selenium.find_element_by_id,
            'table-fuel-log'
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        odo = [t[2] for t in texts]
        assert odo == ['1,011']

    def test_05_vehicles(self, base_url, selenium, testdb):
        self.get(selenium, self.baseurl + '/fuel')
        table = selenium.find_element_by_id('vehicles-table')
        elems = self.tbody2elemlist(table)
        htmls = []
        for row in elems:
            htmls.append(
                [x.get_attribute('innerHTML') for x in row]
            )
        assert htmls == [
            [
                '<a href="javascript:vehicleModal(1)">1</a>',
                '<a href="javascript:vehicleModal(1)">Veh1</a>',
                'true'
            ],
            [
                '<a href="javascript:vehicleModal(2)">2</a>',
                '<a href="javascript:vehicleModal(2)">Veh2</a>',
                'true'
            ],
            [
                '<a href="javascript:vehicleModal(3)">3</a>',
                '<a href="javascript:vehicleModal(3)">Veh3Inactive</a>',
                'false'
            ]
        ]
