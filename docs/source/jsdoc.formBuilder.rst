jsdoc.formBuilder
=================

File: ``biweeklybudget/flaskapp/static/js/formBuilder.js``

.. js:function:: FormBuilder(id)

   Create a new FormBuilder to generate an HTML form

   :param String id: The form HTML element ID.
   

   

.. js:function:: FormBuilder.addCheckbox(id, name, label, checked)

   Add a checkbox to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Boolean checked: Whether to default to checked or not
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addCurrency(id, name, label, options)

   Add a text ``input`` for currency to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Object options: 
   :param String options.htmlClass: The HTML class to apply to the element; defaults to ``form-control``.
   :param String options.helpBlock: Content for block of help text after input; defaults to null.
   :param String options.groupHtml: Additional HTML to add to the outermost form-group div. This is where we'd usually add a default style/display. Defaults to null.
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addDatePicker(id, name, label, options)

   Add a date picker input to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Object options: 
   :param String options.groupHtml: Additional HTML to add to the outermost
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
   

   

.. js:function:: FormBuilder.addRadioInline(name, label, options)

   Add an inline radio button set to the form.
   
   Options is an Array of Objects, each object having keys ``id``, ``value``
   and ``label``. Optional keys are ``checked`` (Boolean) and ``onchange``,
   which will have its value placed literally in the HTML.

   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Array options: the options for the select; array of objects each having the following attributes:
   :param String options.id: the ID for the option
   :param String options.value: the value for the option
   :param String options.label: the label for the option
   :param Boolean options.checked: whether the option should be checked by default *(optional; defaults to false)*
   :param String options.inputHtml: extra HTML string to include in the actual ``input`` element *(optional; defaults to null)*
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addSelect(id, name, label, options)

   Add a select element to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Array options: the options for the select, array of objects (order is preserved) each having the following attributes:
   :param String options.label: the label for the option
   :param String options.value: the value for the option
   :param Boolean options.selected: whether the option should be the default selected value *(optional; defaults to False)*
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addText(id, name, label, options)

   Add a text ``input`` to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param Object options: 
   :param String options.groupHtml: Additional HTML to add to the outermost
   :param String options.inputHtml: extra HTML string to include in the actual ``input`` element *(optional; defaults to null)*
   :param String options.helpBlock: Content for block of help text after input; defaults to null.
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.render()

   Return complete rendered HTML for the form.

   :returns: **String** -- form HTML
   

   

