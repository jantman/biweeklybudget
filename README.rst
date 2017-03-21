biweeklybudget
==============

.. image:: https://img.shields.io/pypi/v/biweeklybudget.svg?maxAge=2592000
   :target: https://pypi.python.org/pypi/biweeklybudget
   :alt: pypi version

.. image:: https://img.shields.io/github/forks/jantman/biweeklybudget.svg
   :alt: GitHub Forks
   :target: https://github.com/jantman/biweeklybudget/network

.. image:: https://img.shields.io/github/issues/jantman/biweeklybudget.svg
   :alt: GitHub Open Issues
   :target: https://github.com/jantman/biweeklybudget/issues

.. image:: https://landscape.io/github/jantman/biweeklybudget/master/landscape.svg
   :target: https://landscape.io/github/jantman/biweeklybudget/master
   :alt: Code Health

.. image:: https://secure.travis-ci.org/jantman/biweeklybudget.png?branch=master
   :target: http://travis-ci.org/jantman/biweeklybudget
   :alt: travis-ci for master branch

.. image:: https://codecov.io/github/jantman/biweeklybudget/coverage.svg?branch=master
   :target: https://codecov.io/github/jantman/biweeklybudget?branch=master
   :alt: coverage report for master branch

.. image:: https://readthedocs.org/projects/biweeklybudget/badge/?version=latest
   :target: https://readthedocs.org/projects/biweeklybudget/?badge=latest
   :alt: sphinx documentation for latest release

.. image:: http://www.repostatus.org/badges/latest/wip.svg
   :alt: Project Status: WIP – Initial development is in progress, but there has not yet been a stable, usable release suitable for the public.
   :target: http://www.repostatus.org/#wip

Responsive Flask/SQLAlchemy personal finance app, specifically for biweekly budgeting.

Requirements
------------

* Python 2.7 or 3.3+ (currently tested with 2.7, 3.3, 3.4, 3.5, 3.6)
* Python `VirtualEnv <http://www.virtualenv.org/>`_ and ``pip`` (recommended installation method; your OS/distribution should have packages for these)

Installation
------------

It's recommended that you install into a virtual environment (virtualenv /
venv). See the `virtualenv usage documentation <http://www.virtualenv.org/en/latest/>`_
for information on how to create a venv.

This app is developed against Python 3.6, but should work back to 2.7. It does
not support Python3 < 3.3.

.. code-block:: bash

    virtualenv --python=python3.6 .
    source bin/activate
    pip install -r requirements.txt
    python setup.py develop

Configuration
-------------

Something here.

Usage
-----

Something else here.

Bugs and Feature Requests
-------------------------

Bug reports and feature requests are happily accepted via the `GitHub Issue Tracker <https://github.com/jantman/biweeklybudget/issues>`_. Pull requests are
welcome. Issues that don't have an accompanying pull request will be worked on
as my time and priority allows.

Old Script Contents
-------------------

-  **ofxgetter.py** - Library for retrieving OFX files. Usage: ``./ofxgetter.py`` for all accounts, or ``./ofxgetter.py ACCT-NAME`` for one account.
-  `~/GIT/misc-scripts/lastpass2vault.py <https://github.com/jantman/misc-scripts/blob/master/lastpass2vault.py>`_ - Script to pull all entries from LastPass and write them to local Vault. Run as ``./lastpass2vault.py -vv -f PATH_TO_VAULT_TOKEN LASTPASS_USERNAME``

Flask App
---------

1. ``source bin/activate``
2. ``export FLASK_APP="biweeklybudget.flaskapp.app"``
3. ``flask --help``

* Run App: ``flask run --host=0.0.0.0``
* Run with debug/reload: ``flask run --host=0.0.0.0 --reload --debugger``
* Build theme: ``pushd biweeklybudget/flaskapp/static/startbootstrap-sb-admin-2 && gulp``

To run the app against the acceptance test database, use: ``MYSQL_CONNSTRING='mysql+pymysql://budgetTester@127.0.0.1:3306/budgettest?charset=utf8mb4' flask run --host=0.0.0.0``

