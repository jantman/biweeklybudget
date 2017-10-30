.. _app_usage:

Application Usage
=================

This documentation is a work in progress. I suppose if anyone other than me
ever tries to use this, I'll document it a bit more.

.. _app_usage.l10n:

Currency Formatting and Localization
------------------------------------

biweeklybudget supports configurable currency symbols and display/formatting,
controlled by the :py:attr:`~biweeklybudget.settings.LOCALE_NAME` and
:py:attr:`~biweeklybudget.settings.CURRENCY_CODE` settings. The former must
specify a `RFC 5646 / BCP 47 <https://tools.ietf.org/html/bcp47>`_ language tag
with a region identifier (i.e. "en_US", "en_GB", "de_DE", etc.). If it is not
set in the settings module or via a ``LOCALE_NAME`` environment variable, it
will be looked up from the ``LC_ALL``, ``LC_MONETARY``, or ``LANG`` environment
variables, in that order. It cannot be a "C" or "C." locale, as these do not
specify currency formatting. The latter, ``CURRENCY_CODE``, must be a valid
`ISO 4217 <https://en.wikipedia.org/wiki/ISO_4217>`_ Currency Code (i.e.
"USD", "EUR", etc.) and can also be set via a ``CURRENCY_CODE`` environment
variable.

These settings only effect the display of monetary units in the user interface
and in log files. I haven't made any attempt at actual internationalization of
the text, mainly because as far as I know I'm the only person in the world using
this software. If anyone else uses it, I'll be happy to work to accomodate users
of other languages or localities.

Right now, regarding localization and currency formatting, please keep in mind
the following caveats (which I'd be happy to fix if anyone needs it):

* The currency specified in downloaded OFX files is ignored. Since currency
  conversion and exchange rates are far outside the scope of this application,
  it's assumed that all accounts will be in the currency defined in settings.
* The ``wishlist2project`` console script that parses Amazon Wishlists and
  updates Projects / BoMs with their contents currently only supports items
  priced in USD, and currently only supports wishlists on the US amazon.com
  site; these are limitations of the upstream project used for wishlist
  parsing.
* The Fuel Log currently calls the volume of fuel units "gallons", probably
  specifies "dollars" or "$" in the UI, and calls the units of distance "miles".
  There's nothing mathematical that would prevent it from handling Kilometers
  per Liter or any other combination of distance, volume and cost. If anyone
  outside of the US is interested in using it, I'll gladly make those parts of
  the user interface configurable as well.
* The database storage of monetary values assumes that they will all be a
  decimal number, and currently only allows for six digits to the left of the
  decimal and four digits to the right; this applies to all monetary units from
  transaction amounts to account balances. As such, if you have any
  transactions, budgets or accounts (including bank and investment accounts
  imported via OFX) with values outside of 999999.9999 to -999999.9999
  (inclusive), the application will not function. If anyone needs support for
  larger numbers (or, at the rate I'm going, I'm still working and paying into
  my pension in about 300 years), the change shouldn't be terribly difficult.
