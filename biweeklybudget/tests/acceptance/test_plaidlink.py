"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2022 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

import sys
from datetime import date, datetime, timedelta
from pytz import UTC
from decimal import Decimal
import pytest

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models import (
    Account, Transaction, BudgetTransaction, PlaidAccount, PlaidItem,
    OFXTransaction, OFXStatement
)

SANDBOX_USERNAME: str = ''
SANDBOX_PASSWORD: str = ''
SANDBOX_MFA: str = '1234'

@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestLinkAndUpdateSimple(AcceptanceHelper):

    def test_0_clean_transactions(self, testdb):
        for stmt in [
            'UPDATE accounts SET plaid_item_id=NULL, plaid_account_id=NULL;',
            'DELETE FROM plaid_accounts;',
            'DELETE FROM plaid_items;',
            'DELETE FROM txn_reconciles;',
            'DELETE FROM ofx_trans;',
            'DELETE FROM ofx_statements;',
            'DELETE FROM budget_transactions;',
            'DELETE FROM transactions;',
        ]:
            testdb.execute(stmt)
        testdb.flush()
        testdb.commit()

    def test_1_verify_db_state(self, testdb):
        for acct in testdb.query(Account).all():
            assert acct.plaid_account_id is None
            assert acct.plaid_item_id is None
        assert len(testdb.query(PlaidAccount).all()) == 0
        assert len(testdb.query(PlaidItem).all()) == 0
        assert len(testdb.query(Transaction).all()) == 0
        assert len(testdb.query(BudgetTransaction).all()) == 0
        assert len(testdb.query(OFXStatement).all()) == 0
        assert len(testdb.query(OFXTransaction).all()) == 0

    def test_2_items_table(self, base_url, selenium):
        self.get(selenium, base_url + '/plaid-update')
        table = selenium.find_element_by_id('table-items-plaid')
        texts = self.tbody2textlist(table)
        assert texts == []

    def test_3_simple_link(self, base_url, selenium):
        self.get(selenium, base_url + '/plaid-update')
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        selenium.find_element_by_id('btn_link_plaid').click()
        self.wait_for_jquery_done(selenium)
        WebDriverWait(selenium, 30).until(
            EC.frame_to_be_available_and_switch_to_it(
                (By.ID, 'plaid-link-iframe-1')
            )
        )
        # inside iframe
        # click Continue button
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, '//button[normalize-space()="Continue"]')
            )
        ).click()
        # search box
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'search-input'))
        ).click()
        # enter search item
        sb = selenium.find_element_by_id('search-input')
        assert sb.is_displayed()
        sb.clear()
        sb.send_keys('First Platypus')
        # click on First Platypus Bank
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'aut-First Platypus Bank'))
        ).click()
        # click on the non-OAuth institution
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'aut-ins_109508'))
        ).click()
        # enter username
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'aut-input-0'))
        ).click()
        user = selenium.find_element_by_id('aut-input-0')
        user.clear()
        user.send_keys(SANDBOX_USERNAME)
        # enter password
        passwd = selenium.find_element_by_id('aut-input-1')
        passwd.clear()
        passwd.send_keys(SANDBOX_PASSWORD)
        # click submit
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'aut-button'))
        ).click()
        # wait for accounts confirmation screen
        WebDriverWait(selenium, 10).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, 'div.Content-module__content'),
                'Your accounts'
            )
        )
        # click continue
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'aut-button'))
        ).click()
        # wait for success message
        WebDriverWait(selenium, 10).until(
            EC.text_to_be_present_in_element(
                (By.CSS_SELECTOR, 'div.Content-module__content'),
                'Your account has been successfully linked to '
            )
        )
        # click continue
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'aut-button'))
        ).click()
        self.wait_for_jquery_done(selenium)
        # verify that it shows up
        table = selenium.find_element_by_id('table-update-plaid')
        texts = self.tbody2textlist(table)
        assert len(texts) == 1
        assert 'First Platypus Bank' in texts[0][1]
        table = selenium.find_element_by_id('table-items-plaid')
        texts = self.tbody2textlist(table)
        assert len(texts) == 1
        assert texts[0][1] == 'First Platypus Bank (ins_109508)'
        assert 'Plaid Checking (0000)' in texts[0][2]
