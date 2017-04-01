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


@pytest.mark.acceptance
class TestSchedTrans(AcceptanceHelper):

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
class TestSchedTransDefault(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.dt = dtnow()
        selenium.get(base_url + '/scheduled')

    def test_table(self, selenium):
        table = selenium.find_element_by_id('table-scheduled-txn')
        texts = self.tbody2textlist(table)
        elems = self.tbody2elemlist(table)
        assert texts == [
            [
                'yes',
                'per period',
                '1 per period',
                '$-333.33',
                'ST3',
                'BankTwoStale (2)',
                'Standing1 (4)'
            ],
            [
                'yes',
                'monthly',
                '4th',
                '$222.22',
                'ST2',
                'BankOne (1)',
                'Periodic2 (2)'
            ],
            [
                'yes',
                'date',
                (self.dt + timedelta(days=4)).date().strftime('%Y-%m-%d'),
                '$111.11',
                'ST1',
                'BankOne (1)',
                'Periodic1 (1)'
            ],
            [
                'NO',
                'per period',
                '3 per period',
                '$666.66',
                'ST6',
                'BankTwoStale (2)',
                'Standing1 (4)'
            ],
            [
                'NO',
                'monthly',
                '5th',
                '$555.55',
                'ST5',
                'BankOne (1)',
                'Periodic2 (2)'
            ],
            [
                'NO',
                'date',
                (self.dt + timedelta(days=5)).date().strftime('%Y-%m-%d'),
                '$444.44',
                'ST4',
                'BankOne (1)',
                'Periodic1 (1)'
            ]
        ]
        linkcols = [
            [
                c[4].get_attribute('innerHTML'),
                c[5].get_attribute('innerHTML'),
                c[6].get_attribute('innerHTML')
            ]
            for c in elems
        ]
        assert linkcols[0] == [
            '<a href="javascript:schedModal(3)">ST3</a>',
            '<a href="/accounts/2">BankTwoStale (2)</a>',
            '<a href="/budgets/4">Standing1 (4)</a>'
        ]
        assert linkcols[1] == [
            '<a href="javascript:schedModal(2)">ST2</a>',
            '<a href="/accounts/1">BankOne (1)</a>',
            '<a href="/budgets/2">Periodic2 (2)</a>'
        ]
        assert linkcols[2] == [
            '<a href="javascript:schedModal(1)">ST1</a>',
            '<a href="/accounts/1">BankOne (1)</a>',
            '<a href="/budgets/1">Periodic1 (1)</a>'
        ]
        assert linkcols[3] == [
            '<a href="javascript:schedModal(6)">ST6</a>',
            '<a href="/accounts/2">BankTwoStale (2)</a>',
            '<a href="/budgets/4">Standing1 (4)</a>'
        ]
        assert linkcols[4] == [
            '<a href="javascript:schedModal(5)">ST5</a>',
            '<a href="/accounts/1">BankOne (1)</a>',
            '<a href="/budgets/2">Periodic2 (2)</a>'
        ]
        assert linkcols[5] == [
            '<a href="javascript:schedModal(4)">ST4</a>',
            '<a href="/accounts/1">BankOne (1)</a>',
            '<a href="/budgets/1">Periodic1 (1)</a>'
        ]

    def test_filter_opts(self, selenium):
        selenium.get(self.baseurl + '/scheduled')
        acct_filter = Select(selenium.find_element_by_id('type_filter'))
        # find the options
        opts = []
        for o in acct_filter.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['date', 'Date'],
            ['monthly', 'Monthly'],
            ['per period', 'Per Period']
        ]

    def test_filter(self, selenium):
        p1trans = [
            'ST3',
            'ST2',
            'ST1',
            'ST6',
            'ST5',
            'ST4'
        ]
        selenium.get(self.baseurl + '/scheduled')
        table = self.retry_stale(
            selenium.find_element_by_id,
            'table-scheduled-txn'
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[4] for t in texts]
        # check sanity
        assert trans == p1trans
        type_filter = Select(selenium.find_element_by_id('type_filter'))
        # select Monthly
        type_filter.select_by_value('monthly')
        table = self.retry_stale(
            selenium.find_element_by_id,
            'table-scheduled-txn'
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[4] for t in texts]
        assert trans == ['ST2', 'ST5']
        # select back to all
        type_filter.select_by_value('None')
        table = self.retry_stale(
            selenium.find_element_by_id,
            'table-scheduled-txn'
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[4] for t in texts]
        assert trans == p1trans

    def test_search(self, selenium):
        selenium.get(self.baseurl + '/scheduled')
        search = self.retry_stale(
            selenium.find_element_by_xpath,
            '//input[@type="search"]'
        )
        search.send_keys('ST3')
        table = self.retry_stale(
            selenium.find_element_by_id,
            'table-scheduled-txn'
        )
        texts = self.retry_stale(self.tbody2textlist, table)
        trans = [t[4] for t in texts]
        # check sanity
        assert trans == ['ST3']


@pytest.mark.acceptance
class DONOTTestSchedTransTransModal(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url + '/ofx')

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
            ['Ledger Balance', '$952.06']
        ]
        assert elems[0][1].get_attribute(
            'innerHTML') == '<a href="/accounts/3">CreditOne (3)</a>'
        assert selenium.find_element_by_id(
            'modalSaveButton').is_displayed() is False


@pytest.mark.acceptance
class DONOTTestSchedTransTransURL(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url + '/ofx/3/T1')

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
            ['Ledger Balance', '$952.06']
        ]
        assert elems[0][1].get_attribute(
            'innerHTML') == '<a href="/accounts/3">CreditOne (3)</a>'
        assert selenium.find_element_by_id(
            'modalSaveButton').is_displayed() is False
