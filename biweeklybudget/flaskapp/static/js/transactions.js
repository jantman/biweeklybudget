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

// for the DataTable
var mytable;

$(document).ready(function() {
    mytable = $('#table-transactions').dataTable({
        processing: true,
        serverSide: true,
        ajax: "/ajax/transactions",
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
                data: "description",
                "render": function(data, type, row) {
                    return $("<div>").append($("<a/>").attr("href", "javascript:transModal(" + row.DT_RowData.id + ", mytable)").text(data)).html();
                }
            },
            {
                data: "account",
                "render": function(data, type, row) {
                    return $("<div>").append($("<a/>").attr("href", "/accounts/" + row.DT_RowData.acct_id).text(data)).html();
                }
            },
            {
                data: "budget",
                "render": function(data, type, row) {
                    return $("<div>").append($("<a/>").attr("href", "/budgets/" + row.DT_RowData.budget_id).text(data)).html();
                }
            },
            {
                data: "scheduled",
                "render": function(data, type, row) {
                    if(data != null) {
                        return $("<div>").append($("<a/>").attr("href", "/scheduled/" + data).text("Yes (" + data + ")")).html();
                    } else {
                        return '&nbsp;';
                    }
                }
            },
            {
                data: "budgeted_amount",
                "render": function(data, type, row) {
                    if(type === "display" || type === "filter") {
                        if(data === row.amount || data === null ) {
                            return '&nbsp';
                        } else {
                            return fmt_currency(data);
                        }
                    } else {
                        return data;
                    }
                }
            },
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
        order: [[ 0, "desc"], [ 1, "asc"]],
        bInfo: true
    });

    $('#table-transactions_length').parent().removeClass('col-sm-6');
    $('#table-transactions_length').parent().addClass('col-sm-3');
    $('#table-transactions_filter').parent().removeClass('col-sm-6');
    $('#table-transactions_filter').parent().addClass('col-sm-3');
    var acctsel = '<div class="col-sm-3"><div id="table-transactions_acct_filter" class="dataTables_length"><label>Account: <select name="account_filter" id="account_filter" class="form-control input-sm" aria-controls="table-transactions">';
    acctsel += '<option value="None" selected="selected"></option>';
    Object.keys(acct_names_to_id).forEach(function (key) {
        acctsel += '<option value="' + acct_names_to_id[key] + '">' + key + '</option>';
    });
    acctsel += '</select></label></div></div>';
    $(acctsel).insertAfter($('#table-transactions_length').parent());
    $('#account_filter').on('change', function() {
        var selectedVal = $(this).val();
        mytable.fnFilter(selectedVal, 3, false);
    });

    var budgsel = '<div class="col-sm-3"><div id="table-transactions_budg_filter" class="dataTables_length"><label>Budget: <select name="budget_filter" id="budget_filter" class="form-control input-sm" aria-controls="table-transactions">';
    budgsel += '<option value="None" selected="selected"></option>';
    Object.keys(budget_names_to_id).forEach(function (key) {
        budgsel += '<option value="' + budget_names_to_id[key] + '">' + key + '</option>';
    });
    budgsel += '</select></label></div></div>';
    $(budgsel).insertAfter($('#table-transactions_length').parent());
    $('#budget_filter').on('change', function() {
        var selectedVal = $(this).val();
        mytable.fnFilter(selectedVal, 4, false);
    });

    $('#btn_add_trans').click(function() {
        transModal(null, mytable);
    });
});
