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

REMOVED = ['ofx_cat_memo_to_name', 'vault_creds_path', 'ofxgetter_config_json']

#: values of the columns that are kept, which must survive both directions
KEPT = {
    'name': 'MigAcct',
    'description': 'Migration test account',
    'acct_type': 'Credit',
    'is_active': 1,
    'negate_ofx_amounts': 1,
    'reconcile_trans': 0,
    're_payment': '^PAYMENT',
}


@pytest.mark.migrations
class TestRemoveOfxgetterAccountFields(MigrationTest):
    """
    Test for revision c5e3a9b1d7f2 - drop Account.ofx_cat_memo_to_name,
    Account.vault_creds_path and Account.ofxgetter_config_json.
    """

    migration_rev = 'c5e3a9b1d7f2'

    def data_setup(self, engine):
        """insert an account with every removed column populated"""
        with engine.begin() as conn:
            conn.execute(
                text(
                    'INSERT INTO accounts (name, description, acct_type, '
                    'is_active, negate_ofx_amounts, reconcile_trans, '
                    're_payment, ofx_cat_memo_to_name, vault_creds_path, '
                    'ofxgetter_config_json) VALUES (:name, :description, '
                    ':acct_type, :is_active, :negate_ofx_amounts, '
                    ':reconcile_trans, :re_payment, 1, :vault, :cfg);'
                ),
                dict(KEPT, vault='secret/foo/bar', cfg='{"foo": "bar"}')
            )

    def _columns_and_row(self, engine):
        with engine.connect() as conn:
            columns = list(conn.execute(
                text('SELECT * FROM accounts WHERE 1=2;')
            ).keys())
            row = conn.execute(
                text('SELECT * FROM accounts WHERE name=:n;'),
                {'n': KEPT['name']}
            ).mappings().one()
        return columns, dict(row)

    def _assert_kept(self, row):
        for k, v in KEPT.items():
            assert row[k] == v, k

    def verify_before(self, engine):
        """before forward migration, and after reverse"""
        columns, row = self._columns_and_row(engine)
        for c in REMOVED:
            assert c in columns
        # the removed columns sit where the base schema put them
        assert columns[columns.index('description') + 1:][:3] == REMOVED
        self._assert_kept(row)

    def verify_after(self, engine):
        """after forward migration"""
        columns, row = self._columns_and_row(engine)
        for c in REMOVED:
            assert c not in columns
        self._assert_kept(row)
