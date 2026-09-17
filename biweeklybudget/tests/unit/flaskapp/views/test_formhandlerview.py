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
from unittest.mock import Mock, patch

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from biweeklybudget.flaskapp.views.formhandlerview import FormHandlerView

pbm = 'biweeklybudget.flaskapp.views.formhandlerview'

#: Throwaway declarative base, so ``FakeModel`` below is a real mapped class
#: whose columns compile to SQL, without touching the application's metadata.
FakeBase = declarative_base()


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


class FakeModel(FakeBase):
    """
    Stand-in for a model class with a unique ``name``, for testing
    :py:meth:`~.FormHandlerView._validate_unique_name` without a database.
    """

    __tablename__ = 'fakes'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True)


class TestValidateUniqueName(object):
    """
    Tests for :py:meth:`~.FormHandlerView._validate_unique_name`; see GitHub
    issue #275.

    The database is mocked out here, so these tests pin two things: the
    message produced when a conflict is found, and the *criteria* the query is
    built from - which is where the trimming and case-insensitivity that
    FR-007 requires actually live. That a duplicate is really rejected end to
    end, against a real MySQL collation, is covered by the acceptance tests in
    ``tests/acceptance/flaskapp/views/test_accounts.py`` and
    ``test_budgets.py``.
    """

    def setup_method(self):
        self.cls = StubFormHandler()

    def _record(self, id, name):
        """
        A stand-in for a conflicting record. ``name`` must be assigned after
        construction: ``Mock(name=...)`` sets the mock's own name rather than
        an attribute called ``name``.
        """
        rec = Mock(id=id)
        rec.name = name
        return rec

    def _mock_session(self, found=None):
        """
        Return (mock db_session, query mock). ``found`` is what ``.first()``
        yields - a conflicting record, or None for no conflict.
        """
        mock_sess = Mock()
        mock_sess.query.return_value.filter.return_value.first.return_value = \
            found
        return mock_sess

    def _criteria_sql(self, mock_sess):
        """
        Return the criteria passed to ``.filter()``, compiled to SQL strings
        with literals inlined, so the comparison the query actually makes can
        be asserted on.
        """
        args = mock_sess.query.return_value.filter.call_args[0]
        return [
            str(c.compile(compile_kwargs={'literal_binds': True}))
            for c in args
        ]

    def test_duplicate_name_is_rejected(self):
        existing = self._record(1, 'BankOne')
        mock_sess = self._mock_session(found=existing)
        data = {'id': '', 'name': 'BankOne'}
        errors = {'id': [], 'name': []}
        with patch('%s.db_session' % pbm, mock_sess):
            res = self.cls._validate_unique_name(
                FakeModel, data, errors, 'Account'
            )
        assert res['name'] == [
            'An Account named "BankOne" already exists (ID 1); '
            'Account names must be unique.'
        ]

    def test_unique_name_is_accepted(self):
        mock_sess = self._mock_session(found=None)
        data = {'id': '', 'name': 'BrandNew'}
        errors = {'id': [], 'name': []}
        with patch('%s.db_session' % pbm, mock_sess):
            res = self.cls._validate_unique_name(
                FakeModel, data, errors, 'Account'
            )
        assert res['name'] == []

    def test_article_agrees_with_the_noun(self):
        """
        "An Account" but "A Budget" - the message is shown to a human.
        """
        existing = self._record(3, 'Periodic1')
        mock_sess = self._mock_session(found=existing)
        errors = {'id': [], 'name': []}
        with patch('%s.db_session' % pbm, mock_sess):
            res = self.cls._validate_unique_name(
                FakeModel, {'id': '', 'name': 'Periodic1'}, errors, 'Budget'
            )
        assert res['name'][0].startswith('A Budget named "Periodic1"')

    def test_message_quotes_the_stored_name_not_the_submitted_one(self):
        """
        A user who typed "bankone" should be shown the "BankOne" they hit.
        """
        existing = self._record(1, 'BankOne')
        mock_sess = self._mock_session(found=existing)
        errors = {'id': [], 'name': []}
        with patch('%s.db_session' % pbm, mock_sess):
            res = self.cls._validate_unique_name(
                FakeModel, {'id': '', 'name': 'bankone'}, errors, 'Account'
            )
        assert '"BankOne"' in res['name'][0]
        assert '"bankone"' not in res['name'][0]

    def test_comparison_is_made_on_the_stripped_name(self):
        """
        ``submit()`` stores ``data['name'].strip()``, so validating the
        unstripped value would let "  Foo  " through and then write it as a
        duplicate of an existing "Foo".
        """
        mock_sess = self._mock_session(found=None)
        errors = {'id': [], 'name': []}
        with patch('%s.db_session' % pbm, mock_sess):
            self.cls._validate_unique_name(
                FakeModel, {'id': '', 'name': '   BankOne   '}, errors,
                'Account'
            )
        sql = self._criteria_sql(mock_sess)
        assert "lower(fakes.name) = 'bankone'" in sql[0]

    def test_comparison_is_case_insensitive(self):
        """
        Both sides are lower-cased explicitly rather than relying on the
        collation, as ``models/utils.py::_resolve_reference`` does.
        """
        mock_sess = self._mock_session(found=None)
        errors = {'id': [], 'name': []}
        with patch('%s.db_session' % pbm, mock_sess):
            self.cls._validate_unique_name(
                FakeModel, {'id': '', 'name': 'BANKONE'}, errors, 'Account'
            )
        sql = self._criteria_sql(mock_sess)
        assert 'lower(fakes.name)' in sql[0]
        assert "'bankone'" in sql[0]

    def test_new_record_excludes_id_zero(self):
        """
        A create has no ID yet; 0 is a safe sentinel because these keys are
        AUTO_INCREMENT and start at 1.
        """
        mock_sess = self._mock_session(found=None)
        errors = {'id': [], 'name': []}
        with patch('%s.db_session' % pbm, mock_sess):
            self.cls._validate_unique_name(
                FakeModel, {'id': '', 'name': 'Foo'}, errors, 'Account'
            )
        sql = self._criteria_sql(mock_sess)
        assert 'fakes.id != 0' in sql[1]

    def test_edit_excludes_the_record_being_edited(self):
        """
        Re-saving a record without renaming it must not collide with itself.
        """
        mock_sess = self._mock_session(found=None)
        errors = {'id': [], 'name': []}
        with patch('%s.db_session' % pbm, mock_sess):
            self.cls._validate_unique_name(
                FakeModel, {'id': '7', 'name': 'Foo'}, errors, 'Account'
            )
        sql = self._criteria_sql(mock_sess)
        assert 'fakes.id != 7' in sql[1]

    @pytest.mark.parametrize('name', ['', '   ', '\t\n'])
    def test_blank_name_adds_no_message_and_makes_no_query(self, name):
        """
        Callers already report a blank name with their own "Name cannot be
        empty"; a second message on the same field would only confuse.
        """
        mock_sess = self._mock_session(found=None)
        errors = {'id': [], 'name': ['Name cannot be empty']}
        with patch('%s.db_session' % pbm, mock_sess):
            res = self.cls._validate_unique_name(
                FakeModel, {'id': '', 'name': name}, errors, 'Account'
            )
        assert res['name'] == ['Name cannot be empty']
        assert mock_sess.query.mock_calls == []

    def test_absent_name_key_is_tolerated(self):
        mock_sess = self._mock_session(found=None)
        errors = {'id': []}
        with patch('%s.db_session' % pbm, mock_sess):
            res = self.cls._validate_unique_name(
                FakeModel, {'id': ''}, errors, 'Account'
            )
        assert res == {'id': []}
        assert mock_sess.query.mock_calls == []
