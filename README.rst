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

.. code-block:: bash

    pip install biweeklybudget

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
