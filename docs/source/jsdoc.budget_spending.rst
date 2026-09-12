jsdoc.budget\_spending
======================

File: ``biweeklybudget/flaskapp/static/js/budget_spending.js``

.. js:function:: .........................s(data)

   Assign each budget its slice colour. Budgets are ranked by their total
   positive spending across every period on the page, and the categorical
   colours are given out in that order; the rest get
   ``BUDGET_SPENDING_OTHER_COLOR``. This depends only on the loaded data, never
   on which budgets are ticked, so a budget keeps its colour in every chart
   and unticking one budget never repaints the others.

   :param data: by-period endpoint response
   :type data: **Object**
   :returns: **Object** -- budget ID to colour
.. js:function:: ...........................n()

   Build the budget checkboxes: one per budget in the endpoint's ``budgets``
   list, ticked unless the budget is marked "Omit from graphs". Changing one
   redraws all the charts from the data already loaded; nothing is saved.
.. js:function:: .........................s(a, b)

   Compare two objects with ``name`` and ``budget_id`` properties, by name
   then ID, for sorting.

   :param a: first object
   :param b: second object
   :type a: **Object**
   :type b: **Object**
   :returns: **number** -- negative, zero or positive, as for ``Array.sort``
.. js:function:: ....................l()

   Redraw every period's panel from the loaded data.

   All the tables are drawn before any chart. A Morris chart takes its width
   from its container once, when it is created; the tables are what make the
   page tall enough to need a scrollbar, which narrows every column. Charts
   drawn before that would keep their wider width and overflow their panels.
.. js:function:: ......................t(period, summary)

   Draw one period's donut chart, if it has any slices. Called only once
   every panel's table has been drawn; see ``budgetSpendingDrawAll()``.

   :param period: one element of the endpoint's ``periods`` list
   :param summary: ``budgetSpendingSummarize(period)``
   :type period: **Object**
   :type summary: **Object**
.. js:function:: ......................l(period, summary)

   Draw one period's panel, apart from its donut chart: dates, total, table
   and net credits, and whether the chart or the "no spending" message is
   shown. Budget names are always inserted as text, never as HTML.

   :param period: one element of the endpoint's ``periods`` list
   :param summary: ``budgetSpendingSummarize(period)``
   :type period: **Object**
   :type summary: **Object**
.. js:function:: .....................s(cents)

   Format an integer number of cents as currency.

   :param cents: amount in cents
   :type cents: **number**
   :returns: **string** -- the formatted amount
.. js:function:: .................d()

   Load the chart data and draw the page. Sets ``data-loaded`` on
   ``#budget-spending-charts`` once drawn.
.. js:function:: ......................e(period)

   Split one period's spending into chart slices and net credits, over the
   included budgets only. Amounts are converted to integer cents before they
   are added up, so that floating point error cannot creep into a total.

   :param period: one element of the endpoint's ``periods`` list
   :type period: **Object**
   :returns: **Object** -- with ``slices`` (positive nets, largest first, each with ``budget_id``, ``name``, ``cents`` and ``percent``), ``credits`` (negative nets, by name) and ``totalCents`` (sum of the slices)
.. js:function:: ...................h(budgetId)

   Return a small colour swatch element identifying a budget's slices.

   :param budgetId: the budget ID
   :type budgetId: **number**
   :returns: **jQuery** -- the swatch span
