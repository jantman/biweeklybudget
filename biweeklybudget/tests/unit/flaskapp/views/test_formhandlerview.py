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

import pytest

from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView


class StubFormHandler(FormHandlerView):
    """
    Minimal concrete FormHandlerView, for testing the normalization hook in
    isolation from any real form or database.
    """

    currency_fields = ['amount', 'sales_tax']
    decimal_fields = ['gallons']

    def validate(self, data):
        return None

    def submit(self, data):
        return 'submitted'


class TestNormalizeCurrency(object):
    """
    Tests for :py:meth:`~.FormHandlerView.normalize_currency`; see GitHub
    issue #323.
    """

    def setup_method(self):
        self.cls = StubFormHandler()

    def test_no_declared_fields_is_a_no_op(self):
        class NoFields(StubFormHandler):
            currency_fields = []
            decimal_fields = []

        data = {'amount': '1,234.56'}
        assert NoFields().normalize_currency(data) == {}
        assert data == {'amount': '1,234.56'}

    def test_canonicalizes_currency_field(self):
        data = {'amount': '$1,234.56'}
        assert self.cls.normalize_currency(data) == {}
        assert data == {'amount': '1234.56'}

    def test_canonicalizes_bare_integer(self):
        # github issue #323: must stay integral, not become "123.0"
        data = {'amount': '123'}
        assert self.cls.normalize_currency(data) == {}
        assert data == {'amount': '123'}

    def test_canonicalizes_parenthesized_negative(self):
        data = {'amount': '(1,234.56)'}
        assert self.cls.normalize_currency(data) == {}
        assert data == {'amount': '-1234.56'}

    def test_canonicalizes_decimal_field(self):
        data = {'gallons': '1,234.56'}
        assert self.cls.normalize_currency(data) == {}
        assert data == {'gallons': '1234.56'}

    def test_absent_field_is_skipped(self):
        data = {'description': 'foo'}
        assert self.cls.normalize_currency(data) == {}
        assert data == {'description': 'foo'}

    @pytest.mark.parametrize('value', ['', '   ', '\t'])
    def test_blank_value_is_left_untouched(self, value):
        # blank handling belongs to each field's own validate(); normalization
        # must not turn "optional and empty" into an error
        data = {'amount': value}
        assert self.cls.normalize_currency(data) == {}
        assert data == {'amount': value}

    @pytest.mark.parametrize('value', [None, 123, 12.3, ['1'], {'a': 1}])
    def test_non_string_value_is_left_untouched(self, value):
        data = {'amount': value}
        assert self.cls.normalize_currency(data) == {}
        assert data == {'amount': value}

    def test_undeclared_field_is_not_normalized(self):
        data = {'notes': '1,234.56'}
        assert self.cls.normalize_currency(data) == {}
        assert data == {'notes': '1,234.56'}

    def test_invalid_currency_value_reports_amount_wording(self):
        data = {'amount': 'abc'}
        assert self.cls.normalize_currency(data) == {
            'amount': ['Invalid amount: "abc"']
        }
        # the raw value is left in place for the error message and redisplay
        assert data == {'amount': 'abc'}

    def test_invalid_decimal_value_reports_number_wording(self):
        data = {'gallons': 'abc'}
        assert self.cls.normalize_currency(data) == {
            'gallons': ['Invalid number: "abc"']
        }

    def test_errors_accumulate_across_fields(self):
        # all bad fields are reported at once, not just the first
        data = {'amount': 'abc', 'sales_tax': '1.2.3', 'gallons': '10,00'}
        assert self.cls.normalize_currency(data) == {
            'amount': ['Invalid amount: "abc"'],
            'sales_tax': ['Invalid amount: "1.2.3"'],
            'gallons': ['Invalid number: "10,00"'],
        }

    def test_good_fields_normalized_even_when_another_is_bad(self):
        data = {'amount': '1,234.56', 'sales_tax': 'abc'}
        errors = self.cls.normalize_currency(data)
        assert list(errors.keys()) == ['sales_tax']
        assert data['amount'] == '1234.56'

    def test_ambiguous_grouping_is_rejected_not_guessed(self):
        # a lenient parser reads this as 1000; silently doing so would corrupt
        # a financial record, so it must be an error instead
        data = {'amount': '10,00'}
        assert self.cls.normalize_currency(data) == {
            'amount': ['Invalid amount: "10,00"']
        }
        assert data == {'amount': '10,00'}

    def test_normalized_value_is_parseable_downstream(self):
        # the whole point: validate()/submit() call Decimal() and float() on
        # these values directly
        from decimal import Decimal
        data = {'amount': '$1,234.56', 'gallons': '10'}
        assert self.cls.normalize_currency(data) == {}
        assert Decimal(data['amount']) == Decimal('1234.56')
        assert float(data['gallons']) == 10.0
