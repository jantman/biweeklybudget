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
from decimal import Decimal

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.ofx_statement import OFXStatement


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestTransStandingBudgetBalanceUpdate(AcceptanceHelper):

    def test_0_verify_db(self, testdb):
        """initial state verification"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 4
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert standing.current_balance == Decimal('9482.29')
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None

    def test_1_add_trans_periodic_budget(self, testdb):
        """add a transaction against a periodic budget"""
        t = Transaction(
            budget_amounts={testdb.query(Budget).get(2): Decimal('222.22')},
            budgeted_amount=Decimal('123.45'),
            description='T5',
            notes='notesT5',
            account=testdb.query(Account).get(1),
            planned_budget=testdb.query(Budget).get(2)
        )
        testdb.add(t)
        testdb.flush()
        testdb.commit()

    def test_2_verify_db(self, testdb):
        """verify no budget objects changed"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 5
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert standing.current_balance == Decimal('9482.29')
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None

    def test_3_add_trans_standing_budget(self, testdb):
        """add a transaction against a standing budget"""
        t = Transaction(
            budget_amounts={testdb.query(Budget).get(5): Decimal('222.22')},
            budgeted_amount=Decimal('123.45'),
            description='T6',
            notes='notesT6',
            account=testdb.query(Account).get(1),
            planned_budget=testdb.query(Budget).get(5)
        )
        testdb.add(t)
        testdb.flush()
        testdb.commit()

    def test_4_verify_db(self, testdb):
        """verify the standing budget balance was updated"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 6
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert standing.current_balance == Decimal('9260.07')
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None

    def test_5_edit_trans_standing_budget(self, testdb):
        """edit a transaction against a standing budget"""
        t = testdb.query(Transaction).get(6)
        budg = testdb.query(Budget).get(5)
        t.set_budget_amounts({budg: Decimal('111.11')})
        testdb.add(t)
        testdb.flush()
        testdb.commit()

    def test_6_verify_db(self, testdb):
        """verify the standing budget balance was updated"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 6
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert standing.current_balance == Decimal('9371.18')
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None

    def test_7_edit_trans_standing_budget(self, testdb):
        """edit a transaction against a standing budget"""
        t = testdb.query(Transaction).get(6)
        t.set_budget_amounts({testdb.query(Budget).get(5): Decimal('-111.11')})
        testdb.add(t)
        testdb.flush()
        testdb.commit()

    def test_8_verify_db(self, testdb):
        """verify the standing budget balance was updated"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 6
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert standing.current_balance == Decimal('9593.40')
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
class TestIsFieldsSet(AcceptanceHelper):

    def test_0_is_fields_set_by_ofxtxn_event_handler(self, testdb):
        """
        Test for
        :py:func:`~.db_event_handlers.handle_ofx_transaction_new_or_change`
        """
        acct = testdb.query(Account).get(1)
        acct.re_interest_paid = None
        testdb.commit()
        assert acct.re_interest_charge == '^interest-charge'
        assert acct.re_interest_paid is None
        assert acct.re_payment == '^(payment|thank you)'
        assert acct.re_late_fee == '^Late Fee'
        assert acct.re_other_fee == '^re-other-fee'
        stmt = testdb.query(OFXStatement).get(1)
        assert stmt.account_id == 1
        assert stmt.filename == '/stmt/BankOne/0'
        txn = OFXTransaction(
            account=acct,
            statement=stmt,
            fitid='BankOne-9-1',
            trans_type='Credit',
            date_posted=stmt.ledger_bal_as_of,
            amount=Decimal('1234.56'),
            name='BankOne-9-1'
        )
        testdb.add(txn)
        testdb.commit()
        assert txn.is_payment is False
        assert txn.is_late_fee is False
        assert txn.is_interest_charge is False
        assert txn.is_other_fee is False
        assert txn.is_interest_payment is False
        txn = OFXTransaction(
            account=acct,
            statement=stmt,
            fitid='BankOne-9-2',
            trans_type='Credit',
            date_posted=stmt.ledger_bal_as_of,
            amount=Decimal('1234.56'),
            name='re-other-fee BankOne-9-2'
        )
        testdb.add(txn)
        testdb.commit()
        assert txn.is_payment is False
        assert txn.is_late_fee is False
        assert txn.is_interest_charge is False
        assert txn.is_other_fee is True
        assert txn.is_interest_payment is False
        txn = OFXTransaction(
            account=acct,
            statement=stmt,
            fitid='BankOne-9-3',
            trans_type='Credit',
            date_posted=stmt.ledger_bal_as_of,
            amount=Decimal('1234.56'),
            name='Late Fee BankOne-9-3'
        )
        testdb.add(txn)
        testdb.commit()
        assert txn.is_payment is False
        assert txn.is_late_fee is True
        assert txn.is_interest_charge is False
        assert txn.is_other_fee is False
        assert txn.is_interest_payment is False
        txn = OFXTransaction(
            account=acct,
            statement=stmt,
            fitid='BankOne-9-4',
            trans_type='Credit',
            date_posted=stmt.ledger_bal_as_of,
            amount=Decimal('1234.56'),
            name='payment BankOne-9-4'
        )
        testdb.add(txn)
        testdb.commit()
        assert txn.is_payment is True
        assert txn.is_late_fee is False
        assert txn.is_interest_charge is False
        assert txn.is_other_fee is False
        assert txn.is_interest_payment is False
        txn = OFXTransaction(
            account=acct,
            statement=stmt,
            fitid='BankOne-9-5',
            trans_type='Credit',
            date_posted=stmt.ledger_bal_as_of,
            amount=Decimal('1234.56'),
            name='Thank You BankOne-9-5'
        )
        testdb.add(txn)
        testdb.commit()
        assert txn.is_payment is True
        assert txn.is_late_fee is False
        assert txn.is_interest_charge is False
        assert txn.is_other_fee is False
        assert txn.is_interest_payment is False
        txn = OFXTransaction(
            account=acct,
            statement=stmt,
            fitid='BankOne-9-6',
            trans_type='Credit',
            date_posted=stmt.ledger_bal_as_of,
            amount=Decimal('1234.56'),
            name='interest-paid'
        )
        testdb.add(txn)
        testdb.commit()
        assert txn.is_payment is False
        assert txn.is_late_fee is False
        assert txn.is_interest_charge is False
        assert txn.is_other_fee is False
        assert txn.is_interest_payment is False

    def test_1_account_re_change_triggers_update_is_fields(self, testdb):
        """
        Test for
        :py:func:`~.db_event_handlers.handle_account_re_change`
        """
        acct = testdb.query(Account).get(1)
        acct.re_interest_paid = None
        testdb.commit()
        assert acct.re_interest_charge == '^interest-charge'
        assert acct.re_interest_paid is None
        assert acct.re_payment == '^(payment|thank you)'
        assert acct.re_late_fee == '^Late Fee'
        assert acct.re_other_fee == '^re-other-fee'
        stmt = testdb.query(OFXStatement).get(1)
        assert stmt.account_id == 1
        assert stmt.filename == '/stmt/BankOne/0'
        txn1 = testdb.query(OFXTransaction).get((1, 'BankOne-9-1'))
        assert txn1.name == 'BankOne-9-1'
        assert txn1.is_payment is False
        assert txn1.is_late_fee is False
        assert txn1.is_interest_charge is False
        assert txn1.is_other_fee is False
        assert txn1.is_interest_payment is False
        txn2 = testdb.query(OFXTransaction).get((1, 'BankOne-9-2'))
        assert txn2.name == 're-other-fee BankOne-9-2'
        assert txn2.is_payment is False
        assert txn2.is_late_fee is False
        assert txn2.is_interest_charge is False
        assert txn2.is_other_fee is True
        assert txn2.is_interest_payment is False
        txn3 = testdb.query(OFXTransaction).get((1, 'BankOne-9-3'))
        assert txn3.name == 'Late Fee BankOne-9-3'
        assert txn3.is_payment is False
        assert txn3.is_late_fee is True
        assert txn3.is_interest_charge is False
        assert txn3.is_other_fee is False
        assert txn3.is_interest_payment is False
        # change the account
        acct.re_interest_charge = '^BankOne-9-1$'
        acct.re_payment = '^Late Fee'
        acct.re_late_fee = '^foobarbaz'
        testdb.commit()
        # re-confirm
        txn1 = testdb.query(OFXTransaction).get((1, 'BankOne-9-1'))
        assert txn1.name == 'BankOne-9-1'
        assert txn1.is_payment is False
        assert txn1.is_late_fee is False
        assert txn1.is_interest_charge is True
        assert txn1.is_other_fee is False
        assert txn1.is_interest_payment is False
        txn2 = testdb.query(OFXTransaction).get((1, 'BankOne-9-2'))
        assert txn2.name == 're-other-fee BankOne-9-2'
        assert txn2.is_payment is False
        assert txn2.is_late_fee is False
        assert txn2.is_interest_charge is False
        assert txn2.is_other_fee is True
        assert txn2.is_interest_payment is False
        txn3 = testdb.query(OFXTransaction).get((1, 'BankOne-9-3'))
        assert txn3.name == 'Late Fee BankOne-9-3'
        assert txn3.is_payment is True
        assert txn3.is_late_fee is False
        assert txn3.is_interest_charge is False
        assert txn3.is_other_fee is False
        assert txn3.is_interest_payment is False
