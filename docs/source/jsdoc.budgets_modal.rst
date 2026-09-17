jsdoc.budgets\_modal
====================

File: ``biweeklybudget/flaskapp/static/js/budgets_modal.js``

.. js:function:: ..........l(id, dataTableObj)

   Show the modal popup, populated with information for one Budget.
   Uses :js:func:`budgetModalDivFillAndShow` as ajax callback.

   :param id: the ID of the Budget to show modal for, or null to show a modal to add a new Budget.
   :param dataTableObj: passed on to ``handleForm()``
   :type id: **number**
   :type dataTableObj: **Object|null**
.. js:function:: ..........................p()

   Generate the HTML for the "Held in accounts" checkboxes on the budget
   modal, one per active budget-funding account.

   Checkboxes rather than a multi-select: :js:func:`serializeForm` reads
   ``select`` elements with ``.find(':selected').val()``, which returns only
   the first selection, so a ``<select multiple>`` would silently drop every
   account but one. Checkboxes already serialize correctly, one boolean per
   ``acct_<id>`` field, and need no change to the shared form JavaScript.

   Reads the ``budget_source_accounts`` global defined by ``budgets.html``,
   which is the only template that loads this file.

   :returns: **String** -- HTML for the account links form group
.. js:function:: ........................w(msg)

   Ajax callback to fill in the modalDiv with data on a budget.
   Callback for ajax call in :js:func:`budgetModal`.
.. js:function:: .................m()

   Generate the HTML for the form on the Modal
.. js:function:: .......................e()

   Handle change of the "Type" radio buttons on the modal.

   The account links are shown for standing budgets only. A periodic budget
   resets every pay period and holds no balance, so saying which account holds
   its money would be meaningless.
