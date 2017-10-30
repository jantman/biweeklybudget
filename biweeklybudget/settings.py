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
import importlib
import logging
from datetime import timedelta, datetime
from babel.numbers import validate_currency, UnknownCurrencyError
from babel import Locale, UnknownLocaleError

logger = logging.getLogger(__name__)

_REQUIRED_VARS = [
    'DB_CONNSTRING',
    'DEFAULT_ACCOUNT_ID',
    'PAY_PERIOD_START_DATE',
    'RECONCILE_BEGIN_DATE',
    'STALE_DATA_TIMEDELTA',
    'CURRENCY_CODE'
]

_DATE_VARS = [
    'PAY_PERIOD_START_DATE',
    'RECONCILE_BEGIN_DATE'
]
_TIMEDELTA_VARS = [
    'STALE_DATA_TIMEDELTA'
]
_INT_VARS = [
    'DEFAULT_ACCOUNT_ID',
    'FUEL_BUDGET_ID',
    'BIWEEKLYBUDGET_TEST_TIMESTAMP'
]
_STRING_VARS = [
    'DB_CONNSTRING',
    'STATEMENTS_SAVE_PATH',
    'TOKEN_PATH',
    'VAULT_ADDR',
    'LOCALE_NAME',
    'CURRENCY_CODE'
]

#: A `RFC 5646 / BCP 47 <https://tools.ietf.org/html/bcp47>`_ Language Tag
#: with a Region suffix to use for number (currency) formatting, i.e. "en_US",
#: "en_GB", "de_DE", etc. If this is not specified (None), it will be looked up
#: from environment variables in the following order: LC_ALL, LC_MONETARY, LANG.
#: If none of those variables are set to a valid locale name (not including
#: the "C" locale, which does not specify currency formatting) and this variable
#: is not set, the application will default to "en_US". This setting only
#: effects how monetary values are displayed in the UI, logs, etc. For further
#: information, see
#: :ref:`Currency Formatting and Localization <app_usage.l10n>`.
LOCALE_NAME = None

#: An `ISO 4217 <https://en.wikipedia.org/wiki/ISO_4217>`_ Currency Code
#: specifying the currency to use for all monetary amounts, i.e. "USD", "EUR",
#: etc. This setting only effects how monetary values are displayed in the UI,
#: logs, etc. Currently defaults to "USD". For further information, see
#: :ref:`Currency Formatting and Localization <app_usage.l10n>`.
CURRENCY_CODE = 'USD'

#: string - SQLAlchemy database connection string. See the
#: :ref:`SQLAlchemy Database URLS docs <sqlalchemy:database_urls>`
#: for further information.
DB_CONNSTRING = None

#: int - Account ID to show first in dropdown lists. This must be the database
#: ID of a valid account.
DEFAULT_ACCOUNT_ID = 1

#: int - Budget ID to select as default when inputting Fuel Log entries. This
#: must be the database ID of a valid budget.
FUEL_BUDGET_ID = 1

#: :py:class:`datetime.date` - The starting date of one pay period (generally
#: the first pay period represented in data in this app). The dates of all pay
#: periods will be determined based on an interval from this date. This must
#: be specified in Y-m-d format (i.e. parsable by
#: :py:meth:`datetime.datetime.strptime` with ``%Y-%m-%d`` format).
PAY_PERIOD_START_DATE = None

#: :py:class:`datetime.date` - When listing unreconciled transactions that need
#: to be reconciled, any transaction before this date will be ignored. This must
#: be specified in Y-m-d format (i.e. parsable by
#: :py:meth:`datetime.datetime.strptime` with ``%Y-%m-%d`` format).
RECONCILE_BEGIN_DATE = None

#: :py:class:`datetime.timedelta` - Time interval beyond which OFX data for
#: accounts will be considered old/stale. This must be specified as a number
#: (integer) that will be converted to a number of days.
STALE_DATA_TIMEDELTA = timedelta(days=2)

#: string - *(optional)* Filesystem path to download OFX statements to, and for
#: backfill_ofx to read them from.
STATEMENTS_SAVE_PATH = None

