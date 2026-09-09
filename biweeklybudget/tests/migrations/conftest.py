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

import os

import pytest

from alembicverify.util import make_alembic_config

from biweeklybudget.tests.migrations.alembic_helpers import (
    uri_for_db, empty_db_by_uri
)


@pytest.fixture
def alembic_root():
    """Absolute path to the Alembic script directory.

    Resolved from ``TOXINIDIR`` rather than from the current working
    directory; see :py:func:`~.alembic_config`.
    """
    return os.path.join(
        os.path.abspath(os.environ['TOXINIDIR']), 'biweeklybudget', 'alembic'
    )


@pytest.fixture
def alembic_db_uri():
    """URI of the (emptied) database that the migration suite builds.

    This is one of the fixture names alembic-verify 1.x expects a project to
    supply; the database it names comes from the ``MYSQL_DBNAME_LEFT``
    environment variable.
    """
    uri = uri_for_db(os.environ['MYSQL_DBNAME_LEFT'])
    empty_db_by_uri(uri)
    return uri


@pytest.fixture
def alembic_config(alembic_db_uri, alembic_root):
    """Alembic config pointed at the migration test database.

    alembic-verify ships a fixture of this name, but it resolves the Alembic
    script location out of ``alembic.ini``, where this project records it as
    the *relative* path ``biweeklybudget/alembic`` - which only resolves when
    the tests are run from the repository root. Ours uses the absolute path
    from the :py:func:`~.alembic_root` fixture instead, so the suite does not
    depend on the working directory.
    """
    return make_alembic_config(alembic_db_uri, alembic_root)
