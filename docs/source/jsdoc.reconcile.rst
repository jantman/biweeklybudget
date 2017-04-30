jsdoc.reconcile
===============

File: ``biweeklybudget/flaskapp/static/js/reconcile.js``

.. js:function:: clean_fitid(fitid)

   Given an OFXTransaction fitid, return a "clean" (alphanumeric) version of it,
   suitable for use as an HTML element id.

   :param String fitid: original, unmodified OFXTransaction fitid.
   

   

.. js:function:: makeTransFromOfx(acct_id, fitid)

   Link function to create a Transaction from a specified OFXTransaction,
   and then reconcile them.

   :param Integer acct_id: the OFXTransaction account ID
   :param String fitid: the OFXTransaction fitid
   

   

.. js:function:: makeTransSaveCallback(data, acct_id, fitid)

   Callback for the "Save" button on the Transaction modal created by
   :js:func:`makeTransFromOfx`. Displays the new Transaction at the bottom
   of the Transactions list, then reconciles it with the original OFXTransaction

   :param Object data: response data from POST to /forms/transaction
   :param Integer acct_id: the OFXTransaction account ID
   :param String fitid: the OFXTransaction fitid
   

   

.. js:function:: reconcileDoUnreconcile(trans_id, acct_id, fitid)

   Unreconcile a reconciled OFXTransaction/Transaction. This removes
   ``trans_id`` from the ``reconciled`` variable, empties the Transaction div's
   reconciled div, and shows the OFX div.

   :param Integer trans_id: the transaction id
   :param Integer acct_id: the account id
   :param String fitid: the FITID
   

   

.. js:function:: reconcileDoUnreconcileNoOfx(trans_id)

   Unreconcile a reconciled NoOFX Transaction. This removes
   ``trans_id`` from the ``reconciled`` variable and empties the Transaction
   div's reconciled div.

   :param Integer trans_id: the transaction id
   

   

.. js:function:: reconcileGetOFX()

   Show unreconciled OFX transactions in the proper div. Empty the div, then
   load transactions via ajax. Uses :js:func:`reconcileShowOFX` as the
   ajax callback.

   

   

.. js:function:: reconcileGetTransactions()

   Show unreconciled transactions in the proper div. Empty the div, then
   load transactions via ajax. Uses :js:func:`reconcileShowTransactions` as the
   ajax callback.

   

   

.. js:function:: reconcileHandleSubmit()

   Handle click of the Submit button on the reconcile view. This POSTs to
   ``/ajax/reconcile`` via ajax. Feedback is provided by appending a div with
   id ``reconcile-msg`` to ``div#notifications-row/div.col-lg-12``.

   

   

.. js:function:: reconcileOfxDiv(trans)

   Generate a div for an individual OFXTransaction, to display on the reconcile
   view.

   :param Object ofxtrans: ajax JSON object representing one OFXTransaction
   

   

.. js:function:: reconcileShowOFX(data)

   Ajax callback handler for :js:func:`reconcileGetOFX`. Display the
   returned data in the proper div.

   :param Object data: ajax response (JSON array of OFXTransaction Objects)
   

   

.. js:function:: reconcileShowTransactions(data)

   Ajax callback handler for :js:func:`reconcileGetTransactions`. Display the
   returned data in the proper div.
   
   Sets each Transaction div as ``droppable``, using
   :js:func:`reconcileTransHandleDropEvent` as the drop event handler and
   :js:func:`reconcileTransDroppableAccept` to test if a draggable is droppable
   on the element.

   :param Object data: ajax response (JSON array of Transaction Objects)
   

   

.. js:function:: reconcileTransDiv(trans)

   Generate a div for an individual Transaction, to display on the reconcile
   view.

   :param Object trans: ajax JSON object representing one Transaction
   

   

.. js:function:: reconcileTransDroppableAccept(drag)

   Accept function for droppables, to determine if a given draggable can be
   dropped on it.

   :param Object drag: the draggable element being dropped.
   

   

.. js:function:: reconcileTransHandleDropEvent(event, ui)

   Handler for Drop events on reconcile Transaction divs. Setup as handler
   via :js:func:`reconcileShowTransactions`. This just gets the draggable and
   the target from the ``event`` and ``ui``, and then passes them on to
   :js:func:`reconcileTransactions`.

   :param Object event: the drop event
   :param Object ui: the UI element, containing the draggable
   

   

.. js:function:: reconcileTransNoOfx(trans_id, note)

   Reconcile a Transaction without a matching OFXTransaction. Called from
   the Save button handler in :js:func:`transNoOfx`.

   

   

.. js:function:: reconcileTransactions(ofx_div, target)

   Reconcile a transaction; move the divs and other elements as necessary,
   and updated the ``reconciled`` variable.

   :param Object ofx_div: the OFXTransaction div element (draggable)
   :param Object target: the Transaction div (drop target)
   

   

.. js:function:: transModalOfxFillAndShow(data)

   Callback for the GET /ajax/ofx/<acct_id>/<fitid> from
   :js:func:`makeTransFromOfx`. Receives the OFXTransaction data and populates
   it into the Transaction modal form.

   :param Object data: OFXTransaction response data
   

   

.. js:function:: transNoOfx(trans_id)

   Show the modal for reconciling a Transaction without a matching
   OFXTransaction. Calls :js:func:`transNoOfxDivForm` to generate the modal form
   div content. Uses an inline function to handle the save action, which calls
   :js:func:`reconcileTransNoOfx` to perform the reconcile action.

   :param number trans_id: the ID of the Transaction
   

   

.. js:function:: transNoOfxDivForm(trans_id)

   Generate the modal form div content for the modal to reconcile a Transaction
   without a matching OFXTransaction. Called by :js:func:`transNoOfx`.

   :param number trans_id: the ID of the Transaction
   

   

.. js:function:: updateReconcileTrans(trans_id)

   Trigger update of a single Transaction on the reconcile page.

   :param Integer trans_id: the Transaction ID to update.
   

   

