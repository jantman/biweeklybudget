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
from biweeklybudget.models.fuel import Vehicle, FuelFill
from biweeklybudget.models.transaction import Transaction


LEVEL_OPTS = [
    ['0', '0/10'], ['10', '1/10'], ['20', '2/10'], ['30', '3/10'],
    ['40', '4/10'], ['50', '5/10'], ['60', '6/10'], ['70', '7/10'],
    ['80', '8/10'], ['90', '9/10'], ['100', '10/10']
]


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestFuel(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
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
@pytest.mark.usefixtures('refreshdb', 'testflask')
@pytest.mark.incremental
class TestFuelLogView(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
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

    def test_05_vehicles(self, base_url, selenium):
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


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestModals(AcceptanceHelper):

    def test_00_vehicle_verify_db(self, testdb):
        b = testdb.query(Vehicle).get(1)
        assert b is not None
        assert b.name == 'Veh1'
        assert b.is_active is True
        b = testdb.query(Vehicle).get(3)
        assert b is not None
        assert b.name == 'Veh3Inactive'
        assert b.is_active is False

    def test_01_vehicle_populate_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/fuel')
        link = selenium.find_element_by_xpath('//a[text()="Veh1"]')
        self.wait_until_clickable(selenium, '//a[text()="Veh1"]', by='xpath')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Vehicle 1'
        assert selenium.find_element_by_id('vehicle_frm_id').get_attribute(
            'value') == '1'
        assert selenium.find_element_by_id(
            'vehicle_frm_name').get_attribute('value') == 'Veh1'
        assert selenium.find_element_by_id('vehicle_frm_active').is_selected()

    def test_02_vehicle_edit_modal_inactive(self, base_url, selenium):
        self.get(selenium, base_url + '/fuel')
        link = selenium.find_element_by_xpath('//a[text()="Veh3Inactive"]')
        self.wait_until_clickable(
            selenium, '//a[text()="Veh3Inactive"]', by='xpath'
        )
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Vehicle 3'
        assert selenium.find_element_by_id('vehicle_frm_id').get_attribute(
            'value') == '3'
        assert selenium.find_element_by_id(
            'vehicle_frm_name').get_attribute('value') == 'Veh3Inactive'
        assert selenium.find_element_by_id(
            'vehicle_frm_active').is_selected() is False
        name = selenium.find_element_by_id('vehicle_frm_name')
        name.clear()
        name.send_keys('Veh3Edited')
        selenium.find_element_by_id('vehicle_frm_active').click()
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Vehicle 3 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'vehicles-table')
        # test that the table is updated
        table = selenium.find_element_by_id('vehicles-table')
        elems = self.tbody2elemlist(table)
        htmls = []
        for row in elems:
            htmls.append(
                [y.get_attribute('innerHTML') for y in row]
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
                '<a href="javascript:vehicleModal(3)">Veh3Edited</a>',
                'true'
            ]
        ]

    def test_03_vehicle_verify_db(self, testdb):
        b = testdb.query(Vehicle).get(3)
        assert b is not None
        assert b.name == 'Veh3Edited'
        assert b.is_active is True

    def test_04_vehicle_modal_add(self, base_url, selenium):
        self.get(selenium, base_url + '/fuel')
        link = selenium.find_element_by_id('btn-add-vehicle')
        self.wait_until_clickable(selenium, 'btn-add-vehicle')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Vehicle'
        name = selenium.find_element_by_id('vehicle_frm_name')
        name.clear()
        name.send_keys('Vehicle4')
        selenium.find_element_by_id('vehicle_frm_active').click()
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Vehicle 4 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'vehicles-table')
        # test that the table is updated
        table = selenium.find_element_by_id('vehicles-table')
        elems = self.tbody2elemlist(table)
        htmls = []
        for row in elems:
            htmls.append(
                [y.get_attribute('innerHTML') for y in row]
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
                '<a href="javascript:vehicleModal(3)">Veh3Edited</a>',
                'true'
            ],
            [
                '<a href="javascript:vehicleModal(4)">4</a>',
                '<a href="javascript:vehicleModal(4)">Vehicle4</a>',
                'false'
            ]
        ]

    def test_10_fuel_verify_db(self, testdb):
        ids = [
            t.id for t in testdb.query(FuelFill).all()
        ]
        assert len(ids) == 6
        assert max(ids) == 6
        trans_ids = [
            x.id for x in testdb.query(Transaction).all()
        ]
        assert len(trans_ids) == 3
        assert max(trans_ids) == 3

    def test_11_fuel_populate_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/fuel')
        link = selenium.find_element_by_id('btn-add-fuel')
        self.wait_until_clickable(selenium, 'btn-add-fuel')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add Fuel Fill'
        veh_sel = Select(selenium.find_element_by_id('fuel_frm_vehicle'))
        opts = [[o.get_attribute('value'), o.text] for o in veh_sel.options]
        assert opts == [['1', 'Veh1'], ['2', 'Veh2'], ['3', 'Veh3Edited']]
        assert veh_sel.first_selected_option.get_attribute('value') == '1'
        date = selenium.find_element_by_id('fuel_frm_date')
        assert date.get_attribute(
            'value') == dtnow().date().strftime('%Y-%m-%d')
        odo = selenium.find_element_by_id('fuel_frm_odo_miles')
        assert odo.get_attribute('value') == ''
        rep_mi = selenium.find_element_by_id('fuel_frm_reported_miles')
        assert rep_mi.get_attribute('value') == ''
        lvl_before = Select(
            selenium.find_element_by_id('fuel_frm_level_before')
        )
        opts = [[o.get_attribute('value'), o.text] for o in lvl_before.options]
        assert opts == LEVEL_OPTS
        assert lvl_before.first_selected_option.get_attribute('value') == '0'
        lvl_after = Select(
            selenium.find_element_by_id('fuel_frm_level_after')
        )
        opts = [[o.get_attribute('value'), o.text] for o in lvl_after.options]
        assert opts == LEVEL_OPTS
        assert lvl_after.first_selected_option.get_attribute('value') == '100'
        fill_loc = selenium.find_element_by_id('fuel_frm_fill_loc')
        assert fill_loc.get_attribute('value') == ''
        cpg = selenium.find_element_by_id('fuel_frm_cost_per_gallon')
        assert cpg.get_attribute('value') == ''
        cost = selenium.find_element_by_id('fuel_frm_total_cost')
        assert cost.get_attribute('value') == ''
        gals = selenium.find_element_by_id('fuel_frm_gallons')
        assert gals.get_attribute('value') == ''
        rep_mpg = selenium.find_element_by_id('fuel_frm_reported_mpg')
        assert rep_mpg.get_attribute('value') == ''
        add_trans = selenium.find_element_by_id('fuel_frm_add_trans')
        assert add_trans.is_selected()
        acct_sel = Select(body.find_element_by_id('fuel_frm_account'))
        opts = [[o.get_attribute('value'), o.text] for o in acct_sel.options]
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
        budget_sel = Select(body.find_element_by_id('fuel_frm_budget'))
        opts = [[o.get_attribute('value'), o.text] for o in budget_sel.options]
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
        assert budget_sel.first_selected_option.get_attribute('value') == '2'
        notes = selenium.find_element_by_id('fuel_frm_notes')
        assert notes.get_attribute('value') == ''

    def test_12_fuel_add_no_trans(self, base_url, selenium):
        self.get(selenium, base_url + '/fuel')
        link = selenium.find_element_by_id('btn-add-fuel')
        self.wait_until_clickable(selenium, 'btn-add-fuel')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add Fuel Fill'
        veh_sel = Select(selenium.find_element_by_id('fuel_frm_vehicle'))
        veh_sel.select_by_value('2')
        date = selenium.find_element_by_id('fuel_frm_date')
        date.clear()
        date.send_keys(
            (dtnow() - timedelta(days=3)).date().strftime('%Y-%m-%d')
        )
        odo = selenium.find_element_by_id('fuel_frm_odo_miles')
        odo.clear()
        odo.send_keys('1123')
        rep_mi = selenium.find_element_by_id('fuel_frm_reported_miles')
        rep_mi.clear()
        rep_mi.send_keys('123')
        lvl_before = Select(
            selenium.find_element_by_id('fuel_frm_level_before')
        )
        lvl_before.select_by_value('50')
        lvl_after = Select(
            selenium.find_element_by_id('fuel_frm_level_after')
        )
        lvl_after.select_by_value('90')
        fill_loc = selenium.find_element_by_id('fuel_frm_fill_loc')
        fill_loc.clear()
        fill_loc.send_keys('Fill Location')
        cpg = selenium.find_element_by_id('fuel_frm_cost_per_gallon')
        cpg.clear()
        cpg.send_keys('1.239')
        cost = selenium.find_element_by_id('fuel_frm_total_cost')
        cost.clear()
        cost.send_keys('12.34')
        gals = selenium.find_element_by_id('fuel_frm_gallons')
        gals.clear()
        gals.send_keys('6.789')
        rep_mpg = selenium.find_element_by_id('fuel_frm_reported_mpg')
        rep_mpg.clear()
        rep_mpg.send_keys('34.5')
        add_trans = selenium.find_element_by_id('fuel_frm_add_trans')
        add_trans.click()
        assert add_trans.is_selected() is False
        acct_sel = Select(body.find_element_by_id('fuel_frm_account'))
        acct_sel.select_by_value('3')
        budget_sel = Select(body.find_element_by_id('fuel_frm_budget'))
        budget_sel.select_by_value('1')
        notes = selenium.find_element_by_id('fuel_frm_notes')
        notes.clear()
        notes.send_keys('My Notes')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved FuelFill 7 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that datatable was updated
        table = selenium.find_element_by_id('table-fuel-log')
        odo_reads = [y[2] for y in self.tbody2textlist(table)]
        assert odo_reads == [
            '1,011', '1,012', '1,013', '1,001', '1,002', '1,003', '1,123'
        ]
        notif = selenium.find_element_by_id('last_mpg_notice')
        assert notif.get_attribute('innerHTML') == 'Last fill MPG: 16.349'

    def test_13_fuel_verify_db(self, testdb):
        ids = [
            t.id for t in testdb.query(FuelFill).all()
        ]
        assert len(ids) == 7
        assert max(ids) == 7
        fill = testdb.query(FuelFill).get(7)
        assert fill.date == (dtnow() - timedelta(days=3)).date()
        assert fill.vehicle_id == 2
        assert fill.odometer_miles == 1123
        assert fill.reported_miles == 123
        assert fill.level_before == 50
        assert fill.level_after == 90
        assert fill.fill_location == 'Fill Location'
        assert float(fill.cost_per_gallon) == 1.239
        assert float(fill.total_cost) == 12.34
        assert float(fill.gallons) == 6.789
        assert float(fill.reported_mpg) == 34.5
        assert fill.notes == 'My Notes'
        # calculated values
        assert fill.calculated_miles == 111
        assert float(fill.calculated_mpg) == 16.349
        trans_ids = [
            x.id for x in testdb.query(Transaction).all()
        ]
        assert len(trans_ids) == 3
        assert max(trans_ids) == 3

    def test_14_fuel_add_with_trans(self, base_url, selenium):
        self.get(selenium, base_url + '/fuel')
        link = selenium.find_element_by_id('btn-add-fuel')
        self.wait_until_clickable(selenium, 'btn-add-fuel')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add Fuel Fill'
        veh_sel = Select(selenium.find_element_by_id('fuel_frm_vehicle'))
        veh_sel.select_by_value('1')
        date = selenium.find_element_by_id('fuel_frm_date')
        date.clear()
        date.send_keys(
            (dtnow() - timedelta(days=2)).date().strftime('%Y-%m-%d')
        )
        odo = selenium.find_element_by_id('fuel_frm_odo_miles')
        odo.clear()
        odo.send_keys('1256')
        rep_mi = selenium.find_element_by_id('fuel_frm_reported_miles')
        rep_mi.clear()
        rep_mi.send_keys('345')
        lvl_before = Select(
            selenium.find_element_by_id('fuel_frm_level_before')
        )
        lvl_before.select_by_value('10')
        lvl_after = Select(
            selenium.find_element_by_id('fuel_frm_level_after')
        )
        lvl_after.select_by_value('100')
        fill_loc = selenium.find_element_by_id('fuel_frm_fill_loc')
        fill_loc.clear()
        fill_loc.send_keys('Fill Location2')
        cpg = selenium.find_element_by_id('fuel_frm_cost_per_gallon')
        cpg.clear()
        cpg.send_keys('1.459')
        cost = selenium.find_element_by_id('fuel_frm_total_cost')
        cost.clear()
        cost.send_keys('14.82')
        gals = selenium.find_element_by_id('fuel_frm_gallons')
        gals.clear()
        gals.send_keys('5.678')
        rep_mpg = selenium.find_element_by_id('fuel_frm_reported_mpg')
        rep_mpg.clear()
        rep_mpg.send_keys('28.3')
        add_trans = selenium.find_element_by_id('fuel_frm_add_trans')
        assert add_trans.is_selected()
        acct_sel = Select(body.find_element_by_id('fuel_frm_account'))
        acct_sel.select_by_value('3')
        budget_sel = Select(body.find_element_by_id('fuel_frm_budget'))
        budget_sel.select_by_value('1')
        notes = selenium.find_element_by_id('fuel_frm_notes')
        notes.clear()
        notes.send_keys('My Notes2')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved FuelFill 8 ' \
                                 'and Transaction 4 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that datatable was updated
        table = selenium.find_element_by_id('table-fuel-log')
        odo_reads = [y[2] for y in self.tbody2textlist(table)]
        assert odo_reads == [
            '1,011', '1,012', '1,013',
            '1,001', '1,002', '1,003',
            '1,256', '1,123'
        ]

    def test_15_fuel_verify_db(self, testdb):
        ids = [
            t.id for t in testdb.query(FuelFill).all()
        ]
        assert len(ids) == 8
        assert max(ids) == 8
        fill = testdb.query(FuelFill).get(8)
        assert fill.date == (dtnow() - timedelta(days=2)).date()
        assert fill.vehicle_id == 1
        assert fill.odometer_miles == 1256
        assert fill.reported_miles == 345
        assert fill.level_before == 10
        assert fill.level_after == 100
        assert fill.fill_location == 'Fill Location2'
        assert float(fill.cost_per_gallon) == 1.459
        assert float(fill.total_cost) == 14.82
        assert float(fill.gallons) == 5.678
        assert float(fill.reported_mpg) == 28.3
        assert fill.notes == 'My Notes2'
        # calculated values
        assert fill.calculated_miles == 245
        assert float(fill.calculated_mpg) == 43.148
        trans_ids = [
            x.id for x in testdb.query(Transaction).all()
        ]
        assert len(trans_ids) == 4
        assert max(trans_ids) == 4
        trans = testdb.query(Transaction).get(4)
        assert trans.date == (dtnow() - timedelta(days=2)).date()
        assert float(trans.actual_amount) == 14.82
        assert trans.budgeted_amount is None
        assert trans.description == 'Fill Location2 - FuelFill #8 (Veh1)'
        assert trans.notes == 'My Notes2'
        assert trans.account_id == 3
        assert trans.budget_id == 1
        assert trans.scheduled_trans_id is None
