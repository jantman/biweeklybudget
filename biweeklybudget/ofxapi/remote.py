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
import pickle
from base64 import b64encode

import requests

from biweeklybudget.ofxapi.exceptions import DuplicateFileException

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

logger = logging.getLogger(__name__)


class OfxApiRemote(object):
    """
    Remote OFX API client, used by ofxgetter/ofxbackfiller when running on a
    remote system.
    """

    def __init__(
        self, api_base_url, ca_bundle=None, client_cert_path=None,
        client_key_path=None
    ):
        """
        Initialize a new OFX remote API client.

        :param api_base_url: base URL to the biweeklybudget installation
        :type api_base_url: str
        :param ca_bundle: Optional; local filesystem path to a SSL CA
          certificate bundle file or directory, to use for server verification.
        :type ca_bundle: str
        :param client_cert_path: Optional; local filesystem path to a SSL
          client certificate to use for authentication, if required.
        :type client_cert_path: str
        :param client_key_path: Optional; local filesystem path to key file for
          the certificate specified in ``client_cert_path``, if key is in a
          separate file. The key must be unencrypted.
        :type client_key_path: str
        """
        logger.debug(
            'New OFX API remote client; base_url=%s cert_path=%s',
            api_base_url, client_cert_path
        )
        self._base_url = api_base_url
        self._cert_path = client_cert_path
        self._key_path = client_key_path
        self._ca_bundle = ca_bundle
        self._requests_kwargs = {}
        if ca_bundle is not None:
            self._requests_kwargs['verify'] = ca_bundle
        if client_cert_path is not None:
            if client_key_path is not None:
                self._requests_kwargs['cert'] = (
                    client_cert_path, client_key_path
                )
            else:
                self._requests_kwargs['cert'] = client_cert_path

    def get_accounts(self):
        """
        Query the database for all
        :py:attr:`ofxgetter-enabled
        <biweeklybudget.models.account.Account.for_ofxgetter>`
        :py:class:`Accounts <biweeklybudget.models.account.Account>` that have
        a non-empty
        :py:attr:`biweeklybudget.models.account.Account.ofxgetter_config` and a
        non-None
        :py:attr:`biweeklybudget.models.account.Account.vault_creds_path`.
        Return a dict of string
        :py:attr:`Account name <biweeklybudget.models.account.Account.name>` to
        dict with keys:

        - ``vault_path`` - :py:attr:`~.Account.vault_creds_path`
        - ``config`` - :py:attr:`~.Account.ofxgetter_config`
        - ``id`` - :py:attr:`~.Account.id`
        - ``cat_memo`` - :py:attr:`~.Account.ofx_cat_memo_to_name`

        :return: dict of account names to configuration
        :rtype: dict
        """
        url = urljoin(self._base_url, '/api/ofx/accounts')
        logger.debug('GET ofx accounts from: %s', url)
        r = requests.get(url, **self._requests_kwargs)
        logger.debug('API Response: HTTP %d; text: %s', r.status_code, r.text)
        return r.json()

    def update_statement_ofx(self, acct_id, ofx, mtime=None, filename=None):
        """
        Update a single statement for the specified account, from an OFX file.

        :param acct_id: Account ID that statement is for
        :type acct_id: int
        :param ofx: Ofx instance for parsed file
        :type ofx: ``ofxparse.ofxparse.Ofx``
        :param mtime: OFX file modification time (or current time)
        :type mtime: datetime.datetime
        :param filename: OFX file name
        :type filename: str
        :returns: 3-tuple of the int ID of the
          :py:class:`~biweeklybudget.models.ofx_statement.OFXStatement`
          created by this run, int count of new :py:class:`~.OFXTransaction`
          created, and int count of :py:class:`~.OFXTransaction` updated
        :rtype: tuple
        :raises: :py:exc:`RuntimeError` on error parsing OFX or unknown account
          type; :py:exc:`~.DuplicateFileException` if the file (according to the
          OFX signon date/time) has already been recorded.
        """
        encodedofx = b64encode(pickle.dumps(ofx))
        encodedmtime = b64encode(pickle.dumps(mtime))
        if not isinstance(encodedofx, type('foo')):
            encodedofx = encodedofx.decode('utf-8')
            encodedmtime = encodedmtime.decode('utf-8')
        postdata = {
            'mtime': encodedmtime,
            'filename': filename,
            'acct_id': acct_id,
            'ofx': encodedofx
        }
        url = urljoin(self._base_url, '/api/ofx/statement')
        logger.debug('POST ofx statement to: %s; data: %s', url, postdata)
        r = requests.post(url, json=postdata, **self._requests_kwargs)
        logger.debug('API Response: HTTP %d; text: %s', r.status_code, r.text)
        try:
            resp = r.json()
        except Exception:
            raise RuntimeError(
                'API response could not be JSON deserialized: %s' % r.text
            )
        if r.status_code == 500:
            raise DuplicateFileException(
                resp['account_id'], resp['filename'], resp['statement_id']
            )
        if r.status_code == 400:
            raise RuntimeError('OFX API Error: %s' % resp.get('message'))
        if r.status_code != 201:
            raise RuntimeError(
                'Unknown OFX API Status Code: %d; response: %s' % (
                    r.status_code, resp
                )
            )
        # success
        logger.debug('Successfully uploaded statement: %s', resp['message'])
        return resp['statement_id'], resp['count_new'], resp['count_updated']
