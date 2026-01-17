jsdoc.forms
===========

File: ``biweeklybudget/flaskapp/static/js/forms.js``

.. js:function:: .........m(container_id, form_id, post_url, dataTableObj, serialize_func)

   Generic function to handle form submission with server-side validation.

   See the Python server-side code for further information.

   :param container\_id: The ID of the container element (div) that is the visual parent of the form. On successful submission, this element will be emptied and replaced with a success message.
   :param form\_id: The ID of the form itself.
   :param post\_url: Relative URL to post form data to.
   :param dataTableObj: passed on to ``handleFormSubmitted()``
   :param serialize\_func: If set (i.e. not ``undefined``), this is a function used serialize the form in place of :js:func:`serializeForm`. This function will be passed the ID of the form (``form_id``) and should return an Object suitable for passing to ``JSON.stringify()``.
   :type container\_id: **string**
   :type form\_id: **string**
   :type post\_url: **string**
   :type dataTableObj: **Object**
   :type serialize\_func: **Object**
.. js:function:: ..............r(jqXHR, textStatus, errorThrown, container_id, form_id)

   Handle an error in the HTTP request to submit the form.
.. js:function:: ..................d(data, container_id, form_id, dataTableObj)

   Handle the response from the API URL that the form data is POSTed to.

   This should either display a success message, or one or more error messages.

   :param data: response data
   :param container\_id: the ID of the modal container on the page
   :param form\_id: the ID of the form on the page
   :param dataTableObj: A reference to the DataTable on the page, that needs to be refreshed. If null, reload the whole page. If a function, call that function. If false, do nothing.
   :type data: **Object**
   :type container\_id: **string**
   :type form\_id: **string**
   :type dataTableObj: **Object**
.. js:function:: ...............m(container_id, form_id, post_url, dataTableObj)

   Generic function to handle form submission with server-side validation of
   an inline (non-modal) form.

   See the Python server-side code for further information.

   :param container\_id: The ID of the container element (div) that is the visual parent of the form. On successful submission, this element will be emptied and replaced with a success message.
   :param form\_id: The ID of the form itself.
   :param post\_url: Relative URL to post form data to.
   :param dataTableObj: passed on to ``handleFormSubmitted()``
   :type container\_id: **string**
   :type form\_id: **string**
   :type post\_url: **string**
   :type dataTableObj: **Object**
.. js:function:: ....................r(jqXHR, textStatus, errorThrown, container_id, form_id)

   Handle an error in the HTTP request to submit the inline (non-modal) form.
.. js:function:: ........................d(data, container_id, form_id, dataTableObj)

   Handle the response from the API URL that the form data is POSTed to, for an
   inline (non-modal) form.

   This should either display a success message, or one or more error messages.

   :param data: response data
   :param container\_id: the ID of the modal container on the page
   :param form\_id: the ID of the form on the page
   :param dataTableObj: A reference to the DataTable on the page, that needs to be refreshed. If null, reload the whole page. If a function, call that function. If false, do nothing.
   :type data: **Object**
   :type container\_id: **string**
   :type form\_id: **string**
   :type dataTableObj: **Object**
.. js:function:: .........n(functionToCheck)

   Return True if ``functionToCheck`` is a function, False otherwise.

   From: http://stackoverflow.com/a/7356528/211734

   :param functionToCheck: The object to test.
   :type functionToCheck: **Object**
.. js:function:: ............m(form_id)

   Given the ID of a form, return an Object (hash/dict) of all data from it,
   to POST to the server.

   :param form\_id: The ID of the form itself.
   :type form\_id: **string**
