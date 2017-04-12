jsdoc.payperiod\_modal
======================

File: ``biweeklybudget/flaskapp/static/js/payperiod_modal.js``

.. js:function:: schedToTransModal(id, payperiod_start_date)

   Show the Scheduled Transaction to Transaction modal popup. This function
   calls :js:func:`schedToTransModalDivForm` to generate the form HTML,
   :js:func:`schedToTransModalDivFillAndShow` to populate the form for editing,
   and :js:func:`handleForm` to handle the Submit action.

   :param number id: the ID of the ScheduledTransaction to show a modal for.
   :param string payperiod_start_date: The Y-m-d starting date of the pay period.
   

   

.. js:function:: schedToTransModalDivFillAndShow(msg)

   Ajax callback to fill in the modalDiv with data on a budget.

   

   

.. js:function:: schedToTransModalDivForm()

   Generate the HTML for the form on the Modal

   

   

