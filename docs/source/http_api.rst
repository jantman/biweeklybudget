.. _http_api:

HTTP API
========

biweeklybudget exposes a number of HTTP endpoints that can be used by external scripts and tools to create transactions, query data, and drive other application functions without using the web UI. This page documents the endpoints most useful for scripting and automation.

All examples assume biweeklybudget is running at ``http://127.0.0.1:8080``.

.. _http_api.common_patterns:

Common Patterns
---------------

.. _http_api.common_patterns.request_format:

Request Format
++++++++++++++

Most write endpoints accept either JSON or form-encoded POST data. When sending JSON, set the ``Content-Type: application/json`` header. The examples in this document use JSON.

.. note::

   JSON is **strongly recommended** over form-encoded data. Some endpoints (e.g. ``/forms/transaction``) require nested objects (like the ``budgets`` field) that cannot be represented in form-encoded format. Form-encoded data will flatten these to strings, causing server errors.

.. _http_api.common_patterns.response_format:

FormHandlerView Response Format
+++++++++++++++++++++++++++++++

Endpoints built on :py:class:`~.FormHandlerView` return a consistent JSON response structure.

On success:

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved Transaction 123 in database."
    }

Some endpoints include additional fields in the success response (documented per-endpoint).

On validation error:

.. code-block:: json

    {
      "success": false,
      "errors": {
        "field_name": ["Error message 1", "Error message 2"]
      }
    }

On submission error (exception during save):

.. code-block:: json

    {
      "success": false,
      "error_message": "Description of the error."
    }

.. _http_api.transactions:

Transactions
------------

.. _http_api.transactions.create_update:

Create or Update a Transaction
++++++++++++++++++++++++++++++

``POST /forms/transaction``

Create a new :py:class:`~.Transaction` or update an existing one. Handled by :py:class:`~.TransactionFormHandler`.

**Request Fields:**

- ``id`` *(integer, optional)* - Transaction ID. If provided, updates the existing transaction; if omitted, creates a new one.
- ``description`` *(string, required)* - Transaction description. Cannot be empty.
- ``amount`` *(decimal, required)* - Transaction amount. Cannot be zero.
- ``account`` *(integer, required)* - :py:class:`~.Account` ID.
- ``date`` *(string, required)* - Date in ``YYYY-MM-DD`` format.
- ``notes`` *(string, required)* - Free-text notes. Use an empty string if not needed. Although semantically optional, this field **must be present** in the request or the server will return a 500 error.
- ``sales_tax`` *(decimal, optional)* - Sales tax amount. Defaults to ``0``.
- ``budgets`` *(object, required)* - A mapping of :py:class:`~.Budget` ID (as string key) to the decimal amount allocated to that budget. At least one budget is required, and the sum of all budget amounts must equal the transaction ``amount``. New transactions cannot use inactive budgets.

  .. note::

     This field must be a JSON object (``{"2": "52.34"}``), not a JSON-encoded string. This means you **must** use ``Content-Type: application/json`` for this endpoint; form-encoded POST data cannot represent nested objects.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"description": "Grocery Store", "amount": "52.34", "account": "1", "date": "2017-07-15", "notes": "", "budgets": {"2": "52.34"}}' \
        http://127.0.0.1:8080/forms/transaction

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved Transaction 123 in database.",
      "trans_id": 123
    }

.. _http_api.transactions.get:

Get a Single Transaction
++++++++++++++++++++++++

``GET /ajax/transactions/<int:trans_id>``

Retrieve details of a single :py:class:`~.Transaction` by ID.

**Example Request:**

.. code-block:: bash

    $ curl http://127.0.0.1:8080/ajax/transactions/123

**Response:**

Returns a JSON object with all :py:class:`~.Transaction` fields plus:

- ``account_name`` *(string)* - Name of the associated account.
- ``budgets`` *(array)* - Array of budget allocation objects, each containing:

  - ``name`` *(string)* - Budget name.
  - ``id`` *(integer)* - Budget ID.
  - ``amount`` *(decimal)* - Amount allocated to this budget.
  - ``is_income`` *(boolean)* - Whether this is an income budget.

