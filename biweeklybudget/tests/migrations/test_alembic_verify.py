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
from pprint import pformat

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from alembicverify.util import (
    get_current_revision,
    get_head_revision,
    prepare_schema_from_migrations,
)

# Importing the models package is load-bearing, not incidental: it is what
# registers every model class against ``Base.metadata``. Importing
# ``biweeklybudget.models.base`` alone leaves the metadata empty, which would
# make the schema comparison below pass vacuously.
import biweeklybudget.models  # noqa
from biweeklybudget.models.base import Base

import biweeklybudget.tests.migrations.alembic_helpers as ah

logger = logging.getLogger(__name__)


@pytest.mark.migrations
def test_upgrade_and_downgrade(alembic_db_uri, alembic_config):
    """Test all migrations up and down.

    Tests that we can apply all migrations from a brand new empty
    database, and also that we can remove them all.
    """
    alembic_config.set_section_option('bwbTest', 'connstring', alembic_db_uri)
    logger.info(
        'Set alembic config bwbTest.connstring to: %s', alembic_db_uri
    )
    ah.load_premigration_sql(alembic_db_uri)
    with prepare_schema_from_migrations(
        alembic_db_uri, alembic_config
    ) as (engine, script):
        head = get_head_revision(alembic_config, engine, script)
        current = get_current_revision(alembic_config, engine, script)

        assert head == current

        while current is not None:
            command.downgrade(alembic_config, '-1')
            current = get_current_revision(alembic_config, engine, script)


@pytest.mark.migrations
def test_model_and_migration_schemas_are_the_same(
        alembic_db_uri, alembic_config):
    """Compares the database schema obtained with all migrations against the
    one we get out of the models.

    This uses Alembic's own autogenerate comparison - the same machinery that
    backs ``alembic revision --autogenerate``. A non-empty diff list is
    literally the migration that would need to be written to bring the
    migration chain back in line with the models.

    Note that Alembic's autogenerate does not examine CHECK constraints, so
    differences in them are neither detected nor reported. This is not a
    reduction in what is verified here: the previous sqlalchemy-diff based
    comparison listed every one of this schema's sixteen named check
    constraints in its ``ignores`` argument, because they did not diff
    correctly, so they were already excluded.
    """
    alembic_config.set_section_option('bwbTest', 'connstring', alembic_db_uri)
    logger.info(
        'Set alembic config bwbTest.connstring to: %s', alembic_db_uri
    )
    ah.load_premigration_sql(alembic_db_uri)
    with prepare_schema_from_migrations(
        alembic_db_uri, alembic_config
    ) as (engine, _):
        with engine.connect() as conn:
            context = MigrationContext.configure(
                conn, opts={'compare_server_default': True}
            )
            diffs = compare_metadata(context, Base.metadata)

    assert diffs == [], \
        'Migrations and models produce different schemas; Alembic would ' \
        'autogenerate the following changes to bring the migrations in ' \
        'line with the models:\n%s' % pformat(diffs)
