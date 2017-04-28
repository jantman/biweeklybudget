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

from datetime import date, datetime
from time import mktime
from json import JSONEncoder
from decimal import Decimal


class MagicJSONEncoder(JSONEncoder):
    """
    Customized JSONEncoder class that uses ``as_dict`` properties on objects
    to encode them.
    """

    def default(self, o):
        if hasattr(o, 'as_dict') and isinstance(type(o).as_dict, property):
            d = o.as_dict
            d['class'] = o.__class__.__name__
            return d
        if isinstance(o, datetime):
            return {
                'class': 'datetime',
                'str': o.strftime('%Y-%m-%d %H:%M:%S'),
                'ts': mktime(o.timetuple()),
                'year': o.year,
                'month': o.month,
                'date': o.day,
                'hour': o.hour,
                'minute': o.minute,
                'second': o.second,
                'tzname': o.strftime('%Z'),
                'tzoffset': o.strftime('%z'),
                'ymdstr': o.strftime('%Y-%m-%d')
            }
        if isinstance(o, date):
            return {
                'class': 'date',
                'str': o.strftime('%Y-%m-%d'),
                'ts': mktime(o.timetuple()),
                'year': o.year,
                'month': o.month,
                'date': o.day
            }
        if isinstance(o, Decimal):
            return float(o)
        return super(MagicJSONEncoder, self).default(o)
