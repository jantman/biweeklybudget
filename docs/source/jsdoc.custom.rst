jsdoc.custom
============

File: ``biweeklybudget/flaskapp/static/js/custom.js``

.. js:function:: ...........y(value)

   Format a float as currency. If ``value`` is null, return ``&nbsp;``.
   Otherwise, construct a new instance of ``Intl.NumberFormat`` and use it to
   format the currency to a string. The formatter is called with the
   ``LOCALE_NAME`` and ``CURRENCY_CODE`` variables, which are templated into
   the header of ``base.html`` using the values specified in the Python
   settings module.

   :param value: the number to format
   :type value: **number**
   :returns: **string** -- The number formatted as currency
.. js:function:: .......l(o)

   Format a null object as "&nbsp;"

   :param o: input value
   :type o: **Object|null**
   :returns: **Object|string** -- o if not null, ``&nbsp;`` if null
.. js:function:: ........t(d)

   Format a javascript Date as ISO8601 YYYY-MM-DD

   :param d: the date to format
   :type d: **Date**
   :returns: **string** -- YYYY-MM-DD
