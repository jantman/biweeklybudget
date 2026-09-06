jsdoc.custom
============

File: ``biweeklybudget/flaskapp/static/js/custom.js``

.. js:function:: ..................s()

   Return the digit grouping separator and decimal separator for
   ``LOCALE_NAME``, i.e. ``[',', '.']`` for ``en-US`` and ``['.', ',']`` for
   ``de-DE``. Determined from ``Intl.NumberFormat`` rather than hard-coded, so
   that changing the Python ``LOCALE_NAME`` setting is all that is needed to
   support another locale.

   :returns: **Array** -- 2-element Array of [group separator, decimal separator]
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
.. js:function:: .............y(value)

   Parse a user-entered currency string to a Number, or ``null`` if it cannot
   be unambiguously interpreted.

   This is the browser counterpart to :js:func:`fmt_currency`, and mirrors
   ``biweeklybudget.utils.parse_currency()`` on the server; the server remains
   the authority, and this function exists so that in-browser validation does
   not reject values the server would accept. See GitHub issue #323.

   For ``en-US``, all of ``1234.56``, ``1,234.56``, ``1 234.56``,
   ``$1,234.56`` and ``(1,234.56)`` are interpreted, and bare integers such as
   ``123`` are accepted. Ambiguously grouped values such as ``10,00`` return
   ``null`` rather than a guess.

   Returns ``null`` and not ``NaN`` deliberately: ``NaN`` comparisons silently
   evaluate false, which is how ``parseFloat`` used to disable the Save button
   with no visible reason.

   :param value: the string to parse
   :type value: **string**
   :returns: **number|null** -- the numeric value, or null if not interpretable
