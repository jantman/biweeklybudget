Changelog
=========

0.6.0 (2017-11-11)
------------------

* `PR #140 <https://github.com/jantman/biweeklybudget/issues/140>`_ - Support user-configurable currencies and currency formatting.
  This isn't all-out localization, but adds ``CURRENCY_CODE`` and ``LOCALE_NAME`` configuration settings to control the currency symbol
  and formatting used in the user interface and logs.
* `PR #141 <https://github.com/jantman/biweeklybudget/pull/141>`_ - Switch acceptance tests from PhantomJS to headless Chrome.
* Switch docs build screenshot script to use headless Chrome instead of PhantomJS.
* `Issue #142 <https://github.com/jantman/biweeklybudget/issues/142>`_ - Speed up acceptance tests. The acceptance tests recently crossed the 20-minute barrier, which is unacceptable. This makes some improvements to the tests, mainly around combining classes that can be combined and also using mysql/mysqldump to refresh the DB, instead of refreshing and recreating via the ORM. That offers a approximately 50-90% speed improvement for each of the 43 refreshes. Unfortunately, it seems that the majority of time is taken up by pytest-selenium; see Issue 142 for further information.
* `Issue #125 <https://github.com/jantman/biweeklybudget/issues/125>`_ - Switch Docker image base from ``python:3.6.1`` (Debian) to ``python:3.6.3-alpine3.4`` (Alpine Linux); drops final image size from 876MB to 274MB. (*Note:* Alpine linux does not have ``/bin/bash``.)
* `Issue #138 <https://github.com/jantman/biweeklybudget/issues/138>`_ - Improvements to build process

  * Run acceptance tests against the built Docker container during runs of the ``docker`` tox environment / ``tests/docker_build.py``.
  * Reminder to sign git release tags
  * Add ``dev/release.py`` script to handle GitHub releases.

* `Issue #139 <https://github.com/jantman/biweeklybudget/issues/139>`_ - Add field to Budget model to allow omitting specific budgets from spending graphs (the graphs on the Budgets view).

0.5.0 (2017-10-28)
------------------

**This release includes database migrations.**

* `Issue #118 <https://github.com/jantman/biweeklybudget/issues/118>`_ - PR to fix bugs in the
  `wishlist <https://github.com/Jaymon/wishlist>`_ dependency package, and vendor that patched
  version in under ``biweeklybudget.vendored.wishlist``.
* `Issue #113 <https://github.com/jantman/biweeklybudget/issues/113>`_ - vendor in other
  git requirements (ofxclient and ofxparse) that seem unmaintained or inactive, so we can install via ``pip``.
* `Issue #115 <https://github.com/jantman/biweeklybudget/issues/115>`_ - In Transactions view, add ability to filter by budget.
* Change ``BiweeklyPayPeriod`` class to never convert to floats (always use decimal.Decimal types).
* `Issue #124 <https://github.com/jantman/biweeklybudget/issues/124>`_ - Major changes to the ``ofxgetter`` and ``ofxbackfiller`` console scripts; centralize all database access in them to the new ``biweeklybudget.ofxapi.local.OfxApiLocal`` class and allow these scripts to function remotely, interacting with the ReST API instead of requiring direct database access.
* `Issue #123 <https://github.com/jantman/biweeklybudget/issues/123>`_ - Modify the Credit Payoffs view to allow removal of Increase and Onetime Payment settings lines.
* `Issue #131 <https://github.com/jantman/biweeklybudget/issues/131>`_ - Add better example data for screenshots.
* `Issue #117 <https://github.com/jantman/biweeklybudget/issues/117>`_ and `#133 <https://github.com/jantman/biweeklybudget/issues/133>`_ - Implement and then revert out a failed attempt at automatic balancing of budgets in the previous pay period.
* `Issue #114 <https://github.com/jantman/biweeklybudget/issues/114>`_

  * Add ``transfer_id`` field and ``transfer`` relationship to Transaction model, to link the halves of budget transfer transactions in the database. The alembic migration for this release iterates all Transactions in the database, and populates these links based on inferences of the description, date, account_id and notes fields of sequential pairs of Transactions. (Note: this migration would likely miss some links if two transfers were created simultaneously, and ended up with the Transaction IDs interleaved).
  * Identify transfer Transactions on the Edit Transaction modal, and provide link to the matching Transaction.
  * Add graph of spending by budget to Budgets view.
* `Issue #133 <https://github.com/jantman/biweeklybudget/issues/133>`_ - Change BiweeklyPayPeriod model to only use actual spent amount when creating remaining amount on payperiods in the past. Previously, all pay periods calculated the overall "remaining" amount as income minus the greater of ``allocated`` or ``spent``; this resulted in pay periods in the past still including allocated-but-not-spent amounts counted against "remaining".

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
