Changelog
=========

1.1.1 (2022-12-30)
------------------

* Docker build - don't include ``-dirty`` in version/tag when building in GHA
* Document how to change Plaid environments
* GHA - Push built Docker images to Docker Hub, for builds of master branch
* Document triggering a Plaid update via the ``/plaid-update`` endpoint.
* Change ``/plaid-update`` endpoint argument name from ``account_ids`` to ``item_ids``.
* Add ``num_days`` parameter support to ``/plaid-update`` endpoint.

1.1.0 (2022-12-29)
------------------

Breaking Changes
++++++++++++++++

* Support for Python versions prior to 3.8 have been dropped; Docker image and testing is now done against Python 3.10.
* Valid values for the ``PLAID_ENV`` setting / environment variable are now the strings "Production", "Development", or "Sandbox" to match the attribute names of ``plaid.configuration.Environment``. Previously these were lower-case instead of capitalized.
* The ``PLAID_PUBLIC_KEY`` setting / environment variable has been removed.
* OFX support is now **deprecated**; going forward, only Plaid will be supported.

All Changes
+++++++++++

* **Drop Python 2 Support and Python 3.5 Support** - biweeklybudget no longer supports Python 2 (2.7) or Python 3.5. Python versions 3.6-3.8 are tested, and development is now done on 3.8.
* `Issue #201 <https://github.com/jantman/biweeklybudget/issues/201>`_ - Fix **major** bug in calculation of "Remaining" amount for pay periods, when one or more periodic budgets have a greater amount spent than allocated and a $0 starting balance. In that case, we were using the allocated amount instead of the spent amount (i.e. if we had a periodic budget with a $0 starting balance and a $2 ScheduledTransaction, and converted that ScheduledTransaction to a $1000 Transaction, the overall PayPeriod remaining amount would be based on the $2 not the $1000).
* Add testing for Python 3.7 and 3.8, and make 3.8 the default for tests and tox environments.
* TravisCI updates for Python 3.7 and 3.8.
* Switch base image for Docker from ``python:3.6.4-alpine3.7`` to ``python:3.8.1-alpine3.11``.
* `Issue #198 <https://github.com/jantman/biweeklybudget/issues/198>`_ - Fix broken method of retrieving current US Prime Rate. Previously we used marketwatch.com for this but they've introduced javascript-based bot protection on their site (which is ironic since we were reading a value from the page's ``meta`` tags, which are specifically intended to be read by machines). Switch to using wsj.com instead and (ugh) parsing a HTML table. This *will* break when the format of the table changes. As previously, we cache this value in the DB for 48 hours in order to be a good citizen.
* `Issue #197 <https://github.com/jantman/biweeklybudget/issues/197>`_ - Add notification for case where balance of all budget-funding accounts is *more* than sum of standing budgets, current payperiod remaining, and unreconciled. This is the opposite of the similar notification that already exists, intended to detect if there is money in accounts not accounted for in the budgets.
* `Issue #196 <https://github.com/jantman/biweeklybudget/issues/196>`_ - Don't include inactive budgets in Budget select elements on Transaction Modal form, unless it's an existing Transaction using that budget.
* `Issue #204 <https://github.com/jantman/biweeklybudget/issues/204>`_ - Add support for account transfer between non-Credit accounts.
* Many dependency updates:

  * Upgrade SQLAlchemy from 1.2.0 to 1.2.11 for `python 3 bug fix (4291) <https://docs.sqlalchemy.org/en/latest/changelog/changelog_12.html#change-2cca6c216347ab83d04c766452b48c1a>`_.
  * Upgrade SQLAlchemy from 1.2.11 to 1.3.13 for `CVE-2019-7548 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-7548>`_ and `CVE-2019-7164 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-7164>`_.
  * Upgrade Flask from 0.12.2 to 1.0.2 for `CVE-2018-1000656 <https://nvd.nist.gov/vuln/detail/CVE-2018-1000656>`_.
  * Upgrade cryptography from 2.1.4 to 2.3.1 for `CVE-2018-10903 <https://nvd.nist.gov/vuln/detail/CVE-2018-10903>`_.
  * Upgrade Jinja2 from 2.10 to 2.10.3 for `CVE-2019-10906 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-10906>`_.
  * Upgrade to latest version for all dependencies.

