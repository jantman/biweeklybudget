.. _getting_started:

Getting Started
===============

.. _getting_started.requirements:

Requirements
------------

**Note:** Alternatively, biweeklybudget is also distributed as a :ref:`Docker container <docker>`.
Using the dockerized version will eliminate all of these dependencies aside from MySQL and
Vault (the latter only if you choose to take advantage of the OFX downloading), both of which you can also run in containers.

* Python 3.5+ (currently tested with 3.5, 3.6, 3.7, 3.8 and developed with 3.8). **Python 2 is not supported.**
* Python `VirtualEnv <http://www.virtualenv.org/>`_ and ``pip`` (recommended installation method; your OS/distribution should have packages for these)
* MySQL, or a compatible database (e.g. `MariaDB <https://mariadb.org/>`_ ). biweeklybudget uses `SQLAlchemy <http://www.sqlalchemy.org/>`_ for database abstraction, but currently specifies some MySQL-specific options, and is only tested with MySQL.
* To use the automated OFX transaction downloading functionality:

  * A running, reachable instance of `Hashicorp Vault <https://www.vaultproject.io/>`_ with your financial institution web credentials stored in it.
  * If your bank does not support OFX remote access ("Direct Connect"), you will need to write a custom screen-scraper class using Selenium and a browser.

Installation
------------

It's recommended that you install into a virtual environment (virtualenv /
venv). See the `virtualenv usage documentation <http://www.virtualenv.org/en/latest/>`_
for information on how to create a venv.

This app is developed against Python 3.8. It does not support Python3 < 3.4.

.. code-block:: bash

    mkdir biweeklybudget
    virtualenv --python=python3.8 .
    source bin/activate
    pip install biweeklybudget

**Important Note:** Anyone who's using this project for actual data should install
from the package on PyPI. While the ``master`` branch of the git repository is always
in a runnable state, there is no guarantee that data will be not be harmed by upgrading
directly to master. Specifically, database migrations are only compatible between released
versions; ``master`` is considered a pre-release/development version, and can have migrations
removed or altered in breaking ways between official releases.

Upgrading
---------

Documentation for upgrades depends on how you've installed and run biweeklybudget:

* For non-docker installations, see :ref:`Flask Application - Database Migrations <flask_app.migrations>`
* For Docker installations, no special action is needed.
* For development installations, see :ref:`Development - Alembic DB Migrations <development.alembic>`

In all cases, you should always perform a full backup of your database before an upgrade.

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

There are also some additional environment variables available:

* ``BIWEEKLYBUDGET_LOG_FILE`` - By default, the Flask application's logs go to STDOUT. The ``BIWEEKLYBUDGET_LOG_FILE`` environment variable can be set to the absolute path of a file, to cause Flask application logs to go to the file *in addition to* STDOUT.


Running Locally
---------------

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

For information on the Flask application and on running the Flask development
server, see :ref:`Flask App <flask_app>`.

.. _docker:

Running In Docker
-----------------

Biweeklybudget is also distributed as a `docker image <https://hub.docker.com/r/jantman/biweeklybudget/>`_,
to make it easier to run without installing as many :ref:`Requirements <getting_started.requirements>`.

You can pull the latest version of the image with ``docker pull jantman/biweeklybudget:latest``, or
a specific release version ``X.Y.Z`` with ``docker pull jantman/biweeklybudget:X.Y.Z``. It is recommended
that you run a specific version number, and that you make sure to perform a database backup before upgrading.

The only dependencies for a Docker installation are:

* MySQL, which can be run via Docker (`MariaDB official image <https://hub.docker.com/_/mariadb/>`_ recommended) or local on the host
* Vault, if you wish to use the OFX downloading feature, which can also be run `via Docker <https://hub.docker.com/_/vault/>`_

**Important Note:** If you run MySQL and/or Vault in containers, please make sure that their data
is backed up and will not be removed.

The `image <https://hub.docker.com/r/jantman/biweeklybudget/>`_ runs with the `tini <https://github.com/krallin/tini>`_ init
wrapper and uses `gunicorn <http://gunicorn.org/>`_ under Python 3.6 to serve the web UI, exposed on port 80. Note that,
while it runs with 4 worker threads, there is no HTTP proxy in front of Gunicorn and this image is intended for local network
use by a single user/client. The image also automatically runs database migrations in a safe manner at start, before starting
the Flask application.

