"""
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
import string
import logging

import plaid

from biweeklybudget import settings
from datetime import datetime
import pytz
from contextlib import contextmanager
from decimal import Decimal
from babel import Locale
from babel.numbers import format_currency, get_currency_symbol, parse_decimal
from plaid import Configuration, ApiClient, Environment
from plaid.api.plaid_api import PlaidApi

logger = logging.getLogger(__name__)

#: Unicode space characters that users (or their clipboards) may use in place of
#: a plain ASCII space, most commonly as a digit grouping separator.
_UNICODE_SPACES = [
    '\t',
    '\u00a0',  # NO-BREAK SPACE
    '\u2007',  # FIGURE SPACE
    '\u2009',  # THIN SPACE
    '\u202f',  # NARROW NO-BREAK SPACE
]


class CurrencyParseError(ValueError):
    """
    Raised by :py:func:`~.parse_currency` when a string cannot be unambiguously
    interpreted as a currency amount.

    Subclasses :py:exc:`ValueError` so that callers which already catch
    ``ValueError`` continue to work.
    """
    pass


def plaid_client() -> PlaidApi:
    """
    Return an initialized Plaid API client instance.
    """
    logger.debug('Getting Plaid client instance')
    assert settings.PLAID_CLIENT_ID is not None
    assert settings.PLAID_SECRET is not None
    assert settings.PLAID_ENV is not None
    configuration = Configuration(
        host=getattr(Environment, settings.PLAID_ENV),
        api_key={
            'clientId': settings.PLAID_CLIENT_ID,
            'secret': settings.PLAID_SECRET,
        }
    )
    api_client = ApiClient(configuration)
    client = PlaidApi(api_client)
    return client


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


def _currency_separators():
    """
    Return the digit grouping separator and decimal separator for
    :py:attr:`~biweeklybudget.settings.LOCALE_NAME`, i.e. ``(',', '.')`` for
    ``en_US`` and ``('.', ',')`` for ``de_DE``.

    :return: 2-tuple of (grouping separator, decimal separator)
    :rtype: tuple
    """
    symbols = Locale.parse(settings.LOCALE_NAME).number_symbols
    # Babel >= 2.12 nests number symbols under the numbering system.
    if 'latn' in symbols:
        symbols = symbols['latn']
    return symbols.get('group', ','), symbols.get('decimal', '.')


def parse_currency(value):
    """
    Parse a user-entered currency string into an exact
    :py:class:`decimal.Decimal`.

    This is the single authority for turning user input into a number; it is
    the counterpart to :py:func:`~.fmt_currency`. All formatting conventions
    come from :py:attr:`~biweeklybudget.settings.LOCALE_NAME` and
    :py:attr:`~biweeklybudget.settings.CURRENCY_CODE`, so support for another
    locale is a settings change and not a code change.

    For ``en_US``, all of the following parse to ``Decimal('1234.56')``::

        1234.56   1,234.56   1 234.56   $1,234.56   $ 1,234.56   1,234.56 $

    and all of these parse to ``Decimal('-1234.56')``::

        -1,234.56   -$1,234.56   (1,234.56)   ($1,234.56)

    Bare integers (``123``) are accepted. Input that cannot be interpreted
    unambiguously - including plausible-looking but invalidly grouped values
    such as ``10,00`` or ``1,23,4.56`` - raises
    :py:exc:`~.CurrencyParseError` rather than returning a guess. This matters:
    lenient parsers read ``10,00`` as ``1000``, which would silently corrupt a
    financial record.

    :param value: the user-supplied string to parse
    :type value: str
    :return: the exact decimal value of ``value``
    :rtype: decimal.Decimal
    :raises: CurrencyParseError if ``value`` cannot be interpreted
    """
    if not isinstance(value, str):
        raise CurrencyParseError(
            'Cannot parse non-string currency value: %r' % value
        )
    s = value
    for space in _UNICODE_SPACES:
        s = s.replace(space, ' ')
    s = s.strip()
    negative = False
    if s.startswith('(') and s.endswith(')'):
        negative = True
        s = s[1:-1].strip()
    symbol = get_currency_symbol(
        settings.CURRENCY_CODE, locale=settings.LOCALE_NAME
    )
    # Strip the currency symbol, ISO code and sign repeatedly until the string
    # stops changing. A single pass is not enough: for "-$1,234.56", taking the
    # sign first leaves "$1,234.56", which the decimal parser rejects.
    changed = True
    while changed and s != '':
        changed = False
        for token in [symbol, settings.CURRENCY_CODE]:
            if token == '':
                continue
            if s.startswith(token):
                s = s[len(token):].strip()
                changed = True
            elif s.endswith(token):
                s = s[:-len(token)].strip()
                changed = True
        if s.startswith('-') or s.startswith('+'):
            if s[0] == '-':
                negative = not negative
            s = s[1:].strip()
            changed = True
    if s == '':
        raise CurrencyParseError('Invalid currency value: "%s"' % value)
    group_sep, decimal_sep = _currency_separators()
    # Rewrite spaces used as grouping separators into the locale's own grouping
    # separator, rather than simply deleting them, so that the grouping check
    # below applies to space-separated input too. Deleting them would read
    # "1 2 3" as 123.
    s = s.replace(' ', group_sep)
    # Only digits and the locale's two separators may remain. babel's
    # parse_decimal() falls back to Decimal(), which happily accepts "1e5",
    # "nan" and "inf"; none of those are amounts a user meant to type.
    if not set(s) <= set(string.digits + group_sep + decimal_sep):
        raise CurrencyParseError('Invalid currency value: "%s"' % value)
    try:
        parsed = parse_decimal(s, locale=settings.LOCALE_NAME, strict=True)
    except Exception as ex:
        raise CurrencyParseError(
            'Invalid currency value: "%s" (%s)' % (value, ex)
        )
    if not isinstance(parsed, Decimal):
        # defensive; babel returns Decimal, but never hand back a float
        parsed = Decimal(str(parsed))
    if negative:
        parsed = -parsed
    return parsed


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
