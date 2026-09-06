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

from alembicverify.util import make_alembic_config


@pytest.fixture
def alembic_config_left(uri_left, alembic_root):
    """Alembic config pointed at the "left" (migrations) test database.

    This replaces the deprecated fixture of the same name shipped by
    alembic-verify, which resolves the script location from ``alembic.ini``
    as a path relative to the current working directory.
    """
    return make_alembic_config(uri_left, alembic_root)


@pytest.fixture
def alembic_config_right(uri_right, alembic_root):
    """Alembic config pointed at the "right" (models) test database.

    See :py:func:`~.alembic_config_left`.
    """
    return make_alembic_config(uri_right, alembic_root)