#: string - *(optional)* Filesystem path to read Vault token from, for OFX
#: credentials.
TOKEN_PATH = None

#: string - *(optional)* Address to connect to Vault at, for OFX credentials.
VAULT_ADDR = None

#: int - FOR ACCEPTANCE TESTS ONLY - This is used to "fudge" the current time
#: to the specified integer timestamp. Used for acceptance tests only. Do NOT
#: set this outside of acceptance testing.
BIWEEKLYBUDGET_TEST_TIMESTAMP = None

if 'SETTINGS_MODULE' in os.environ:
    logger.debug('Attempting to import settings module %s',
                 os.environ['SETTINGS_MODULE'])
    modname = os.environ.get('SETTINGS_MODULE')
    m = importlib.import_module(modname)
    module_dict = m.__dict__
    try:
        to_import = m.__all__
    except AttributeError:
        to_import = [name for name in module_dict if not name.startswith('_')]
    v = {name: module_dict[name] for name in to_import}
    logger.debug('Import from SETTINGS_MODULE: %s', v)
    globals().update(v)
else:
    logger.debug('SETTINGS_MODULE not defined')

for varname in _STRING_VARS:
    if varname not in os.environ:
        continue
    logger.debug('Setting %S from env var: %s', varname, os.environ[varname])
    globals()[varname] = os.environ[varname]

for varname in _INT_VARS:
    if varname not in os.environ:
        continue
    try:
        value = int(os.environ[varname])
        assert os.environ[varname] == '%s' % value
    except:
        raise SystemExit('ERROR: env var %s cannot parse as int' % varname)
    logger.debug('Setting %S from env var: %s', varname, value)
    globals()[varname] = value

for varname in _TIMEDELTA_VARS:
    if varname not in os.environ:
        continue
    try:
        value = int(os.environ[varname])
        assert os.environ[varname] == '%s' % value
    except:
        raise SystemExit('ERROR: env var %s cannot parse as int' % varname)
    value = timedelta(days=value)
    logger.debug('Setting %S from env var: %s', varname, value)
    globals()[varname] = value

for varname in _DATE_VARS:
    if varname not in os.environ:
        continue
    try:
        value = datetime.strptime(os.environ[varname], '%Y-%m-%d')
    except:
        raise SystemExit('ERROR: env var %s cannot parse as %Y-%m-%d' % varname)
    logger.debug('Setting %S from env var: %s', varname, value)
    globals()[varname] = value

for varname in _REQUIRED_VARS:
    if globals().get(varname, None) is None:
        raise SystemExit(
            'ERROR: setting or environment variable "%s" must be set' % varname
        )

# Handle the "LOCALE_NAME" variable special logic for default if not specified.
if LOCALE_NAME is None or LOCALE_NAME == 'C' or LOCALE_NAME.startswith('C.'):
    logger.debug('LOCALE_NAME unset or C locale')
    for varname in ['LC_ALL', 'LC_MONETARY', 'LANG']:
        val = os.environ.get(varname, '').strip()
        if val != '' and val != 'C' and not val.startswith('C.'):
            logger.debug(
                'Setting LOCALE_NAME to %s from env var %s', val, varname
            )
            LOCALE_NAME = val
            break
    if LOCALE_NAME is None:
        logger.debug('LOCALE_NAME not set; defaulting to en_US')
        LOCALE_NAME = 'en_US'

# Check for a valid locale
try:
    Locale.parse(LOCALE_NAME)
except UnknownLocaleError:
    raise SystemExit(
        'ERROR: LOCALE_NAME setting of "%s" is not a valid BCP 47 Language Tag.'
        ' See <https://tools.ietf.org/html/bcp47> for more information.' %
        LOCALE_NAME
    )

# Check for a valid currency code
try:
    validate_currency(CURRENCY_CODE)
except UnknownCurrencyError:
    raise SystemExit(
        'ERROR: CURRENCY_CODE setting of "%s" is not a valid currency code. See'
        ' <https://en.wikipedia.org/wiki/ISO_4217> for more information and '
        'a list of valid codes.' % CURRENCY_CODE
    )

logger.debug('Done loading settings.')
