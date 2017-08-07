"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2017 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

    This file is part of biweeklybudget, also known as biweeklybudget.

    biweeklybudget is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    biweeklybudget is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with biweeklybudget.  If not, see <http://www.gnu.org/licenses/>.

The Copyright and Authors attributions contained herein may not be removed or
otherwise altered, except to add the Author attribution of a contributor to
this work. (Additional Terms pursuant to Section 7b of the AGPL v3)
################################################################################
While not legally required, I sincerely request that anyone who finds
bugs please submit them at <https://github.com/jantman/biweeklybudget> or
to me via email, and that you send any contributions or improvements
either as a pull request on GitHub, or to me via email.
################################################################################

AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""

import logging
from flask.views import MethodView
from flask import render_template, jsonify, request
from datatables import DataTable
from sqlalchemy import or_

from biweeklybudget.flaskapp.app import app
from biweeklybudget.db import db_session
from biweeklybudget.models.projects import Project, BoMItem
from biweeklybudget.flaskapp.views.searchableajaxview import SearchableAjaxView
from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView


logger = logging.getLogger(__name__)


class ProjectsView(MethodView):
    """
    Render the GET /projects view using the ``projects.html`` template.
    """

    def get(self):
        total_active = 0.0
        remain_active = 0.0
        for p in db_session.query(Project).filter(
                Project.is_active.__eq__(True)
        ).all():
            total_active += p.total_cost
            remain_active += p.remaining_cost
        return render_template(
            'projects.html',
            total_active=total_active,
            remain_active=remain_active
        )


class ProjectsAjax(SearchableAjaxView):
    """
    Handle GET /ajax/projects endpoint.
    """

    def _filterhack(self, qs, s, args):
        """
        DataTables 1.10.12 has built-in support for filtering based on a value
        in a specific column; when this is done, the filter value is set in
        ``columns[N][search][value]`` where N is the column number. However,
        the python datatables package used here only supports the global
        ``search[value]`` input, not the per-column one.

        However, the DataTable search is implemented by passing a callable
        to ``table.searchable()`` which takes two arguments, the current Query
        that's being built, and the user's ``search[value]`` input; this must
        then return a Query object with the search applied.

        In python datatables 0.4.9, this code path is triggered on
        ``if callable(self.search_func) and search.get("value", None):``

        As such, we can "trick" the table to use per-column searching (currently
        only if global searching is not being used) by examining the per-column
        search values in the request, and setting the search function to one
        (this method) that uses those values instead of the global
        ``search[value]``.

        :param qs: Query currently being built
        :type qs: ``sqlalchemy.orm.query.Query``
        :param s: user search value
        :type s: str
        :param args: args
        :type args: dict
        :return: Query with searching applied
        :rtype: ``sqlalchemy.orm.query.Query``
        """
        # search
        if s != '' and s != 'FILTERHACK':
            if len(s) < 3:
                return qs
            s = '%' + s + '%'
            qs = qs.filter(or_(
                Project.notes.like(s),
                Project.name.like(s)
            ))
        return qs

    def get(self):
        """
        Render and return JSON response for GET /ajax/projects
        """
        args = request.args.to_dict()
        args_dict = self._args_dict(args)
        if self._have_column_search(args_dict) and args['search[value]'] == '':
            args['search[value]'] = 'FILTERHACK'
        table = DataTable(
            args,
            Project,
            db_session.query(Project),
            [
                'name',
                'total_cost',
                'remaining_cost',
                'is_active',
                'notes'
            ]
        )
        table.add_data(
            id=lambda o: o.id
        )
        if args['search[value]'] != '':
            table.searchable(lambda qs, s: self._filterhack(qs, s, args_dict))
        return jsonify(table.json())


