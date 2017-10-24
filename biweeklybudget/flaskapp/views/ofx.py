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
from flask.views import MethodView
from flask import render_template, jsonify, request
from datatables import DataTable
from sqlalchemy import or_
import pickle
from base64 import b64decode

from biweeklybudget.flaskapp.app import app
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.account import Account
from biweeklybudget.db import db_session
from biweeklybudget.flaskapp.views.searchableajaxview import SearchableAjaxView
from biweeklybudget.ofxapi.local import OfxApiLocal
from biweeklybudget.ofxapi.exceptions import DuplicateFileException

logger = logging.getLogger(__name__)


class OfxView(MethodView):
    """
    Render the GET /ofx view using the ``ofx.html`` template.
    """

    def get(self):
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        return render_template(
            'ofx.html',
            accts=accts
        )


class OfxTransView(MethodView):
    """
    Render the GET /ofx/<int:acct_id>/<str:fitid> view
    using the ``ofx.html`` template.
    """

    def get(self, acct_id, fitid):
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        return render_template(
            'ofx.html',
            accts=accts,
            acct_id=acct_id,
            fitid=fitid
        )


class OfxTransAjax(MethodView):
    """
    Handle GET /ajax/ofx/<int:acct_id>/<str:fitid> endpoint.
    """

    def get(self, acct_id, fitid):
        txn = db_session.query(OFXTransaction).get((acct_id, fitid))
        stmt = txn.statement.as_dict
        res = {
            'acct_name': db_session.query(Account).get(acct_id).name,
            'acct_id': txn.account_id,
            'txn': txn.as_dict,
            'stmt': stmt,
            'account_amount': txn.account_amount
        }
        return jsonify(res)


class OfxAccounts(MethodView):
    """
    Handle GET /api/ofx/accounts endpoint.

    This returns the JSON-ified return value from
    :py:meth:`~.OfxApiLocal.get_accounts` and will usually be called from
    :py:meth:`~.OfxApiRemote.get_accounts`.
    """

    def get(self):
        api = OfxApiLocal(db_session)
        return jsonify(api.get_accounts())


class OfxStatementPost(MethodView):
    """
    Handle POST /api/ofx/statement endpoint.

    This is a ReST API bridge between
    :py:meth:`~.OfxApiRemote.update_statement_ofx` on the client side and
    :py:meth:`~.OfxApiLocal.update_statement_ofx` on the server side.
    """

    def post(self):
        """
        Handle POST to /api/ofx/statement (from
        :py:meth:`~.OfxApiRemote.update_statement_ofx`) to upload a new OFX
        Statement (via :py:meth:`~.OfxApiLocal.update_statement_ofx`).

        The POSTed JSON should have the following keys:

        - ``acct_id`` (int) the Account ID the Statement is for
        - ``mtime`` (str) base64-encoded, pickled representation of the file
          modification time of the OFX file
        - ``filename`` (str) the file name of the OFX file
        - ``ofx`` (str) base64-encoded, pickled representation of the
          ``ofxparse.ofxparse.Ofx`` instance representing the Statement

        Returns a JSON object with the following fields:

        - ``success`` (bool) whether the operation was successful
        - ``message`` (str) message describing success or error message

        For successful operations, the JSON object will contain the following
        additional fields:

        - ``count_new`` (int) count of new transactions added
        - ``count_updated`` (int) count of transactions updated
        - ``statement_id`` (int) ID of the newly-added statement

        HTTP Status Codes:

        - 201 - Statement successfully added
        - 500 - DuplicateFileException
        - 400 - Any other error/exception
        """
        data = request.get_json()
        if sorted(data.keys()) != ['acct_id', 'filename', 'mtime', 'ofx']:
            logger.error('POST contained invalid or missing keys: %s',
                         data.keys())
            resp = jsonify({
                'success': False,
                'message': 'Invalid or missing JSON keys.'
            })
            resp.status_code = 400
            return resp
        try:
            ofx = pickle.loads(b64decode(data['ofx']))
            mtime = pickle.loads(b64decode(data['mtime']))
        except Exception:
            logger.error(
                'Error unpickling or base64-decoding OFX Statement post: %s',
                data['ofx'], exc_info=True
            )
            resp = jsonify({
                'success': False,
                'message': 'Unable to unpickle or b64decode "ofx" field.'
            })
            resp.status_code = 400
            return resp
        api = OfxApiLocal(db_session)
        try:
            stmt_id, count_new, count_upd = api.update_statement_ofx(
                data['acct_id'], ofx, mtime=mtime, filename=data['filename']
            )
        except DuplicateFileException as ex:
            resp = jsonify({
                'success': False,
                'message': 'File %s is a duplicate of stmt %d for account '
                           '%d' % (
                               ex.filename, ex.stmt_id, ex.acct_id
                           ),
                'account_id': ex.acct_id,
                'filename': ex.filename,
                'statement_id': ex.stmt_id
            })
            resp.status_code = 500
            return resp
        except Exception as ex:
            resp = jsonify({
                'success': False,
                'message': 'Exception: %s' % str(ex)
            })
            resp.status_code = 400
            return resp
        resp = jsonify({
            'success': True,
            'message': 'Successfully inserted Statement %d with %d new and %d '
                       'updated Transactions' % (
                           stmt_id, count_new, count_upd
                       ),
            'count_new': count_new,
            'count_updated': count_upd,
            'statement_id': stmt_id
        })
        resp.status_code = 201
        return resp