* Remove ``convert_unicode`` argument from SQLAlchemy DB engine arguments per SQLAlchemy 1.3 upgrade guide / `SQLAlchemy #4393 <https://github.com/sqlalchemy/sqlalchemy/issues/4393>`_.
* Numerous updates to fix ``tox`` tests.
* Implement transaction downloading via `Plaid <https://plaid.com/>`__.
* Switch tests from deprecated ``pep8`` / ``pytest-pep8`` packages to ``pycodestyle`` / ``pytest-pycodestyle``.
* Add optional ``VERSIONFINDER_DEBUG`` env var; set to ``true`` to enable logging for versionfinder / pip / git.
* Drop testing for Python 3.6; move default test environment to 3.9.
* Add ``git`` to Docker image.
* Move testing and runtime to Python 3.10, and get all test environments running successfully.
* Move CI from TravisCI to GitHub Actions and remove all traces of TravisCI.
* Add acceptance test coverage of the Plaid Link process.
* Updates for ``tox`` 4.0.6.
* Update Plaid API client to latest version

  * Valid values for the ``PLAID_ENV`` setting / environment variable are now the strings "Production", "Development", or "Sandbox" to match the attribute names of ``plaid.configuration.Environment``.
  * The ``PLAID_PUBLIC_KEY`` setting / environment variable has been removed.

1.0.0 (2018-07-07)
------------------

* Fix major logic error in Credit Card Payoff calculations; interest fees were ignored for the current month/statement, resulting in "Next Payment" values significantly lower than they should be. Fixed to use the last Interest Charge retrieved via OFX (or, if no interest charges present in OFX statements, prompt users to manually enter the last Interest Charge via a new modal that will create an OFXTransaction for it) as the interest amount on the first month/statement when calculating payoffs. This fix now returns Next Payment values that aren't identical to sample cards, but are significantly closer (within 1-2%).
* `Issue #105 <https://github.com/jantman/biweeklybudget/issues/105>`_ - Major refactor to the Transaction database model. This is transparent to users, but causes massive database and code changes. This is the first step in supporting Transaction splits between multiple budgets:

  * A new BudgetTransaction model has been added, which will support a one-to-many association between Transactions and Budgets. This model associates a Transaction with a Budget, and a currency amount counted against that Budget. This first step only supports a one-to-one relationship, but a forthcoming change will implement the one-to-many budget split for Transactions.
  * The database migration for this creates BudgetTransactions for every current Transaction, migrating data to the new format.
  * The ``budget_id`` attribute and ``budget`` relationship of the Transaction model has been removed, as that information is now in the related BudgetTransactions.
  * A new ``planned_budget_id`` attribute (and ``planned_budget`` relationship) has been added to the Transaction model. For Transactions that were created from ScheduledTransactions, this attribute/relationship stores the original planned budget (distinct from the actual budget now stored in BudgetTransactions).
  * The Transaction model now has a ``budget_transactions`` back-populated property, containing a list of all associated BudgetTransactions.
  * The Transaction model now has a ``set_budget_amounts()`` method which takes a single dict mapping either integer Budget IDs or Budget objects, to the Decimal amount of the Transaction allocated to that Budget. While the underlying API supports an arbitrary number of budgets, the UI and codebase currently only supports one.
  * The Transaction constructor now accepts a ``budget_amounts`` keyword argument that passes its value through to ``set_budget_amounts()``, for ease of creating Transactions in one call.
  * ``Transaction.actual_amount`` is no longer an attribute stored in the database, but now a hybrid property (read-only) generated from the sum of amounts of all related BudgetTransactions.
  * Add support to serialize property values of models, in addition to attributes.

