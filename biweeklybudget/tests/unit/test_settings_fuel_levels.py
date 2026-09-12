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
import os
import subprocess
import sys

import pytest

from biweeklybudget import settings
from biweeklybudget.settings import parse_fuel_levels, validate_fuel_levels

#: The fuel level options that were hard-coded in fuel.js before GitHub
#: issue #208; the default must stay exactly this.
TENTHS = [
    ('0/10', 0), ('1/10', 10), ('2/10', 20), ('3/10', 30), ('4/10', 40),
    ('5/10', 50), ('6/10', 60), ('7/10', 70), ('8/10', 80), ('9/10', 90),
    ('10/10', 100)
]


def import_settings_with_env(fuel_levels):
    """
    Import :py:mod:`biweeklybudget.settings` in a fresh interpreter with the
    ``FUEL_LEVELS`` environment variable set, and print the resulting setting
    as JSON. A subprocess is used because the setting is processed at import
    time, and reloading the shared module in this process would leave it
    half-initialised for every other test if the import failed.

    :param fuel_levels: value for the FUEL_LEVELS environment variable
    :type fuel_levels: str
    :return: the completed process
    :rtype: subprocess.CompletedProcess
    """
    env = dict(os.environ)
    env['FUEL_LEVELS'] = fuel_levels
    # importing settings requires DB_CONNSTRING; it does not connect.
    env.setdefault(
        'DB_CONNSTRING', 'mysql+pymysql://user:pass@127.0.0.1/unused'
    )
    return subprocess.run(
        [
            sys.executable, '-c',
            'import json; from biweeklybudget import settings; '
            'print(json.dumps(settings.FUEL_LEVELS))'
        ],
        env=env, capture_output=True, text=True, timeout=120
    )


class TestFuelLevelsDefault:

    def test_default(self):
        # the test settings module does not set FUEL_LEVELS
        assert settings.FUEL_LEVELS == TENTHS


class TestParseFuelLevels:

    def test_quarters(self):
        assert parse_fuel_levels('E:0,1/4:25,1/2:50,3/4:75,F:100') == [
            ('E', 0), ('1/4', 25), ('1/2', 50), ('3/4', 75), ('F', 100)
        ]

    def test_whitespace_is_stripped(self):
        assert parse_fuel_levels(' E : 0 , F:100 ') == [('E', 0), ('F', 100)]

    def test_label_may_contain_colon(self):
        assert parse_fuel_levels('a:b:50,F:100') == [('a:b', 50), ('F', 100)]

    def test_order_is_kept(self):
        assert parse_fuel_levels('F:100,E:0') == [('F', 100), ('E', 0)]

    @pytest.mark.parametrize('value', [
        'E:x,F:100',
        'E:-5,F:100',
        'E:1.5,F:100',
        'E:,F:100',
        'E0,F:100',
        'E:0,F:100,',
        '',
    ])
    def test_invalid(self, value):
        with pytest.raises(ValueError):
            parse_fuel_levels(value)


class TestValidateFuelLevels:

    def test_tuples(self):
        assert validate_fuel_levels(TENTHS) == TENTHS

    def test_lists_are_normalised_to_tuples(self):
        assert validate_fuel_levels([['E', 0], ['F', 100]]) == [
            ('E', 0), ('F', 100)
        ]

    def test_tuple_of_levels(self):
        assert validate_fuel_levels((('E', 0), ('F', 100))) == [
            ('E', 0), ('F', 100)
        ]

    def test_labels_are_stripped(self):
        assert validate_fuel_levels([(' E ', 0), ('F', 100)]) == [
            ('E', 0), ('F', 100)
        ]

    def test_out_of_order_is_kept(self):
        levels = [('8', 100), ('4', 50), ('0', 0)]
        assert validate_fuel_levels(levels) == levels

    def test_boundaries_accepted(self):
        assert validate_fuel_levels([('E', 0), ('F', 100)]) == [
            ('E', 0), ('F', 100)
        ]

    def test_returns_new_list(self):
        levels = [('E', 0), ('F', 100)]
        assert validate_fuel_levels(levels) is not levels

    @pytest.mark.parametrize('levels', [
        None,
        'E:0,F:100',
        {'E': 0, 'F': 100},
        [],
        [('F', 100)],
        [('E', 0), ('F',)],
        [('E', 0), ('F', 100, 1)],
        [('E', 0), 'F'],
        [('', 0), ('F', 100)],
        [('   ', 0), ('F', 100)],
        [(None, 0), ('F', 100)],
        [(1, 0), ('F', 100)],
        [('E', 0.5), ('F', 100)],
        [('E', '50'), ('F', 100)],
        [('E', True), ('F', 100)],
        [('E', None), ('F', 100)],
        [('E', -1), ('F', 100)],
        [('E', 0), ('F', 101)],
        [('E', 0), ('E', 50), ('F', 100)],
        [('E', 0), (' E', 50), ('F', 100)],
        [('E', 0), ('1/2', 50), ('half', 50), ('F', 100)],
    ])
    def test_invalid(self, levels):
        with pytest.raises(ValueError):
            validate_fuel_levels(levels)

    def test_error_names_the_problem(self):
        with pytest.raises(ValueError) as exc:
            validate_fuel_levels([('E', 0), ('F', 150)])
        assert '150' in str(exc.value)


class TestFuelLevelsEnvVar:

    def test_env_var_is_used(self):
        res = import_settings_with_env('E:0, 1/2:50 ,F:100')
        assert res.returncode == 0, res.stderr
        assert json.loads(res.stdout.strip().splitlines()[-1]) == [
            ['E', 0], ['1/2', 50], ['F', 100]
        ]

    @pytest.mark.parametrize('value', [
        'E:0,F:150',
        'F:100',
        'E:0,E:50,F:100',
        'E:x,F:100',
        'E:0,1/2:50,half:50,F:100',
    ])
    def test_invalid_env_var_exits(self, value):
        res = import_settings_with_env(value)
        assert res.returncode != 0
        assert 'ERROR: FUEL_LEVELS setting is invalid' in res.stderr
