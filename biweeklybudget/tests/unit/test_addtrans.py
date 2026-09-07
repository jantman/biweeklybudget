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

import json
import sys

import pytest
import requests

from biweeklybudget.addtrans import (
    DEFAULT_URL, URL_ENV_VAR, base_url_for, build_payload, main, parse_args,
    post_transaction
)

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call
else:
    from unittest.mock import Mock, patch, call

pbm = 'biweeklybudget.addtrans'

#: the minimum arguments that parse successfully
MINIMAL = ['BankOne', '123.45', 'a description', '-b', 'Groceries']


def _response(status_code=200, json_body=None, text=''):
    res = Mock(spec_set=requests.Response)
    type(res).status_code = status_code
    type(res).text = text if text else json.dumps(json_body)
    if json_body is None:
        res.json.side_effect = ValueError('no json')
    else:
        res.json.return_value = json_body
    return res


class TestBaseUrlFor(object):

    def test_argument_wins(self):
        with patch.dict('os.environ', {URL_ENV_VAR: 'http://from-env:1/'}):
            assert base_url_for('http://from-arg:2/') == 'http://from-arg:2'

    def test_env_var_used_when_no_argument(self):
        with patch.dict('os.environ', {URL_ENV_VAR: 'http://from-env:1'}):
            assert base_url_for(None) == 'http://from-env:1'

    def test_default_when_neither(self):
        with patch.dict('os.environ', {}, clear=True):
            assert base_url_for(None) == DEFAULT_URL

    def test_empty_env_var_falls_through_to_default(self):
        with patch.dict('os.environ', {URL_ENV_VAR: '   '}):
            assert base_url_for(None) == DEFAULT_URL

    def test_trailing_slash_is_stripped(self):
        """So that the path is appended exactly once."""
        with patch.dict('os.environ', {}, clear=True):
            assert base_url_for('http://foo:8080/') == 'http://foo:8080'


class TestParseArgs(object):

    def test_positionals(self):
        with patch.dict('os.environ', {}, clear=True):
            args = parse_args(MINIMAL)
        assert args.account == 'BankOne'
        assert args.amount == '123.45'
        assert args.description == 'a description'
        assert args.base_url == DEFAULT_URL

    def test_single_budget_gets_the_whole_amount(self):
        with patch.dict('os.environ', {}, clear=True):
            args = parse_args(MINIMAL)
        assert args.budgets == {'Groceries': '123.45'}

    def test_single_budget_with_explicit_amount(self):
        with patch.dict('os.environ', {}, clear=True):
            args = parse_args(
                ['BankOne', '123.45', 'desc', '-b', 'Groceries=100.00']
            )
        assert args.budgets == {'Groceries': '100.00'}

    def test_multiple_budgets(self):
        with patch.dict('os.environ', {}, clear=True):
            args = parse_args([
                'BankOne', '30.00', 'desc',
                '-b', 'Food=10.00', '-b', '7=20.00'
            ])
        assert args.budgets == {'Food': '10.00', '7': '20.00'}

    def test_budget_name_containing_spaces(self):
        with patch.dict('os.environ', {}, clear=True):
            args = parse_args(
                ['BankOne', '5.00', 'desc', '-b', 'Periodic3 Inactive']
            )
        assert args.budgets == {'Periodic3 Inactive': '5.00'}

    def test_default_date_is_today(self):
        with patch.dict('os.environ', {}, clear=True):
            with patch('%s.date' % pbm) as mock_date:
                mock_date.today.return_value.strftime.return_value = \
                    '2026-09-07'
                args = parse_args(MINIMAL)
        assert args.date == '2026-09-07'
        assert mock_date.today.return_value.strftime.mock_calls == [
            call('%Y-%m-%d')
        ]

    def test_explicit_date(self):
        with patch.dict('os.environ', {}, clear=True):
            args = parse_args(MINIMAL + ['-d', '2020-01-02'])
        assert args.date == '2020-01-02'

    def test_multiple_budgets_without_amounts_is_a_usage_error(self):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(SystemExit) as excinfo:
                parse_args([
                    'BankOne', '30.00', 'desc', '-b', 'Food', '-b', 'Fuel'
                ])
        assert excinfo.value.code == 2

    def test_one_of_several_budgets_without_an_amount_is_a_usage_error(self):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(SystemExit) as excinfo:
                parse_args([
                    'BankOne', '30.00', 'desc',
                    '-b', 'Food=10.00', '-b', 'Fuel'
                ])
        assert excinfo.value.code == 2

    def test_duplicate_budget_is_a_usage_error(self):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(SystemExit) as excinfo:
                parse_args([
                    'BankOne', '30.00', 'desc',
                    '-b', 'Food=10.00', '-b', 'Food=20.00'
                ])
        assert excinfo.value.code == 2

    def test_empty_budget_name_is_a_usage_error(self):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(SystemExit) as excinfo:
                parse_args(['BankOne', '30.00', 'desc', '-b', '=10.00'])
        assert excinfo.value.code == 2

    def test_no_budget_is_a_usage_error(self):
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(SystemExit) as excinfo:
                parse_args(['BankOne', '30.00', 'desc'])
        assert excinfo.value.code == 2


