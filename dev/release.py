#!/usr/bin/env python
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
import sys
import logging
import json
import subprocess
import requests
from shutil import rmtree
from time import sleep
from copy import deepcopy
from github_releaser import GithubReleaser
from release_utils import (
    StepRegistry, prompt_user, BaseStep, fail, is_git_dirty, TravisChecker
)
from biweeklybudget.version import VERSION

if sys.version_info[0:2] != (3, 6):
    raise SystemExit('ERROR: release.py can only run under py 3.6')

FORMAT = "[%(levelname)s %(filename)s:%(lineno)s - %(name)s.%(funcName)s() ] " \
         "%(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger()

for n in ['urllib3', 'urllib', 'requests', 'git', 'github3']:
    l = logging.getLogger(n)
    l.setLevel(logging.ERROR)
    l.propagate = True


steps = StepRegistry()


@steps.register(1)
class InitialChecks(BaseStep):

    def run(self):
        if not prompt_user('Have you opened an issue for the release?'):
            fail('You must open an issue for the release.')
        b = self._current_branch
        if b == 'master':
            fail('release.py cannot be run from master for a new release')
        if not prompt_user(
            'Is the current branch (%s) the release branch?' % b
        ):
            fail('You must run this script from the release branch.')
        if not prompt_user(
            'Have you verified whether or not DB migrations are needed, and '
            'if they are, ensure they’ve been created, tested and verified?'
        ):
            fail('You must verify migrations first.')
        if not prompt_user(
            'Have you confirmed that there are CHANGES.rst entries for all '
            'major changes?'
        ):
            fail('Please check CHANGES.rst before releasing code.')
        if not prompt_user(
            'Is the current version (%s) the version being released?' % VERSION
        ):
            fail(
                'Please increment the version in biweeklybudget/version.py '
                'before running the release script.'
            )
        if not prompt_user(
            'Is the test coverage at least as high as the last release, and '
            'are there acceptance tests for all non-trivial changes?'
        ):
            fail('Test coverage!!!')


@steps.register(2)
class RegenerateScreenshots(BaseStep):

    def run(self):
        self._run_tox_env('screenshots')
        self._ensure_committed()


@steps.register(3)
class RegenerateJsdoc(BaseStep):

    def run(self):
        self._run_tox_env('jsdoc')
        self._ensure_committed()


@steps.register(4)
class RegenerateDocs(BaseStep):

    def run(self):
        self._run_tox_env('docs')
        self._ensure_committed()


@steps.register(5)
class BuildDocker(BaseStep):

    def run(self):
        self._run_tox_env('docker')
        self._ensure_committed()


@steps.register(6)
class EnsurePushed(BaseStep):

    def run(self):
        self._ensure_pushed()


@steps.register(7)
class GistReleaseNotes(BaseStep):

    def run(self):
        result = None
        while result is not True:
            md = self._gh._get_markdown()
            print("Changelog Markdown:\n%s\n" % md)
            result = prompt_user('Does this markdown look right?')
            if result is not True:
                input('Revise Changelog and then press any key.')
                continue
            url = self._gist(md)
            logger.info('Gist URL: <%s>', url)
            result = prompt_user('Does the gist at <%s> look right?' % url)


@steps.register(8)
class ConfirmTravisAndCoverage(BaseStep):

    def run(self):
        commit = self._current_commit
        logger.info('Polling for finished TravisCI build of %s', commit)
        build = self._travis.poll_for_build(commit)
        while build is None or build.finished is False:
            sleep(10)
            build = self._travis.poll_for_build(commit)
        logger.info('Travis build finished')
        if not build.passed:
            fail('Travis build %s (%s) did not pass. Please fix build failures '
                 'and then re-run.' % (build.number, build.id))
        logger.info('OK, Travis build passed.')
        logger.info(
            'Build URL: <https://travis-ci.org/jantman/biweeklybudget/'
            'builds/%s>', build.id
        )
        if not prompt_user(
            'Is the test coverage at least as high as the last release, and '
            'are there acceptance tests for all non-trivial changes?'
        ):
            fail('Test coverage!!!')


@steps.register(9)
class ConfirmReadmeRenders(BaseStep):

    def run(self):
        logger.info(
            'Readme URL: <https://github.com/jantman/biweeklybudget/blob/%s/'
            'README.rst>', self._current_branch
        )
        if not prompt_user('Does the Readme at the above URL render properly?'):
            fail('Please fix the README and then re-run.')


