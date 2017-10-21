jsdoc.balance\_budgets\_modal
=============================

File: ``biweeklybudget/flaskapp/static/js/balance_budgets_modal.js``

.. js:function:: balanceBudgetsConfirmationDivForm(data)

   Generate the HTML for the form on the Confirmation Modal.

   

   

.. js:function:: balanceBudgetsConfirmationModal(data)

   Show the modal popup for balancing budgets for a specified payperiod.
   Uses :js:func:`balanceBudgetsConfirmationDivForm` to generate the form. Uses
   :js:func:`handleBalanceBudgetsFormSubmitted` as the form submission handler.

   :param string pp_start_date: The date, as a "yyyy-mm-dd" string, that the pay period to balance starts on.
   

   

.. js:function:: balanceBudgetsDivForm()

   Generate the HTML for the form on the Modal

   

   

.. js:function:: balanceBudgetsModal(pp_start_date)

   Show the modal popup for balancing budgets for a specified payperiod.
   Uses :js:func:`balanceBudgetsDivForm` to generate the form. Uses
   :js:func:`handleBalanceBudgetsFormSubmitted` as the form submission handler.

   :param string pp_start_date: The date, as a "yyyy-mm-dd" string, that the pay period to balance starts on.
   

   

.. js:function:: handleBalanceBudgetsFormSubmitted(data, container_id, form_id, dataTableObj)

   Form submission handler for :js:func:`balanceBudgetsModal`. On success,
   empties the modal and passes the server response data to
   :js:func:`balanceBudgetsConfirmationModal`.
   
   This should either display one or more error messages, or call a success
   callback.

   :param Object data: response data
   :param string container_id: the ID of the modal container on the page
   :param string form_id: the ID of the form on the page
   :param Object dataTableObj: A reference to the DataTable on the page, that needs to be refreshed. If null, reload the whole page. If a function, call that function. If false, do nothing.
   

   

