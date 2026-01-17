jsdoc.fuel
==========

File: ``biweeklybudget/flaskapp/static/js/fuel.js``

.. js:function:: ...........l(dataTableObj)

   Show the modal to add a fuel log entry. This function calls
   :js:func:`fuelModalDivForm` to generate the form HTML,
   :js:func:`schedModalDivFillAndShow` to populate the form for editing,
   and :js:func:`handleForm` to handle the Submit action.

   :param dataTableObj: passed on to :js:func:`handleForm`
   :type dataTableObj: **Object|null**
.. js:function:: ...............m()

   Generate the HTML for the form on the Modal
.. js:function:: ...........l(id)

   Show the Vehicle modal popup, optionally populated with
   information for one Vehicle. This function calls
   :js:func:`vehicleModalDivForm` to generate the form HTML,
   :js:func:`vehicleModalDivFillAndShow` to populate the form for editing,
   and :js:func:`handleForm` to handle the Submit action.

   :param id: the ID of the Vehicle to show a modal for, or null to show modal to add a new Vehicle.
   :type id: **number**
.. js:function:: .........................w(msg)

   Ajax callback to fill in the modalDiv with data on a Vehicle.
.. js:function:: ..................m()

   Generate the HTML for the form on the Modal