.. code-block:: json

    {
      "id": 123,
      "description": "Grocery Store",
      "date": "2017-07-15",
      "actual_amount": 52.34,
      "sales_tax": 0.0,
      "account_id": 1,
      "account_name": "BankOne",
      "notes": null,
      "scheduled_trans_id": null,
      "budgets": [
        {"name": "Food", "id": 2, "amount": 52.34, "is_income": false}
      ]
    }

.. _http_api.transactions.sched_to_trans:

Create Transaction from Scheduled Transaction
++++++++++++++++++++++++++++++++++++++++++++++

``POST /forms/sched_to_trans``

Convert a :py:class:`~.ScheduledTransaction` into an actual :py:class:`~.Transaction`. The new transaction inherits the budget from the scheduled transaction. Handled by :py:class:`~.SchedToTransFormHandler`.

**Request Fields:**

- ``id`` *(integer, required)* - :py:class:`~.ScheduledTransaction` ID.
- ``date`` *(string, required)* - Date in ``YYYY-MM-DD`` format. Must be within the current pay period.
- ``description`` *(string, required)* - Transaction description. Cannot be empty.
- ``amount`` *(decimal, required)* - Transaction amount. Cannot be zero.
- ``sales_tax`` *(decimal, optional)* - Sales tax amount. Defaults to ``0``.
- ``notes`` *(string, optional)* - Free-text notes.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"id": "5", "date": "2017-07-15", "description": "Phone Bill", "amount": "80.00"}' \
        http://127.0.0.1:8080/forms/sched_to_trans

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully created Transaction 456 for ScheduledTransaction 5."
    }

.. _http_api.transactions.skip_sched:

Skip a Scheduled Transaction
+++++++++++++++++++++++++++++

``POST /forms/skip_sched_trans``

Skip a :py:class:`~.ScheduledTransaction` for a specific pay period by creating a $0 Transaction as a record. Handled by :py:class:`~.SkipSchedTransFormHandler`.

**Request Fields:**

- ``id`` *(integer, required)* - :py:class:`~.ScheduledTransaction` ID.
- ``payperiod_start_date`` *(string, required)* - Start date of the pay period in ``YYYY-MM-DD`` format.
- ``notes`` *(string, required)* - Reason for skipping. Cannot be empty.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"id": "5", "payperiod_start_date": "2017-07-07", "notes": "Paid in advance last month"}' \
        http://127.0.0.1:8080/forms/skip_sched_trans

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully created Transaction 789 to skip ScheduledTransaction 5."
    }

.. _http_api.scheduled:

Scheduled Transactions
----------------------

.. _http_api.scheduled.create_update:

Create or Update a Scheduled Transaction
+++++++++++++++++++++++++++++++++++++++++

``POST /forms/scheduled``

Create a new :py:class:`~.ScheduledTransaction` or update an existing one. Handled by :py:class:`~.ScheduledFormHandler`.

**Request Fields:**

- ``id`` *(integer, optional)* - ScheduledTransaction ID. If provided, updates the existing record.
- ``description`` *(string, required)* - Description. Cannot be empty.
- ``amount`` *(decimal, required)* - Amount. Cannot be zero.
- ``sales_tax`` *(decimal, optional)* - Sales tax amount. Defaults to ``0``.
- ``account`` *(integer, required)* - :py:class:`~.Account` ID.
- ``budget`` *(integer, required)* - :py:class:`~.Budget` ID.
- ``notes`` *(string, optional)* - Free-text notes.
- ``is_active`` *(boolean, optional)* - Whether the scheduled transaction is active.
- ``type`` *(string, required)* - Schedule type. One of:

  - ``monthly`` - Recurs on a specific day of each month. Requires ``day_of_month`` *(integer)*.
  - ``per_period`` - Recurs a fixed number of times per pay period. Requires ``num_per_period`` *(integer)*.
  - ``weekly`` - Recurs on a specific day of each week. Requires ``day_of_week`` *(integer, 0=Monday through 6=Sunday)*.
  - ``annual`` - Recurs on a specific month and day each year. Requires ``annual_month`` *(integer, 1-12)* and ``annual_day`` *(integer, 1-31)*.
  - ``date`` - Occurs on a single specific date. Requires ``date`` *(string, YYYY-MM-DD)*.

