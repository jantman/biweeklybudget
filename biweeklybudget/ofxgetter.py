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
from copy import deepcopy
from io import StringIO
import importlib

from ofxparse import OfxParser
from ofxclient.account import Account as OfxClientAccount

from biweeklybudget.utils import Vault
from biweeklybudget import settings
from biweeklybudget.models.account import Account
from biweeklybudget.db import init_db, db_session, cleanup_db
from biweeklybudget.ofxupdater import OFXUpdater
from biweeklybudget.cliutils import set_log_debug, set_log_info
from biweeklybudget.models.ofx_transaction import OFXTransaction

logger = logging.getLogger(__name__)

# suppress requests logging
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)
requests_log.propagate = True


class OfxGetter(object):

    @staticmethod
    def accounts():
        """
        Return a sorted list of all Account objects that are for ofxgetter.
        """
        return [a for a in db_session.query(
                Account).filter(
            Account.for_ofxgetter).order_by(Account.name).all()
        ]

    def __init__(self, savedir='./'):
        self.savedir = savedir
        self._account_data = {}
        for acct in self.accounts():
            if acct.vault_creds_path is None and acct.ofxgetter_config == {}:
                continue
            self._account_data[acct.name] = {
                'vault_path': acct.vault_creds_path,
                'config': acct.ofxgetter_config,
                'id': acct.id,
                'cat_memo': acct.ofx_cat_memo_to_name
            }
        logger.debug('Initialized with data for %d accounts',
                     len(self._account_data))
        self._accounts = {}
        self.vault = Vault()
        for acct_name in self._account_data.keys():
            data = self._account_data[acct_name]['config']
            vault_path = self._account_data[acct_name]['vault_path']
            logger.debug('Getting secrets for account %s', acct_name)
            secrets = self.vault.read(vault_path)
            data['institution']['password'] = secrets['password']
            data['institution']['username'] = secrets['username']
            if 'class_name' not in data:
                self._accounts[acct_name] = OfxClientAccount.deserialize(data)
        logger.debug('Initialized %d accounts', len(self._accounts))
        self.now_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    def get_ofx(self, account_name, write_to_file=True, days=30):
        """
        Download OFX from the specified account. Return it as a string.

        :param account_name: account name to download
        :type account_name: str
        :param write_to_file: if True, also write to a file named
          "<account_name>_<date stamp>.ofx"
        :type write_to_file: bool
        :param days: number of days of data to download
        :type days: int
        :return: OFX string
        :rtype: str
        """
        fname = None
        logger.debug('Downloading OFX for account: %s', account_name)
        if 'class_name' in self._account_data[account_name]['config']:
            ofxdata = self._get_ofx_scraper(account_name, days=days)
        else:
            acct = self._accounts[account_name]
            logger.debug(
                'Disabling logging for ofxclient, which has bad logging'
            )
            oldlvl = logging.getLogger().getEffectiveLevel()
            logging.getLogger().setLevel(logging.WARNING)
            ofxdata = acct.download(days=days).read()
            logging.getLogger().setLevel(oldlvl)
            logger.debug('Re-enabling ofxclient logging')
        if write_to_file:
            fname = self._write_ofx_file(account_name, ofxdata)
        self._ofx_to_db(account_name, fname, ofxdata)
        return ofxdata

    def _ofx_to_db(self, account_name, fname, ofxdata):
        """
        Put OFX Data to the DB

        :param account_name: account name to download
        :type account_name: str
        :param ofxdata: raw OFX data
        :type ofxdata: str
        :param fname: filename OFX was written to
        :type fname: str
        """
        logger.debug('Parsing OFX')
        ofx = OfxParser.parse(StringIO(ofxdata))
        logger.debug('Instantiating OFXUpdater')
        updater = OFXUpdater(
            self._account_data[account_name]['id'],
            account_name,
            cat_memo=self._account_data[account_name]['cat_memo']
        )
        logger.debug('Updating OFX in DB')
        updater.update(ofx, filename=fname)
        count_new = 0
        count_upd = 0
        for obj in db_session.dirty:
            if isinstance(obj, OFXTransaction):
                count_upd += 1
        for obj in db_session.new:
            if isinstance(obj, OFXTransaction):
                count_new += 1
        db_session.commit()
        logger.info('Account "%s" - inserted %d new OFXTransaction(s), updated '
                    '%d existing OFXTransaction(s)',
                    account_name, count_new, count_upd)
        logger.debug('Done updating OFX in DB')

    def _get_ofx_scraper(self, account_name, days=30):
        """
        Get OFX via a ScreenScraper subclass.

        :param account_name: account name
        :type account_name: str
        :param days: number of days of data to download
        :type days: int
        :return: OFX string
        :rtype: str
        """
        data = self._account_data[account_name]['config']
        clsname = data['class_name']
        modname = data['module_name']
        logger.debug('Scraper - getting class %s from module %s',
                     clsname, modname)
        cls = getattr(
            importlib.import_module(modname),
            clsname
        )
        logger.debug('Getting secrets for account %s', account_name)
        secrets = self.vault.read(
            self._account_data[account_name]['vault_path']
        )
        if 'kwargs' in data:
            kwargs = deepcopy(data['kwargs'])
        else:
            kwargs = {}
        kwargs['username'] = secrets['username']
        kwargs['password'] = secrets['password']
        kwargs['savedir'] = os.path.join(self.savedir, account_name)
        acct = cls(**kwargs)
        ofxdata = acct.run()
        return ofxdata

    def _write_ofx_file(self, account_name, ofxdata):
        """
        Write OFX data to a file.

        :param account_name: account name
        :type account_name: str
        :param ofxdata: raw OFX data string
        :type ofxdata: str
        :returns: name of the file that was written
        :rtype: str
        """
        if not os.path.exists(os.path.join(self.savedir, account_name)):
            os.makedirs(os.path.join(self.savedir, account_name))
        fname = '%s_%s.ofx' % (account_name, self.now_str)
        fpath = os.path.join(self.savedir, account_name, fname)
        logger.debug('Writing %d bytes of OFX to: %s', len(ofxdata), fpath)
        with open(fpath, 'w') as fh:
            fh.write(ofxdata)
        logger.debug('Wrote OFX data to: %s', fpath)
        return fname


def parse_args():
    p = argparse.ArgumentParser(description='Download OFX transactions')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    p.add_argument('-l', '--list-accts', dest='list', action='store_true',
                   help='list accounts and exit')
    p.add_argument('ACCOUNT_NAME', type=str, action='store', default=None,
                   nargs='?',
                   help='Account name; omit to download all accounts')
    args = p.parse_args()
    return args


def main():
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
    if args.verbose <= 1:
        # if we're not in verbose mode, suppress routine logging for cron
        lgr = logging.getLogger('alembic')
        lgr.setLevel(logging.WARNING)
        lgr = logging.getLogger('biweeklybudget.db')
        lgr.setLevel(logging.WARNING)

    atexit.register(cleanup_db)
    init_db()

    if args.list:
        for k in OfxGetter.accounts():
            print(k.name)
        raise SystemExit(0)

    getter = OfxGetter(settings.STATEMENTS_SAVE_PATH)
    if args.ACCOUNT_NAME is not None:
        getter.get_ofx(args.ACCOUNT_NAME)
        raise SystemExit(0)
    # else all of them
    total = 0
    success = 0
    for acct in OfxGetter.accounts():
        try:
            total += 1
            getter.get_ofx(acct.name)
            success += 1
        except Exception:
            logger.error(
                'Failed to download account %s', acct.name, exc_info=True
            )
    if success != total:
        logger.warning('Downloaded %d of %d accounts', success, total)
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
