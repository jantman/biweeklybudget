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
from decimal import Decimal
from datetime import date

from biweeklybudget.tests.migrations.migration_test_helpers import MigrationTest

logger = logging.getLogger(__name__)


@pytest.mark.migrations
class TestAddSalesTaxField(MigrationTest):
    """
    Test for revision d01774fa3ae3
    """

    migration_rev = 'd01774fa3ae3'

    def data_setup(self, engine):
        """method to setup sample data in empty tables"""
        return

    def verify_before(self, engine):
        """method to verify data before forward migration, and after reverse"""
        conn = engine.connect()
        columns = conn.execute('SELECT * FROM transactions WHERE 1=2;').keys()
        conn.close()
        assert 'sales_tax' not in columns

    def verify_after(self, engine):
        """method to verify data after forward migration"""
        conn = engine.connect()
        columns = conn.execute('SELECT * FROM transactions WHERE 1=2;').keys()
        conn.close()
        assert 'sales_tax' in columns
