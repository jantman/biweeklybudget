jsdoc.reconcile
===============

File: ``biweeklybudget/flaskapp/static/js/reconcile.js``

.. js:function:: ..........d(fitid)

   Given an OFXTransaction fitid, return a "clean" (alphanumeric) version of it,
   suitable for use as an HTML element id.

   :param fitid: original, unmodified OFXTransaction fitid.
   :type fitid: **String**
.. js:function:: .............s(acct_id, fitid)

   Show the modal for reconciling an OFXTransaction without a matching
   Transaction. Calls :js:func:`ignoreOfxTransDivForm` to generate the modal form
   div content. Uses an inline function to handle the save action, which calls
   :js:func:`reconcileOfxNoTrans` to perform the reconcile action.

   :param acct\_id: the Account ID of the OFXTransaction
   :param fitid: the FitID of the OFXTransaction
   :type acct\_id: **number**
   :type fitid: **string**
.. js:function:: ....................m(acct_id, fitid)

   Generate the modal form div content for the modal to reconcile a Transaction
   without a matching OFXTransaction. Called by :js:func:`transNoOfx`.

   :param acct\_id: the Account ID of the OFXTransaction
   :param fitid: the FitID of the OFXTransaction
   :type acct\_id: **number**
   :type fitid: **string**
.. js:function:: ...............x(acct_id, fitid)

   Link function to create a Transaction from a specified OFXTransaction,
   and then reconcile them.

   :param acct\_id: the OFXTransaction account ID
   :param fitid: the OFXTransaction fitid
   :type acct\_id: **Integer**
   :type fitid: **String**
.. js:function:: ....................k(data, acct_id, fitid)

   Callback for the "Save" button on the Transaction modal created by
   :js:func:`makeTransFromOfx`. Displays the new Transaction at the bottom
   of the Transactions list, then reconciles it with the original OFXTransaction

   :param data: response data from POST to /forms/transaction
   :param acct\_id: the OFXTransaction account ID
   :param fitid: the OFXTransaction fitid
   :type data: **Object**
   :type acct\_id: **Integer**
   :type fitid: **String**
.. js:function:: .....................e(trans_id, acct_id, fitid)

   Unreconcile a reconciled OFXTransaction/Transaction. This removes
   ``trans_id`` from the ``reconciled`` variable, empties the Transaction div's
   reconciled div, and shows the OFX div.

   :param trans\_id: the transaction id
   :param acct\_id: the account id
   :param fitid: the FITID
   :type trans\_id: **Integer**
   :type acct\_id: **Integer**
   :type fitid: **String**
.. js:function:: ..........................x(trans_id)

   Unreconcile a reconciled NoOFX Transaction. This removes
   ``trans_id`` from the ``reconciled`` variable and empties the Transaction
   div's reconciled div.

   :param trans\_id: the transaction id
   :type trans\_id: **Integer**
.. js:function:: ............................s(acct_id, fitid)

   Unreconcile a reconciled NoTrans OFXTransaction. This removes
   ``acct_id + "%" + fitid`` from the ``ofxIgnored`` variable and regenerates
   the OFXTransaction's div.

   :param acct\_id: the Account ID of the OFXTransaction
   :param fitid: the FitID of the OFXTransaction
   :type acct\_id: **number**
   :type fitid: **string**
.. js:function:: ..............X()

   Show unreconciled OFX transactions in the proper div. Empty the div, then
   load transactions via ajax. Uses :js:func:`reconcileShowOFX` as the
   ajax callback.
.. js:function:: .......................s()

   Show unreconciled transactions in the proper div. Empty the div, then
   load transactions via ajax. Uses :js:func:`reconcileShowTransactions` as the
   ajax callback.
.. js:function:: ....................t()

   Handle click of the Submit button on the reconcile view. This POSTs to
   ``/ajax/reconcile`` via ajax. Feedback is provided by appending a div with
   id ``reconcile-msg`` to ``div#notifications-row/div.col-lg-12``.
.. js:function:: ..............v(ofxtrans)

   Generate a div for an individual OFXTransaction, to display on the reconcile
   view.

   :param ofxtrans: ajax JSON object representing one OFXTransaction
   :type ofxtrans: **Object**
.. js:function:: ..................s(acct_id, fitid, note)

   Reconcile an OFXTransaction without a matching Transaction. Called from
   the Save button handler in :js:func:`ignoreOfxTrans`.
.. js:function:: ...............X(data)

   Ajax callback handler for :js:func:`reconcileGetOFX`. Display the
   returned data in the proper div.

   :param data: ajax response (JSON array of OFXTransaction Objects)
   :type data: **Object**
.. js:function:: ........................s(data)

   Ajax callback handler for :js:func:`reconcileGetTransactions`. Display the
   returned data in the proper div.

   Sets each Transaction div as ``droppable``, using
   :js:func:`reconcileTransHandleDropEvent` as the drop event handler and
   :js:func:`reconcileTransDroppableAccept` to test if a draggable is droppable
   on the element.

   :param data: ajax response (JSON array of Transaction Objects)
   :type data: **Object**
.. js:function:: ................v(trans)

   Generate a div for an individual Transaction, to display on the reconcile
   view. Called from :js:func:`reconcileShowTransactions`,
   :js:func:`makeTransSaveCallback` and :js:func:`updateReconcileTrans`.

   :param trans: ajax JSON object representing one Transaction
   :type trans: **Object**
.. js:function:: ............................t(drag)

   Accept function for droppables, to determine if a given draggable can be
   dropped on it.

   :param drag: the draggable element being dropped.
   :type drag: **Object**
.. js:function:: ............................t(event, ui)

   Handler for Drop events on reconcile Transaction divs. Setup as handler
   via :js:func:`reconcileShowTransactions`. This just gets the draggable and
   the target from the ``event`` and ``ui``, and then passes them on to
   :js:func:`reconcileTransactions`.

   :param event: the drop event
   :param ui: the UI element, containing the draggable
   :type event: **Object**
   :type ui: **Object**
.. js:function:: ..................x(trans_id, note)

   Reconcile a Transaction without a matching OFXTransaction. Called from
   the Save button handler in :js:func:`transNoOfx`.
.. js:function:: ....................s(ofx_div, target)

   Reconcile a transaction; move the divs and other elements as necessary,
   and updated the ``reconciled`` variable.

   :param ofx\_div: the OFXTransaction div element (draggable)
   :param target: the Transaction div (drop target)
   :type ofx\_div: **Object**
   :type target: **Object**
.. js:function:: .......................w(data)

   Callback for the GET /ajax/ofx/<acct_id>/<fitid> from
   :js:func:`makeTransFromOfx`. Receives the OFXTransaction data and populates
   it into the Transaction modal form.

   :param data: OFXTransaction response data
   :type data: **Object**
.. js:function:: .........x(trans_id)

   Show the modal for reconciling a Transaction without a matching
   OFXTransaction. Calls :js:func:`transNoOfxDivForm` to generate the modal form
   div content. Uses an inline function to handle the save action, which calls
   :js:func:`reconcileTransNoOfx` to perform the reconcile action.

   :param trans\_id: the ID of the Transaction
   :type trans\_id: **number**
.. js:function:: ................m(trans_id)

   Generate the modal form div content for the modal to reconcile a Transaction
   without a matching OFXTransaction. Called by :js:func:`transNoOfx`.

   :param trans\_id: the ID of the Transaction
   :type trans\_id: **number**
.. js:function:: ...................s(trans_id)

   Trigger update of a single Transaction on the reconcile page.

   :param trans\_id: the Transaction ID to update.
   :type trans\_id: **Integer**
