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
from datetime import datetime
from pytz import UTC

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
import biweeklybudget.models.base  # noqa
from biweeklybudget.tests.conftest import engine
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.ofx_statement import OFXStatement


@pytest.mark.acceptance
class TestBaseTemplateNavigation(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url)

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element_by_id('side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_nav_links(self, selenium):
        nav = selenium.find_element_by_xpath(
            "//div[contains(@class, 'sidebar-nav')]/ul"
        )
        navlinks = []
        for li in nav.find_elements_by_xpath("//li/a"):
            if li.text.strip() == '':
                continue
            navlinks.append(
                (self.relurl(li.get_attribute('href')), li.text)
            )
        assert navlinks == [
            ('/', 'Home'),
            ('/payperiods', 'Pay Periods'),
            ('/accounts', 'Accounts'),
            ('/ofx', 'OFX'),
            ('/transactions', 'Transactions'),
            ('/reconcile', 'Reconcile'),
            ('/budgets', 'Budgets'),
            ('/scheduled', 'Scheduled'),
            ('/help', 'Help/Docs/Code (AGPL)')
        ]


@pytest.mark.acceptance
class TestBaseTemplateNotifications(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        self.get(selenium, base_url)

    def test_notifications(self, selenium):
        div = selenium.find_element_by_id('notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'

    def test_stale_accounts(self, selenium):
        div = selenium.find_elements_by_xpath(
            "//div[@id='notifications-row']/div/div"
        )[0]
        assert div.text == '2 Accounts with stale data. View Accounts.'
        a = div.find_element_by_tag_name('a')
        assert self.relurl(a.get_attribute('href')) == '/accounts'
        assert a.text == 'View Accounts'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
class TestBaseTmplUnreconciledNotification(AcceptanceHelper):

    def test_00_clean_db(self, testdb):
        # clean the database
        biweeklybudget.models.base.Base.metadata.reflect(engine)
        biweeklybudget.models.base.Base.metadata.drop_all(engine)
        biweeklybudget.models.base.Base.metadata.create_all(engine)

    def test_01_add(self, testdb):
        a = Account(
            description='First Bank Account',
            name='BankOne',
            ofx_cat_memo_to_name=True,
            ofxgetter_config_json='{"foo": "bar"}',
            vault_creds_path='secret/foo/bar/BankOne',
            acct_type=AcctType.Bank
        )
        testdb.add(a)
        a.set_balance(
            overall_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC),
            ledger=1.0,
            ledger_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC)
        )
        b = Budget(
            name='1Income',
            is_periodic=True,
            description='1Income',
            starting_balance=0.0,
            is_income=True
        )
        testdb.add(b)
        testdb.flush()
        testdb.commit()

    def test_02_notification_none(self, selenium, base_url):
        self.get(selenium, base_url)
        assert 'unreconciled-alert' not in selenium.page_source
        assert 'Unreconciled Transactions' not in selenium.page_source

    def test_03_add_ofx(self, testdb):
        acct1 = testdb.query(Account).get(1)
        stmt1 = OFXStatement(
            account=acct1,
            filename='a1.ofx',
            file_mtime=datetime(2017, 4, 10, 12, 31, 42, tzinfo=UTC),
            as_of=datetime(2017, 4, 10, 12, 31, 42, tzinfo=UTC),
            currency='USD',
            acctid='1',
            bankid='b1',
            routing_number='r1'
        )
        testdb.add(stmt1)
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFX1',
            trans_type='Deposit',
            date_posted=datetime(2017, 4, 10, 12, 3, 4, tzinfo=UTC),
            amount=-100.0,
            name='ofx1-income'
        ))
        # matches Transaction 2
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFX2',
            trans_type='Debit',
            date_posted=datetime(2017, 4, 11, 12, 3, 4, tzinfo=UTC),
            amount=250.0,
            name='ofx2-trans1'
        ))
        # matches Transcation 3
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFX3',
            trans_type='Purchase',
            date_posted=datetime(2017, 4, 9, 12, 3, 4, tzinfo=UTC),
            amount=-600.0,
            name='ofx3-trans2-st1'
        ))
        testdb.flush()
        testdb.commit()

    def test_04_notification(self, selenium, base_url):
        self.baseurl = base_url
        self.get(selenium, base_url)
        div = selenium.find_element_by_class_name('unreconciled-alert')
        assert div.text == '3 Unreconciled OFXTransactions.'
        a = div.find_element_by_tag_name('a')
        assert self.relurl(a.get_attribute('href')) == '/reconcile'
        assert a.text == 'Unreconciled OFXTransactions'
