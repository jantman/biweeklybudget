jsdoc.scheduled\_modal
======================

File: ``biweeklybudget/flaskapp/static/js/scheduled_modal.js``

.. js:function:: .........l(id, dataTableObj)

   Show the ScheduledTransaction modal popup, optionally populated with
   information for one ScheduledTransaction. This function calls
   :js:func:`schedModalDivForm` to generate the form HTML,
   :js:func:`schedModalDivFillAndShow` to populate the form for editing,
   and :js:func:`handleForm` to handle the Submit action.

   :param id: the ID of the ScheduledTransaction to show a modal for, or null to show modal to add a new ScheduledTransaction.
   :param dataTableObj: passed on to :js:func:`handleForm`
   :type id: **number**
   :type dataTableObj: **Object|null**
.. js:function:: .......................w(msg)

   Ajax callback to fill in the modalDiv with data on a budget.
.. js:function:: ................m()

   Generate the HTML for the form on the Modal
.. js:function:: ......................e()

   Handle change of the "Type" radio buttons on the modal
