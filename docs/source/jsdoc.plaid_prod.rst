jsdoc.plaid\_prod
=================

File: ``biweeklybudget/flaskapp/static/js/plaid_prod.js``

.. js:function:: plaidLink()

   Initiate a Plaid link. Perform the link process and retrieve a public token;
   POST it to /ajax/plaid/handle_link.

   

   

.. js:function:: plaidRefresh(item_id)

   Call the /ajax/plaid/refresh_item_accounts endpoint and then reload this page.

   

   

.. js:function:: plaidUpdate(item_id)

   Update the existing Plaid account / Link.

   

   