class TestBuildPayload(object):

    def _payload(self, argv):
        with patch.dict('os.environ', {}, clear=True):
            return build_payload(parse_args(argv))

    def test_minimal(self):
        assert self._payload(MINIMAL + ['-d', '2026-09-07']) == {
            'date': '2026-09-07',
            'amount': '123.45',
            'description': 'a description',
            'notes': '',
            'account': 'BankOne',
            'budgets': {'Groceries': '123.45'}
        }

    def test_notes_always_present_even_when_empty(self):
        """The endpoint used to 500 without it, and an explicit empty string
        costs nothing."""
        assert self._payload(MINIMAL)['notes'] == ''

    def test_optional_fields_omitted_when_not_given(self):
        payload = self._payload(MINIMAL)
        assert 'sales_tax' not in payload
        assert 'credit_payment_acct' not in payload
        assert 'no_budget_impact' not in payload

    def test_all_optional_fields(self):
        payload = self._payload(MINIMAL + [
            '-n', 'some notes', '-t', '1.23', '-p', 'CreditOne',
            '--no-budget-impact'
        ])
        assert payload['notes'] == 'some notes'
        assert payload['sales_tax'] == '1.23'
        assert payload['credit_payment_acct'] == 'CreditOne'
        assert payload['no_budget_impact'] is True

    def test_amount_is_passed_through_verbatim(self):
        """No client-side currency parsing; the server owns that definition."""
        payload = self._payload(
            ['BankOne', '$1,234.56', 'desc', '-b', 'Food']
        )
        assert payload['amount'] == '$1,234.56'
        assert payload['budgets'] == {'Food': '$1,234.56'}


