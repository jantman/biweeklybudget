jsdoc.formBuilder
=================

File: ``biweeklybudget/flaskapp/static/js/formBuilder.js``

.. js:function:: FormBuilder(id)

   Create a new FormBuilder to generate an HTML form

   :param String id: The form HTML element ID.
   

   

.. js:function:: FormBuilder.addCurrency(id, name, label, options)

   Add a text ``input`` for currency to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Object options: 
   :param String options.htmlClass: The HTML class to apply to the element
   :param String options.helpBlock: Content for block of help text after input
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addDatePicker(id, name, label)

   Add a date picker input to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addHidden(id, name, value)

   Add a hidden ``input`` to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String value: The value of the form element
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addLabelToValueSelect(id, name, label, options, defaultValue, addNone)

   Add a select element to the form, taking an Object of options where keys
   are the labels and values are the values. This is a convenience wrapper
   around :js:func:`budgetTransferDivForm`.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Object options: the options for the select, label to value
   :param String defaultValue: A value to select as the default
   :param Boolean addNone: If true, prepend an option with a value of "None" and an empty label.
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addP(content)

   Add a paragraph (``p`` tag) to the form.

   :param String content: The content of the ``p`` tag.
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addSelect(id, name, label, options)

   Add a select element to the form.
   
   Options can either be an object or an array of objects. If an object, its
   keys are used for the textual content of each option, and its values are
   used for the option value. If an array of objects, order is preserved and
   each object must have ``value`` and ``label`` keys, and can optionally
   have a ``selected`` key with a boolean value.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Array options: the options for the select, array of objects
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addText(id, name, label)

   Add a text ``input`` to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.render()

   Return complete rendered HTML for the form.

   :returns: **String** -- form HTML
   

   

