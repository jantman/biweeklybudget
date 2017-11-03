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
import re
from distutils.spawn import find_executable
import subprocess

logger = logging.getLogger(__name__)

mysqldump_path = find_executable('mysqldump')
mysql_path = find_executable('mysql')


def do_mysqldump(dumpdir, eng, with_data=True):
    """
    Shell out and mysqldump the database to the path specified by fpath.

    :param dumpdir: LocalPath specifying the directory to save dump to
    :param eng: SQLAlchemy engine to get connection information from
    :type eng: sqlalchemy.engine.Engine
    :param with_data: whether or not to include data, or just schema
    :type with_data: bool
    :raises: RuntimeError, AssertionError
    """
    assert mysqldump_path is not None
    assert eng.url.drivername == 'mysql+pymysql'
    if with_data:
        fpath = str(dumpdir.join('withdata.sql'))
        args = [
            mysqldump_path,
            '--create-options',
            '--routines',
            '--triggers',
            '--no-create-db'
        ]
    else:
        fpath = str(dumpdir.join('nodata.sql'))
        args = [
            mysqldump_path,
            '--create-options',
            '--no-data',
            '--no-create-db'
        ]
    args.append('--host=%s' % eng.url.host)
    args.append('--port=%s' % eng.url.port)
    args.append('--user=%s' % eng.url.username)
    if eng.url.password is not None:
        args.append('--password=%s' % eng.url.password)
    args.append(eng.url.database)
    logger.info('Running: %s', ' '.join(args))
    res = subprocess.check_output(args)
    if not with_data:
        # for no-data dumps, need to remove the AUTO_INCREMENT setters
        res = re.sub(b'AUTO_INCREMENT=\d+\s', b'', res)
    with open(str(fpath), 'wb') as fh:
        fh.write(res)
    logger.info('Wrote %d bytes of SQL to %s', len(res), fpath)


def restore_mysqldump(dumpdir, eng, with_data=True):
    """
    Shell out and restore a mysqldump file to the database.

    :param dumpdir: LocalPath specifying the directory to save dump to
    :param eng: SQLAlchemy engine to get connection information from
    :type eng: sqlalchemy.engine.Engine
    :param with_data: whether or not to include data, or just schema
    :type with_data: bool
    :raises: RuntimeError, AssertionError
    """
    assert mysql_path is not None
    assert eng.url.drivername == 'mysql+pymysql'
    if with_data:
        fpath = str(dumpdir.join('withdata.sql'))
    else:
        fpath = str(dumpdir.join('nodata.sql'))
    args = [
        mysql_path,
        '--batch',
        '--host=%s' % eng.url.host,
        '--port=%s' % eng.url.port,
        '--user=%s' % eng.url.username,
        '--database=%s' % eng.url.database
    ]
    if eng.url.password is not None:
        args.append('--password=%s' % eng.url.password)
    logger.info('Passing %s to %s', fpath, ' '.join(args))
    with open(str(fpath), 'rb') as fh:
        proc = subprocess.Popen(args, stdin=fh)
        stdout, stderr = proc.communicate()
    logger.info('MySQL dump restore complete.')
    logger.debug('mysql STDOUT: %s', stdout)
    logger.debug('mysql STDERR: %s', stderr)
