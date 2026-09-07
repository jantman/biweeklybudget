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

from biweeklybudget import settings
from biweeklybudget.flaskapp.views.index import (
    parse_chart_days, sample_chart_rows
)


class TestParseChartDays(object):
    """
    Tests for :py:func:`~.parse_chart_days`; see GitHub issue #279.

    These cover every row of the parameter resolution table in the feature's
    ``contracts/http-api.md``. The rule under test is that anything which is not
    a non-negative integer falls back to the default rather than raising.
    """

    def test_absent_parameter_uses_default(self):
        assert parse_chart_days(None, 365) == 365

    def test_empty_string_uses_default(self):
        assert parse_chart_days('', 365) == 365

    def test_whitespace_only_uses_default(self):
        assert parse_chart_days('   ', 365) == 365

    def test_zero_means_all_history(self):
        # 0 is a valid, meaningful value -- not a falsey value to default away
        assert parse_chart_days('0', 365) == 0

    def test_positive_integer_is_used(self):
        assert parse_chart_days('30', 365) == 30

    def test_surrounding_whitespace_is_tolerated(self):
        assert parse_chart_days(' 90 ', 365) == 90

    def test_negative_uses_default(self):
        assert parse_chart_days('-1', 365) == 365

    def test_non_numeric_uses_default(self):
        assert parse_chart_days('abc', 365) == 365

    def test_float_like_uses_default(self):
        assert parse_chart_days('1.5', 365) == 365

    def test_huge_value_is_accepted(self):
        # far more days than any stored history; harmless, and equivalent to a
        # value the user can already ask for with days=0
        assert parse_chart_days('999999', 365) == 999999

    def test_integer_input_is_accepted(self):
        # request.args.get returns str, but the helper must not care
        assert parse_chart_days(30, 365) == 30

    def test_default_is_returned_verbatim(self):
        # the default is whatever the caller passed, including 0
        assert parse_chart_days('nope', 0) == 0


class TestSampleChartRows(object):
    """
    Tests for :py:func:`~.sample_chart_rows`; see GitHub issue #279.

    Each test pins one of the guarantees stated in that function's docstring and
    in the feature's ``data-model.md``.
    """

    def test_empty_input_returns_empty(self):
        assert sample_chart_rows([], 300) == []

    def test_fewer_rows_than_limit_returns_the_same_list(self):
        rows = [{'date': '2026-01-%02d' % i} for i in range(1, 11)]
        result = sample_chart_rows(rows, 300)
        # identity, not just equality: nothing is copied, dropped or reordered
        assert result is rows

    def test_exactly_the_limit_returns_the_same_list(self):
        rows = list(range(300))
        assert sample_chart_rows(rows, 300) is rows

    def test_result_never_exceeds_max_points(self):
        # includes exact multiples, off-by-one sizes and awkward remainders
        for length in [301, 400, 599, 600, 601, 900, 1000, 1825, 3650]:
            rows = list(range(length))
            result = sample_chart_rows(rows, 300)
            assert len(result) <= 300, (length, len(result))

    def test_exact_multiple_does_not_overflow_the_limit(self):
        # regression guard: striding across the whole list and then appending
        # the final row returns max_points + 1 whenever the stride exactly
        # fills the quota. Six rows into three points is the smallest case.
        rows = list(range(6))
        result = sample_chart_rows(rows, 3)
        assert len(result) == 3
        assert result[-1] == 5

    def test_last_row_is_always_kept(self):
        for length in [301, 400, 599, 600, 601, 1825]:
            rows = [{'n': i} for i in range(length)]
            result = sample_chart_rows(rows, 300)
            assert result[-1] is rows[-1], length

    def test_first_row_is_kept(self):
        rows = [{'n': i} for i in range(1000)]
        result = sample_chart_rows(rows, 300)
        assert result[0] is rows[0]

    def test_order_is_preserved(self):
        rows = list(range(1825))
        result = sample_chart_rows(rows, 300)
        assert result == sorted(result)
        assert len(set(result)) == len(result)

    def test_max_points_of_one_returns_only_the_last_row(self):
        rows = list(range(50))
        assert sample_chart_rows(rows, 1) == [49]

    @pytest.mark.parametrize('max_points', [0, -1, -100])
    def test_max_points_below_one_is_treated_as_one(self, max_points):
        rows = list(range(50))
        assert sample_chart_rows(rows, max_points) == [49]

    def test_five_years_of_daily_balances(self):
        # the reporter's actual scale in GitHub issue #279
        rows = [{'date': i} for i in range(1825)]
        result = sample_chart_rows(rows, 300)
        assert len(result) <= 300
        assert result[0] is rows[0]
        assert result[-1] is rows[-1]

    def test_bound_holds_for_every_small_combination(self):
        # exhaustive over the sizes where off-by-one errors live
        for length in range(0, 65):
            for max_points in range(1, 20):
                rows = list(range(length))
                result = sample_chart_rows(rows, max_points)
                assert len(result) <= max_points, (length, max_points)
                if rows:
                    assert result[-1] == rows[-1], (length, max_points)
                    assert result == sorted(result), (length, max_points)
                    assert len(set(result)) == len(result)


class TestChartSettings(object):
    """
    The two settings added for GitHub issue #279 must be present with their
    documented defaults, overridable by environment variable, and *not*
    required -- an installation whose settings module predates this feature
    must keep working without being edited.
    """

    def test_default_days_present_with_documented_default(self):
        assert settings.ACCOUNT_BALANCE_CHART_DEFAULT_DAYS == 365

    def test_max_points_present_with_documented_default(self):
        assert settings.ACCOUNT_BALANCE_CHART_MAX_POINTS == 300

    def test_both_are_int_vars(self):
        # so the existing environment variable override path applies
        assert 'ACCOUNT_BALANCE_CHART_DEFAULT_DAYS' in settings._INT_VARS
        assert 'ACCOUNT_BALANCE_CHART_MAX_POINTS' in settings._INT_VARS

    def test_neither_is_required(self):
        assert 'ACCOUNT_BALANCE_CHART_DEFAULT_DAYS' not in settings._REQUIRED_VARS
        assert 'ACCOUNT_BALANCE_CHART_MAX_POINTS' not in settings._REQUIRED_VARS
