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

import pytest
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import socket
import json
from time import time

import biweeklybudget.settings
from biweeklybudget.tests.fixtures.sampledata import SampleDataLoader
from biweeklybudget.tests.sqlhelpers import restore_mysqldump, do_mysqldump

try:
    from pytest_flask.fixtures import LiveServer
except ImportError:
    pass

connstr = os.environ.get('DB_CONNSTRING', None)
if connstr is None:
    connstr = 'mysql+pymysql://budgetTester:jew8fu0ue@127.0.0.1:3306/' \
              'budgettest?charset=utf8mb4'
    os.environ['DB_CONNSTRING'] = connstr
biweeklybudget.settings.DB_CONNSTRING = connstr

import biweeklybudget.db  # noqa
import biweeklybudget.models.base  # noqa
from biweeklybudget.db_event_handlers import init_event_listeners  # noqa
from biweeklybudget.tests.unit.test_interest import InterestData  # noqa

engine = create_engine(
    connstr, convert_unicode=True, echo=False,
    connect_args={'sql_mode': 'STRICT_ALL_TABLES'},
    pool_size=10, pool_timeout=120
)

logger = logging.getLogger(__name__)

# suppress webdriver DEBUG logging
selenium_log = logging.getLogger("selenium")
selenium_log.setLevel(logging.INFO)
selenium_log.propagate = True

class_refresh_db_durations = []


@pytest.fixture(scope='session')
def dump_file_path(tmpdir_factory):
    """
    Return the directory to use for the SQL dump files
    """
    return tmpdir_factory.mktemp('sqldump')


@pytest.fixture(scope="session")
def refreshdb(dump_file_path):
    """
    Refresh/Load DB data before tests; also exec mysqldump to write a
    SQL dump file for faster refreshes during test runs.
    """
    if 'NO_REFRESH_DB' not in os.environ:
        # setup the connection
        conn = engine.connect()
        logger.info('Refreshing DB (session-scoped)')
        # clean the database
        biweeklybudget.models.base.Base.metadata.drop_all(engine)
        biweeklybudget.models.base.Base.metadata.create_all(engine)
        # load the sample data
        data_sess = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=conn)
        )
        SampleDataLoader(data_sess).load()
        data_sess.flush()
        data_sess.commit()
        data_sess.close()
        # close connection
        conn.close()
    else:
        logger.info('Skipping session-scoped DB refresh')
    # write the dump files
    do_mysqldump(dump_file_path, engine)
    do_mysqldump(dump_file_path, engine, with_data=False)
    yield


@pytest.fixture(scope="class")
def class_refresh_db(dump_file_path):
    """
    This fixture rolls the DB back to the previous state when the class is
    finished; to be used on classes that alter data.

    Use like:

        @pytest.mark.usefixtures('class_refresh_db', 'testdb')
        class MyClass(AcceptanceHelper):
    """
    global class_refresh_db_durations
    yield
    if 'NO_CLASS_REFRESH_DB' in os.environ:
        return
    logger.info('Refreshing DB (class-scoped)')
    s = time()
    restore_mysqldump(dump_file_path, engine)
    class_refresh_db_durations.append(time() - s)


@pytest.fixture
def testdb():
    """
    DB fixture to be used in tests
    """
    # setup the connection
    conn = engine.connect()
    sess = sessionmaker(autocommit=False, bind=conn)()
    init_event_listeners(sess)
    # yield the session
    yield(sess)
    sess.close()
    conn.close()


@pytest.fixture(scope="session")
def testflask():
    """
    This is a version of pytest-flask's live_server fixture, modified for
    session use.
    """
    if 'BIWEEKLYBUDGET_TEST_BASE_URL' not in os.environ:
        # Bind to an open port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        from biweeklybudget.flaskapp.app import app  # noqa
        server = LiveServer(app, port)
        server.start()
        yield(server)
        server.stop()


@pytest.fixture(scope="session")
def base_url(testflask):
    """
    Simple fixture to return ``testflask`` base URL
    """
    url = os.environ.get('BIWEEKLYBUDGET_TEST_BASE_URL', None)
    if url is not None:
        return url
    return testflask.url()


@pytest.fixture
def selenium(selenium):
    """
    Per pytest-selenium docs, use this to override the selenium fixture to
    provide global common setup.
    """
    selenium.set_window_size(1920, 1080)
    selenium.implicitly_wait(2)
    # from http://stackoverflow.com/a/13853684/211734
    selenium.set_script_timeout(30)
    # from http://stackoverflow.com/a/17536547/211734
    selenium.set_page_load_timeout(30)
    return selenium


@pytest.fixture
def chrome_options(chrome_options):
    chrome_options.add_argument('headless')
    return chrome_options


def pytest_addoption(parser):
    group = parser.getgroup("terminal reporting", "reporting", after="general")
    group.addoption('--durations-file',
                    action="store", type=str, default=None, metavar="P",
                    help="write all durations as JSON to P")


def pytest_terminal_summary(terminalreporter):
    """Write all test durations to results/durations.json"""
    fpath = terminalreporter.config.option.durations_file
    if fpath is None:
        return
    tr = terminalreporter
    dlist = []
    for replist in tr.stats.values():
        for rep in replist:
            if hasattr(rep, 'duration'):
                dlist.append(rep)
    if not dlist:
        return
    dlist.sort(key=lambda x: x.duration)
    dlist.reverse()
    tr.write_sep("-", "wrote all test durations to: %s" % fpath)

    result = []
    for rep in dlist:
        nodeid = rep.nodeid.replace("::()::", "::")
        result.append([nodeid, rep.when, rep.duration])
    with open(fpath, 'w') as fh:
        fh.write(json.dumps({
            'requests': result,
            'class_refresh_db': class_refresh_db_durations
        }))


# next section from:
# https://docs.pytest.org/en/latest/example/simple.html#\
# incremental-testing-test-steps


def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail("previous test failed (%s)" % previousfailed.name)


"""
Begin generated/parametrized tests for interest calculation.

I REALLY wish pytest still supported yield tests, this is sooooo messy!
"""


def pytest_generate_tests(metafunc):
    if (
        metafunc.function.__name__.startswith('test_calculate') and
        metafunc.module.__name__ == 'biweeklybudget.tests.unit.test_interest'
    ):
        if metafunc.cls.__name__ == 'TestDataAmEx':
            param_for_adbdaily_calc(metafunc, InterestData.amex)
        if metafunc.cls.__name__ == 'TestDataCiti':
            param_for_adbdaily_calc(metafunc, InterestData.citi)
        if metafunc.cls.__name__ == 'TestDataDiscover':
            param_for_adbdaily_calc(metafunc, InterestData.discover)


def param_for_adbdaily_calc(metafunc, s):
    dates = [d['start'].strftime('%Y-%m-%d') for d in s]
    metafunc.parametrize(
        'data',
        s,
        ids=dates
    )
