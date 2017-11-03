#!/usr/bin/env python
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
import argparse
import logging
import json
import os
import requests
import warnings
from datetime import timedelta
import statistics
from collections import defaultdict

try:
    from travispy import TravisPy
    from travispy.travispy import PUBLIC
except ImportError:
    raise SystemExit(
        "ERROR: TravisPy not installed. Please run 'pip install TravisPy'"
    )

if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    raise SystemExit('Needs py3.4+ for statistics module')

FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()

for lname in ['requests']:
    l = logging.getLogger(lname)
    l.setLevel(logging.WARNING)
    l.propagate = True


class TestTimeAnalyzer(object):

    def __init__(self, build_num=None, toxenv='acceptance36'):
        self._toxenv = toxenv
        token = os.environ.get('GITHUB_TOKEN', None)
        if token is None:
            raise SystemExit(
                'Please export your GitHub PAT as the "GITHUB_TOKEN" env var'
            )
        logger.debug('Connecting to TravisCI API...')
        self._travis = TravisPy.github_auth(token)
        if build_num is None:
            build = self._latest_travis_build()
            logger.info(
                'Found latest finished build: %s (%s)', build.number, build.id
            )
        else:
            build = self._travis.builds(
                slug='jantman/biweeklybudget', number=build_num
            )[0]
            logger.info(
                'Using CLI-specified build: %s (%s)', build.number, build.id
            )
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.job = self._find_travis_job(build, toxenv)
        logger.info('Found acceptance test job: %s', self.job.number)
        self._timing = self._get_timing_from_s3(self.job.number)

    def run(self):
        print('=> Build job %s ran in %s' % (
            self.job.id, timedelta(seconds=self.job.duration)
        ))
        pytest_total = sum([x[2] for x in self._timing['requests']])
        print('=> pytest durations total: %s' % timedelta(seconds=pytest_total))
        if 'class_refresh_db' in self._timing:
            self.crdb_stats(self._timing['class_refresh_db'])
        self.type_stats(self._timing['requests'])
        self.module_stats(self._timing['requests'])
        self.class_stats(self._timing['requests'])

    def crdb_stats(self, data):
        print('=> class_refresh_db fixture total: %s' % timedelta(
            seconds=sum(data)
        ))
        data = sorted(data)
        print('\tCalled %d times' % len(data))
        mu = statistics.mean(data)
        print('\tMean runtime: %s' % mu)
        print('\tMedian runtime: %s' % statistics.median(data))
        print('\tVariance: %s' % statistics.variance(data))

    def type_stats(self, data):
        res = defaultdict(int)
        for item in data:
            res[item[1]] += item[2]
        print('=> pytest durations by setup/call/teardown')
        for k, v in sorted(res.items(), key=lambda x: x[1], reverse=True):
            print('\t%s: %s' % (k, timedelta(seconds=v)))

    def class_stats(self, data):
        res = defaultdict(int)
        for item in data:
            parts = item[0].split('::')
            res['%s::%s' % (parts[0], parts[1])] += item[2]
        print('=> pytest durations by class')
        for k, v in sorted(res.items(), key=lambda x: x[1], reverse=True):
            print('\t%s: %s' % (k, timedelta(seconds=v)))

    def module_stats(self, data):
        res = defaultdict(int)
        for item in data:
            parts = item[0].split('::')
            res[parts[0]] += item[2]
        print('=> pytest durations by module')
        for k, v in sorted(res.items(), key=lambda x: x[1], reverse=True):
            print('\t%s: %s' % (k, timedelta(seconds=v)))

    def _get_timing_from_s3(self, jobnum):
        url = 'http://jantman-personal-public.s3-website-us-east-1.amazonaws' \
              '.com/travisci/jantman/biweeklybudget/%s/results/' \
              'test_durations.json' % jobnum
        logger.debug('Getting test durations from: %s', url)
        r = requests.get(url)
        r.raise_for_status()
        logger.debug('Got timings from S3')
        return json.loads(r.text)

    def _find_travis_job(self, build, toxenv):
        """Given a build object, find the acceptance36 job"""
        for jobid in build.job_ids:
            j = self._travis.job(jobid)
            if 'TOXENV=%s' % toxenv in j.config['env']:
                logger.debug('Found %s job: %s', toxenv, j.number)
                return j
        raise SystemExit(
            'ERROR: could not find %s job for build %s (%s)' % (
                toxenv, build.number, build.id
            )
        )

    def _latest_travis_build(self):
        logger.debug('Finding latest finished build...')
        r = self._travis.repo('jantman/biweeklybudget')
        for bnum in range(int(r.last_build_number), 0, -1):
            b = self._travis.builds(
                slug='jantman/biweeklybudget', number=bnum
            )[0]
            if b.finished and (b.failed or b.passed):
                logger.debug(
                    'Found build to use: %s (%s) state=%s', b.number, b.id,
                    b.state
                )
                return b
        raise SystemExit(
            'ERROR: could not find a finished (passed or failed) build!'
        )


def parse_args(argv):
    """
    parse arguments/options

    this uses the new argparse module instead of optparse
    see: <https://docs.python.org/2/library/argparse.html>
    """
    p = argparse.ArgumentParser(description='Report on test run timings')
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    c = ['acceptance36', 'acceptance27']
    p.add_argument('-j', '--jobtype', dest='jobtype', action='store', type=str,
                   choices=c, default=c[0], help='TOXENV for job')
    p.add_argument('BUILD_NUM', action='store', type=str, nargs='?',
                   default=None,
                   help='TravisCI X.Y build number to analyze; if not '
                        'specified, will use latest acceptance36 build.')
    args = p.parse_args(argv)
    return args


def set_log_info():
    """set logger level to INFO"""
    set_log_level_format(logging.INFO,
                         '%(asctime)s %(levelname)s:%(name)s:%(message)s')


def set_log_debug():
    """set logger level to DEBUG, and debug-level output format"""
    set_log_level_format(
        logging.DEBUG,
        "%(asctime)s [%(levelname)s %(filename)s:%(lineno)s - "
        "%(name)s.%(funcName)s() ] %(message)s"
    )


def set_log_level_format(level, format):
    """
    Set logger level and format.

    :param level: logging level; see the :py:mod:`logging` constants.
    :type level: int
    :param format: logging formatter format string
    :type format: str
    """
    formatter = logging.Formatter(fmt=format)
    logger.handlers[0].setFormatter(formatter)
    logger.setLevel(level)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    # set logging level
    if args.verbose > 1:
        set_log_debug()
    elif args.verbose == 1:
        set_log_info()

    TestTimeAnalyzer(build_num=args.BUILD_NUM, toxenv=args.jobtype).run()
