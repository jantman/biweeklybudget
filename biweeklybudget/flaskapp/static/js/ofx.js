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
 * Show the modal popup, populated with information for one OFX Transaction.
 */
function ofxTransModal(acct_id, fitid) {
    var url = "/ajax/ofx/" + acct_id + "/" + encodeURIComponent(fitid);
    $.ajax(url).done(function( msg ) {
        var modal = $("#modalDiv");
        modal.find('.modal-title').text('OFXTransaction Account=' + acct_id + ' FITID=' + fitid);
        var mbody = $('#modalBody');
        mbody.append('<div class="table-responsive"><table class="table table-bordered table-hover"><tbody></tbody></table></div><!-- /.table-responsive -->');
        var tbody = modal.find('tbody');
        tbody.empty();
        tbody.append('<tr><th>Account</th><td><a href="/accounts/' + msg['acct_id'] + '">' + msg['acct_name'] + ' (' + msg['acct_id'] + ')</a></td></tr>');
        tbody.append('<tr><th>FITID</th><td>' + msg['txn']['fitid'] + '</td></tr>');
        tbody.append('<tr><th>Date Posted</th><td>' + msg['txn']['date_posted']['ymdstr'] + '</td></tr>');
        tbody.append('<tr><th>Amount</th><td>' + fmt_currency(msg['txn']['amount']) + '</td></tr>');
        tbody.append('<tr><th>Name</th><td>' + msg['txn']['name'] + '</td></tr>');
        tbody.append('<tr><th>Memo</th><td>' + fmt_null(msg['txn']['memo']) + '</td></tr>');
        tbody.append('<tr><th>Type</th><td>' + fmt_null(msg['txn']['trans_type']) + '</td></tr>');
        tbody.append('<tr><th>Description</th><td>' + fmt_null(msg['txn']['description']) + '</td></tr>');
        tbody.append('<tr><th>Notes</th><td>' + fmt_null(msg['txn']['notes']) + '</td></tr>');
        tbody.append('<tr><th>Checknum</th><td>' + fmt_null(msg['txn']['checknum']) + '</td></tr>');
        tbody.append('<tr><th>MCC</th><td>' + fmt_null(msg['txn']['mcc']) + '</td></tr>');
        tbody.append('<tr><th>SIC</th><td>' + fmt_null(msg['txn']['sic']) + '</td></tr>');
        tbody.append('<tr><th colspan="2" style="text-align: center;">OFX Statement</th></tr>');
        tbody.append('<tr><th>ID</th><td>' + fmt_null(msg['stmt']['id']) + '</td></tr>');
        tbody.append('<tr><th>Date</th><td>' + msg['stmt']['as_of']['ymdstr'] + '</td></tr>');
        tbody.append('<tr><th>Filename</th><td>' + fmt_null(msg['stmt']['filename']) + '</td></tr>');
        tbody.append('<tr><th>File mtime</th><td>' + msg['stmt']['file_mtime']['ymdstr'] + '</td></tr>');
        tbody.append('<tr><th>Ledger Balance</th><td>' + fmt_currency(msg['stmt']['ledger_bal']) + '</td></tr>');
        $('#modalSaveButton').hide();
        modal.modal('show');
    });
}

$(document).ready(function() {
    var mytable = $('#table-ofx-txn').dataTable({
        processing: true,
        serverSide: true,
        ajax: "/ajax/ofx",
        columns: [
            { data: "date" },
            {
                data: "amount",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        fmt_currency(data) :
                        data;
                }
            },
            {
                data: "account",
                "render": function(data, type, row) {
                    return $("<div>").append($("<a/>").attr("href", "/accounts/" + row.DT_RowData.acct_id).text(data)).html();
                }
            },
            { data: "type" },
            { data: "name" },
            { data: "memo" },
            { data: "description" },
            {
                data: "fitid",
                "render": function(data, type, row) {
                    return $("<div>").append($("<a/>").attr("href", "javascript:ofxTransModal(" + row.DT_RowData.acct_id + ", '" + data + "')").text(data)).html();
                }
            },
            { data: "last_stmt" },
            { data: "last_stmt_date" },
            {
                data: "reconcile_id",
                "render": function(data, type, row) {
                    if(data != null) {
                        return $("<div>").append($("<a/>").attr("href", "javascript:txnReconcileModal(" + data + ")").text("Yes (" + data + ")")).html();
                    } else {
                        return '&nbsp;';
                    }
                }
            }
        ],
        order: [[ 0, "desc"]],
        bInfo: true
    });

    $('#table-ofx-txn_length').parent().removeClass('col-sm-6');
    $('#table-ofx-txn_length').parent().addClass('col-sm-4');
    $('#table-ofx-txn_filter').parent().removeClass('col-sm-6');
    $('#table-ofx-txn_filter').parent().addClass('col-sm-4');
    var acctsel = '<div class="col-sm-4"><div id="table-ofx-txn_acct_filter" class="dataTables_length"><label>Account: <select name="account_filter" id="account_filter" class="form-control input-sm" aria-controls="table-ofx-txn">';
    acctsel += '<option value="None" selected="selected"></option>';
    Object.keys(acct_names_to_id).forEach(function (key) {
        acctsel += '<option value="' + acct_names_to_id[key] + '">' + key + '</option>';
    });
    acctsel += '</select></label></div></div>';
    $(acctsel).insertAfter($('#table-ofx-txn_length').parent());
    $('#account_filter').on('change', function() {
        var selectedVal = $(this).val();
        mytable.fnFilter(selectedVal, 2, false);
    });
});
