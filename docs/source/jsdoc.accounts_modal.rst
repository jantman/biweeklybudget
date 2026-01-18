jsdoc.accounts\_modal
=====================

File: ``biweeklybudget/flaskapp/static/js/accounts_modal.js``

.. js:function:: ...........l(id, dataTableObj)

   Show the modal popup, populated with information for one account.
   Uses :js:func:`accountModalDivFillAndShow` as ajax callback.

   :param id: the ID of the account to show modal for, or null to show a modal to add a new account.
   :param dataTableObj: passed on to ``handleForm()``
   :type id: **number**
   :type dataTableObj: **Object|null**
.. js:function:: .........................w(msg)

   Ajax callback to fill in the modalDiv with data on a account.
   Callback for ajax call in :js:func:`accountModal`.
.. js:function:: ..................m()

   Generate the HTML for the form on the Modal
.. js:function:: ........................e()

   Handle change of the "Type" radio buttons on the modal
