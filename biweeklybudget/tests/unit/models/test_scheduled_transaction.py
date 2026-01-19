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
from datetime import date
from decimal import Decimal

from biweeklybudget.models.scheduled_transaction import ScheduledTransaction

import pytest


class TestScheduleType:

    def test_date(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            date=date(2025, 4, 15)
        )
        assert st.schedule_type == 'date'

    def test_monthly(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_month=15
        )
        assert st.schedule_type == 'monthly'

    def test_per_period(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            num_per_period=2
        )
        assert st.schedule_type == 'per period'

    def test_weekly(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=0  # Monday
        )
        assert st.schedule_type == 'weekly'

    def test_annual(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=4,
            annual_day=15
        )
        assert st.schedule_type == 'annual'

    def test_none(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test'
        )
        assert st.schedule_type is None


class TestRecurrenceStr:

    def test_date(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            date=date(2025, 4, 15)
        )
        assert st.recurrence_str == '2025-04-15'

    def test_monthly_first(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_month=1
        )
        assert st.recurrence_str == '1st'

    def test_monthly_second(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_month=2
        )
        assert st.recurrence_str == '2nd'

    def test_monthly_third(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_month=3
        )
        assert st.recurrence_str == '3rd'

    def test_monthly_fourth(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_month=4
        )
        assert st.recurrence_str == '4th'

    def test_per_period(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            num_per_period=3
        )
        assert st.recurrence_str == '3 per period'

    def test_weekly_monday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=0
        )
        assert st.recurrence_str == 'Every Monday'

    def test_weekly_tuesday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=1
        )
        assert st.recurrence_str == 'Every Tuesday'

    def test_weekly_wednesday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=2
        )
        assert st.recurrence_str == 'Every Wednesday'

    def test_weekly_thursday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=3
        )
        assert st.recurrence_str == 'Every Thursday'

    def test_weekly_friday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=4
        )
        assert st.recurrence_str == 'Every Friday'

    def test_weekly_saturday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=5
        )
        assert st.recurrence_str == 'Every Saturday'

    def test_weekly_sunday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=6
        )
        assert st.recurrence_str == 'Every Sunday'

    def test_annual_jan(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=1,
            annual_day=15
        )
        assert st.recurrence_str == 'Jan 15th'

    def test_annual_apr(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=4,
            annual_day=4
        )
        assert st.recurrence_str == 'Apr 4th'

    def test_annual_dec_first(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=12,
            annual_day=1
        )
        assert st.recurrence_str == 'Dec 1st'

    def test_annual_jul_fourth(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=7,
            annual_day=4
        )
        assert st.recurrence_str == 'Jul 4th'

    def test_annual_dec_25(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=12,
            annual_day=25
        )
        assert st.recurrence_str == 'Dec 25th'

    def test_none(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test'
        )
        assert st.recurrence_str is None


class TestValidators:

    def test_day_of_month_valid_min(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_month=1
        )
        assert st.day_of_month == 1

    def test_day_of_month_valid_max(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_month=28
        )
        assert st.day_of_month == 28

    def test_day_of_month_invalid_zero(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                day_of_month=0
            )

    def test_day_of_month_invalid_29(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                day_of_month=29
            )

    def test_num_per_period_valid(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            num_per_period=1
        )
        assert st.num_per_period == 1

    def test_num_per_period_invalid_zero(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                num_per_period=0
            )

    def test_day_of_week_valid_monday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=0
        )
        assert st.day_of_week == 0

    def test_day_of_week_valid_sunday(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            day_of_week=6
        )
        assert st.day_of_week == 6

    def test_day_of_week_invalid_negative(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                day_of_week=-1
            )

    def test_day_of_week_invalid_7(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                day_of_week=7
            )

    def test_annual_month_valid_jan(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=1,
            annual_day=15
        )
        assert st.annual_month == 1

    def test_annual_month_valid_dec(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=12,
            annual_day=15
        )
        assert st.annual_month == 12

    def test_annual_month_invalid_zero(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                annual_month=0,
                annual_day=15
            )

    def test_annual_month_invalid_13(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                annual_month=13,
                annual_day=15
            )

    def test_annual_day_valid_min(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=1,
            annual_day=1
        )
        assert st.annual_day == 1

    def test_annual_day_valid_max(self):
        st = ScheduledTransaction(
            amount=Decimal('100.00'),
            description='Test',
            annual_month=1,
            annual_day=31
        )
        assert st.annual_day == 31

    def test_annual_day_invalid_zero(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                annual_month=1,
                annual_day=0
            )

    def test_annual_day_invalid_32(self):
        with pytest.raises(AssertionError):
            ScheduledTransaction(
                amount=Decimal('100.00'),
                description='Test',
                annual_month=1,
                annual_day=32
            )
