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
import warnings

from retrying import retry

import biweeklybudget.settings
from biweeklybudget.tests.fixtures.sampledata import SampleDataLoader
from biweeklybudget.tests.sqlhelpers import restore_mysqldump, do_mysqldump
from biweeklybudget.tests.selenium_helpers import (
    set_browser_for_fullpage_screenshot
)

try:
    # Note that in pytest 3.6.0 thanks to issue #3487, anything called
    # "pytest_" in this file is attempted to be loaded as a plugin, and then
    # causes the test run to fail.
    import pytest_selenium.pytest_selenium as ptselenium
    from selenium.webdriver.support.event_firing_webdriver import \
        EventFiringWebDriver
    from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWD
    from selenium.webdriver.common.desired_capabilities import \
        DesiredCapabilities
    from selenium.webdriver import ChromeOptions
    HAVE_PYTEST_SELENIUM = True
except ImportError:
    HAVE_PYTEST_SELENIUM = False

import biweeklybudget.db  # noqa
import biweeklybudget.models.base  # noqa
from biweeklybudget.db_event_handlers import init_event_listeners  # noqa
from biweeklybudget.tests.unit.test_interest import InterestData  # noqa
from biweeklybudget.tests.migrations.alembic_helpers import (
    uri_for_db, empty_db_by_uri  # noqa
)

LIVESERVER_LOG_PATH = os.environ.get('BIWEEKLYBUDGET_LOG_FILE')

_DB_ENGINE = None

logger = logging.getLogger(__name__)

# suppress webdriver DEBUG logging
selenium_log = logging.getLogger("selenium")
selenium_log.setLevel(logging.INFO)
selenium_log.propagate = True

class_refresh_db_durations = []


def get_db_engine():
    global _DB_ENGINE
    if _DB_ENGINE is None:
        connstr = os.environ.get('DB_CONNSTRING', None)
        if connstr is None:
            connstr = 'mysql+pymysql://budgetTester:jew8fu0ue@127.0.0.1:3306/' \
                      'budgettest?charset=utf8mb4'
            os.environ['DB_CONNSTRING'] = connstr
        biweeklybudget.settings.DB_CONNSTRING = connstr
        _DB_ENGINE = create_engine(
            connstr, echo=False,
            connect_args={
                'sql_mode': 'STRICT_ALL_TABLES,NO_ZERO_DATE,'
                            'NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO,'
                            'NO_AUTO_CREATE_USER'
            },
            pool_size=10, pool_timeout=120
        )
    return _DB_ENGINE


@pytest.fixture
def alembic_root():
    return os.path.join(
        os.path.abspath(os.environ['TOXINIDIR']), 'biweeklybudget', 'alembic'
    )


@pytest.fixture
def uri_left():
    uri = uri_for_db(os.environ['MYSQL_DBNAME_LEFT'])
    empty_db_by_uri(uri)
    return uri


@pytest.fixture
def uri_right():
    uri = uri_for_db(os.environ['MYSQL_DBNAME_RIGHT'])
    empty_db_by_uri(uri)
    return uri


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
        conn = get_db_engine().connect()
        logger.info('Refreshing DB (session-scoped)')
        # clean the database
        biweeklybudget.models.base.Base.metadata.drop_all(get_db_engine())
        with warnings.catch_warnings():
            # Ignore warning from MariaDB MDEV-17544 when creating tables;
            # SQLAlchemy 1.3.13 names the primary keys, but MariaDB ignores
            # the names; MariaDB >= 10.4.7 now throws a warning for this.
            warnings.filterwarnings(
                'ignore',
                message=r'^\(1280, "Name.*ignored for PRIMARY key\."\)$',
                category=Warning
            )
            biweeklybudget.models.base.Base.metadata.create_all(get_db_engine())
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
    do_mysqldump(dump_file_path, get_db_engine())
    do_mysqldump(dump_file_path, get_db_engine(), with_data=False)
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
    restore_mysqldump(dump_file_path, get_db_engine())
    class_refresh_db_durations.append(time() - s)


@pytest.fixture
def testdb():
    """
    DB fixture to be used in tests
    """
    # setup the connection
    engine = get_db_engine()
    conn = engine.connect()
    sess = sessionmaker(autocommit=False, bind=conn)()
    init_event_listeners(sess, engine)
    # yield the session
    yield sess
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
        from pytest_flask.fixtures import LiveServer  # noqa
        from biweeklybudget.flaskapp.app import app  # noqa
        server = LiveServer(app, 'localhost', port)
        server.start()
        yield server
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


def retry_if_conn_error(ex):
    try:
        return isinstance(ex, ConnectionError)
    except NameError:
        return isinstance(ex, IOError)


@retry(
    stop_max_attempt_number=3, wait_fixed=3000,
    retry_on_exception=retry_if_conn_error
)
def get_driver_for_class(driver_class, driver_kwargs):
    """
    Wrapper around the selenium ``driver()`` fixture's
    ``driver_class(**driver_kwargs)`` call that retries up to 3 times, 3
    seconds apart, if a ConnectionError is raised.
    """
    return driver_class(**driver_kwargs)


