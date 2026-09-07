jsdoc.index
===========

File: ``biweeklybudget/flaskapp/static/js/index.js``

.. js:function:: ...................a(days, cb)

   Fetch account balance chart data for a given number of days of history.

   :param days: days of history to request; 0 means all history.
   :param cb: callback, passed the decoded response object.
   :type days: **number**
   :type cb: **function**
.. js:function:: ...................t(ajaxdata)

   Draw or redraw the Account Balances chart from an endpoint response.

   On the first call this constructs the Morris.Line; on later calls it hands
   the new data to the existing chart via setData(), which redraws in place
   without a page reload. When the response holds no data at all, a plain
   message is shown in place of the chart.

   :param ajaxdata: response from /ajax/chart-data/account-balances, with "data" (one object per date) and "keys" (account names) properties.
   :type ajaxdata: **Object**
.. js:function:: .....................t(days)

   Load the Account Balances chart for a given number of days of history.

   :param days: days of history to show; 0 means all history.
   :type days: **number**
