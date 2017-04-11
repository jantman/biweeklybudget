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

import sys
import pytest
import os
import importlib
import types
from inspect import isclass


def find_tests():
    testdir = os.path.realpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..'
    ))
    res = []
    for root, dirs, files in os.walk(testdir):
        for name in files:
            p = os.path.join(root, name)
            if not p.endswith('.py') or not name.startswith('test'):
                continue
            res.extend(find_mod_disabled_tests(p, testdir))
    return res


def find_mod_disabled_tests(path, testdir):
    tests = []
    mname = 'biweeklybudget.tests.'
    mname += path.replace(testdir + '/', '').replace(
        '.py', '').replace('/', '.')
    spec = importlib.util.spec_from_file_location(mname, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for x in dir(mod):
        if 'test' not in x.lower():
            continue
        a = getattr(mod, x)
        if isinstance(a, types.FunctionType) and 'donot' in x.lower():
            tests.append('%s.%s' % (mname, x))
        if isclass(a):
            if 'donot' in x.lower():
                tests.append('%s.%s' % (mname, x))
            for methname in dir(a):
                if 'test' not in methname.lower():
                    continue
                meth = getattr(a, methname)
                if not isinstance(meth, types.FunctionType):
                    continue
                if 'donot' in methname.lower():
                    tests.append('%s.%s.%s' % (mname, x, methname))
    return tests


@pytest.mark.skipif(sys.version_info[0:2] != (3, 6), reason='py36 only')
def test_disabled_tests():
    """
    Fail if any tests are disabled via my usual hackish "DONOT" prefix.
    """
    assert find_tests() == []
