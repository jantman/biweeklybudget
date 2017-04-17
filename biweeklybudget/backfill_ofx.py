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

from datetime import datetime
import os
import argparse
import logging
import atexit
from io import BytesIO
from pytz import UTC

from ofxparse import OfxParser
from sqlalchemy.exc import InvalidRequestError, IntegrityError

from biweeklybudget import settings
from biweeklybudget.db import init_db, db_session, cleanup_db
from biweeklybudget.models.account import Account
from biweeklybudget.ofxupdater import OFXUpdater, DuplicateFileException
from biweeklybudget.cliutils import set_log_debug, set_log_info


logger = logging.getLogger(__name__)


class OfxBackfiller(object):
    """
    Class to backfill OFX in database from files on disk.
    """

    def __init__(self, savedir):
        logger.info('Initializing OfxBackfiller with savedir=%s', savedir)
        self.savedir = savedir
        logger.debug('Registering exit handler cleanup_db')
        atexit.register(cleanup_db)
        logger.debug('Initalizing database')
        init_db()
        logger.debug('Database initialized')

    def run(self):
        """
        Main entry point - run the backfill.
        """
        logger.debug('Checking for Accounts with statement directories')
        for acct in db_session.query(Account).all():
            p = os.path.join(settings.STATEMENTS_SAVE_PATH, acct.name)
            if not os.path.isdir(p):
                logger.info('No statement directory for Account %d (%s)',
                            acct.id, p)
                continue
            logger.debug('Found directory %s for Account %d', p, acct.id)
            self._do_account_dir(
                acct.id, acct.name, acct.ofx_cat_memo_to_name, p
            )

    def _do_account_dir(self, acct_id, acct_name, cat_memo, path):
        """
        Handle all OFX statements in a per-account directory.

        :param acct_id: account database ID
        :type acct_id: int
        :param acct_name: account name
        :type acct_name: str
        :param cat_memo: whether or not to concatenate OFX Memo to Name
        :type cat_memo: bool
        :param path: absolute path to per-account directory
        :type path: str
        """
        logger.debug('Doing account %s (id=%d) directory (%s)',
                     acct_name, acct_id, path)
        files = {}
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if not os.path.isfile(p):
                continue
            extension = p.split('.')[-1].lower()
            if extension not in ['ofx', 'qfx']:
                continue
            files[p] = os.path.getmtime(p)
        logger.debug('Found %d files for account %s', len(files), acct_name)
        updater = OFXUpdater(acct_id, acct_name, cat_memo=cat_memo)
        # run through the files, oldest to newest
        success = 0
        already = 0
        for p in sorted(files, key=files.get):
            try:
                self._do_one_file(updater, p)
                success += 1
            except DuplicateFileException:
                already += 1
                logger.warning('OFX is already parsed for account; skipping')
            except (InvalidRequestError, IntegrityError, TypeError):
                # if we have DB errors, bomb out immediately
                logger.error('Session dirty: %s', db_session.dirty)
                logger.error('Session new: %s', db_session.new)
                raise
            except Exception:
                logger.error('Exception parsing and inserting file %s',
                             p, exc_info=True)
        logger.info('Successfully parsed and inserted %d of %d files for '
                    'account %s; %d files already in DB', success, len(files),
                    acct_name, already)

    def _do_one_file(self, updater, path):
        """
        Parse one OFX file and use OFXUpdater to upsert it into the DB.

        :param updater: OFXUpdater instance for this class
        :type updater: biweeklybudget.ofxupdater.OFXUpdater
        :param path: absolute path to OFX/QFX file
        :type path: str
        """
        logger.debug('Handle file %s for %s (%d)', path, updater.acct_name,
                     updater.acct_id)
        with open(path, 'rb') as fh:
            ofx_str = fh.read()
        ofx = OfxParser.parse(BytesIO(ofx_str))
        logger.debug('Parsed OFX')
        fname = os.path.basename(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=UTC)
        updater.update(ofx, mtime=mtime, filename=fname)
        logger.debug('Done updating')
        db_session.commit()


def parse_args():
    """
    Parse command-line arguments.
    """
    p = argparse.ArgumentParser(description='Backfill OFX from disk')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    args = p.parse_args()
    return args


def main():
    """
    Main entry point - instantiate and run :py:class:`~.OfxBackfiller`.
    """
    global logger
    format = "[%(asctime)s %(levelname)s] %(message)s"
    logging.basicConfig(level=logging.WARNING, format=format)
    logger = logging.getLogger()

    args = parse_args()

    # set logging level
    if args.verbose > 1:
        set_log_debug(logger)
    elif args.verbose == 1:
        set_log_info(logger)

    cls = OfxBackfiller(settings.STATEMENTS_SAVE_PATH)
    cls.run()

if __name__ == "__main__":
    main()
