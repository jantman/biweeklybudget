#!/usr/bin/env python
"""
Development script to convert current version release notes to markdown and
either upload to Github as a gist, or create a Github release for the version.

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

import os
import pymysql.cursors
from pymysql.err import OperationalError
import logging
from time import sleep

FORMAT = "[%(levelname)s %(filename)s:%(lineno)s - %(name)s.%(funcName)s() ] " \
         "%(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger()

logger.info(
    'Connecting to MySQL on %s:%s as %s (with password)',
    os.environ['MYSQL_HOST'], os.environ['MYSQL_PORT'], os.environ['MYSQL_USER']
)

for _ in range(0, 40):
    try:
        connection = pymysql.connect(
            host=os.environ['MYSQL_HOST'],
            user=os.environ['MYSQL_USER'],
            port=int(os.environ['MYSQL_PORT']),
            password=os.environ['MYSQL_PASS'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        break
    except OperationalError:
        logger.error('Error connecting to DB; retry in 5s')
        sleep(5)

have_dbs = []
want_dbs = [
    os.environ.get(x, None) for x in [
        'MYSQL_DBNAME', 'MYSQL_DBNAME_LEFT', 'MYSQL_DBNAME_RIGHT'
    ] if os.environ.get(x, None)
]

logger.info('Want to create databases: %s', want_dbs)

with connection:
    with connection.cursor() as cursor:
        # Read a single record
        sql = "SHOW DATABASES;"
        logger.info('EXECUTE SQL: %s', sql)
        cursor.execute(sql)
        result = cursor.fetchall()
        have_dbs = [x['Database'] for x in result]
        logger.info('Have databases: %s', have_dbs)
        for dbname in want_dbs:
            if dbname in have_dbs:
                continue
            sql = f"CREATE DATABASE {dbname} CHARACTER SET = 'utf8mb4';"
            logger.info('EXECUTE SQL: %s', sql)
            cursor.execute(sql)
    connection.connect()
logger.info('Done setting up test DBs.')
