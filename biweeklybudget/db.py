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

This is mostly based on http://flask.pocoo.org/docs/0.12/patterns/sqlalchemy/
"""

from biweeklybudget import settings
import logging
import os
from copy import deepcopy
import warnings
import pkg_resources

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from pymysql.err import Warning
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
from alembic import command

from biweeklybudget.utils import in_directory

logger = logging.getLogger(__name__)

logger.debug('Creating DB engine with connection: %s',
             settings.DB_CONNSTRING)

echo = False
if os.environ.get('SQL_ECHO', '') == 'true':
    echo = True

# For some reason, with PyMySQL, even setting sql_mode to TRADITIONAL isn't
# raising an Exception when data is truncated. So we need to explicitly convert
# ``pymysql.err.Warning`` to an exception...
warnings.simplefilter('error', category=Warning)

engine_args = {
    'convert_unicode': True,
    'echo': echo,
    'pool_recycle': 3600
}

if settings.DB_CONNSTRING.startswith('mysql'):
    engine_args['connect_args'] = {'sql_mode': 'TRADITIONAL'}

#: The database engine object; return value of
#: :py:func:`sqlalchemy.create_engine`.
engine = create_engine(settings.DB_CONNSTRING, **engine_args)

logger.debug('Creating DB session')

#: :py:class:`sqlalchemy.orm.scoping.scoped_session` session
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

logger.debug('Setting up Base and query')

from biweeklybudget.models.base import Base  # noqa
Base.query = db_session.query_property()
from biweeklybudget.db_event_handlers import init_event_listeners  # noqa


def _alembic_get_current_rev(config, script):
    """
    Works sorta like alembic.command.current

    :param config: alembic Config
    :return: current revision
    :rtype: str
    """
    config._curr_rev = None

    def display_version(rev, _):
        for rev in script.get_all_current(rev):
            config._curr_rev = rev.cmd_format(False)
        return []

    with EnvironmentContext(
        config,
        script,
        fn=display_version
    ):
        script.run_env()
    if config._curr_rev is not None and ' ' in config._curr_rev:
        config._curr_rev = config._curr_rev.strip().split(' ')[0]
    return config._curr_rev


def init_db():
    """
    Initialize the database; call
    :py:meth:`sqlalchemy.schema.MetaData.create_all` on the metadata object.
    """
    logger.debug('Initializing database')
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    alembic_ini = pkg_resources.resource_filename(
        pkg_resources.Requirement.parse('biweeklybudget'),
        'biweeklybudget/alembic/alembic.ini'
    )
    topdir = os.path.abspath(
        os.path.join(os.path.dirname(alembic_ini), '..', '..')
    )
    logger.debug('Alembic configuration: %s', alembic_ini)
    with in_directory(topdir):
        alembic_config = Config(alembic_ini)
        script = ScriptDirectory.from_config(alembic_config)
        curr_rev = _alembic_get_current_rev(alembic_config, script)
        head_rev = script.get_revision("head").revision
        if curr_rev is None:
            # alembic not initialized at all; stamp with current version
            logger.warning(
                'Alembic not setup; creating all models and stamping'
            )
            logger.debug('Creating all models')
            Base.metadata.create_all(engine)
            command.stamp(alembic_config, "head")
            logger.debug("DB stamped at %s", head_rev)
        elif curr_rev != head_rev:
            logger.warning("Alembic head is %s but this DB is at %s; "
                           "running migrations", head_rev, curr_rev)
            command.upgrade(alembic_config, "head")
            logger.info("Migrations complete")
        else:
            logger.debug('Alembic is at the correct head version (%s)',
                         curr_rev)
    logger.debug('Done initializing DB')
    init_event_listeners(db_session)


def cleanup_db():
    """
    This must be called from all scripts, using

        atexit.register(cleanup_db)

    """
    logger.debug('Closing DB session')
    db_session.remove()


def upsert_record(model_class, key_fields, **kwargs):
    """
    Upsert a record in the database.

    ``key_fields`` is either a string primary key field name (a key in the
    ``kwargs`` dict) or a list or tuple of string primary key field names, for
    compound keys.

    If a record can be found matching these keys, it will be updated and
    committed. If not, a new one will be inserted. Either way, the record is
    returned.

    :py:meth:`sqlalchemy.orm.session.Session.commit` is **NOT** called.

    :param model_class: the class of model to insert/update
    :type model_class: biweeklybudget.models.base.ModelAsDict
    :param key_fields: The field name(s) (keys in ``kwargs``) that make up the
      primary key. This can be a single string, or a list or tuple of strings
      for compound keys. The values for these key fields MUST be included in
      ``kwargs``.
    :param kwargs: arguments to provide to the model class constructor, or to
      update if there is an existing record matching the key.
    :type kwargs: dict
    :return: inserted or updated record; type is an instance of ``model_class``
    """
    args = {}
    for k, v in kwargs.items():
        if isinstance(v, Base):
            args[k] = v
        else:
            args[k] = deepcopy(v)
    pkey = None
    if isinstance(key_fields, type('')):
        pkey = args[key_fields]
        del args[key_fields]
    else:
        pkey = []
        for k in key_fields:
            pkey.append(args[k])
            del args[k]
        pkey = tuple(pkey)
    logger.info('Upserting %s key=%s: %s', model_class, pkey, kwargs)
    res = db_session.query(model_class).get(pkey)
    if res is None:
        # not in DB yet; insert
        logger.debug('INSERTing (no existing record found)')
        o = model_class(**kwargs)
        db_session.add(o)
        return o
    logger.debug('Matching record exists; updating')
    for k, v in args.items():
        setattr(res, k, v)
    return res
