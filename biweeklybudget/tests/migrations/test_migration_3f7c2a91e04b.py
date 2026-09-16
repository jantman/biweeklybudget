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
from datetime import datetime
from sqlalchemy import text

from biweeklybudget.tests.migrations.migration_test_helpers import MigrationTest

logger = logging.getLogger(__name__)

ADDED = 'last_successful_update'

#: values of the existing columns, which must survive both directions
KEPT = {
    'item_id': 'MigItem1',
    'access_token': 'MigAccessToken',
    'institution_name': 'MigInst',
    'institution_id': 'ins_mig',
}


@pytest.mark.migrations
class TestAddPlaidItemLastSuccessfulUpdate(MigrationTest):
    """
    Test for revision 3f7c2a91e04b - add PlaidItem.last_successful_update.
    """

    migration_rev = '3f7c2a91e04b'

    def data_setup(self, engine):
        """insert a Plaid Item with every pre-existing column populated"""
        with engine.begin() as conn:
            conn.execute(
                text(
                    'INSERT INTO plaid_items (item_id, access_token, '
                    'institution_name, institution_id, last_updated) VALUES ('
                    ':item_id, :access_token, :institution_name, '
                    ':institution_id, :last_updated);'
                ),
                dict(KEPT, last_updated='2026-09-01 12:34:56')
            )

    def _columns_and_row(self, engine):
        with engine.connect() as conn:
            columns = list(conn.execute(
                text('SELECT * FROM plaid_items WHERE 1=2;')
            ).keys())
            row = conn.execute(
                text('SELECT * FROM plaid_items WHERE item_id=:i;'),
                {'i': KEPT['item_id']}
            ).mappings().one()
        return columns, dict(row)

    def _assert_kept(self, row):
        for k, v in KEPT.items():
            assert row[k] == v, k
        assert row['last_updated'] == datetime(2026, 9, 1, 12, 34, 56)

    def verify_before(self, engine):
        """before forward migration, and after reverse"""
        columns, row = self._columns_and_row(engine)
        assert ADDED not in columns
        self._assert_kept(row)

    def verify_after(self, engine):
        """after forward migration"""
        columns, row = self._columns_and_row(engine)
        assert ADDED in columns
        # the column follows last_updated, as the model declares it
        assert columns[columns.index('last_updated') + 1] == ADDED
        # existing rows get no value; none can be backfilled
        assert row[ADDED] is None
        self._assert_kept(row)
        # and the new column accepts a value
        with engine.begin() as conn:
            conn.execute(
                text(
                    'UPDATE plaid_items SET last_successful_update=:d '
                    'WHERE item_id=:i;'
                ),
                {'d': '2026-09-14 13:45:12', 'i': KEPT['item_id']}
            )
        _, row = self._columns_and_row(engine)
        assert row[ADDED] == datetime(2026, 9, 14, 13, 45, 12)
