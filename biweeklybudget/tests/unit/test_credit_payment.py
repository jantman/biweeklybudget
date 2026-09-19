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

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from biweeklybudget.credit_payment import (
    CreditPaymentAttribution, CREDIT_PAYMENT_MAX_PERIODS
)

pbm = 'biweeklybudget.credit_payment'


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


class TestEffectiveBeginDate(object):
    """
    Tests for the per-account lower bound on the charge window; GitHub issue
    #358. The bound is the later of the configured begin date and the start of
    the pay period *after* the one holding the earliest payment designated
    toward the account.
    """

    def _attr(self, first_payment_date, configured, next_period_start=None):
        """
        Build a CreditPaymentAttribution far enough to call
        ``_effective_begin_date()`` without touching a database, and return a
        2-tuple of it and the mocked session, so the query can be inspected.
        """
        db = Mock()
        db.query.return_value.filter.return_value.scalar.return_value = \
            first_payment_date
        a = CreditPaymentAttribution.__new__(CreditPaymentAttribution)
        a._db = db
        a.account = Mock(id=2)
        a.payment_date = date(2017, 6, 21)
        a.exclude_txn_id = None
        a.configured_begin_date = configured
        period = Mock()
        period.next.start_date = next_period_start
        with patch('%s.BiweeklyPayPeriod' % pbm) as m_pp:
            m_pp.period_for_date.return_value = period
            result = a._effective_begin_date()
            calls = m_pp.period_for_date.call_args_list
        return result, db, calls

    def test_no_designated_payment_returns_configured(self):
        """FR-004: with nothing to anchor the window, the configured date
        stands and behaviour is exactly what it was before issue #358."""
        result, _, calls = self._attr(None, date(2017, 1, 1))
        assert result == date(2017, 1, 1)
        # no pay period is looked up at all
        assert calls == []

    def test_derived_bound_wins_when_later(self):
        """FR-002: the bound is the start of the period after the one holding
        the earliest designated payment."""
        result, _, calls = self._attr(
            date(2017, 4, 20), date(2017, 1, 1),
            next_period_start=date(2017, 4, 28)
        )
        assert result == date(2017, 4, 28)
        assert len(calls) == 1
        assert calls[0][0][0] == date(2017, 4, 20)

    def test_configured_date_wins_when_later(self):
        """FR-007: the configured date is a floor and is never undercut by a
        derived bound that falls earlier."""
        result, _, _ = self._attr(
            date(2017, 4, 20), date(2017, 6, 1),
            next_period_start=date(2017, 4, 28)
        )
        assert result == date(2017, 6, 1)

    def test_equal_dates_are_stable(self):
        """The two bounds coinciding is not a special case."""
        result, _, _ = self._attr(
            date(2017, 4, 20), date(2017, 4, 28),
            next_period_start=date(2017, 4, 28)
        )
        assert result == date(2017, 4, 28)

    def test_exclude_txn_id_is_not_applied(self):
        """FR-005: the transaction being edited still anchors the window, so
        the derivation query must not filter it out. Only two filter terms are
        passed -- the account and the payment date -- and the query is never
        narrowed further."""
        db = Mock()
        db.query.return_value.filter.return_value.scalar.return_value = None
        a = CreditPaymentAttribution.__new__(CreditPaymentAttribution)
        a._db = db
        a.account = Mock(id=2)
        a.payment_date = date(2017, 6, 21)
        a.exclude_txn_id = 17
        a.configured_begin_date = date(2017, 1, 1)
        a._effective_begin_date()
        # one filter() call carrying exactly the account and date bounds
        assert db.query.return_value.filter.call_count == 1
        assert len(db.query.return_value.filter.call_args[0]) == 2
        # and no second filter chained off the first
        assert db.query.return_value.filter.return_value.filter.called is False


