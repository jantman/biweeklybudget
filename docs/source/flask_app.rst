.. _flask_app:

Flask Application
=================

Running Flask Development Server
--------------------------------

Flask comes bundled with a builtin development server for fast local development and testing.
This is an easy way to take biweeklybudget for a spin, but carries some important and critical
warnings if you use it with real data. For upstream documentation, see the
`Flask Development Server docs <http://flask.pocoo.org/docs/0.12/server/>`_. Please note that
the development server is a single process and defaults to single-threaded, and is only realistically
usable by one user.

1. First, setup your environment per :ref:`Getting Started - Setup <getting_started.setup>`.
2. ``export FLASK_APP="biweeklybudget.flaskapp.app"``
3. If you're running against an existing database, see important information in the "Database Migrations" section, below.
4. ``flask --help`` for information on usage:

  * Run App: ``flask run``
  * Run with debug/reload: ``flask rundev``

To run the app against the acceptance test database, use: ``DB_CONNSTRING='mysql+pymysql://budgetTester@127.0.0.1:3306/budgettest?charset=utf8mb4' flask run``

By default, Flask will only bind to localhost. If you want to bind to all interfaces, you can add ``--host=0.0.0.0`` to the ``flask run`` commands. Please be aware of the implications of this (see "Security", below).

If you wish to run the flask app in a multi-process/thread/worker WSGI container,
be sure that you run the ``initdb`` entrypoint before starting the workers. Otherwise,
it's likely that all workers will attempt to create the database tables or run migrations
at the same time, and fail.

.. _flask_app.migrations:

Database Migrations
-------------------

If you run the Flask application (whether in the flask development server or a separate WSGI container)
against an existing database and there are unapplied Alembic database migrations, it's very likely that
multiple threads or processes will attempt to perform the same migrations at the same time, and leave the
database in an inconsistent and unusable state. As such, there are two important warnings:

1. Always be sure that you have a recent database backup before upgrading.
2. You must manually trigger database migrations before starting Flask. This can be done
   by running the ``initdb`` console script provided by the biweeklybudget package
   (``bin/initdb`` in your virtualenv).

Security
--------

This code hasn't been audited. It might have SQL injection vulnerabilities in it. It might dump your bank account details in HTML comments. Anything is possible!

To put it succinctly, this was written to be used by me, and me only. It was written with the assumption that anyone who can possibly access any of the application at all, whether in a browser or locally, is authorized to view and/or edit anything and everything related to the application (configuration, everything in the database, everything in Vault if it's being used). If you even think about making this accessible to anything other than localhost on a computer you physically own, it's entirely up to you how you secure it, but make sure you do it really well.

Logging
-------

By default, the Flask application's logs go to STDOUT. The ``BIWEEKLYBUDGET_LOG_FILE`` environment variable can be set to the absolute path of a file, to cause Flask application logs to go to the file *in addition to* STDOUT.

MySQL Connection Errors
-----------------------

See :ref:`Getting Started - MySQL Connection Errors <getting_started.mysql_connection_errors>` for some information on handling MySQL connection errors.