For ease of running, the image defaults the ``SETTINGS_MODULE`` environment variable to
``biweeklybudget.settings_example``. This allows leveraging the environment variable
:ref:`configuration <getting_started.configuration>` overrides so that you need only
specify configuration options that you want to override from
`settings_example.py <https://github.com/jantman/biweeklybudget/blob/master/biweeklybudget/settings_example.py>`_.

For ease of running, it's highly recommended that you put your configuration in a Docker-readable
environment variables file.

Environment Variable File
+++++++++++++++++++++++++

In the following examples, we reference the following environment variable file.
It will override settings from `settings_example.py <https://github.com/jantman/biweeklybudget/blob/master/biweeklybudget/settings_example.py>`_
as needed; specifically, we need to override the database connection string,
pay period start date and reconcile begin date. In the examples below, we would
save this as ``biweeklybudget.env``:

.. code-block:: none

    DB_CONNSTRING=mysql+pymysql://USERNAME:PASSWORD@HOST:PORT/DBNAME?charset=utf8mb4
    PAY_PERIOD_START_DATE=2017-03-28
    RECONCILE_BEGIN_DATE=2017-02-15


Containerized MySQL Example
+++++++++++++++++++++++++++

This assumes that you already have a MySQL database container running with the
container name "mysql" and exposing port 3306, and that we want the biweeklybudget
web UI served on host port 8080:

In our ``biweeklybudget.env``, we would specify the database connection string for the "mysql" container:

.. code-block:: none

    DB_CONNSTRING=mysql+pymysql://USERNAME:PASSWORD@mysql:3306/DBNAME?charset=utf8mb4

And then run biweeklybudget:

.. code-block:: none

    docker run --name biweeklybudget --env-file biweeklybudget.env \
    -p 8080:80 --link mysql jantman/biweeklybudget:latest

Host-Local MySQL Example
++++++++++++++++++++++++

It is also possible to use a MySQL server on the physical (Docker) host system. To do so,
you'll need to know the host system's IP address. On Linux when using the default "bridge"
Docker networking mode, this will coorespond to a ``docker0`` interface on the host system.
The Docker documentation on `adding entries to the Container's hosts file <https://docs.docker.com/engine/reference/commandline/run/#add-entries-to-container-hosts-file---add-host>`_
provides a helpful snippet for this (on my systems, this results in ``172.17.0.1``):

.. code-block:: none

    ip -4 addr show scope global dev docker0 | grep inet | awk '{print $2}' | cut -d / -f 1

In our ``biweeklybudget.env``, we would specify the database connection string that uses the "dockerhost" hosts file entry, created by the ``--add-host`` option:

.. code-block:: none

    # "dockerhost" is added to /etc/hosts via the `--add-host` docker run option
    DB_CONNSTRING=mysql+pymysql://USERNAME:PASSWORD@dockerhost:3306/DBNAME?charset=utf8mb4

So using that, we could run biweeklybudget listening on port 8080 and using our host's MySQL server (on port 3306):

.. code-block:: none

    docker run --name biweeklybudget --env-file biweeklybudget.env \
    --add-host="dockerhost:$(ip -4 addr show scope global dev docker0 | grep inet | awk '{print $2}' | cut -d / -f 1)" \
    -p 8080:80 jantman/biweeklybudget:latest

You may need to adjust those commands depending on your operating system, Docker networking mode, and MySQL server.

.. _getting_started.mysql_connection_errors:

MySQL Connection Errors
+++++++++++++++++++++++

On resource-constrained systems or with MySQL servers tuned for minimal resource utilization, you may see the Flask application returning HTTP 500 errors after periods of inactivity, with the Flask application log reporting something like "Lost connection to MySQL server during query" and MySQL reporting "Aborted connection" errors. This is due to connections in the SQLAlchemy connection pool timing out, but the application not being aware of that. If this happens, you can set the ``SQL_POOL_PRE_PING`` environment variable (to any value). This will enable SQLAlchemy's ``pool_pre_ping`` feature (see `Disconnect Handling - Pessimistic <http://docs.sqlalchemy.org/en/latest/core/pooling.html#pool-disconnects-pessimistic>`_) which tests that connections are still working before executing queries with them.

