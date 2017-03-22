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

Testing
-------

Testing is done via `pytest <http://pytest.org/latest/>`_, driven by `tox <http://tox.testrun.org/>`_.

* testing is as simple as:

  * ``pip install tox``
  * ``tox``

* If you want to pass additional arguments to pytest, add them to the tox command line after "--". i.e., for verbose pytext output on py27 tests: ``tox -e py27 -- -v``

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

If you want to run the acceptance tests without dumping and refreshing the test database, export the ``NO_REFRESH_DB`` environment variable.

Alembic DB Migrations
---------------------

This project uses `Alembic <http://alembic.zzzcomputing.com/en/latest/index.html>`_
for DB migrations:

* To generate migrations, run ``alembic revision --autogenerate -m "message"`` and examine/edit then commit the resulting file(s).
* To apply migrations, run ``alembic upgrade head``.
* To see the current DB version, run ``alembic current``.
* To see migration history, run ``alembic history``.

Release Checklist
-----------------

1. Open an issue for the release; cut a branch off master for that issue.
2. Verify whether or not DB migrations are needed. If they are, ensure they've been created, tested and verified.
3. Confirm that there are CHANGES.rst entries for all major changes.
4. Ensure that Travis tests passing in all environments.
5. Ensure that test coverage is no less than the last release (ideally, 100%).
6. Increment the version number in biweeklybudget/version.py and add version and release date to CHANGES.rst, then push to GitHub.
7. Confirm that README.rst renders correctly on GitHub.
8. Upload package to testpypi:

   * Make sure your ~/.pypirc file is correct (a repo called ``test`` for https://testpypi.python.org/pypi)
   * ``rm -Rf dist``
   * ``python setup.py register -r https://testpypi.python.org/pypi``
   * ``python setup.py sdist bdist_wheel``
   * ``twine upload -r test dist/*``
   * Check that the README renders at https://testpypi.python.org/pypi/biweeklybudget

9. Create a pull request for the release to be merged into master. Upon successful Travis build, merge it.
10. Tag the release in Git, push tag to GitHub:

   * tag the release. for now the message is quite simple: ``git tag -a X.Y.Z -m 'X.Y.Z released YYYY-MM-DD'``
   * push the tag to GitHub: ``git push origin X.Y.Z``

11. Upload package to live pypi:

    * ``twine upload dist/*``

12. make sure any GH issues fixed in the release were closed.