class ProjectsFormHandler(FormHandlerView):
    """
    Handle POST /forms/projects
    """

    def validate(self, data):
        """
        Validate the form data. Return None if it is valid, or else a hash of
        field names to list of error strings for each field.

        :param data: submitted form data
        :type data: dict
        :return: None if no errors, or hash of field name to errors for that
          field
        """
        have_errors = False
        errors = {k: [] for k in data.keys()}
        action = data.get('action', None)
        if action is None:
            raise RuntimeError('No action specified in form data!')
        elif action == 'add':
            if data.get('name', '').strip() == '':
                errors['name'].append('Name cannot be empty')
                have_errors = True
            if len(data.get('name').strip()) > 40:
                errors['name'].append('Name must be <= 40 characters in length')
                have_errors = True
            q = db_session.query(Project).filter(
                Project.name.__eq__(data['name'].strip())
            ).all()
            if len(q) > 0:
                errors['name'].append('Name must be unique')
                have_errors = True
        elif action in ['activate', 'deactivate']:
            if 'id' not in data:
                raise RuntimeError('id must be specified to (de)activate')
            p = db_session.query(Project).get(int(data['id']))
            if p is None:
                raise RuntimeError('Invalid Project id: %s' % data['id'])
        else:
            raise RuntimeError('Invalid action: %s' % action)
        if have_errors:
            return errors
        return None

    def submit(self, data):
        """
        Handle form submission; create or update models in the DB. Raises an
        Exception for any errors.

        :param data: submitted form data
        :type data: dict
        :return: message describing changes to DB (i.e. link to created record)
        :rtype: str
        """
        action = data.get('action', None)
        if action == 'add':
            proj = Project()
            proj.name = data['name'].strip()
            proj.notes = data['notes'].strip()
        elif action == 'activate':
            proj = db_session.query(Project).get(int(data['id']))
            logger.info('Activate %s', proj)
            proj.is_active = True
        elif action == 'deactivate':
            proj = db_session.query(Project).get(int(data['id']))
            logger.info('Deactivate %s', proj)
            proj.is_active = False
        else:
            raise RuntimeError('Invalid action: %s' % action)
        db_session.add(proj)
        db_session.commit()
        if action == 'add':
            logger.info('Created Project %s', proj)
        return 'Successfully saved Project %d in database.' % proj.id


class BoMItemView(MethodView):
    """
    Render the GET /project/<int:project_id> view using the ``bomitem.html``
    template.
    """

    def get(self, project_id):
        proj = db_session.query(Project).get(project_id)
        return render_template(
            'bomitem.html',
            project_id=project_id,
            project_name=proj.name,
            project_notes=proj.notes,
            remaining=proj.remaining_cost,
            total=proj.total_cost
        )


class BoMItemsAjax(SearchableAjaxView):
    """
    Handle GET /ajax/projects/<int:project_id>/bom_items endpoint.
    """

    def _filterhack(self, qs, s, args):
        """
        DataTables 1.10.12 has built-in support for filtering based on a value
        in a specific column; when this is done, the filter value is set in
        ``columns[N][search][value]`` where N is the column number. However,
        the python datatables package used here only supports the global
        ``search[value]`` input, not the per-column one.

        However, the DataTable search is implemented by passing a callable
        to ``table.searchable()`` which takes two arguments, the current Query
        that's being built, and the user's ``search[value]`` input; this must
        then return a Query object with the search applied.

        In python datatables 0.4.9, this code path is triggered on
        ``if callable(self.search_func) and search.get("value", None):``

        As such, we can "trick" the table to use per-column searching (currently
        only if global searching is not being used) by examining the per-column
        search values in the request, and setting the search function to one
        (this method) that uses those values instead of the global
        ``search[value]``.

        :param qs: Query currently being built
        :type qs: ``sqlalchemy.orm.query.Query``
        :param s: user search value
        :type s: str
        :param args: args
        :type args: dict
        :return: Query with searching applied
        :rtype: ``sqlalchemy.orm.query.Query``
        """
        # search
        if s != '' and s != 'FILTERHACK':
            if len(s) < 3:
                return qs
            s = '%' + s + '%'
            qs = qs.filter(or_(
                BoMItem.notes.like(s),
                BoMItem.name.like(s),
                BoMItem.url.like(s)
            ))
        return qs

    def get(self, project_id):
        """
        Render and return JSON response for
        GET /ajax/projects/<int:project_id>/bom_items
        """
        args = request.args.to_dict()
        args_dict = self._args_dict(args)
        if self._have_column_search(args_dict) and args['search[value]'] == '':
            args['search[value]'] = 'FILTERHACK'
        table = DataTable(
            args,
            BoMItem,
            db_session.query(BoMItem).filter(
                BoMItem.project_id.__eq__(project_id)
            ),
            [
                'name',
                'quantity',
                'unit_cost',
                'is_active',
                'notes',
                'url',
                'id'
            ]
        )
        table.add_data(
            line_cost=lambda o: float(o.unit_cost) * o.quantity
        )
        if args['search[value]'] != '':
            table.searchable(lambda qs, s: self._filterhack(qs, s, args_dict))
        return jsonify(table.json())


