#!/usr/bin/env python
"""
Script to build Docker image of the project and possibly test it.

Actions are largely driven by environment variables, and some information
about the version of biweeklybudget installed...

If ``TRAVIS=="true"``:

  - build the image using the sdist created by ``tox``
  - run the image with test configuration and in-memory SQLite, make sure
    it serves pages (just check that ``GET /`` is 200 OK).

Otherwise:

  - just build the image
  - only test it if ``TEST_DOCKER=="true"``
  - tag it appropriately
  - if checked out to a git tag according to versionfinder, or
    ``DOCKER_BUILD_VER`` is set, build Docker image for that version
    **from PyPI**. Otherwise, build using the sdist created by ``tox``.

"""

import os
import sys
import logging
import time
from git import Repo
import requests
from versionfinder import find_version

FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.WARNING, format=FORMAT)
logger = logging.getLogger()


class DockerImageBuilder(object):

    # image_name = 'jantman/biweeklybudget'
    image_name = 'jantman/mongodb24'

    def __init__(self, toxinidir):
        """
        :param toxinidir: directory containing tox.ini
        :type toxinidir: str
        """
        self._toxinidir = toxinidir
        self._gitdir = os.path.join(self._toxinidir, '.git')
        logger.debug('Initializing DockerImageBuilder; toxinidir=%s gitdir=%s',
                     self._toxinidir, self._gitdir)
        if not os.path.exists(self._gitdir) or not os.path.isdir(self._gitdir):
            raise RuntimeError(
                'Error: %s does not exist or is not a directory' % self._gitdir
            )

    def _find_git_info(self):
        """
        Return information about the state of the Git repository tox is being
        run from.
        
        :return: dict with keys 'dirty' (bool), 'sha' (str), 'tag' (str or None)
        :rtype: dict
        """
        res = {}
        logger.debug('Checking git status...')
        repo = Repo(path=self._gitdir, search_parent_directories=False)
        res['sha'] = repo.head.commit.hexsha
        res['dirty'] = repo.is_dirty(untracked_files=True)
        res['tag'] = None
        for tag in repo.tags:
            # each is a git.Tag object
            if tag.commit.hexsha == res['sha']:
                res['tag'] = tag.name
        logger.debug('Git info: %s', res)
        return res

    def _tag_for_travis(self):
        """
        Return the Docker image tag for a TravisCI build.

        :rtype: str
        :return: tag for Docker image
        """
        job = os.environ.get('TRAVIS_JOB_NUMBER', '%d' % int(time.time()))
        return 'travis_%s' % job

    @property
    def build_ver(self):
        """
        Return the pypi version to build, or None if not a release build.

        :rtype: str
        :return: release build version or None
        """
        env_ver = os.environ.get('DOCKER_BUILD_VER', None)
        if env_ver is not None:
            logger.debug('build_ver %s based on DOCKER_BUILD_VER env var',
                         env_ver)
            return env_ver
        if self._gitinfo['tag'] is not None:
            logger.debug('build_ver %s based on git tag', self._gitinfo['tag'])
            return self._gitinfo['tag']
        return None

    def _tag_for_local(self):
        """
        Return the Docker image tag for a local build

        :return: tag for local build
        :rtype: str
        """
        time_s = '%d' % int(time.time())
        if self.build_ver is not None:
            tag = '%s_%s' % (self.build_ver, time_s)
            logger.debug('Local tag (build_ver): %s', tag)
            return tag
        sha = self._gitinfo['sha'][:8]
        if self._gitinfo['dirty']:
            sha += '-dirty'
        tag = '%s_%s' % (sha, time_s)
        logger.debug('Local tag: %s', tag)
        return tag

    def build(self):
        self._gitinfo = self._find_git_info()
        if os.environ.get('TRAVIS', 'false') == 'true':
            tag = self.build_travis()
            self.test(tag)
        else:
            tag = self.build_local()
            if os.environ.get('TEST_DOCKER', 'false') == 'true':
                self.test(tag)
        print("Built image with tag: %s" % tag)

    def build_travis(self):
        """
        Build the image on TravisCI. Return the tag of the built image.

        :rtype: str
        :return: tag for built image
        """
        tag = self._tag_for_travis()
        logger.info('Travis build; tag=%s', tag)
        self._check_tag(tag)
        return self._build_image(tag)

    def build_local(self):
        """
        Build the image locally. Return the tag of the built image.

        :rtype: str
        :return: tag for built image
        """
        tag = self._tag_for_local()
        logger.info('Local build; tag=%s', tag)
        self._check_tag(tag)
        if self.build_ver is not None:
            return self._build_release_image(tag)
        return self._build_image(tag)

    def _build_image(self, tag):
        """
        Build Docker image from the tox-generated sdist, with the specified tag.

        :param tag: tag to assign to the image
        :type tag: str
        :return: tag assigned to the image
        :rtype: str
        """
        return tag

    def _build_release_image(self, tag):
        """
        Build Docker image from PyPI release, with the specified tag.

        :param tag: tag to assign to the image
        :type tag: str
        :return: tag assigned to the image
        :rtype: str
        """
        return tag

    def _check_tag(self, tag):
        """
        Confirm that the specified tag is not already present on Docker Hub or
        locally.

        :param tag: tag to check
        :type tag: str
        """
        self._check_tag_local(tag)
        logger.debug('Checking for tag on hub.docker.com')
        url = 'https://hub.docker.com/v2/%s/tags/list' % self.image_name
        res = requests.get(url)
        logger.debug('GET %s: %d', url, res.status_code)
        if res.status_code == 404:
            return

    def _check_tag_local(self, tag):
        """
        Confirm that the specified tag is not already present locally.

        :param tag: tag to check
        :type tag: str
        """
        return True

    def test(self, tag):
        """
        Test the image that was just built.

        :param tag: tag of built image
        :type tag: str
        """
        raise NotImplementedError()


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
    sys.argv.pop(0)
    if sys.argv[0] in ['-v', '-vv']:
        sys.argv.pop(0)
        set_log_debug()
    toxinidir = sys.argv[0]
    b = DockerImageBuilder(toxinidir)
    b.build()
