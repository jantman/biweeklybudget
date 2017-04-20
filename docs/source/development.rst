.. _development:

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

.. _development.loading_data:

Loading Data
------------

The sample data used for acceptance tests is defined in ``biweeklybudget/tests/fixtures/sampledata.py``.
This data can be loaded by `setting up the environment <_getting_started.setup>`
and then using the ``loaddata`` entrypoint (the following values for
options are actually the defaults, but are shown for clarity):

.. code-block:: bash

    loaddata -m biweeklybudget.tests.fixtures.sampledata -c SampleDataLoader

This entrypoint will **drop all tables and data** and then load fresh data from
the specified class.

If you wish, you can copy ``biweeklybudget/tests/fixtures/sampledata.py`` to your
`customization package <_getting_started.customization>` and edit it to load your own
custom data. This should only be required if you plan on dropping and reinitializing the
database often.

Testing
-------

Testing is done via `pytest <http://pytest.org/latest/>`_, driven by `tox <http://tox.testrun.org/>`_.

* testing is as simple as:

  * ``pip install tox``
  * ``tox``

* If you want to pass additional arguments to pytest, add them to the tox command line after "--". i.e., for verbose pytext output on py27 tests: ``tox -e py27 -- -v``

For rapid iteration on tests, you can either use my
`toxit <https://github.com/jantman/misc-scripts/blob/master/toxit.py>`_ script
to re-run the test commands in an existing tox environment, or you can use
the ``bin/t`` and ``bin/ta`` scripts to run unit or acceptance tests,
respectively, on only one module.

Unit Tests
++++++++++

There are minimal unit tests, really only some examples and room to test some potentially fragile code. Run them via the ``^py\d+`` tox environments.

Integration Tests
+++++++++++++++++

There's a pytest marker for integration tests, effectively defined as anything that might use either a mocked/in-memory DB or the flask test client, but no HTTP server and no real RDBMS. Run them via the ``integration`` tox environment. But there aren't any of them yet.

Acceptance Tests
++++++++++++++++

There are acceptance tests, which use a real MySQL DB (see the connection string in ``tox.ini`` and ``conftest.py``) and a real Flask HTTP server, and selenium. Run them via the ``acceptance`` tox environment.

The acceptance tests connect to a local MySQL database using a connection string specified by the ``DB_CONNSTRING`` environment variable, or defaulting to a DB name and user/password that can be seen in ``conftest.py``. Once connected, the tests will drop all tables in the test DB, re-create all models/tables, and then load sample data. After the DB is initialized, tests will run the local Flask app on a random port, and run Selenium backed by PhantomJS.

If you want to run the acceptance tests without dumping and refreshing the test database, export the ``NO_REFRESH_DB`` environment variable. Setting the ``NO_CLASS_REFRESH_DB``
environment variable will prevent refreshing the DB after classes that manipulate data;
this will cause subsequent tests to fail but can be useful for debugging.

Alembic DB Migrations
---------------------

This project uses `Alembic <http://alembic.zzzcomputing.com/en/latest/index.html>`_
for DB migrations:

* To generate migrations, run ``alembic -c biweeklybudget/alembic/alembic.ini revision --autogenerate -m "message"`` and examine/edit then commit the resulting file(s).
* To apply migrations, run ``alembic -c biweeklybudget/alembic/alembic.ini upgrade head``.
* To see the current DB version, run ``alembic -c biweeklybudget/alembic/alembic.ini current``.
* To see migration history, run ``alembic -c biweeklybudget/alembic/alembic.ini history``.

Database Debugging
------------------

If you set the ``SQL_ECHO`` environment variable to "true", all SQL run by
SQLAlchemy will be logged at INFO level.

Frontend / UI
-------------

The UI is based on `BlackrockDigital's startbootstrap-sb-admin-2 <https://github.com/BlackrockDigital/startbootstrap-sb-admin-2>`_,
currently as of the 3.3.7-1 GitHub release. It is currently not modified at all, but should it need to be rebuilt,
this can be done with: ``pushd biweeklybudget/flaskapp/static/startbootstrap-sb-admin-2 && gulp``

Sphinx also generates documentation for the custom javascript files. This must be done manually
on a machine with `jsdoc <http://usejsdoc.org/>`_ installed, via: ``tox -e jsdoc``.

Release Checklist
-----------------

1. Open an issue for the release; cut a branch off master for that issue.
2. Verify whether or not DB migrations are needed. If they are, ensure they've been created, tested and verified.
3. Confirm that there are CHANGES.rst entries for all major changes.
4. Rebuild documentation and javascript documentation locally: ``tox -e jsdoc,docs``. Commit any changes.
5. Ensure that Travis tests passing in all environments.
6. Ensure that test coverage is no less than the last release (ideally, 100%).
7. Increment the version number in biweeklybudget/version.py and add version and release date to CHANGES.rst, then push to GitHub.
8. Confirm that README.rst renders correctly on GitHub.
9. Upload package to testpypi:

   * Make sure your ~/.pypirc file is correct (a repo called ``test`` for https://testpypi.python.org/pypi)
   * ``rm -Rf dist``
   * ``python setup.py register -r https://testpypi.python.org/pypi``
   * ``python setup.py sdist bdist_wheel``
   * ``twine upload -r test dist/*``
   * Check that the README renders at https://testpypi.python.org/pypi/biweeklybudget

10. Create a pull request for the release to be merged into master. Upon successful Travis build, merge it.
11. Tag the release in Git, push tag to GitHub:

   * tag the release. for now the message is quite simple: ``git tag -a X.Y.Z -m 'X.Y.Z released YYYY-MM-DD'``
   * push the tag to GitHub: ``git push origin X.Y.Z``

12. Upload package to live pypi:

    * ``twine upload dist/*``

13. make sure any GH issues fixed in the release were closed.
