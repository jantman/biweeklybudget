"""
Development script to convert current version release notes to markdown and
either upload to Github as a gist, or create a Github release for the version.

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

import os
import logging
import subprocess
from copy import deepcopy

logger = logging.getLogger(__name__)


def prompt_user(s):
    res = None
    while res not in ['y', 'Y', 'n', 'N']:
        try:
            res = input(s + '[y|n] ')
        except EOFError:
            res = ''
    if res.strip() in ['y', 'Y']:
        return True
    return False


def fail(s):
    logger.critical(s)
    raise SystemExit(1)


def is_git_dirty(raise_on_dirty=False):
    dirty = False
    if subprocess.call(
            ['git', 'diff', '--no-ext-diff', '--quiet', '--exit-code']
    ) != 0:
        dirty = True
    if subprocess.call(
            ['git', 'diff-index', '--cached', '--quiet', 'HEAD', '--']
    ) != 0:
        dirty = True
    if dirty and raise_on_dirty:
        raise RuntimeError(
            'ERROR: Git clone is dirty. Commit before continuing.'
        )
    return dirty


class StepRegistry(object):

    def __init__(self):
        self._steps = {}

    def register(self, step_num, klass=None):
        if klass:
            raise RuntimeError(
                'StepRegistry.register can only be used to decorate classes, '
                'not functions.'
            )

        def _register_class(klass):
            if not isinstance(step_num, type(1)):
                raise RuntimeError(
                    'ERROR on register decorator of class %s: step number '
                    '"%s" is not an integer.' % (klass.__name__, step_num)
                )
            if step_num in self._steps:
                raise RuntimeError(
                    'ERROR: Duplicate step number %d on classes %s and %s' % (
                        step_num, self._steps[step_num].__name__, klass.__name__
                    )
                )
            self._steps[step_num] = klass
            return klass

        return _register_class

    @property
    def step_numbers(self):
        return sorted(self._steps.keys())

    def step(self, stepnum):
        return self._steps[stepnum]


class BaseStep(object):

    def __init__(self, github_releaser):
        self._gh = github_releaser

    def run(self):
        raise NotImplementedError('BaseStep run() not overridden')

    @property
    def _current_branch(self):
        res = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])
        return res.stdout.strip()

    def _ensure_committed(self):
        while is_git_dirty():
            input(
                'Git repository has uncommitted changes; please commit '
                'changes and press any key.'
            )

    def _run_tox_env(self, env_name):
        """
        Run the specified tox environment.

        :param env_name: name of the tox environment to run
        :type env_name: str
        :raises: RuntimeError
        """
        projdir = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..'
            )
        )
        env = deepcopy(os.environ)
        env['PATH'] = self._fixed_path(projdir)
        cmd = [os.path.join(projdir, 'bin', 'tox'), '-e', env_name]
        logger.info(
            'Running tox environment %s: args="%s" cwd=%s '
            'timeout=1800', env_name, ' '.join(cmd), projdir
        )
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=projdir, timeout=1800, env=env
        )
        logger.info('tox process exited %d', res.returncode)
        if res.returncode != 0:
            logger.error(
                'ERROR: tox environment %s exitcode %d',
                env_name, res.returncode
            )
            logger.error(
                'tox output:\n%s', res.stdout.decode()
            )
            res.check_returncode()

    def _fixed_path(self, projdir):
        """
        Return the current PATH, fixed to remove the docker tox env.

        :return: sanitized path
        :rtype: str
        """
        res = []
        toxdir = os.path.join(projdir, '.tox')
        for p in os.environ['PATH'].split(':'):
            if not p.startswith(toxdir):
                res.append(p)
        return ':'.join(res)