Settings Module Example
+++++++++++++++++++++++

If you need to provide biweeklybudget with more complicated configuration, this is
still possible via a Python settings module. The easiest way to inject one into the
Docker image is to `mount <https://docs.docker.com/engine/reference/commandline/run/#mount-volume--v---read-only>`_
a python module directly into the biweeklybudget package directory. Assuming you have
a custom settings module on your local machine at ``/opt/biweeklybudget-settings.py``, you would
run the container as shown below to mount the custom settings module into the container and use it.
Note that this example assumes using MySQL in another container; adjust as necessary if you are using
MySQL running on the Docker host:

.. code-block:: none

    docker run --name biweeklybudget -e SETTINGS_MODULE=biweeklybudget.mysettings \
    -v /opt/biweeklybudget-settings.py:/app/lib/python3.6/site-packages/biweeklybudget/mysettings.py \
    -p 8080:80 --link mysql jantman/biweeklybudget:latest

Note on Locales
+++++++++++++++

biweeklybudget uses Python's `locale <https://docs.python.org/3.6/library/locale.html>`_ module
to format currency. This requires an appropriate locale installed on the system. The docker image
distributed for this package only includes the ``en_US.UTF-8`` locale. If you need a different one,
please cut a pull request against ``docker_build.py``.

Running ofxgetter in Docker
+++++++++++++++++++++++++++

If you wish to use the :ref:`ofxgetter <ofx>` script inside the Docker container, some special
settings are needed:

1. You must mount the statement save path (:py:const:`~biweeklybudget.settings.STATEMENTS_SAVE_PATH`) into the container.
2. You must mount the Vault token file path (:py:const:`~biweeklybudget.settings.TOKEN_PATH`) into the container.
3. You must set either the ``VAULT_ADDR`` environment variable, or the :py:const:`~biweeklybudget.settings.VAULT_ADDR` setting.

As an example, for using ofxgetter in Docker with your statements saved to ``/home/myuser/statements`` on your host computer and your Vault token stored in ``/home/myuser/.vault-token`` on your host computer, you would set :py:const:`~biweeklybudget.settings.STATEMENTS_SAVE_PATH` in your settings file to ``/statements`` and :py:const:`~biweeklybudget.settings.TOKEN_PATH` to ``/.token``, and add to your ``docker run`` command:

.. code-block:: none

    -v /home/myuser/statements:/statements \
    -v /home/myuser/.vault-token:/.token

Assuming your container was running with ``--name biweeklybudget``, you could run ofxgetter (e.g. via cron) as:

.. code-block:: none

    docker exec biweeklybudget /bin/sh -c 'cd /statements && /app/bin/ofxgetter'

We run explicitly in the statements directory so that if ``ofxgetter`` encounters an error
when using a :py:class:`~biweeklybudget.screenscraper.ScreenScraper` class, the screenshots
and HTML output will be saved to the host filesystem.

Command Line Entrypoints and Scripts
------------------------------------

biweeklybudget provides the following setuptools entrypoints (command-line
script wrappers in ``bin/``). First setup your environment according to the
instructions above.

* ``bin/db_tester.py`` - Skeleton of a script that connects to and inits the DB. Edit this to use for one-off DB work. To get an interactive session, use ``python -i bin/db_tester.py``.
* ``loaddata`` - Entrypoint for dropping **all** existing data and loading test fixture data, or your base data. This is an awful, manual hack right now.
* ``ofxbackfiller`` - Entrypoint to backfill OFX Statements to DB from disk.
* ``ofxgetter`` - Entrypoint to download OFX Statements for one or all accounts, save to disk, and load to DB. See :ref:`OFX <ofx>`.
* ``wishlist2project`` - For any projects with "Notes" fields matching an Amazon wishlist URL of a public wishlist (``^https://www.amazon.com/gp/registry/wishlist/``), synchronize the wishlist items to the project. Requires ``wishlist==0.1.2``.
