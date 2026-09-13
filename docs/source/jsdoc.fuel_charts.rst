jsdoc.fuel\_charts
==================

File: ``biweeklybudget/flaskapp/static/js/fuel_charts.js``

.. js:function:: .................a(ajaxdata)

   The fuel prices endpoint returns only ``data``, one ``price`` per date, with
   no ``keys``; add the single series name that :js:func:`lineChartCreate`
   expects.

   :param ajaxdata: response from /ajax/chart-data/fuel-prices
   :type ajaxdata: **Object**
   :returns: **Object** -- the same data, with ``keys`` of ``['price']``
.. js:function:: .........s()

   Draw the Fuel Economy and Fuel Prices charts with :js:func:`lineChartCreate`.
.. js:function:: ...........s()

   Reload both fuel charts' data in place, after a fuel fill is added.
