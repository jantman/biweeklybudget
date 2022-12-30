.. _plaid:

Plaid
=====

`Plaid <https://plaid.com/>`__ is a company that provides API-based tools and solutions for interfacing with financial institutions. Among their products is a transaction API that handles authentication with financial instituions and provides ReST access to transaction and balance information. As of March 2020, they provide free developer accounts with access to up to 100 "items" (financial institution accounts), and production accounts with a pay-as-you-go pricing model that is quite affordable.

With many of my banks and credit card companies discontinuing support for OFX Direct Connect citing security concerns (mainly that most of them use OFX 1.x implementations that require your normal credentials in cleartext), or breaking the OFX protocol in ways that only Intuit seems to support, I needed an alternative to the pain of writing error-prone screen scrapers. Plaid seems to be this solution, is reasonably priced (or free for initial testing with a developer account), and supports all of my accounts. As such, I'm going to be discontinuing development on the :ref:`ofx` component and focusing on Plaid for the future. Plaid provides a simple, easy, secure way to retrieve balance and transaction information for accounts.

The Plaid component uses the same "OFX" models in biweeklybudget that the older OFX Direct Connect component used. Transactions retrieved via Plaid will still show up on the "OFX Transactions" view, and reconciling works the same way. Both Plaid and OFX write their data into the same models and database tables.

**IMPORTANT** As of late 2022, a handful of financial institutions, Chase being the most notable, require `OAuth2 integration via Plaid <https://plaid.com/docs/link/oauth/>`__. This requires that your Plaid account request and be approved for Production environment access, which is a non-trivial process that requires additional legal agreements and a security and privacy review. In addition, Chase has their own partner review process that includes a security review. While it is *possible* for an individual to pass these reviews for a personal project, it's far from trivial. I would only recommend this for folks who have professional experience developing and operating applications that handle financial data, and who intend to operate biweeklybudget in a similar fashion.

.. _plaid.configuration:

Configuration
-------------

The first step to using the Plaid transaction support is registering for an account with `Plaid <https://plaid.com/>`__. As that process may change, I recommend using their site to find out how. As of this writing, there is a large "Get API keys" button on the homepage to get your started. You will initially be given testing / sandbox keys, which can only retrieve information about fake accounts that Plaid maintains (though it is realistic data, and can be used to see how biweeklybudget integrates with Plaid). In order to retrieve your real data, you will need to request Development access. Once you have that, you can proceed.

biweeklybudget needs to be configured with your Plaid credentials. I highly recommend setting these as environment variables rather than hard-coding them in your settings file (if you use one). You will need to run biweeklybudget with the following Plaid-related environment variables / settings:

* ``PLAID_CLIENT_ID`` - Your Client ID credential, provided by Plaid.
* ``PLAID_SECRET`` - Your Secret credential, provided by Plaid.
* ``PLAID_ENV`` - The Plaid environment name to connect to. This must be one of "Sandbox", "Development", or "Production", and must match the environment that your credentials are for.
* ``PLAID_PRODUCTS`` - The Plaid products you are requesting access to. Right now, for biweeklybudget, this should be ``transactions``.
* ``PLAID_COUNTRY_CODES`` - A comma-separated list of country codes that you want to be able to select institutions from. Only ``US`` has been tested.

.. _plaid.usage:

Usage
-----

.. _plaid.linking:

Linking Accounts to Plaid
+++++++++++++++++++++++++

**TBD**

.. _plaid.update-ui:

Updating Transactions via UI
++++++++++++++++++++++++++++

Updating through the UI will retrieve transactions for the last 30 days. If you want to retrieve more than that, you must do so :ref:`via the API <plaid.update-api>`.

1. Click the "Plaid Update" link in the left navigation menu.
2. In the "Plaid Update Transactions" table, select the Plaid Items that you want to update transactions for.
3. Click the "Update Transactions" button at the bottom of the table.
4. When the update is complete, you will be redirected to a page showing results in a table.

.. _plaid.update-api:

Updating Transactions via API
+++++++++++++++++++++++++++++

Transactions can be updated via a simple API at the same ``/plaid-update`` endpoint. This API can return either a JSON or human-readable plain-text output depending on the ``Accept`` header. For full documentation, see the documentation of :py:class:`~.PlaidUpdate` and :py:meth:`~.PlaidUpdate.post`.

In short, the endpoint takes a POST or GET request that specifies an ``item_ids`` parameter as a string comma-separated list of :py:class:`~.PlaidItem` IDs to update, or the special string ``ALL`` to update all Items. Optionally, you can specify a ``num_days`` parameter to retrieve transactions for something other than the last 30 days. The response is either JSON if the ``Accept`` header is set to ``application/json`` or human-readable plain text if set to ``text/plain`` (if set to any other value, it will return the full HTML that would be sent to the browser).

The following examples assume that biweeklybudget is available at ``http://127.0.0.1:8080``

To update transactions for all Plaid Items via a GET request and return human-readable text:

.. code-block:: bash

    curl -H 'Accept: text/plain' 'http://127.0.0.1:8080/plaid-update?account_ids=ALL'

      % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                     Dload  Upload   Total   Spent    Left  Speed

      0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
      0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
      0     0    0     0    0     0      0      0 --:--:--  0:00:01 --:--:--     0
      0     0    0     0    0     0      0      0 --:--:--  0:00:02 --:--:--     0
      0     0    0     0    0     0      0      0 --:--:--  0:00:03 --:--:--     0
    100   874  100   874    0     0    231      0  0:00:03  0:00:03 --:--:--   232
    AcctOne (plaidItemId1): 23 updated, 0 added (stmts: [21728])
    AcctTwo (plaidItemId2): 31 updated, 0 added (stmts: [21729])
    AcctThree (plaidItemId3): 35 updated, 3 added (stmts: [21730])
    TOTAL: 89 updated, 3 added, 0 account(s) failed

To update transactions for Plaid Items with IDs plaidItemId1 and plaidItemId2 for the last 60 days via a POST, and return JSON:

**TBD**

.. _plaid.troubleshooting:

Troubleshooting
---------------

API responses from Plaid are logged at debug-level. The UI process of linking an account via Plaid happens mostly in client-side JavaScript, which logs pertinent information to the browser's console log. The `Plaid Dashboard <https://dashboard.plaid.com/>`__ also provides some useful debug information, espeically when correlated with the ``link_token`` and/or ``item_id`` that should be logged by biweeklybudget.

.. _plaid.change-env:

Changing Plaid Environments
---------------------------

It may be necessary to change Plaid environments, such as if you started using the Development environment and then switched to Production for OAuth2 integrations. This process will require setting up Plaid again.

Also **note** that Plaid ``transaction_id`` (our ``fitid``) _will_ change between environments. As such, you should update transactions in the old environment immediately before switching environments, then update transactions in the new environment, and you will need to manually ignore any transactions that are duplicates.

1. Un-associate all of your Accounts from Plaid Accounts. This can be done manually via the Account edit modal or by running the following SQL query directly against the database: ``UPDATE accounts SET plaid_item_id=NULL, plaid_account_id=NULL;``
2. Delete all of your Plaid Accounts and Plaid Items from the database: ``DELETE FROM plaid_accounts; DELETE FROM plaid_items;``
3. Update your configuration / environment variables for the new ``PLAID_ENV`` that you want to use and your ``PLAID_SECRET`` for that environment.
4. Re-link all of your Plaid items, and then re-associate them with your Accounts.
