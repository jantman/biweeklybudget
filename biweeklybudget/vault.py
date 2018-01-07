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
import hvac
import logging

logger = logging.getLogger(__name__)


class SecretMissingException(Exception):

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return repr(self.path)


class Vault(object):
    """
    Provides simpler access to Vault
    """

    def __init__(self, addr=None, token_path=None):
        """
        Connect to Vault and maintain connection

        :param addr: URL to connect to Vault at. If None, defaults to
          :py:attr:`biweeklybudget.settings.VAULT_ADDR`.
        :type addr: str
        :param token_path: path to read Vault token from. If None, defaults to
          :py:attr:`biweeklybudget.settings.TOKEN_PATH`.
        :type token_path: str
        """
        if addr is None and 'VAULT_ADDR' in os.environ:
            addr = os.environ['VAULT_ADDR']
        if token_path is None and 'TOKEN_PATH' in os.environ:
            token_path = os.environ['TOKEN_PATH']
        # if not in constructor or environment, use settings if possible
        if addr is None or token_path is None:
            try:
                from biweeklybudget import settings
                if addr is None:
                    addr = settings.VAULT_ADDR
                if token_path is None:
                    token_path = settings.TOKEN_PATH
            except Exception:
                logger.error('ERROR: you must either set the SETTINGS_MODULE '
                             'environment variable to use a settings module, '
                             'or export VAULT_ADDR and TOKEN_PATH environment '
                             'variables.')
                raise SystemExit(1)
        token_path = os.path.expanduser(token_path)
        logger.debug('Connecting to Vault at %s with token from %s',
                     addr, token_path)
        with open(token_path, 'r') as fh:
            tkn = fh.read().strip()
        self.conn = hvac.Client(url=addr, token=tkn)
        assert self.conn.is_authenticated()
        logger.debug('Connected to Vault')

    def read(self, secret_path):
        """
        Read and return a secret from Vault. Return only the data portion.

        :param secret_path: path to read in Vault
        :type secret_path: str
        :return: secret data
        :rtype: dict
        """
        res = self.conn.read(secret_path)
        if res is None:
            raise SecretMissingException(secret_path)
        return res['data']
