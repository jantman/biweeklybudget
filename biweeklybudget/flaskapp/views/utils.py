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

from flask.views import MethodView
from biweeklybudget import settings
from biweeklybudget.utils import dtnow
from biweeklybudget.flaskapp.app import app


class DateTestJS(MethodView):
    """
    Handle GET /utils/datetest.js endpoint.
    """

    def get(self):
        if settings.BIWEEKLYBUDGET_TEST_TIMESTAMP is None:
            return 'var BIWEEKLYBUDGET_DEFAULT_DATE = new Date();'
        dt = dtnow()
        return 'var BIWEEKLYBUDGET_DEFAULT_DATE = new Date(%s, %s, %s);' % (
            dt.year, (dt.month - 1), dt.day
        )


def set_url_rules(a):
    a.add_url_rule(
        '/utils/datetest.js',
        view_func=DateTestJS.as_view('date_test_js')
    )


set_url_rules(app)
