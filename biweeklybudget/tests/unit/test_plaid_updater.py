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

from biweeklybudget.plaid_updater import PlaidUpdateResult
from biweeklybudget.models.account import Account

from unittest.mock import Mock

pbm = 'biweeklybudget.plaid_updater'
pb = f'{pbm}.PlaidUpdater'


class TestPlaidUpdateResult:

    def test_happy_path(self):
        acct = Mock(spec_set=Account)
        type(acct).id = 2
        r = PlaidUpdateResult(
            acct, True, 1, 2, 'foo', 123
        )
        assert r.account == acct
        assert r.success is True
        assert r.updated == 1
        assert r.added == 2
        assert r.exc == 'foo'
        assert r.stmt_id == 123
        assert r.as_dict == {
            'account_id': 2,
            'success': True,
            'exception': 'foo',
            'statement_id': 123,
            'added': 2,
            'updated': 1
        }
