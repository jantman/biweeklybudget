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
from sqlalchemy import func
from decimal import Decimal
from time import sleep
from biweeklybudget.models.projects import Project, BoMItem
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestProjects(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/projects')

    def test_heading(self, selenium):
        heading = selenium.find_element(By.CLASS_NAME, 'navbar-brand')
        assert heading.text == 'Projects / Bill of Materials - BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element(By.ID, 'side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_notifications(self, selenium):
        div = selenium.find_element(By.ID, 'notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestProjectsView(AcceptanceHelper):

    def test_00_verify_db(self, testdb):
        b = testdb.query(Project).get(1)
        assert b is not None
        assert b.name == 'P1'
        assert b.notes == 'ProjectOne'
        assert b.is_active is True
        assert b.standing_budget_id is not None
        standing1 = testdb.query(Budget).filter(
            Budget.name.__eq__('Standing1')
        ).one()
        assert b.standing_budget_id == standing1.id
        b = testdb.query(Project).get(2)
        assert b is not None
        assert b.name == 'P2'
        assert b.notes == 'ProjectTwo'
        assert b.is_active is True
        assert b.standing_budget_id is None
        b = testdb.query(Project).get(3)
        assert b is not None
        assert b.name == 'P3Inactive'
        assert b.notes == 'ProjectThreeInactive'
        assert b.is_active is False
        assert b.standing_budget_id is None
        assert testdb.query(Project).with_entities(
            func.max(Project.id)
        ).scalar() == 3
        assert testdb.query(BoMItem).with_entities(
            func.max(BoMItem.id)
        ).scalar() == 5

    def test_01_table(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        assert selenium.find_element(By.ID,
                                     'active-remaining-cost').get_attribute('innerHTML') == '$77.77'
        assert selenium.find_element(By.ID,
                                     'active-total-cost').get_attribute('innerHTML') == '$2,546.89'
        table = selenium.find_element(By.ID, 'table-projects')
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        assert htmls == [
            [
                '<a href="/projects/1">P1</a>'
                ' <a href="#" onclick="projectModal(1)">(edit)</a>',
                '$2,546.89',
                '$77.77',
                'Standing1',
                'yes <a onclick="deactivateProject(1);" href="#">'
                '(deactivate)</a>',
                'ProjectOne'
            ],
            [
                '<a href="/projects/2">P2</a>'
                ' <a href="#" onclick="projectModal(2)">(edit)</a>',
                '$0.00',
                '$0.00',
                '',
                'yes <a onclick="deactivateProject(2);" href="#">'
                '(deactivate)</a>',
                'ProjectTwo'
            ],
            [
                '<a href="/projects/3">P3Inactive</a>'
                ' <a href="#" onclick="projectModal(3)">(edit)</a>',
                '$5.34',
                '$3.00',
                '',
                'NO <a onclick="activateProject(3);" href="#">'
                '(activate)</a>',
                'ProjectThreeInactive'
            ]
        ]

    def test_02_search(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        search = self.retry_stale(
            lambda: selenium.find_element(By.XPATH, '//input[@type="search"]')
        )
        search.send_keys('Inact')
        sleep(1)
        self.wait_for_jquery_done(selenium)
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-projects')
        )
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        assert htmls == [
            [
                '<a href="/projects/3">P3Inactive</a>'
                ' <a href="#" onclick="projectModal(3)">(edit)</a>',
                '$5.34',
                '$3.00',
                '',
                'NO <a onclick="activateProject(3);" href="#">(activate)</a>',
                'ProjectThreeInactive'
            ]
        ]

    def test_03_add_with_standing_budget(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        name = selenium.find_element(By.ID, 'proj_frm_name')
        name.clear()
        name.send_keys('NewP')
        notes = selenium.find_element(By.ID, 'proj_frm_notes')
        notes.clear()
        notes.send_keys('My New Project')
        budget_sel = Select(
            selenium.find_element(By.ID, 'proj_frm_standing_budget_id')
        )
        budget_sel.select_by_visible_text('Standing2')
        btn = selenium.find_element(By.ID, 'formSaveButton')
        btn.click()
        self.wait_for_jquery_done(selenium)
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-projects')
        )
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        assert htmls == [
            [
                '<a href="/projects/4">NewP</a>'
                ' <a href="#" onclick="projectModal(4)">(edit)</a>',
                '$0.00',
                '$0.00',
                'Standing2',
                'yes <a onclick="deactivateProject(4);" href="#">'
                '(deactivate)</a>',
                'My New Project'
            ],
            [
                '<a href="/projects/1">P1</a>'
                ' <a href="#" onclick="projectModal(1)">(edit)</a>',
                '$2,546.89',
                '$77.77',
                'Standing1',
                'yes <a onclick="deactivateProject(1);" href="#">'
                '(deactivate)</a>',
                'ProjectOne'
            ],
            [
                '<a href="/projects/2">P2</a>'
                ' <a href="#" onclick="projectModal(2)">(edit)</a>',
                '$0.00',
                '$0.00',
                '',
                'yes <a onclick="deactivateProject(2);" href="#">'
                '(deactivate)</a>',
                'ProjectTwo'
            ],
            [
                '<a href="/projects/3">P3Inactive</a>'
                ' <a href="#" onclick="projectModal(3)">(edit)</a>',
                '$5.34',
                '$3.00',
                '',
                'NO <a onclick="activateProject(3);" href="#">'
                '(activate)</a>',
                'ProjectThreeInactive'
            ]
        ]

    def test_04_verify_db(self, testdb):
        b = testdb.query(Project).get(1)
        assert b is not None
        assert b.name == 'P1'
        assert b.notes == 'ProjectOne'
        assert b.is_active is True
        standing1 = testdb.query(Budget).filter(
            Budget.name.__eq__('Standing1')
        ).one()
        assert b.standing_budget_id == standing1.id
        b = testdb.query(Project).get(2)
        assert b is not None
        assert b.name == 'P2'
        assert b.notes == 'ProjectTwo'
        assert b.is_active is True
        assert b.standing_budget_id is None
        b = testdb.query(Project).get(3)
        assert b is not None
        assert b.name == 'P3Inactive'
        assert b.notes == 'ProjectThreeInactive'
        assert b.is_active is False
        assert b.standing_budget_id is None
        b = testdb.query(Project).get(4)
        assert b is not None
        assert b.name == 'NewP'
        assert b.notes == 'My New Project'
        assert b.is_active is True
        standing2 = testdb.query(Budget).filter(
            Budget.name.__eq__('Standing2')
        ).one()
        assert b.standing_budget_id == standing2.id
        assert testdb.query(Project).with_entities(
            func.max(Project.id)
        ).scalar() == 4
        assert testdb.query(BoMItem).with_entities(
            func.max(BoMItem.id)
        ).scalar() == 5

    def test_05_add_without_standing_budget(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        name = selenium.find_element(By.ID, 'proj_frm_name')
        name.clear()
        name.send_keys('NewP2')
        notes = selenium.find_element(By.ID, 'proj_frm_notes')
        notes.clear()
        notes.send_keys('No Budget')
        # Leave standing budget as None (default)
        btn = selenium.find_element(By.ID, 'formSaveButton')
        btn.click()
        self.wait_for_jquery_done(selenium)
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-projects')
        )
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        # Just check that NewP2 appears with empty standing budget
        found = False
        for row in htmls:
            if 'NewP2' in row[0]:
                assert row[3] == ''
                found = True
                break
        assert found, 'NewP2 not found in table'

    def test_06_verify_db_no_budget(self, testdb):
        b = testdb.query(Project).get(5)
        assert b is not None
        assert b.name == 'NewP2'
        assert b.notes == 'No Budget'
        assert b.is_active is True
        assert b.standing_budget_id is None

    def test_07_deactivate(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        link = selenium.find_element(By.XPATH,
                                     '//a[@onclick="deactivateProject(1);"]'
                                     )
        link.click()
        self.wait_for_jquery_done(selenium)
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-projects')
        )
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        # P1 should now be inactive
        found = False
        for row in htmls:
            if 'P1</a>' in row[0] and 'projectModal(1)' in row[0]:
                assert 'activate' in row[4].lower()
                assert 'Standing1' in row[3]
                found = True
                break
        assert found, 'P1 not found in table'

    def test_08_verify_db_deactivated(self, testdb):
        b = testdb.query(Project).get(1)
        assert b is not None
        assert b.name == 'P1'
        assert b.notes == 'ProjectOne'
        assert b.is_active is False
        # standing budget should still be linked
        standing1 = testdb.query(Budget).filter(
            Budget.name.__eq__('Standing1')
        ).one()
        assert b.standing_budget_id == standing1.id

    def test_09_activate(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        link = selenium.find_element(By.XPATH,
                                     '//a[@onclick="activateProject(3);"]'
                                     )
        link.click()
        self.wait_for_jquery_done(selenium)
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-projects')
        )
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        # P3Inactive should now be active
        found = False
        for row in htmls:
            if 'P3Inactive' in row[0]:
                assert 'deactivate' in row[4].lower()
                found = True
                break
        assert found, 'P3Inactive not found in table'

    def test_10_verify_db_activated(self, testdb):
        b = testdb.query(Project).get(3)
        assert b is not None
        assert b.name == 'P3Inactive'
        assert b.notes == 'ProjectThreeInactive'
        assert b.is_active is True

    def test_11_edit_modal_populate(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        editlink = selenium.find_element(By.XPATH,
                                         '//a[@onclick="projectModal(1)"]'
                                         )
        modal, title, body = self.try_click_and_get_modal(selenium, editlink)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Project 1'
        assert body.find_element(By.ID, 'proj_frm_id').get_attribute('value') == '1'
        assert body.find_element(By.ID, 'proj_frm_name').get_attribute('value') == 'P1'
        assert body.find_element(By.ID, 'proj_frm_notes').get_attribute('value') == 'ProjectOne'
        standing1 = Select(body.find_element(By.ID, 'proj_frm_standing_budget_id'))
        assert standing1.first_selected_option.text == 'Standing1'

    def test_12_edit_modal_change_budget(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        editlink = selenium.find_element(By.XPATH,
                                         '//a[@onclick="projectModal(1)"]'
                                         )
        modal, title, body = self.try_click_and_get_modal(selenium, editlink)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Project 1'
        # Change standing budget from Standing1 to Standing2
        budget_sel = Select(body.find_element(By.ID, 'proj_frm_standing_budget_id'))
        budget_sel.select_by_visible_text('Standing2')
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Project 1 in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)

    def test_13_verify_db_after_edit(self, testdb):
        b = testdb.query(Project).get(1)
        assert b is not None
        assert b.name == 'P1'
        standing2 = testdb.query(Budget).filter(
            Budget.name.__eq__('Standing2')
        ).one()
        assert b.standing_budget_id == standing2.id

    def test_14_edit_modal_remove_budget(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        editlink = selenium.find_element(By.XPATH,
                                         '//a[@onclick="projectModal(1)"]'
                                         )
        modal, title, body = self.try_click_and_get_modal(selenium, editlink)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Project 1'
        # Remove standing budget (set to None)
        budget_sel = Select(body.find_element(By.ID, 'proj_frm_standing_budget_id'))
        budget_sel.select_by_value('None')
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Project 1 in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)

    def test_15_verify_db_budget_removed(self, testdb):
        b = testdb.query(Project).get(1)
        assert b is not None
        assert b.standing_budget_id is None

    def test_16_table_shows_budget_after_edit(self, base_url, selenium):
        self.get(selenium, base_url + '/projects')
        table = selenium.find_element(By.ID, 'table-projects')
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        # P1 should now have empty standing budget
        found = False
        for row in htmls:
            if 'projectModal(1)' in row[0]:
                assert row[3] == ''
                found = True
                break
        assert found, 'P1 not found in table'
        # NewP (id=4) should still have Standing2
        found = False
        for row in htmls:
            if 'projectModal(4)' in row[0]:
                assert row[3] == 'Standing2'
                found = True
                break
        assert found, 'NewP not found in table'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestOneProjectView(AcceptanceHelper):

    def test_00_verify_db(self, testdb):
        b = testdb.query(Project).get(1)
        assert b is not None
        assert b.name == 'P1'
        assert b.notes == 'ProjectOne'
        assert b.is_active is True
        assert len(
            testdb.query(BoMItem).filter(BoMItem.project_id.__eq__(1)).all()
        ) == 3
        i = testdb.query(BoMItem).get(1)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item1'
        assert i.notes == 'P1Item1Notes'
        assert i.unit_cost == Decimal('11.11')
        assert i.quantity == 1
        assert i.url is None
        assert i.is_active is True
        i = testdb.query(BoMItem).get(2)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item2'
        assert i.notes == 'P1Item2Notes'
        assert i.unit_cost == Decimal('22.22')
        assert i.quantity == 3
        assert i.url == 'http://item2.p1.com'
        assert i.is_active is True
        i = testdb.query(BoMItem).get(3)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item3'
        assert i.notes == 'P1Item3Notes'
        assert i.unit_cost == Decimal('1234.56')
        assert i.quantity == 2
        assert i.url == 'http://item3.p1.com'
        assert i.is_active is False

    def test_01_table(self, base_url, selenium):
        self.get(selenium, base_url + '/projects/1')
        # Top headings
        assert selenium.find_element(By.ID,
                                     'div-notes').get_attribute('innerHTML') == 'ProjectOne'
        assert selenium.find_element(By.ID,
                                     'div-remaining-amount').get_attribute('innerHTML') == '$77.77'
        assert selenium.find_element(By.ID,
                                     'div-total-amount').get_attribute('innerHTML') == '$2,546.89'
        # Table
        table = selenium.find_element(By.ID, 'table-items')
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        assert htmls == [
            [
                '<span style="float: left;">P1Item1</span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(1)">(edit)</a></span>',
                '1',
                '$11.11',
                '$11.11',
                'P1Item1Notes',
                'yes'
            ],
            [
                '<span style="float: left;">'
                '<a href="http://item2.p1.com">P1Item2</a></span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(2)">(edit)</a></span>',
                '3',
                '$22.22',
                '$66.66',
                'P1Item2Notes',
                'yes'
            ],
            [
                '<span style="float: left;">'
                '<a href="http://item3.p1.com">P1Item3</a></span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(3)">(edit)</a></span>',
                '2',
                '$1,234.56',
                '$2,469.12',
                'P1Item3Notes',
                '<span style="color: #a94442;">NO</span>'
            ],
        ]
        rows = self.tbody2trlist(table)
        assert 'inactive' not in rows[0].get_attribute('class')
        assert 'inactive' not in rows[1].get_attribute('class')
        assert 'inactive' in rows[2].get_attribute('class')

    def test_02_search(self, base_url, selenium):
        self.get(selenium, base_url + '/projects/1')
        search = self.retry_stale(
            lambda: selenium.find_element(By.XPATH, '//input[@type="search"]')
        )
        search.send_keys('Item2')
        sleep(1)
        self.wait_for_jquery_done(selenium)
        table = self.retry_stale(
            lambda: selenium.find_element(By.ID, 'table-items')
        )
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        assert htmls == [
            [
                '<span style="float: left;">'
                '<a href="http://item2.p1.com">P1Item2</a></span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(2)">(edit)</a></span>',
                '3',
                '$22.22',
                '$66.66',
                'P1Item2Notes',
                'yes'
            ]
        ]
        rows = self.tbody2trlist(table)
        assert 'inactive' not in rows[0].get_attribute('class')

    def test_03_populate_modal(self, base_url, selenium):
        self.get(selenium, base_url + '/projects/1')
        editlink = selenium.find_element(By.XPATH,
                                         '//a[@onclick="bomItemModal(3)"]'
                                         )
        modal, title, body = self.try_click_and_get_modal(selenium, editlink)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit BoM Item 3'
        id = body.find_element(By.ID, 'bom_frm_id')
        assert id.get_attribute('value') == '3'
        proj_id = body.find_element(By.ID, 'bom_frm_project_id')
        assert proj_id.get_attribute('value') == '1'
        name = body.find_element(By.ID, 'bom_frm_name')
        assert name.get_attribute('value') == 'P1Item3'
        notes = body.find_element(By.ID, 'bom_frm_notes')
        assert notes.get_attribute('value') == 'P1Item3Notes'
        quantity = body.find_element(By.ID, 'bom_frm_quantity')
        assert quantity.get_attribute('value') == '2'
        cost = body.find_element(By.ID, 'bom_frm_unit_cost')
        assert cost.get_attribute('value') == '1234.56'
        url = body.find_element(By.ID, 'bom_frm_url')
        assert url.get_attribute('value') == 'http://item3.p1.com'
        active = body.find_element(By.ID, 'bom_frm_active')
        assert active.is_selected() is False

    def test_04_edit_item(self, base_url, selenium):
        self.get(selenium, base_url + '/projects/1')
        editlink = selenium.find_element(By.XPATH,
                                         '//a[@onclick="bomItemModal(3)"]'
                                         )
        modal, title, body = self.try_click_and_get_modal(selenium, editlink)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit BoM Item 3'
        id = body.find_element(By.ID, 'bom_frm_id')
        assert id.get_attribute('value') == '3'
        proj_id = body.find_element(By.ID, 'bom_frm_project_id')
        assert proj_id.get_attribute('value') == '1'
        name = body.find_element(By.ID, 'bom_frm_name')
        name.send_keys('Edited')
        notes = body.find_element(By.ID, 'bom_frm_notes')
        notes.clear()
        notes.send_keys('Foo')
        quantity = body.find_element(By.ID, 'bom_frm_quantity')
        quantity.clear()
        quantity.send_keys('3')
        cost = body.find_element(By.ID, 'bom_frm_unit_cost')
        cost.clear()
        cost.send_keys('2.22')
        url = body.find_element(By.ID, 'bom_frm_url')
        assert url.get_attribute('value') == 'http://item3.p1.com'
        url.send_keys('/edited')
        active = body.find_element(By.ID, 'bom_frm_active')
        assert active.is_selected() is False
        active.click()
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved BoMItem 3 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # Table
        table = selenium.find_element(By.ID, 'table-items')
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        assert htmls == [
            [
                '<span style="float: left;">P1Item1</span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(1)">(edit)</a></span>',
                '1',
                '$11.11',
                '$11.11',
                'P1Item1Notes',
                'yes'
            ],
            [
                '<span style="float: left;">'
                '<a href="http://item2.p1.com">P1Item2</a></span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(2)">(edit)</a></span>',
                '3',
                '$22.22',
                '$66.66',
                'P1Item2Notes',
                'yes'
            ],
            [
                '<span style="float: left;">'
                '<a href="http://item3.p1.com/edited">P1Item3Edited</a></span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(3)">(edit)</a></span>',
                '3',
                '$2.22',
                '$6.66',
                'Foo',
                'yes'
            ],
        ]
        rows = self.tbody2trlist(table)
        assert 'inactive' not in rows[0].get_attribute('class')
        assert 'inactive' not in rows[1].get_attribute('class')
        assert 'inactive' not in rows[2].get_attribute('class')
        self.wait_for_jquery_done(selenium)
        assert selenium.find_element(By.ID,
                                     'div-notes').get_attribute('innerHTML') == 'ProjectOne'
        assert selenium.find_element(By.ID,
                                     'div-remaining-amount').get_attribute('innerHTML') == '$84.43'
        assert selenium.find_element(By.ID,
                                     'div-total-amount').get_attribute('innerHTML') == '$84.43'

    def test_05_verify_db(self, testdb):
        b = testdb.query(Project).get(1)
        assert b is not None
        assert b.name == 'P1'
        assert b.notes == 'ProjectOne'
        assert b.is_active is True
        assert len(
            testdb.query(BoMItem).filter(BoMItem.project_id.__eq__(1)).all()
        ) == 3
        i = testdb.query(BoMItem).get(1)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item1'
        assert i.notes == 'P1Item1Notes'
        assert i.unit_cost == Decimal('11.11')
        assert i.quantity == 1
        assert i.url is None
        assert i.is_active is True
        i = testdb.query(BoMItem).get(2)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item2'
        assert i.notes == 'P1Item2Notes'
        assert i.unit_cost == Decimal('22.22')
        assert i.quantity == 3
        assert i.url == 'http://item2.p1.com'
        assert i.is_active is True
        i = testdb.query(BoMItem).get(3)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item3Edited'
        assert i.notes == 'Foo'
        assert i.unit_cost == Decimal('2.22')
        assert i.quantity == 3
        assert i.url == 'http://item3.p1.com/edited'
        assert i.is_active is True

    def test_06_add_item(self, base_url, selenium):
        self.get(selenium, base_url + '/projects/1')
        editlink = selenium.find_element(By.ID, 'btn_add_item')
        modal, title, body = self.try_click_and_get_modal(selenium, editlink)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New BoM Item'
        id = body.find_element(By.ID, 'bom_frm_id')
        assert id.get_attribute('value') == ''
        proj_id = body.find_element(By.ID, 'bom_frm_project_id')
        assert proj_id.get_attribute('value') == '1'
        name = body.find_element(By.ID, 'bom_frm_name')
        name.send_keys('NewItem4')
        notes = body.find_element(By.ID, 'bom_frm_notes')
        notes.clear()
        notes.send_keys('FourNotes')
        quantity = body.find_element(By.ID, 'bom_frm_quantity')
        quantity.clear()
        quantity.send_keys('5')
        cost = body.find_element(By.ID, 'bom_frm_unit_cost')
        cost.clear()
        cost.send_keys('12.34')
        url = body.find_element(By.ID, 'bom_frm_url')
        url.send_keys('http://item4.com')
        active = body.find_element(By.ID, 'bom_frm_active')
        assert active.is_selected()
        active.click()
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved BoMItem 6 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # Table
        table = selenium.find_element(By.ID, 'table-items')
        htmls = self.inner_htmls(self.tbody2elemlist(table))
        assert htmls == [
            [
                '<span style="float: left;">P1Item1</span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(1)">(edit)</a></span>',
                '1',
                '$11.11',
                '$11.11',
                'P1Item1Notes',
                'yes'
            ],
            [
                '<span style="float: left;">'
                '<a href="http://item2.p1.com">P1Item2</a></span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(2)">(edit)</a></span>',
                '3',
                '$22.22',
                '$66.66',
                'P1Item2Notes',
                'yes'
            ],
            [
                '<span style="float: left;">'
                '<a href="http://item3.p1.com/edited">P1Item3Edited</a></span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(3)">(edit)</a></span>',
                '3',
                '$2.22',
                '$6.66',
                'Foo',
                'yes'
            ],
            [
                '<span style="float: left;">'
                '<a href="http://item4.com">NewItem4</a></span>'
                '<span style="float: right;">'
                '<a href="#" onclick="bomItemModal(6)">(edit)</a></span>',
                '5',
                '$12.34',
                '$61.70',
                'FourNotes',
                '<span style="color: #a94442;">NO</span>'
            ]
        ]
        rows = self.tbody2trlist(table)
        assert 'inactive' not in rows[0].get_attribute('class')
        assert 'inactive' not in rows[1].get_attribute('class')
        assert 'inactive' not in rows[2].get_attribute('class')
        assert selenium.find_element(By.ID,
                                     'div-notes').get_attribute('innerHTML') == 'ProjectOne'
        assert selenium.find_element(By.ID,
                                     'div-remaining-amount').get_attribute('innerHTML') == '$84.43'
        assert selenium.find_element(By.ID,
                                     'div-total-amount').get_attribute('innerHTML') == '$146.13'

    def test_07_verify_db(self, testdb):
        b = testdb.query(Project).get(1)
        assert b is not None
        assert b.name == 'P1'
        assert b.notes == 'ProjectOne'
        assert b.is_active is True
        assert len(
            testdb.query(BoMItem).filter(BoMItem.project_id.__eq__(1)).all()
        ) == 4
        i = testdb.query(BoMItem).get(1)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item1'
        assert i.notes == 'P1Item1Notes'
        assert i.unit_cost == Decimal('11.11')
        assert i.quantity == 1
        assert i.url is None
        assert i.is_active is True
        i = testdb.query(BoMItem).get(2)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item2'
        assert i.notes == 'P1Item2Notes'
        assert i.unit_cost == Decimal('22.22')
        assert i.quantity == 3
        assert i.url == 'http://item2.p1.com'
        assert i.is_active is True
        i = testdb.query(BoMItem).get(3)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'P1Item3Edited'
        assert i.notes == 'Foo'
        assert i.unit_cost == Decimal('2.22')
        assert i.quantity == 3
        assert i.url == 'http://item3.p1.com/edited'
        assert i.is_active is True
        i = testdb.query(BoMItem).get(6)
        assert i is not None
        assert i.project_id == 1
        assert i.name == 'NewItem4'
        assert i.notes == 'FourNotes'
        assert i.unit_cost == Decimal('12.34')
        assert i.quantity == 5
        assert i.url == 'http://item4.com'
        assert i.is_active is False
