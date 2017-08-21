jsdoc.credit\_payoffs
=====================

File: ``biweeklybudget/flaskapp/static/js/credit_payoffs.js``

.. js:function:: addIncrease(settings)

   Link handler to add another "starting on, increase payments by" form to
   the credit payoff page.

   

   

.. js:function:: addOnetime(settings)

   Link handler to add another one time payment form to the credit payoff page.

   

   

.. js:function:: loadSettings()

   Load settings from embedded JSON. Called on page load.

   

   

.. js:function:: nextIndex(prefix)

   Return the next index for the form with an ID beginning with a given string.

   :param string prefix: The prefix of the form IDs.
   :returns: **int** -- next form index
   

   

.. js:function:: recalcPayoffs()

   Buttom handler to serialize and submit the forms, to save user input and
   recalculate the payoff amounts.

   

   

.. js:function:: serializeForms()

   Serialize the form data into an object and return it.

   :returns: **Object** -- serialized forms.
   

   

.. js:function:: setChanged()

   Event handler to activate the "Save & Recalculate" button when user input
   fields have changed.

   

   

