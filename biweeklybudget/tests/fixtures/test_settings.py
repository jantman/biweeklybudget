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
from datetime import timedelta, date

#: Address to connect to Vault at, for OFX credentials
VAULT_ADDR = 'http://127.0.0.1:8200'

#: Path to read Vault token from, for OFX credentials
TOKEN_PATH = 'vault_token.txt'

#: Path to download OFX statements to, and for backfill_ofx to read them from
STATEMENTS_SAVE_PATH = os.path.expanduser('~/ofx')

#: SQLAlchemy database connection string. Note that the value given in
#: generated documentation is the value used in CI builds, not the real default.
DB_CONNSTRING = None

# MySQL connection settings
if 'DB_CONNSTRING' in os.environ:
    DB_CONNSTRING = os.environ['DB_CONNSTRING']
else:
    MYSQL_DBNAME = 'budget'
    MYSQL_HOST = 'localhost'
    MYSQL_PORT = 3306
    MYSQL_USER = 'budgetUser'
    MYSQL_PASS = 'budgetPassword'
    DB_CONNSTRING = 'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4'.format(
        MYSQL_USER, MYSQL_PASS, MYSQL_HOST, MYSQL_PORT, MYSQL_DBNAME
    )

#: :py:class:`datetime.timedelta` beyond which OFX data will be considered old
STALE_DATA_TIMEDELTA = timedelta(days=2)

#: int - FOR ACCEPTANCE TESTS ONLY - This is used to "fudge" the current time
#: to the specified integer timestamp. Used for acceptance tests only. Do NOT
#: set this outside of acceptance testing.
# Tests run as 1501223084 - Friday, July 28, 2017 6:24:44 AM UTC
BIWEEKLYBUDGET_TEST_TIMESTAMP = os.environ.get('BIWEEKLYBUDGET_TEST_TIMESTAMP')
PAY_PERIOD_START_DATE = date(2017, 7, 21)

#: When listing unreconciled transactions that need to be reconciled, any
#: :py:class:`~.OFXTransaction` before this date will be ignored.
RECONCILE_BEGIN_DATE = date(2017, 1, 1)

#: Account ID to show first in dropdown lists
DEFAULT_ACCOUNT_ID = 1

#: int - Budget ID to select as default when inputting Fuel Log entries. This
#: must be the database ID of a valid budget.
FUEL_BUDGET_ID = 2

#: Plaid Client ID
PLAID_CLIENT_ID = os.environ.get('PLAID_CLIENT_ID', 'plaidCID')

#: Plaid Secret (client secret)
PLAID_SECRET = os.environ.get('PLAID_SECRET', 'plaidSecret')

#: Plaid environment name. Use 'sandbox' to test with Plaid's Sandbox
#: environment (username: user_good, password: pass_good). Use `development` to
#: test with live users and credentials and `production` to go live
PLAID_ENV = 'Sandbox'

#: PLAID_PRODUCTS is a comma-separated list of products to use when initializing
#: Link. Note that this list must contain 'assets' in order for the app to be
#: able to create and retrieve asset reports.
PLAID_PRODUCTS = 'transactions'

#: PLAID_COUNTRY_CODES is a comma-separated list of countries for which users
#: will be able to select institutions from.
PLAID_COUNTRY_CODES = 'US'

#: PLAID_USER_ID is a unique per-user ID for users of Plaid applications.
#: Since this is a single-user app, we just hard-code to "1"
PLAID_USER_ID = '1'
