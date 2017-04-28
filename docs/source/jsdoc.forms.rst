jsdoc.forms
===========

File: ``biweeklybudget/flaskapp/static/js/forms.js``

.. js:function:: handleForm(container_id, form_id, post_url, dataTableObj)

   Generic function to handle form submission with server-side validation.
   
   See the Python server-side code for further information.

   :param string container_id: The ID of the container element (div) that is the visual parent of the form. On successful submission, this element will be emptied and replaced with a success message.
   :param string form_id: The ID of the form itself.
   :param string post_url: Relative URL to post form data to.
   :param Object dataTableObj: passed on to ``handleFormSubmitted()``
   

   

.. js:function:: handleFormError(jqXHR, textStatus, errorThrown, container_id, form_id)

   Handle an error in the HTTP request to submit the form.

   

   

.. js:function:: handleFormSubmitted(data, container_id, form_id, dataTableObj)

   Handle the response from the API URL that the form data is POSTed to.
   
   This should either display a success message, or one or more error messages.

   :param Object data: response data
   :param string container_id: the ID of the modal container on the page
   :param string form_id: the ID of the form on the page
   :param Object dataTableObj: A reference to the DataTable on the page, that needs to be refreshed. If null, reload the whole page. If a function, call that function. If false, do nothing.
   

   

.. js:function:: isFunction(functionToCheck)

   Return True if ``functionToCheck`` is a function, False otherwise.
   
   From: http://stackoverflow.com/a/7356528/211734

   :param Object functionToCheck: The object to test.
   

   

.. js:function:: serializeForm(form_id)

   Given the ID of a form, return an Object (hash/dict) of all data from it,
   to POST to the server.

   :param string form_id: The ID of the form itself.
   

   

