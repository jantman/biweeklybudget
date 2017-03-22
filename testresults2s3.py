#!/usr/bin/env python
"""
Upload test artifacts to S3, from TravisCI, along with a generated index page.
"""

import os
import boto3
import logging
from mimetypes import guess_type

FORMAT = "[%(asctime)s %(levelname)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=FORMAT)
logger = logging.getLogger()

# suppress boto3 internal logging below WARNING level
boto3_log = logging.getLogger("boto3")
boto3_log.setLevel(logging.WARNING)
boto3_log.propagate = True

# suppress botocore internal logging below WARNING level
botocore_log = logging.getLogger("botocore")
botocore_log.setLevel(logging.WARNING)
botocore_log.propagate = True

# suppress s3transfer internal logging below WARNING level
s3transfer_log = logging.getLogger("s3transfer")
s3transfer_log.setLevel(logging.WARNING)
s3transfer_log.propagate = True


class S3Uploader(object):

    def __init__(self):
        self._s3 = boto3.resource(
            's3', region_name='us-east-1',
            aws_access_key_id=os.environ['TRAVIS_ACCESS_KEY'],
            aws_secret_access_key=os.environ['TRAVIS_SECRET_KEY']
        )
        if 'TRAVIS_REPO_SLUG' not in os.environ:
            raise RuntimeError('TRAVIS_REPO_SLUG not in environment')
        if 'TRAVIS_JOB_NUMBER' not in os.environ:
            raise RuntimeError('TRAVIS_JOB_NUMBER not in environment')
        self.bkt = self._s3.Bucket('jantman-personal-public')
        self.basedir = os.path.dirname(os.path.realpath(__file__)) + '/'
        self.prefix = 'travisci/%s/%s/' % (
            os.environ['TRAVIS_REPO_SLUG'],
            os.environ['TRAVIS_JOB_NUMBER']
        )

    def run(self):
        files = self._list_all_files(['htmlcov', 'results', 'coverage.xml'])
        files.append(self.write_index_html(files))
        for f in sorted(files):
            self.upload_file(self.key_for_path(f), f)
        print("Uploaded %d files" % len(files))
        print("\nResults available at:\n")
        print('http://jantman-personal-public.s3-website-us-east-1.'
              'amazonaws.com/%sindex.html' % self.prefix)

    def write_index_html(self, files):
        p = os.path.join(self.basedir, 'index.html')
        title = 'TravisCI %s Job %s' % (
            os.environ['TRAVIS_REPO_SLUG'],
            os.environ['TRAVIS_JOB_NUMBER']
        )
        s = '<html><head><title>%s</title></head>' % title
        s += '<body><h1>%s</h1><ul>' % title
        for f in sorted(files):
            f = f.replace(self.basedir, '')
            s += '<li><a href="%s">%s</a>' % (f, f)
        s += '</ul></body></html>'
        with open(p, 'w') as fh:
            fh.write(s)
        return p

    def key_for_path(self, f):
        """
        Return the key in S3 for a file at f
        """
        return f.replace(self.basedir, self.prefix)

    def _list_all_files(self, paths):
        """
        Given a list of paths on the local filesystem, return a list of all
        files in ``paths`` that exist, and for any directories in ``paths`` that
        exist, all files recursively contained in them.

        :param paths: list of file/directory paths to check
        :type paths: list
        :return: list of all extant files contained under those paths
        :rtype: list
        """
        files = []
        logger.info('Listing files under %d paths', len(paths))
        for p in paths:
            p = os.path.abspath(os.path.join(self.basedir, p))
            if not os.path.exists(p):
                logger.warning('Skipping non-existent path: %s', p)
                continue
            if os.path.isfile(p):
                files.append(p)
            elif os.path.isdir(p):
                dirs = self._listdir(p)
                logger.debug('Found %d files under %s', len(dirs), p)
                files.extend(dirs)
            else:
                logger.warning('Skipping unknown path type: %s', p)
        logger.debug('Done finding candidate files.')
        return list(set(files))

    def _listdir(self, path):
        """
        Given the path to a directory, return a list of all file paths under
        that directory (recursively).

        :param path: path to directory
        :type path: str
        :return: list of regular file paths under that directory
        :rtype: list
        """
        files = []
        for root, _, filenames in os.walk(path):
            for fn in filenames:
                p = os.path.join(root, fn)
                if os.path.isfile(p):
                    files.append(p)
        return files

    def upload_file(self, key, path):
        mt = guess_type(path)[0]
        logger.info('Uploading %s to %s (Content-Type: %s)', path, key, mt)
        self.bkt.upload_file(
            path, key, ExtraArgs={'ContentType': mt}
        )

if __name__ == "__main__":
    S3Uploader().run()
