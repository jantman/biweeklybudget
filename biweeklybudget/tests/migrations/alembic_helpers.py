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

import os
import logging
from sqlalchemy import create_engine


logger = logging.getLogger(__name__)


def uri_for_db(dbname):
    dbpass = ''
    if 'MYSQL_PASS' in os.environ:
        dbpass = ':%s' % os.environ['MYSQL_PASS']
    return '{scheme}://{user}{passwd}@{host}:{port}/{dbname}' \
           '?charset=utf8mb4'.format(
               scheme='mysql+pymysql',
               user=os.environ.get('MYSQL_USER', 'root'),
               passwd=dbpass,
               host=os.environ.get('MYSQL_HOST', '127.0.0.1'),
               port=os.environ.get('MYSQL_PORT', '3306'),
               dbname=dbname
           )


def empty_db_by_uri(uri):
    logger.info('Emptying database: %s', uri)
    engine = create_engine(uri)
    tables = [r[0] for r in engine.execute('SHOW TABLES;')]
    if len(tables) == 0:
        logger.info('Database already empty.')
        return
    logger.debug('Executing SQL: SET FOREIGN_KEY_CHECKS = 0')
    engine.execute('SET FOREIGN_KEY_CHECKS = 0')
    sql = 'DROP TABLE %s;' % ', '.join(tables)
    logger.debug('Executing SQL: %s', sql)
    engine.execute(sql)
    logger.debug('Executing SQL: SET FOREIGN_KEY_CHECKS = 1')
    engine.execute('SET FOREIGN_KEY_CHECKS = 1')
    engine.dispose()
    logger.info('DB emptied.')


def load_premigration_sql(uri):
    """
    Given a database URI, load the initial state SQL when Alembic was added
    to the project.
    """
    sqlpath = os.path.abspath(os.path.join(
        os.environ['TOXINIDIR'], 'biweeklybudget', 'tests', 'fixtures',
        'premigration_db_state.sql'
    ))
    logger.debug('Reading pre-migration DB state SQL from %s', sqlpath)
    sql = []
    with open(sqlpath, 'r') as fh:
        for line in fh.readlines():
            line = line.strip()
            if line != '':
                sql.append(line)
    engine = create_engine(uri)
    logger.info(
        'Loading SQL from pre-migration DB state into %s', engine.url.database
    )
    for s in sql:
        logger.debug('Executing SQL: %s', s)
        engine.execute(s)
    engine.dispose()
    logger.info('Pre-migration DB state loaded into %s', engine.url.database)
