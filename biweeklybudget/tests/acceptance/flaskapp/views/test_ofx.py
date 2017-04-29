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
from datetime import timedelta, datetime
from selenium.webdriver.support.ui import Select
from pytz import UTC

from biweeklybudget.utils import dtnow
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper


@pytest.mark.acceptance
class TestOFX(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/ofx')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'OFX Transactions - BiweeklyBudget'

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
class TestOFXDefault(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.dt = dtnow()
        self.get(selenium, base_url + '/ofx')

    def test_table(self, selenium):
        table = selenium.find_element_by_id('table-ofx-txn')
        texts = self.tbody2textlist(table)
        elems = self.tbody2elemlist(table)
        assert texts[0] == [
            (self.dt - timedelta(hours=22)).strftime('%Y-%m-%d'),
            '$123.81',
            'CreditOne (3)',
            'Purchase',
            '123.81 Credit Purchase T1',
            '38328',
            'CreditOneT1Desc',
            'T1',
            '4',
            (self.dt - timedelta(hours=13)).strftime('%Y-%m-%d'),
            ''
        ]
        assert elems[0][2].get_attribute(
            'innerHTML') == '<a href="/accounts/3">CreditOne (3)</a>'
        assert elems[0][7].get_attribute(
            'innerHTML') == '<a href="javascript:ofxTransModal(' \
                            '3, \'T1\')">T1</a>'
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['CreditOne (3)', 'T1'],
            ['CreditTwo (4)', '002'],
            ['BankOne (1)', 'BankOne.0.1'],
            ['CreditTwo (4)', '001'],
            ['BankOne (1)', 'BankOne.1.1'],
            ['BankOne (1)', 'BankOne.1.2'],
            ['BankOne (1)', 'BankOne.1.3'],
            ['BankOne (1)', 'BankOne.1.4'],
            ['BankOne (1)', 'BankOne.1.5'],
            ['BankOne (1)', 'BankOne.1.6']
        ]
        reconciles = [t[10] for t in texts]
        assert reconciles == [
            '',
            '',
            'Yes (1)',
            '',
            '',
            '',
            '',
            '',
            '',
            ''
        ]
        assert elems[2][10].get_attribute('innerHTML') == '<a ' \
            'href="javascript:txnReconcileModal(1)">Yes (1)</a>'

    def test_paginate(self, selenium):
        self.get(selenium, self.baseurl + '/ofx')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['CreditOne (3)', 'T1'],
            ['CreditTwo (4)', '002'],
            ['BankOne (1)', 'BankOne.0.1'],
            ['CreditTwo (4)', '001'],
            ['BankOne (1)', 'BankOne.1.1'],
            ['BankOne (1)', 'BankOne.1.2'],
            ['BankOne (1)', 'BankOne.1.3'],
            ['BankOne (1)', 'BankOne.1.4'],
            ['BankOne (1)', 'BankOne.1.5'],
            ['BankOne (1)', 'BankOne.1.6']
        ]
        page2_link = selenium.find_element_by_xpath(
            '//li[@class="paginate_button "]/a[text()="2"]'
        )
        page2_link.click()
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['BankOne (1)', 'BankOne.1.7'],
            ['BankOne (1)', 'BankOne.1.8'],
            ['BankOne (1)', 'BankOne.1.9'],
            ['BankOne (1)', 'BankOne.1.10'],
            ['BankOne (1)', 'BankOne.1.11'],
            ['BankOne (1)', 'BankOne.1.12'],
            ['BankOne (1)', 'BankOne.1.13'],
            ['BankOne (1)', 'BankOne.1.14'],
            ['BankOne (1)', 'BankOne.1.15'],
            ['BankOne (1)', 'BankOne.1.16']
        ]

    def test_filter_opts(self, selenium):
        self.get(selenium, self.baseurl + '/ofx')
        acct_filter = Select(selenium.find_element_by_id('account_filter'))
        # find the options
        opts = []
        for o in acct_filter.options:
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

    def test_filter(self, selenium):
        p1trans = [
            ['CreditOne (3)', 'T1'],
            ['CreditTwo (4)', '002'],
            ['BankOne (1)', 'BankOne.0.1'],
            ['CreditTwo (4)', '001'],
            ['BankOne (1)', 'BankOne.1.1'],
            ['BankOne (1)', 'BankOne.1.2'],
            ['BankOne (1)', 'BankOne.1.3'],
            ['BankOne (1)', 'BankOne.1.4'],
            ['BankOne (1)', 'BankOne.1.5'],
            ['BankOne (1)', 'BankOne.1.6']
        ]
        self.get(selenium, self.baseurl + '/ofx')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        # check sanity
        assert trans == p1trans
        acct_filter = Select(selenium.find_element_by_id('account_filter'))
        # select CreditTwo (4)
        acct_filter.select_by_value('4')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['CreditTwo (4)', '002'],
            ['CreditTwo (4)', '001']
        ]
        # select back to all
        acct_filter.select_by_value('None')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == p1trans

    def test_search(self, selenium):
        p1trans = [
            ['CreditTwo (4)', '001'],
            ['BankTwoStale (2)', '1'],
            ['DisabledBank (6)', '001']
        ]
        self.get(selenium, self.baseurl + '/ofx')
        search = self.retry_stale(
            selenium.find_element_by_xpath,
            '//input[@type="search"]'
        )
        search.send_keys('inte')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        # check sanity
        assert trans == p1trans
        acct_filter = Select(selenium.find_element_by_id('account_filter'))
        # select CreditTwo (4)
        acct_filter.select_by_value('4')
        table = self.retry_stale(selenium.find_element_by_id, 'table-ofx-txn')
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [[t[2], t[7]] for t in texts]
        assert trans == [
            ['CreditTwo (4)', '001']
        ]