Scripts / Entrypoints
---------------------

* ``bin/db_tester.py`` - Skeleton of a script that connects to and inits the DB. Edit this to use for one-off DB work.
* ``bin/loaddata`` - Entrypoint for loading test fixture data, or my base data. This is an awful, manual hack right now.
* ``bin/ofxbackfiller`` - Entrypoint to backfill OFX Statements to DB from disk.
* ``bin/ofxgetter`` - Entrypoint to download OFX Statements for one or all accounts, save to disk, and load to DB.

DB Migrations
-------------

This project uses `Alembic <http://alembic.zzzcomputing.com/en/latest/index.html>`_
for DB migrations:

* To generate migrations, run ``alembic revision --autogenerate -m "message"`` and examine/edit then commit the resulting file(s).
* To apply migrations, run ``alembic upgrade head``.
* To see the current DB version, run ``alembic current``.
* To see migration history, run ``alembic history``.

OFX Downloads
-------------

``ofxgetter`` downloads OFX statements from your bank(s), stores them locally, and writes
them to the database. It requires an instance of `Hashicorp Vault <https://www.vaultproject.io/>`_ to retrieve credentials from.

To Do
-----

* Homepage

  * standing budgets and their balances
  * graph of income vs expenses

* Accounts

  * credit accounts - field for credit limit, so I can see available credit
  * switch how the balances are stored to not require OFX, and to keep historical records of balances (this will require an account_balances table). Not sure how to maintain this relationship nicely, or maybe the solution is either with a property on the model to find the current balance, or a separate query helper function. We want to lazy-load all balances past the current one...

* Transactions (views with pagination)

  * view per account
  * combined across all accounts
  * Transaction input page or modal