class TestPostTransaction(object):

    def test_success(self, capsys):
        res = _response(json_body={
            'success': True,
            'success_message': 'Successfully saved Transaction 12  in '
                               'database.',
            'trans_id': 12
        })
        with patch('%s.requests.post' % pbm) as mock_post:
            mock_post.return_value = res
            rc = post_transaction('http://foo:8080', {'a': 'b'})
        assert rc == 0
        assert mock_post.mock_calls[0] == call(
            'http://foo:8080/forms/transaction', json={'a': 'b'}, timeout=30
        )
        out = capsys.readouterr().out
        assert 'Created Transaction 12' in out

    def test_validation_errors(self, capsys):
        res = _response(json_body={
            'success': False,
            'errors': {
                'account': ['Account "Nope" is invalid.'],
                'amount': [],
                'budgets': ['Budget "Nah" is invalid.']
            }
        })
        with patch('%s.requests.post' % pbm) as mock_post:
            mock_post.return_value = res
            rc = post_transaction('http://foo:8080', {})
        assert rc == 1
        err = capsys.readouterr().err
        assert 'account: Account "Nope" is invalid.' in err
        assert 'budgets: Budget "Nah" is invalid.' in err
        # fields with no errors must not be printed as blank lines
        assert 'amount:' not in err

    def test_error_message(self, capsys):
        res = _response(json_body={
            'success': False, 'error_message': 'it went wrong'
        })
        with patch('%s.requests.post' % pbm) as mock_post:
            mock_post.return_value = res
            rc = post_transaction('http://foo:8080', {})
        assert rc == 1
        assert 'it went wrong' in capsys.readouterr().err

    def test_connection_error(self, capsys):
        with patch('%s.requests.post' % pbm) as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError(
                'refused'
            )
            rc = post_transaction('http://foo:8080', {})
        assert rc == 1
        err = capsys.readouterr().err
        assert 'could not reach biweeklybudget at ' \
               'http://foo:8080/forms/transaction' in err
        assert 'refused' in err

    def test_timeout(self, capsys):
        with patch('%s.requests.post' % pbm) as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout('too slow')
            rc = post_transaction('http://foo:8080', {})
        assert rc == 1
        assert 'could not reach biweeklybudget' in capsys.readouterr().err

    def test_non_200_status(self, capsys):
        res = _response(status_code=404, text='Not Found')
        with patch('%s.requests.post' % pbm) as mock_post:
            mock_post.return_value = res
            rc = post_transaction('http://foo:8080', {})
        assert rc == 1
        err = capsys.readouterr().err
        assert 'returned HTTP 404' in err
        assert 'Not Found' in err

    def test_non_json_body(self, capsys):
        res = _response(status_code=200, text='<html>whoops</html>')
        with patch('%s.requests.post' % pbm) as mock_post:
            mock_post.return_value = res
            rc = post_transaction('http://foo:8080', {})
        assert rc == 1
        assert 'non-JSON response' in capsys.readouterr().err


class TestMain(object):

    def test_dry_run_posts_nothing(self, capsys):
        with patch.dict('os.environ', {}, clear=True):
            with patch('%s.requests.post' % pbm) as mock_post:
                with pytest.raises(SystemExit) as excinfo:
                    with patch.object(
                        sys, 'argv',
                        ['addtrans'] + MINIMAL + ['-d', '2026-09-07',
                                                  '--dry-run']
                    ):
                        main()
        assert excinfo.value.code == 0
        assert mock_post.mock_calls == []
        assert json.loads(capsys.readouterr().out) == {
            'date': '2026-09-07',
            'amount': '123.45',
            'description': 'a description',
            'notes': '',
            'account': 'BankOne',
            'budgets': {'Groceries': '123.45'}
        }

    def test_exit_status_comes_from_post(self):
        with patch.dict('os.environ', {}, clear=True):
            with patch('%s.post_transaction' % pbm) as mock_post:
                mock_post.return_value = 1
                with pytest.raises(SystemExit) as excinfo:
                    with patch.object(sys, 'argv', ['addtrans'] + MINIMAL):
                        main()
        assert excinfo.value.code == 1

    def test_url_from_environment(self):
        with patch.dict('os.environ', {URL_ENV_VAR: 'http://env:9'}):
            with patch('%s.post_transaction' % pbm) as mock_post:
                mock_post.return_value = 0
                with pytest.raises(SystemExit):
                    with patch.object(sys, 'argv', ['addtrans'] + MINIMAL):
                        main()
        assert mock_post.mock_calls[0][1][0] == 'http://env:9'

    def test_verbose_sets_log_level(self):
        with patch.dict('os.environ', {}, clear=True):
            with patch('%s.post_transaction' % pbm) as mock_post:
                with patch('%s.set_log_info' % pbm) as mock_info:
                    with patch('%s.set_log_debug' % pbm) as mock_debug:
                        mock_post.return_value = 0
                        with pytest.raises(SystemExit):
                            with patch.object(
                                sys, 'argv', ['addtrans'] + MINIMAL + ['-vv']
                            ):
                                main()
        assert len(mock_debug.mock_calls) == 1
        assert mock_info.mock_calls == []