class TestSplitForDisplay(object):
    """
    Tests for the display cap; GitHub issue #358. Everything older than the
    most recent :py:const:`~.CREDIT_PAYMENT_MAX_PERIODS` periods collapses into
    one summary row. The cap is a display concern and must never change an
    amount.
    """

    def _periods(self, count, attributed_through=0):
        """
        ``count`` period dicts, oldest first, each 100.00 outstanding. The
        first ``attributed_through`` of them have their whole 100.00 covered by
        the payment, which is what oldest-first attribution produces.
        """
        return [
            {
                'start_date': date(2017, 1, 6) + timedelta(days=14 * n),
                'end_date': date(2017, 1, 19) + timedelta(days=14 * n),
                'is_closed': True,
                'outstanding': Decimal('100.00'),
                'attributed': (
                    Decimal('100.00') if n < attributed_through
                    else Decimal('0.0')
                )
            }
            for n in range(0, count)
        ]

    def test_empty(self):
        periods, rollup = CreditPaymentAttribution._split_for_display([])
        assert periods == []
        assert rollup is None

    def test_under_the_cap(self):
        given = self._periods(CREDIT_PAYMENT_MAX_PERIODS - 1)
        periods, rollup = CreditPaymentAttribution._split_for_display(given)
        assert periods == given
        assert rollup is None

    def test_exactly_the_cap_is_not_collapsed(self):
        """FR-013: the boundary is inclusive -- a window holding exactly the
        cap's worth of periods renders as it did before issue #358."""
        given = self._periods(CREDIT_PAYMENT_MAX_PERIODS)
        periods, rollup = CreditPaymentAttribution._split_for_display(given)
        assert periods == given
        assert rollup is None

    def test_one_over_the_cap(self):
        """The smallest rollup there can be: one period."""
        given = self._periods(CREDIT_PAYMENT_MAX_PERIODS + 1)
        periods, rollup = CreditPaymentAttribution._split_for_display(given)
        assert len(periods) == CREDIT_PAYMENT_MAX_PERIODS
        assert periods == given[1:]
        assert rollup == {
            'count': 1,
            'start_date': given[0]['start_date'],
            'end_date': given[0]['end_date'],
            'outstanding': Decimal('100.00'),
            'attributed': Decimal('0.0')
        }

    def test_long_window_sums_and_dates(self):
        """FR-012: the summary states how many periods it stands for, the
        range they span, and both of their summed amounts."""
        given = self._periods(20, attributed_through=4)
        periods, rollup = CreditPaymentAttribution._split_for_display(given)
        assert len(periods) == CREDIT_PAYMENT_MAX_PERIODS
        assert periods == given[-CREDIT_PAYMENT_MAX_PERIODS:]
        assert rollup['count'] == 20 - CREDIT_PAYMENT_MAX_PERIODS
        assert rollup['start_date'] == given[0]['start_date']
        assert rollup['end_date'] == given[13]['end_date']
        assert rollup['outstanding'] == Decimal('1400.00')
        # oldest-first attribution puts the whole payment on collapsed
        # periods; the summary must say so rather than hide it
        assert rollup['attributed'] == Decimal('400.00')

    def test_amounts_are_conserved(self):
        """FR-014: nothing is lost or double-counted by the split, for either
        column, whatever the window's length."""
        for count in [0, 1, CREDIT_PAYMENT_MAX_PERIODS, 7, 20, 213]:
            given = self._periods(count, attributed_through=min(count, 9))
            periods, rollup = CreditPaymentAttribution._split_for_display(
                given
            )
            for key in ['outstanding', 'attributed']:
                split_total = sum(
                    [p[key] for p in periods], Decimal('0.0')
                ) + (Decimal('0.0') if rollup is None else rollup[key])
                assert split_total == sum(
                    [p[key] for p in given], Decimal('0.0')
                )

    def test_decimal_arithmetic(self):
        """Constitution "Financial correctness": the sums stay exact. Summed
        as floats, 0.1 twelve times over is not 1.2."""
        given = [
            {
                'start_date': date(2017, 1, 6) + timedelta(days=14 * n),
                'end_date': date(2017, 1, 19) + timedelta(days=14 * n),
                'is_closed': True,
                'outstanding': Decimal('0.10'),
                'attributed': Decimal('0.10')
            }
            for n in range(0, 18)
        ]
        _, rollup = CreditPaymentAttribution._split_for_display(given)
        assert rollup['outstanding'] == Decimal('1.20')
        assert rollup['attributed'] == Decimal('1.20')
        assert isinstance(rollup['outstanding'], Decimal)
