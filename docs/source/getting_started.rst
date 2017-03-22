.. _getting_started:

Getting Started
===============

Requirements
------------

* Python 2.7 or 3.3+ (currently tested with 2.7, 3.3, 3.4, 3.5, 3.6 and developed with 3.6)
* Python `VirtualEnv <http://www.virtualenv.org/>`_ and ``pip`` (recommended installation method; your OS/distribution should have packages for these)
* Git, to install certain upstream dependencies.
* MySQL, or a compatible database (e.g. `MariaDB <https://mariadb.org/>`_). biweeklybudget uses `SQLAlchemy <http://www.sqlalchemy.org/>`_ for database abstraction, but currently specifies some MySQL-specific options, and is only tested with MySQL.
* To use the automated OFX transaction downloading functionality:

  * A running, reachable instance of `Hashicorp Vault <https://www.vaultproject.io/>`_ with your financial institution web credentials stored in it.
  * `PhantomJS <http://phantomjs.org/>`_ for downloading transaction data from institutions that do not support OFX remote access ("Direct Connect").

Installation
------------

It's recommended that you install into a virtual environment (virtualenv /
venv). See the `virtualenv usage documentation <http://www.virtualenv.org/en/latest/>`_
for information on how to create a venv.

This app is developed against Python 3.6, but should work back to 2.7. It does
not support Python3 < 3.3.

Please note that, at the moment, two dependencies are installed via git in order
to make use of un-merged pull requests that fix bugs; since

.. code-block:: bash

    git clone https://github.com/jantman/biweeklybudget.git && cd biweeklybudget
    virtualenv --python=python3.6 .
    source bin/activate
    pip install -r requirements.txt
    python setup.py develop

Upgrading
---------

This project uses `Alembic <http://alembic.zzzcomputing.com/en/latest/index.html>`_
for DB migrations:

* To apply migrations, run ``alembic upgrade head``.
* To see the current DB version, run ``alembic current``.
* To see migration history, run ``alembic history``.

.. _getting_started.configuration:

Configuration
-------------

biweeklybudget primarily takes its settings from constants defined in a Python
module. :py:mod:`biweeklybudget.settings` imports all globals/constants from a
module defined in the ``SETTINGS_MODULE`` environment variable. The recommended
way to configure this is to create your own separate Python package for customization
(either in a private git repository, or just in a directory on your computer)
and install this package into the same virtualenv as biweeklybudget. You then
set the ``SETTINGS_MODULE`` environment variable to the Python module/import
path of this module (i.e. the dotted path, like ``packagename.modulename``).

Once you've created the customization package, you can install it in the virtualenv
with ``pip install -e <git URL>`` (if it is kept in a git repository) or
``pip install -e <local path>``.

This customization package can also be used for
:ref:`Loading Data <_development.loading_data>` during development, or
implementing :ref:`Custom OFX Downloading via Selenium <_ofx.selenium>`.

If you just want to try the application without worrying about creating a
customization package, you can copy ``biweeklybudget/settings_example.py`` to
a new file, edit it, add it to ``.gitignore``, and then use
``SETTINGS_MODULE=biweeklybudget.NewModuleName``. This will, however, make it
more complicated to pull upstream changes and improvements.

Usage
-----

.. _getting_started.setup:

Setup
+++++

.. code-block:: bash

    source bin/activate
    export SETTINGS_MODULE=<settings module>

It's recommended that you create an alias or script to do this for you.

Flask
+++++

For information on the Flask application, see `Flask App <flask_app>`.

Command Line Entrypoints and Scripts
++++++++++++++++++++++++++++++++++++

biweeklybudget provides the following setuptools entrypoints (command-line
script wrappers in ``bin/``). First setup your environment according to the
instructions above.

* ``bin/db_tester.py`` - Skeleton of a script that connects to and inits the DB. Edit this to use for one-off DB work.
* ``loaddata`` - Entrypoint for loading test fixture data, or my base data. This is an awful, manual hack right now.
* ``ofxbackfiller`` - Entrypoint to backfill OFX Statements to DB from disk.
* ``ofxgetter`` - Entrypoint to download OFX Statements for one or all accounts, save to disk, and load to DB.