@steps.register(10)
class TestPyPI(BaseStep):

    def run(self):
        projdir = self.projdir
        logger.info('Removing dist directory...')
        rmtree(os.path.join(projdir, 'dist'))
        env = deepcopy(os.environ)
        env['PATH'] = self._fixed_path(projdir)
        cmd = ['python', 'setup.py', 'sdist', 'bdist_wheel']
        logger.info(
            'Running: %s (cwd=%s)', ' '.join(cmd), projdir
        )
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=projdir, timeout=1800, env=env
        )
        if res.returncode != 0:
            logger.error(
                'ERROR: command exited %d:\n%s',
                res.returncode, res.stdout.decode()
            )
            fail('%s failed.' % ' '.join(cmd))
        cmd = ['twine', 'upload', '-r', 'test', 'dist/*']
        logger.info(
            'Running: %s (cwd=%s)', ' '.join(cmd), projdir
        )
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=projdir, timeout=1800, env=env, shell=True
        )
        if res.returncode != 0:
            logger.error(
                'ERROR: command exited %d:\n%s',
                res.returncode, res.stdout.decode()
            )
            fail('%s failed.' % ' '.join(cmd))
        logger.info('Package generated and uploaded to Test PyPI.')
        res = self.pypi_has_version(test=True)
        while not res:
            logger.info('Waiting for new version to show up on TestPyPI...')
            sleep(10)
            res = self.pypi_has_version(test=True)
        logger.info(
            'Package is live on Test PyPI. URL: <https://testpypi.python.org/'
            'pypi/biweeklybudget>'
        )
        if not prompt_user('Does the Readme at the above URL render properly?'):
            fail('Please fix the README and then re-run.')

    def pypi_has_version(self, test=False):
        host = 'pypi'
        if test:
            host = 'testpypi'
        url = 'https://%s.python.org/pypi/biweeklybudget/json' % host
        try:
            r = requests.get(url)
            if r.json()['info']['version'] == VERSION:
                return True
            return False
        except Exception:
            logger.warning('Exception getting JSON from %s', url, exc_info=True)
        return False


# 14. Create PR; wait for build; merge
# 15. Tag release (signed) and push
# 16. upload
# 17. GitHub release
# 18. Build and push Docker
# 19. make sure GH issues closed; readthedocs build

class BwbReleaseAutomator(object):

    def __init__(self, savepath):
        self._savepath = savepath
        logger.info('Release step/position save path: %s', savepath)
        self.gh = GithubReleaser()
        self.travis = TravisChecker()

    def run(self):
        if self.gh.get_tag(VERSION) != (None, None):
            logger.error(
                'Version %s is already released on GitHub. Either you need to '
                'increment the version number in biweeklybudget/version.py or '
                'the release is complete.', VERSION
            )
            raise SystemExit(1)
        is_git_dirty(raise_on_dirty=True)
        last_step = self._last_step
        for stepnum in steps.step_numbers:
            if stepnum <= last_step:
                logger.debug('Skipping step %d - already completed', stepnum)
                continue
            cls = steps.step(stepnum)
            logger.info('Running step %d (%s)', stepnum, cls.__name__)
            cls(self.gh, self.travis).run()
            self._record_successful_step(stepnum)
        logger.info('DONE!')
        logger.debug('Removing: %s', self._savepath)
        os.unlink(self._savepath)

    @property
    def _last_step(self):
        """
        If ``self._savepath`` doesn't exist, can't be read as JSON, or doesn't
        match ``VERSION``, return 0. Otherwise, return the step which that file
        lists as the last-run step for this release.

        :return: last-run step from the release or 0
        :rtype: int
        """
        if not os.path.exists(self._savepath):
            return 0
        try:
            with open(self._savepath, 'r') as fh:
                j = json.loads(fh.read())
        except Exception:
            logger.warning(
                'Could not read or JSON-deserialize %s', self._savepath
            )
            return 0
        if j.get('version', '') != VERSION:
            return 0
        return j.get('last_successful_step', 0)

    def _record_successful_step(self, stepnum):
        with open(self._savepath, 'w') as fh:
            fh.write(json.dumps({
                'version': VERSION,
                'last_successful_step': stepnum
            }))
        logger.debug('Updated last_successful_step to %d', stepnum)


if __name__ == "__main__":
    BwbReleaseAutomator(
        os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..',
                '.release_position.json'
            )
        )
    ).run()
    raise NotImplementedError('Uncomment is_git_dirty call in run()')
