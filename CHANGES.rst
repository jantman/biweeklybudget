Changelog
=========

Unreleased Changes
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
