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
from io import BytesIO
from pytz import UTC

from biweeklybudget.vendored.ofxparse import OfxParser
from sqlalchemy.exc import InvalidRequestError, IntegrityError

from biweeklybudget import settings
from biweeklybudget.cliutils import set_log_debug, set_log_info
from biweeklybudget.ofxapi import apiclient
from biweeklybudget.ofxapi.exceptions import DuplicateFileException

logger = logging.getLogger(__name__)


class OfxBackfiller(object):
    """
    Class to backfill OFX in database from files on disk.
    """

    def __init__(self, client, savedir):
        """
        Initialize the OFX Backfiller.

        :param client: API client
        :type client: Instance of :py:class:`~.OfxApiLocal` or
          :py:class:`~.OfxApiRemote`
        :param savedir: directory/path to save statements in
        :type savedir: str
        """
        logger.info('Initializing OfxBackfiller with savedir=%s', savedir)
        self.savedir = savedir
        self._client = client

    def run(self):
        """
        Main entry point - run the backfill.
        """
        logger.debug('Checking for Accounts with statement directories')
        accounts = self._client.get_accounts()
        for acctname in sorted(accounts.keys()):
            p = os.path.join(settings.STATEMENTS_SAVE_PATH, acctname)
            data = accounts[acctname]
            if not os.path.isdir(p):
                logger.info('No statement directory for Account %d (%s)',
                            data['id'], p)
                continue
            logger.debug('Found directory %s for Account %d', p, data['id'])
            self._do_account_dir(data['id'], p)

    def _do_account_dir(self, acct_id, path):
        """
        Handle all OFX statements in a per-account directory.

        :param acct_id: account database ID
        :type acct_id: int
        :param path: absolute path to per-account directory
        :type path: str
        """
        logger.debug('Doing account %d directory (%s)', acct_id, path)
        files = {}
        for f in os.listdir(path):
            p = os.path.join(path, f)
            if not os.path.isfile(p):
                continue
            extension = p.split('.')[-1].lower()
            if extension not in ['ofx', 'qfx']:
                continue
            files[p] = os.path.getmtime(p)
        logger.debug('Found %d files for account %d', len(files), acct_id)
        # run through the files, oldest to newest
        success = 0
        already = 0
        for p in sorted(files, key=files.get):
            try:
                self._do_one_file(acct_id, p)
                success += 1
            except DuplicateFileException:
                already += 1
                logger.warning('OFX is already parsed for account; skipping')
            except (InvalidRequestError, IntegrityError, TypeError):
                raise
            except Exception:
                logger.error('Exception parsing and inserting file %s',
                             p, exc_info=True)
        logger.info('Successfully parsed and inserted %d of %d files for '
                    'account %d; %d files already in DB', success, len(files),
                    acct_id, already)

    def _do_one_file(self, acct_id, path):
        """
        Parse one OFX file and use OFXUpdater to upsert it into the DB.

        :param acct_id: Account ID number
        :type acct_id: int
        :param path: absolute path to OFX/QFX file
        :type path: str
        """
        logger.debug('Handle file %s for Account %d', path, acct_id)
        with open(path, 'rb') as fh:
            ofx_str = fh.read()
        ofx = OfxParser.parse(BytesIO(ofx_str))
        logger.debug('Parsed OFX')
        fname = os.path.basename(path)
        mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=UTC)
        self._client.update_statement_ofx(
            acct_id, ofx, mtime=mtime, filename=fname
        )
        logger.debug('Done updating')


def parse_args():
    """
    Parse command-line arguments.
    """
    p = argparse.ArgumentParser(description='Backfill OFX from disk')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    p.add_argument('-r', '--remote', dest='remote', action='store', type=str,
                   default=None,
                   help='biweeklybudget API URL to use instead of direct DB '
                        'access')
    p.add_argument('--ca-bundle', dest='ca_bundle', action='store', type=str,
                   default=None,
                   help='Path to CA certificate bundle file or directory to '
                        'use for SSL verification')
    p.add_argument('--client-cert', dest='client_cert', action='store',
                   type=str, default=None,
                   help='path to client certificate to use for SSL client '
                        'cert auth')
    p.add_argument('--client-key', dest='client_key', action='store',
                   type=str, default=None,
                   help='path to unencrypted client key to use for SSL client '
                        'cert auth, if key is not contained in the cert file')
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

    client = apiclient(
        api_url=args.remote, ca_bundle=args.ca_bundle,
        client_cert=args.client_cert, client_key=args.client_key
    )
    cls = OfxBackfiller(client, settings.STATEMENTS_SAVE_PATH)
    cls.run()

if __name__ == "__main__":
    main()
