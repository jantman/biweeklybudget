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
from decimal import Decimal
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.models.transaction import Transaction
from selenium.webdriver.support.ui import Select
from biweeklybudget.utils import dtnow
import requests
from time import sleep


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestAccountsNavigation(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
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
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestAccountsMainPage(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
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
                '$1,047.94', '$544.54', '$503.40'
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
@pytest.mark.incremental
class TestAccountModal(AcceptanceHelper):

    def test_10_verify_db(self, testdb):
        acct = testdb.query(Account).get(1)
        assert acct is not None
        assert acct.name == 'BankOne'
        assert acct.description == 'First Bank Account'
        assert acct.ofx_cat_memo_to_name is True
        assert acct.vault_creds_path == 'secret/foo/bar/BankOne'
        assert acct.ofxgetter_config_json == '{"foo": "bar"}'
        assert acct.negate_ofx_amounts is False
        assert acct.reconcile_trans is True
        assert acct.acct_type == AcctType.Bank
        assert acct.credit_limit is None
        assert acct.apr is None
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name is None
        assert acct.min_payment_class_name is None
        assert acct.is_active is True
        assert acct.re_interest_charge == '^interest-charge'
        assert acct.re_interest_paid == '^interest-paid'
        assert acct.re_payment == '^(payment|thank you)'
        assert acct.re_late_fee == '^Late Fee'
        assert acct.re_other_fee == '^re-other-fee'
        assert acct.plaid_item_id == 'PlaidItem1'
        assert acct.plaid_account_id == 'PlaidAcct1'

    def test_11_get_acct1_url(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/1')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 1'
        assert selenium.find_element_by_id('account_frm_id').get_attribute(
            'value') == '1'
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
        # BEGIN REs
        assert selenium.find_element_by_id(
            'account_frm_re_interest_charge'
        ).get_attribute('value') == '^interest-charge'
        assert selenium.find_element_by_id(
            'account_frm_re_interest_paid'
        ).get_attribute('value') == '^interest-paid'
        assert selenium.find_element_by_id(
            'account_frm_re_payment'
        ).get_attribute('value') == '^(payment|thank you)'
        assert selenium.find_element_by_id(
            'account_frm_re_late_fee'
        ).get_attribute('value') == '^Late Fee'
        assert selenium.find_element_by_id(
            'account_frm_re_other_fee'
        ).get_attribute('value') == '^re-other-fee'
        # END REs
        assert Select(
            selenium.find_element_by_id('account_frm_plaid_account')
        ).first_selected_option.get_attribute(
            'value'
        ) == 'PlaidItem1,PlaidAcct1'
        assert selenium.find_element_by_id('account_frm_active').is_selected()

    def test_12_edit_acct1(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/1')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 1'
        selenium.find_element_by_id('account_frm_name').send_keys('Edited')
        selenium.find_element_by_id('account_frm_plaid_account')
        Select(
            selenium.find_element_by_id('account_frm_plaid_account')
        ).select_by_value('PlaidItem1,PlaidAcct4')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Account 1 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()

    def test_13_verify_db(self, testdb):
        acct = testdb.query(Account).get(1)
        assert acct is not None
        assert acct.name == 'BankOneEdited'
        assert acct.description == 'First Bank Account'
        assert acct.ofx_cat_memo_to_name is True
        assert acct.vault_creds_path == 'secret/foo/bar/BankOne'
        assert acct.ofxgetter_config_json == '{"foo": "bar"}'
        assert acct.negate_ofx_amounts is False
        assert acct.reconcile_trans is True
        assert acct.acct_type == AcctType.Bank
        assert acct.credit_limit is None
        assert acct.apr is None
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name is None
        assert acct.min_payment_class_name is None
        assert acct.is_active is True
        assert acct.plaid_item_id == 'PlaidItem1'
        assert acct.plaid_account_id == 'PlaidAcct4'

    def test_20_verify_db(self, testdb):
        acct = testdb.query(Account).get(2)
        assert acct is not None
        assert acct.name == 'BankTwoStale'
        assert acct.description == 'Stale Bank Account'
        assert acct.ofx_cat_memo_to_name is False
        assert acct.vault_creds_path == 'secret/foo/bar/BankTwo'
        assert acct.ofxgetter_config_json == '{"foo": "baz"}'
        assert acct.negate_ofx_amounts is True
        assert acct.reconcile_trans is True
        assert acct.acct_type == AcctType.Bank
        assert acct.credit_limit is None
        assert acct.apr is None
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name is None
        assert acct.min_payment_class_name is None
        assert acct.is_active is True
        assert acct.re_interest_charge is None
        assert acct.re_interest_paid is None
        assert acct.re_payment is None
        assert acct.re_late_fee is None
        assert acct.re_other_fee is None
        assert acct.plaid_item_id is None
        assert acct.plaid_account_id is None

    def test_21_get_acct2_click(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_xpath('//a[text()="BankTwoStale"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 2'
        assert selenium.find_element_by_id('account_frm_id').get_attribute(
            'value') == '2'
        assert selenium.find_element_by_id('account_frm_name').get_attribute(
            'value') == 'BankTwoStale'
        assert selenium.find_element_by_id(
            'account_frm_description'
        ).get_attribute('value') == 'Stale Bank Account'
        assert selenium.find_element_by_id(
            'account_frm_type_bank').is_selected()
        assert selenium.find_element_by_id(
            'account_frm_type_credit').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_investment').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_ofx_cat_memo').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_vault_creds_path'
        ).get_attribute('value') == 'secret/foo/bar/BankTwo'
        assert selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).get_attribute('value') == '{"foo": "baz"}'
        assert selenium.find_element_by_id(
            'account_frm_negate_ofx').is_selected() is True
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
        # BEGIN REs
        assert selenium.find_element_by_id(
            'account_frm_re_interest_charge'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_re_interest_paid'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_re_payment'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_re_late_fee'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_re_other_fee'
        ).get_attribute('value') == ''
        # END REs
        assert Select(
            selenium.find_element_by_id('account_frm_plaid_account')
        ).first_selected_option.get_attribute(
            'value'
        ) == 'null,null'
        assert selenium.find_element_by_id('account_frm_active').is_selected()

    def test_22_edit_acct2(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_xpath('//a[text()="BankTwoStale"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 2'
        selenium.find_element_by_id('account_frm_name').send_keys('Edited')
        selenium.find_element_by_id('account_frm_description').clear()
        selenium.find_element_by_id('account_frm_description').send_keys(
            'a2desc'
        )
        selenium.find_element_by_id('account_frm_ofx_cat_memo').click()
        selenium.find_element_by_id('account_frm_vault_creds_path').send_keys(
            '/baz'
        )
        selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).clear()
        selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).send_keys('{"key": "value"}')
        selenium.find_element_by_id('account_frm_negate_ofx').click()
        selenium.find_element_by_id('account_frm_reconcile_trans').click()
        selenium.find_element_by_id('account_frm_active').click()
        # BEGIN REs
        selenium.find_element_by_id(
            'account_frm_re_interest_charge'
        ).send_keys('my-re-ic$')
        selenium.find_element_by_id(
            'account_frm_re_interest_paid'
        ).send_keys('my-re-ip$')
        selenium.find_element_by_id(
            'account_frm_re_payment'
        ).send_keys('my-re-p$')
        selenium.find_element_by_id(
            'account_frm_re_late_fee'
        ).send_keys('my-re-lf$')
        # END REs
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Account 2 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()

    def test_23_verify_db(self, testdb):
        acct = testdb.query(Account).get(2)
        assert acct is not None
        assert acct.name == 'BankTwoStaleEdited'
        assert acct.description == 'a2desc'
        assert acct.ofx_cat_memo_to_name is True
        assert acct.vault_creds_path == 'secret/foo/bar/BankTwo/baz'
        assert acct.ofxgetter_config_json == '{"key": "value"}'
        assert acct.negate_ofx_amounts is False
        assert acct.reconcile_trans is False
        assert acct.acct_type == AcctType.Bank
        assert acct.credit_limit is None
        assert acct.apr is None
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name is None
        assert acct.min_payment_class_name is None
        assert acct.is_active is False
        assert acct.re_interest_charge == 'my-re-ic$'
        assert acct.re_interest_paid == 'my-re-ip$'
        assert acct.re_payment == 'my-re-p$'
        assert acct.re_late_fee == 'my-re-lf$'
        assert acct.re_other_fee is None
        assert acct.plaid_item_id is None
        assert acct.plaid_account_id is None

    def test_30_verify_db(self, testdb):
        acct = testdb.query(Account).get(3)
        assert acct is not None
        assert acct.name == 'CreditOne'
        assert acct.description == 'First Credit Card, limit 2000'
        assert acct.ofx_cat_memo_to_name is False
        assert acct.vault_creds_path is None
        assert acct.ofxgetter_config_json is None
        assert acct.negate_ofx_amounts is True
        assert acct.reconcile_trans is True
        assert acct.acct_type == AcctType.Credit
        assert acct.credit_limit == Decimal('2000.0')
        assert acct.apr is None
        assert acct.prime_rate_margin == Decimal('0.005')
        assert acct.interest_class_name == 'AdbCompoundedDaily'
        assert acct.min_payment_class_name == 'MinPaymentAmEx'
        assert acct.is_active is True
        assert acct.re_interest_charge == '^INTEREST CHARGED TO'
        assert acct.re_interest_paid is None
        assert acct.re_payment == '.*Online Payment, thank you.*'
        assert acct.re_late_fee == '^Late Fee'
        assert acct.re_other_fee == '^re-other-fee'
        assert acct.plaid_item_id == 'PlaidItem1'
        assert acct.plaid_account_id == 'PlaidAcct2'

    def test_31_get_acct3_click(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_xpath('//a[text()="CreditOne"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 3'
        assert selenium.find_element_by_id('account_frm_id').get_attribute(
            'value') == '3'
        assert selenium.find_element_by_id('account_frm_name').get_attribute(
            'value') == 'CreditOne'
        assert selenium.find_element_by_id(
            'account_frm_description'
        ).get_attribute('value') == 'First Credit Card, limit 2000'
        assert selenium.find_element_by_id(
            'account_frm_type_bank').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_credit').is_selected()
        assert selenium.find_element_by_id(
            'account_frm_type_investment').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_ofx_cat_memo').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_vault_creds_path'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_negate_ofx').is_selected()
        assert selenium.find_element_by_id(
            'account_frm_reconcile_trans').is_selected()
        # BEGIN CREDIT
        assert selenium.find_element_by_id(
            'account_frm_credit_limit').is_displayed()
        assert selenium.find_element_by_id(
            'account_frm_credit_limit').get_attribute('value') == '2000'
        assert selenium.find_element_by_id(
            'account_frm_apr').is_displayed()
        assert selenium.find_element_by_id(
            'account_frm_apr').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_margin').is_displayed()
        assert selenium.find_element_by_id(
            'account_frm_margin').get_attribute('value') == '0.005'
        assert selenium.find_element_by_id(
            'account_frm_int_class_name').is_displayed()
        assert Select(selenium.find_element_by_id(
            'account_frm_int_class_name')
        ).first_selected_option.get_attribute('value') == 'AdbCompoundedDaily'
        assert selenium.find_element_by_id(
            'account_frm_min_pay_class_name').is_displayed()
        assert Select(selenium.find_element_by_id(
            'account_frm_min_pay_class_name')
        ).first_selected_option.get_attribute('value') == 'MinPaymentAmEx'
        # END CREDIT
        assert Select(
            selenium.find_element_by_id('account_frm_plaid_account')
        ).first_selected_option.get_attribute(
            'value'
        ) == 'PlaidItem1,PlaidAcct2'
        assert selenium.find_element_by_id('account_frm_active').is_selected()

    def test_32_edit_acct3(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_xpath('//a[text()="CreditOne"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 3'
        selenium.find_element_by_id('account_frm_name').send_keys('Edited')
        selenium.find_element_by_id('account_frm_margin').clear()
        selenium.find_element_by_id('account_frm_margin').send_keys('4.21')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Account 3 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()

    def test_33_verify_db(self, testdb):
        acct = testdb.query(Account).get(3)
        assert acct is not None
        assert acct.name == 'CreditOneEdited'
        assert acct.description == 'First Credit Card, limit 2000'
        assert acct.ofx_cat_memo_to_name is False
        assert acct.vault_creds_path is None
        assert acct.ofxgetter_config_json is None
        assert acct.negate_ofx_amounts is True
        assert acct.reconcile_trans is True
        assert acct.acct_type == AcctType.Credit
        assert acct.credit_limit == Decimal('2000.0')
        assert acct.apr is None
        assert acct.prime_rate_margin == Decimal('0.0421')
        assert acct.interest_class_name == 'AdbCompoundedDaily'
        assert acct.min_payment_class_name == 'MinPaymentAmEx'
        assert acct.is_active is True
        assert acct.re_interest_charge == '^INTEREST CHARGED TO'
        assert acct.re_interest_paid is None
        assert acct.re_payment == '.*Online Payment, thank you.*'
        assert acct.re_late_fee == '^Late Fee'
        assert acct.re_other_fee == '^re-other-fee'
        assert acct.plaid_item_id == 'PlaidItem1'
        assert acct.plaid_account_id == 'PlaidAcct2'

    def test_40_verify_db(self, testdb):
        acct = testdb.query(Account).get(4)
        assert acct is not None
        assert acct.name == 'CreditTwo'
        assert acct.description == 'Credit 2 limit 5500'
        assert acct.ofx_cat_memo_to_name is False
        assert acct.vault_creds_path == '/foo/bar'
        assert acct.ofxgetter_config_json == ''
        assert acct.negate_ofx_amounts is False
        assert acct.reconcile_trans is True
        assert acct.acct_type == AcctType.Credit
        assert acct.credit_limit == Decimal('5500.0')
        assert acct.apr == Decimal('0.1')
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name == 'AdbCompoundedDaily'
        assert acct.min_payment_class_name == 'MinPaymentDiscover'
        assert acct.is_active is True
        assert acct.re_interest_charge is None
        assert acct.re_interest_paid is None
        assert acct.re_payment is None
        assert acct.re_late_fee is None
        assert acct.re_other_fee is None

    def test_41_get_acct4_url(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/4')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 4'
        assert selenium.find_element_by_id('account_frm_id').get_attribute(
            'value') == '4'
        assert selenium.find_element_by_id('account_frm_name').get_attribute(
            'value') == 'CreditTwo'
        assert selenium.find_element_by_id(
            'account_frm_description'
        ).get_attribute('value') == 'Credit 2 limit 5500'
        assert selenium.find_element_by_id(
            'account_frm_type_bank').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_credit').is_selected()
        assert selenium.find_element_by_id(
            'account_frm_type_investment').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_ofx_cat_memo').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_vault_creds_path'
        ).get_attribute('value') == '/foo/bar'
        assert selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_negate_ofx').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_reconcile_trans').is_selected()
        # BEGIN CREDIT
        assert selenium.find_element_by_id(
            'account_frm_credit_limit').is_displayed()
        assert selenium.find_element_by_id(
            'account_frm_credit_limit').get_attribute('value') == '5500'
        assert selenium.find_element_by_id(
            'account_frm_apr').is_displayed()
        assert selenium.find_element_by_id(
            'account_frm_apr').get_attribute('value') == '0.1'
        assert selenium.find_element_by_id(
            'account_frm_margin').is_displayed()
        assert selenium.find_element_by_id(
            'account_frm_margin').get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_int_class_name').is_displayed()
        assert Select(selenium.find_element_by_id(
            'account_frm_int_class_name')
        ).first_selected_option.get_attribute('value') == 'AdbCompoundedDaily'
        assert selenium.find_element_by_id(
            'account_frm_min_pay_class_name').is_displayed()
        assert Select(selenium.find_element_by_id(
            'account_frm_min_pay_class_name')
        ).first_selected_option.get_attribute('value') == 'MinPaymentDiscover'
        # END CREDIT
        assert selenium.find_element_by_id('account_frm_active').is_selected()

    def test_42_edit_acct4(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts/4')
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 4'
        selenium.find_element_by_id('account_frm_name').send_keys('Edited')
        selenium.find_element_by_id('account_frm_description').clear()
        selenium.find_element_by_id('account_frm_description').send_keys(
            'a4desc'
        )
        selenium.find_element_by_id('account_frm_ofx_cat_memo').click()
        selenium.find_element_by_id('account_frm_vault_creds_path').send_keys(
            '/baz'
        )
        selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).clear()
        selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).send_keys('{"key": "value"}')
        selenium.find_element_by_id('account_frm_negate_ofx').click()
        selenium.find_element_by_id('account_frm_reconcile_trans').click()
        # BEGIN CREDIT
        selenium.find_element_by_id('account_frm_credit_limit').clear()
        selenium.find_element_by_id('account_frm_credit_limit').send_keys(
            '123.45'
        )
        selenium.find_element_by_id('account_frm_apr').clear()
        selenium.find_element_by_id('account_frm_apr').send_keys('45.67')
        selenium.find_element_by_id('account_frm_margin').clear()
        Select(selenium.find_element_by_id(
            'account_frm_int_class_name')
        ).select_by_value('AdbCompoundedDaily')
        Select(selenium.find_element_by_id(
            'account_frm_min_pay_class_name')
        ).select_by_value('MinPaymentCiti')
        # END CREDIT
        selenium.find_element_by_id('account_frm_active').click()
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Account 4 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()

    def test_43_verify_db(self, testdb):
        acct = testdb.query(Account).get(4)
        assert acct is not None
        assert acct.name == 'CreditTwoEdited'
        assert acct.description == 'a4desc'
        assert acct.ofx_cat_memo_to_name is True
        assert acct.vault_creds_path == '/foo/bar/baz'
        assert acct.ofxgetter_config_json == '{"key": "value"}'
        assert acct.negate_ofx_amounts is True
        assert acct.reconcile_trans is False
        assert acct.acct_type == AcctType.Credit
        assert acct.credit_limit == Decimal('123.45')
        assert acct.apr == Decimal('0.4567')
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name == 'AdbCompoundedDaily'
        assert acct.min_payment_class_name == 'MinPaymentCiti'
        assert acct.is_active is False
        assert acct.re_interest_charge is None
        assert acct.re_interest_paid is None
        assert acct.re_payment is None
        assert acct.re_late_fee is None
        assert acct.re_other_fee is None

    def test_50_verify_db(self, testdb):
        acct = testdb.query(Account).get(5)
        assert acct is not None
        assert acct.name == 'InvestmentOne'
        assert acct.description == 'Investment One Stale'
        assert acct.ofx_cat_memo_to_name is False
        assert acct.vault_creds_path == ''
        assert acct.ofxgetter_config_json == ''
        assert acct.negate_ofx_amounts is False
        assert acct.reconcile_trans is False
        assert acct.acct_type == AcctType.Investment
        assert acct.credit_limit is None
        assert acct.apr is None
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name is None
        assert acct.min_payment_class_name is None
        assert acct.is_active is True
        assert acct.re_interest_charge is None
        assert acct.re_interest_paid is None
        assert acct.re_payment is None
        assert acct.re_late_fee is None
        assert acct.re_other_fee is None

    def test_51_get_acct5_click(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_xpath('//a[text()="InvestmentOne"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 5'
        assert selenium.find_element_by_id('account_frm_id').get_attribute(
            'value') == '5'
        assert selenium.find_element_by_id('account_frm_name').get_attribute(
            'value') == 'InvestmentOne'
        assert selenium.find_element_by_id(
            'account_frm_description'
        ).get_attribute('value') == 'Investment One Stale'
        assert selenium.find_element_by_id(
            'account_frm_type_bank').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_credit').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_investment').is_selected()
        assert selenium.find_element_by_id(
            'account_frm_ofx_cat_memo').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_vault_creds_path'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_negate_ofx').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_reconcile_trans').is_selected() is False
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

    def test_52_edit_acct5(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_xpath('//a[text()="InvestmentOne"]')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Account 5'
        selenium.find_element_by_id('account_frm_name').send_keys('Edited')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Account 5 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()

    def test_53_verify_db(self, testdb):
        acct = testdb.query(Account).get(5)
        assert acct is not None
        assert acct.name == 'InvestmentOneEdited'
        assert acct.description == 'Investment One Stale'
        assert acct.ofx_cat_memo_to_name is False
        assert acct.vault_creds_path is None
        assert acct.ofxgetter_config_json is None
        assert acct.negate_ofx_amounts is False
        assert acct.reconcile_trans is False
        assert acct.acct_type == AcctType.Investment
        assert acct.credit_limit is None
        assert acct.apr is None
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name is None
        assert acct.min_payment_class_name is None
        assert acct.is_active is True
        assert acct.re_interest_charge is None
        assert acct.re_interest_paid is None
        assert acct.re_payment is None
        assert acct.re_late_fee is None
        assert acct.re_other_fee is None

    def test_60_verify_db(self, testdb):
        max_id = max([
            t.id for t in testdb.query(Account).all()
        ])
        assert max_id == 6

    def test_61_modal_add_bank(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_id('btn_add_acct_bank')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Account'
        assert selenium.find_element_by_id('account_frm_id').get_attribute(
            'value') == ''
        assert selenium.find_element_by_id('account_frm_name').get_attribute(
            'value') == ''
        assert selenium.find_element_by_id(
            'account_frm_description'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_type_bank').is_selected() is True
        assert selenium.find_element_by_id(
            'account_frm_type_credit').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_investment').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_ofx_cat_memo').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_vault_creds_path'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_negate_ofx').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_reconcile_trans').is_selected()
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
        assert selenium.find_element_by_id(
            'account_frm_active').is_selected() is True
        selenium.find_element_by_id('account_frm_name').send_keys('Acct7')
        selenium.find_element_by_id('account_frm_description').clear()
        selenium.find_element_by_id('account_frm_description').send_keys(
            'a7desc'
        )
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Account 7 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()

    def test_62_verify_db(self, testdb):
        acct = testdb.query(Account).get(7)
        assert acct is not None
        assert acct.name == 'Acct7'
        assert acct.description == 'a7desc'
        assert acct.ofx_cat_memo_to_name is False
        assert acct.vault_creds_path is None
        assert acct.ofxgetter_config_json is None
        assert acct.negate_ofx_amounts is False
        assert acct.reconcile_trans is True
        assert acct.acct_type == AcctType.Bank
        assert acct.credit_limit is None
        assert acct.apr is None
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name is None
        assert acct.min_payment_class_name is None
        assert acct.is_active is True
        assert acct.re_interest_charge is None
        assert acct.re_interest_paid is None
        assert acct.re_payment is None
        assert acct.re_late_fee is None
        assert acct.re_other_fee is None

    def test_70_verify_db(self, testdb):
        max_id = max([
            t.id for t in testdb.query(Account).all()
        ])
        assert max_id == 7

    def test_71_modal_add_credit(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_id('btn_add_acct_credit')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Account'
        assert selenium.find_element_by_id('account_frm_id').get_attribute(
            'value') == ''
        assert selenium.find_element_by_id('account_frm_name').get_attribute(
            'value') == ''
        assert selenium.find_element_by_id(
            'account_frm_description'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_type_bank').is_selected() is True
        assert selenium.find_element_by_id(
            'account_frm_type_credit').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_investment').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_ofx_cat_memo').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_vault_creds_path'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_negate_ofx').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_reconcile_trans').is_selected()
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
        assert selenium.find_element_by_id(
            'account_frm_active').is_selected() is True
        selenium.find_element_by_id('account_frm_name').send_keys('Acct8')
        selenium.find_element_by_id('account_frm_description').clear()
        selenium.find_element_by_id('account_frm_description').send_keys(
            'a8desc'
        )
        selenium.find_element_by_id('account_frm_type_credit').click()
        selenium.find_element_by_id('account_frm_ofx_cat_memo').click()
        selenium.find_element_by_id('account_frm_vault_creds_path').send_keys(
            '/path/to/creds'
        )
        selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).send_keys('{"foo": "blam"}')
        selenium.find_element_by_id('account_frm_negate_ofx').click()
        selenium.find_element_by_id('account_frm_reconcile_trans').click()
        # BEGIN CREDIT
        selenium.find_element_by_id('account_frm_credit_limit').clear()
        selenium.find_element_by_id('account_frm_credit_limit').send_keys(
            '987.65'
        )
        selenium.find_element_by_id('account_frm_apr').clear()
        selenium.find_element_by_id('account_frm_apr').send_keys('45.67')
        selenium.find_element_by_id('account_frm_margin').clear()
        Select(selenium.find_element_by_id(
            'account_frm_int_class_name')
        ).select_by_value('AdbCompoundedDaily')
        Select(selenium.find_element_by_id(
            'account_frm_min_pay_class_name')
        ).select_by_value('MinPaymentCiti')
        # END CREDIT
        selenium.find_element_by_id('account_frm_active').click()
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Account 8 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()

    def test_72_verify_db(self, testdb):
        acct = testdb.query(Account).get(8)
        assert acct is not None
        assert acct.name == 'Acct8'
        assert acct.description == 'a8desc'
        assert acct.ofx_cat_memo_to_name is True
        assert acct.vault_creds_path == '/path/to/creds'
        assert acct.ofxgetter_config_json == '{"foo": "blam"}'
        assert acct.negate_ofx_amounts is True
        assert acct.reconcile_trans is False
        assert acct.acct_type == AcctType.Credit
        assert acct.credit_limit == Decimal('987.65')
        assert acct.apr == Decimal('0.4567')
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name == 'AdbCompoundedDaily'
        assert acct.min_payment_class_name == 'MinPaymentCiti'
        assert acct.is_active is False
        assert acct.re_interest_charge is None
        assert acct.re_interest_paid is None
        assert acct.re_payment is None
        assert acct.re_late_fee is None
        assert acct.re_other_fee is None

    def test_80_verify_db(self, testdb):
        max_id = max([
            t.id for t in testdb.query(Account).all()
        ])
        assert max_id == 8

    def test_81_modal_add_bank(self, base_url, selenium):
        self.get(selenium, base_url + '/accounts')
        link = selenium.find_element_by_id('btn_add_acct_invest')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add New Account'
        assert selenium.find_element_by_id('account_frm_id').get_attribute(
            'value') == ''
        assert selenium.find_element_by_id('account_frm_name').get_attribute(
            'value') == ''
        assert selenium.find_element_by_id(
            'account_frm_description'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_type_bank').is_selected() is True
        assert selenium.find_element_by_id(
            'account_frm_type_credit').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_type_investment').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_ofx_cat_memo').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_vault_creds_path'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_ofxgetter_config_json'
        ).get_attribute('value') == ''
        assert selenium.find_element_by_id(
            'account_frm_negate_ofx').is_selected() is False
        assert selenium.find_element_by_id(
            'account_frm_reconcile_trans').is_selected()
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
        assert selenium.find_element_by_id(
            'account_frm_active').is_selected() is True
        selenium.find_element_by_id('account_frm_name').send_keys('Acct9')
        selenium.find_element_by_id('account_frm_description').clear()
        selenium.find_element_by_id('account_frm_description').send_keys(
            'a9desc'
        )
        selenium.find_element_by_id('account_frm_type_investment').click()
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Account 9 in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()

    def test_82_verify_db(self, testdb):
        acct = testdb.query(Account).get(9)
        assert acct is not None
        assert acct.name == 'Acct9'
        assert acct.description == 'a9desc'
        assert acct.ofx_cat_memo_to_name is False
        assert acct.vault_creds_path is None
        assert acct.ofxgetter_config_json is None
        assert acct.negate_ofx_amounts is False
        assert acct.reconcile_trans is True
        assert acct.acct_type == AcctType.Investment
        assert acct.credit_limit is None
        assert acct.apr is None
        assert acct.prime_rate_margin is None
        assert acct.interest_class_name is None
        assert acct.min_payment_class_name is None
        assert acct.is_active is True
        assert acct.re_interest_charge is None
        assert acct.re_interest_paid is None
        assert acct.re_payment is None
        assert acct.re_late_fee is None
        assert acct.re_other_fee is None
        assert acct.plaid_item_id is None
        assert acct.plaid_account_id is None


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestAccountTransfer(AcceptanceHelper):

    def test_01_verify_db(self, testdb):
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 4
        accts = {
            t.id: t for t in testdb.query(Account).all()
        }
        assert accts[1].acct_type == AcctType.Bank
        assert accts[1].balance.ledger == Decimal('12789.01')
        assert accts[1].unreconciled_sum == Decimal('0.0')
        assert accts[2].acct_type == AcctType.Bank
        assert accts[2].balance.ledger == Decimal('100.23')
        assert accts[2].unreconciled_sum == Decimal('-333.33')
        assert accts[3].acct_type == AcctType.Credit
        assert accts[4].acct_type == AcctType.Credit
        assert accts[5].acct_type == AcctType.Investment
        assert accts[5].balance.ledger == Decimal('10362.91')

    def test_02_transfer_modal(self, base_url, selenium):
        # Fill in the form
        self.get(selenium, base_url + '/accounts')
        # check the table content on the page
        btable = selenium.find_element_by_id('table-accounts-bank')
        btexts = self.tbody2textlist(btable)
        assert btexts == [
            [
                'BankOne',
                '$12,789.01 (14 hours ago)',
                '$0.00',
                '$12,789.01'
            ],
            [
                'BankTwoStale',
                '$100.23 (18 days ago)',
                '-$333.33',
                '$433.56'
            ]
        ]
        itable = selenium.find_element_by_id('table-accounts-investment')
        itexts = self.tbody2textlist(itable)
        assert itexts == [
            [
                'InvestmentOne',
                '$10,362.91 (13 days ago)'
            ]
        ]
        # open the modal to do a transfer
        link = selenium.find_element_by_id('btn_acct_txfr_bank')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Account Transfer'
        assert body.find_element_by_id(
            'acct_txfr_frm_date').get_attribute('value') == dtnow(
            ).strftime('%Y-%m-%d')
        amt = body.find_element_by_id('acct_txfr_frm_amount')
        amt.clear()
        amt.send_keys('123.45')
        budget_sel = Select(
            body.find_element_by_id('acct_txfr_frm_budget')
        )
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['7', 'Income (i)']
        ]
        assert budget_sel.first_selected_option.get_attribute(
            'value') == 'None'
        budget_sel.select_by_value('2')
        from_acct_sel = Select(
            body.find_element_by_id('acct_txfr_frm_from_account')
        )
        opts = []
        for o in from_acct_sel.options:
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
        assert from_acct_sel.first_selected_option.get_attribute(
            'value'
        ) == 'None'
        from_acct_sel.select_by_value('1')
        to_acct_sel = Select(
            body.find_element_by_id('acct_txfr_frm_to_account')
        )
        opts = []
        for o in to_acct_sel.options:
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
        assert to_acct_sel.first_selected_option.get_attribute(
            'value'
        ) == 'None'
        to_acct_sel.select_by_value('2')
        notes = selenium.find_element_by_id('acct_txfr_frm_notes')
        notes.clear()
        notes.send_keys('Account Transfer Notes')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transactions 5 and 6' \
                                 ' in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-accounts-bank')
        # ensure that the page content updated after refreshing
        btable = selenium.find_element_by_id('table-accounts-bank')
        btexts = self.tbody2textlist(btable)
        assert btexts == [
            [
                'BankOne',
                '$12,789.01 (14 hours ago)',
                '$123.45',
                '$12,665.56'
            ],
            [
                'BankTwoStale',
                '$100.23 (18 days ago)',
                '-$456.78',
                '$557.01'
            ]
        ]
        itable = selenium.find_element_by_id('table-accounts-investment')
        itexts = self.tbody2textlist(itable)
        assert itexts == [
            [
                'InvestmentOne',
                '$10,362.91 (13 days ago)'
            ]
        ]

    def test_03_verify_db(self, testdb):
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 6
        desc = 'Account Transfer - 123.45 from BankOne (1) to BankTwoStale (2)'
        t2 = testdb.query(Transaction).get(5)
        assert t2.date == dtnow().date()
        assert t2.actual_amount == Decimal('123.45')
        assert t2.budgeted_amount == Decimal('123.45')
        assert t2.description == desc
        assert t2.notes == 'Account Transfer Notes'
        assert t2.account_id == 1
        assert t2.scheduled_trans_id is None
        assert len(t2.budget_transactions) == 1
        assert t2.budget_transactions[0].budget_id == 2
        assert t2.budget_transactions[0].amount == Decimal('123.45')
        t1 = testdb.query(Transaction).get(6)
        assert t1.date == dtnow().date()
        assert t1.actual_amount == Decimal('-123.45')
        assert t1.budgeted_amount == Decimal('-123.45')
        assert t1.description == desc
        assert t1.notes == 'Account Transfer Notes'
        assert t1.account_id == 2
        assert t1.scheduled_trans_id is None
        assert len(t1.budget_transactions) == 1
        assert t1.budget_transactions[0].budget_id == 2
        assert t1.budget_transactions[0].amount == Decimal('-123.45')
        acct1 = testdb.query(Account).get(1)
        assert acct1.balance.ledger == Decimal('12789.01')
        assert acct1.unreconciled_sum == Decimal('123.45')
        acct2 = testdb.query(Account).get(2)
        assert acct2.balance.ledger == Decimal('100.23')
        assert acct2.unreconciled_sum == Decimal('-456.78')

    def test_04_no_date_error(self, base_url, selenium):
        # Fill in the form
        self.get(selenium, base_url + '/accounts')
        # open the modal to do a transfer
        link = selenium.find_element_by_id('btn_acct_txfr_bank')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Account Transfer'
        date_box = body.find_element_by_id('acct_txfr_frm_date')
        assert date_box.get_attribute('value') == dtnow().strftime('%Y-%m-%d')
        date_box.clear()
        amt = body.find_element_by_id('acct_txfr_frm_amount')
        amt.clear()
        amt.send_keys('123.45')
        budget_sel = Select(
            body.find_element_by_id('acct_txfr_frm_budget')
        )
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'Periodic1'],
            ['2', 'Periodic2'],
            ['4', 'Standing1'],
            ['5', 'Standing2'],
            ['7', 'Income (i)']
        ]
        assert budget_sel.first_selected_option.get_attribute(
            'value') == 'None'
        budget_sel.select_by_value('2')
        from_acct_sel = Select(
            body.find_element_by_id('acct_txfr_frm_from_account')
        )
        opts = []
        for o in from_acct_sel.options:
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
        assert from_acct_sel.first_selected_option.get_attribute(
            'value'
        ) == 'None'
        from_acct_sel.select_by_value('1')
        to_acct_sel = Select(
            body.find_element_by_id('acct_txfr_frm_to_account')
        )
        opts = []
        for o in to_acct_sel.options:
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
        assert to_acct_sel.first_selected_option.get_attribute(
            'value'
        ) == 'None'
        to_acct_sel.select_by_value('2')
        notes = selenium.find_element_by_id('acct_txfr_frm_notes')
        notes.clear()
        notes.send_keys('Account Transfer Notes')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_class_name('formfeedback')
        assert len(x) == 1
        assert x[0].text.strip() == 'Transactions must have a date'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_load_complete(selenium)
        self.wait_for_id(selenium, 'table-accounts-bank')
        # ensure that the page content updated after refreshing
        btable = selenium.find_element_by_id('table-accounts-bank')
        btexts = self.tbody2textlist(btable)
        assert btexts == [
            [
                'BankOne',
                '$12,789.01 (14 hours ago)',
                '$123.45',
                '$12,665.56'
            ],
            [
                'BankTwoStale',
                '$100.23 (18 days ago)',
                '-$456.78',
                '$557.01'
            ]
        ]
        itable = selenium.find_element_by_id('table-accounts-investment')
        itexts = self.tbody2textlist(itable)
        assert itexts == [
            [
                'InvestmentOne',
                '$10,362.91 (13 days ago)'
            ]
        ]

    def test_05_no_date_error_requests(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': "",
                'amount': "100",
                'notes': "",
                'budget': "1",
                'from_account': "1",
                'to_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": [],
                "budget": [],
                "date": [
                    "Transactions must have a date"
                ],
                "from_account": [],
                "notes": [],
                "to_account": []
            },
            "success": False
        }

    def test_06_zero_amount(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': "0",
                'notes': "",
                'budget': "1",
                'from_account': "1",
                'to_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": ['Amount cannot be zero'],
                "budget": [],
                "date": [],
                "from_account": [],
                "notes": [],
                "to_account": []
            },
            "success": False
        }

    def test_07_negative_amount(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': "-120",
                'notes': "",
                'budget': "1",
                'from_account': "1",
                'to_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": ['Amount cannot be negative'],
                "budget": [],
                "date": [],
                "from_account": [],
                "notes": [],
                "to_account": []
            },
            "success": False
        }

    def test_08_empty_from_account(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': "120",
                'notes': "",
                'budget': "1",
                'from_account': "None",
                'to_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": [],
                "budget": [],
                "date": [],
                "from_account": ['From Account cannot be empty'],
                "notes": [],
                "to_account": []
            },
            "success": False
        }

    def test_09_non_transferrable_from_account(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': "120",
                'notes': "",
                'budget': "1",
                'from_account': "3",
                'to_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": [],
                "budget": [],
                "date": [],
                "from_account": ['From Account type is not transferrable'],
                "notes": [],
                "to_account": []
            },
            "success": False
        }

    def test_10_invalid_from_account(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': "120",
                'notes': "",
                'budget': "1",
                'from_account': "999",
                'to_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": [],
                "budget": [],
                "date": [],
                "from_account": ['from_account ID does not exist'],
                "notes": [],
                "to_account": []
            },
            "success": False
        }

    def test_11_empty_to_account(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': "120",
                'notes': "",
                'budget': "1",
                'to_account': "None",
                'from_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": [],
                "budget": [],
                "date": [],
                "to_account": ['To Account cannot be empty'],
                "notes": [],
                "from_account": []
            },
            "success": False
        }

    def test_12_non_transferrable_to_account(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': "120",
                'notes': "",
                'budget': "1",
                'to_account': "3",
                'from_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": [],
                "budget": [],
                "date": [],
                "to_account": ['To Account type is not transferrable'],
                "notes": [],
                "from_account": []
            },
            "success": False
        }

    def test_13_invalid_to_account(self, base_url):
        r = requests.post(
            base_url + '/forms/account_transfer',
            json={
                'date': dtnow().strftime('%Y-%m-%d'),
                'amount': "120",
                'notes': "",
                'budget': "1",
                'to_account': "999",
                'from_account': "2"
            }
        )
        assert r.status_code == 200
        assert r.json() == {
            "errors": {
                "amount": [],
                "budget": [],
                "date": [],
                "to_account": ['to_account ID does not exist'],
                "notes": [],
                "from_account": []
            },
            "success": False
        }

    def test_99_verify_db_no_changes_from_errors(self, testdb):
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 6
        desc = 'Account Transfer - 123.45 from BankOne (1) to BankTwoStale (2)'
        t2 = testdb.query(Transaction).get(5)
        assert t2.date == dtnow().date()
        assert t2.actual_amount == Decimal('123.45')
        assert t2.budgeted_amount == Decimal('123.45')
        assert t2.description == desc
        assert t2.notes == 'Account Transfer Notes'
        assert t2.account_id == 1
        assert t2.scheduled_trans_id is None
        assert len(t2.budget_transactions) == 1
        assert t2.budget_transactions[0].budget_id == 2
        assert t2.budget_transactions[0].amount == Decimal('123.45')
        t1 = testdb.query(Transaction).get(6)
        assert t1.date == dtnow().date()
        assert t1.actual_amount == Decimal('-123.45')
        assert t1.budgeted_amount == Decimal('-123.45')
        assert t1.description == desc
        assert t1.notes == 'Account Transfer Notes'
        assert t1.account_id == 2
        assert t1.scheduled_trans_id is None
        assert len(t1.budget_transactions) == 1
        assert t1.budget_transactions[0].budget_id == 2
        assert t1.budget_transactions[0].amount == Decimal('-123.45')
        acct1 = testdb.query(Account).get(1)
        assert acct1.balance.ledger == Decimal('12789.01')
        assert acct1.unreconciled_sum == Decimal('123.45')
        acct2 = testdb.query(Account).get(2)
        assert acct2.balance.ledger == Decimal('100.23')
        assert acct2.unreconciled_sum == Decimal('-456.78')
