"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016-2024 Jason Antman <http://www.jasonantman.com>

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
from sqlalchemy import func

from biweeklybudget.db import db_session
from biweeklybudget.utils import parse_currency, CurrencyParseError

logger = logging.getLogger(__name__)


class FormHandlerView(MethodView):

    #: List of names of form fields that hold currency amounts. Values of these
    #: fields are normalized to a canonical numeric string by
    #: :py:meth:`~.normalize_currency` before :py:meth:`~.validate` is called,
    #: so that user-entered formatting such as ``$1,234.56`` or a bare ``123``
    #: is accepted everywhere. See GitHub issue #323.
    currency_fields = []

    #: List of names of form fields that hold non-currency decimal numbers.
    #: Normalized identically to :py:attr:`~.currency_fields`, but reported
    #: with "number" rather than "amount" wording when invalid.
    decimal_fields = []

    def post(self):
        """
        Handle a POST request for a form. Validate it, if valid update the DB.

        Returns a JSON hash with the following structure:

        'errors' -> hash of field names to list of error strings
        'error_message' -> string error message
        'success' -> boolean
        'success_message' -> string success message
        """
        data = request.get_json(silent=True)
        if data is None:
            # not JSON, must be form encoded
            data = request.form.to_dict()
        errors = self.normalize_currency(data)
        if errors:
            logger.info('Currency normalization failed. data=%s errors=%s',
                        data, errors)
            return jsonify({
                'success': False,
                'errors': errors
            })
        try:
            res = self.validate(data)
        except Exception as ex:
            logger.warning('Form validation raised an exception. data=%s',
                           data, exc_info=True)
            return jsonify({
                'success': False,
                'error_message': str(ex)
            })
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

    def normalize_currency(self, data):
        """
        Normalize every field named in :py:attr:`~.currency_fields` and
        :py:attr:`~.decimal_fields` to a canonical numeric string, in place.

        This is the single place where user-entered currency formatting is
        interpreted on the server; doing it here, before
        :py:meth:`~.validate` runs, means every downstream
        ``Decimal(data[key])`` and ``float(data[key])`` in ``validate()`` and
        ``submit()`` receives a value it can parse. See GitHub issue #323.

        Fields that are absent from ``data``, that are empty or whitespace
        only, or that are not strings, are left untouched - each field's
        existing "blank means zero" or "blank is an error" behavior is
        unchanged by normalization.

        :param data: submitted form data; modified in place
        :type data: dict
        :return: hash of field name to list of error strings for that field;
          empty if every field was valid
        :rtype: dict
        """
        errors = {}
        fields = [(k, 'amount') for k in self.currency_fields]
        fields += [(k, 'number') for k in self.decimal_fields]
        for key, noun in fields:
            if key not in data:
                continue
            value = data[key]
            if not isinstance(value, str) or value.strip() == '':
                continue
            try:
                data[key] = str(parse_currency(value))
            except CurrencyParseError:
                errors.setdefault(key, []).append(
                    'Invalid %s: "%s"' % (noun, value)
                )
        return errors

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
        Validate a numeric (non-currency) field.

        Accepts anything :py:func:`~biweeklybudget.utils.parse_currency`
        accepts, which includes bare integers; the previous implementation
        required a decimal point, rejecting ``123`` while accepting ``123.0``
        (GitHub issue #323).

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
            parse_currency(data[key])
        except Exception:
            errors[key].append('Invalid number: "%s"' % data[key])
        return errors

    def _validate_decimal(self, key, data, errors):
        """
        Validate a currency amount field.

        Accepts anything :py:func:`~biweeklybudget.utils.parse_currency`
        accepts, i.e. bare integers, thousands separators and a currency
        symbol (GitHub issue #323).

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
            parse_currency(data[key])
        except Exception:
            errors[key].append('Invalid amount: "%s"' % data[key])
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

    def _validate_unique_name(self, cls, data, errors, noun, key='name'):
        """
        Validate that the submitted name in ``data[key]`` is not already used
        by a different record of model class ``cls``.

        ``Account.name`` and ``Budget.name`` are ``unique=True``. Without this
        check the constraint is only discovered when the database rejects the
        write, and the resulting ``IntegrityError`` - complete with the SQL
        statement and every bound parameter - is handed to the user as a
        generic "Server Error" banner that does not even say which field was
        at fault. Checking here instead attaches the message to the offending
        field and means nothing is written, so the record store is untouched
        and no rollback is needed. See GitHub issue #275.

        The comparison is deliberately made on the **stripped** name, because
        that is what ``submit()`` stores; comparing the raw value would let
        ``" Foo "`` pass this check and then be written as a duplicate of an
        existing ``"Foo"``.

        The comparison is also deliberately **case-insensitive**, via an
        explicit :py:func:`sqlalchemy.func.lower` rather than by relying on
        the database collation, for the same reason it is done that way in
        :py:func:`biweeklybudget.models.utils._resolve_reference`: the
        behavior is then a property of this code and is pinned by a test. Two
        records whose names differ only in case must not coexist regardless of
        what the unique index permits, because ``_resolve_reference`` matches
        API names with ``func.lower()`` and ``one_or_none()`` and would raise
        for either of them.

        A blank name is left alone. Callers already report that with their own
        "Name cannot be empty" message, and stacking a second message on top
        of it would only confuse.

        The message quotes the **stored** name rather than the submitted one,
        so that a user who typed ``bankone`` is shown the ``BankOne`` they
        actually collided with.

        :param cls: the model class to check; must have ``id`` and a unique
          ``name`` column
        :type cls: type
        :param data: submitted form data
        :type data: dict
        :param errors: hash of field name to list of error strings, as built
          by the calling ``validate()``
        :type errors: dict
        :param noun: human-readable name of the model, used in the message
          (i.e. ``Account`` or ``Budget``)
        :type noun: str
        :param key: the key in ``data`` and ``errors`` holding the name
        :type key: str
        :return: updated ``errors``
        :rtype: dict
        """
        name = data.get(key, '').strip()
        if name == '':
            return errors
        record_id = 0
        if 'id' in data and str(data['id']).strip() != '':
            record_id = int(data['id'])
        existing = db_session.query(cls).filter(
            func.lower(cls.name) == name.lower(),
            cls.id != record_id
        ).first()
        if existing is not None:
            article = 'An' if noun[0].upper() in 'AEIOU' else 'A'
            errors[key].append(
                f'{article} {noun} named "{existing.name}" already exists '
                f'(ID {existing.id}); {noun} names must be unique.'
            )
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
