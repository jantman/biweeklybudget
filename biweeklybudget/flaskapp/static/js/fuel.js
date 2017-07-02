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
 * Generate the HTML for the form on the Modal
 */
function fuelModalDivForm() {
    return new FormBuilder('fuelLogForm')
        .addHidden('trans_frm_id', 'id', '')
        .addDatePicker('trans_frm_date', 'date', 'Date')
        .addCurrency('trans_frm_amount', 'amount', 'Amount', { helpBlock: 'Transaction amount (positive for expenses, negative for income).' })
        .addText('trans_frm_description', 'description', 'Description')
        .addLabelToValueSelect('trans_frm_account', 'account', 'Account', acct_names_to_id, 'None', true)
        .addLabelToValueSelect('trans_frm_budget', 'budget', 'Budget', budget_names_to_id, 'None', true)
        .addText('trans_frm_notes', 'notes', 'Notes')
        .render();
}

/**
 * Show the modal to add a fuel log entry. This function calls
 * :js:func:`fuelModalDivForm` to generate the form HTML,
 * :js:func:`schedModalDivFillAndShow` to populate the form for editing,
 * and :js:func:`handleForm` to handle the Submit action.
 *
 * @param {(Object|null)} dataTableObj - passed on to :js:func:`handleForm`
 */
function fuelLogModal(dataTableObj) {
    $('#modalBody').empty();
    $('#modalBody').append(fuelModalDivForm());
    $('#trans_frm_date').val(isoformat(new Date()));
    $('#trans_frm_date_input_group').datepicker({
        todayBtn: "linked",
        autoclose: true,
        todayHighlight: true,
        format: 'yyyy-mm-dd'
    });
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'fuelLogForm', '/forms/fuel', dataTableObj);
    }).show();
    $('#trans_frm_account option[value=' + default_account_id + ']').prop('selected', 'selected').change();
    $('#modalLabel').text('Add Fuel Fill');
    $("#modalDiv").modal('show');
}

/**
 * Generate the HTML for the form on the Modal
 */
function vehicleModalDivForm() {
    return new FormBuilder('vehicleForm')
        .addHidden('vehicle_frm_id', 'id', '')
        .addText('vehicle_frm_name', 'name', 'Name')
        .addCheckbox('vehicle_frm_active', 'is_active', 'Active?', true)
        .render();
}

/**
 * Ajax callback to fill in the modalDiv with data on a Vehicle.
 */
function vehicleModalDivFillAndShow(msg) {
    $('#modalLabel').text('Edit Vehicle ' + msg['id']);
    $('#vehicle_frm_id').val(msg['id']);
    $('#vehicle_frm_name').val(msg['name']);
    if(msg['is_active'] === true) {
        $('#vehicle_frm_active').prop('checked', true);
    } else {
        $('#vehicle_frm_active').prop('checked', false);
    }
    $("#modalDiv").modal('show');
}

/**
 * Show the Vehicle modal popup, optionally populated with
 * information for one Vehicle. This function calls
 * :js:func:`vehicleModalDivForm` to generate the form HTML,
 * :js:func:`vehicleModalDivFillAndShow` to populate the form for editing,
 * and :js:func:`handleForm` to handle the Submit action.
 *
 * @param {number} id - the ID of the Vehicle to show a modal for,
 *   or null to show modal to add a new Vehicle.
 */
function vehicleModal(id) {
    $('#modalBody').empty();
    $('#modalBody').append(vehicleModalDivForm());
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'vehicleForm', '/forms/vehicle', null);
    }).show();
    if(id) {
        var url = "/ajax/vehicle/" + id;
        $.ajax(url).done(vehicleModalDivFillAndShow);
    } else {
        $('#modalLabel').text('Add New Vehicle');
        $("#modalDiv").modal('show');
    }
}

// for the DataTable
var mytable;

$(document).ready(function() {
    mytable = $('#table-fuel-log').dataTable({
        processing: true,
        serverSide: true,
        ajax: "/ajax/fuelLog",
        columns: [
            { data: "date" },
            {
                data: "vehicle",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        data + ' (' + row.DT_RowData.vehicle_id + ')'
                        : data;
                }
            },
            {
                data: "odometer_miles",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        data.toString().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,") :
                        data;
                }
            },
            { data: "reported_miles" },
            { data: "calculated_miles" },
            {
                data: "level_before",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        data.toString() + '%' : data;
                }
            },
            {
                data: "level_after",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        data.toString() + '%' : data;
                }
            },
            { data: "fill_location" },
            {
                data: "cost_per_gallon",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        '$' + data.toString().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,") :
                        data;
                }
            },
            {
                data: "total_cost",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        '$' + data.toString().replace(/(\d)(?=(\d\d\d)+(?!\d))/g, "$1,") :
                        data;
                }
            },
            {
                data: "gallons",
                "render": function(data, type, row) {
                    return type === "display" || type === "filter" ?
                        data.toFixed(3) :
                        data;
                }
            },
            { data: "reported_mpg" },
            { data: "calculated_mpg" },
            { data: "notes" }
        ],
        order: [[ 0, "desc"], [ 1, "asc"]],
        bInfo: true
    });

    $('#table-fuel-log_length').parent().removeClass('col-sm-6');
    $('#table-fuel-log_length').parent().addClass('col-sm-4');
    $('#table-fuel-log_filter').parent().removeClass('col-sm-6');
    $('#table-fuel-log_filter').parent().addClass('col-sm-4');
    var vehsel = '<div class="col-sm-4"><div id="table-fuel-log_veh_filter" class="dataTables_length"><label>Vehicle: <select name="vehicle_filter" id="vehicle_filter" class="form-control input-sm" aria-controls="table-fuel-log">';
    vehsel += '<option value="None" selected="selected"></option>';
    Object.keys(vehicles).forEach(function (key) {
        if( vehicles[key].is_active == "True" ) {
            vehsel += '<option value="' + key + '">' + vehicles[key].name + '</option>';
        }
    });
    vehsel += '</select></label></div></div>';
    $(vehsel).insertAfter($('#table-fuel-log_length').parent());
    $('#vehicle_filter').on('change', function() {
        var selectedVal = $(this).val();
        mytable.fnFilter(selectedVal, 1, false);
    });

    $('#btn-add-fuel').click(function() {
        fuelLogModal(mytable);
    });

    $('#btn-add-vehicle').click(function() {
        vehicleModal(null);
    });
});
