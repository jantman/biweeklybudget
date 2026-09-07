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

from decimal import Decimal

from biweeklybudget.credit_payment import CreditPaymentAttribution


class TestConsume(object):
    """
    Tests for the allocation step of
    :py:class:`~.CreditPaymentAttribution`. Charges are settled oldest first;
    everything else in the class is built on this.
    """

    def _periods(self, *amounts):
        return [
            {'outstanding': Decimal(a), 'attributed': Decimal('0.0')}
            for a in amounts
        ]

    def test_exact_single_period(self):
        p = self._periods('400.00')
        rem = CreditPaymentAttribution._consume(
            p, Decimal('400.00'), 'attributed'
        )
        assert rem == Decimal('0.0')
        assert p[0]['attributed'] == Decimal('400.00')
        assert p[0]['outstanding'] == Decimal('0.0')

    def test_oldest_first(self):
        """500.00 against 400.00 of closed-period charges and 150.00 of open
        ones fills the closed period first."""
        p = self._periods('400.00', '150.00')
        rem = CreditPaymentAttribution._consume(
            p, Decimal('500.00'), 'attributed'
        )
        assert rem == Decimal('0.0')
        assert p[0]['attributed'] == Decimal('400.00')
        assert p[1]['attributed'] == Decimal('100.00')
        assert p[1]['outstanding'] == Decimal('50.00')

    def test_excess_is_returned(self):
        p = self._periods('400.00', '150.00')
        rem = CreditPaymentAttribution._consume(
            p, Decimal('600.00'), 'attributed'
        )
        assert rem == Decimal('50.00')
        assert p[0]['attributed'] == Decimal('400.00')
        assert p[1]['attributed'] == Decimal('150.00')

    def test_partial_first_period_only(self):
        p = self._periods('400.00', '150.00')
        rem = CreditPaymentAttribution._consume(
            p, Decimal('250.00'), 'attributed'
        )
        assert rem == Decimal('0.0')
        assert p[0]['attributed'] == Decimal('250.00')
        assert p[0]['outstanding'] == Decimal('150.00')
        assert p[1]['attributed'] == Decimal('0.0')

    def test_three_periods(self):
        """A payment covering three closed periods at once -- the missed-cycle
        case from GitHub issue #210."""
        p = self._periods('100.00', '200.00', '300.00')
        rem = CreditPaymentAttribution._consume(
            p, Decimal('600.00'), 'attributed'
        )
        assert rem == Decimal('0.0')
        assert [x['attributed'] for x in p] == [
            Decimal('100.00'), Decimal('200.00'), Decimal('300.00')
        ]

    def test_skips_already_settled_periods(self):
        p = self._periods('0.0', '150.00')
        rem = CreditPaymentAttribution._consume(
            p, Decimal('50.00'), 'attributed'
        )
        assert rem == Decimal('0.0')
        assert p[0]['attributed'] == Decimal('0.0')
        assert p[1]['attributed'] == Decimal('50.00')

    def test_none_key_only_reduces(self):
        """Prior payments are consumed with key=None: they reduce what is
        outstanding without being reported as attributed to this payment."""
        p = self._periods('400.00')
        rem = CreditPaymentAttribution._consume(p, Decimal('150.00'), None)
        assert rem == Decimal('0.0')
        assert p[0]['outstanding'] == Decimal('250.00')
        assert p[0]['attributed'] == Decimal('0.0')

    def test_zero_amount(self):
        p = self._periods('400.00')
        rem = CreditPaymentAttribution._consume(
            p, Decimal('0.0'), 'attributed'
        )
        assert rem == Decimal('0.0')
        assert p[0]['outstanding'] == Decimal('400.00')

    def test_negative_amount_is_not_applied(self):
        """A refund flowing back from the card settles nothing; it is carried
        through as excess rather than being allocated backwards."""
        p = self._periods('400.00')
        rem = CreditPaymentAttribution._consume(
            p, Decimal('-50.00'), 'attributed'
        )
        assert rem == Decimal('-50.00')
        assert p[0]['outstanding'] == Decimal('400.00')
