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
from biweeklybudget.models.account import Account

logger = logging.getLogger(__name__)


class OfxApiLocal(object):

    def __init__(self, db_sess):
        """
        Initialize a new Local OFX API client, when running ofxgetter or
        ofxbackfiller with direct database access, or used to back the OFX
        HTTP API.

        :param db_sess: active database session to use for queries
        :type db_sess: sqlalchemy.orm.session.Session
        """
        self._db = db_sess

    def get_accounts(self):
        """
        Query the database for all
        :py:attr:`ofxgetter-enabled <~.account.Account.for_ofxgetter>`
        :py:class:`Accounts <~.models.account.Account>` that have a non-empty
        :py:attr:`~.Account.ofxgetter_config` and a non-None
        :py:attr:`~.Account.vault_creds_path`. Return a dict of string
        :py:attr:`Account name `~.Account.name` to dict with keys:

        - ``vault_path`` - :py:attr:`~.Account.vault_creds_path`
        - ``config`` - :py:attr:`~.Account.ofxgetter_config`
        - ``id`` - :py:attr:`~.Account.id`
        - ``cat_memo`` - :py:attr:`~.Account.ofx_cat_memo_to_name`

        :return: dict of account names to configuration
        :rtype: dict
        """
        result = {}
        for acct in self._db.query(Account).filter(
            Account.for_ofxgetter
        ).order_by(Account.name).all():
            if acct.vault_creds_path is None and acct.ofxgetter_config == {}:
                continue
            result[acct.name] = {
                'vault_path': acct.vault_creds_path,
                'config': acct.ofxgetter_config,
                'id': acct.id,
                'cat_memo': acct.ofx_cat_memo_to_name
            }
        logger.debug('Query found %d ofxgetter-enabled Accounts', len(result))
        return result
