#!/usr/bin/env python
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
import os
import re
from collections import defaultdict

index_head = """Screenshots
===========

"""

import os
import glob
import socket
import logging
from time import sleep
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import biweeklybudget.settings
from biweeklybudget.settings import PAY_PERIOD_START_DATE
from biweeklybudget.tests.fixtures.sampledata import SampleDataLoader
try:
    from pytest_flask.fixtures import LiveServer
except ImportError:
    pass

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from PIL import Image

format = "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - " \
         "%(name)s.%(funcName)s() ] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger()

connstr = os.environ.get('DB_CONNSTRING', None)
if connstr is None:
    connstr = 'mysql+pymysql://budgetTester:jew8fu0ue@127.0.0.1:3306/' \
              'budgettest?charset=utf8mb4'
    os.environ['DB_CONNSTRING'] = connstr
biweeklybudget.settings.DB_CONNSTRING = connstr

import biweeklybudget.db  # noqa
import biweeklybudget.models.base  # noqa
from biweeklybudget.flaskapp.app import app  # noqa
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.models.ofx_transaction import OFXTransaction

engine = create_engine(
    connstr, convert_unicode=True, echo=False,
    connect_args={'sql_mode': 'STRICT_ALL_TABLES'},
    pool_size=10, pool_timeout=120
)


