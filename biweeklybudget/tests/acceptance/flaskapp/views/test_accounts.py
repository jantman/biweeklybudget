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
from biweeklybudget.models.account import Account, AcctType


@pytest.mark.acceptance
class TestAccountsNavigation(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/accounts')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'Accounts - BiweeklyBudget'

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
class TestAccountsMainPage(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/accounts')

    def test_bank_table(self, selenium):
        table = selenium.find_element_by_xpath(
            "//div[@id='panel-bank-accounts']//table"
        )
        assert self.thead2list(table) == [
            'Account', 'Balance', 'Unreconciled', 'Difference'
        ]
        assert self.tbody2textlist(table) == [
            ['BankOne', '$12,789.01 (14 hours ago)', '$0.00', '$12,789.01'],
            ['BankTwoStale', '$100.23 (18 days ago)', '-$333.33', '$433.56']
        ]
        links = []
        tbody = table.find_element_by_tag_name('tbody')
        for tr in tbody.find_elements_by_tag_name('tr'):
            td = tr.find_elements_by_tag_name('td')[0]
            links.append(td.get_attribute('innerHTML'))
        assert links == [
            '<a href="javascript:accountModal(1, null)">BankOne</a>',
            '<a href="javascript:accountModal(2, null)">BankTwoStale</a>',
        ]

    def test_bank_stale_span(self, selenium):
        tbody = selenium.find_element_by_xpath(
            "//div[@id='panel-bank-accounts']//table/tbody"
        )
        rows = tbody.find_elements_by_tag_name('tr')
        bankTwoStale_bal_td = rows[1].find_elements_by_tag_name('td')[1]
        bal_span = bankTwoStale_bal_td.find_elements_by_tag_name('span')[1]
        assert bal_span.text == '(18 days ago)'
        assert bal_span.get_attribute('class') == 'data_age text-danger'

    def test_credit_table(self, selenium):
        table = selenium.find_element_by_xpath(
            "//div[@id='panel-credit-cards']//table"
        )
        assert self.thead2list(table) == [
            'Account', 'Balance', 'Credit Limit', 'Available', 'Unreconciled',
            'Difference'
        ]
        assert self.tbody2textlist(table) == [
            [
                'CreditOne', '-$952.06 (13 hours ago)', '$2,000.00',
                '$1,047.94', '$222.22', '$825.72'
            ],
            [
                'CreditTwo', '-$5,498.65 (a day ago)', '$5,500.00', '$1.35',
                '$0.00', '$1.35'
            ]
        ]
        links = []
        tbody = table.find_element_by_tag_name('tbody')
        for tr in tbody.find_elements_by_tag_name('tr'):
            td = tr.find_elements_by_tag_name('td')[0]
            links.append(td.get_attribute('innerHTML'))
        assert links == [
            '<a href="javascript:accountModal(3, null)">CreditOne</a>',
            '<a href="javascript:accountModal(4, null)">CreditTwo</a>',
        ]

    def test_investment_table(self, selenium):
        table = selenium.find_element_by_xpath(
            "//div[@id='panel-investment']//table"
        )
        assert self.thead2list(table) == ['Account', 'Value']
        assert self.tbody2textlist(table) == [
            ['InvestmentOne', '$10,362.91 (13 days ago)']
        ]
        links = []
        tbody = table.find_element_by_tag_name('tbody')
        for tr in tbody.find_elements_by_tag_name('tr'):
            td = tr.find_elements_by_tag_name('td')[0]
            links.append(td.get_attribute('innerHTML'))
        assert links == [
            '<a href="javascript:accountModal(5, null)">InvestmentOne</a>'
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestAccountModal(AcceptanceHelper):

    def test_00_verify_db(self, testdb):
        a1 = testdb.query(Account).get(1)
        assert a1 is not None
        assert a1.name == 'BankOne'
        assert a1.description == 'First Bank Account'
        assert a1.ofx_cat_memo_to_name is True
        assert a1.vault_creds_path == 'secret/foo/bar/BankOne'
        assert a1.ofxgetter_config_json == '{"foo": "bar"}'
        assert a1.negate_ofx_amounts is False
        assert a1.reconcile_trans is True
        assert a1.acct_type == AcctType.Bank
        assert a1.credit_limit is None
        assert a1.apr is None
        assert a1.prime_rate_margin is None
        assert a1.interest_class_name is None
        assert a1.min_payment_class_name is None
        assert a1.is_active is True

    def test_01_get_acct1_by_url(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/1')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 1'
        assert selenium.find_element_by_id('account_frm_name').get_attribute(
            'value') == 'BankOne'
        assert selenium.find_element_by_id(
            'account_frm_description'
        ).get_attribute('value') == 'First Bank Account'
        assert selenium.find_element_by_id(
            'account_frm_type_bank').is_selected()
        assert selenium.find_element_by_id(
            'account_frm_type_credit').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_investment').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_ofx_cat_memo').is_selected()
        assert selenium.find_element_by_id(
            'account_frm_vault_creds_path'
        ).get_attribute('value') == 'secret/foo/bar/BankOne'
        assert selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).get_attribute('value') == '{"foo": "bar"}'
        assert selenium.find_element_by_id(
            'account_frm_negate_ofx').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_reconcile_trans').is_selected() is True
        # BEGIN CREDIT
        assert selenium.find_element_by_id(
            'account_frm_credit_limit').is_displayed() is False
        assert selenium.find_element_by_id(
            'account_frm_apr').is_displayed() is False
        assert selenium.find_element_by_id(
            'account_frm_margin').is_displayed() is False
        assert selenium.find_element_by_id(
            'account_frm_int_class_name').is_displayed() is False
        assert selenium.find_element_by_id(
            'account_frm_min_pay_class_name').is_displayed() is False
        # END CREDIT
        assert selenium.find_element_by_id('account_frm_active').is_selected()

    def test_02_get_acct2_click(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_xpath('//a[text()="BankTwoStale"]')
        link.click()
