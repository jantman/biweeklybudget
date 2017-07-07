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

/**
 * Handler for when a project is added via the form.
 */
function handleProjectAdded() {
    $('#proj_frm_name').val("");
    $('#proj_frm_notes').val("");
    mytable.api().ajax.reload();
}

/**
 * Handler for links to activate a project.
 */
function activateProject(proj_id) {
    $.ajax({
        type: "POST",
        url: '/forms/projects',
        data: { id: proj_id, action: 'activate'},
        success: function(data) {
            mytable.api().ajax.reload();
        },
        error: function(jqXHR, textStatus, errorThrown) {
            handleFormError(jqXHR, textStatus, errorThrown, container_id, form_id);
            alert('Error submitting form: ' + textStatus + ': ' + jqXHR.status + ' ' + errorThrown);
        }
    });
}

/**
 * Handler for links to deactivate a project.
 */
function deactivateProject(proj_id) {
    $.ajax({
        type: "POST",
        url: '/forms/projects',
        data: { id: proj_id, action: 'deactivate'},
        success: function(data) {
            mytable.api().ajax.reload();
        },
        error: function(jqXHR, textStatus, errorThrown) {
            handleFormError(jqXHR, textStatus, errorThrown, container_id, form_id);
            alert('Error submitting form: ' + textStatus + ': ' + jqXHR.status + ' ' + errorThrown);
        }
    });
}

$(document).ready(function() {
    mytable = $('#table-projects').dataTable({
        processing: true,
        serverSide: true,
        ajax: "/ajax/projects",
        columns: [
            {
                data: "name",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        '<a href="/projects/' + row.DT_RowData.id + '">' + data + '</a>' :
                        data;
                }
            },
            {
                data: "total_cost",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        fmt_currency(data) :
                        data;
                }
            },
            {
                data: "remaining_cost",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        fmt_currency(data) :
                        data;
                }
            },
            {
                data: "is_active",
                "render": function(data, type, row) {
                    if(type !== "display" && type !== "filter") { return data; }
                    if(data === true) {
                        return 'yes <a onclick="deactivateProject(' + row.DT_RowData.id + ');" href="#">(deactivate)</a>';
                    } else {
                        return 'NO <a onclick="activateProject(' + row.DT_RowData.id + ');" href="#">(activate)</a>';
                    }
                }
            },
            { data: "notes" }
        ],
        order: [[3, "desc"], [ 0, "asc"]],
        bInfo: true
    });

    $('#formSaveButton').click(function() {
        handleInlineForm('add_project_frm_div', 'add_project_frm', '/forms/projects', handleProjectAdded);
    });
});
