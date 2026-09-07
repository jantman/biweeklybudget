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


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestStandingBudgetExcludedTransactions(AcceptanceHelper):
    """
    Standing budget balances and transactions excluded from budget arithmetic;
    GitHub issues #210 and #319.

    Standing budget balances are persisted state maintained by the handlers in
    ``db_event_handlers``, not computed on read like periodic budget totals.
    So an excluded transaction has to be skipped here as well, or a credit card
    payment recorded against a standing budget would debit that budget --
    exactly the double-count the feature removes -- and stay wrong.

    Sample data: Budget 5 is "Standing2", a standing budget starting at
    9482.29. Account 3 is CreditOne, a credit account.
    """

    def test_0_verify_db(self, testdb):
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.current_balance == Decimal('9482.29')

    def test_1_credit_payment_does_not_debit_standing_budget(self, testdb):
        testdb.add(Transaction(
            budget_amounts={testdb.query(Budget).get(5): Decimal('500.00')},
            description='CardPaymentStanding',
            account=testdb.query(Account).get(1),
            credit_payment_acct=testdb.query(Account).get(3)
        ))
        testdb.flush()
        testdb.commit()

    def test_2_verify_balance_unchanged(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9482.29')

    def test_3_no_budget_impact_does_not_debit_standing_budget(self, testdb):
        testdb.add(Transaction(
            budget_amounts={testdb.query(Budget).get(5): Decimal('40.00')},
            description='NoImpactStanding',
            account=testdb.query(Account).get(1),
            no_budget_impact=True
        ))
        testdb.flush()
        testdb.commit()

    def test_4_verify_balance_still_unchanged(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9482.29')

    def test_5_ordinary_transaction_still_debits(self, testdb):
        """The guard must not break the ordinary case."""
        testdb.add(Transaction(
            budget_amounts={testdb.query(Budget).get(5): Decimal('100.00')},
            description='OrdinaryStanding',
            account=testdb.query(Account).get(1)
        ))
        testdb.flush()
        testdb.commit()

    def test_6_verify_ordinary_debited(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9382.29')

    def test_7_clearing_designation_debits_standing_budget(self, testdb):
        """Spec FR-014, for a standing budget: a transaction that stops being
        a credit card payment must debit the budget it is allocated to."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CardPaymentStanding')
        ).one()
        t.credit_payment_acct_id = None
        testdb.flush()
        testdb.commit()

    def test_8_verify_debited_on_clear(self, testdb):
        # 9382.29 - 500.00
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('8882.29')

    def test_9_resetting_designation_refunds(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CardPaymentStanding')
        ).one()
        t.credit_payment_acct_id = 3
        testdb.flush()
        testdb.commit()

    def test_10_verify_refunded(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9382.29')

    def test_11_toggling_no_budget_impact_flag(self, testdb):
        """The same correction applies to the general flag."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('OrdinaryStanding')
        ).one()
        t.no_budget_impact = True
        testdb.flush()
        testdb.commit()

    def test_12_verify_refunded_on_flag(self, testdb):
        # the 100.00 debit from test_5 is refunded
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9482.29')

    def test_13_deleting_excluded_transaction_does_not_credit(self, testdb):
        """Deleting an excluded transaction must not credit the standing
        budget, because it never debited it."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('NoImpactStanding')
        ).one()
        for bt in list(t.budget_transactions):
            testdb.delete(bt)
        testdb.delete(t)
        testdb.flush()
        testdb.commit()

    def test_14_verify_balance_after_delete(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9482.29')

    def test_15_changing_amount_of_excluded_transaction(self, testdb):
        """Changing the amount of an excluded transaction must not move the
        standing budget balance either."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CardPaymentStanding')
        ).one()
        t.set_budget_amounts({
            testdb.query(Budget).get(5): Decimal('750.00')
        })
        testdb.flush()
        testdb.commit()

    def test_16_verify_balance_after_amount_change(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9482.29')


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestStandingBudgetExclusionCombinedChanges(AcceptanceHelper):
    """
    Standing budget corrections when an exclusion change is combined with
    another change in the same save. Both cases were found in review of
    PR #329; GitHub issue #210.

    The Add/Edit Transaction form assigns ``no_budget_impact`` and
    ``credit_payment_acct_id`` on every submit and then calls
    ``set_budget_amounts()``, so a single save can change both exclusion fields
    at once, and can change the amount at the same time. Each of those
    interacts with ``handle_budget_trans_amount_change``, which runs
    synchronously on assignment rather than at flush.

    Budget 5 is "Standing2", starting at 9482.29. Account 3 is CreditOne.
    """

    def test_00_baseline(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9482.29')

    def test_01_add_ordinary(self, testdb):
        testdb.add(Transaction(
            budget_amounts={testdb.query(Budget).get(5): Decimal('100.00')},
            description='CombinedA',
            account=testdb.query(Account).get(1)
        ))
        testdb.flush()
        testdb.commit()

    def test_02_ordinary_was_debited(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9382.29')

    def test_03_both_fields_change_becoming_excluded(self, testdb):
        """Both exclusion fields change in one save. Reconstructing the prior
        state from one field's old value paired with the other's already
        mutated value gives the wrong answer; both old values must be resolved
        before either is evaluated."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CombinedA')
        ).one()
        t.no_budget_impact = True
        t.credit_payment_acct_id = 3
        testdb.flush()
        testdb.commit()

    def test_04_verify_refunded_once(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9482.29')

    def test_05_both_fields_change_becoming_ordinary(self, testdb):
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CombinedA')
        ).one()
        t.no_budget_impact = False
        t.credit_payment_acct_id = None
        testdb.flush()
        testdb.commit()

    def test_06_verify_debited_once(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9382.29')

    def test_07_becoming_excluded_while_amount_changes(self, testdb):
        """The correction must use the amount that was actually debited
        (100.00), not the new amount (150.00). The amount-change handler skips
        here, because by the time it fires the transaction is already
        excluded."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CombinedA')
        ).one()
        t.no_budget_impact = True
        t.set_budget_amounts({
            testdb.query(Budget).get(5): Decimal('150.00')
        })
        testdb.flush()
        testdb.commit()

    def test_08_verify_refunded_old_amount(self, testdb):
        # 9382.29 + 100.00 debited, not + 150.00
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9482.29')

    def test_09_becoming_ordinary_while_amount_changes(self, testdb):
        """Here the amount-change handler does *not* skip, so it applies the
        150 -> 200 delta itself; this handler must then debit only the old
        amount or the delta is counted twice."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CombinedA')
        ).one()
        t.no_budget_impact = False
        t.set_budget_amounts({
            testdb.query(Budget).get(5): Decimal('200.00')
        })
        testdb.flush()
        testdb.commit()

    def test_10_verify_debited_new_amount_once(self, testdb):
        # 9482.29 - 200.00, reached as -50 (delta) then -150 (old amount)
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9282.29')

    def test_11_add_excluded_transaction(self, testdb):
        testdb.add(Transaction(
            budget_amounts={testdb.query(Budget).get(5): Decimal('50.00')},
            description='CombinedB',
            account=testdb.query(Account).get(1),
            no_budget_impact=True
        ))
        testdb.flush()
        testdb.commit()

    def test_12_excluded_not_debited(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9282.29')

    def test_13_both_fields_change_still_excluded(self, testdb):
        """Both fields change but the transaction is excluded before and
        after, so nothing should move. The overwrite bug made this look like a
        transition and applied a phantom refund."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CombinedB')
        ).one()
        t.no_budget_impact = False
        t.credit_payment_acct_id = 3
        testdb.flush()
        testdb.commit()

    def test_14_verify_no_phantom_refund(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9282.29')

    def test_15_resave_with_no_real_change(self, testdb):
        """The form assigns both fields on every submit, so they always have
        attribute history even when the value is unchanged. That must not be
        treated as a transition."""
        t = testdb.query(Transaction).filter(
            Transaction.description.__eq__('CombinedB')
        ).one()
        t.no_budget_impact = False
        t.credit_payment_acct_id = 3
        t.notes = 'touched'
        testdb.flush()
        testdb.commit()

    def test_16_verify_unchanged_on_resave(self, testdb):
        assert testdb.query(Budget).get(5).current_balance == \
            Decimal('9282.29')
