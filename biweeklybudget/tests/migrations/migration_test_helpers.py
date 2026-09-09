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
from sqlalchemy import create_engine
from alembic.command import upgrade, downgrade
from alembic.script import ScriptDirectory
from alembic.environment import EnvironmentContext  # noqa

from biweeklybudget.tests.migrations.alembic_helpers import (
    load_premigration_sql
)

logger = logging.getLogger(__name__)


@pytest.mark.migrations
class MigrationTest(object):
    """
    Class to assist with writing tests for Alembic migrations that change data.

    To implement:

    1. Subclass in a new module and mark with ``@pytest.mark.migrations``
    2. Set the ``migration_rev`` class attribute.
    3. Override ``data_setup``, ``verify_before`` and ``verify_after``.
    """

    migration_rev = None

    def data_setup(self, engine):
        """method to setup sample data in empty tables"""
        raise NotImplementedError("Must implement in subclass")

    def verify_before(self, engine):
        """method to verify data before forward migration, and after reverse"""
        raise NotImplementedError("Must implement in subclass")

    def verify_after(self, engine):
        """method to verify data after forward migration"""
        raise NotImplementedError("Must implement in subclass")

    def _migrate_up_to(self, rev, alembic_conf):
        """Apply all migrations up to but NOT INCLUDING rev"""
        upgrade(alembic_conf, rev)

    def _apply_migration(self, rev, alembic_conf):
        """Apply the migration specified by rev"""
        upgrade(alembic_conf, rev)

    def _reverse_migration(self, rev, alembic_conf):
        """Reverse the migration specified by rev"""
        downgrade(alembic_conf, rev)

    def _get_current_rev(self, alembic_conf, engine):
        script = ScriptDirectory.from_config(alembic_conf)
        with engine.connect() as conn:
            with EnvironmentContext(alembic_conf, script) as env_context:
                env_context.configure(conn, version_table="alembic_version")
                migration_context = env_context.get_context()
                revision = migration_context.get_current_revision()
        return revision

    def _rev_list(self, alembic_conf):
        script = ScriptDirectory.from_config(alembic_conf)
        revs = []
        for sc in script.walk_revisions(base="base", head="heads"):
            revs.append({
                'down_revision': sc.down_revision,
                'revision': sc.revision,
                'doc': sc.doc
            })
        revs.reverse()
        return revs

    def test_migration_roundtrip(self, alembic_db_uri, alembic_config):
        """DO NOT OVERRIDE. Method that runs migration tests."""
        alembic_config.set_section_option(
            'bwbTest', 'connstring', alembic_db_uri
        )
        load_premigration_sql(alembic_db_uri)
        engine = create_engine(alembic_db_uri)
        revs = self._rev_list(alembic_config)
        up_to_rev = None
        for rev in revs:
            if rev['revision'] == self.migration_rev:
                break
            up_to_rev = rev['revision']
        self._migrate_up_to(up_to_rev, alembic_config)
        logger.info('Migrated up to revision: %s', up_to_rev)
        self.data_setup(engine)
        self.verify_before(engine)
        self._apply_migration(self.migration_rev, alembic_config)
        logger.info(
            'Migrated up to revision: %s',
            self._get_current_rev(alembic_config, engine)
        )
        self.verify_after(engine)
        self._reverse_migration(up_to_rev, alembic_config)
        logger.info(
            'Migrated back to revision: %s',
            self._get_current_rev(alembic_config, engine)
        )
        self.verify_before(engine)
