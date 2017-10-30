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
from biweeklybudget import settings
from datetime import datetime
import pytz
from contextlib import contextmanager
from babel.numbers import format_currency

logger = logging.getLogger(__name__)


def fix_werkzeug_logger():
    """
    Remove the werkzeug logger StreamHandler (call from ``app.py``).

    With Werkzeug at least as of 0.12.1, werkzeug._internal._log sets up its own
    StreamHandler if logging isn't already configured. Because we're using
    the ``flask`` command line wrapper, that will ALWAYS be imported (and
    executed) before we can set up our own logger. As a result, to fix the
    duplicate log messages, we have to go back and remove that StreamHandler.
    """
    wlog = logging.getLogger('werkzeug')
    logger.info('Removing handlers from "werkzeug" logger')
    for h in wlog.handlers:
        wlog.removeHandler(h)


def fmt_currency(amt):
    """
    Using :py:attr:`~biweeklybudget.settings.LOCALE_NAME` and
    :py:attr:`~biweeklybudget.settings.CURRENCY_CODE`, return ``amt`` formatted
    as currency.

    :param amt: The amount to format; any numeric type.
    :return: ``amt`` formatted for the appropriate locale and currency
    :rtype: str
    """
    return format_currency(
        amt, settings.CURRENCY_CODE, locale=settings.LOCALE_NAME
    )


def dtnow():
    """
    Return the current datetime as a timezone-aware DateTime object in UTC.

    :return: current datetime
    :rtype: datetime.datetime
    """
    # This is for acceptance tests... :(
    if settings.BIWEEKLYBUDGET_TEST_TIMESTAMP is not None:
        return datetime.fromtimestamp(
            int(settings.BIWEEKLYBUDGET_TEST_TIMESTAMP), pytz.utc
        )
    return datetime.utcnow().replace(tzinfo=pytz.utc)


def decode_json_datetime(d):
    """
    Return a datetime.datetime for a datetime that was serialized with
    :py:class:`~.MagicJSONEncoder`.

    :param d: dict from deserialized JSON
    :type d: dict
    :return: datetime represented by dict
    :rtype: datetime.datetime
    """
    return datetime(
        d['year'], d['month'], d['date'], d['hour'], d['minute'], d['second'],
        tzinfo=pytz.timezone(d['tzname'])
    )


def date_suffix(n):
    """
    Given an integer day of month (1 <= n <= 31), return that number with the
    appropriate suffix (st|nd|rd|th).

    From: http://stackoverflow.com/a/5891598/211734

    :param n: Integer day of month
    :type n: int
    :return: n with the appropriate suffix
    :rtype: str
    """
    return 'th' if 11 <= n <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(
        n % 10, 'th'
    )


@contextmanager
def in_directory(path):
    pwd = os.getcwd()
    os.chdir(path)
    yield os.path.abspath(path)
    os.chdir(pwd)


class SecretMissingException(Exception):

    def __init__(self, path):
        self.path = path

    def __str__(self):
        return repr(self.path)


class Vault(object):
    """
    Provides simpler access to Vault
    """

    def __init__(self, addr=settings.VAULT_ADDR,
                 token_path=settings.TOKEN_PATH):
        """
        Connect to Vault and maintain connection

        :param addr: URL to connect to Vault at
        :type addr: str
        :param token_path: path to read Vault token from
        :type token_path: str
        """
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
