jsdoc.bom\_items\_modal
=======================

File: ``biweeklybudget/flaskapp/static/js/bom_items_modal.js``

.. js:function:: bomItemModal(id)

   Show the BoM Item modal popup, optionally populated with
   information for one BoM Item. This function calls
   :js:func:`bomItemModalDivForm` to generate the form HTML,
   :js:func:`bomItemModalDivFillAndShow` to populate the form for editing,
   and :js:func:`handleForm` to handle the Submit action.

   :param number id: the ID of the BoM Item to show a modal for, or null to show modal to add a new Transaction.
   

   

.. js:function:: bomItemModalDivFillAndShow(msg)

   Ajax callback to fill in the modalDiv with data on a BoM Item.

   

   

.. js:function:: bomItemModalDivForm()

   Generate the HTML for the form on the Modal

   

   

