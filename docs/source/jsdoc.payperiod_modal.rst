jsdoc.payperiod\_modal
======================

File: ``biweeklybudget/flaskapp/static/js/payperiod_modal.js``

.. js:function:: ................l(id, payperiod_start_date)

   Show the Scheduled Transaction to Transaction modal popup. This function
   calls :js:func:`schedToTransModalDivForm` to generate the form HTML,
   :js:func:`schedToTransModalDivFillAndShow` to populate the form for editing,
   and :js:func:`handleForm` to handle the Submit action.

   :param id: the ID of the ScheduledTransaction to show a modal for.
   :param payperiod\_start\_date: The Y-m-d starting date of the pay period.
   :type id: **number**
   :type payperiod\_start\_date: **string**
.. js:function:: ..............................w(msg)

   Ajax callback to fill in the modalDiv with data on a budget.
.. js:function:: .......................m()

   Generate the HTML for the form on the Modal
.. js:function:: ..................l(id, payperiod_start_date)

   Show the Skip Scheduled Transaction modal popup. This function
   calls :js:func:`skipSchedTransModalDivForm` to generate the form HTML,
   :js:func:`skipSchedTransModalDivFillAndShow` to populate the form for
   editing, and :js:func:`handleForm` to handle the Submit action.

   :param id: the ID of the ScheduledTransaction to show a modal for.
   :param payperiod\_start\_date: The Y-m-d starting date of the pay period.
   :type id: **number**
   :type payperiod\_start\_date: **string**
.. js:function:: ................................w(msg)

   Ajax callback to fill in the modalDiv with data on a budget.
.. js:function:: .........................m()

   Generate the HTML for the form on the Modal
