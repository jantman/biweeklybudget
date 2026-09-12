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

import pytest

from biweeklybudget.budget_spending import reporting_periods, PERIODS


class FakePayPeriod(object):
    """
    Minimal stand-in for :py:class:`~.BiweeklyPayPeriod`, which needs a
    database; :py:func:`~.reporting_periods` only reads these attributes.
    """

    def __init__(self, start_date):
        self.start_date = start_date
        self.end_date = start_date + timedelta(days=13)

    @property
    def previous(self):
        return FakePayPeriod(self.start_date - timedelta(days=14))


def periods_for(today, pp_start):
    """Return reporting_periods() for ``today`` as a dict keyed by key."""
    return {
        p['key']: (p['start_date'], p['end_date'])
        for p in reporting_periods(today, FakePayPeriod(pp_start))
    }


class TestReportingPeriods(object):

    def test_keys_names_and_order(self):
        res = reporting_periods(date(2017, 7, 28), FakePayPeriod(
            date(2017, 7, 21)))
        assert [(p['key'], p['name']) for p in res] == PERIODS
        assert [p['key'] for p in res] == [
            'current_pay_period', 'previous_pay_period',
            'current_month', 'previous_month',
            'current_year', 'previous_year'
        ]

    def test_mid_month(self):
        assert periods_for(date(2017, 7, 28), date(2017, 7, 21)) == {
            'current_pay_period': (date(2017, 7, 21), date(2017, 8, 3)),
            'previous_pay_period': (date(2017, 7, 7), date(2017, 7, 20)),
            'current_month': (date(2017, 7, 1), date(2017, 7, 31)),
            'previous_month': (date(2017, 6, 1), date(2017, 6, 30)),
            'current_year': (date(2017, 1, 1), date(2017, 12, 31)),
            'previous_year': (date(2016, 1, 1), date(2016, 12, 31)),
        }

    def test_first_of_january(self):
        res = periods_for(date(2021, 1, 1), date(2020, 12, 25))
        assert res['current_month'] == (date(2021, 1, 1), date(2021, 1, 31))
        assert res['previous_month'] == (
            date(2020, 12, 1), date(2020, 12, 31)
        )
        assert res['current_year'] == (date(2021, 1, 1), date(2021, 12, 31))
        assert res['previous_year'] == (
            date(2020, 1, 1), date(2020, 12, 31)
        )
        # the pay period straddles the new year; it is used as given
        assert res['current_pay_period'] == (
            date(2020, 12, 25), date(2021, 1, 7)
        )

    def test_thirty_first_of_december(self):
        res = periods_for(date(2020, 12, 31), date(2020, 12, 25))
        assert res['current_month'] == (
            date(2020, 12, 1), date(2020, 12, 31)
        )
        assert res['previous_month'] == (
            date(2020, 11, 1), date(2020, 11, 30)
        )
        assert res['current_year'] == (date(2020, 1, 1), date(2020, 12, 31))

    def test_leap_day(self):
        res = periods_for(date(2020, 2, 29), date(2020, 2, 21))
        assert res['current_month'] == (date(2020, 2, 1), date(2020, 2, 29))
        assert res['previous_month'] == (date(2020, 1, 1), date(2020, 1, 31))

    def test_march_after_non_leap_february(self):
        res = periods_for(date(2021, 3, 1), date(2021, 2, 26))
        assert res['current_month'] == (date(2021, 3, 1), date(2021, 3, 31))
        assert res['previous_month'] == (date(2021, 2, 1), date(2021, 2, 28))

    def test_march_after_leap_february(self):
        res = periods_for(date(2024, 3, 15), date(2024, 3, 8))
        assert res['previous_month'] == (date(2024, 2, 1), date(2024, 2, 29))

    @pytest.mark.parametrize('today', [
        date(2017, 7, 28), date(2021, 1, 1), date(2020, 12, 31),
        date(2020, 2, 29), date(2021, 3, 1), date(2019, 4, 30)
    ])
    def test_invariants(self, today):
        # a pay period containing today, starting on a Friday on or before it
        pp_start = today - timedelta(days=(today.weekday() - 4) % 7)
        res = periods_for(today, pp_start)
        for key, (start, end) in res.items():
            assert start <= end, key
        for kind in ['pay_period', 'month', 'year']:
            cur_start, cur_end = res['current_%s' % kind]
            prev_start, prev_end = res['previous_%s' % kind]
            # today is in every current period
            assert cur_start <= today <= cur_end, kind
            # each previous period ends the day before its current one starts
            assert prev_end == cur_start - timedelta(days=1), kind
        cur_pp = res['current_pay_period']
        prev_pp = res['previous_pay_period']
        assert cur_pp[1] - cur_pp[0] == timedelta(days=13)
        assert prev_pp[1] - prev_pp[0] == timedelta(days=13)