class Screenshotter(object):
    """
    Generate sample screenshots for the documentation, and the
    ``screenshots.rst`` documentation page.
    """

    screenshots = [
        {
            'path': '/',
            'filename': 'index',
            'title': 'Index Page',
            'description': 'Main landing page.'
        },
        {
            'path': '/payperiods',
            'filename': 'payperiods',
            'title': 'Pay Periods View',
            'description': 'Summary of previous, current and upcoming pay '
                           'periods, plus date selector to find a pay period.'
        },
        {
            'path': '/payperiod/%s' % PAY_PERIOD_START_DATE.strftime(
                '%Y-%m-%d'
            ),
            'filename': 'payperiod',
            'title': 'Single Pay Period View',
            'description': 'Shows a pay period (current in this example) '
                           'balances (income, allocated, spent, remaining), '
                           'budgets and transactions (previous/manually-'
                           'entered and scheduled).'
        },
        {
            'path': '/accounts',
            'filename': 'accounts',
            'title': 'Accounts View'
        },
        {
            'path': '/accounts/1',
            'filename': 'account1',
            'title': 'Account Details',
            'description': 'Details of a single account.'
        },
        {
            'path': '/ofx',
            'filename': 'ofx',
            'title': 'OFX Transactions',
            'description': 'Shows transactions imported from OFX statements.'
        },
        {
            'path': '/transactions',
            'filename': 'transactions',
            'title': 'Transactions View',
            'description': 'Shows all manually-entered transactions.'
        },
        {
            'path': '/transactions/2',
            'filename': 'transaction2',
            'title': 'Transaction Detail',
            'description': 'Transaction detail modal to view and edit a '
                           'transaction.'
        },
        {
            'path': '/budgets',
            'filename': 'budgets',
            'title': 'Budgets',
            'description': 'List all budgets'
        },
        {
            'path': '/budgets/2',
            'filename': 'budget2',
            'title': 'Single Budget View',
            'description': 'Budget detail modal to view and edit a budget.'
        },
        {
            'path': '/scheduled',
            'filename': 'scheduled',
            'title': 'Scheduled Transactions',
            'description': 'List all scheduled transactions (active and '
                           'inactive).'
        },
        {
            'path': '/scheduled/1',
            'filename': 'scheduled1',
            'title': 'Specific Date Scheduled Transaction',
            'description': 'Scheduled transactions can occur one-time on a '
                           'single specific date.'
        },
        {
            'path': '/scheduled/2',
            'filename': 'scheduled2',
            'title': 'Monthly Scheduled Transaction',
            'description': 'Scheduled transactions can occur monthly on a '
                           'given date.'
        },
        {
            'path': '/scheduled/3',
            'filename': 'scheduled3',
            'title': 'Number Per-Period Scheduled Transactions',
            'description': 'Scheduled transactions can occur a given number '
                           'of times per pay period.'
        },
        {
            'path': '/reconcile',
            'filename': 'reconcile',
            'title': 'Reconcile Transactions with OFX',
            'description': 'OFX Transactions reported by financial institutions'
                           ' can be marked as reconciled with a corresponding '
                           'Transaction.',
            'preshot_func': '_reconcile_preshot'
        },
        {
            'path': '/reconcile',
            'filename': 'reconcile-drag',
            'title': 'Drag-and-Drop Reconciling',
            'description': 'To reconcile an OFX transaction with a Transaction,'
                           ' just drag and drop.',
            'preshot_func': '_reconcile_drag_preshot'
        },
        {
            'path': '/fuel',
            'filename': 'fuel',
            'title': 'Fuel Log',
            'description': 'Vehicle fuel log and fuel economy tracking.'
        },
        {
            'path': '/projects',
            'filename': 'projects',
            'title': 'Project Tracking',
            'description': 'Track projects and their cost.'
        },
        {
            'path': '/projects/1',
            'filename': 'bom',
            'title': 'Projects - Bill of Materials',
            'description': 'Track individual items/materials for projects.'
        }
    ]

    def __init__(self, toxinidir):
        """
        Initialize class

        :param toxinidir: tox.ini directory
        :type toxinidir: str
        """
        logger.info('Starting Screenshotter, toxinidir=%s', toxinidir)
        self.toxinidir = toxinidir
        self.srcdir = os.path.realpath(os.path.join(
            toxinidir, 'docs', 'source'
        ))
        self.browser = None
        self.server = self._create_server()

    def run(self):
        logger.info('Removing old screenshots')
        for f in glob.glob('docs/source/*.png'):
            os.unlink(f)
        self._refreshdb()
        logger.info('Starting server...')
        self.server.start()
        logger.info('LiveServer running at: %s', self.base_url)
        for sdict in self.screenshots:
            self.take_screenshot(**sdict)
        logger.info('Stopping server...')
        self.server.stop()
        self.make_rst()

    def make_rst(self):
        r = index_head
        for sdict in self.screenshots:
            r += sdict['title'] + "\n"
            r += '-' * len(sdict['title']) + "\n\n"
            if 'description' in sdict:
                r += "%s\n\n" % sdict['description']
            r += '.. image:: %s_sm.png' % sdict['filename'] + "\n"
            r += '   :target: %s.png' % sdict['filename'] + "\n"
            r += "\n"
        r_path = os.path.join(self.srcdir, 'screenshots.rst')
        if os.path.exists(r_path):
            os.unlink(r_path)
        with open(r_path, 'w') as fh:
            fh.write(r)
        logger.info('screenshots.rst written to: %s', r_path)

    def take_screenshot(self, path=None, filename=None, title=None,
                        preshot_func=None, description=None):
        """Take a screenshot and save it."""
        self.get(path)
        sleep(1)
        if preshot_func is not None:
            getattr(self, preshot_func)()
            sleep(1)
        # get_screenshot_as_png() -> binary data
        fpath = os.path.join(self.srcdir, '%s.png' % filename)
        logger.info('Screenshotting "%s" to %s', path, fpath)
        self.browser.get_screenshot_as_file(fpath)
        self._resize_image(filename)

    def _reconcile_preshot(self):
        logger.info('Reconcile preshot')
        self._update_db()
        self.get('/reconcile')
        sleep(1)

    def _reconcile_drag_preshot(self):
        ofxdiv = self.browser.find_element_by_id('ofx-2-0')
        logger.info('ofxdiv location: %s size: %s',
                    ofxdiv.location, ofxdiv.size)
        pos_x = (ofxdiv.location['x'] - 400) + (ofxdiv.size['width'] / 4)
        pos_y = (ofxdiv.location['y'] - 50) + (ofxdiv.size['height'] / 2)
        self.browser.execute_script(
            "$('body').append($('%s'));" % self._cursor_script(pos_x, pos_y)
        )
        actions = ActionChains(self.browser)
        actions.move_to_element(ofxdiv)
        actions.click_and_hold()
        actions.move_by_offset(-400, -50)
        actions.perform()
        self.browser.get_screenshot_as_file('docs/source/foo.png')

    def _cursor_script(self, x_pos, y_pos):
        s = '<img width="37" height="37" src="data:image/png;base64,iVBOR' \
            'w0KGgoAAAANSUhEUgAAACUAAAAlCAIAAABK/LdUAAAACXBIWXMAAA7EAAAOx' \
            'AGVKw4bAAAAB3RJTUUH4QUBAC04abho4wAABbtJREFUWMPtl3lQ1GUYx9/fs' \
            'Se7mxwSsAjLjajcKgsooSjKkXjhXTKmNApeRIqMk4Y20lhYgZlYWSkKBXHJq' \
            'CCgpCApIFcJuMACCwvswe7+9vzt79cfzFDTlKEBM830/PXOO++8n3meeb/f5' \
            '30gDMPADAYMZjb+Izyt3jBDPIIgVyVmu61LbxeIZ4L3dUk9ROfs3By9L72AI' \
            'Mjp5ckUmrTsipgwvqu9tcKAfFFQO7289y/d9vP3EkmU1U1dGyOWnsy+1T88N' \
            'l285s7B3DvtvDk2pbVtd5sEAxKlr4/3wbOF08VLyih2dXe+2yQQiGQyhfqHq' \
            'mZHe+79VlF+ZfPU867damztG9MRiEqrd7G1cLa1sDJnNz8T+fguSMooVmDaS' \
            'd6DTvJc3u3HOpwkjbi3kzWVigISwBAgSSAUieWYobNX7OdhP2X5kSR55I0Qv' \
            'hP7lydNdQ8bbC04c3mWBr32xs0qo6z/8+TIScIAANDz/dqA4xQUnaD29IniT' \
            '+UO6UyC/ecXlJZfTF4dvsSbSqVCEAQAkCkwnd5oZcF5mfzEUuXW1Cuzw97Lu' \
            '1lPkiQAAIIgO67V5ZNbQ91NRnrb8k5vjnjNj0ajjcMwDAvdc94j9qOUzDK1V' \
            'v9i+X1741FKZpmFtY25mamsv6v28gE6nf78QuWU/JR88f6ihT4dHV1Aj2W+u' \
            'zbU3/mfed0iaUJ6QUuPNDyUj6AUApBFpZXZySsjQnxQFAUAGHBj7u2mmqbuQ' \
            'E/elnAfKgUBAKhUqjWHvwQcLoPFesWEgZDG8ura14PdziREmnIYf11PI0F8e' \
            'r2GH5dJYVu+tSVKpTeKZUoGjRIS7P/2hyW1jR1GoxEAsC+9IDW7uleBnMmp2' \
            '30qDwCg1WrjTuSIVIiHs51Kra9p7pZr8HfiN0n1NJ9tH/9Jnb/rYcfxa51i9' \
            'dGEbe09wz/WtJqyGdbmHAqCBHq5WJqyUrLKqrJdpApNXkVzWFiIUCwPCvAtK' \
            'r0zMDzWLRxo7MUS34zpHpQy6BQaBalr68VxY1SQZxjf68RXxXqDcUu' \
            '4z595AyNjPFs7GpUyIldJlWoKiqg0OrXOoNYZ5EoNIEkEQYwECUjgYGNOp' \
            '1GHJAqSII0EMduUrVJh3YOjEAQTBEkQJAxDbBMaAsMSuVKl1JhxmBMUJDU' \
            '1dXy1ftmCll8F53Mq3By4bjyrQYlSienoVLShteNxfX3G/pUuDnNYTFpTx' \
            '0Dj0362CeNxY1vAXKv49XwOi0EnVeeuVJqamys1erlKs8TTwc5yVn5ZzbB' \
            'IePlEbKAn72/fS7tAfDijqHNI7e7uMjKmQVGkraHhs/2hG1YFMJlMAACm0' \
            'V/Ir61pFAR68fZuCGIxqePvZU/a9fperSWXy6JRxiQS6bDo9N6I2BVek9L' \
            'D9xVPjmWVoUxTHEa1o/1tuUkcDvsPLZ7AcRxBEARBJjYL7zzakVZsacNVj' \
            'op3xyxM2bmMxaS9gL+o1Lr0b6ouFdYe2MQ/Ehc+LmocxwU9fUnnSvqGVQk' \
            'b+duj+RO6lMnl8R/kQzAlbe9qV7vZL+ln4zYGQRBJkhqNpvpha0rWLY614' \
            '/IAzwvfFR7bvnjX2mAGgw7DMEEQMAz/W/+ciBv3mpM/KRUOY/a8OTErA2l' \
            'UVDgoKa+ug3F1XJTf8fjI8QJMGW/Noey6LoWLi6OlGZtKQSAAAUBCEDSmx' \
            'B7cry/P3OXvYTeV/TZhcwiJa40kaBUMPRWOdPaPtgiGxFKlTqfjWrDmOVl' \
            'NcX9fsdg11NsOJXTWFuyu/tGu/hEFpp3n8GpjQ0vW0XUMGnXq/y/piZHPO' \
            'rsWuc/xdrbhWs7ausK3ua0zdvn8EF+nyV+CTv4oz8Zs34aAe+1dkUHeQxI' \
            'lgwILe3oLTx+axv/n4W0hfb09TCq62MPuamHF2YPRs9iMaeQxaJT0xKirR' \
            'ZUPGp96O5qvW7Zg2ueH6KUei1zMH9T9fC4p5iXmFej/+XZK4zcO2rOZ8fx' \
            'z1AAAAABJRU5ErkJggg==" style="position: '
        s += 'absolute; left: %spx; top: %spx; z-index: 99;" />' % (
            x_pos, y_pos
        )
        return s

    def _resize_image(self, fname):
        """Resize an image"""
        fpath = os.path.join(self.srcdir, '%s.png' % fname)
        smallpath = os.path.join(self.srcdir, '%s_sm.png' % fname)
        logger.info('Generating 640x480 to: %s', smallpath)
        im = Image.open(fpath)
        im.thumbnail((640, 480))
        im.save(smallpath, "PNG")

    def get(self, path):
        """
        Get a page, via selenium.

        :param path: relative path to get on site
        :type path: str
        """
        url = '%s%s' % (self.base_url, path)
        logger.debug('GET %s', url)
        if self.browser is None:
            self.browser = self._get_browser()
        self.browser.get(url)

    def _get_browser(self):
        b = webdriver.PhantomJS()
        b.set_window_size(1920, 1080)
        b.implicitly_wait(2)
        return b

    def _create_server(self):
        """
        This is a version of pytest-flask's live_server fixture, modified for
        session use.
        """
        # Bind to an open port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
        logger.info('LiveServer will listen on port %s', port)
        return LiveServer(app, port)

    @property
    def base_url(self):
        """
        Simple fixture to return ``testflask`` base URL
        """
        return self.server.url()

    def _refreshdb(self):
        """
        Refresh/Load DB data before tests
        """
        if 'NO_REFRESH_DB' in os.environ:
            logger.info('Skipping session-scoped DB refresh')
            return
        # setup the connection
        conn = engine.connect()
        logger.info('Refreshing DB (session-scoped)')
        # clean the database
        biweeklybudget.models.base.Base.metadata.reflect(engine)
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
        conn.close()
        logger.info('DB refreshed.')

    def _update_db(self):
        conn = engine.connect()
        logger.info('Updating DB')
        data_sess = scoped_session(
            sessionmaker(autocommit=False, autoflush=False, bind=conn)
        )
        for t in data_sess.query(OFXTransaction).filter(
                OFXTransaction.account_id.__eq__(1)
        ).all():
            if t.reconcile is not None:
                continue
            data_sess.delete(t)
        data_sess.flush()
        data_sess.commit()
        data_sess.close()
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: make_jsdoc.py TOXINIDIR")
        raise SystemExit(1)
    Screenshotter(sys.argv[1]).run()
