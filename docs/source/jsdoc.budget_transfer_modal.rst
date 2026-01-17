jsdoc.budget\_transfer\_modal
=============================

File: ``biweeklybudget/flaskapp/static/js/budget_transfer_modal.js``

.. js:function:: ....................m()

   Generate the HTML for the form on the Modal
.. js:function:: ..................l(txfr_date)

   Show the modal popup for transferring between budgets.
   Uses :js:func:`budgetTransferDivForm` to generate the form.

   :param txfr\_date: The date, as a "yyyy-mm-dd" string, to default the form to. If null or undefined, will default to ``BIWEEKLYBUDGET_DEFAULT_DATE``.
   :type txfr\_date: **string**
