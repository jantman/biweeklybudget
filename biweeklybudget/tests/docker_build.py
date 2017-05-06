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
from git import Repo
from versionfinder import find_version


class DockerImageBuilder(object):

    def __init__(self, toxinidir):
        """
        :param toxinidir: directory containing tox.ini
        :type toxinidir: str
        """
        self._toxinidir = toxinidir
        self._gitdir = os.path.join(self._toxinidir, '.git')
        if not os.path.exists(self._gitdir) or not os.path.isdir(self._gitdir):
            raise RuntimeError(
                'Error: %s does not exist or is not a directory' % self._gitdir
            )

    def _find_git_info(self):
        """
        
        :return: dict with keys 'dirty' (bool), 'sha' (str), 'tag' (str or None)
        :rtype: dict
        """
        res = {}
        repo = Repo(path=self._gitdir, search_parent_directories=False)
        res['sha'] = repo.head.commit.hexsha
        res['dirty'] = repo.is_dirty(untracked_files=True)
        res['tag'] = None
        for tag in repo.tags:
            # each is a git.Tag object
            if tag.commit.hexsha == res['commit']:
                res['tag'] = tag.name
        return res

    def build(self):
        if (
            os.environ.get('TEST_DOCKER', 'false') == 'true' or
            os.environ.get('TRAVIS', 'false') == 'true'
        ):
            self.build_travis()
        else:
            self.build_local()

    def build_travis(self):
        pass

    def build_local(self):
        pass

    def test(self):
        pass

if __name__ == "__main__":
    toxinidir = sys.argv[1]
    b = DockerImageBuilder(toxinidir)
    b.build()
