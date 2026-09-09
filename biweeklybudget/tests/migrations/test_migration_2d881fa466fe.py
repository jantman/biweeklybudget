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

import pytest
import logging
from sqlalchemy import text

from biweeklybudget.tests.migrations.migration_test_helpers import MigrationTest

logger = logging.getLogger(__name__)


@pytest.mark.migrations
class TestAddBudgetAccountsTable(MigrationTest):
    """
    Test for revision 2d881fa466fe - add the budget_accounts association table
    linking standing Budgets to the Accounts that hold their money. See GitHub
    issue #321.
    """

    migration_rev = '2d881fa466fe'

    def data_setup(self, engine):
        """method to setup sample data in empty tables"""
        return

    def _tables(self, engine):
        conn = engine.connect()
        tables = [
            row[0] for row in conn.execute(text('SHOW TABLES;')).fetchall()
        ]
        conn.close()
        return tables

    def verify_before(self, engine):
        """method to verify data before forward migration, and after reverse"""
        assert 'budget_accounts' not in self._tables(engine)

    def verify_after(self, engine):
        """method to verify data after forward migration"""
        assert 'budget_accounts' in self._tables(engine)
        conn = engine.connect()
        columns = conn.execute(
            text('SELECT * FROM budget_accounts WHERE 1=2;')
        ).keys()
        conn.close()
        assert sorted(columns) == ['account_id', 'budget_id']
