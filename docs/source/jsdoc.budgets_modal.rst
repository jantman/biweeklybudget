jsdoc.budgets\_modal
====================

File: ``biweeklybudget/flaskapp/static/js/budgets_modal.js``

.. js:function:: budgetModal(id, dataTableObj)

   Show the modal popup, populated with information for one Budget.
   Uses :js:func:`budgetModalDivFillAndShow` as ajax callback.

   :param number id: the ID of the Budget to show modal for, or null to show a modal to add a new Budget.
   :param Object|null dataTableObj: passed on to ``handleForm()``
   

   

.. js:function:: budgetModalDivFillAndShow(msg)

   Ajax callback to fill in the modalDiv with data on a budget.
   Callback for ajax call in :js:func:`budgetModal`.

   

   

.. js:function:: budgetModalDivForm()

   Generate the HTML for the form on the Modal

   

   

.. js:function:: budgetModalDivHandleType()

   Handle change of the "Type" radio buttons on the modal

   

   

