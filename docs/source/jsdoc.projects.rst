jsdoc.projects
==============

File: ``biweeklybudget/flaskapp/static/js/projects.js``

.. js:function:: ..............t(proj_id)

   Handler for links to activate a project.
.. js:function:: ................t(proj_id)

   Handler for links to deactivate a project.
.. js:function:: .................d()

   Handler for when a project is added via the form.
.. js:function:: ...........l(id)

   Show the Project edit modal popup, populated with information for one
   Project. This function calls projectModalDivForm to generate the form HTML,
   projectModalDivFillAndShow to populate the form for editing, and handleForm
   to handle the Submit action.

   :param id: the ID of the Project to show a modal for.
   :type id: **number**
.. js:function:: .........................w(msg)

   Ajax callback to fill in the modal with data on a Project.
.. js:function:: ..................m()

   Generate the HTML for the project edit modal form.
