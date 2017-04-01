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
import sys

from biweeklybudget.models.account import Account
from biweeklybudget.flaskapp.notifications import NotificationsController

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call  # noqa
else:
    from unittest.mock import Mock, patch, call  # noqa

pbm = 'biweeklybudget.flaskapp.notifications'
pb = '%s.NotificationsController' % pbm


class TestNotifications(object):

    def test_num_stale_accounts(self):
        accts = [
            Mock(is_stale=True, is_active=True),
            Mock(is_stale=False, is_active=True)
        ]
        with patch('%s.db_session' % pbm) as mock_db:
            mock_db.query.return_value.filter.return_value\
                .all.return_value = accts
            res = NotificationsController.num_stale_accounts()
        assert res == 1
        assert mock_db.mock_calls[0] == call.query(Account)
        assert mock_db.mock_calls[2] == call.query().filter().all()

    def test_get_notifications_no_stale(self):
        with patch('%s.num_stale_accounts' % pb) as m_num_stale:
            m_num_stale.return_value = 0
            res = NotificationsController.get_notifications()
        assert res == [
            {
                'classes': 'alert alert-warning',
                'content': 'XX Unreconciled Transactions. (EXAMPLE) '
                           '<a href="/reconcile" class="alert-link">'
                           'Alert Link</a>.'
            }
        ]

    def test_get_notifications_one_stale(self):
        with patch('%s.num_stale_accounts' % pb) as m_num_stale:
            m_num_stale.return_value = 1
            res = NotificationsController.get_notifications()
        assert res == [
            {
                'classes': 'alert alert-danger',
                'content': '1 Account with stale data. <a href="/accounts" '
                           'class="alert-link">View Accounts</a>.'
            },
            {
                'classes': 'alert alert-warning',
                'content': 'XX Unreconciled Transactions. (EXAMPLE) '
                           '<a href="/reconcile" class="alert-link">'
                           'Alert Link</a>.'
            }
        ]

    def test_get_notifications_three_stale(self):
        with patch('%s.num_stale_accounts' % pb) as m_num_stale:
            m_num_stale.return_value = 3
            res = NotificationsController.get_notifications()
        assert res == [
            {
                'classes': 'alert alert-danger',
                'content': '3 Accounts with stale data. <a href="/accounts" '
                           'class="alert-link">View Accounts</a>.'
            },
            {
                'classes': 'alert alert-warning',
                'content': 'XX Unreconciled Transactions. (EXAMPLE) '
                           '<a href="/reconcile" class="alert-link">'
                           'Alert Link</a>.'
            }
        ]
