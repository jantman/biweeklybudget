.. _plaid:

Plaid
=====

Testing (Sandbox)
-----------------

.. code-block:: bash

    export PLAID_CLIENT_ID=5cf090726590ed001352c268
    export PLAID_SECRET=4265c2b9575665adff6dff6843ec82
    export PLAID_PUBLIC_KEY=c248f0f1788d692421ccb7a1df2126
    export PLAID_PRODUCTS=transactions
    export PLAID_COUNTRY_CODES=US
    export PLAID_ENV=sandbox

In sandbox, there will be one and only one fake account, a bank account. The credentials for successfully authenticating are a username of ``user_good`` and a password of ``pass_good``.
