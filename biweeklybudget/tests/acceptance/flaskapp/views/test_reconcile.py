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
from datetime import datetime, date
from pytz import UTC
import re
import json
from time import sleep
from selenium.webdriver import ActionChains
import requests
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from biweeklybudget.utils import dtnow, fmt_currency
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models import *
from biweeklybudget.tests.sqlhelpers import restore_mysqldump
from biweeklybudget.tests.conftest import engine

dnow = dtnow()


def txn_div(id, dt, amt, acct_name, acct_id,
            budget_name, budget_id, desc, drop_div=''):
    """
    Return the HTML for a Transaction div.

    :param drop_div: contents of ``reconcile-drop-target`` div
    :type drop_div: str
    :return: HTML for Transaction reconcile div
    :rtype: str
    """
    s = '<div class="reconcile reconcile-trans ui-droppable" ' \
        'id="trans-%s" data-trans-id="%s" data-acct-id="%s" data-amt="%s">' % (
            id, id, acct_id, amt
        )
    s += '<div class="row">'
    s += '<div class="col-lg-3">%s</div>' % dt.strftime('%Y-%m-%d')
    s += '<div class="col-lg-3">%s</div>' % fmt_currency(amt)
    s += '<div class="col-lg-3"><strong>Acct:</strong> '
    s += '<span style="white-space: nowrap;">'
    s += '<a href="/accounts/%s">%s (%s)</a>' % (acct_id, acct_name, acct_id)
    s += '</span></div>'
    s += '<div class="col-lg-3"><strong>Budget:</strong> '
    s += '<span style="white-space: nowrap;">'
    s += '<a href="/budgets/%s">%s (%s)</a>' % (
        budget_id, budget_name, budget_id
    )
    s += '</span></div>'
    s += '</div>'
    s += '<div class="row"><div class="col-lg-12">'
    if drop_div == '':
        s += '<div style="float: left;"><a href="javascript:transModal('
        s += '%s, function () { updateReconcileTrans(%s) })">Trans %s</a>' \
             ': %s</div>' % (id, id, id, desc)
        s += '<div style="float: right;" class="trans-no-ofx"><a ' \
             'href="javascript:transNoOfx(%s)" style="" title="Reconcile ' \
             'as never having a matching OFX Transaction">(no OFX)</a>' \
             '</div>' % id
    else:
        s += '<div style="float: left;"><span class="disabledEditLink">' \
             'Trans %s</span>: %s</div>' % (id, desc)
        s += '<div style="float: right;" class="trans-no-ofx"><a ' \
             'href="javascript:transNoOfx(%s)" style="display: none;" ' \
             'title="Reconcile as never having a matching OFX Transaction">' \
             '(no OFX)</a></div>' % id
    s += '</div></div>'
    s += '<div class="reconcile-drop-target">%s</div>' % drop_div
    s += '</div>'
    return s


def clean_fitid(fitid):
    return re.sub(r'\W', '', fitid)


