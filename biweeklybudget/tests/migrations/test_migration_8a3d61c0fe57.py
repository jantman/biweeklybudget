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

ADDED = 'omit_from_graphs'

#: values of the existing columns, which must survive both directions
KEPT = {
    'id': 8357,
    'name': 'MigOmitAcct',
    'description': 'Account for the omit_from_graphs migration test',
    'acct_type': 'Bank',
}


@pytest.mark.migrations
class TestAddAccountOmitFromGraphs(MigrationTest):
    """
    Test for revision 8a3d61c0fe57 - add Account.omit_from_graphs.
    """

    migration_rev = '8a3d61c0fe57'

    def data_setup(self, engine):
        """insert an Account that exists before the column does"""
        with engine.begin() as conn:
            conn.execute(
                text(
                    'INSERT INTO accounts (id, name, description, acct_type, '
                    'is_active, reconcile_trans) VALUES (:id, :name, '
                    ':description, :acct_type, 1, 1);'
                ),
                KEPT
            )

    def _columns_and_row(self, engine):
        with engine.connect() as conn:
            columns = list(conn.execute(
                text('SELECT * FROM accounts WHERE 1=2;')
            ).keys())
            row = conn.execute(
                text('SELECT * FROM accounts WHERE id=:i;'),
                {'i': KEPT['id']}
            ).mappings().one()
        return columns, dict(row)

    def _assert_kept(self, row):
        for k, v in KEPT.items():
            assert row[k] == v, k
        assert row['is_active'] == 1

    def verify_before(self, engine):
        """before forward migration, and after reverse"""
        columns, row = self._columns_and_row(engine)
        assert ADDED not in columns
        self._assert_kept(row)

    def verify_after(self, engine):
        """after forward migration"""
        columns, row = self._columns_and_row(engine)
        assert ADDED in columns
        # An Account that predates the column gets NULL, and NULL means "not
        # omitted" everywhere it is read. This is what makes the upgrade a
        # no-op for which Accounts are plotted, and it is why the reading
        # filter must be spelled ``IS NOT true`` rather than ``= false``.
        # See GitHub issue #357.
        assert row[ADDED] is None
        self._assert_kept(row)
        # a NULL flag is selected by the filter the chart view uses, and would
        # not be selected by the ``= false`` spelling
        with engine.connect() as conn:
            found = conn.execute(
                text(
                    'SELECT id FROM accounts '
                    'WHERE omit_from_graphs IS NOT true AND id=:i;'
                ),
                {'i': KEPT['id']}
            ).fetchall()
            assert len(found) == 1
            not_found = conn.execute(
                text(
                    'SELECT id FROM accounts '
                    'WHERE omit_from_graphs = false AND id=:i;'
                ),
                {'i': KEPT['id']}
            ).fetchall()
            assert not_found == []
        # and the new column accepts both values
        for value, expected in [('true', 1), ('false', 0)]:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        'UPDATE accounts SET omit_from_graphs=%s '
                        'WHERE id=:i;' % value
                    ),
                    {'i': KEPT['id']}
                )
            _, row = self._columns_and_row(engine)
            assert row[ADDED] == expected
        # leave it as it was found, so verify_before holds after the reverse
        with engine.begin() as conn:
            conn.execute(
                text('UPDATE accounts SET omit_from_graphs=NULL WHERE id=:i;'),
                {'i': KEPT['id']}
            )
