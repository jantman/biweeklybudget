jsdoc.custom
============

File: ``biweeklybudget/flaskapp/static/js/custom.js``

.. js:function:: fmt_currency(value)

   Format a float as currency

   :param number value: the number to format
   :returns: **string** -- The number formatted as currency
   

   

.. js:function:: fmt_dtdict_ymd(d)

   Format a dtdict as returned by
   :py:class:`biweeklybudget.flaskapp.jsonencoder.MagicJSONEncoder`
   in ``%Y-%m-%d`` format.

   :param Object d: date dict
   :returns: **string** -- formatted Y-m-d date
   

   

.. js:function:: fmt_null(o)

   Format a null object as "&nbsp;"

   :param Object|null o: input value
   :returns: **Object|string** -- o if not null, ``&nbsp;`` if null
   

   

