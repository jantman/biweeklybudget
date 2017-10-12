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

import argparse
import logging
import atexit

from biweeklybudget.models.projects import Project, BoMItem
from biweeklybudget.db import init_db, db_session, cleanup_db
from biweeklybudget.cliutils import set_log_debug, set_log_info

from biweeklybudget.vendored.wishlist.core import Wishlist

logger = logging.getLogger(__name__)

# suppress requests logging
requests_log = logging.getLogger("requests")
requests_log.setLevel(logging.WARNING)
requests_log.propagate = True


class WishlistToProject(object):

    def __init__(self):
        atexit.register(cleanup_db)
        init_db()
        self._wlist = Wishlist()

    def run(self):
        """
        Run the synchronization.

        :return: 2-tuple; count of successful syncs, total count of projects
          with associated wishlists
        :rtype: tuple
        """
        logger.debug('Beginning wishlist sync run')
        success = 0
        total = 0
        for list_url, proj in self._get_wishlist_projects():
            total += 1
            try:
                if self._do_project(list_url, proj):
                    success += 1
            except Exception:
                logger.error('Exception updating project %s with list %s',
                             proj, list_url, exc_info=True)
        return success, total

    def _do_project(self, list_url, project):
        """
        Update a project with information from its wishlist.

        :param list_url: Amazon wishlist URL
        :type list_url: str
        :param project: the project to update
        :type project: Project
        :return: whether or not the update was successful
        :rtype: bool
        """
        logger.debug('Handling project: %s', project)
        pitems = self._project_items(project)
        witems = self._wishlist_items(list_url)
        logger.debug('Project has %d items; wishlist has %d',
                     len(pitems), len(witems))
        for url, item in pitems.items():
            if url not in witems:
                logger.info(
                    '%s (%s) removed from amazon list; setting inactive',
                    item, url
                )
                item.is_active = False
                db_session.add(item)
        for url, item in witems.items():
            if url in pitems:
                bitem = pitems[url]
                logger.info('Updating %s from Amazon wishlist', bitem)
            else:
                bitem = BoMItem()
                bitem.project = project
                logger.info('Adding new BoMItem for wishlist %s', url)
            bitem.url = url
            bitem.is_active = True
            bitem.quantity = item['quantity']
            bitem.unit_cost = item['cost']
            bitem.name = item['name']
            db_session.add(bitem)
        logger.info('Committing changes for project %s url %s',
                    project, list_url)
        db_session.commit()
        return True

    def _project_items(self, proj):
        """
        Return all of the BoMItems for the specified project, as a dict of
        URL to BoMItem.

        :param proj: the project to get items for
        :type proj: Project
        :return: item URLs to BoMItems
        :rtype: dict
        """
        res = {}
        for i in db_session.query(BoMItem).filter(
            BoMItem.project.__eq__(proj)
        ).all():
            res[i.url] = i
        return res

    def _wishlist_items(self, list_url):
        """
        Get the items on the specified wishlist.

        :param list_url: wishlist URL
        :type list_url: str
        :return: dict of item URL to item details dict
        :rtype: dict
        """
        res = {}
        list_name = list_url.split('/')[-1]
        logger.debug('Getting wishlist items for wishlist: %s', list_name)
        items = [i for i in self._wlist.get(list_name)]
        logger.debug("Found %d items in list" % len(items))
        for item in items:
            d = {'name': item.title, 'url': item.url}
            try:
                d['quantity'] = item.wanted_count
            except Exception:
                d['quantity'] = 1
            if item.price > 0:
                d['cost'] = item.price
            else:
                d['cost'] = item.marketplace_price
            res[item.url] = d
        return res

    def _get_wishlist_projects(self):
        """
        Find all projects with descriptions that begin with a wishlist URL.

        :return: list of (url, Project object) tuples
        :rtype: list
        """
        res = []
        logger.debug('Querying active projects for wishlist URLs')
        q = db_session.query(Project).filter(Project.is_active.__eq__(True))
        total_p = 0
        for p in q.all():
            total_p += 1
            if p.notes.strip() == '':
                continue
            u = p.notes.split(' ')[0]
            if self._url_is_wishlist(u):
                res.append((u, p))
        logger.info('Found %d of %d projects with wishlist URLs',
                    len(res), total_p)
        return res

    @staticmethod
    def _url_is_wishlist(url):
        """
        Determine if the given string or URL matches a wishlist.

        :param url: URL or string to test
        :type url: str
        :return: whether url is a wishlist URL
        :rtype: bool
        """
        return url.startswith('https://www.amazon.com/gp/registry/wishlist/')


def parse_args():
    p = argparse.ArgumentParser(
        description='Synchronize Amazon wishlists to projects, for projects '
                    'with Notes fields beginning with an Amazon public '
                    'wishlist URL'
    )
    p.add_argument('-v', '--verbose', dest='verbose', action='count', default=0,
                   help='verbose output. specify twice for debug-level output.')
    args = p.parse_args()
    return args


def main():
    global logger
    format = "[%(asctime)s %(levelname)s] %(message)s"
    logging.basicConfig(level=logging.WARNING, format=format)
    logger = logging.getLogger()

    args = parse_args()

    # set logging level
    if args.verbose > 1:
        set_log_debug(logger)
    elif args.verbose == 1:
        set_log_info(logger)
    if args.verbose <= 1:
        # if we're not in verbose mode, suppress routine logging for cron
        lgr = logging.getLogger('alembic')
        lgr.setLevel(logging.WARNING)
        lgr = logging.getLogger('biweeklybudget.db')
        lgr.setLevel(logging.WARNING)

    syncer = WishlistToProject()
    success, total = syncer.run()
    if success != total:
        logger.warning('Synced %d of %d project wishlists', success, total)
        raise SystemExit(1)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
