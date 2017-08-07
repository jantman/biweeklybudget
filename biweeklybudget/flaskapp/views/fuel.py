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
from sqlalchemy import or_, asc
from decimal import Decimal, ROUND_FLOOR
from datetime import datetime
from copy import copy

from biweeklybudget.flaskapp.app import app
from biweeklybudget.db import db_session
from biweeklybudget.models.fuel import FuelFill, Vehicle
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.flaskapp.views.searchableajaxview import SearchableAjaxView
from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView


logger = logging.getLogger(__name__)


class FuelView(MethodView):
    """
    Render the GET /fuel view using the ``fuel.html`` template.
    """

    def get(self):
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        budgets = {}
        for b in db_session.query(Budget).all():
            if b.is_income:
                budgets['%s (income)' % b.name] = b.id
            else:
                budgets[b.name] = b.id
        vehicles = {
            v.id: {'name': v.name, 'is_active': v.is_active}
            for v in db_session.query(Vehicle).all()
        }
        return render_template(
            'fuel.html',
            accts=accts,
            budgets=budgets,
            vehicles=vehicles
        )


class FuelAjax(SearchableAjaxView):
    """
    Handle GET /ajax/fuelLog endpoint.
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
        # Ok, build our filter...
        veh_filter = args['columns'][1]['search']['value']
        if veh_filter != '' and veh_filter != 'None':
            qs = qs.filter(FuelFill.vehicle_id == veh_filter)
        # search
        if s != '' and s != 'FILTERHACK':
            if len(s) < 3:
                return qs
            s = '%' + s + '%'
            qs = qs.filter(or_(
                FuelFill.notes.like(s)),
                FuelFill.fill_location.like(s)
            )
        return qs

    def get(self):
        """
        Render and return JSON response for GET /ajax/ofx
        """
        args = request.args.to_dict()
        args_dict = self._args_dict(args)
        if self._have_column_search(args_dict) and args['search[value]'] == '':
            args['search[value]'] = 'FILTERHACK'
        table = DataTable(
            args,
            FuelFill,
            db_session.query(FuelFill).filter(
                FuelFill.vehicle.has(is_active=True)
            ),
            [
                (
                    'date',
                    lambda i: i.date.strftime('%Y-%m-%d')
                ),
                (
                    'vehicle',
                    'vehicle.name'
                ),
                'odometer_miles',
                'reported_miles',
                'calculated_miles',
                'level_before',
                'level_after',
                'fill_location',
                'cost_per_gallon',
                'total_cost',
                (
                    'gallons',
                    lambda i: i.gallons.quantize(
                        Decimal('.001'), rounding=ROUND_FLOOR
                    )
                ),
                'reported_mpg',
                'calculated_mpg',
                'notes'
            ]
        )
        table.add_data(
            vehicle_id=lambda o: o.vehicle_id
        )
        if args['search[value]'] != '':
            table.searchable(lambda qs, s: self._filterhack(qs, s, args_dict))
        return jsonify(table.json())


class VehicleAjax(MethodView):
    """
    Handle GET /ajax/vehicle/<int:vehicle_id> endpoint.
    """

    def get(self, vehicle_id):
        v = db_session.query(Vehicle).get(vehicle_id)
        return jsonify(v.as_dict)


class VehicleFormHandler(FormHandlerView):
    """
    Handle POST /forms/vehicle
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
        logger.warning(data)
        have_errors = False
        errors = {k: [] for k in data.keys()}
        if data.get('name', '').strip() == '':
            errors['name'].append('Name cannot be empty')
            have_errors = True
        if data.get('id', '').strip() == '':
            v = db_session.query(Vehicle).filter(
                Vehicle.name.__eq__(data.get('name'))
            ).all()
            if len(v) > 0:
                errors['name'].append('Name must be unique')
                have_errors = True
        else:
            v = db_session.query(Vehicle).filter(
                Vehicle.name.__eq__(data.get('name')),
                Vehicle.id.__ne__(int(data.get('id')))
            ).all()
            if len(v) > 0:
                errors['name'].append('Name must be unique')
                have_errors = True
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
        if 'id' in data and data['id'].strip() != '':
            # updating an existing Vehicle
            veh = db_session.query(Vehicle).get(int(data['id']))
            if veh is None:
                raise RuntimeError("Error: no Vehicle with ID %s" % data['id'])
            action = 'updating Vehicle ' + data['id']
        else:
            veh = Vehicle()
            action = 'creating new Vehicle'
        veh.name = data['name'].strip()
        if data['is_active'] == 'true':
            veh.is_active = True
        else:
            veh.is_active = False
        logger.info('%s: %s', action, veh.as_dict)
        db_session.add(veh)
        db_session.commit()
        return 'Successfully saved Vehicle %d in database.' % veh.id


