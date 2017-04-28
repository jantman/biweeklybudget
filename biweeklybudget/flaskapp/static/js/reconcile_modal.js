/*
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
*/

/**
 * Ajax callback to generate the modal HTML with reconcile information.
 */
function txnReconcileModalDiv(msg) {
    var frm = '<div>';
    // TxnReconcile info
    frm += '<div class="row"><div class="col-lg-12">\n'
    frm += '<dl class="dl-horizontal">\n';
    frm += '<dt>Date Reconciled</dt><dd>' + msg['reconcile']['reconciled_at']['str'] + ' ' + msg['reconcile']['reconciled_at']['tzname'] + '</dd>\n';
    frm += '<dt>Note</dt><dd>' + msg['reconcile']['note'] + '</dd>\n';
    frm += '<dt>Rule</dt><dd>' + msg['reconcile']['rule_id'] + '</dd>\n'
    frm += '</dl>\n';
    frm += '</div><!-- /col-lg-12 --></div><!-- /row -->\n';
    frm += '<div class="row">\n';
    // Transaction info
    frm += '<div class="col-lg-6">\n';
    frm += '<div class="table-responsive">\n<table class="table table-bordered table-hover" id="txnReconcileModal-trans">\n<tbody>\n';
    frm += '<tr><th colspan="2" style="text-align: center;">Transaction</th></tr>\n';
    frm += '<tr><th>Date</th><td>' + msg['transaction']['date']['str'] + '</td></tr>\n';
    frm += '<tr><th>Amount</th><td>' + fmt_currency(msg['transaction']['actual_amount']) + '</td></tr>\n';
    frm += '<tr><th>Budgeted Amount</th><td>' + fmt_currency(msg['transaction']['budgeted_amount']) + '</td></tr>\n';
    frm += '<tr><th>Description</th><td>' + msg['transaction']['description'] + '</td></tr>\n';
    frm += '<tr><th>Account</th><td><a href="/accounts/' + msg['acct_id'] + '">' + msg['acct_name'] + ' (' + msg['acct_id'] + ')</a></td></tr>\n';
    frm += '<tr><th>Budget</th><td><a href="/budgets/' + msg['transaction']['budget_id'] + '">' + msg['budget_name'] + ' (' + msg['transaction']['budget_id'] + ')</a></td></tr>\n';
    frm += '<tr><th>Notes</th><td>' + msg['transaction']['notes'] + '</td></tr>\n';
    frm += '<tr><th>Scheduled?</th><td>';
    if (msg['transaction']['scheduled_trans_id'] !== null) {
        frm += '<a href="/scheduled/' + msg['transaction']['scheduled_trans_id'] + '">Yes (' + msg['transaction']['scheduled_trans_id'] + ')</a>';
    } else {
        frm += '&nbsp;';
    }
    frm += '</td></tr>\n';
    frm += '</tbody>\n</table>\n</div><!-- /.table-responsive -->\n';
    frm += '</div><!-- /col-lg-6 -->\n';
    if (msg['ofx_trans'] !== null) {
        // OFXTransaction and OFXStatement info
        frm += '<div class="col-lg-6">\n';
        frm += '<div class="table-responsive">\n<table class="table table-bordered table-hover" id="txnReconcileModal-ofx">\n<tbody>\n';
        frm += '<tr><th colspan="2" style="text-align: center;">OFX Transaction</th></tr>\n';
        frm += '<tr><th>Account</th><td><a href="/accounts/' + msg['acct_id'] + '">' + msg['acct_name'] + ' (' + msg['acct_id'] + ')</a></td></tr>\n';
        frm += '<tr><th>FITID</th><td>' + msg['ofx_trans']['fitid'] + '</td></tr>\n';
        frm += '<tr><th>Date Posted</th><td>' + msg['ofx_trans']['date_posted']['ymdstr'] + '</td></tr>\n';
        frm += '<tr><th>Amount</th><td>' + fmt_currency(msg['ofx_trans']['amount']) + '</td></tr>\n';
        frm += '<tr><th>Name</th><td>' + msg['ofx_trans']['name'] + '</td></tr>\n';
        frm += '<tr><th>Memo</th><td>' + fmt_null(msg['ofx_trans']['memo']) + '</td></tr>\n';
        frm += '<tr><th>Type</th><td>' + fmt_null(msg['ofx_trans']['trans_type']) + '</td></tr>\n';
        frm += '<tr><th>Description</th><td>' + fmt_null(msg['ofx_trans']['description']) + '</td></tr>\n';
        frm += '<tr><th>Notes</th><td>' + fmt_null(msg['ofx_trans']['notes']) + '</td></tr>\n';
        frm += '<tr><th>Checknum</th><td>' + fmt_null(msg['ofx_trans']['checknum']) + '</td></tr>\n';
        frm += '<tr><th>MCC</th><td>' + fmt_null(msg['ofx_trans']['mcc']) + '</td></tr>\n';
        frm += '<tr><th>SIC</th><td>' + fmt_null(msg['ofx_trans']['sic']) + '</td></tr>\n';
        frm += '<tr><th colspan="2" style="text-align: center;">OFX Statement</th></tr>\n';
        frm += '<tr><th>ID</th><td>' + fmt_null(msg['ofx_stmt']['id']) + '</td></tr>\n';
        frm += '<tr><th>Date</th><td>' + msg['ofx_stmt']['as_of']['ymdstr'] + '</td></tr>\n';
        frm += '<tr><th>Filename</th><td>' + fmt_null(msg['ofx_stmt']['filename']) + '</td></tr>\n';
        frm += '<tr><th>File mtime</th><td>' + msg['ofx_stmt']['file_mtime']['ymdstr'] + '</td></tr>\n';
        frm += '<tr><th>Ledger Balance</th><td>' + fmt_currency(msg['ofx_stmt']['ledger_bal']) + '</td></tr>\n';
        frm += '</tbody>\n</table>\n</div><!-- /.table-responsive -->\n';
        frm += '</div><!-- /col-lg-6 -->\n';
    } else {
        frm += '<div class="col-lg-6">\n';
        frm += '<p>No OFX Transaction</p>';
        frm += '</div><!-- /col-lg-6 -->\n';
    }
    frm += '</div><!-- /row -->\n';
    frm += '</div><!-- modal content opening div -->\n';
    $('#modalBody').empty();
    $('#modalBody').append(frm);
    $('#modalLabel').text('Transaction Reconcile ' + msg['reconcile']['id']);
    $('#modalSaveButton').hide();
    $("#modalDiv").modal('show');
}

/**
 * Show the TxnReconcile modal popup. This function
 * calls :js:func:`txnReconcileModalDiv` to generate the HTML.
 *
 * @param {number} id - the ID of the TxnReconcile to show a modal for.
 */
function txnReconcileModal(id) {
    $('#modalBody').empty();
    var url = "/ajax/reconcile/" + id;
    $.ajax(url).done(txnReconcileModalDiv);
}