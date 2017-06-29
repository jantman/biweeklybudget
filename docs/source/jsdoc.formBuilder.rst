jsdoc.formBuilder
=================

File: ``biweeklybudget/flaskapp/static/js/formBuilder.js``

.. js:function:: FormBuilder(id)

   Create a new FormBuilder to generate an HTML form

   :param String id: The form HTML element ID.
   

   

.. js:function:: FormBuilder.addHidden(id, name, value)

   Add a hidden input to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String value: The value of the form element
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addP(content)

   Add a paragraph (``p`` tag) to the form.

   :param String content: The content of the ``p`` tag.
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.addText(id, name, label, htmlClass)

   Add a text input to the form.

   :param String id: The id of the form element
   :param String name: The name of the form element
   :param String label: The label text for the form element
   :param String htmlClass: The HTML class to apply to the element
   :returns: **FormBuilder** -- this
   

   

.. js:function:: FormBuilder.render()

   Return complete rendered HTML for the form.

   :returns: **String** -- form HTML
   

   

