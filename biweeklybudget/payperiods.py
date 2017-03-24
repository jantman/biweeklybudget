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

from datetime import timedelta


class BiweeklyPayPeriod(object):
    """
    This object contains all logic related to working with pay periods,
    specifically finding a pay period for a given data, and figuring out the
    start and end dates of pay periods. Sure, the app is called "biweeklybudget"
    but there's no reason to hard-code logic all over the place that's this
    simple.
    """

    _period_length = timedelta(days=13, hours=23, minutes=59, seconds=59)

    def __init__(self, start_date):
        self._start_date = start_date
        self._end_date = start_date + self._period_length

    @property
    def start_date(self):
        """
        Return the starting date for this pay period. The period is generally
        considered to start at midnight (00:00) of this date.

        :return:
        :rtype:
        """
        pass

    @property
    def end_date(self):
        """
        Return the date of the last day in this pay period. The pay period is
        generally considered to end at the last instant (i.e. 23:59:59) of this
        date.

        :return:
        :rtype:
        """
        pass

    @property
    def next_start_date(self):
        pass

    @property
    def previous_start_date(self):
        pass

    @staticmethod
    def period_for_date(dt):
        """
        Given a datetime, return the BiweeklyPayPeriod instance describing the
        pay period containing this date.

        :param dt: datetime or date to find the pay period for
        :type dt: :py:class:`~datetime.datetime` or :py:class:`~datetime.date`
        :return:
        :rtype: :py:class:`~.BiweeklyPayPeriod`
        """
        pass
