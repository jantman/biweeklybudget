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
from datetime import timedelta

# Address to connect to Vault at, for OFX credentials
VAULT_ADDR = 'http://127.0.0.1:8200'

# Path to read Vault token from
TOKEN_PATH = 'vault_token.txt'

# Path to download OFX statements to, and read them from
STATEMENTS_SAVE_PATH = os.path.expanduser('~/ofx')

# MySQL connection settings
if 'MYSQL_CONNSTRING' in os.environ:
    MYSQL_CONNSTRING = os.environ['MYSQL_CONNSTRING']
else:
    MYSQL_DBNAME = 'budget'
    MYSQL_HOST = 'localhost'
    MYSQL_PORT = 3306
    MYSQL_USER = 'budgetUser'
    MYSQL_PASS = 'budgetPassword'
    MYSQL_CONNSTRING = 'mysql+pymysql://{}:{}@{}:{}/{}?charset=utf8mb4'.format(
        MYSQL_USER, MYSQL_PASS, MYSQL_HOST, MYSQL_PORT, MYSQL_DBNAME
    )

STALE_DATA_TIMEDELTA = timedelta(days=2)
