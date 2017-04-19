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

from biweeklybudget.utils import dtnow
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models import *
import biweeklybudget.models.base  # noqa
from biweeklybudget.tests.conftest import engine

dnow = dtnow()


@pytest.mark.acceptance
class TestReconcile(AcceptanceHelper):

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium, testflask, refreshdb):  # noqa
        self.baseurl = base_url
        selenium.get(base_url + '/reconcile')

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


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
class TestReconcileSimple(AcceptanceHelper):

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
            acct_type=AcctType.Bank
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
        # income
        testdb.add(Transaction(
            date=date(2017, 4, 10),
            actual_amount=-100.00,
            budgeted_amount=-100.00,
            description='income',
            account=acct1,
            budget=ibudget
        ))
        # one transaction
        testdb.add(Transaction(
            date=date(2017, 4, 10),
            actual_amount=250.00,
            description='trans1',
            account=acct1,
            budget=e2budget
        ))
        # another transaction
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
            actual_amount=1400.00,
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
        # transactions
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFX1',
            trans_type='Deposit',
            date_posted=datetime(2017, 4, 10, 12, 3, 4, tzinfo=UTC),
            amount=100.0,
            name='ofx1-income'
        ))
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFX2',
            trans_type='Debit',
            date_posted=datetime(2017, 4, 11, 12, 3, 4, tzinfo=UTC),
            amount=-250.0,
            name='ofx2-trans1'
        ))
        testdb.add(OFXTransaction(
            account=acct2,
            statement=stmt2,
            fitid='OFX3',
            trans_type='Purchase',
            date_posted=datetime(2017, 4, 9, 12, 3, 4, tzinfo=UTC),
            amount=-600.0,
            name='ofx3-trans2-st1'
        ))
        testdb.add(OFXTransaction(
            account=acct1,
            statement=stmt1,
            fitid='OFXT4',
            trans_type='Purchase',
            date_posted=datetime(2017, 4, 14, 12, 3, 4, tzinfo=UTC),
            amount=-10.0,
            name='ofx4-st2'
        ))
        testdb.add(OFXTransaction(
            account=acct2,
            statement=stmt2,
            fitid='OFXT5',
            trans_type='Foo',
            date_posted=datetime(2017, 4, 16, 12, 3, 4, tzinfo=UTC),
            amount=123.0,
            name='ofx5'
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
            fitid='OFX6',
            trans_type='Purchase',
            date_posted=datetime(2017, 4, 17, 12, 3, 4, tzinfo=UTC),
            amount=-600.0,
            name='ofx6-trans4'
        )
        testdb.add(o)
        t = Transaction(
            date=date(2017, 4, 16),
            actual_amount=600.00,
            description='trans4',
            account=acct2,
            budget=e2budget
        )
        testdb.add(t)
        testdb.add(TxnReconcile(transaction=t, ofx_trans=o))
        testdb.flush()
        testdb.commit()
