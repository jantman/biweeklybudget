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
import logging

from biweeklybudget.ofxapi.local import OfxApiLocal
from biweeklybudget.ofxapi.remote import OfxApiRemote

logger = logging.getLogger(__name__)


def apiclient(api_url=None, ca_bundle=None, client_cert=None, client_key=None):
    if api_url is None:
        logger.info('Using OfxApiLocal direct database access')
        import atexit
        from biweeklybudget.db import init_db, cleanup_db, db_session
        atexit.register(cleanup_db)
        init_db()
        return OfxApiLocal(db_session)
    logger.info('Using OfxApiRemote with base_url %s', api_url)
    return OfxApiRemote(
        api_url, ca_bundle=ca_bundle, client_cert_path=client_cert,
        client_key_path=client_key
    )
