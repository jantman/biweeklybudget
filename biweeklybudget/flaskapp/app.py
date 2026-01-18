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
import os

if os.environ.get('NEW_RELIC_LICENSE_KEY', '') != '':
    import newrelic.agent
    newrelic.agent.initialize()

# workaround for https://github.com/jantman/versionfinder/issues/5
# caused by versionfinder import in ``views/help.py``
try:
    import pip  # noqa
except (ImportError, KeyError):
    pass

from collections import namedtuple

import datatables
from flask import Flask

from biweeklybudget.db import init_db, cleanup_db
from biweeklybudget.flaskapp.jsonencoder import MagicJSONProvider
from biweeklybudget.utils import fix_werkzeug_logger

format = "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - " \
         "%(name)s.%(funcName)s() ] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger()

if 'BIWEEKLYBUDGET_LOG_FILE' in os.environ:
    # mainly for acceptance tests
    fhandler = logging.FileHandler(os.environ['BIWEEKLYBUDGET_LOG_FILE'])
    fhandler.setLevel(logging.DEBUG)
    fhandler.setFormatter(logging.Formatter(fmt=format))
    logger.addHandler(fhandler)

fix_werkzeug_logger()

app = Flask(__name__)
app.jinja_env.add_extension('jinja2.ext.loopcontrols')
# Flask 3.x uses json_provider_class instead of json_encoder
app.json_provider_class = MagicJSONProvider
app.json = MagicJSONProvider(app)
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


# Monkey-patch datatables package for SQLAlchemy 2.0 compatibility
# The package uses query.join('relationship_name') which no longer works in
# SQLAlchemy 2.0 - it must pass the actual relationship attribute instead
_original_datatable_init = datatables.DataTable.__init__


def _patched_datatable_init(self, params, model, query, columns):
    self.params = params
    self.model = model
    self.query = query
    self.data = {}
    self.columns = []
    self.columns_dict = {}
    self.search_func = lambda qs, s: qs

    DataColumn = namedtuple("DataColumn", ("name", "model_name", "filter"))

    for col in columns:
        name, model_name, filter_func = None, None, None

        if isinstance(col, datatables.DataColumn):
            self.columns.append(col)
            continue
        elif isinstance(col, tuple):
            if len(col) == 3:
                name, model_name, filter_func = col
            elif len(col) == 2:
                if callable(col[1]):
                    name, filter_func = col
                    model_name = name
                else:
                    name, model_name = col
            else:
                raise ValueError("Columns must be a tuple of 2 to 3 elements")
        else:
            name, model_name = col, col

        d = DataColumn(name=name, model_name=model_name, filter=filter_func)
        self.columns.append(d)
        self.columns_dict[d.name] = d

    # SQLAlchemy 2.0 fix: use getattr to get the actual relationship attribute
    # instead of passing a string to query.join()
    for column in (col for col in self.columns if "." in col.model_name):
        relationship_name = column.model_name.split(".")[0]
        self.query = self.query.join(getattr(self.model, relationship_name))


datatables.DataTable.__init__ = _patched_datatable_init


from biweeklybudget.flaskapp.views import *  # noqa
from biweeklybudget.flaskapp.filters import *  # noqa
from biweeklybudget.flaskapp.jinja_tests import *  # noqa
from biweeklybudget.flaskapp.context_processors import *  # noqa
from biweeklybudget.flaskapp.cli_commands import *  # noqa
