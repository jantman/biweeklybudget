"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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
from flask import jsonify, request
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class FormHandlerView(MethodView):

    def post(self):
        """
        Handle a POST request for a form. Validate it, if valid update the DB.

        Returns a JSON hash with the following structure:

        'errors' -> hash of field names to list of error strings
        'error_message' -> string error message
        'success' -> boolean
        'success_message' -> string success message
        """
        data = request.form.to_dict()
        res = self.validate(data)
        if res is not None:
            logger.info('Form validation failed. data=%s errors=%s',
                        data, res)
            return jsonify({
                'success': False,
                'errors': res
            })
        try:
            res = self.submit(data)
        except Exception as ex:
            logger.warning('Form submission failed. data=%s', data,
                           exc_info=True)
            return jsonify({
                'success': False,
                'error_message': str(ex)
            })
        if isinstance(res, type({})):
            return jsonify(res)
        return jsonify({
            'success': True,
            'success_message': res
        })

    def validate(self, data):
        """
        Validate the form data. Return None if it is valid, or else a hash of
        field names to list of error strings for each field.

        :param data: submitted form data
        :type data: dict
        :return: None if no errors, or hash of field name to errors for that
          field
        """
        raise NotImplementedError()

    def _validate_int(self, key, data, errors):
        """
        Validate an integer field.

        :param key: the key in data to look at
        :type key: str
        :param data: the form data
        :type data: dict
        :param err_list: list of error messages for the field
        :type err_list: dict
        :return: updated err_list
        :rtype: dict
        """
        try:
            x = int(data[key])
            assert data[key] == '%d' % x
        except Exception:
            errors[key].append('Invalid integer value: "%s"' % data[key])
        return errors

    def _validate_float(self, key, data, errors):
        """
        Validate a float field.

        :param key: the key in data to look at
        :type key: str
        :param data: the form data
        :type data: dict
        :param err_list: list of error messages for the field
        :type err_list: dict
        :return: updated err_list
        :rtype: dict
        """
        try:
            x = float(data[key])
            assert data[key].startswith('%s' % x)
        except Exception:
            errors[key].append('Invalid float value: "%s"' % data[key])
        return errors

    def _validate_decimal(self, key, data, errors):
        """
        Validate a Decimal field.

        :param key: the key in data to look at
        :type key: str
        :param data: the form data
        :type data: dict
        :param err_list: list of error messages for the field
        :type err_list: dict
        :return: updated err_list
        :rtype: dict
        """
        try:
            Decimal(data[key])
        except Exception:
            errors[key].append('Invalid Decimal value: "%s"' % data[key])
        return errors

    def _validate_date_ymd(self, key, data, errors):
        """
        Validate a YYYY-mm-dd date field.

        :param key: the key in data to look at
        :type key: str
        :param data: the form data
        :type data: dict
        :param err_list: list of error messages for the field
        :type err_list: dict
        :return: updated err_list
        :rtype: dict
        """
        if data[key].strip() == '':
            errors[key].append('Date cannot be empty')
            return errors
        try:
            datetime.strptime(data[key], '%Y-%m-%d').date()
        except Exception:
            errors[key].append(
                'Date "%s" is not valid (YYYY-MM-DD)' % data[key]
            )
        return errors

    def _validate_not_empty(self, key, data, errors):
        """
        Validate that a string is not empty.

        :param key: the key in data to look at
        :type key: str
        :param data: the form data
        :type data: dict
        :param err_list: list of error messages for the field
        :type err_list: dict
        :return: updated err_list
        :rtype: dict
        """
        if data[key].strip() == '':
            errors[key].append('Cannot be empty')
        return errors

    def fix_string(self, s):
        """
        Strip a string. If the result is empty, return None. Otherwise return
        the result.

        :param s: form data value
        :type s: str
        :return: stripped string or None
        """
        s = s.strip()
        if s == '':
            return None
        return s

    def submit(self, data):
        """
        Handle form submission; create or update models in the DB.

        :param data: submitted form data
        :type data: dict
        :return: message describing changes to DB
        :rtype: str
        """
        raise NotImplementedError()