**Example Request (monthly):**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"description": "Rent", "amount": "1200.00", "account": "1", "budget": "3", "type": "monthly", "day_of_month": "1"}' \
        http://127.0.0.1:8080/forms/scheduled

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved ScheduledTransaction 10 in database."
    }

.. _http_api.scheduled.get:

Get a Single Scheduled Transaction
+++++++++++++++++++++++++++++++++++

``GET /ajax/scheduled/<int:sched_trans_id>``

Retrieve details of a single :py:class:`~.ScheduledTransaction` by ID.

**Example Request:**

.. code-block:: bash

    $ curl http://127.0.0.1:8080/ajax/scheduled/10

**Response:**

Returns a JSON object with all :py:class:`~.ScheduledTransaction` fields plus:

- ``account_name`` *(string)* - Name of the associated account.
- ``budget_name`` *(string)* - Name of the associated budget.

.. _http_api.accounts:

Accounts
--------

.. _http_api.accounts.create_update:

Create or Update an Account
++++++++++++++++++++++++++++

``POST /forms/account``

Create a new :py:class:`~.Account` or update an existing one. Handled by :py:class:`~.AccountFormHandler`.

**Request Fields:**

- ``id`` *(integer, optional)* - Account ID. If provided, updates the existing account.
- ``name`` *(string, required)* - Account name. Cannot be empty.
- ``description`` *(string, optional)* - Account description.
- ``acct_type`` *(string, required)* - Account type: ``Bank``, ``Credit``, or ``Investment``.
- ``is_active`` *(boolean, optional)* - Whether the account is active.
- ``credit_limit`` *(decimal, optional)* - Credit limit (for credit accounts).
- ``apr`` *(decimal, optional)* - Annual Percentage Rate (for credit accounts). Values greater than 1 are converted to a decimal (e.g. ``22.5`` becomes ``0.225``).
- ``prime_rate_margin`` *(decimal, optional)* - Prime rate margin (for credit accounts).
- ``interest_class_name`` *(string, optional)* - Interest calculation class name.
- ``min_payment_class_name`` *(string, optional)* - Minimum payment formula class name.
- ``ofx_cat_memo_to_name`` *(boolean, optional)* - Use OFX category/memo as transaction name.
- ``vault_creds_path`` *(string, optional)* - Vault path for OFX credentials.
- ``ofxgetter_config_json`` *(string, optional)* - JSON configuration for ofxgetter. Must be valid JSON.
- ``negate_ofx_amounts`` *(boolean, optional)* - Whether to negate OFX amounts.
- ``reconcile_trans`` *(boolean, optional)* - Whether to reconcile transactions.
- ``re_interest_charge``, ``re_interest_paid``, ``re_payment``, ``re_late_fee``, ``re_other_fee`` *(string, optional)* - Regular expressions for OFX transaction categorization. Must be valid regex patterns.
- ``plaid_account`` *(string, optional)* - Plaid account association as ``"item_id,account_id"`` or ``"null,null"`` to clear.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"name": "Checking Account", "acct_type": "Bank"}' \
        http://127.0.0.1:8080/forms/account

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved Account 5 in database."
    }

.. _http_api.accounts.get:

Get a Single Account
++++++++++++++++++++

``GET /ajax/account/<int:account_id>``

Retrieve details of a single :py:class:`~.Account` by ID.

**Example Request:**

.. code-block:: bash

    $ curl http://127.0.0.1:8080/ajax/account/5

**Response:**

Returns a JSON object with all :py:class:`~.Account` fields (via ``as_dict``).

.. _http_api.accounts.transfer:

Account Transfer
++++++++++++++++

