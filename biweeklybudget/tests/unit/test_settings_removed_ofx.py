"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2026 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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
to me via email, and that you also submit a patch for them so that I can
help others. If you are using this software in a way that you find
useful, please consider informing me of it via email.
################################################################################
AUTHORS:
Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>
################################################################################
"""

import json
import os
import subprocess
import sys

from biweeklybudget import settings

#: Settings that only configured OFX downloading and Vault, removed in GitHub
#: issue #265.
REMOVED = ['VAULT_ADDR', 'TOKEN_PATH', 'STATEMENTS_SAVE_PATH']


def import_settings(extra_env, pythonpath=None):
    """
    Import :py:mod:`biweeklybudget.settings` in a fresh interpreter with extra
    environment variables, and print which of the removed settings it defines.
    A subprocess is used because settings are processed at import time.

    :param extra_env: environment variables to add
    :type extra_env: dict
    :param pythonpath: directory to prepend to ``PYTHONPATH``, if any
    :type pythonpath: str
    :return: the completed process
    :rtype: subprocess.CompletedProcess
    """
    env = dict(os.environ)
    env.update(extra_env)
    # importing settings requires DB_CONNSTRING; it does not connect.
    env.setdefault(
        'DB_CONNSTRING', 'mysql+pymysql://user:pass@127.0.0.1/unused'
    )
    if pythonpath is not None:
        env['PYTHONPATH'] = os.pathsep.join(
            [pythonpath] + [
                p for p in [env.get('PYTHONPATH')] if p
            ]
        )
    return subprocess.run(
        [
            sys.executable, '-c',
            'import json; from biweeklybudget import settings; '
            'print(json.dumps({n: getattr(settings, n, None) for n in %r}))'
            % (REMOVED,)
        ],
        env=env, capture_output=True, text=True, timeout=120
    )


class TestRemovedOfxSettings:

    def test_not_defined_by_default(self):
        for name in REMOVED:
            assert not hasattr(settings, name), name

    def test_environment_variables_ignored(self):
        res = import_settings({
            'VAULT_ADDR': 'http://127.0.0.1:8200',
            'TOKEN_PATH': '/tmp/vault_token.txt',
            'STATEMENTS_SAVE_PATH': '/tmp/statements',
        })
        assert res.returncode == 0, res.stderr
        assert json.loads(res.stdout.strip().splitlines()[-1]) == {
            n: None for n in REMOVED
        }

    def test_settings_module_still_defining_them_starts(self, tmp_path):
        (tmp_path / 'old_ofx_settings.py').write_text(
            'from biweeklybudget.tests.fixtures.test_settings import *  '
            '# noqa\n'
            "VAULT_ADDR = 'http://127.0.0.1:8200'\n"
            "TOKEN_PATH = 'vault_token.txt'\n"
            "STATEMENTS_SAVE_PATH = '/tmp/ofx'\n"
        )
        res = import_settings(
            {'SETTINGS_MODULE': 'old_ofx_settings'},
            pythonpath=str(tmp_path)
        )
        assert res.returncode == 0, res.stderr