def ofx_div(dt_posted, amt, acct_name, acct_id, trans_type, fitid, name,
            trans_id=None):
    """
    Return the HTML for an OFXTransaction div.

    :param trans_id: if dropped on a Transaction div, the trans_id
    :type trans_id: int
    :return: HTML for OFXTransaction reconcile div
    :rtype: str
    """
    cfitid = clean_fitid(fitid)
    if int(amt) == amt:
        # JS doesn't put the trailing decimal on a ".0" number
        amt = int(amt)
    if trans_id is not None:
        classes = 'reconcile reconcile-ofx-dropped'
        _id = 'dropped-ofx-%s-%s' % (acct_id, cfitid)
    else:
        classes = 'reconcile reconcile-ofx ui-draggable ui-draggable-handle'
        _id = 'ofx-%s-%s' % (acct_id, cfitid)
    s = '<div class="%s" id="%s" data-acct-id="%s" ' \
        'data-amt="%s" data-fitid="%s" style="">' % (
            classes, _id, acct_id, amt, fitid
        )
    s += '<div class="row">'
    s += '<div class="col-lg-3">%s</div>' % dt_posted.strftime('%Y-%m-%d')
    s += '<div class="col-lg-3">%s</div>' % fmt_currency(amt)
    s += '<div class="col-lg-3"><strong>Acct:</strong> '
    s += '<span style="white-space: nowrap;">'
    s += '<a href="/accounts/%s">%s (%s)</a>' % (acct_id, acct_name, acct_id)
    s += '</span></div>'
    s += '<div class="col-lg-3"><strong>Type:</strong> %s</div>' % trans_type
    s += '</div>'
    s += '<div class="row"><div class="col-lg-12">'
    s += '<div style="float: left;">'
    s += '<a href="javascript:ofxTransModal(%s, \'%s\', false)">%s</a>' % (
        acct_id, cfitid, fitid
    )
    s += ': %s' % name
    s += '</div>'
    if trans_id is None:
        s += '<div style="float: right;" class="make-trans-link"><a ' \
             'href="javascript:makeTransFromOfx(%d, \'%s\')" ' \
             'title="Create Transaction from this OFX">(make trans)</a>' \
             '</div>' % (acct_id, fitid)
    s += '</div>'
    s += '</div></div>'
    if trans_id is not None:
        return '<div style="text-align: right;"><a href="javascript:reconc' \
               'ileDoUnreconcile(%s, %s, \'%s\')">Unreconcile</a></div>%s' % (
                   trans_id, acct_id, fitid, s
               )
    return s


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestReconcile(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')

    def test_heading(self, selenium):
        heading = selenium.find_element_by_class_name('navbar-brand')
        assert heading.text == 'Reconcile Transactions - BiweeklyBudget'

    def test_nav_menu(self, selenium):
        ul = selenium.find_element_by_id('side-menu')
        assert ul is not None
        assert 'nav' in ul.get_attribute('class')
        assert ul.tag_name == 'ul'

    def test_notifications(self, selenium):
        div = selenium.find_element_by_id('notifications-row')
        assert div is not None
        assert div.get_attribute('class') == 'row'


class ReconcileHelper(AcceptanceHelper):

    def get_reconciled(self, driver):
        """
        Execute javascript in the selenium browser to return the
        ``reconciled`` JavaScript object as a JSON string; deserialize the
        JSON and return the resulting dict.

        :param driver: Selenium driver instance
        :type driver: selenium.webdriver.remote.webdriver.WebDriver
        :return: ``reconciled`` javascript variable from page
        :rtype: dict
        """
        script = 'return JSON.stringify(reconciled);'
        res = driver.execute_script(script)
        print("reconciled JSON: %s" % res)
        r = json.loads(res)
        return {int(x): r[x] for x in r}

    def test_00_clean_db(self, dump_file_path):
        # clean the database; empty schema
        restore_mysqldump(dump_file_path, engine, with_data=False)

    def test_01_add_accounts(self, testdb):
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
        b = Account(
            description='Second Bank Account',
            name='BankTwo',
            acct_type=AcctType.Bank,
            negate_ofx_amounts=True
        )
        testdb.add(b)
        b.set_balance(
            overall_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC),
            ledger=1.0,
            ledger_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC)
        )
        testdb.flush()
        testdb.commit()

    def test_02_add_budgets(self, testdb):
        testdb.add(Budget(
            name='1Income',
            is_periodic=True,
            description='1Income',
            starting_balance=0.0,
            is_income=True
        ))
        testdb.add(Budget(
            name='2Periodic',
            is_periodic=True,
            description='2Periodic',
            starting_balance=500.00
        ))
        testdb.add(Budget(
            name='3Periodic',
            is_periodic=True,
            description='3Periodic',
            starting_balance=0.00
        ))
        testdb.flush()
        testdb.commit()

    def test_03_add_transactions(self, testdb):
        acct1 = testdb.query(Account).get(1)
        acct2 = testdb.query(Account).get(2)
        ibudget = testdb.query(Budget).get(1)
        e1budget = testdb.query(Budget).get(2)
        e2budget = testdb.query(Budget).get(3)
        # income - matches OFX1
        testdb.add(Transaction(
            date=date(2017, 4, 10),
            actual_amount=-100.00,
            budgeted_amount=-100.00,
            description='income',
            account=acct1,
            budget=ibudget
        ))
        # one transaction - matches OFX2
        testdb.add(Transaction(
            date=date(2017, 4, 10),
            actual_amount=250.00,
            description='trans1',
            account=acct1,
            budget=e2budget
        ))
        # another transaction - matches OFX3
        st1 = ScheduledTransaction(
            amount=500.0,
            description='ST1',
            account=acct2,
            budget=e1budget,
            date=date(2017, 4, 10)
        )
        testdb.add(st1)
        testdb.add(Transaction(
            date=date(2017, 4, 11),
            actual_amount=600.0,
            budgeted_amount=500.0,
            description='trans2',
            account=acct2,
            budget=e1budget,
            scheduled_trans=st1
        ))
        # non-matched transaction
        testdb.add(Transaction(
            date=date(2017, 4, 14),
            actual_amount=10.00,
            description='trans3',
            account=acct2,
            budget=e2budget
        ))
        # matched ScheduledTransaction
        st2 = ScheduledTransaction(
            amount=10.0,
            description='ST2',
            account=acct1,
            budget=e2budget,
            day_of_month=13
        )
        testdb.add(st2)
        # pair that matches OFXT6 and OFXT7
        testdb.add(Transaction(
            date=date(2017, 4, 16),
            actual_amount=25.00,
            description='trans4',
            account=acct2,
            budget=e2budget
        ))
        testdb.add(Transaction(
            date=date(2017, 4, 17),
            actual_amount=25.00,
            description='trans5',
            account=acct2,
            budget=e2budget
        ))
        testdb.flush()
        testdb.commit()

    def test_04_add_ofx(self, testdb):
        acct1 = testdb.query(Account).get(1)
        acct2 = testdb.query(Account).get(2)
        stmt1 = OFXStatement(
            account=acct1,
            filename='a1.ofx',
            file_mtime=dnow,
            as_of=dnow,
            currency='USD',
            acctid='1',
            bankid='b1',
            routing_number='r1'
        )
        testdb.add(stmt1)
        stmt2 = OFXStatement(
            account=acct2,
            filename='a2.ofx',
            file_mtime=dnow,
            as_of=dnow,
            currency='USD',
            acctid='2',
            bankid='b2',
            routing_number='r2'
        )
        testdb.add(stmt2)
        ################
        # transactions #
        ################
        # matches Transaction 1
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
            account=acct2,
            statement=stmt2,
            fitid='OFX3',
            trans_type='Purchase',
            date_posted=datetime(2017, 4, 9, 12, 3, 4, tzinfo=UTC),
            amount=-600.0,
            name='ofx3-trans2-st1'
        ))
        # non-matched - have Transaction 4 same amt but wrong acct
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFXT4',
            trans_type='Purchase',
            date_posted=datetime(2017, 4, 14, 12, 3, 4, tzinfo=UTC),
            amount=10.0,
            name='ofx4-st2'
        ))
        # matches ScheduledTransaction 2
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFXT5',
            trans_type='Foo',
            date_posted=datetime(2017, 4, 16, 12, 3, 4, tzinfo=UTC),
            amount=10.0,
            name='ofx5'
        ))
        # pair of matched transactions - Transaction 4 and 5
        testdb.add(OFXTransaction(
            account=acct2,
            statement=stmt2,
            fitid='OFXT6',
            trans_type='Foo',
            date_posted=datetime(2017, 4, 16, 12, 3, 4, tzinfo=UTC),
            amount=-25.0,
            name='ofx6'
        ))
        testdb.add(OFXTransaction(
            account=acct2,
            statement=stmt2,
            fitid='OFXT7',
            trans_type='Foo',
            date_posted=datetime(2017, 4, 17, 12, 3, 4, tzinfo=UTC),
            amount=-25.0,
            name='ofx7'
        ))
        testdb.flush()
        testdb.commit()

    def test_05_add_reconciled(self, testdb):
        acct2 = testdb.query(Account).get(2)
        stmt2 = testdb.query(OFXStatement).get(2)
        e2budget = testdb.query(Budget).get(3)
        o = OFXTransaction(
            account=acct2,
            statement=stmt2,
            fitid='OFX8',
            trans_type='Purchase',
            date_posted=datetime(2017, 4, 17, 12, 3, 4, tzinfo=UTC),
            amount=-600.0,
            name='ofx8-trans4'
        )
        testdb.add(o)
        t = Transaction(
            date=date(2017, 4, 16),
            actual_amount=600.00,
            description='trans6',
            account=acct2,
            budget=e2budget
        )
        testdb.add(t)
        testdb.add(TxnReconcile(transaction=t, ofx_trans=o))
        testdb.flush()
        testdb.commit()


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestColumns(ReconcileHelper):

    def test_06_transactions(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        trans_div = selenium.find_element_by_id('trans-panel')
        actual_trans = [
            self.normalize_html(x.get_attribute('outerHTML'))
            for x in trans_div.find_elements_by_class_name('reconcile-trans')
        ]
        expected_trans = [
            txn_div(
                1,
                date(2017, 4, 10),
                -100,
                'BankOne', 1,
                '1Income', 1,
                'income'
            ),
            txn_div(
                2,
                date(2017, 4, 10),
                250,
                'BankOne', 1,
                '3Periodic', 3,
                'trans1'
            ),
            txn_div(
                3,
                date(2017, 4, 11),
                600,
                'BankTwo', 2,
                '2Periodic', 2,
                'trans2'
            ),
            txn_div(
                4,
                date(2017, 4, 14),
                10,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans3'
            ),
            txn_div(
                5,
                date(2017, 4, 16),
                25,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans4'
            ),
            txn_div(
                6,
                date(2017, 4, 17),
                25,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans5'
            )
        ]
        assert actual_trans == expected_trans

    def test_07_ofxtrans(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel')
        actual_ofx = [
            self.normalize_html(x.get_attribute('outerHTML'))
            for x in ofxtrans_div.find_elements_by_class_name('reconcile-ofx')
        ]
        expected_ofx = [
            ofx_div(
                date(2017, 4, 9),
                600.00,
                'BankTwo', 2,
                'Purchase',
                'OFX3',
                'ofx3-trans2-st1'
            ),
            ofx_div(
                date(2017, 4, 10),
                -100,
                'BankOne', 1,
                'Deposit',
                'OFX1',
                'ofx1-income'
            ),
            ofx_div(
                date(2017, 4, 11),
                250,
                'BankOne', 1,
                'Debit',
                'OFX2',
                'ofx2-trans1'
            ),
            ofx_div(
                date(2017, 4, 14),
                10,
                'BankOne', 1,
                'Purchase',
                'OFXT4',
                'ofx4-st2'
            ),
            ofx_div(
                date(2017, 4, 16),
                10,
                'BankOne', 1,
                'Foo',
                'OFXT5',
                'ofx5'
            ),
            ofx_div(
                date(2017, 4, 16),
                25,
                'BankTwo', 2,
                'Foo',
                'OFXT6',
                'ofx6'
            ),
            ofx_div(
                date(2017, 4, 17),
                25,
                'BankTwo', 2,
                'Foo',
                'OFXT7',
                'ofx7'
            )
        ]
        assert expected_ofx == actual_ofx


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestAccountReconcileFalse(ReconcileHelper):

    def test_06_transactions(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        trans_div = selenium.find_element_by_id('trans-panel')
        actual_trans = [
            self.normalize_html(x.get_attribute('outerHTML'))
            for x in trans_div.find_elements_by_class_name('reconcile-trans')
        ]
        expected_trans = [
            txn_div(
                1,
                date(2017, 4, 10),
                -100,
                'BankOne', 1,
                '1Income', 1,
                'income'
            ),
            txn_div(
                2,
                date(2017, 4, 10),
                250,
                'BankOne', 1,
                '3Periodic', 3,
                'trans1'
            ),
            txn_div(
                3,
                date(2017, 4, 11),
                600,
                'BankTwo', 2,
                '2Periodic', 2,
                'trans2'
            ),
            txn_div(
                4,
                date(2017, 4, 14),
                10,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans3'
            ),
            txn_div(
                5,
                date(2017, 4, 16),
                25,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans4'
            ),
            txn_div(
                6,
                date(2017, 4, 17),
                25,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans5'
            )
        ]
        assert actual_trans == expected_trans

    def test_07_ofxtrans(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel')
        actual_ofx = [
            self.normalize_html(x.get_attribute('outerHTML'))
            for x in ofxtrans_div.find_elements_by_class_name('reconcile-ofx')
        ]
        expected_ofx = [
            ofx_div(
                date(2017, 4, 9),
                600.00,
                'BankTwo', 2,
                'Purchase',
                'OFX3',
                'ofx3-trans2-st1'
            ),
            ofx_div(
                date(2017, 4, 10),
                -100,
                'BankOne', 1,
                'Deposit',
                'OFX1',
                'ofx1-income'
            ),
            ofx_div(
                date(2017, 4, 11),
                250,
                'BankOne', 1,
                'Debit',
                'OFX2',
                'ofx2-trans1'
            ),
            ofx_div(
                date(2017, 4, 14),
                10,
                'BankOne', 1,
                'Purchase',
                'OFXT4',
                'ofx4-st2'
            ),
            ofx_div(
                date(2017, 4, 16),
                10,
                'BankOne', 1,
                'Foo',
                'OFXT5',
                'ofx5'
            ),
            ofx_div(
                date(2017, 4, 16),
                25,
                'BankTwo', 2,
                'Foo',
                'OFXT6',
                'ofx6'
            ),
            ofx_div(
                date(2017, 4, 17),
                25,
                'BankTwo', 2,
                'Foo',
                'OFXT7',
                'ofx7'
            )
        ]
        assert expected_ofx == actual_ofx

    def test_08_set_do_not_reconcile(self, testdb):
        acct = testdb.query(Account).get(2)
        acct.reconcile_trans = False
        testdb.flush()
        testdb.commit()

    def test_09_transactions(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        trans_div = selenium.find_element_by_id('trans-panel')
        actual_trans = [
            self.normalize_html(x.get_attribute('outerHTML'))
            for x in trans_div.find_elements_by_class_name('reconcile-trans')
        ]
        expected_trans = [
            txn_div(
                1,
                date(2017, 4, 10),
                -100,
                'BankOne', 1,
                '1Income', 1,
                'income'
            ),
            txn_div(
                2,
                date(2017, 4, 10),
                250,
                'BankOne', 1,
                '3Periodic', 3,
                'trans1'
            )
        ]
        assert actual_trans == expected_trans

    def test_10_ofxtrans(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel')
        actual_ofx = [
            self.normalize_html(x.get_attribute('outerHTML'))
            for x in ofxtrans_div.find_elements_by_class_name('reconcile-ofx')
        ]
        expected_ofx = [
            ofx_div(
                date(2017, 4, 10),
                -100,
                'BankOne', 1,
                'Deposit',
                'OFX1',
                'ofx1-income'
            ),
            ofx_div(
                date(2017, 4, 11),
                250,
                'BankOne', 1,
                'Debit',
                'OFX2',
                'ofx2-trans1'
            ),
            ofx_div(
                date(2017, 4, 14),
                10,
                'BankOne', 1,
                'Purchase',
                'OFXT4',
                'ofx4-st2'
            ),
            ofx_div(
                date(2017, 4, 16),
                10,
                'BankOne', 1,
                'Foo',
                'OFXT5',
                'ofx5'
            )
        ]
        assert expected_ofx == actual_ofx


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestTransactionEditModal(ReconcileHelper):

    def test_06_verify_db(self, testdb):
        t = testdb.query(Transaction).get(1)
        assert t is not None
        assert t.description == 'income'
        assert t.date == date(2017, 4, 10)
        assert float(t.actual_amount) == -100.00
        assert t.account_id == 1
        assert t.budget_id == 1

    def test_07_edit(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')
        link = selenium.find_element_by_xpath('//a[text()="Trans 1"]')
        link.click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Edit Transaction 1'
        assert body.find_element_by_id(
            'trans_frm_id').get_attribute('value') == '1'
        amt = body.find_element_by_id('trans_frm_amount')
        amt.clear()
        amt.send_keys('-123.45')
        desc = body.find_element_by_id('trans_frm_description')
        desc.send_keys('edited')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 1 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # test that updated budget was removed from the page
        trans_div = selenium.find_element_by_id('trans-panel')
        actual_trans = [
            self.normalize_html(t.get_attribute('outerHTML'))
            for t in trans_div.find_elements_by_class_name('reconcile-trans')
        ]
        expected_trans = [
            txn_div(
                1,
                date(2017, 4, 10),
                -123.45,
                'BankOne', 1,
                '1Income', 1,
                'incomeedited'
            ),
            txn_div(
                2,
                date(2017, 4, 10),
                250,
                'BankOne', 1,
                '3Periodic', 3,
                'trans1'
            ),
            txn_div(
                3,
                date(2017, 4, 11),
                600,
                'BankTwo', 2,
                '2Periodic', 2,
                'trans2'
            ),
            txn_div(
                4,
                date(2017, 4, 14),
                10,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans3'
            ),
            txn_div(
                5,
                date(2017, 4, 16),
                25,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans4'
            ),
            txn_div(
                6,
                date(2017, 4, 17),
                25,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans5'
            )
        ]
        assert actual_trans == expected_trans


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestDragLimitations(ReconcileHelper):

    def test_06_success(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')
        src = selenium.find_element_by_id('ofx-2-OFX3')
        tgt = selenium.find_element_by_id(
            'trans-3').find_element_by_class_name('reconcile-drop-target')
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(src, tgt).perform()
        # ensure that the OFX div was hidden in the OFX column
        src = selenium.find_element_by_id('ofx-2-OFX3')
        assert src.is_displayed() is False
        # ensure that the OFX div was placed in the drop target
        tgt = selenium.find_element_by_id('trans-3')
        expected = txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2',
            drop_div=ofx_div(
                date(2017, 4, 9),
                600.00,
                'BankTwo', 2,
                'Purchase',
                'OFX3',
                'ofx3-trans2-st1',
                trans_id=3
            )
        )
        assert self.normalize_html(tgt.get_attribute('outerHTML')) == expected
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {
            3: [2, 'OFX3']
        }

    def test_07_already_has_ofx(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')
        src = selenium.find_element_by_id('ofx-2-OFXT6')
        src2 = selenium.find_element_by_id('ofx-2-OFXT7')
        tgt = selenium.find_element_by_id(
            'trans-5').find_element_by_class_name('reconcile-drop-target')
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(src, tgt).perform()
        # ensure that the OFX div was hidden in the OFX column
        src = selenium.find_element_by_id('ofx-2-OFXT6')
        assert src.is_displayed() is False
        # ensure that the OFX div was placed in the drop target
        tgt = selenium.find_element_by_id('trans-5')
        expected = txn_div(
            5,
            date(2017, 4, 16),
            25,
            'BankTwo', 2,
            '3Periodic', 3,
            'trans4',
            drop_div=ofx_div(
                date(2017, 4, 16),
                25,
                'BankTwo', 2,
                'Foo',
                'OFXT6',
                'ofx6',
                trans_id=5
            )
        )
        assert self.normalize_html(tgt.get_attribute('outerHTML')) == expected
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {
            5: [2, 'OFXT6']
        }
        # get the innerHTML of both columns
        trans_div = selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML')
        # attempt to drag the other OFX
        chain = ActionChains(selenium)
        chain.drag_and_drop(src2, tgt).perform()
        # sleep a bit for the drag to stop
        sleep(1)
        # ensure both columns are still the same
        assert selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML') == trans_div
        assert selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML') == ofxtrans_div
        # ensure reconciled JS var is still the same
        assert self.get_reconciled(selenium) == {
            5: [2, 'OFXT6']
        }

    def test_08_wrong_account(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')
        src = selenium.find_element_by_id('ofx-1-OFXT4')
        tgt = selenium.find_element_by_id(
            'trans-4').find_element_by_class_name('reconcile-drop-target')
        # get the innerHTML of both columns
        trans_div = selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML')
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(src, tgt).perform()
        # sleep a bit for the drag to stop
        sleep(1)
        # ensure both columns are still the same
        assert selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML') == trans_div
        assert selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML') == ofxtrans_div
        # ensure reconciled JS var is still the same
        assert self.get_reconciled(selenium) == {}

    def test_09_wrong_amount(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')
        src = selenium.find_element_by_id('ofx-1-OFXT4')
        tgt = selenium.find_element_by_id(
            'trans-1').find_element_by_class_name('reconcile-drop-target')
        # get the innerHTML of both columns
        trans_div = selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML')
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(src, tgt).perform()
        # sleep a bit for the drag to stop
        sleep(1)
        # ensure both columns are still the same
        assert selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML') == trans_div
        assert selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML') == ofxtrans_div
        # ensure reconciled JS var is still the same
        assert self.get_reconciled(selenium) == {}

    def test_10_wrong_acct_and_amount(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')
        src = selenium.find_element_by_id('ofx-1-OFXT4')
        tgt = selenium.find_element_by_id(
            'trans-3').find_element_by_class_name('reconcile-drop-target')
        # get the innerHTML of both columns
        trans_div = selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML')
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(src, tgt).perform()
        # sleep a bit for the drag to stop
        sleep(1)
        # ensure both columns are still the same
        assert selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML') == trans_div
        assert selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML') == ofxtrans_div
        # ensure reconciled JS var is still the same
        assert self.get_reconciled(selenium) == {}

    def test_11_unreconcile(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/reconcile')
        src = selenium.find_element_by_id('ofx-2-OFX3')
        tgt = selenium.find_element_by_id(
            'trans-3').find_element_by_class_name('reconcile-drop-target')
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(src, tgt).perform()
        # ensure that the OFX div was hidden in the OFX column
        src = selenium.find_element_by_id('ofx-2-OFX3')
        assert src.is_displayed() is False
        # ensure that the OFX div was placed in the drop target
        tgt = selenium.find_element_by_id('trans-3')
        expected = txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2',
            drop_div=ofx_div(
                date(2017, 4, 9),
                600.00,
                'BankTwo', 2,
                'Purchase',
                'OFX3',
                'ofx3-trans2-st1',
                trans_id=3
            )
        )
        assert self.normalize_html(tgt.get_attribute('outerHTML')) == expected
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {
            3: [2, 'OFX3']
        }
        # unreconcile
        link = tgt.find_element_by_xpath('//a[text()="Unreconcile"]')
        link.click()
        src = selenium.find_element_by_id('ofx-2-OFX3')
        tgt = selenium.find_element_by_id('trans-3')
        assert src.is_displayed() is True
        assert self.normalize_html(src.get_attribute('outerHTML')) == ofx_div(
            date(2017, 4, 9),
            600.00,
            'BankTwo', 2,
            'Purchase',
            'OFX3',
            'ofx3-trans2-st1'
        )
        assert tgt.find_element_by_class_name(
            'reconcile-drop-target').get_attribute('innerHTML') == ''
        assert self.get_reconciled(selenium) == {}
        expected = txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2'
        )
        assert self.normalize_html(tgt.get_attribute('outerHTML')) == expected


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestDragAndDropReconcile(ReconcileHelper):

    def test_06_verify_db(self, testdb):
        res = testdb.query(TxnReconcile).all()
        assert len(res) == 1
        assert res[0].id == 1
        assert res[0].txn_id == 7
        assert res[0].ofx_account_id == 2
        assert res[0].ofx_fitid == 'OFX8'

    def test_07_drag_and_drop(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-2-OFX3'),
            selenium.find_element_by_id(
                'trans-3'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-1-OFX1'),
            selenium.find_element_by_id(
                'trans-1'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-1-OFX2'),
            selenium.find_element_by_id(
                'trans-2'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-2-OFXT6'),
            selenium.find_element_by_id(
                'trans-5'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-2-OFXT7'),
            selenium.find_element_by_id(
                'trans-6'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {
            3: [2, 'OFX3'],
            1: [1, 'OFX1'],
            2: [1, 'OFX2'],
            5: [2, 'OFXT6'],
            6: [2, 'OFXT7']
        }
        # click submit button
        selenium.find_element_by_id('reconcile-submit').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        assert self.get_reconciled(selenium) == {}
        msg = selenium.find_element_by_id('reconcile-msg')
        assert msg.text == 'Successfully reconciled 5 transactions'
        assert 'alert-success' in msg.get_attribute('class')

    def test_08_submit_with_nothing_reconciled(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        assert self.get_reconciled(selenium) == {}
        # get the innerHTML of both columns
        trans_div = selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML')
        # attempt to drag the other OFX
        selenium.find_element_by_id('reconcile-submit').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        # ensure both columns are still the same
        assert selenium.find_element_by_id('trans-panel').get_attribute(
            'innerHTML') == trans_div
        assert selenium.find_element_by_id('ofx-panel').get_attribute(
            'innerHTML') == ofxtrans_div
        msg = selenium.find_element_by_id('reconcile-msg')
        assert msg.text == 'Warning: No reconciled transactions; ' \
                           'did not submit form.'
        assert 'alert-warning' in msg.get_attribute('class')


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestUIReconcileMulti(ReconcileHelper):

    def test_06_verify_db(self, testdb):
        res = testdb.query(TxnReconcile).all()
        assert len(res) == 1
        assert res[0].id == 1
        assert res[0].txn_id == 7
        assert res[0].ofx_account_id == 2
        assert res[0].ofx_fitid == 'OFX8'

    def test_07_drag_and_drop(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-2-OFX3'),
            selenium.find_element_by_id(
                'trans-3'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {
            3: [2, 'OFX3']
        }
        # click submit button
        selenium.find_element_by_id('reconcile-submit').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        assert self.get_reconciled(selenium) == {}
        msg = selenium.find_element_by_id('reconcile-msg')
        assert msg.text == 'Successfully reconciled 1 transactions'
        assert 'alert-success' in msg.get_attribute('class')
        # reconcile 2 more
        self.wait_for_id(selenium, 'ofx-1-OFX2')
        chain = ActionChains(selenium)
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-1-OFX1'),
            selenium.find_element_by_id(
                'trans-1'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-1-OFX2'),
            selenium.find_element_by_id(
                'trans-2'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {
            1: [1, 'OFX1'],
            2: [1, 'OFX2']
        }
        # click submit button
        selenium.find_element_by_id('reconcile-submit').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        assert self.get_reconciled(selenium) == {}
        msg = selenium.find_element_by_id('reconcile-msg')
        assert msg.text == 'Successfully reconciled 2 transactions'
        assert 'alert-success' in msg.get_attribute('class')

    def test_08_invalid_trans_id(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        assert self.get_reconciled(selenium) == {}
        script = 'reconciled[1234] = [4, "OFXNONE"];'
        selenium.execute_script(script)
        assert self.get_reconciled(selenium) == {
            1234: [4, "OFXNONE"]
        }
        # click submit button
        selenium.find_element_by_id('reconcile-submit').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        assert self.get_reconciled(selenium) == {
            1234: [4, "OFXNONE"]
        }
        msg = selenium.find_element_by_id('reconcile-msg')
        assert msg.text == 'Error 400: Invalid Transaction ID: 1234'
        assert 'alert-danger' in msg.get_attribute('class')


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestReconcileBackend(ReconcileHelper):

    def test_06_verify_db(self, testdb):
        res = testdb.query(TxnReconcile).all()
        assert len(res) == 1
        assert res[0].id == 1
        assert res[0].txn_id == 7
        assert res[0].ofx_account_id == 2
        assert res[0].ofx_fitid == 'OFX8'

    def test_07_success(self, base_url):
        res = requests.post(
            base_url + '/ajax/reconcile',
            json={3: [2, 'OFX3']}
        )
        assert res.json() == {
            'success': True,
            'success_message': 'Successfully reconciled 1 transactions'
        }
        assert res.status_code == 200

    def test_08_verify_db(self, testdb):
        res = testdb.query(TxnReconcile).all()
        assert len(res) == 2
        assert res[0].id == 1
        assert res[1].id == 2
        assert res[1].txn_id == 3
        assert res[1].ofx_account_id == 2
        assert res[1].ofx_fitid == 'OFX3'

    def test_09_invalid_trans(self, base_url, testdb):
        res = requests.post(
            base_url + '/ajax/reconcile',
            json={32198: [2, 'OFX3']}
        )
        assert res.json() == {
            'success': False,
            'error_message': 'Invalid Transaction ID: 32198'
        }
        assert res.status_code == 400
        assert len(testdb.query(TxnReconcile).all()) == 2

    def test_10_invalid_ofx(self, base_url, testdb):
        res = requests.post(
            base_url + '/ajax/reconcile',
            json={3: [2, 'OFX338ufd']}
        )
        assert res.json() == {
            'success': False,
            'error_message': "Invalid OFXTransaction: (2, 'OFX338ufd')"
        }
        assert res.status_code == 400
        assert len(testdb.query(TxnReconcile).all()) == 2

    def test_10_commit_exception(self, base_url):
        # already reconciled in test_07
        res = requests.post(
            base_url + '/ajax/reconcile',
            json={3: [2, 'OFX3']}
        )
        j = res.json()
        assert sorted(j.keys()) == ['error_message', 'success']
        assert j['success'] is False
        assert j['error_message'].startswith('Exception committing reconcile')
        assert "Duplicate entry '3' for key " \
               "'uq_txn_reconciles_txn_id'" in j['error_message']
        assert res.status_code == 400

    def test_11_verify_db(self, testdb):
        testdb.expire_all()
        res = testdb.query(TxnReconcile).all()
        assert len(res) == 2
        assert res[0].id == 1
        assert res[1].id == 2
        assert res[1].txn_id == 3
        assert res[1].ofx_account_id == 2
        assert res[1].ofx_fitid == 'OFX3'

    def test_12_reconcile_noOFX(self, base_url):
        res = requests.post(
            base_url + '/ajax/reconcile',
            json={4: 'Foo Bar Baz'}
        )
        assert res.json() == {
            'success': True,
            'success_message': 'Successfully reconciled 1 transactions'
        }
        assert res.status_code == 200

    def test_13_verify_db(self, testdb):
        testdb.expire_all()
        res = testdb.query(TxnReconcile).all()
        assert len(res) == 3
        assert res[2].txn_id == 4
        assert res[2].note == 'Foo Bar Baz'

    def test_14_verify_reconcile_modal(self, base_url, selenium, testdb):
        res = testdb.query(TxnReconcile).all()
        txn_id = res[-1].txn_id
        self.get(selenium, base_url + '/transactions')
        selenium.find_element_by_link_text('Yes (%s)' % txn_id).click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Transaction Reconcile %s' % txn_id
        assert 'Foo Bar Baz' in body.text
        assert body.find_elements_by_class_name('col-lg-6')[1].text == \
            'No OFX Transaction'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestOFXMakeTrans(AcceptanceHelper):

    def get_reconciled(self, driver):
        """
        Execute javascript in the selenium browser to return the
        ``reconciled`` JavaScript object as a JSON string; deserialize the
        JSON and return the resulting dict.

        :param driver: Selenium driver instance
        :type driver: selenium.webdriver.remote.webdriver.WebDriver
        :return: ``reconciled`` javascript variable from page
        :rtype: dict
        """
        script = 'return JSON.stringify(reconciled);'
        res = driver.execute_script(script)
        print("reconciled JSON: %s" % res)
        r = json.loads(res)
        return {int(x): r[x] for x in r}

    def test_00_clean_db(self, dump_file_path):
        # clean the database; empty schema
        restore_mysqldump(dump_file_path, engine, with_data=False)

    def test_01_add_accounts(self, testdb):
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
        b = Account(
            description='Second Bank Account',
            name='BankTwo',
            acct_type=AcctType.Bank,
            negate_ofx_amounts=True
        )
        testdb.add(b)
        b.set_balance(
            overall_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC),
            ledger=1.0,
            ledger_date=datetime(2017, 4, 10, 12, 0, 0, tzinfo=UTC)
        )
        testdb.flush()
        testdb.commit()

    def test_02_add_budgets(self, testdb):
        testdb.add(Budget(
            name='1Income',
            is_periodic=True,
            description='1Income',
            starting_balance=0.0,
            is_income=True
        ))
        testdb.add(Budget(
            name='2Periodic',
            is_periodic=True,
            description='2Periodic',
            starting_balance=500.00
        ))
        testdb.add(Budget(
            name='3Periodic',
            is_periodic=True,
            description='3Periodic',
            starting_balance=0.00
        ))
        testdb.flush()
        testdb.commit()

    def test_03_add_transactions(self, testdb):
        acct1 = testdb.query(Account).get(1)
        ibudget = testdb.query(Budget).get(1)
        # income - matches OFX1
        testdb.add(Transaction(
            date=date(2017, 4, 10),
            actual_amount=-123.45,
            budgeted_amount=-123.45,
            description='income',
            account=acct1,
            budget=ibudget
        ))
        testdb.flush()
        testdb.commit()

    def test_04_add_ofx(self, testdb):
        acct2 = testdb.query(Account).get(2)
        stmt1 = OFXStatement(
            account=acct2,
            filename='a2.ofx',
            file_mtime=dnow,
            as_of=dnow,
            currency='USD',
            acctid='2',
            bankid='b1',
            routing_number='r1'
        )
        testdb.add(stmt1)
        # matches Transaction 2
        testdb.add(OFXTransaction(
            account=acct2,
            statement=stmt1,
            fitid='OFX2',
            trans_type='Debit',
            date_posted=datetime(2017, 4, 11, 12, 3, 4, tzinfo=UTC),
            amount=251.23,
            name='ofx2-trans1'
        ))
        testdb.flush()
        testdb.commit()

    def test_06_verify_db(self, testdb):
        res = testdb.query(TxnReconcile).all()
        assert len(res) == 0

    def test_07_verify_db_transaction(self, testdb):
        res = testdb.query(Transaction).all()
        assert len(res) == 1
        assert res[0].id == 1

    def test_08_trans_from_ofx(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        ofxdiv = selenium.find_element_by_id('ofx-2-OFX2')
        link = ofxdiv.find_element_by_xpath('//a[text()="(make trans)"]')
        link.click()
        # test the modal population
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Add Transaction for OFX (2, OFX2)'
        assert body.find_element_by_id(
            'trans_frm_date').get_attribute('value') == date(
            2017, 4, 11).strftime('%Y-%m-%d')
        assert body.find_element_by_id(
            'trans_frm_amount').get_attribute('value') == '-251.23'
        assert body.find_element_by_id(
            'trans_frm_description').get_attribute('value') == 'ofx2-trans1'
        acct_sel = Select(body.find_element_by_id('trans_frm_account'))
        opts = []
        for o in acct_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', 'BankOne'],
            ['2', 'BankTwo']
        ]
        assert acct_sel.first_selected_option.get_attribute('value') == '2'
        budget_sel = Select(body.find_element_by_id('trans_frm_budget'))
        opts = []
        for o in budget_sel.options:
            opts.append([o.get_attribute('value'), o.text])
        assert opts == [
            ['None', ''],
            ['1', '1Income (i)'],
            ['2', '2Periodic'],
            ['3', '3Periodic']
        ]
        budget_sel.select_by_value('2')
        notes = selenium.find_element_by_id('trans_frm_notes')
        assert notes.get_attribute(
            'value') == 'created from OFXTransaction(2, OFX2)'
        notes.send_keys('foo')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        # check that we got positive confirmation
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements_by_tag_name('div')[0]
        assert 'alert-success' in x.get_attribute('class')
        assert x.text.strip() == 'Successfully saved Transaction 2 ' \
                                 'in database.'
        # dismiss the modal
        selenium.find_element_by_id('modalCloseButton').click()
        self.wait_for_jquery_done(selenium)
        # ensure that the original OFX div is hidden
        assert selenium.find_element_by_id('ofx-2-OFX2').is_displayed() is False
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {
            2: [2, 'OFX2']
        }
        # ensure that the Transaction was added, and the ofx moved to it
        trans_div = selenium.find_element_by_id('trans-panel')
        actual_trans = [
            self.normalize_html(t.get_attribute('outerHTML'))
            for t in trans_div.find_elements_by_class_name('reconcile-trans')
        ]
        expected_trans = [
            txn_div(
                1,
                date(2017, 4, 10),
                -123.45,
                'BankOne', 1,
                '1Income', 1,
                'income'
            ),
            txn_div(
                2,
                date(2017, 4, 11),
                -251.23,
                'BankTwo', 2,
                '2Periodic', 2,
                'ofx2-trans1',
                drop_div=ofx_div(
                    date(2017, 4, 11),
                    -251.23,
                    'BankTwo', 2,
                    'Debit',
                    'OFX2',
                    'ofx2-trans1',
                    trans_id=2
                )
            )
        ]
        assert actual_trans == expected_trans
        # wait for submit button to be visible and clickable, and click it
        self.wait_for_jquery_done(selenium)
        WebDriverWait(selenium, 10).until(
            EC.invisibility_of_element_located((By.ID, 'modalDiv'))
        )
        WebDriverWait(selenium, 10).until(
            EC.element_to_be_clickable((By.ID, 'reconcile-submit'))
        )
        selenium.find_element_by_id('reconcile-submit').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        assert self.get_reconciled(selenium) == {}
        msg = selenium.find_element_by_id('reconcile-msg')
        assert msg.text == 'Successfully reconciled 1 transactions'
        assert 'alert-success' in msg.get_attribute('class')

    def test_09_verify_db_txnreconcile(self, testdb):
        res = testdb.query(TxnReconcile).all()
        assert len(res) == 1
        assert res[0].id == 1
        assert res[0].txn_id == 2
        assert res[0].ofx_account_id == 2
        assert res[0].ofx_fitid == 'OFX2'

    def test_10_verify_db_transaction(self, testdb):
        res = testdb.query(Transaction).all()
        assert len(res) == 2
        assert res[1].id == 2
        assert res[1].account_id == 2
        assert res[1].date == date(2017, 4, 11)
        assert float(res[1].actual_amount) == -251.23
        assert res[1].description == 'ofx2-trans1'
        assert res[1].budget_id == 2
        assert res[1].notes == 'created from OFXTransaction(2, OFX2)foo'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestTransReconcileNoOfx(ReconcileHelper):

    def test_06_transactions_column(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        trans_div = selenium.find_element_by_id('trans-panel')
        actual_trans = [
            self.normalize_html(x.get_attribute('outerHTML'))
            for x in trans_div.find_elements_by_class_name('reconcile-trans')
        ]
        expected_trans = [
            txn_div(
                1,
                date(2017, 4, 10),
                -100,
                'BankOne', 1,
                '1Income', 1,
                'income'
            ),
            txn_div(
                2,
                date(2017, 4, 10),
                250,
                'BankOne', 1,
                '3Periodic', 3,
                'trans1'
            ),
            txn_div(
                3,
                date(2017, 4, 11),
                600,
                'BankTwo', 2,
                '2Periodic', 2,
                'trans2'
            ),
            txn_div(
                4,
                date(2017, 4, 14),
                10,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans3'
            ),
            txn_div(
                5,
                date(2017, 4, 16),
                25,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans4'
            ),
            txn_div(
                6,
                date(2017, 4, 17),
                25,
                'BankTwo', 2,
                '3Periodic', 3,
                'trans5'
            )
        ]
        assert actual_trans == expected_trans

    def test_07_ofx_column(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        ofxtrans_div = selenium.find_element_by_id('ofx-panel')
        actual_ofx = [
            self.normalize_html(x.get_attribute('outerHTML'))
            for x in ofxtrans_div.find_elements_by_class_name('reconcile-ofx')
        ]
        expected_ofx = [
            ofx_div(
                date(2017, 4, 9),
                600.00,
                'BankTwo', 2,
                'Purchase',
                'OFX3',
                'ofx3-trans2-st1'
            ),
            ofx_div(
                date(2017, 4, 10),
                -100,
                'BankOne', 1,
                'Deposit',
                'OFX1',
                'ofx1-income'
            ),
            ofx_div(
                date(2017, 4, 11),
                250,
                'BankOne', 1,
                'Debit',
                'OFX2',
                'ofx2-trans1'
            ),
            ofx_div(
                date(2017, 4, 14),
                10,
                'BankOne', 1,
                'Purchase',
                'OFXT4',
                'ofx4-st2'
            ),
            ofx_div(
                date(2017, 4, 16),
                10,
                'BankOne', 1,
                'Foo',
                'OFXT5',
                'ofx5'
            ),
            ofx_div(
                date(2017, 4, 16),
                25,
                'BankTwo', 2,
                'Foo',
                'OFXT6',
                'ofx6'
            ),
            ofx_div(
                date(2017, 4, 17),
                25,
                'BankTwo', 2,
                'Foo',
                'OFXT7',
                'ofx7'
            )
        ]
        assert expected_ofx == actual_ofx

    def test_08_reconcile_unreconcile_noOFX_visible(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        # check Trans and OFX
        trans = selenium.find_element_by_id('trans-3')
        assert self.normalize_html(trans.get_attribute('outerHTML')) == txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2'
        )
        ofx = selenium.find_element_by_id('ofx-2-OFX3')
        assert self.normalize_html(ofx.get_attribute('outerHTML')) == ofx_div(
            date(2017, 4, 9),
            600.00,
            'BankTwo', 2,
            'Purchase',
            'OFX3',
            'ofx3-trans2-st1'
        )
        # drag and drop
        chain = ActionChains(selenium)
        chain.drag_and_drop(
            selenium.find_element_by_id('ofx-2-OFX3'),
            selenium.find_element_by_id(
                'trans-3'
            ).find_element_by_class_name('reconcile-drop-target')
        ).perform()
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {
            3: [2, 'OFX3']
        }
        # check Trans and OFX
        trans = selenium.find_element_by_id('trans-3')
        assert self.normalize_html(trans.get_attribute('outerHTML')) == txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2',
            drop_div=ofx_div(
                date(2017, 4, 9),
                600.00,
                'BankTwo', 2,
                'Purchase',
                'OFX3',
                'ofx3-trans2-st1',
                trans_id=3
            )
        )
        ofx = selenium.find_element_by_id('ofx-2-OFX3')
        assert ofx.is_displayed() is False
        # unreconcile
        trans.find_element_by_xpath('//a[text()="Unreconcile"]').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        # check Trans and OFX
        trans = selenium.find_element_by_id('trans-3')
        assert self.normalize_html(trans.get_attribute('outerHTML')) == txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2'
        )
        ofx = selenium.find_element_by_id('ofx-2-OFX3')
        assert self.normalize_html(ofx.get_attribute('outerHTML')) == ofx_div(
            date(2017, 4, 9),
            600.00,
            'BankTwo', 2,
            'Purchase',
            'OFX3',
            'ofx3-trans2-st1'
        )
        # ensure the reconciled variable was updated
        assert self.get_reconciled(selenium) == {}
        # click submit button
        selenium.find_element_by_id('reconcile-submit').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        assert self.get_reconciled(selenium) == {}
        msg = selenium.find_element_by_id('reconcile-msg')
        assert msg.text == 'Warning: No reconciled transactions; ' \
            'did not submit form.'
        assert 'alert-warning' in msg.get_attribute('class')

    def test_09_reconcile_unreconcile_noOFX(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        # check Trans and OFX
        trans = selenium.find_element_by_id('trans-3')
        assert self.normalize_html(trans.get_attribute('outerHTML')) == txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2'
        )
        ofx = selenium.find_element_by_id('ofx-2-OFX3')
        assert self.normalize_html(ofx.get_attribute('outerHTML')) == ofx_div(
            date(2017, 4, 9),
            600.00,
            'BankTwo', 2,
            'Purchase',
            'OFX3',
            'ofx3-trans2-st1'
        )
        assert self.get_reconciled(selenium) == {}
        # reconcile as noOFX
        trans.find_element_by_link_text('(no OFX)').click()
        modal, title, body = self.get_modal_parts(selenium)
        self.assert_modal_displayed(modal, title, body)
        assert title.text == 'Reconcile Transaction 3 Without OFX'
        assert body.find_element_by_id(
            'trans_frm_id').get_attribute('value') == '3'
        note = body.find_element_by_id('trans_frm_note')
        note.clear()
        note.send_keys('My Trans Note')
        # submit the form
        selenium.find_element_by_id('modalSaveButton').click()
        sleep(1)
        self.wait_for_jquery_done(selenium)
        # assert modal is hidden
        assert selenium.find_element_by_id('modalDiv').is_displayed() is False
        # test trans div was updated
        noofx_div = '<div style="text-align: right;"><a href="' \
                    'javascript:reconcileDoUnreconcileNoOfx(3)">' \
                    'Unreconcile</a></div><div class="reconcile" ' \
                    'id="trans-3-noOFX" style=""><p><strong>No OFX:</strong>' \
                    ' My Trans Note</p></div>'
        trans = selenium.find_element_by_id('trans-3')
        assert self.normalize_html(trans.get_attribute('outerHTML')) == txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2',
            drop_div=noofx_div
        )
        # test that reconciled var was updated
        assert self.get_reconciled(selenium) == {3: 'My Trans Note'}
        # unreconcile
        trans.find_element_by_link_text('Unreconcile').click()
        trans = selenium.find_element_by_id('trans-3')
        assert self.normalize_html(trans.get_attribute('outerHTML')) == txn_div(
            3,
            date(2017, 4, 11),
            600,
            'BankTwo', 2,
            '2Periodic', 2,
            'trans2'
        )
        assert self.get_reconciled(selenium) == {}
