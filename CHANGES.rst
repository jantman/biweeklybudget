Changelog
=========

0.4.0 (2017-08-22)
------------------

* Have ``ofxgetter`` enable ofxclient logging when running at DEBUG level (``-vv``).
* Bump ofxclient requirement to my `vanguard-fix <https://github.com/jantman/ofxclient/tree/vanguard-fix>`_ branch
  for `PR #47 <https://github.com/captin411/ofxclient/pull/47>`_.
* `Issue #101 <https://github.com/jantman/biweeklybudget/issues/101>`_ - Fix static example amounts on ``/projects`` view.
* `Issue #103 <https://github.com/jantman/biweeklybudget/issues/103>`_ - Show most recent MPG in notification box after adding fuel fill.
* `Issue #97 <https://github.com/jantman/biweeklybudget/issues/97>`_ - Fix integration tests that are date-specific and break on certain dates (run all integration tests as if it were a fixed date).
* `Issue #104 <https://github.com/jantman/biweeklybudget/issues/104>`_ - Relatively major changes to add calculation of Credit account payoff times and amounts.
* `Issue #107 <https://github.com/jantman/biweeklybudget/issues/107>`_ - Fix bug where Budget Transfer modal dialog would always default to current date, even when viewing past or future pay periods.
* `Issue #48 <https://github.com/jantman/biweeklybudget/issues/48>`_ - UI support for adding and editing accounts.

0.3.0 (2017-07-09)
------------------

* `Issue #88 <https://github.com/jantman/biweeklybudget/issues/88>`_ - Add tracking of cost for Projects and Bills of Materials (BoM) for them.
* Add script / entry point to sync Amazon Wishlist with a Project.
* `Issue #74 <https://github.com/jantman/biweeklybudget/issues/74>`_ - Another attempt at working over-balance notification.

0.2.0 (2017-07-02)
------------------

* Fix ``/pay_period_for`` redirect to be a 302 instead of 301, add redirect logging, remove some old debug logging from that view.
* Fix logging exception in db_event_handlers on initial data load.
* Switch ofxparse requirement to use upstream repo now that https://github.com/jseutter/ofxparse/pull/127 is merged.
* `Issue #83 <https://github.com/jantman/biweeklybudget/issues/83>`_ - Fix 500 error preventing display of balance chart on ``/`` view when an account has a None ledger balance.
* `Issue #86 <https://github.com/jantman/biweeklybudget/issues/86>`_ - Allow budget transfers to periodic budgets.
* `Issue #74 <https://github.com/jantman/biweeklybudget/issues/74>`_ - Warning notification for low balance should take current pay period's overall allocated sum, minus reconciled transactions, into account.
* Fix some template bugs that were causing HTML to be escaped into plaintext.
* `Issue #15 <https://github.com/jantman/biweeklybudget/issues/15>`_ - Add pay period totals table to index page.
* Refactor form generation in UI to use new FormBuilder javascript class (DRY).
* Fix date-sensitive acceptance test.
* `Issue #87 <https://github.com/jantman/biweeklybudget/issues/87>`_ - Add fuel log / fuel economy tracking.

0.1.2 (2017-05-28)
------------------

* Minor fix to instructions printed after release build in ``biweeklybudget/tests/docker_build.py``
* `Issue #61 <https://github.com/jantman/biweeklybudget/issues/61>`_ - Document running ``ofxgetter`` in the Docker container.
* fix ReconcileRule repr for uncommited (id is None)
* `Issue #67 <https://github.com/jantman/biweeklybudget/issues/67>`_ - ofxgetter logging -
  suppress DB and Alembic logging at INFO and above; log number of inserted  and updated transactions.
* `Issue #71 <https://github.com/jantman/biweeklybudget/issues/71>`_ - Fix display text next to prev/curr/next periods on ``/payperiod/YYYY-mm-dd`` view; add 6 more future pay periods to the ``/payperiods`` table.
* `Issue #72 <https://github.com/jantman/biweeklybudget/issues/72>`_ - Add a built-in method for transferring money from periodic (per-pay-period) to standing budgets; add budget Transfer buttons on Budgets and Pay Period views.
* `Issue #75 <https://github.com/jantman/biweeklybudget/issues/75>`_ - Add link on payperiod views to skip a ScheduledTransaction instance this period.
* `Issue #57 <https://github.com/jantman/biweeklybudget/issues/57>`_ - Ignore future transactions from unreconciled transactions list.
* Transaction model - fix default for ``date`` field to actually be just a date; previously, Transactions with ``date`` left as default would attempt to put a full datetime into a date column, and throw a data truncation warning.
* Transaction model - Fix ``__repr__`` to not throw exception on un-persisted objects.
* When adding or updating the ``actual_amount`` of a Transaction against a Standing Budget, update the ``current_balance`` of the budget.
* Fix ordering of Transactions table on Pay Period view, to properly sort by date and then amount.
* Numerous fixes to date-sensitive acceptance tests.
* `Issue #79 <https://github.com/jantman/biweeklybudget/issues/79>`_ - Update ``/pay_period_for`` view to redirect to current pay period when called with no query parameters; add bookmarkable link to current pay period to Pay Periods view.

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
