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

from setuptools import setup, find_packages
from biweeklybudget.version import VERSION, PROJECT_URL

with open('README.rst') as f:
    long_description = f.read()

pyver_requires = []
dep_links = []
with open('requirements.txt') as f:
    for line in f.readlines():
        if line.startswith('#'):
            continue
        if '://' in line:
            dep_links.append(line.strip())
        else:
            pyver_requires.append(line.strip())

classifiers = [
    'Development Status :: 2 - Pre-Alpha',
    'Environment :: Web Environment',
    'Framework :: Flask',
    'Intended Audience :: End Users/Desktop',
    'License :: OSI Approved :: GNU Affero General Public License '
    'v3 or later (AGPLv3+)',
    'Natural Language :: English',
    'Operating System :: POSIX',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.3',
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Topic :: Office/Business :: Financial'
]

setup(
    name='biweeklybudget',
    version=VERSION,
    author='Jason Antman',
    author_email='jason@jasonantman.com',
    packages=find_packages(),
    package_data={
        'biweeklybudget': [
            'flaskapp/templates/*',
            'flaskapp/static/*',
            'alembic/alembic.ini',
            'alembic/env.py',
            'alembic/versions/*.py'
        ]
    },
    url=PROJECT_URL,
    description='Responsive Flask/SQLAlchemy personal finance app, '
                'specifically for biweekly budgeting.',
    long_description=long_description,
    install_requires=pyver_requires,
    dependency_links=dep_links,
    include_package_data=True,
    entry_points="""
    [console_scripts]
    loaddata = biweeklybudget.load_data:main
    ofxgetter = biweeklybudget.ofxgetter:main
    ofxbackfiller = biweeklybudget.backfill_ofx:main
    initdb = biweeklybudget.initdb:main
    wishlist2project = biweeklybudget.wishlist2project:main
    ofxclient = biweeklybudget.vendored.ofxclient.cli:run
    [flask.commands]
    rundev=biweeklybudget.flaskapp.cli_commands:rundev_command
    """,
    keywords="budget finance biweekly ofx flask responsive sqlalchemy bank",
    classifiers=classifiers
)
