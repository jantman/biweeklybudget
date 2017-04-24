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
from locale import currency
import re
import json
from time import sleep
from selenium.webdriver import ActionChains

from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models import *
import biweeklybudget.models.base  # noqa
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
    s += '<div class="col-lg-3">%s</div>' % currency(amt, grouping=True)
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
        s += '<a href="javascript:transModal('
        s += '%s, function () { updateReconcileTrans(%s) })">Trans %s</a>: ' \
             '%s' % (id, id, id, desc)
    else:
        s += '<span class="disabledEditLink">Trans %s</span>: %s' % (
            id, desc
        )
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
    s += '<div class="col-lg-3">%s</div>' % currency(amt, grouping=True)
    s += '<div class="col-lg-3"><strong>Acct:</strong> '
    s += '<span style="white-space: nowrap;">'
    s += '<a href="/accounts/%s">%s (%s)</a>' % (acct_id, acct_name, acct_id)
    s += '</span></div>'
    s += '<div class="col-lg-3"><strong>Type:</strong> %s</div>' % trans_type
    s += '</div>'
    s += '<div class="row"><div class="col-lg-12">'
    s += '<a href="javascript:ofxTransModal(%s, \'%s\', false)">%s</a>' % (
        acct_id, cfitid, fitid
    )
    s += ': %s' % name
    s += '</div>'
    s += '</div></div>'
    if trans_id is not None:
        return '<div style="text-align: right;"><a href="javascript:reconc' \
               'ileDoUnreconcile(%s, %s, \'%s\')">Unreconcile</a></div>%s' % (
                   trans_id, acct_id, fitid, s
               )
    return s


@pytest.mark.acceptance
class DONOTTestReconcile(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
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

    def test_00_clean_db(self, testdb):
        # clean the database
        biweeklybudget.models.base.Base.metadata.reflect(engine)
        biweeklybudget.models.base.Base.metadata.drop_all(engine)
        biweeklybudget.models.base.Base.metadata.create_all(engine)

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
class DONOTTestColumns(ReconcileHelper):

    def test_06_transactions(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        trans_div = selenium.find_element_by_id('trans-panel')
        actual_trans = [
            x.get_attribute('outerHTML')
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
            x.get_attribute('outerHTML')
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
class DONOTTestTransactionEditModal(ReconcileHelper):

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
            x.get_attribute('outerHTML')
            for x in trans_div.find_elements_by_class_name('reconcile-trans')
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
class DONOTTestDragLimitations(ReconcileHelper):

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
        assert tgt.get_attribute('outerHTML') == expected
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
        assert tgt.get_attribute('outerHTML') == expected
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
        assert tgt.get_attribute('outerHTML') == expected
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
        assert src.get_attribute('outerHTML') == ofx_div(
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
        assert tgt.get_attribute('outerHTML') == expected


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
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

    def test_08_submit_with_nothing_reconciled(self, base_url, selenium):
        self.get(selenium, base_url + '/reconcile')
        # check the columns
        # submit the form
        # make sure the columns are the same
        # make sure the warning box is there
