#!/usr/bin/env python

import os
import argparse
import logging
import atexit

from sqlalchemy.orm.exc import NoResultFound

import biweeklybudget.settings as settings
from biweeklybudget.db import init_db, db_session, cleanup_db
from biweeklybudget.models import *


format = "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - " \
         "%(name)s.%(funcName)s() ] %(message)s"
logging.basicConfig(level=logging.DEBUG, format=format)
logger = logging.getLogger()


def main():
    logger.debug('Initalizing database')
    atexit.register(cleanup_db)
    init_db()
    logger.debug('Database initialized')
    print("DO STUFF HERE")

if __name__ == "__main__":
    main()
