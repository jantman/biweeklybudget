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

from biweeklybudget.utils import dtnow, plaid_client
from pytz import utc
from datetime import datetime
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
