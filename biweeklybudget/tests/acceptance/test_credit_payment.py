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
from datetime import date, timedelta
from decimal import Decimal

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.credit_payment import (
    CreditPaymentAttribution, CREDIT_PAYMENT_MAX_PERIODS
)
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
        # The earliest payment designated toward a card anchors its charge
        # window: charges are counted from the pay period *after* the one
        # holding it (GitHub issue #358). This one sits in the first period,
        # 2017-04-07 .. 2017-04-20, so the window begins 2017-04-21 -- before
        # both of the fixture's charges, leaving the assertions in this test
        # and in tests 07, 09 and 10 measuring exactly what they measured
        # before the window became per-account. Without it the window would
        # begin 2017-05-19, past the end of the fixture's data, and those
        # tests would all collapse to asserting zeroes.
        testdb.add(Transaction(
            date=date(2017, 4, 10),
            budget_amounts={budget: Decimal('900.00')},
            description='Pre-feature payment',
            account=bank,
            credit_payment_acct=card
        ))
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


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestCreditPaymentWindow(AcceptanceHelper):
    """
    The per-account charge window and the display cap; GitHub issue #358.

    Pay periods start 2017-01-06, so they run:

      * P0  2017-01-06 .. 2017-01-19    * P6   2017-03-31 .. 2017-04-13
      * P1  2017-01-20 .. 2017-02-02    * P7   2017-04-14 .. 2017-04-27
      * P2  2017-02-03 .. 2017-02-16    * P8   2017-04-28 .. 2017-05-11
      * P3  2017-02-17 .. 2017-03-02    * P9   2017-05-12 .. 2017-05-25
      * P4  2017-03-03 .. 2017-03-16    * P10  2017-05-26 .. 2017-06-08
      * P5  2017-03-17 .. 2017-03-30    * P11  2017-06-09 .. 2017-06-22

    The card carries 100.00 of charges in each of those twelve periods, which
    is the shape the feature exists for: far more history than one payment
    could settle, and twice as many periods as the display cap. "Today" and
    the payment date are 2017-06-21, in P11.

    The tests run in order and build on each other: the first few see a card
    with no payment ever designated toward it, then one is recorded, and the
    window narrows.
    """

    def test_00_clean_db(self, dump_file_path):
        restore_mysqldump(dump_file_path, get_db_engine(), with_data=False)

    def test_01_add_data(self, testdb):
        testdb.add(Account(
            description='Bank Account', name='BankOne',
            acct_type=AcctType.Bank
        ))
        testdb.add(Account(
            description='Credit Card', name='HistoryCard',
            acct_type=AcctType.Credit, credit_limit=Decimal('5000.00')
        ))
        testdb.add(Budget(
            name='1Periodic', is_periodic=True, description='1Periodic',
            starting_balance=Decimal('50000.00')
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    def test_02_add_charges(self, testdb):
        card = testdb.query(Account).get(2)
        budget = testdb.query(Budget).get(1)
        # 100.00 on the tenth day of each of the twelve periods beginning
        # 2017-01-06; period N starts 2017-01-06 plus 14N days.
        for n in range(0, 12):
            testdb.add(Transaction(
                date=date(2017, 1, 6) + timedelta(days=(14 * n) + 9),
                budget_amounts={budget: Decimal('100.00')},
                description='Charges for period %d' % n,
                account=card
            ))
        testdb.flush()
        testdb.commit()

    def _attr(self, testdb, amount, pmt_date=date(2017, 6, 21), **kwargs):
        return CreditPaymentAttribution(
            testdb, testdb.query(Account).get(2), Decimal(amount),
            pmt_date, **kwargs
        )

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_03_no_designated_payment_uses_configured_date(
        self, m_dtnow, testdb
    ):
        """FR-004: an account that has never had a payment designated toward
        it behaves exactly as it did before issue #358 -- the configured
        CREDIT_PAYMENT_BEGIN_DATE is the window, and the whole of the card's
        recorded history counts as unpaid. This is the one noisy panel an
        upgrading install still sees, once per card."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        a = self._attr(testdb, '100.00')
        assert a.begin_date == date(2017, 1, 1)
        assert a.configured_begin_date == date(2017, 1, 1)
        # all twelve periods' charges
        assert a.total_unpaid == Decimal('1200.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_04_cap_and_rollup(self, m_dtnow, testdb):
        """FR-010 to FR-014: the twelve-period window is capped at six rows,
        the other six collapsing into one summary carrying their count, date
        range and summed amounts. The cap is a display concern only: the
        payment is still attributed oldest-first across the whole window, and
        the totals are computed over all twelve periods."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        a = self._attr(testdb, '250.00')
        assert a.begin_date == date(2017, 1, 1)
        # the six most recent periods, P6 .. P11, still oldest-first
        assert len(a.periods) == CREDIT_PAYMENT_MAX_PERIODS
        assert [p['start_date'] for p in a.periods] == [
            date(2017, 3, 31), date(2017, 4, 14), date(2017, 4, 28),
            date(2017, 5, 12), date(2017, 5, 26), date(2017, 6, 9)
        ]
        # P0 .. P5, and the whole 250.00 landed on them: attribution is
        # oldest-first, so the rollup must state where the payment went
        assert a.rollup == {
            'count': 6,
            'start_date': date(2017, 1, 6),
            'end_date': date(2017, 3, 30),
            'outstanding': Decimal('600.00'),
            'attributed': Decimal('250.00')
        }
        assert a.total_unpaid == Decimal('1200.00')
        assert a.total_attributed == Decimal('250.00')
        assert a.excess == Decimal('0.0')
        # FR-014: the rendered rows reconcile to the totals line
        assert sum(
            [p['attributed'] for p in a.periods], Decimal('0.0')
        ) + a.rollup['attributed'] == a.total_attributed
        assert sum(
            [p['outstanding'] for p in a.periods], Decimal('0.0')
        ) + a.rollup['outstanding'] == a.total_unpaid

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_05_add_anchor_payment(self, m_dtnow, testdb):
        """Record the first payment ever designated toward the card, dated
        2017-04-20, which falls in P7 (2017-04-14 .. 2017-04-27)."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        bank = testdb.query(Account).get(1)
        card = testdb.query(Account).get(2)
        budget = testdb.query(Budget).get(1)
        testdb.add(Transaction(
            date=date(2017, 4, 20),
            budget_amounts={budget: Decimal('750.00')},
            description='First recorded payment',
            account=bank,
            credit_payment_acct=card
        ))
        testdb.flush()
        testdb.commit()

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_06_window_starts_after_anchor_period(self, m_dtnow, testdb):
        """FR-002 / SC-001: the window now begins at the start of the period
        *after* the one holding that first payment -- 2017-04-28 -- so the
        panel lists four periods instead of twelve, and needs no rollup."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        a = self._attr(testdb, '100.00')
        assert a.begin_date == date(2017, 4, 28)
        assert a.configured_begin_date == date(2017, 1, 1)
        assert [p['start_date'] for p in a.periods] == [
            date(2017, 4, 28), date(2017, 5, 12),
            date(2017, 5, 26), date(2017, 6, 9)
        ]
        assert a.rollup is None

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_07_anchor_is_not_also_a_prior_payment(self, m_dtnow, testdb):
        """FR-005a -- the invariant the boundary rule exists for. The
        anchoring payment of 750.00 falls outside the window it defines, so it
        is not ALSO subtracted from the charges inside that window. Four
        periods of 100.00 lie in the window, so 400.00 is unpaid; were the
        anchor subtracted as well it would wipe all four out and the unpaid
        total would be zero."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        a = self._attr(testdb, '400.00')
        assert a.total_unpaid == Decimal('400.00')
        assert a.total_attributed == Decimal('400.00')
        assert a.excess == Decimal('0.0')
        assert a.warnings == []

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    @patch('%s.settings.CREDIT_PAYMENT_BEGIN_DATE' % pbm, date(2017, 5, 26))
    def test_08_configured_date_is_a_floor(self, m_dtnow, testdb):
        """FR-007 / spec Example D: a configured begin date later than the
        derived bound wins. It remains the operator's manual floor and is
        never undercut."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        a = self._attr(testdb, '100.00')
        assert a.begin_date == date(2017, 5, 26)
        assert a.configured_begin_date == date(2017, 5, 26)
        # only P10 and P11 remain
        assert a.total_unpaid == Decimal('200.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_09_editing_the_anchor_shows_what_entering_it_showed(
        self, m_dtnow, testdb
    ):
        """FR-005: reopening a payment for editing must show the panel that
        entering it showed. A payment being entered is not yet in the database
        and cannot anchor anything, so the same payment reopened must not
        anchor anything either -- it is excluded from deriving the window as
        well as from the prior-payments sum.

        Reopening the anchor at its own date is the case that matters: were it
        left to anchor, the derived bound would be 2017-04-28, *after* its own
        2017-04-20 date, so the window would be empty and the panel would warn
        that the payment exceeds $0.00 of unpaid charges -- the exact opposite
        of showing what entering it showed."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        anchor = testdb.query(Transaction).filter(
            Transaction.description.__eq__('First recorded payment')
        ).one()
        a = self._attr(
            testdb, '750.00', pmt_date=date(2017, 4, 20),
            exclude_txn_id=anchor.id
        )
        assert a.begin_date == date(2017, 1, 1)
        # P0 .. P6, the seven periods whose charges are dated on or before
        # 2017-04-20. Under the bug this was 0.00.
        assert a.total_unpaid == Decimal('700.00')
        assert a.total_attributed == Decimal('700.00')
        assert a.excess == Decimal('50.00')
        assert len(a.warnings) == 1
        assert '$700.00 of unpaid charges' in a.warnings[0]

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_09a_editing_the_anchor_from_a_later_date(self, m_dtnow, testdb):
        """The same rule seen from the other side: excluding the anchor leaves
        nothing to derive a bound from, so the configured floor stands. A
        *different* payment being edited would leave the anchor in place and
        the window unchanged -- see test_06."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        anchor = testdb.query(Transaction).filter(
            Transaction.description.__eq__('First recorded payment')
        ).one()
        a = self._attr(testdb, '100.00', exclude_txn_id=anchor.id)
        assert a.begin_date == date(2017, 1, 1)
        assert a.total_unpaid == Decimal('1200.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_10_back_dated_payment_uses_configured_date(
        self, m_dtnow, testdb
    ):
        """FR-003 / spec Example E: only payments dated on or before the one
        being evaluated take part in deriving the bound, so a payment
        back-dated before every designated payment gets the configured begin
        date rather than being measured against an empty window."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        a = self._attr(testdb, '100.00', pmt_date=date(2017, 3, 1))
        assert a.begin_date == date(2017, 1, 1)
        # P0 .. P3, whose charges are dated on or before 2017-03-01
        assert a.total_unpaid == Decimal('400.00')

    @patch('%s.settings.PAY_PERIOD_START_DATE' % ppm, date(2017, 1, 6))
    @patch('%s.dtnow' % pbm)
    def test_11_payment_inside_anchor_period_empties_window(
        self, m_dtnow, testdb
    ):
        """FR-005b: a second payment dated inside the anchoring payment's own
        pay period leaves the derived bound after the payment date, so the
        window is empty. The configured date is deliberately NOT reinstated as
        a fallback -- doing so would swing the panel back to the whole of
        recorded history."""
        m_dtnow.return_value.date.return_value = date(2017, 6, 21)
        a = self._attr(testdb, '100.00', pmt_date=date(2017, 4, 25))
        assert a.begin_date == date(2017, 4, 28)
        assert a.periods == []
        assert a.rollup is None
        assert a.total_unpaid == Decimal('0.0')
        assert a.total_attributed == Decimal('0.0')
        assert a.excess == Decimal('100.00')
