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
 * Handle change of the "Type" radio buttons on the modal
 */
function budgetModalDivHandleType() {
    if($('#budget_frm_type_standing').is(':checked')) {
        $('#budget_frm_starting_balance_group').hide();
        $('#budget_frm_current_balance_group').show();
    } else {
        $('#budget_frm_current_balance_group').hide();
        $('#budget_frm_starting_balance_group').show();
    }
}

/**
 * Generate the HTML for the form on the Modal
 */
function budgetModalDivForm() {
    return new FormBuilder('budgetForm')
        .addHidden('budget_frm_id', 'id', '')
        .addText('budget_frm_name', 'name', 'Name')
        .addRadioInline(
            'is_periodic',
            'Type',
            [
                { id: 'budget_frm_type_periodic', label: 'Periodic', value: 'true', inputHtml: 'onchange="budgetModalDivHandleType()"', checked: true },
                { id: 'budget_frm_type_standing', label: 'Standing', value: 'false', inputHtml: 'onchange="budgetModalDivHandleType()"' }
            ]
        )
        .addText('budget_frm_description', 'description', 'Description')
        .addCurrency('budget_frm_starting_balance', 'starting_balance', 'Starting Balance')
        .addCurrency('budget_frm_current_balance', 'current_balance', 'Current Balance', { groupHtml: 'style="display: none;"' })
        .addCheckbox('budget_frm_active', 'is_active', 'Active?', true)
        .addCheckbox('budget_frm_income', 'is_income', 'Income?')
        .addCheckbox('budget_frm_omit_from_graphs', 'omit_from_graphs', 'Omit from graphs?')
        .render();
}

/**
 * Ajax callback to fill in the modalDiv with data on a budget.
 * Callback for ajax call in :js:func:`budgetModal`.
 */
function budgetModalDivFillAndShow(msg) {
    $('#modalLabel').text('Edit Budget ' + msg['id']);
    $('#budget_frm_id').val(msg['id']);
    $('#budget_frm_name').val(msg['name']);
    if(msg['is_periodic'] === true) {
        $('#budget_frm_type_standing').prop('checked', false);
        $('#budget_frm_type_periodic').prop('checked', true);
    } else {
        $('#budget_frm_type_periodic').prop('checked', false);
        $('#budget_frm_type_standing').prop('checked', true);
    }
    budgetModalDivHandleType();
    $('#budget_frm_description').val(msg['description']);
    $('#budget_frm_starting_balance').val(msg['starting_balance']);
    $('#budget_frm_current_balance').val(msg['current_balance']);
    if(msg['is_active'] === true) {
        $('#budget_frm_active').prop('checked', true);
    } else {
        $('#budget_frm_active').prop('checked', false);
    }
    if(msg['is_income'] === true) {
        $('#budget_frm_income').prop('checked', true);
    } else {
        $('#budget_frm_income').prop('checked', false);
    }
    if(msg['omit_from_graphs'] === true) {
        $('#budget_frm_omit_from_graphs').prop('checked', true);
    } else {
        $('#budget_frm_omit_from_graphs').prop('checked', false);
    }
    $("#modalDiv").modal('show');
}

/**
 * Show the modal popup, populated with information for one Budget.
 * Uses :js:func:`budgetModalDivFillAndShow` as ajax callback.
 *
 * @param {number} id - the ID of the Budget to show modal for, or null to
 *   show a modal to add a new Budget.
 * @param {(Object|null)} dataTableObj - passed on to ``handleForm()``
 */
function budgetModal(id, dataTableObj) {
    $('#modalBody').empty();
    $('#modalBody').append(budgetModalDivForm());
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'budgetForm', '/forms/budget', dataTableObj);
    }).show();
    if(id) {
        var url = "/ajax/budget/" + id;
        $.ajax(url).done(budgetModalDivFillAndShow);
    } else {
        $('#modalLabel').text('Add New Budget');
        $("#modalDiv").modal('show');
    }
}