* Relatively major and sweeping code refactors to support the above.
* Switch tests from using deprecated pytest-capturelog to using pytest built-in log capturing.
* Miscellaneous fixes to unit and acceptance tests, and docs build.
* Finish converting *all* code, including tests and sample data, from using floats to Decimals.
* Acceptance test fix so that pytest-selenium can take full page screenshots with Chromedriver.
* `PR #180 <https://github.com/jantman/biweeklybudget/pull/180>`_ - Acceptance test fix so that the testflask LiveServer fixture captures server logs, and includes them in test HTML reports (this generates a temporary file per-test-run outside of pytest's control).
* Fix bug found where simultaneously editing the Amount and Budget of an existing Transaction against a Standing Budget would result in incorrect changes to the balances of the Budgets.
* Add a new ``migrations`` tox environment that automatically tests all database migrations (forward and reverse) and also validates that the database schema created from the migrations matches the one created from the models.
* Add support for writing tests of data manipulation during database migrations, and write tests for the migration in for Issue 105, above.
* Add support for ``BIWEEKLYBUDGET_LOG_FILE`` environment variable to cause Flask application logs to go to a file *in addition to* STDOUT.
* Add support for ``SQL_POOL_PRE_PING`` environment variable to enable SQLAlchemy ``pool_pre_ping`` feature (see `Disconnect Handling - Pessimistic <http://docs.sqlalchemy.org/en/latest/core/pooling.html#pool-disconnects-pessimistic>`_) for resource-constrained systems.
* Modify acceptance tests to retry up to 3 times, 3 seconds apart, if a ConnectionError (or subclass thereof) is raised when constructing the Selenium driver instance. This is a workaround for intermittent ConnectionResetErrors in TravisCI.
* `Issue #177 <https://github.com/jantman/biweeklybudget/issues/177>`_

  * Add SQL query timing support via ``SQL_QUERY_PROFILE`` environment variable.
  * When running under ``flask rundev``, append the number of milliseconds taken to serve the request to the werkzeug access log.
  * When running under Docker/Gunicorn, append the decimal number of seconds taken to serve the request to the Gunicorn access log.

* `Issue #184 <https://github.com/jantman/biweeklybudget/issues/184>`_ - Redact database password from ``/help`` view, and change ``/help`` view to show Version containing git commit hash for pre-release/development Docker builds.
* `Issue #183 <https://github.com/jantman/biweeklybudget/issues/183>`_

  * Add UI link to ignore reconciling an OFXTransaction if there will not be a matching Transaction.
  * Remove default values for the ``Account`` model's ``re_`` fields in preparation for actually using them.
  * Replace the ``Account`` model's ``re_fee`` field with separate ``re_late_fee`` and ``re_other_fee`` fields.
  * Add UI support for specifying Interest Charge, Interest Paid, Payment, Late Fee, and Other Fee regexes on each account.
  * Add DB event handler on new or changed OFXTransaction, to set ``is_*`` fields according to Account ``re_*`` fields.
  * Add DB event handler on change to Account model ``re_*`` fields, that triggers ``OFXTransaction.update_is_fields()`` to recalculate using the new regex.
  * Change ``OFXTransaction.unreconciled`` to filter out OFXTransactions with any of the ``is_*`` set to True.

* Upgrade chromedriver in TravisCI builds from 2.33 to 2.36, to fix failing acceptance tests caused by Ubuntu upgrade from Chrome 64 to 65.
* Fix bug in ``/budgets`` view where "Spending By Budget, Per Calendar Month" chart was showing only inactive budgets instead of only active budgets.
* `Issue #178 <https://github.com/jantman/biweeklybudget/issues/178>`_ - UI support for splitting Transactions between multiple Budgets.
* Have frontend forms submit as JSON POST instead of urlencoded.
* Properly capture Chrome console logs during acceptance tests.
* Bump ``versionfinder`` requirement version to 0.1.3 to work with pip 9.0.2.
* On help view, show long version string if we have it.
* `Issue #177 <https://github.com/jantman/biweeklybudget/issues/177>`_ - Fix bug in ``flask rundev`` logging.
* Many workarounds for flaky acceptance tests, including some for the selenium/Chrome "Element is not clickable at point... Other element would receive the click" error.
* ``biweeklybudget.screenscraper.ScreenScraper`` - Save webdriver and browser logs on failure, and set Chrome to capture all logs.
* ``biweeklybudget.screenscraper.ScreenScraper`` - Add option to explicitly set a User-Agent on Chrome or PhantomJS.
* `Issue #192 <https://github.com/jantman/biweeklybudget/issues/192>`_ - Fix bug where the ``is_`` fields weren't set on OFXTransactions when created via ofxgetter remote API.
* ``ofxgetter`` - add support to list all accounts at the Institution of one account
* ``ofxgetter`` - add ability to specify how many days of data to retrieve

0.7.1 (2018-01-10)
------------------

* `Issue #170 <https://github.com/jantman/biweeklybudget/issues/170>`_ - Upgrade **all** python dependencies to their latest versions.
* `Issue #171 <https://github.com/jantman/biweeklybudget/issues/171>`_ - Upgrade Docker base image from ``python:3.6.3-alpine3.4`` to ``python:3.6.4-alpine3.7``.
* `Issue #157 <https://github.com/jantman/biweeklybudget/issues/157>`_ - Remove PhantomJS from Docker image, as it's broken and shouldn't be needed.
* Switch TravisCI builds from Docker (``sudo: false``) to VM (``sudo: enabled``) infrastructure.

0.7.0 (2018-01-07)
------------------

**This version has a remote OFX upload incompatibility. See below.**

* `Issue #156 <https://github.com/jantman/biweeklybudget/issues/156>`_ - Add headless chrome support to ``screenscraper.py``.
* Remove ``pluggy`` transient dependency from requirements.txt; was breaking builds.
* Following pytest, drop testing of and support for Python 3.3.
* `Issue #159 <https://github.com/jantman/biweeklybudget/issues/159>`_ - Implement internationalization of volume and distance units for Fuel Log pages. This change introduces five new settings: ``FUEL_VOLUME_UNIT``, ``FUEL_VOLUME_ABBREVIATION``, ``DISTANCE_UNIT``, ``DISTANCE_UNIT_ABBREVIATION`` and ``FUEL_ECO_ABBREVIATION``.
* `Issue #154 <https://github.com/jantman/biweeklybudget/issues/154>`_ - Fix documentation errors on the Getting Started page, "Running ofxgetter in Docker" section.
* `Issue #152 <https://github.com/jantman/biweeklybudget/issues/152>`_ - Fix for bug where new Transactions could be entered against inactive budgets. Ensure that existing transactions against inactive budgets can still be edited, but existing transactions cannot be changed to an inactive budget.
* `Issue #161 <https://github.com/jantman/biweeklybudget/issues/161>`_ - Fix bug where Transactions against inactive budgets weren't counted towards payperiod overall or per-budget totals.
* `Issue #163 <https://github.com/jantman/biweeklybudget/issues/163>`_ - Include next payment amount on Credit Payoffs view.
* `Issue #84 <https://github.com/jantman/biweeklybudget/issues/84>`_ - Remove vendored-in ``ofxparse`` package now that `my PR #127 <https://github.com/jseutter/ofxparse/pull/127>`_ has been merged and released on PyPI. **Important note:** The version of ofxparse is changed in this release. If you are using ``ofxgetter -r`` (remote API mode), the versions of ofxparse (and therefore biweeklybudget/ofxgetter) must match between the client and server.
* `Issue #165 <https://github.com/jantman/biweeklybudget/issues/165>`_ - Remove vendored-in ``wishlist`` package now that `my PR #8 <https://github.com/Jaymon/wishlist/pull/8>`_ has been merged and released on PyPI.
* `Issue #155 <https://github.com/jantman/biweeklybudget/issues/155>`_ - Refactor ofxgetter to fix bug where ``SETTINGS_MODULE`` was still required even if running remotely.

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
