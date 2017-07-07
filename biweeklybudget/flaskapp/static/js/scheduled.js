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
    mytable = $('#table-scheduled-txn').dataTable({
        processing: true,
        serverSide: true,
        ajax: "/ajax/scheduled",
        columns: [
            {
                data: "is_active",
                "render": function(data, type, row) {
                    if (type === "display" || type === "filter") {
                        if (data === false) {
                            return '<span style="color: #a94442;">NO</span>';
                        }
                        return 'yes';
                    }
                    return data;
                }
            },
            { data: "schedule_type" },
            { data: "recurrence_str" },
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
                    return $("<div>").append($("<a/>").attr("href", "javascript:schedModal(" + row.DT_RowData.id + ", mytable)").text(data)).html();
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
            }
        ],
        order: [[ 0, "desc"], [ 1, "desc"], [2, "asc"], [3, "asc"]],
        bInfo: true,
        "fnRowCallback": function(nRow, aData, iDisplayIndex, iDisplayIndexFull) {
            if(aData.is_active === false) {
                $(nRow).addClass('inactive');
            }
        }
    });

    $('#table-scheduled-txn_length').parent().removeClass('col-sm-6');
    $('#table-scheduled-txn_length').parent().addClass('col-sm-4');
    $('#table-scheduled-txn_filter').parent().removeClass('col-sm-6');
    $('#table-scheduled-txn_filter').parent().addClass('col-sm-4');
    var acctsel = '<div class="col-sm-4"><div id="table-scheduled-txn_acct_filter" class="dataTables_length"><label>Type: <select name="type_filter" id="type_filter" class="form-control input-sm" aria-controls="table-scheduled-txn"><option value="None" selected="selected"></option><option value="date">Date</option><option value="monthly">Monthly</option><option value="per period">Per Period</option>';
    acctsel += '</select></label></div></div>';
    $(acctsel).insertAfter($('#table-scheduled-txn_length').parent());
    $('#type_filter').on('change', function() {
        var selectedVal = $(this).val();
        mytable.fnFilter(selectedVal, 1, false);
    });

    $('#btn_add_sched').click(function() {
        schedModal(null, mytable);
    });
});