@pytest.fixture
def driver(request, driver_class, driver_kwargs):
    """
    Returns a WebDriver instance based on options and capabilities

    This is copied from pytest-selenium 1.11.4, but modified to retry getting
    the driver up to 3 times to cope with intermittent connection resets in
    TravisCI. We ripped the original ``driver = driver_class(**driver_kwargs)``
    out and replaced it with the ``get_driver_for_class()`` function, which
    is wrapped in the retrying package's ``@retry`` decorator.
    """
    kwargs = driver_kwargs
    if 'desired_capabilities' not in kwargs:
        kwargs['desired_capabilities'] = DesiredCapabilities.CHROME
    kwargs['desired_capabilities']['goog:loggingPrefs'] = {
        'browser': 'ALL',
        'driver': 'ALL'
    }
    kwargs['desired_capabilities']['loggingPrefs'] = {
        'browser': 'ALL',
    }
    driver = get_driver_for_class(driver_class, kwargs)
    event_listener = request.config.getoption('event_listener')
    if event_listener is not None:
        # Import the specified event listener and wrap the driver instance
        mod_name, class_name = event_listener.rsplit('.', 1)
        mod = __import__(mod_name, fromlist=[class_name])
        event_listener = getattr(mod, class_name)
        if not isinstance(driver, EventFiringWebDriver):
            driver = EventFiringWebDriver(driver, event_listener())

    request.node._driver = driver
    yield driver
    driver.quit()


@pytest.fixture
def selenium(driver):
    """
    Per pytest-selenium docs, use this to override the selenium fixture to
    provide global common setup.
    """
    driver.set_window_size(1920, 1080)
    driver.implicitly_wait(2)
    # from http://stackoverflow.com/a/13853684/211734
    driver.set_script_timeout(30)
    # from http://stackoverflow.com/a/17536547/211734
    driver.set_page_load_timeout(30)
    yield driver


def _gather_screenshot(item, report, driver, summary, extra):
    """
    Redefine pytest-selenium's _gather_screenshot so that we can get full-page
    screenshots. This implementation is copied from pytest-selenium 1.11.4,
    but calls :py:func:`~.selenium_helpers.set_browser_for_fullpage_screenshot`
    before calling ``driver.get_screenshot_as_base64()``.
    """
    try:
        set_browser_for_fullpage_screenshot(driver)
        screenshot = driver.get_screenshot_as_base64()
    except Exception as e:
        summary.append('WARNING: Failed to gather screenshot: {0}'.format(e))
        return
    pytest_html = item.config.pluginmanager.getplugin('html')
    if pytest_html is not None:
        # add screenshot to the html report
        extra.append(pytest_html.extras.image(screenshot, 'Screenshot'))


def _gather_logs(item, report, driver, summary, extra):
    """Redefine here to fix a bug"""
    pytest_html = item.config.pluginmanager.getplugin("html")
    try:
        # this doesn't work with chromedriver
        # types = driver.log_types
        types = ['browser', 'driver', 'server']
    except Exception as e:
        # note that some drivers may not implement log types
        summary.append("WARNING: Failed to gather log types: {0}".format(e))
        return
    for name in types:
        try:
            log = driver.get_log(name)
        except Exception as e:
            summary.append(
                "WARNING: Failed to gather {0} log: {1}".format(name, e)
            )
            return
        if pytest_html is not None:
            extra.append(
                pytest_html.extras.text(
                    ptselenium.format_log(log), "%s Log" % name.title()
                )
            )


# redefine _gather_screenshot to use our implementation
if HAVE_PYTEST_SELENIUM:
    ptselenium._gather_screenshot = _gather_screenshot
    ptselenium._gather_logs = _gather_logs


@pytest.fixture
def chrome_options(chrome_options: 'ChromeOptions') -> 'ChromeOptions':
    chrome_options.add_argument('headless')
    chrome_options.add_argument('window-size=1920x1080')
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


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            parent = item.parent
            parent._previousfailed = item
    outcome = yield
    if (
        hasattr(item.session, 'liveserver_log') and
        item.nodeid in item.session.liveserver_log
    ):
        report = outcome.get_result()
        extra = getattr(report, 'extra', [])
        pos = item.session.liveserver_log[item.nodeid]
        pytest_html = item.config.pluginmanager.getplugin('html')
        if pytest_html is not None:
            fh = open(LIVESERVER_LOG_PATH, 'r')
            fh.seek(pos['start'])
            if 'end' in pos:
                log = fh.read(pos['end'] - pos['start'])
            else:
                log = fh.read()
            extra.append(pytest_html.extras.text(log, 'LiveServer'))
            msg = 'NOTE: testflask LiveServer logging captured via ' \
                  'pytest-html to: %s %s' % (LIVESERVER_LOG_PATH, pos)
            for item in list(report.sections):
                if item[0] == 'testflask':
                    report.sections.remove(item)
            report.sections.append(('testflask', msg))
            report.extra = extra
        else:
            report.sections.append((
                'testflask',
                'ERROR - pytest-html not present, cannot save server log!\n'
            ))


def getfilesize(fpath):
    f = open(fpath, 'r')
    f.seek(0, 2)
    val = f.tell()
    f.close()
    return val


def pytest_runtest_setup(item):
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail("previous test failed (%s)" % previousfailed.name)
    if hasattr(item, 'fixturenames') and 'testflask' in item.fixturenames:
        if not hasattr(item.session, 'liveserver_log'):
            setattr(item.session, 'liveserver_log', {})
        item.session.liveserver_log[item.nodeid] = {
            'start': getfilesize(LIVESERVER_LOG_PATH)
        }


def pytest_runtest_teardown(item):
    if (
        hasattr(item.session, 'liveserver_log') and
        item.nodeid in item.session.liveserver_log
    ):
        item.session.liveserver_log[item.nodeid][
            'end'] = getfilesize(LIVESERVER_LOG_PATH)


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
