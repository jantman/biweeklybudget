jsdoc.reconcile
===============

File: ``biweeklybudget/flaskapp/static/js/reconcile.js``

.. js:function:: clean_fitid(fitid)

   Given an OFXTransaction fitid, return a "clean" (alphanumeric) version of it,
   suitable for use as an HTML element id.

   :param String fitid: original, unmodified OFXTransaction fitid.
   

   

.. js:function:: reconcileGetOFX()

   Show unreconciled OFX transactions in the proper div. Empty the div, then
   load transactions via ajax. Uses :js:func:`reconcileShowOFX` as the
   ajax callback.

   

   

.. js:function:: reconcileGetTransactions()

   Show unreconciled transactions in the proper div. Empty the div, then
   load transactions via ajax. Uses :js:func:`reconcileShowTransactions` as the
   ajax callback.

   

   

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
   via :js:func:`reconcileShowTransactions`.

   :param Object event: the drop event
   :param Object ui: the UI element, containing the draggable
   

   

.. js:function:: updateReconcileTrans(trans_id)

   Trigger update of a single Transaction on the reconcile page.

   :param Integer trans_id: the Transaction ID to update.
   

   