class FuelLogFormHandler(FormHandlerView):
    """
    Handle POST /forms/fuel
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
        errors = self._validate_date_ymd('date', data, errors)
        if data['add_trans'] == 'true':
            if data['account'] == 'None':
                errors['account'].append('Transactions must have an account')
            if data['budget'] == 'None':
                errors['budget'].append('Transactions must have a budget')
        if db_session.query(Vehicle).get(int(data['vehicle'])) is None:
            errors['vehicle'].append('Invalid Vehicle ID %s' % data['vehicle'])
        errors = self._validate_int('odometer_miles', data, errors)
        errors = self._validate_int('reported_miles', data, errors)
        errors = self._validate_not_empty('fill_location', data, errors)
        errors = self._validate_float('cost_per_gallon', data, errors)
        errors = self._validate_float('total_cost', data, errors)
        errors = self._validate_float('gallons', data, errors)
        errors = self._validate_float('reported_mpg', data, errors)
        errors = self._validate_int('vehicle', data, errors)
        errors = self._validate_int('level_before', data, errors)
        errors = self._validate_int('level_after', data, errors)
        if len(errors['total_cost']) == 0 and float(data['total_cost']) == 0:
            errors['total_cost'].append('Total Cost cannot be zero')
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
        total = float(data['total_cost'])
        dt = datetime.strptime(data['date'], '%Y-%m-%d').date()
        veh_name = db_session.query(Vehicle).get(int(data['vehicle'])).name
        fill = FuelFill()
        fill.date = dt
        fill.vehicle_id = int(data['vehicle'])
        fill.odometer_miles = int(data['odometer_miles'])
        fill.reported_miles = int(data['reported_miles'])
        fill.level_before = int(data['level_before'])
        fill.level_after = int(data['level_after'])
        fill.fill_location = data['fill_location'].strip()
        fill.cost_per_gallon = float(data['cost_per_gallon'])
        fill.total_cost = total
        fill.gallons = float(data['gallons'])
        fill.reported_mpg = float(data['reported_mpg'])
        fill.notes = data['notes'].strip()
        logger.info('Creating new FuelFill: %s', fill.as_dict)
        db_session.add(fill)
        db_session.commit()
        fill.calculate_mpg()
        db_session.commit()
        if data['add_trans'] != 'true':
            return {
                'success_message': 'Successfully saved FuelFill %d '
                                   'in database.' % fill.id,
                'success': True,
                'fill_id': fill.id,
                'calculated_mpg': fill.calculated_mpg
            }
        trans = Transaction()
        budg = db_session.query(Budget).get(int(data['budget']))
        trans.description = '%s - FuelFill #%d (%s)' % (
            data['fill_location'].strip(), fill.id, veh_name
        )
        trans.date = dt
        trans.actual_amount = total
        trans.account_id = int(data['account'])
        trans.budget = budg
        trans.notes = data['notes'].strip()
        logger.info('Creating new Transaction for FuelFill: %s', trans.as_dict)
        db_session.add(trans)
        db_session.commit()
        return {
            'success_message': 'Successfully saved FuelFill %d '
                               ' and Transaction %d in database.' % (
                                  fill.id, trans.id),
            'success': True,
            'trans_id': trans.id,
            'fill_id': fill.id,
            'calculated_mpg': fill.calculated_mpg
        }


class FuelMPGChartView(MethodView):
    """
    Handle GET /ajax/chart-data/fuel-economy endpoint.
    """

    def get(self):
        vehicles = {
            x.id: x.name for x in
            db_session.query(
                Vehicle
            ).filter(Vehicle.is_active.__eq__(True)).all()
        }
        veh_names = vehicles.values()
        datedict = {x: None for x in veh_names}
        data = {}
        mpgs = db_session.query(
            FuelFill
        ).filter(
            FuelFill.vehicle.has(is_active=True),
            FuelFill.calculated_mpg.__ne__(None)
        ).order_by(asc(FuelFill.date), asc(FuelFill.odometer_miles))
        for mpg in mpgs.all():
            ds = mpg.date.strftime('%Y-%m-%d')
            if ds not in data:
                data[ds] = copy(datedict)
                data[ds]['date'] = ds
            if mpg.calculated_mpg is None:
                data[ds][mpg.vehicle.name] = 0.0
            else:
                data[ds][mpg.vehicle.name] = float(mpg.calculated_mpg)
        resdata = []
        last = None
        for k in sorted(data.keys()):
            if last is None:
                last = data[k]
                continue
            d = copy(data[k])
            for subk in veh_names:
                if d[subk] is None:
                    d[subk] = last[subk]
            last = d
            resdata.append(d)
        res = {
            'data': resdata,
            'keys': sorted(veh_names)
        }
        return jsonify(res)


class FuelPriceChartView(MethodView):
    """
    Handle GET /ajax/chart-data/fuel-prices endpoint.
    """

    def get(self):
        resdata = []
        prices = db_session.query(
            FuelFill
        ).filter(
            FuelFill.cost_per_gallon.__ne__(None)
        ).order_by(asc(FuelFill.date))
        for point in prices.all():
            ds = point.date.strftime('%Y-%m-%d')
            resdata.append({
                'date': ds,
                'price': float(point.cost_per_gallon)
            })
        res = {
            'data': resdata
        }
        return jsonify(res)


app.add_url_rule('/fuel', view_func=FuelView.as_view('fuel_view'))
app.add_url_rule(
    '/ajax/fuelLog',
    view_func=FuelAjax.as_view('fuel_ajax')
)
app.add_url_rule(
    '/ajax/vehicle/<int:vehicle_id>',
    view_func=VehicleAjax.as_view('vehicle_ajax')
)
app.add_url_rule(
    '/forms/vehicle',
    view_func=VehicleFormHandler.as_view('vehicle_form')
)
app.add_url_rule(
    '/forms/fuel',
    view_func=FuelLogFormHandler.as_view('fuel_form')
)
app.add_url_rule(
    '/ajax/chart-data/fuel-economy',
    view_func=FuelMPGChartView.as_view('fuel_mpg_chart_view')
)
app.add_url_rule(
    '/ajax/chart-data/fuel-prices',
    view_func=FuelPriceChartView.as_view('fuel_price_chart_view')
)
