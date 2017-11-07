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

Testing is done via `pytest <https://docs.pytest.org/en/latest/>`_, driven by `tox <https://tox.readthedocs.io/>`_.

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

There are acceptance tests, which use a real MySQL DB (see the connection string in ``tox.ini`` and ``conftest.py``) and a real Flask HTTP server, and selenium. Run them via the ``acceptance`` tox environment. Note that they're currently configured to use Headless Chrome; running them locally will require a modern Chrome version that supports the ``--headless`` flag (Chrome 59+) and a matching version of `chromedriver <https://sites.google.com/a/chromium.org/chromedriver/>`_.

The acceptance tests connect to a local MySQL database using a connection string specified by the ``DB_CONNSTRING`` environment variable, or defaulting to a DB name and user/password that can be seen in ``conftest.py``. Once connected, the tests will drop all tables in the test DB, re-create all models/tables, and then load sample data. After the DB is initialized, tests will run the local Flask app on a random port, and run Selenium backed by PhantomJS.

If you want to run the acceptance tests without dumping and refreshing the test database, export the ``NO_REFRESH_DB`` environment variable. Setting the ``NO_CLASS_REFRESH_DB``
environment variable will prevent refreshing the DB after classes that manipulate data;
this will cause subsequent tests to fail but can be useful for debugging.

Running Acceptance Tests Against Docker
+++++++++++++++++++++++++++++++++++++++

The acceptance tests have a "hidden" hook to run against an already-running Flask application,
run during the ``docker`` tox environment build. **Be warned** that the acceptance tests modify data,
so they should never be run against a real database. This hook is controlled via the
``BIWEEKLYBUDGET_TEST_BASE_URL`` environment variable. If this variable is set, the acceptance
tests will not start a Flask server, but will instead use the specified URL. The URL must not
end with a trailing slash.

.. _development.alembic:

Alembic DB Migrations
---------------------

This project uses `Alembic <http://alembic.zzzcomputing.com/en/latest/index.html>`_
for DB migrations:

* To generate migrations, run ``alembic -c biweeklybudget/alembic/alembic.ini revision --autogenerate -m "message"`` and examine/edit then commit the resulting file(s). This must be run *before* the model changes are applied to the DB. If adding new models, make sure to import the model class in ``models/__init__.py``.
* To apply migrations, run ``alembic -c biweeklybudget/alembic/alembic.ini upgrade head``.
* To see the current DB version, run ``alembic -c biweeklybudget/alembic/alembic.ini current``.
* To see migration history, run ``alembic -c biweeklybudget/alembic/alembic.ini history``.

Database Debugging
------------------

If you set the ``SQL_ECHO`` environment variable to "true", all SQL run by
SQLAlchemy will be logged at INFO level.

To get an interactive Python shell with the database initialized, use ``python -i bin/db_tester.py``.

Docker Image Build
------------------

Use the ``docker`` tox environment. See the docstring at the top of
``biweeklybudget/tests/docker_build.py`` for further information.

Frontend / UI
-------------

The UI is based on `BlackrockDigital's startbootstrap-sb-admin-2 <https://github.com/BlackrockDigital/startbootstrap-sb-admin-2>`_,
currently as of the 3.3.7-1 GitHub release. It is currently not modified at all, but should it need to be rebuilt,
this can be done with: ``pushd biweeklybudget/flaskapp/static/startbootstrap-sb-admin-2 && gulp``

Sphinx also generates documentation for the custom javascript files. This must be done manually
on a machine with `jsdoc <http://usejsdoc.org/>`_ installed, via: ``tox -e jsdoc``.

.. _development.vendored_requirements:

Vendored Requirements
---------------------

A number of this project's dependencies are or were seemingly abandoned, and weren't
responding to bugfix pull requests or weren't pushing new releases to PyPI. This made
the installation process painful, as it required ``pip install -r requirements.txt``
to pull in git requirements.

In an attempt to make installation easier, we've vendored any git requirements in to
this repository under ``biweeklybudget/vendored/``. The intent is to move these back
to ``setup.py`` requirements when each project includes the fixes we need in its
official release on PyPI.

To updated the vendored projects:

1. Update ``biweeklybudget/vendored/vendored_requirements.txt``
2. Run ``cd biweeklybudget/vendored && install_vendored.sh``
3. Ensure that our main ``setup.py`` includes all dependencies of the vendored projects.

Release Checklist
-----------------

1. Open an issue for the release; cut a branch off master for that issue.
2. Verify whether or not DB migrations are needed. If they are, ensure they've been created, tested and verified.
3. Confirm that there are CHANGES.rst entries for all major changes.
4. Rebuild documentation and javascript documentation locally: ``tox -e jsdoc,docs``. Commit any changes.
5. Run the Docker image build and tests locally: ``tox -e docker``. If the pull request includes changes to the Dockerfile
   or the container build process, run acceptance tests against the newly-built container as described above.
6. Ensure that Travis tests passing in all environments.
7. Ensure that test coverage is no less than the last release, and that there are acceptance tests for any non-trivial changes.
8. If there have been any major visual or functional changes to the UI, regenerate screenshots via ``tox -e screenshots``.
9. Increment the version number in biweeklybudget/version.py and add version and release date to CHANGES.rst, then push to GitHub.
10. Run ``dev/release.py gist`` to convert the CHANGES.rst entry for the current version to Markdown and upload it as a Github Gist. View the gist and ensure that the Markdown rendered properly and all links are valid. Iterate on this until the rendered version looks correct.
11. Confirm that README.rst renders correctly on GitHub.
12. Upload package to testpypi:

   * Make sure your ~/.pypirc file is correct (a repo called ``test`` for https://testpypi.python.org/pypi)
   * ``rm -Rf dist``
   * ``python setup.py sdist bdist_wheel``
   * ``twine upload -r test dist/*``
   * Check that the README renders at https://testpypi.python.org/pypi/biweeklybudget

13. Create a pull request for the release to be merged into master. Upon successful Travis build, merge it.
14. Tag the release in Git (using a signed tag), push tag to GitHub:

   * tag the release with a signed tag: ``git tag -s -a X.Y.Z -m 'X.Y.Z released YYYY-MM-DD'``
   * verify the signature: ``git tag -v X.Y.Z``
   * push the tag to GitHub: ``git push origin X.Y.Z``

15. Upload package to live pypi:

    * ``twine upload dist/*``

16. Run ``dev/release.py release`` to create the release on GitHub.
17. Build and push the new Docker image:

   * Check out the git tag: ``git checkout X.Y.Z``
   * Build the Docker image: ``DOCKER_BUILD_VER=X.Y.Z tox -e docker``
   * Follow the instructions from that script to push the image to the
     Docker Hub and tag a "latest" version.

18. make sure any GH issues fixed in the release were closed.
19. Log in to readthedocs.org and enable building of the release tag. You may need to re-run another build to get the tag to be picked up.
