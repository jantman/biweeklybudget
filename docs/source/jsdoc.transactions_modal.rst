jsdoc.transactions\_modal
=========================

File: ``biweeklybudget/flaskapp/static/js/transactions_modal.js``

.. js:function:: transModal(id, dataTableObj)

   Show the Transaction modal popup, optionally populated with
   information for one Transaction. This function calls
   :js:func:`transModalDivForm` to generate the form HTML,
   :js:func:`transModalDivFillAndShow` to populate the form for editing,
   and :js:func:`handleForm` to handle the Submit action.

   :param number id: the ID of the Transaction to show a modal for, or null to show modal to add a new Transaction.
   :param Object|null dataTableObj: passed on to :js:func:`handleForm`
   

   

.. js:function:: transModalDivFillAndShow(msg)

   Ajax callback to fill in the modalDiv with data on a Transaction.

   

   

.. js:function:: transModalDivForm()

   Generate the HTML for the form on the Modal

   

   

