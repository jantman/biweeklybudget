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
import json

from alembic import command
from sqlalchemy import create_engine
from sqlalchemydiff.comparer import Comparer

from alembicverify.util import (
    get_current_revision,
    get_head_revision,
    prepare_schema_from_migrations,
)
from biweeklybudget.models.base import Base

import biweeklybudget.tests.migrations.alembic_helpers as ah

logger = logging.getLogger(__name__)


def prepare_schema_from_models(uri, sqlalchemy_base):
    """Create all tables of ``sqlalchemy_base`` in the database at ``uri``.

    sqlalchemy-diff removed its ``util.prepare_schema_from_models`` helper in
    1.0.0; this is a local equivalent.
    """
    engine = create_engine(uri)
    try:
        sqlalchemy_base.metadata.create_all(engine)
    finally:
        engine.dispose()


@pytest.mark.migrations
def test_upgrade_and_downgrade(uri_left, alembic_config_left):
    """Test all migrations up and down.

    Tests that we can apply all migrations from a brand new empty
    database, and also that we can remove them all.
    """
    alembic_config_left.set_section_option('bwbTest', 'connstring', uri_left)
    logger.info('Set alembic config bwbTest.connstring to: %s', uri_left)
    ah.load_premigration_sql(uri_left)
    engine, script = prepare_schema_from_migrations(
        uri_left, alembic_config_left
    )

    head = get_head_revision(alembic_config_left, engine, script)
    current = get_current_revision(alembic_config_left, engine, script)

    assert head == current

    while current is not None:
        command.downgrade(alembic_config_left, '-1')
        current = get_current_revision(alembic_config_left, engine, script)


@pytest.mark.migrations
def test_model_and_migration_schemas_are_the_same(
        uri_left, uri_right, alembic_config_left):
    """Compares the database schema obtained with all migrations against the
    one we get out of the models.
    """
    alembic_config_left.set_section_option('bwbTest', 'connstring', uri_left)
    logger.info('Set alembic config bwbTest.connstring to: %s', uri_left)
    ah.load_premigration_sql(uri_left)
    prepare_schema_from_migrations(uri_left, alembic_config_left)
    prepare_schema_from_models(uri_right, Base)

    result = Comparer.from_params(uri_left, uri_right).compare(
        ignores=[
            'alembic_version',
            # for some reason, these constraints don't diff correctly,
            # likely due to creation order
            'accounts.check_constraints.CONSTRAINT_1',
            'accounts.check_constraints.CONSTRAINT_2',
            'accounts.check_constraints.CONSTRAINT_3',
            'accounts.check_constraints.CONSTRAINT_4',
            'budgets.check_constraints.CONSTRAINT_1',
            'budgets.check_constraints.CONSTRAINT_2',
            'budgets.check_constraints.CONSTRAINT_3',
            'budgets.check_constraints.CONSTRAINT_4',
            'ofx_trans.check_constraints.CONSTRAINT_1',
            'ofx_trans.check_constraints.CONSTRAINT_2',
            'ofx_trans.check_constraints.CONSTRAINT_3',
            'ofx_trans.check_constraints.CONSTRAINT_4',
            'ofx_trans.check_constraints.CONSTRAINT_5',
            'reconcile_rules.check_constraints.CONSTRAINT_1',
            'scheduled_transactions.check_constraints.CONSTRAINT_1',
        ]
    )

    assert result.is_match is True, \
        'Differences (left is migrations, right is models):\n' \
        '%s' % json.dumps(
            result.errors, sort_keys=True, indent=4, separators=(',', ': ')
        )
