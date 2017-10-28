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

from flask import Flask

from biweeklybudget.db import init_db, cleanup_db
from biweeklybudget.flaskapp.jsonencoder import MagicJSONEncoder
from biweeklybudget.utils import fix_werkzeug_logger

format = "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - " \
         "%(name)s.%(funcName)s() ] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger()

fix_werkzeug_logger()

app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
app.json_encoder = MagicJSONEncoder
init_db()


def before_request():
    """
    When running in debug mode, clear jinja cache.
    """
    logger.warning('DEBUG MODE - Clearing jinja cache')
    app.jinja_env.cache = {}


@app.teardown_appcontext
def shutdown_session(exception=None):
    cleanup_db()


if app.debug:
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.before_request(before_request)
    app.jinja_env.auto_reload = True


from biweeklybudget.flaskapp.views import *  # noqa
from biweeklybudget.flaskapp.filters import *  # noqa
from biweeklybudget.flaskapp.jinja_tests import *  # noqa
from biweeklybudget.flaskapp.context_processors import *  # noqa
from biweeklybudget.flaskapp.cli_commands import *  # noqa