@pytest.mark.acceptance
class TestOFXTransModal(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/ofx')

    def test_modal_on_click(self, selenium):
        link = selenium.find_element_by_xpath('//a[text()="T1"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'OFXTransaction Account=3 FITID=T1'
        texts = self.tbody2textlist(body)
        elems = self.tbody2elemlist(body)
        pdate = (dtnow() - timedelta(hours=22))
        fdate = (dtnow() - timedelta(hours=13))
        assert texts == [
            ['Account', 'CreditOne (3)'],
            ['FITID', 'T1'],
            ['Date Posted', pdate.strftime('%Y-%m-%d')],
            ['Amount', '$123.81'],
            ['Name', '123.81 Credit Purchase T1'],
            ['Memo', '38328'],
            ['Type', 'Purchase'],
            ['Description', 'CreditOneT1Desc'],
            ['Notes', ''],
            ['Checknum', '123'],
            ['MCC', 'T1mcc'],
            ['SIC', 'T1sic'],
            ['OFX Statement'],
            ['ID', '4'],
            ['Date', fdate.strftime('%Y-%m-%d')],
            ['Filename', '/stmt/CreditOne/0'],
            ['File mtime', fdate.strftime('%Y-%m-%d')],
            ['Ledger Balance', '-$952.06']
        ]
        assert elems[0][1].get_attribute(
            'innerHTML') == '<a href="/accounts/3">CreditOne (3)</a>'
        assert selenium.find_element_by_id(
            'modalSaveButton').is_displayed() is False


@pytest.mark.acceptance
class TestOFXTransURL(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url + '/ofx/3/T1')

    def test_modal_auto_displayed(self, selenium):
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'OFXTransaction Account=3 FITID=T1'
        texts = self.tbody2textlist(body)
        elems = self.tbody2elemlist(body)
        pdate = (dtnow() - timedelta(hours=22))
        fdate = (dtnow() - timedelta(hours=13))
        assert texts == [
            ['Account', 'CreditOne (3)'],
            ['FITID', 'T1'],
            ['Date Posted', pdate.strftime('%Y-%m-%d')],
            ['Amount', '$123.81'],
            ['Name', '123.81 Credit Purchase T1'],
            ['Memo', '38328'],
            ['Type', 'Purchase'],
            ['Description', 'CreditOneT1Desc'],
            ['Notes', ''],
            ['Checknum', '123'],
            ['MCC', 'T1mcc'],
            ['SIC', 'T1sic'],
            ['OFX Statement'],
            ['ID', '4'],
            ['Date', fdate.strftime('%Y-%m-%d')],
            ['Filename', '/stmt/CreditOne/0'],
            ['File mtime', fdate.strftime('%Y-%m-%d')],
            ['Ledger Balance', '-$952.06']
        ]
        assert elems[0][1].get_attribute(
            'innerHTML') == '<a href="/accounts/3">CreditOne (3)</a>'
        assert selenium.find_element_by_id(
            'modalSaveButton').is_displayed() is False


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestTransReconciledModal(AcceptanceHelper):

    def test_0_verify_db(self, testdb):
        t = testdb.query(TxnReconcile).get(1)
        assert t.ofx_account_id == 1
        assert t.ofx_fitid == 'BankOne.0.1'
        assert t.txn_id == 1
        assert t.rule_id is None
        assert t.note == 'reconcile notes'
        assert t.reconciled_at == datetime(2017, 4, 10, 8, 9, 11, tzinfo=UTC)

    def test_1_modal(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/transactions')
        link = selenium.find_element_by_xpath(
            '//a[@href="javascript:txnReconcileModal(1)"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Transaction Reconcile 1'
        dl = body.find_element_by_tag_name('dl')
        assert dl.get_attribute('innerHTML') == '\n' \
            '<dt>Date Reconciled</dt><dd>2017-04-10 08:09:11 UTC</dd>\n' \
            '<dt>Note</dt><dd>reconcile notes</dd>\n' \
            '<dt>Rule</dt><dd>null</dd>\n'
        trans_tbl = body.find_element_by_id('txnReconcileModal-trans')
        trans_texts = self.tbody2textlist(trans_tbl)
        assert trans_texts == [
            ['Transaction'],
            [
                'Date',
                (dtnow() + timedelta(days=4)).strftime('%Y-%m-%d')
            ],
            ['Amount', '$111.13'],
            ['Budgeted Amount', '$111.11'],
            ['Description', 'T1foo'],
            ['Account', 'BankOne (1)'],
            ['Budget', 'Periodic1 (1)'],
            ['Notes', 'notesT1'],
            ['Scheduled?', 'Yes (1)']
        ]
        trans_elems = self.tbody2elemlist(trans_tbl)
        assert trans_elems[5][1].get_attribute('innerHTML') == '<a href=' \
            '"/accounts/1">BankOne (1)</a>'
        assert trans_elems[6][1].get_attribute('innerHTML') == '<a href=' \
            '"/budgets/1">Periodic1 (1)</a>'
        assert trans_elems[8][1].get_attribute('innerHTML') == '<a href=' \
            '"/scheduled/1">Yes (1)</a>'
        ofx_tbl = body.find_element_by_id('txnReconcileModal-ofx')
        ofx_texts = self.tbody2textlist(ofx_tbl)
        assert ofx_texts == [
            ['OFX Transaction'],
            ['Account', 'BankOne (1)'],
            ['FITID', 'BankOne.0.1'],
            ['Date Posted', (dtnow() - timedelta(days=6)).strftime('%Y-%m-%d')],
            ['Amount', '-$20.00'],
            ['Name', 'Late Fee'],
            ['Memo', ''],
            ['Type', 'Debit'],
            ['Description', ''],
            ['Notes', ''],
            ['Checknum', ''],
            ['MCC', ''],
            ['SIC', ''],
            ['OFX Statement'],
            ['ID', '1'],
            ['Date', (dtnow() - timedelta(hours=46)).strftime('%Y-%m-%d')],
            ['Filename', '/stmt/BankOne/0'],
            [
                'File mtime',
                (dtnow() - timedelta(hours=46)).strftime('%Y-%m-%d')
            ],
            ['Ledger Balance', '$12,345.67']
        ]
        ofx_elems = self.tbody2elemlist(ofx_tbl)
        assert ofx_elems[1][1].get_attribute('innerHTML') == '<a href=' \
            '"/accounts/1">BankOne (1)</a>'
