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

from biweeklybudget.utils import (
    dtnow, plaid_client, parse_currency, CurrencyParseError
)
from pytz import utc
from datetime import datetime
from decimal import Decimal
from freezegun import freeze_time

from unittest.mock import patch, call, Mock, DEFAULT

pbm: str = 'biweeklybudget.utils'


class TestPlaidClient:

    def test_happy_path(self):
        mock_client = Mock()
        mock_config = Mock()
        mock_api = Mock()

        class MockEnv:
            Production = 'prodEnv'
            Development = 'devEnv'
            Sandbox = 'sandEnv'

        with patch.multiple(
            pbm,
            Configuration=DEFAULT,
            ApiClient=DEFAULT,
            Environment=MockEnv,
            PlaidApi=DEFAULT
        ) as mocks:
            mocks['Configuration'].return_value = mock_config
            mocks['ApiClient'].return_value = mock_client
            mocks['PlaidApi'].return_value = mock_api
            res = plaid_client()
        assert mocks['Configuration'].mock_calls == [
            call(
                host='sandEnv',
                api_key={
                    'clientId': 'plaidCID',
                    'secret': 'plaidSecret'
                }
            )
        ]
        assert mocks['ApiClient'].mock_calls == [
            call(mock_config)
        ]
        assert mocks['PlaidApi'].mock_calls == [
            call(mock_client)
        ]
        assert res == mock_api


class TestDtNow(object):

    @freeze_time('2016-05-13 11:21:32', tz_offset=0)
    @patch('biweeklybudget.utils.settings.BIWEEKLYBUDGET_TEST_TIMESTAMP', None)
    def test_dtnow(self):
        assert dtnow() == datetime(
            2016, 5, 13, 11, 21, 32, tzinfo=utc
        )

    def test_dtnow_test(self):
        assert dtnow() == datetime(
            2017, 7, 28, 6, 24, 44, tzinfo=utc
        )


#: Values that :py:func:`~biweeklybudget.utils.parse_currency` must accept for
#: the ``en_US``/``USD`` settings used by the test settings module, as
#: (input, expected Decimal) pairs.
CURRENCY_ACCEPT_CASES = [
    # bare integers - github issue #323
    ('123', Decimal('123')),
    ('0', Decimal('0')),
    ('1234', Decimal('1234')),
    # plain decimals
    ('123.45', Decimal('123.45')),
    ('0.01', Decimal('0.01')),
    # comma thousands separators - github issue #323
    ('1,234.56', Decimal('1234.56')),
    ('1,000', Decimal('1000')),
    ('1,234,567.89', Decimal('1234567.89')),
    # space thousands separators, including unicode spaces
    ('1 234.56', Decimal('1234.56')),
    ('1\u00a0234.56', Decimal('1234.56')),
    ('1\u202f234.56', Decimal('1234.56')),
    # currency symbol and ISO code
    ('$1,234.56', Decimal('1234.56')),
    ('$ 1,234.56', Decimal('1234.56')),
    ('1,234.56 $', Decimal('1234.56')),
    ('USD 1,234.56', Decimal('1234.56')),
    # explicit signs
    ('-1,234.56', Decimal('-1234.56')),
    ('-$1,234.56', Decimal('-1234.56')),
    ('+123', Decimal('123')),
    ('-123', Decimal('-123')),
    # parentheses as negative
    ('(1,234.56)', Decimal('-1234.56')),
    ('($1,234.56)', Decimal('-1234.56')),
    # surrounding whitespace
    ('  1234.56  ', Decimal('1234.56')),
    ('\t1,234.56\u00a0', Decimal('1234.56')),
    # more than 2 decimal places is preserved, not rounded
    ('1.23456', Decimal('1.23456')),
    # negative zero is zero, so "cannot be zero" checks still fire
    ('-0.00', Decimal('0')),
]

