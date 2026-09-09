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

import logging

from flask.views import MethodView
from flask import render_template

from biweeklybudget.cashposition import CashPosition
from biweeklybudget.db import db_session
from biweeklybudget.flaskapp.app import app

logger = logging.getLogger(__name__)


class CashPositionView(MethodView):
    """
    Render the GET /cash-position view using the ``cash-position.html``
    template.

    Lays the available-funds calculation out as a waterfall, itemized and with
    every line linked to the view it derives from. The notification banner on
    every page reports the bottom line of this calculation in a single
    sentence; this page is where you find out how it got there. See GitHub
    issue #321.

    The page is read-only. Everything on it is edited somewhere else, and each
    line links to wherever that is.
    """

    def get(self):
        return render_template(
            'cash-position.html',
            cp=CashPosition(db_session)
        )


app.add_url_rule(
    '/cash-position',
    view_func=CashPositionView.as_view('cash_position_view')
)
