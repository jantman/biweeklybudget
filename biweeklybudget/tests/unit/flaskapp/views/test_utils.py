"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2020 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

from biweeklybudget.flaskapp.views.utils import DateTestJS, set_url_rules
from unittest.mock import Mock, patch, call

pbm = 'biweeklybudget.flaskapp.views.utils'


class TestUrlRules:

    def test_rules(self):
        m_dtj_view = Mock()
        m_app = Mock()
        with patch(f'{pbm}.DateTestJS') as dtj_cls:
            dtj_cls.as_view.return_value = m_dtj_view
            set_url_rules(m_app)
        assert m_app.mock_calls == [
            call.add_url_rule('/utils/datetest.js', view_func=m_dtj_view)
        ]
        assert dtj_cls.mock_calls == [call.as_view('date_test_js')]


class TestDateTestJS:

    def test_normal(self):
        with patch(f'{pbm}.settings.BIWEEKLYBUDGET_TEST_TIMESTAMP', None):
            res = DateTestJS().get()
        assert res == 'var BIWEEKLYBUDGET_DEFAULT_DATE = new Date();'

    def test_during_tests(self):
        res = DateTestJS().get()
        assert res == 'var BIWEEKLYBUDGET_DEFAULT_DATE = new ' \
                      'Date(2017, 6, 28);'