* Calendar / Per-Pay-Period

  * see all transactions for period, both actual and scheduled (future)
  * way to mark a future transaction as having been made (converts from scheduled to real txn, links real txn to scheduled txn ID) - [hybrid attributes and setters](http://docs.sqlalchemy.org/en/rel_1_1/orm/extensions/hybrid.html)
  * show balances for next few pay periods
  * show actual calendar widget
  * show all budgets for the pay period, and all standing budgets

* Reconcile transaction

  * rules-based reconciling should pre-populate the drag & drop instead of committing
  * drag & drop - `jsfiddle <http://jsfiddle.net/KyleMit/Wdyd6/>`_, `cards tutorial <http://www.elated.com/res/File/articles/development/javascript/jquery/drag-and-drop-with-jquery-your-essential-guide/card-game.html>`_, `w3schools <https://www.w3schools.com/html/html5_draganddrop.asp>`_, `explanation <http://apress.jensimmons.com/v5/pro-html5-programming/ch9.html>`_
  * should show confirmation after submission, before updating DB

* Scheduled Transactions

  * specific dates
  * day of month
  * number of txns per pay period
  * schedule for "any date" in a pay period
  * One table for scheduled/future trans with general info plus per-type columns (i.e. a num_per_pay_period column, a date column, a day_of_month column). Can craft a query using this format to get all scheduled transactions for a given pay period; would assign dates and order for viewing, and would also be able to remove anything that has a "real" txn associated (because converting a scheduled to real will include the scheduled ID in the real one).

* Budgets

  * per-pay-period recurring budgets
  * standing budgets (and funding sources/amounts)

Notes / Links
-------------

* Assuming flask is run as shown above, the full example pages from the SB Admin 2 theme/template can be seen at `http://localhost:5000/static/startbootstrap-sb-admin-2/pages/index.html <http://localhost:5000/static/startbootstrap-sb-admin-2/pages/index.html>`_
* `Flask message flashing <http://flask.pocoo.org/docs/0.12/quickstart/#message-flashing>`_
* `Flask views <http://flask.pocoo.org/docs/0.12/views/>`_
* `Flask sessions <http://flask.pocoo.org/docs/0.12/quickstart/#sessions>`_
* `WTForms validation <http://flask.pocoo.org/docs/0.12/patterns/wtforms/>`_
* `Nice full datatables demo <http://localhost:5000/static/startbootstrap-sb-admin-2/pages/tables.html>`_
* Possibly-useful icons:

  * fa-check-square-o
  * fa-edit
  * fa-shopping-cart
  * fa-credit-card
  * fa-bar-chart-o
  * fa-dollar
  * fa-history
  * glyphicon-piggy-bank

Testing
-------

There are minimal unit tests, really only some examples and room to test some potentially fragile code. Run them via the ``py27`` tox environment.

There's a pytest marker for integration tests, effectively defined as anything that might use either a mocked/in-memory DB or the flask test client, but no HTTP server and no real RDBMS. Run them via the ``integration`` tox environment.

There are acceptance tests, which use a real MySQL DB (see the connection string in ``tox.ini`` and ``conftest.py``) and a real Flask HTTP server, and selenium. Run them via the ``acceptance`` tox environment.

The acceptance tests connect to a local MySQL database using a connection string specified by the ``MYSQL_CONNSTRING`` environment variable, or defaulting to a DB name and user/password that can be seen in ``conftest.py``. Once connected, the tests will drop all tables in the test DB, re-create all models/tables, and then load sample data. After the DB is initialized, tests will run the local Flask app on a random port, and run Selenium backed by PhantomJS.

If you want to run the acceptance tests without dumping and refreshing the test database, export the ``NO_REFRESH_DB`` environment variable.

Development
===========

To install for development:

1. Fork the `biweeklybudget <https://github.com/jantman/biweeklybudget>`_ repository on GitHub
2. Create a new branch off of master in your fork.

.. code-block:: bash

    $ virtualenv biweeklybudget
    $ cd biweeklybudget && source bin/activate
    $ pip install -e git+git@github.com:YOURNAME/biweeklybudget.git@BRANCHNAME#egg=biweeklybudget
    $ cd src/biweeklybudget

The git clone you're now in will probably be checked out to a specific commit,
so you may want to ``git checkout BRANCHNAME``.

Guidelines
----------

* pep8 compliant with some exceptions (see pytest.ini)
* 100% test coverage with pytest (with valid tests)

Testing
-------

Testing is done via `pytest <http://pytest.org/latest/>`_, driven by `tox <http://tox.testrun.org/>`_.

* testing is as simple as:

  * ``pip install tox``
  * ``tox``

* If you want to pass additional arguments to pytest, add them to the tox command line after "--". i.e., for verbose pytext output on py27 tests: ``tox -e py27 -- -v``

Release Checklist
-----------------

1. Open an issue for the release; cut a branch off master for that issue.
2. Confirm that there are CHANGES.rst entries for all major changes.
3. Ensure that Travis tests passing in all environments.
4. Ensure that test coverage is no less than the last release (ideally, 100%).
5. Increment the version number in biweeklybudget/version.py and add version and release date to CHANGES.rst, then push to GitHub.
6. Confirm that README.rst renders correctly on GitHub.
7. Upload package to testpypi:

   * Make sure your ~/.pypirc file is correct (a repo called ``test`` for https://testpypi.python.org/pypi)
   * ``rm -Rf dist``
   * ``python setup.py register -r https://testpypi.python.org/pypi``
   * ``python setup.py sdist bdist_wheel``
   * ``twine upload -r test dist/*``
   * Check that the README renders at https://testpypi.python.org/pypi/biweeklybudget

8. Create a pull request for the release to be merged into master. Upon successful Travis build, merge it.
9. Tag the release in Git, push tag to GitHub:

   * tag the release. for now the message is quite simple: ``git tag -a X.Y.Z -m 'X.Y.Z released YYYY-MM-DD'``
   * push the tag to GitHub: ``git push origin X.Y.Z``

11. Upload package to live pypi:

    * ``twine upload dist/*``

10. make sure any GH issues fixed in the release were closed.
