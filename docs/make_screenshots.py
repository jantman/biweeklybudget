#!/usr/bin/env python

import sys
import os
import re
from collections import defaultdict

index_head = """UI JavaScript Docs
==================

Files
-----

.. toctree::

"""

import os
import socket
import logging
from time import sleep
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import biweeklybudget.settings
from biweeklybudget.tests.fixtures.sampledata import SampleDataLoader
try:
    from pytest_flask.fixtures import LiveServer
except ImportError:
    pass

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

    def __init__(self, toxinidir):
        """
        Initialize class

        :param toxinidir: tox.ini directory
        :type toxinidir: str
        """
        logger.info('Starting Screenshotter, toxinidir=%s', toxinidir)
        self.toxinidir = toxinidir
        """
        self.jsdir = os.path.join(
            toxinidir, 'biweeklybudget', 'flaskapp', 'static', 'js'
        )
        self.srcdir = os.path.join(
            toxinidir, 'docs', 'source'
        )
        self.app = FakeApp()
        self.app.config.js_source_path = self.jsdir
        """
        self.server = self._create_server()

    def run(self):
        self._refreshdb()
        logger.info('Starting server...')
        self.server.start()
        logger.info('LiveServer running at: %s', self.base_url)
        sleep(60)
        logger.info('Stopping server...')
        self.server.stop()

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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("USAGE: make_jsdoc.py TOXINIDIR")
        raise SystemExit(1)
    Screenshotter(sys.argv[1]).run()
