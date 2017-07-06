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
 * Reload the top-level project information on the page.
 */
function reloadProject() {
    console.log('reload project');
}

// for the DataTable
var mytable;

$(document).ready(function() {
    mytable = $('#table-items').dataTable({
        processing: true,
        serverSide: true,
        ajax: "/ajax/projects/bom_items/" + project_id,
        columns: [
            {
                data: "name",
                "render": function(data, type, row) {
                    if(type === "display" || type === "filter") {
                        var d = $("<div>");
                        var namespan = $('<span style="float: left;"/>');
                        if(row.url !== null) {
                            namespan.append($("<a/>").attr("href", row.url).text(data));
                        } else {
                            namespan.text(data);;
                        }
                        d.append(namespan);
                        d.append($('<span style="float: right;"/>').append($("<a/>").attr("href", "#").attr("onclick", "bomItemModal(" + row.id + ")").text("(edit)")));
                        return d.html();
                    } else {
                        return data;
                    }
                }
            },
            {
                data: "quantity"
            },
            {
                data: "unit_cost",
                "render": function(data, type, row) {
                    if(type === "display" || type === "filter") {
                        return '$' + data.toString().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,");
                    } else {
                        return data;
                    }
                }
            },
            {
                data: "line_cost",
                "render": function(data, type, row) {
                    if(type === "display" || type === "filter") {
                        return '$' + row.DT_RowData.line_cost.toString().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,");
                    } else {
                        return row.DT_RowData.line_cost;
                    }
                }
            },
            {
                data: "notes"
            },
            {
                data: "is_active",
                "render": function(data, type, row) {
                    if(type === "display" || type === "filter") {
                        if(data === true) {
                            return 'yes';
                        } else {
                            return '<span style="color: #a94442;">NO</span>';
                        }
                    } else {
                        return data;
                    }
                }
            },
            {
                data: "id",
                visible: false
            }
        ],
        order: [[ 5, "desc"], [ 6, "asc"]],
        bInfo: true,
        createdRow: function(row, data, dataIndex) {
            if(data.is_active === false) {
                $(row).addClass('inactive');
            }
        }
    });

    $('#table-items_length').parent().removeClass('col-sm-6');
    $('#table-items_length').parent().addClass('col-sm-4');
    $('#table-items_filter').parent().removeClass('col-sm-6');
    $('#table-items_filter').parent().addClass('col-sm-4');
    $('<div class="col-sm-4"><p><button type="button" class="btn btn-primary" id="btn_add_trans">Add Item</button></p></div>').insertAfter($('#table-items_length').parent());

/*
    $('#btn_add_trans').click(function() {
        transModal(null, mytable);
    });
    */

    reloadProject();
});