``POST /forms/account_transfer``

Transfer money between two accounts by creating two linked :py:class:`~.Transaction` records (one negative, one positive). Handled by :py:class:`~.AccountTransferFormHandler`.

**Request Fields:**

- ``date`` *(string, required)* - Date in ``YYYY-MM-DD`` format.
- ``amount`` *(decimal, required)* - Transfer amount. Must be positive.
- ``from_account`` *(integer, required)* - Source :py:class:`~.Account` ID. Must be active.
- ``to_account`` *(integer, required)* - Destination :py:class:`~.Account` ID. Must be active.
- ``budget`` *(integer, required)* - :py:class:`~.Budget` ID to categorize the transfer.
- ``notes`` *(string, optional)* - Free-text notes.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"date": "2017-07-15", "amount": "500.00", "from_account": "1", "to_account": "2", "budget": "4"}' \
        http://127.0.0.1:8080/forms/account_transfer

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved Transactions 100 and 101 in database."
    }

.. _http_api.budgets:

Budgets
-------

.. _http_api.budgets.create_update:

Create or Update a Budget
+++++++++++++++++++++++++

``POST /forms/budget``

Create a new :py:class:`~.Budget` or update an existing one. Handled by :py:class:`~.BudgetFormHandler`.

**Request Fields:**

- ``id`` *(integer, optional)* - Budget ID. If provided, updates the existing budget.
- ``name`` *(string, required)* - Budget name. Cannot be empty.
- ``description`` *(string, optional)* - Budget description.
- ``is_periodic`` *(boolean, required)* - ``true`` for periodic (per-pay-period) budgets, ``false`` for standing budgets.
- ``starting_balance`` *(decimal, conditional)* - Required if ``is_periodic`` is ``true``. The amount allocated per pay period.
- ``current_balance`` *(decimal, conditional)* - Required if ``is_periodic`` is ``false``. The current standing balance.
- ``is_active`` *(boolean, optional)* - Whether the budget is active.
- ``is_income`` *(boolean, optional)* - Whether this is an income budget.
- ``omit_from_graphs`` *(boolean, optional)* - Whether to exclude this budget from spending graphs.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"name": "Groceries", "is_periodic": true, "starting_balance": "200.00"}' \
        http://127.0.0.1:8080/forms/budget

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved Budget 7 in database."
    }

.. _http_api.budgets.get:

Get a Single Budget
+++++++++++++++++++

``GET /ajax/budget/<int:budget_id>``

Retrieve details of a single :py:class:`~.Budget` by ID.

**Example Request:**

.. code-block:: bash

    $ curl http://127.0.0.1:8080/ajax/budget/7

**Response:**

Returns a JSON object with all :py:class:`~.Budget` fields (via ``as_dict``).

.. _http_api.budgets.transfer:

Budget Transfer
+++++++++++++++

``POST /forms/budget_transfer``

Transfer money between two budgets by creating two linked :py:class:`~.Transaction` records. Handled by :py:class:`~.BudgetTransferFormHandler`.

**Request Fields:**

- ``date`` *(string, required)* - Date in ``YYYY-MM-DD`` format.
- ``amount`` *(decimal, required)* - Transfer amount. Must be positive.
- ``account`` *(integer, required)* - :py:class:`~.Account` ID.
- ``from_budget`` *(integer, required)* - Source :py:class:`~.Budget` ID.
- ``to_budget`` *(integer, required)* - Destination :py:class:`~.Budget` ID.
- ``notes`` *(string, optional)* - Free-text notes.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"date": "2017-07-15", "amount": "50.00", "account": "1", "from_budget": "2", "to_budget": "3"}' \
        http://127.0.0.1:8080/forms/budget_transfer

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved Transactions 200 and 201 in database."
    }

.. _http_api.reconciliation:

Reconciliation
--------------

.. _http_api.reconciliation.submit:

Submit Reconciliation
+++++++++++++++++++++

``POST /ajax/reconcile``

