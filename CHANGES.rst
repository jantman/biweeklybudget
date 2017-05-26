Changelog
=========

Unreleased Changes
------------------

* Minor fix to instructions printed after release build in ``biweeklybudget/tests/docker_build.py``
* `Issue #61 <https://github.com/jantman/biweeklybudget/issues/61>`_ - Document running ``ofxgetter`` in the Docker container.
* fix ReconcileRule repr for uncommited (id is None)
* `Issue #67 <https://github.com/jantman/biweeklybudget/issues/67>`_ - ofxgetter logging -
  suppress DB and Alembic logging at INFO and above; log number of inserted  and updated transactions.
* `Issue #71 <https://github.com/jantman/biweeklybudget/issues/71>`_ - Fix display text next to prev/curr/next periods on ``/payperiod/YYYY-mm-dd`` view; add 6 more future pay periods to the ``/payperiods`` table.
* `Issue #72 <https://github.com/jantman/biweeklybudget/issues/72>`_ - Add a built-in method for transferring money from periodic (per-pay-period) to standing budgets; add budget Transfer buttons on Budgets and Pay Period views.

0.1.1 (2017-05-20)
------------------

* Improve ofxgetter/ofxupdater error handling; catch OFX files with error messages in them.
* `Issue #62 <https://github.com/jantman/biweeklybudget/issues/62>`_ - Fix phantomjs in Docker image.
  * Allow docker image tests to run against an existing image, defined by ``DOCKER_TEST_TAG``.
  * Retry MySQL DB creation during Docker tests until it succeeds, or fails 10 times.
  * Add testing of PhantomJS in Docker image testing; check version and that it actually works (GET a page).
  * More reliable stopping and removing of Docker containers during Docker image tests.
* `Issue #63 <https://github.com/jantman/biweeklybudget/issues/63>`_ - Enable gunicorn request logging in Docker container.
* Switch to my fork of ofxclient in requirements.txt, to pull in `ofxclient PR #41 <https://github.com/captin411/ofxclient/pull/41>`_
* `Issue #64 <https://github.com/jantman/biweeklybudget/issues/64>`_ - Fix duplicate/multiple on click event handlers in UI that were causing duplicate transactions.

0.1.0 (2017-05-07)
------------------

* Initial Release
