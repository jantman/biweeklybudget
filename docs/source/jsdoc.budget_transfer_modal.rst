jsdoc.budget\_transfer\_modal
=============================

File: ``biweeklybudget/flaskapp/static/js/budget_transfer_modal.js``

.. js:function:: budgetTransferDivForm()

   Generate the HTML for the form on the Modal

   

   

.. js:function:: budgetTransferModal(txfr_date)

   Show the modal popup for transferring between budgets.
   Uses :js:func:`budgetTransferDivForm` to generate the form.

   :param string txfr_date: The date, as a "yyyy-mm-dd" string, to default the form to. If null or undefined, will default to ``BIWEEKLYBUDGET_DEFAULT_DATE``.
   

   

