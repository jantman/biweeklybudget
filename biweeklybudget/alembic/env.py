"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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

from __future__ import with_statement
import os
from alembic import context
from sqlalchemy import pool, create_engine
from logging.config import fileConfig
import logging
import warnings
from biweeklybudget.settings import DB_CONNSTRING
from biweeklybudget.models.base import Base

logger = logging.getLogger(__name__)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# only configure logging if used standalone, not when imported in app:
if len(logging.getLogger().handlers) < 1:
    # Interpret the config file for Python logging.
    # This line sets up loggers basically.
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def env_get_connstring():
    """Helper for migration tests"""
    try:
        conf = config.get_section_option('bwbTest', 'connstring', default=None)
    except Exception:
        conf = None
    if conf:
        logger.debug('Overriding connstring to: %s', conf)
        return conf
    logger.debug('Using default connstring from settings: %s', DB_CONNSTRING)
    return DB_CONNSTRING


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = env_get_connstring()
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    echo = False
    if os.environ.get('SQL_ECHO', '') == 'true':
        echo = True
    connectable = create_engine(
        env_get_connstring(), poolclass=pool.NullPool,
        pool_pre_ping=('SQL_POOL_PRE_PING' in os.environ), echo=echo
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            with warnings.catch_warnings():
                # Ignore warning from MariaDB MDEV-17544 when creating tables;
                # SQLAlchemy 1.3.13 names the primary keys, but MariaDB ignores
                # the names; MariaDB >= 10.4.7 now throws a warning for this.
                warnings.filterwarnings(
                    'ignore',
                    message=r'^\(1280, "Name.*ignored for PRIMARY key\."\)$',
                    category=Warning
                )
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
