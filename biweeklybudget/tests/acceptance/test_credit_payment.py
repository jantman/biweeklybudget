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
from datetime import date
from decimal import Decimal

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.credit_payment import CreditPaymentAttribution
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.tests.conftest import get_db_engine
from biweeklybudget.tests.sqlhelpers import restore_mysqldump

import sys
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import patch
else:
    from unittest.mock import patch

pbm = 'biweeklybudget.credit_payment'
ppm = 'biweeklybudget.biweeklypayperiod'


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestCreditPaymentAttribution(AcceptanceHelper):
    """
    The payment attribution and over-payment warning; GitHub issue #210,
    User Story 3.

    Pay periods start 2017-04-07, so:

      * 2017-04-07 .. 2017-04-20  (closed)
      * 2017-04-21 .. 2017-05-04  (closed)
      * 2017-05-05 .. 2017-05-18  ("today" is 2017-05-10, so this is open)

    The scenario the spec pins: 400.00 of unpaid charges in a closed period and
    150.00 in the currently-open one.
    """

    def test_00_clean_db(self, dump_file_path):
        restore_mysqldump(dump_file_path, get_db_engine(), with_data=False)

    def test_01_add_data(self, testdb):
        testdb.add(Account(
            description='Bank Account', name='BankOne',
            acct_type=AcctType.Bank
        ))
        testdb.add(Account(
            description='Credit Card', name='CreditOne',
            acct_type=AcctType.Credit, credit_limit=Decimal('2000.00')
        ))
        testdb.add(Budget(
            name='1Periodic', is_periodic=True, description='1Periodic',
            starting_balance=Decimal('5000.00')
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    def test_02_add_charges(self, testdb):
        card = testdb.query(Account).get(2)
        budget = testdb.query(Budget).get(1)
        # 400.00 in the closed period 2017-04-21 .. 2017-05-04
        testdb.add(Transaction(
            date=date(2017, 4, 25),
            budget_amounts={budget: Decimal('400.00')},
            description='Closed period charges',
            account=card
        ))
        # 150.00 in the open period 2017-05-05 .. 2017-05-18
        testdb.add(Transaction(
            date=date(2017, 5, 8),
            budget_amounts={budget: Decimal('150.00')},
            description='Open period charges',
            account=card
        ))
        testdb.flush()
        testdb.commit()

    def _attr(self, testdb, amount, **kwargs):
        return CreditPaymentAttribution(
            testdb, testdb.query(Account).get(2), Decimal(amount),
            date(2017, 5, 10), **kwargs
        )

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_03_payment_of_400(self, m_dtnow, testdb):
        """Spec US3 scenario 1: the whole 400.00 settles closed-period
        charges, nothing applies to the open period, and there is no
        warning."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        a = self._attr(testdb, '400.00')
        assert a.total_unpaid == Decimal('550.00')
        assert a.total_attributed == Decimal('400.00')
        assert a.excess == Decimal('0.0')
        assert a.warnings == []
        assert [
            (p['start_date'], p['is_closed'], p['attributed'])
            for p in a.periods
        ] == [
            (date(2017, 4, 21), True, Decimal('400.00')),
            (date(2017, 5, 5), False, Decimal('0.0'))
        ]

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_04_payment_of_500(self, m_dtnow, testdb):
        """Spec US3 scenario 2: 400.00 settles the closed period, 100.00
        applies to the open one, and there is still no warning."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        a = self._attr(testdb, '500.00')
        assert a.total_attributed == Decimal('500.00')
        assert a.excess == Decimal('0.0')
        assert a.warnings == []
        assert [
            (p['start_date'], p['is_closed'], p['attributed'])
            for p in a.periods
        ] == [
            (date(2017, 4, 21), True, Decimal('400.00')),
            (date(2017, 5, 5), False, Decimal('100.00'))
        ]

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_05_payment_of_600_warns(self, m_dtnow, testdb):
        """Spec US3 scenario 3 / SC-004: 600.00 exceeds the 550.00 of recorded
        unpaid charges by 50.00, and says so."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        a = self._attr(testdb, '600.00')
        assert a.total_unpaid == Decimal('550.00')
        assert a.total_attributed == Decimal('550.00')
        assert a.excess == Decimal('50.00')
        assert len(a.warnings) == 1
        assert a.warnings[0] == (
            'This payment exceeds the $550.00 of unpaid charges recorded for '
            'CreditOne by $50.00. This usually means charges are missing from '
            'your records, or were recorded against the wrong account.'
        )

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_06_prior_payment_reduces_unpaid(self, m_dtnow, testdb):
        """A payment already recorded toward the card is subtracted from the
        unpaid total, so the next payment is measured against what is left."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        bank = testdb.query(Account).get(1)
        card = testdb.query(Account).get(2)
        budget = testdb.query(Budget).get(1)
        testdb.add(Transaction(
            date=date(2017, 5, 6),
            budget_amounts={budget: Decimal('400.00')},
            description='Earlier payment',
            account=bank,
            credit_payment_acct=card
        ))
        testdb.flush()
        testdb.commit()
        a = self._attr(testdb, '150.00')
        # The 400.00 closed-period charges are already settled; only the
        # 150.00 of open-period charges remain.
        assert a.total_unpaid == Decimal('150.00')
        assert a.total_attributed == Decimal('150.00')
        assert a.excess == Decimal('0.0')
        assert a.warnings == []
        assert [
            (p['start_date'], p['attributed']) for p in a.periods
        ] == [(date(2017, 5, 5), Decimal('150.00'))]

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_07_editing_excludes_self(self, m_dtnow, testdb):
        """Spec US3 scenario 6 / FR-019: reopening a saved payment must not
        count that payment against itself. Without exclude_txn_id the 400.00
        earlier payment is treated as already settling the closed period."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        payment = testdb.query(Transaction).filter(
            Transaction.description.__eq__('Earlier payment')
        ).one()
        a = self._attr(testdb, '400.00', exclude_txn_id=payment.id)
        assert a.total_unpaid == Decimal('550.00')
        assert a.total_attributed == Decimal('400.00')
        assert a.excess == Decimal('0.0')
        assert a.warnings == []

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_08_pays_itself_warning(self, m_dtnow, testdb):
        """Spec FR-022."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        a = self._attr(testdb, '100.00', payer_account_id=2)
        assert a.pays_itself is True
        assert a.warnings == [
            'This transaction is recorded against CreditOne and is also '
            'marked as a payment toward CreditOne. A payment should be '
            'recorded against the account the money came from.'
        ]
        a = self._attr(testdb, '100.00', payer_account_id=1)
        assert a.pays_itself is False
        assert a.warnings == []

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_09_charges_after_payment_date_not_attributed(
        self, m_dtnow, testdb
    ):
        """A payment cannot settle a charge that had not been made when it was
        paid. Attributing as of 2017-05-07 sees only the 400.00 of closed
        period charges, not the 150.00 dated 2017-05-08."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        payment = testdb.query(Transaction).filter(
            Transaction.description.__eq__('Earlier payment')
        ).one()
        a = CreditPaymentAttribution(
            testdb, testdb.query(Account).get(2), Decimal('550.00'),
            date(2017, 5, 7), exclude_txn_id=payment.id
        )
        assert a.total_unpaid == Decimal('400.00')
        assert a.total_attributed == Decimal('400.00')
        assert a.excess == Decimal('150.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    @patch('%s.settings.CREDIT_PAYMENT_BEGIN_DATE' % pbm, date(2017, 5, 1))
    def test_10_charges_before_begin_date_not_counted(self, m_dtnow, testdb):
        """Spec FR-018: charges before the tracking start date are not counted
        as unpaid, so a payment settling them trips the warning."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        payment = testdb.query(Transaction).filter(
            Transaction.description.__eq__('Earlier payment')
        ).one()
        a = self._attr(testdb, '550.00', exclude_txn_id=payment.id)
        # Only the 150.00 dated 2017-05-08 falls inside the window.
        assert a.total_unpaid == Decimal('150.00')
        assert a.excess == Decimal('400.00')
        assert len(a.warnings) == 1
        assert '$150.00 of unpaid charges' in a.warnings[0]


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestCreditPaymentAttributionEdgeCases(AcceptanceHelper):

    def test_00_clean_db(self, dump_file_path):
        restore_mysqldump(dump_file_path, get_db_engine(), with_data=False)

    def test_01_add_data(self, testdb):
        testdb.add(Account(
            description='Bank Account', name='BankOne',
            acct_type=AcctType.Bank
        ))
        testdb.add(Account(
            description='Credit Card', name='EmptyCard',
            acct_type=AcctType.Credit, credit_limit=Decimal('1000.00')
        ))
        testdb.add(Budget(
            name='1Periodic', is_periodic=True, description='1Periodic',
            starting_balance=Decimal('5000.00')
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_02_card_with_no_charges(self, m_dtnow, testdb):
        """Spec edge case: any payment toward a card with no recorded charges
        exceeds its recorded unpaid charges, and the breakdown is empty."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        a = CreditPaymentAttribution(
            testdb, testdb.query(Account).get(2), Decimal('100.00'),
            date(2017, 5, 10)
        )
        assert a.periods == []
        assert a.total_unpaid == Decimal('0.0')
        assert a.total_attributed == Decimal('0.0')
        assert a.excess == Decimal('100.00')
        assert len(a.warnings) == 1
        assert '$0.00 of unpaid charges' in a.warnings[0]

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 4, 7))
    @patch('%s.dtnow' % pbm)
    def test_03_negative_amount(self, m_dtnow, testdb):
        """Spec edge case: a negative amount is a refund flowing back from the
        card. It settles nothing and does not warn about over-payment."""
        m_dtnow.return_value.date.return_value = date(2017, 5, 10)
        a = CreditPaymentAttribution(
            testdb, testdb.query(Account).get(2), Decimal('-50.00'),
            date(2017, 5, 10)
        )
        assert a.total_attributed == Decimal('0.0')
        assert a.excess == Decimal('-50.00')
        assert a.warnings == []
