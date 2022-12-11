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

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
import pytest
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models import (
    Account, Transaction, BudgetTransaction, PlaidAccount, PlaidItem,
    OFXTransaction, OFXStatement
)
from biweeklybudget.utils import dtnow
from plaid import Client

SANDBOX_USERNAME: str = 'user_good'
SANDBOX_PASSWORD: str = 'pass_good'

ONE_HOUR = timedelta(hours=1)


@pytest.mark.plaid
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestLinkAndUpdateSimple(AcceptanceHelper):

    plaid_accts = {}
    plaid_acct_ids = []
    plaid_item_access_token = None

    def test_00_clean_transactions_and_setup(self, testdb):
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
        self.plaid_accts = {}
        self.plaid_acct_ids = []
        self.plaid_item_access_token = None

    def test_01_verify_db_state(self, testdb):
        for acct in testdb.query(Account).all():
            assert acct.plaid_account_id is None
            assert acct.plaid_item_id is None
        assert len(testdb.query(PlaidAccount).all()) == 0
        assert len(testdb.query(PlaidItem).all()) == 0
        assert len(testdb.query(Transaction).all()) == 0
        assert len(testdb.query(BudgetTransaction).all()) == 0
        assert len(testdb.query(OFXStatement).all()) == 0
        assert len(testdb.query(OFXTransaction).all()) == 0

    def test_02_plaid_items_table_is_empty(self, base_url, selenium):
        self.get(selenium, base_url + '/plaid-update')
        table = selenium.find_element_by_id('table-items-plaid')
        texts = self.tbody2textlist(table)
        assert texts == []

    def test_03_do_simple_link(self, base_url, selenium):
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
        )
        user = selenium.find_element_by_id('aut-input-0')
        user.clear()
        user.send_keys(SANDBOX_USERNAME)
        # enter password
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'aut-input-1'))
        )
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
        # verify that it shows up
        selenium.switch_to.default_content()
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        WebDriverWait(selenium, 10).until(
            EC.visibility_of_element_located((By.ID, 'table-items-plaid'))
        )
        WebDriverWait(selenium, 10).until(
            EC.presence_of_element_located((By.ID, 'table-items-plaid'))
        )
        WebDriverWait(selenium, 30).until(
            EC.text_to_be_present_in_element(
                (By.ID, 'table-items-plaid'),
                'First Platypus Bank'
            )
        )
        table = selenium.find_element_by_id('table-items-plaid')
        texts = self.tbody2textlist(table)
        assert len(texts) == 1
        assert texts[0][1] == 'First Platypus Bank (ins_109508)'
        assert texts[0][2] == 'Plaid 401k (6666), ' \
                              'Plaid CD (2222), ' \
                              'Plaid Checking (0000), ' \
                              'Plaid Credit Card (3333), ' \
                              'Plaid IRA (5555), ' \
                              'Plaid Money Market (4444), ' \
                              'Plaid Mortgage (8888), ' \
                              'Plaid Saving (1111), ' \
                              'Plaid Student Loan (7777)'
        assert texts[0][3] in ['now', 'a second ago']

    def test_04_verify_db_updated(self, testdb):
        # check plaid items and accounts
        pitems: List[PlaidItem] = testdb.query(PlaidItem).all()
        assert len(pitems) == 1
        assert pitems[0].institution_name == 'First Platypus Bank'
        assert pitems[0].institution_id == 'ins_109508'
        assert dtnow() - pitems[0].last_updated < ONE_HOUR
        self.plaid_item_access_token = pitems[0].access_token
        paccts: List[PlaidAccount] = testdb.query(PlaidAccount).all()
        assert len(paccts) == 9
        # find and check the checking and credit accounts
        checking = None
        credit = None
        for item in paccts:
            self.plaid_acct_ids.append(item.account_id)
            if item.name == 'Plaid Checking':
                checking = item
            elif item.name == 'Plaid Credit Card':
                credit = item
        assert checking is not None
        assert checking.mask == '0000'
        assert checking.account_type == 'depository'
        assert checking.account_subtype == 'checking'
        self.plaid_accts['checking'] = {
            'name': checking.name,
            'acct_id': checking.account_id,
            'item_id': checking.item_id
        }
        assert credit is not None
        assert credit.mask == '3333'
        assert credit.account_type == 'credit'
        assert credit.account_subtype == 'credit card'
        self.plaid_accts['credit'] = {
            'name': credit.name,
            'acct_id': credit.account_id,
            'item_id': credit.item_id
        }

    def test_05_associate_accounts_in_db(self, testdb):
        acct_chk: Account = testdb.query(Account).get(1)
        acct_chk.plaid_item_id = self.plaid_accts['checking']['item_id']
        acct_chk.plaid_account_id = self.plaid_accts['checking']['acct_id']
        testdb.add(acct_chk)
        acct_credit: Account = testdb.query(Account).get(3)
        acct_credit.plaid_item_id = self.plaid_accts['credit']['item_id']
        acct_credit.plaid_account_id = self.plaid_accts['credit']['acct_id']
        testdb.add(acct_credit)
        testdb.commit()

    def test_06_verify_no_transactions_in_db(self, testdb):
        assert len(testdb.query(Transaction).all()) == 0
        assert len(testdb.query(BudgetTransaction).all()) == 0
        assert len(testdb.query(OFXStatement).all()) == 0
        assert len(testdb.query(OFXTransaction).all()) == 0

    def test_07_update_transactions(self, base_url, selenium):
        self.get(selenium, base_url + '/plaid-update')
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        print('Waiting 30 seconds for item to be ready...')
        time.sleep(30)
        selenium.find_element_by_id('btn_plaid_txns').click()
        self.wait_for_jquery_done(selenium)
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        WebDriverWait(selenium, 10).until(
            EC.visibility_of_element_located(
                (By.ID, 'table-accounts-plaid')
            )
        )
        div = selenium.find_element_by_class_name('unreconciled-alert')
        assert div.text == '13 Unreconciled OFXTransactions.'
        table = selenium.find_element_by_id('table-accounts-plaid')
        texts = self.tbody2textlist(table)
        print(texts)
        assert texts == [
            [
                "First Platypus Bank ("
                f"{self.plaid_accts['credit']['item_id']})",
                '0',
                '13',
                'None',
                ''
            ],
            ['Total', '0', '13', '', '']
        ]

    def test_08_verify_new_transactions_in_db(self, testdb):
        assert len(testdb.query(Transaction).all()) == 0
        assert len(testdb.query(BudgetTransaction).all()) == 0
        assert len(testdb.query(OFXStatement).all()) == 2
        assert len(
            testdb.query(OFXStatement).filter(
                OFXStatement.account_id == 1
            ).all()
        ) == 1
        assert len(
            testdb.query(OFXStatement).filter(
                OFXStatement.account_id == 3
            ).all()
        ) == 1
        assert len(testdb.query(OFXTransaction).all()) == 13
        assert len(
            testdb.query(OFXTransaction).filter(
                OFXTransaction.account_id == 1
            ).all()
        ) == 6
        assert len(
            testdb.query(OFXTransaction).filter(
                OFXTransaction.account_id == 3
            ).all()
        ) == 7

    def test_09_update_transactions_again(self, base_url, selenium, testdb):
        orig_updated: datetime = testdb.query(PlaidItem).get(
            self.plaid_accts['checking']['item_id']
        ).last_updated
        assert len(testdb.query(OFXStatement).all()) == 2
        assert len(testdb.query(OFXTransaction).all()) == 13
        testdb.flush()
        testdb.commit()
        self.get(selenium, base_url + '/plaid-update')
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        selenium.find_element_by_id('btn_plaid_txns').click()
        self.wait_for_jquery_done(selenium)
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        WebDriverWait(selenium, 10).until(
            EC.visibility_of_element_located(
                (By.ID, 'table-accounts-plaid')
            )
        )
        div = selenium.find_element_by_class_name('unreconciled-alert')
        assert div.text == '13 Unreconciled OFXTransactions.'
        table = selenium.find_element_by_id('table-accounts-plaid')
        texts = self.tbody2textlist(table)
        assert texts == [
            [
                "First Platypus Bank "
                f"({self.plaid_accts['credit']['item_id']})",
                '13',
                '0',
                'None',
                ''
            ],
            ['Total', '13', '0', '', '']
        ]
        assert len(testdb.query(OFXStatement).all()) == 4
        assert len(testdb.query(OFXTransaction).all()) == 13
        new_updated: datetime = testdb.query(PlaidItem).get(
            self.plaid_accts['checking']['item_id']
        ).last_updated
        assert new_updated > orig_updated

    def test_10_change_item_institutions_in_db(self, testdb):
        pitems: List[PlaidItem] = testdb.query(PlaidItem).all()
        assert len(pitems) == 1
        pitems[0].institution_name = 'Wrong in DB'
        pitems[0].institution_id = 'wrongInDB'
        testdb.add(pitems[0])
        testdb.commit()

    def test_11_update_item_info(self, base_url, selenium):
        self.get(selenium, base_url + '/plaid-update')
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        button = selenium.find_element_by_id('btn_import_plaid')
        button.click()
        # wait for page reload, indicated by staleness of element
        WebDriverWait(selenium, 20).until(
            EC.staleness_of(button)
        )

    def test_12_verify_item_info_updated(self, testdb):
        pitems: List[PlaidItem] = testdb.query(PlaidItem).all()
        assert len(pitems) == 1
        assert pitems[0].institution_name == 'First Platypus Bank'
        assert pitems[0].institution_id == 'ins_109508'

    def test_13_break_some_plaid_accounts(self, testdb):
        assert len(testdb.query(PlaidAccount).all()) == 9
        item_id = self.plaid_accts['checking']['item_id']
        chk_acct_id = self.plaid_accts['checking']['acct_id']
        credit_acct_id = self.plaid_accts['credit']['acct_id']
        acct_ids = [x for x in self.plaid_acct_ids]
        acct_ids.remove(chk_acct_id)
        acct_ids.remove(credit_acct_id)
        # remove/change two of the other accounts from the DB
        testdb.delete(testdb.query(PlaidAccount).get((item_id, acct_ids[0])))
        acct = testdb.query(PlaidAccount).get((item_id, acct_ids[-1]))
        acct.account_id = 'fooBarBaz'
        testdb.add(acct)
        testdb.flush()
        testdb.commit()
        all_accts: List[PlaidAccount] = testdb.query(PlaidAccount).all()
        assert len(all_accts) == 8
        assert 'fooBarBaz' in [x.account_id for x in all_accts]

    def test_14_refresh_plaid_accounts_for_item(self, base_url, selenium):
        self.get(selenium, base_url + '/plaid-update')
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        item_id = self.plaid_accts['checking']['item_id']
        button = selenium.find_element_by_css_selector(
            f'a[onclick="plaidRefresh(\'{item_id}\')"]'
        )
        button.click()
        # wait for page reload, indicated by staleness of element
        WebDriverWait(selenium, 20).until(
            EC.staleness_of(button)
        )

    def test_15_verify_accounts_updated_in_db(self, testdb):
        all_accts: List[PlaidAccount] = testdb.query(PlaidAccount).all()
        assert len(all_accts) == 9
        acct_ids = sorted([x.account_id for x in all_accts])
        assert acct_ids == sorted(self.plaid_acct_ids)

    def test_16_plaid_api_set_item_needs_login(self):
        client: Client = Client(
            client_id=os.environ['PLAID_CLIENT_ID'],
            secret=os.environ['PLAID_SECRET'],
            public_key=os.environ['PLAID_PUBLIC_KEY'],
            environment=os.environ['PLAID_ENV'],
            api_version='2019-05-29'
        )
        res = client.Sandbox.item.reset_login(self.plaid_item_access_token)
        # xfail - let's see what the response is
        assert res == {}

    def test_17_try_update_transactions_expect_error(self, base_url, selenium):
        self.get(selenium, base_url + '/plaid-update')
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        selenium.find_element_by_id('btn_plaid_txns').click()
        self.wait_for_jquery_done(selenium)
        self.wait_for_load_complete(selenium)
        self.wait_for_jquery_done(selenium)
        WebDriverWait(selenium, 10).until(
            EC.visibility_of_element_located(
                (By.ID, 'table-accounts-plaid')
            )
        )
        table = selenium.find_element_by_id('table-accounts-plaid')
        texts = self.tbody2textlist(table)
        print(texts)
        assert texts == [
            [
                "First Platypus Bank ("
                f"{self.plaid_accts['credit']['item_id']})",
                '0',
                '13',
                'None',
                ''
            ],
            ['Total', '0', '13', '', '']
        ]

    def test_18_update_item_relogin(self):
        raise NotImplementedError()

    def test_19_verify_item_updated_in_db(self):
        raise NotImplementedError()

    def test_20_update_transactions(self):
        raise NotImplementedError()