Submit a batch of reconciliation matches linking :py:class:`~.Transaction` records with :py:class:`~.OFXTransaction` records. Handled by :py:meth:`~.ReconcileView.post`.

**Request Body (JSON):**

- ``reconciled`` *(object, required)* - A mapping of Transaction ID (as string key) to either:

  - A two-element array ``[acct_id, fitid]`` to match with a specific OFX transaction, or
  - A string reason for marking as reconciled without an OFX match (e.g. ``"No OFX"``).

- ``ofxIgnored`` *(object, optional)* - A mapping of OFX transaction keys (formatted as ``"ACCT_ID%FITID"``) to a string reason for ignoring.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"reconciled": {"123": [1, "FID12345"], "124": "Cash purchase"}, "ofxIgnored": {"1%FID99999": "Duplicate"}}' \
        http://127.0.0.1:8080/ajax/reconcile

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully reconciled 2 transactions and ignored 1 OFX transactions."
    }

.. _http_api.reconciliation.unreconciled_ofx:

List Unreconciled OFX Transactions
+++++++++++++++++++++++++++++++++++

``GET /ajax/unreconciled/ofx``

Retrieve all unreconciled :py:class:`~.OFXTransaction` records.

**Example Request:**

.. code-block:: bash

    $ curl http://127.0.0.1:8080/ajax/unreconciled/ofx

**Response:**

Returns a JSON array of OFX transaction objects, each including all :py:class:`~.OFXTransaction` fields plus:

- ``account_name`` *(string)* - Name of the associated account.
- ``account_amount`` *(decimal)* - Transaction amount in the account's currency direction.

.. _http_api.reconciliation.unreconciled_trans:

List Unreconciled Transactions
++++++++++++++++++++++++++++++

``GET /ajax/unreconciled/trans``

Retrieve all unreconciled :py:class:`~.Transaction` records.

**Example Request:**

.. code-block:: bash

    $ curl http://127.0.0.1:8080/ajax/unreconciled/trans

**Response:**

Returns a JSON array of transaction objects, each including all :py:class:`~.Transaction` fields plus:

- ``account_name`` *(string)* - Name of the associated account.
- ``budgets`` *(array)* - Array of budget allocation objects (same structure as in :ref:`Get a Single Transaction <http_api.transactions.get>`).

.. _http_api.ofx:

OFX Statements
--------------

.. _http_api.ofx.upload:

Upload OFX Statement
+++++++++++++++++++++

``POST /api/ofx/statement``

Upload a new OFX statement to the database. This endpoint is primarily used by the ``ofxgetter`` tool and accepts pickled Python objects (not standard JSON). Handled by :py:class:`~.OfxApiLocal`.

**Request Body (JSON):**

- ``acct_id`` *(integer)* - :py:class:`~.Account` ID.
- ``mtime`` *(string)* - Base64-encoded pickled file modification time.
- ``filename`` *(string)* - OFX filename.
- ``ofx`` *(string)* - Base64-encoded pickled ``ofxparse.Ofx`` object.

.. warning::

   This endpoint uses Python pickle for serialization and is intended for use by the ``ofxgetter`` tool running on the same trusted system. Do not expose this endpoint to untrusted input.

**Success Response (HTTP 201):**

.. code-block:: json

    {
      "success": true,
      "message": "Successfully imported OFX data.",
      "count_new": 5,
      "count_updated": 12,
      "statement_id": 42
    }

.. _http_api.ofx.accounts:

List OFX Accounts
+++++++++++++++++

``GET /api/ofx/accounts``

Retrieve the list of OFX-enabled accounts.

**Example Request:**

.. code-block:: bash

    $ curl http://127.0.0.1:8080/api/ofx/accounts

**Response:**

Returns a JSON object from :py:meth:`~.OfxApiLocal.get_accounts`.

.. _http_api.fuel:

Fuel Log
--------

.. _http_api.fuel.create:

Log a Fuel Fill
+++++++++++++++

``POST /forms/fuel``

Log a fuel fill and optionally create a :py:class:`~.Transaction` for the cost. Handled by :py:class:`~.FuelFormHandler`.

