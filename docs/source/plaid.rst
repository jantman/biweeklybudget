.. _plaid:

Plaid
=====

`Plaid <https://plaid.com/>`__ is a company that provides API-based tools and solutions for interfacing with financial institutions. Among their products is a transaction API that handles authentication with financial instituions and provides ReST access to transaction and balance information. As of March 2020, they provide free developer accounts with access to up to 100 "items" (financial institution accounts), and production accounts with a pay-as-you-go pricing model that is quite affordable.

With many of my banks and credit card companies discontinuing support for OFX Direct Connect citing security concerns (mainly that most of them use OFX 1.x implementations that require your normal credentials in cleartext), or breaking the OFX protocol in ways that only Intuit seems to support, I needed an alternative to the pain of writing error-prone screen scrapers. Plaid seems to be this solution, is reasonably priced (or free for initial testing with a developer account), and supports all of my accounts. As such, I'm going to be discontinuing development on the :ref:`ofx` component and focusing on Plaid for the future. Plaid provides a simple, easy, secure way to retrieve balance and transaction information for accounts.

The Plaid component uses the same "OFX" models in biweeklybudget that the older OFX Direct Connect component used. Transactions retrieved via Plaid will still show up on the "OFX Transactions" view, and reconciling works the same way. Both Plaid and OFX write their data into the same models and database tables.

Configuration
-------------

The first step to using the Plaid transaction support is registering for an account with `Plaid <https://plaid.com/>`__. As that process may change, I recommend using their site to find out how. As of this writing, there is a large "Get API keys" button on the homepage to get your started. You will initially be given testing / sandbox keys, which can only retrieve information about fake accounts that Plaid maintains (though it is realistic data, and can be used to see how biweeklybudget integrates with Plaid). In order to retrieve your real data, you will need to request Development access. Once you have that, you can proceed.

biweeklybudget needs to be configured with your Plaid credentials. I highly recommend setting these as environment variables rather than hard-coding them in your settings file (if you use one). You will need to run biweeklybudget with the following Plaid-related environment variables / settings:

* ``PLAID_CLIENT_ID`` - Your Client ID credential, provided by Plaid.
* ``PLAID_SECRET`` - Your Secret credential, provided by Plaid.
* ``PLAID_PUBLIC_KEY`` - Your Public Key credential, provided by Plaid.
* ``PLAID_ENV`` - The Plaid environment name to connect to. This must be one of "sandbox", "development", or "production", and must match the environment that your credentials are for.
* ``PLAID_PRODUCTS`` - The Plaid products you are requesting access to. Right now, for biweeklybudget, this should be ``transactions``.
* ``PLAID_COUNTRY_CODES`` - A comma-separated list of country codes that you want to be able to select institutions from. Only ``US`` has been tested.

Usage
-----

Linking Accounts to Plaid
+++++++++++++++++++++++++

To link an account via Plaid, open the Account modal (by clicking on any link to the account, such as those on the ``/accounts`` view) and scroll down to the bottom.

Updating Transactions via UI
++++++++++++++++++++++++++++

TBD.

Updating Transactions via API
+++++++++++++++++++++++++++++

TBD.

Troubleshooting
---------------

API responses from Plaid are logged at debug-level. The UI process of linking an account via Plaid happens mostly in client-side JavaScript, which logs pertinent information to the browser's console log. The Plaid Dashboard (accessed by logging in to plaid.com) also provides some useful debug information.