class ProjectAjax(MethodView):
    """
    Render the GET /ajax/projects/<int:project_id> JSON view.
    """

    def get(self, project_id):
        proj = db_session.query(Project).get(project_id)
        d = proj.as_dict
        d['total_cost'] = proj.total_cost
        d['remaining_cost'] = proj.remaining_cost
        return jsonify(d)


class BoMItemAjax(MethodView):
    """
    Render the GET /ajax/projects/bom_item/<int:id> JSON view.
    """

    def get(self, id):
        return jsonify(db_session.query(BoMItem).get(id).as_dict)


class BoMItemFormHandler(FormHandlerView):
    """
    Handle POST /forms/bom_item
    """

    def validate(self, data):
        """
        Validate the form data. Return None if it is valid, or else a hash of
        field names to list of error strings for each field.

        :param data: submitted form data
        :type data: dict
        :return: None if no errors, or hash of field name to errors for that
          field
        """
        errors = {k: [] for k in data.keys()}
        if data.get('name', '').strip() == '':
            errors['name'].append('name cannot be empty')
        errors = self._validate_int('quantity', data, errors)
        errors = self._validate_int('project_id', data, errors)
        if len(errors['quantity']) < 1:
            if int(data['quantity']) < 0:
                errors['quantity'].append('Quantity cannot be negative')
        errors = self._validate_float('unit_cost', data, errors)
        for v in errors.values():
            if len(v) > 0:
                return errors
        return None

    def submit(self, data):
        """
        Handle form submission; create or update models in the DB. Raises an
        Exception for any errors.

        :param data: submitted form data
        :type data: dict
        :return: message describing changes to DB (i.e. link to created record)
        :rtype: str
        """
        if 'id' in data and data['id'].strip() != '':
            # updating an existing BoMItem
            item = db_session.query(BoMItem).get(int(data['id']))
            if item is None:
                raise RuntimeError("Error: no BoMItem with ID "
                                   "%s" % data['id'])
            action = 'updating BoMItem ' + data['id']
        else:
            item = BoMItem()
            action = 'creating new BoMItem'
        item.project = db_session.query(Project).get(int(data['project_id']))
        item.name = data['name'].strip()
        item.notes = data['notes'].strip()
        item.quantity = int(data['quantity'].strip())
        item.unit_cost = float(data['unit_cost'].strip())
        item.url = data['url'].strip()
        if data['is_active'] == 'true':
            item.is_active = True
        else:
            item.is_active = False
        logger.info('%s: %s', action, item.as_dict)
        db_session.add(item)
        db_session.commit()
        return {
            'success_message': 'Successfully saved BoMItem %d '
                               'in database.' % item.id,
            'success': True,
            'id': item.id
        }


app.add_url_rule('/projects', view_func=ProjectsView.as_view('projects'))
app.add_url_rule(
    '/forms/projects',
    view_func=ProjectsFormHandler.as_view('projects_form')
)
app.add_url_rule(
    '/ajax/projects',
    view_func=ProjectsAjax.as_view('projects_ajax')
)
app.add_url_rule(
    '/projects/<int:project_id>',
    view_func=BoMItemView.as_view('bom_item_view')
)
app.add_url_rule(
    '/ajax/projects/<int:project_id>',
    view_func=ProjectAjax.as_view('ajax_project_view')
)
app.add_url_rule(
    '/ajax/projects/<int:project_id>/bom_items',
    view_func=BoMItemsAjax.as_view('bom_items_ajax')
)
app.add_url_rule(
    '/ajax/projects/bom_item/<int:id>',
    view_func=BoMItemAjax.as_view('bom_item_ajax')
)
app.add_url_rule(
    '/forms/bom_item',
    view_func=BoMItemFormHandler.as_view('bom_item_form')
)