class OfxAjax(SearchableAjaxView):
    """
    Handle GET /ajax/ofx endpoint.
    """

    def _filterhack(self, qs, s, args):
        """
        DataTables 1.10.12 has built-in support for filtering based on a value
        in a specific column; when this is done, the filter value is set in
        ``columns[N][search][value]`` where N is the column number. However,
        the python datatables package used here only supports the global
        ``search[value]`` input, not the per-column one.

        However, the DataTable search is implemented by passing a callable
        to ``table.searchable()`` which takes two arguments, the current Query
        that's being built, and the user's ``search[value]`` input; this must
        then return a Query object with the search applied.

        In python datatables 0.4.9, this code path is triggered on
        ``if callable(self.search_func) and search.get("value", None):``

        As such, we can "trick" the table to use per-column searching (currently
        only if global searching is not being used) by examining the per-column
        search values in the request, and setting the search function to one
        (this method) that uses those values instead of the global
        ``search[value]``.

        :param qs: Query currently being built
        :type qs: ``sqlalchemy.orm.query.Query``
        :param s: user search value
        :type s: str
        :param args: args
        :type args: dict
        :return: Query with searching applied
        :rtype: ``sqlalchemy.orm.query.Query``
        """
        # Ok, build our filter...
        acct_filter = args['columns'][2]['search']['value']
        if acct_filter != '' and acct_filter != 'None':
            qs = qs.filter(OFXTransaction.account_id == acct_filter)
        # search
        if s != '' and s != 'FILTERHACK':
            if len(s) < 3:
                return qs
            s = '%' + s + '%'
            qs = qs.filter(or_(
                OFXTransaction.name.like(s),
                OFXTransaction.memo.like(s),
                OFXTransaction.description.like(s),
                OFXTransaction.notes.like(s)
            ))
        return qs

    def get(self):
        """
        Render and return JSON response for GET /ajax/ofx
        """
        args = request.args.to_dict()
        args_dict = self._args_dict(args)
        if self._have_column_search(args_dict) and args['search[value]'] == '':
            args['search[value]'] = 'FILTERHACK'
        table = DataTable(
            args, OFXTransaction, db_session.query(OFXTransaction), [
                (
                    'date',
                    'date_posted',
                    lambda i: i.date_posted.strftime('%Y-%m-%d')
                ),
                (
                    'amount',
                    lambda a: float(a.amount)
                ),
                (
                    'account',
                    'account.name',
                    lambda i: "{} ({})".format(i.name, i.id)
                ),
                ('type', 'trans_type'),
                'name',
                'memo',
                'description',
                'fitid',
                ('last_stmt', 'statement.id'),
                (
                    'last_stmt_date',
                    'statement.as_of',
                    lambda i: i.as_of.strftime('%Y-%m-%d')
                ),
                (
                    'reconcile_id',
                    'reconcile',
                    lambda i: None if i.reconcile is None else i.reconcile.id
                )
            ]
        )
        table.add_data(acct_id=lambda o: o.account_id)
        if args['search[value]'] != '':
            table.searchable(lambda qs, s: self._filterhack(qs, s, args_dict))
        return jsonify(table.json())


app.add_url_rule('/ofx', view_func=OfxView.as_view('ofx_view'))
app.add_url_rule('/ajax/ofx', view_func=OfxAjax.as_view('ofx_ajax'))
app.add_url_rule(
    '/ajax/ofx/<int:acct_id>/<fitid>',
    view_func=OfxTransAjax.as_view('ofx_trans_ajax')
)
app.add_url_rule(
    '/api/ofx/accounts',
    view_func=OfxAccounts.as_view('ofx_api_accounts')
)
app.add_url_rule(
    '/api/ofx/statement',
    view_func=OfxStatementPost.as_view('ofx_api_statement')
)
app.add_url_rule(
    '/ofx/<int:acct_id>/<fitid>',
    view_func=OfxTransView.as_view('ofx_trans')
)