#: Values that :py:func:`~biweeklybudget.utils.parse_currency` must reject.
CURRENCY_REJECT_CASES = [
    # not numbers at all
    'abc',
    'twelve',
    '',
    '   ',
    '$',
    '$ ',
    # invalid grouping; a lenient parser reads these as 1000/1234/123/1234.56
    # and silently corrupts the amount, which is the whole point of rejecting
    '10,00',
    '1,234,',
    ',123',
    '1,23,4.56',
    '1,2345.67',
    '12,34.5',
    # space-separated digit runs that are not valid groups
    '1 2 3',
    # multiple decimal separators
    '1.2.3',
    '1..2',
    # misplaced signs
    '5-',
    '-(5)',
    '1-2',
    # things Decimal() would otherwise happily accept
    '1e5',
    '1E5',
    'nan',
    'NaN',
    'inf',
    '-inf',
    'Infinity',
    # non-ascii digits
    '\uff11\uff12\uff13',
    # non-string input
    None,
    123,
    12.3,
    Decimal('1.23'),
    ['1.23'],
]


class TestParseCurrency(object):
    """
    Tests for :py:func:`biweeklybudget.utils.parse_currency`; see GitHub issue
    #323.
    """

    @pytest.mark.parametrize('value,expected', CURRENCY_ACCEPT_CASES)
    def test_accepted(self, value, expected):
        assert parse_currency(value) == expected

    @pytest.mark.parametrize('value,expected', CURRENCY_ACCEPT_CASES)
    def test_accepted_returns_decimal(self, value, expected):
        # never a float; cents must survive exactly
        assert isinstance(parse_currency(value), Decimal)

    @pytest.mark.parametrize('value', CURRENCY_REJECT_CASES)
    def test_rejected(self, value):
        with pytest.raises(CurrencyParseError):
            parse_currency(value)

    def test_currency_parse_error_is_value_error(self):
        # callers that already catch ValueError keep working
        assert issubclass(CurrencyParseError, ValueError)

    def test_bare_integer_stays_integral(self):
        # github issue #323: "123" must not become "123.0"
        assert str(parse_currency('123')) == '123'

    def test_precision_is_preserved(self):
        assert str(parse_currency('1.23456')) == '1.23456'
        assert str(parse_currency('1.50')) == '1.50'

    def test_canonical_form_round_trips(self):
        for value, _ in CURRENCY_ACCEPT_CASES:
            parsed = parse_currency(value)
            assert parse_currency(str(parsed)) == parsed

    def test_no_float_rounding(self):
        # 0.1 + 0.2 == 0.30000000000000004 in binary floating point
        assert parse_currency('0.1') + parse_currency('0.2') == Decimal('0.3')

    def test_error_message_includes_value(self):
        with pytest.raises(CurrencyParseError) as excinfo:
            parse_currency('1,23,4.56')
        assert '1,23,4.56' in str(excinfo.value)


class TestParseCurrencyLocale(object):
    """
    Normalization must be driven by settings, not hard-coded, so that adding a
    locale is a configuration change rather than a code change.
    """

    @patch('biweeklybudget.utils.settings.LOCALE_NAME', 'de_DE')
    @patch('biweeklybudget.utils.settings.CURRENCY_CODE', 'EUR')
    def test_de_de_accepts_german_formatting(self):
        assert parse_currency('1.234,56') == Decimal('1234.56')
        assert parse_currency('1 234,56') == Decimal('1234.56')
        assert parse_currency('1234,56') == Decimal('1234.56')
        assert parse_currency('1234') == Decimal('1234')

    @patch('biweeklybudget.utils.settings.LOCALE_NAME', 'de_DE')
    @patch('biweeklybudget.utils.settings.CURRENCY_CODE', 'EUR')
    def test_de_de_rejects_us_formatting(self):
        with pytest.raises(CurrencyParseError):
            parse_currency('1,234.56')

    @patch('biweeklybudget.utils.settings.LOCALE_NAME', 'de_DE')
    @patch('biweeklybudget.utils.settings.CURRENCY_CODE', 'EUR')
    def test_de_de_currency_symbol(self):
        assert parse_currency('\u20ac1.234,56') == Decimal('1234.56')
        assert parse_currency('1.234,56 \u20ac') == Decimal('1234.56')
