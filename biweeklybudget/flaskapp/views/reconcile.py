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

from biweeklybudget.flaskapp.app import app
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.account import Account
from biweeklybudget.models.txn_reconcile import TxnReconcile
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.db import db_session

logger = logging.getLogger(__name__)


class ReconcileView(MethodView):
    """
    Render the top-level GET /reconcile view using ``reconcile.html`` template.
    """

    def get(self):
        budgets = {}
        active_budgets = {}
        for b in db_session.query(Budget).all():
            k = b.name
            if b.is_income:
                k = '%s (i)' % b.name
            budgets[b.id] = k
            if b.is_active:
                active_budgets[b.id] = k
        accts = {a.name: a.id for a in db_session.query(Account).all()}
        return render_template(
            'reconcile.html',
            budgets=budgets,
            accts=accts,
            active_budgets=active_budgets
        )


class TxnReconcileAjax(MethodView):
    """
    Handle GET /ajax/reconcile/<int:reconcile_id> endpoint.
    """

    def get(self, reconcile_id):
        rec = db_session.query(TxnReconcile).get(reconcile_id)

        res = {
            'reconcile': rec.as_dict,
            'transaction': rec.transaction.as_dict
        }
        res['transaction']['budgets'] = [
            {
                'name': bt.budget.name,
                'id': bt.budget_id,
                'amount': bt.amount,
                'is_income': bt.budget.is_income
            }
            for bt in sorted(
                rec.transaction.budget_transactions,
                key=lambda x: x.amount, reverse=True
            )
        ]
        if rec.ofx_trans is not None:
            res['ofx_trans'] = rec.ofx_trans.as_dict
            res['ofx_stmt'] = rec.ofx_trans.statement.as_dict
            res['acct_id'] = rec.ofx_trans.account_id
            res['acct_name'] = rec.ofx_trans.account.name
        else:
            res['ofx_trans'] = None
            res['ofx_stmt'] = None
            res['acct_id'] = rec.transaction.account_id
            res['acct_name'] = rec.transaction.account.name
        return jsonify(res)


class OfxUnreconciledAjax(MethodView):
    """
    Handle GET /ajax/unreconciled/ofx endpoint.
    """

    def get(self):
        res = []
        for t in OFXTransaction.unreconciled(
            db_session
        ).order_by(OFXTransaction.date_posted, OFXTransaction.fitid).all():
            d = t.as_dict
            d['account_name'] = t.account.name
            d['account_amount'] = t.account_amount
            res.append(d)
        return jsonify(res)


class TransUnreconciledAjax(MethodView):
    """
    Handle GET /ajax/unreconciled/trans endpoint.
    """

    def get(self):
        res = []
        for t in Transaction.unreconciled(
            db_session
        ).order_by(Transaction.date, Transaction.id).all():
            d = t.as_dict
            d['budgets'] = [
                {
                    'name': bt.budget.name,
                    'id': bt.budget_id,
                    'amount': bt.amount,
                    'is_income': bt.budget.is_income
                }
                for bt in sorted(
                    t.budget_transactions, key=lambda x: x.amount,
                    reverse=True
                )
            ]
            d['account_name'] = t.account.name
            res.append(d)
        return jsonify(res)


class ReconcileAjax(MethodView):
    """
    Handle POST ``/ajax/reconcile`` endpoint.
    """

    def post(self):
        """
        Handle POST ``/ajax/reconcile``

        Request is a JSON dict with two keys, "reconciled" and "ofxIgnored".
        "reconciled" value is a dict of integer transaction ID keys, to
        values which are either a string reason why the Transaction is being
        reconciled as "No OFX" or a 2-item list of OFXTransaction acct_id
        and fitid.
        "ofxIgnored" is a dict with string keys which are strings identifying
        an OFXTransaction in the form "<ACCT_ID>%<FITID>", and values are a
        string reason why the OFXTransaction is being reconciled without a
        matching Transaction.

        Response is a JSON dict. Keys are ``success`` (boolean) and either
        ``error_message`` (string) or ``success_message`` (string).

        :return: JSON response
        """
        raw = request.get_json()
        data = {
            'reconciled': {
                int(x): raw['reconciled'][x] for x in raw['reconciled']
            },
            'ofxIgnored': raw.get('ofxIgnored', {})
        }
        logger.debug('POST /ajax/reconcile: %s', data)
        rec_count = 0
        for trans_id in sorted(data['reconciled'].keys()):
            trans = db_session.query(Transaction).get(trans_id)
            if trans is None:
                logger.error('Invalid transaction ID: %s', trans_id)
                return jsonify({
                    'success': False,
                    'error_message': 'Invalid Transaction ID: %s' % trans_id
                }), 400
            if not isinstance(data['reconciled'][trans_id], type([])):
                # it's a string; reconcile without OFX
                db_session.add(TxnReconcile(
                    txn_id=trans_id,
                    note=data['reconciled'][trans_id]
                ))
                logger.info(
                    'Reconcile %s as NoOFX; note=%s',
                    trans, data['reconciled'][trans_id]
                )
                rec_count += 1
                continue
            # else reconcile with OFX
            ofx_key = (
                data['reconciled'][trans_id][0], data['reconciled'][trans_id][1]
            )
            ofx = db_session.query(OFXTransaction).get(ofx_key)
            if ofx is None:
                logger.error('Invalid OFXTransaction: %s', ofx_key)
                return jsonify({
                    'success': False,
                    'error_message': 'Invalid OFXTransaction: (%s, \'%s\')' % (
                        ofx_key[0], ofx_key[1]
                    )
                }), 400
            db_session.add(TxnReconcile(
                txn_id=trans_id,
                ofx_account_id=data['reconciled'][trans_id][0],
                ofx_fitid=data['reconciled'][trans_id][1]
            ))
            logger.info('Reconcile %s with %s', trans, ofx)
            rec_count += 1
        # handle OFXTransactions to reconcile with no Transaction
        for ofxkey in sorted(data['ofxIgnored'].keys()):
            note = data['ofxIgnored'][ofxkey]
            acct_id, fitid = ofxkey.split('%', 1)
            db_session.add(TxnReconcile(
                ofx_account_id=acct_id,
                ofx_fitid=fitid,
                note=note
            ))
            logger.info(
                'Reconcile OFXTransaction (%s, %s) as NoTransaction; note=%s',
                acct_id, fitid, note
            )
            rec_count += 1
        try:
            db_session.flush()
            db_session.commit()
        except Exception as ex:
            logger.error('Exception committing transaction reconcile',
                         exc_info=True)
            return jsonify({
                'success': False,
                'error_message': 'Exception committing reconcile(s): %s' % ex
            }), 400
        return jsonify({
            'success': True,
            'success_message': 'Successfully reconciled '
                               '%d transactions' % rec_count
        })


app.add_url_rule(
    '/reconcile',
    view_func=ReconcileView.as_view('reconcile_view')
)

app.add_url_rule(
    '/ajax/reconcile/<int:reconcile_id>',
    view_func=TxnReconcileAjax.as_view('txn_reconcile_ajax')
)

app.add_url_rule(
    '/ajax/unreconciled/ofx',
    view_func=OfxUnreconciledAjax.as_view('ofx_unreconciled_ajax')
)

app.add_url_rule(
    '/ajax/unreconciled/trans',
    view_func=TransUnreconciledAjax.as_view('trans_unreconciled_ajax')
)

app.add_url_rule(
    '/ajax/reconcile',
    view_func=ReconcileAjax.as_view('reconcile_ajax')
)
