.. _getting_started:

Getting Started
===============

.. _getting_started.requirements:

Requirements
------------

**Note:** Alternatively, biweeklybudget is also distributed as a :ref:`Docker container <docker>`.
Using the dockerized version will eliminate all of these dependencies aside from MySQL and
Vault (the latter only if you choose to take advantage of the OFX downloading), both of which you can also run in containers.

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

Please note that, at the moment, one dependency is installed via git in order
to make use of an un-merged pull request that fixes a bug; since installation doesn't
support specifying git dependencies in ``setup.py``, you must install with
``requirements.txt`` directly:

.. code-block:: bash

    git clone https://github.com/jantman/biweeklybudget.git && cd biweeklybudget
    virtualenv --python=python3.6 .
    source bin/activate
    pip install -r requirements.txt
    python setup.py develop

.. _getting_started.configuration:

Configuration
-------------

biweeklybudget can take its configuration settings via either constants defined in a Python
module or environment variables. Configuration in environment variables always
overrides configuration from the settings module.

Settings Module
+++++++++++++++

:py:mod:`biweeklybudget.settings` imports all globals/constants from a
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
:ref:`Loading Data <development.loading_data>` during development, or
implementing :ref:`Custom OFX Downloading via Selenium <ofx.selenium>`. It is
the recommended configuration method if you need to include more logic than
simply defining static configuration settings.

Environment Variables
+++++++++++++++++++++

Every configuration setting can also be specified by setting an environment
variable with the same name; these will override any settings defined in
a ``SETTINGS_MODULE``, if specified. Note that some environment variables
require specific formatting of their values; see the
:py:mod:`settings module documentation <biweeklybudget.settings>` for a list
of these variables and the required formats.

Usage
-----

.. _getting_started.setup:

Setup
+++++

.. code-block:: bash

    source bin/activate
    export SETTINGS_MODULE=<settings module>

It's recommended that you create an alias to do this for you. Alternatively,
instead of setting ``SETTINGS_MODULE``, you can export the required environment
variables (see above).

Flask
+++++

For information on the Flask application, see `Flask App <flask_app>`.

Command Line Entrypoints and Scripts
++++++++++++++++++++++++++++++++++++

biweeklybudget provides the following setuptools entrypoints (command-line
script wrappers in ``bin/``). First setup your environment according to the
instructions above.

* ``bin/db_tester.py`` - Skeleton of a script that connects to and inits the DB. Edit this to use for one-off DB work. To get an interactive session, use ``python -i bin/db_tester.py``.
* ``loaddata`` - Entrypoint for dropping **all** existing data and loading test fixture data, or your base data. This is an awful, manual hack right now.
* ``ofxbackfiller`` - Entrypoint to backfill OFX Statements to DB from disk.
* ``ofxgetter`` - Entrypoint to download OFX Statements for one or all accounts, save to disk, and load to DB. See :ref:`OFX <ofx>`.
