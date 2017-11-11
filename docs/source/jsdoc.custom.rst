jsdoc.custom
============

File: ``biweeklybudget/flaskapp/static/js/custom.js``

.. js:function:: fmt_currency(value)

   Format a float as currency. If ``value`` is null, return ``&nbsp;``.
   Otherwise, construct a new instance of ``Intl.NumberFormat`` and use it to
   format the currency to a string. The formatter is called with the
   ``LOCALE_NAME`` and ``CURRENCY_CODE`` variables, which are templated into
   the header of ``base.html`` using the values specified in the Python
   settings module.

   :param number value: the number to format
   :returns: **string** -- The number formatted as currency
   

   

.. js:function:: fmt_null(o)

   Format a null object as "&nbsp;"

   :param Object|null o: input value
   :returns: **Object|string** -- o if not null, ``&nbsp;`` if null
   

   

.. js:function:: isoformat(d)

   Format a javascript Date as ISO8601 YYYY-MM-DD

   :param Date d: the date to format
   :returns: **string** -- YYYY-MM-DD
   

   

