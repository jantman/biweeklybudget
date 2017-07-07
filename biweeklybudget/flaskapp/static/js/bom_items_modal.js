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
function bomItemModalDivForm() {
    return new FormBuilder('bomItemForm')
        .addHidden('bom_frm_id', 'id', '')
        .addHidden('bom_frm_project_id', 'project_id', project_id)
        .addText('bom_frm_name', 'name', 'Name')
        .addText('bom_frm_notes', 'notes', 'Notes')
        .addText('bom_frm_quantity', 'quantity', 'Quantity')
        .addCurrency('bom_frm_unit_cost', 'unit_cost', 'Unit Cost')
        .addText('bom_frm_url', 'url', 'URL')
        .addCheckbox('bom_frm_active', 'is_active', 'Active?', true)
        .render();
}

/**
 * Ajax callback to fill in the modalDiv with data on a BoM Item.
 */
function bomItemModalDivFillAndShow(msg) {
    $('#modalLabel').text('Edit BoM Item ' + msg['id']);
    $('#bom_frm_id').val(msg['id']);
    $('#bom_frm_project_id').val(msg['project_id']);
    $('#bom_frm_name').val(msg['name']);
    $('#bom_frm_notes').val(msg['notes']);
    $('#bom_frm_quantity').val(msg['quantity']);
    $('#bom_frm_unit_cost').val(msg['unit_cost']);
    $('#bom_frm_url').val(msg['url']);
    if(msg['is_active'] === true) {
        $('#bom_frm_active').prop('checked', true);
    } else {
        $('#bom_frm_active').prop('checked', false);
    }
    $("#modalDiv").modal('show');
}

/**
 * Show the BoM Item modal popup, optionally populated with
 * information for one BoM Item. This function calls
 * :js:func:`bomItemModalDivForm` to generate the form HTML,
 * :js:func:`bomItemModalDivFillAndShow` to populate the form for editing,
 * and :js:func:`handleForm` to handle the Submit action.
 *
 * @param {number} id - the ID of the BoM Item to show a modal for,
 *   or null to show modal to add a new Transaction.
 */
function bomItemModal(id) {
    $('#modalBody').empty();
    $('#modalBody').append(bomItemModalDivForm());
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'bomItemForm', '/forms/bom_item', function() {
            reloadProject();
            mytable.api().ajax.reload();
        });
    }).show();
    if(id) {
        var url = "/ajax/projects/bom_item/" + id;
        $.ajax(url).done(bomItemModalDivFillAndShow);
    } else {
        $('#modalLabel').text('Add New BoM Item');
        $("#modalDiv").modal('show');
    }
}
