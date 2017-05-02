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

import logging
from flask.views import MethodView
from flask import render_template, request
from versionfinder import find_version

from biweeklybudget.flaskapp.app import app
from biweeklybudget.version import VERSION, PROJECT_URL
from biweeklybudget.settings import DB_CONNSTRING

logger = logging.getLogger(__name__)

for lname in ['versionfinder', 'pip', 'git']:
    l = logging.getLogger(lname)
    l.setLevel(logging.CRITICAL)
    l.propagate = True


class HelpView(MethodView):
    """
    Render the GET /help view using the ``help.html`` template.
    """

    def get(self):
        return render_template(
            'help.html',
            ver_info=find_version('biweeklybudget').long_str,
            version=VERSION,
            url=PROJECT_URL,
            ua_str=request.headers.get('User-Agent', 'unknown'),
            db_uri=DB_CONNSTRING
        )


app.add_url_rule('/help', view_func=HelpView.as_view('help_view'))
