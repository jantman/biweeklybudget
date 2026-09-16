jsdoc.plaid\_prod
=================

File: ``biweeklybudget/flaskapp/static/js/plaid_prod.js``

.. js:function:: ..........e(item_id)

   Call the /ajax/plaid/delete_item endpoint and then reload this page. On
   failure, show the server's message and leave the page alone, since nothing
   was deleted.

   :param item\_id: the Plaid Item ID to delete.
   :type item\_id: **string**
.. js:function:: .................m(item_id, institution_name, account_names)

   Show the confirmation modal for deleting a Plaid Item. Makes no request of
   its own; the deletion happens in :js:func:`plaidDelete`, called when the
   modal's Delete button is clicked.

   :param item\_id: the Plaid Item ID to delete.
   :param institution\_name: the Item's institution name, for display.
   :param account\_names: comma-separated "Name (id)" for each Account linked to this Item, or an empty string if none are.
   :type item\_id: **string**
   :type institution\_name: **string**
   :type account\_names: **string**
.. js:function:: ........k()

   Initiate a Plaid link. Perform the link process and retrieve a public token;
   POST it to /ajax/plaid/handle_link.
.. js:function:: ...........h(item_id)

   Call the /ajax/plaid/refresh_item_accounts endpoint and then reload this page.
.. js:function:: ..........e(item_id)

   Update the existing Plaid account / Link.