**Request Fields:**

- ``date`` *(string, required)* - Date in ``YYYY-MM-DD`` format.
- ``vehicle`` *(integer, required)* - :py:class:`~.Vehicle` ID.
- ``odometer_miles`` *(integer, required)* - Current odometer reading.
- ``reported_miles`` *(integer, required)* - Miles reported by trip computer since last fill.
- ``level_before`` *(integer, required)* - Fuel level before fill (0-100).
- ``level_after`` *(integer, required)* - Fuel level after fill (0-100).
- ``fill_location`` *(string, required)* - Location of the fill. Cannot be empty.
- ``cost_per_gallon`` *(decimal, required)* - Cost per gallon. Must be positive.
- ``total_cost`` *(decimal, required)* - Total cost. Must be positive and non-zero.
- ``gallons`` *(decimal, required)* - Gallons purchased. Must be positive.
- ``reported_mpg`` *(decimal, required)* - MPG reported by trip computer. Must be positive.
- ``notes`` *(string, optional)* - Free-text notes.
- ``add_trans`` *(boolean, optional)* - Whether to create a :py:class:`~.Transaction` for the fill cost.

  If ``add_trans`` is true:

  - ``account`` *(integer, required)* - :py:class:`~.Account` ID.
  - ``budget`` *(integer, required)* - :py:class:`~.Budget` ID.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"date": "2017-07-15", "vehicle": "1", "odometer_miles": "12345", "reported_miles": "300", "level_before": "10", "level_after": "95", "fill_location": "Shell Station", "cost_per_gallon": "2.899", "total_cost": "35.50", "gallons": "12.245", "reported_mpg": "24.5", "add_trans": true, "account": "1", "budget": "5"}' \
        http://127.0.0.1:8080/forms/fuel

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved FuelFill 15 and Transaction 500 in database.",
      "fill_id": 15,
      "calculated_mpg": 24.49,
      "trans_id": 500
    }

When ``add_trans`` is false, the response omits ``trans_id``.

.. _http_api.fuel.vehicle:

Create or Update a Vehicle
++++++++++++++++++++++++++

``POST /forms/vehicle``

Create a new :py:class:`~.Vehicle` or update an existing one. Handled by :py:class:`~.VehicleFormHandler`.

**Request Fields:**

- ``id`` *(integer, optional)* - Vehicle ID. If provided, updates the existing vehicle.
- ``name`` *(string, required)* - Vehicle name. Cannot be empty and must be unique.
- ``is_active`` *(boolean, optional)* - Whether the vehicle is active.

**Example Request:**

.. code-block:: bash

    $ curl -X POST -H 'Content-Type: application/json' \
        -d '{"name": "Honda Civic"}' \
        http://127.0.0.1:8080/forms/vehicle

**Success Response:**

.. code-block:: json

    {
      "success": true,
      "success_message": "Successfully saved Vehicle 3 in database."
    }

.. _http_api.plaid:

Plaid
-----

Plaid transaction updating is documented in detail at :ref:`plaid.update-api`. In summary, the ``/plaid-update`` endpoint accepts ``item_ids`` (a comma-separated list of :py:class:`~.PlaidItem` IDs or ``ALL``) and an optional ``num_days`` parameter, and can return JSON (``Accept: application/json``) or plain text (``Accept: text/plain``) responses.

.. _http_api.utility:

Utility
-------

.. _http_api.utility.pay_period_for:

Pay Period Lookup
+++++++++++++++++

``GET /pay_period_for``

Redirect to the pay period page for a given date, or the current date if no date is specified.

**Query Parameters:**

- ``date`` *(string, optional)* - Date in ``YYYY-MM-DD`` format. Defaults to today.

**Example Request:**

.. code-block:: bash

    $ curl -v 'http://127.0.0.1:8080/pay_period_for?date=2017-07-15'

**Response:**

HTTP 302 redirect to ``/payperiod/YYYY-MM-DD`` where the date is the start of the pay period containing the requested date.
