jsdoc.credit\_payoffs
=====================

File: ``biweeklybudget/flaskapp/static/js/credit_payoffs.js``

.. js:function:: ..........e(settings)

   Link handler to add another "starting on, increase payments by" form to
   the credit payoff page.
.. js:function:: .........e(settings)

   Link handler to add another one time payment form to the credit payoff page.
.. js:function:: ...........s()

   Load settings from embedded JSON. Called on page load.
.. js:function:: ........x(prefix)

   Return the next index for the form with an ID beginning with a given string.

   :param prefix: The prefix of the form IDs.
   :type prefix: **string**
   :returns: **int** -- next form index
.. js:function:: ............s()

   Buttom handler to serialize and submit the forms, to save user input and
   recalculate the payoff amounts.
.. js:function:: .............e(idx)

   Remove the specified Increase form.
.. js:function:: ............e(idx)

   Remove the specified Onetime form.
.. js:function:: .............s()

   Serialize the form data into an object and return it.

   :returns: **Object** -- serialized forms.
.. js:function:: .........d()

   Event handler to activate the "Save & Recalculate" button when user input
   fields have changed.
