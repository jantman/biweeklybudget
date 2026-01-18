jsdoc.bom\_items\_modal
=======================

File: ``biweeklybudget/flaskapp/static/js/bom_items_modal.js``

.. js:function:: ...........l(id)

   Show the BoM Item modal popup, optionally populated with
   information for one BoM Item. This function calls
   :js:func:`bomItemModalDivForm` to generate the form HTML,
   :js:func:`bomItemModalDivFillAndShow` to populate the form for editing,
   and :js:func:`handleForm` to handle the Submit action.

   :param id: the ID of the BoM Item to show a modal for, or null to show modal to add a new Transaction.
   :type id: **number**
.. js:function:: .........................w(msg)

   Ajax callback to fill in the modalDiv with data on a BoM Item.
.. js:function:: ..................m()

   Generate the HTML for the form on the Modal
