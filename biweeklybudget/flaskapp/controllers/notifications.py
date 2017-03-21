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

from biweeklybudget.flaskapp.controllers.accounts import AccountController


class NotificationsController(object):

    @staticmethod
    def get_notifications():
        """
        Return all notifications that should be displayed at the top of pages,
        as a list in the order they should appear. Each list item is a dict
        with keys "classes" and "content", where classes is the string that
        should appear in the notification div's "class" attribute, and content
        is the string content of the div.
        """
        res = []
        num_stale = AccountController.num_stale_accounts()
        if num_stale > 0:
            a = 'Accounts'
            if num_stale == 1:
                a = 'Account'
            res.append({
                'classes': 'alert alert-danger',
                'content': '%d %s with stale data. <a href="/accounts" '
                           'class="alert-link">View Accounts</a>.' % (num_stale,
                                                                      a)
            })
        res.append({
            'classes': 'alert alert-warning',
            'content': 'XX Unreconciled Transactions. (EXAMPLE) '
                       '<a href="/reconcile" class="alert-link">Alert Link</a>.'
        })
        return res
