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
function budgetModalHandleType() {
    if($('#budget_frm_type_standing').is(':checked')) {
        $('#budget_frm_group_starting_balance').hide();
        $('#budget_frm_group_current_balance').show();
    } else {
        $('#budget_frm_group_current_balance').hide();
        $('#budget_frm_group_starting_balance').show();
    }
}

/**
 * Generate the HTML for the form on the Modal
 */
function budgetModalForm() {
    var frm = '<form role="form">';
    // name
    frm += '<div class="form-group"><label>Name</label><input class="form-control" id="budget_frm_name" name="name"></div>';
    // type
    frm += '<div class="form-group"><label>Type </label> <label class="radio-inline"><input type="radio" name="budget_frm_type" id="budget_frm_type_periodic" value="periodic" onchange="budgetModalHandleType()" checked>Periodic</label><label class="radio-inline"><input type="radio" name="budget_frm_type" id="budget_frm_type_standing" value="standing" onchange="budgetModalHandleType()">Standing</label></div>';
    // description
    frm += '<div class="form-group"><label>Description</label><input class="form-control" id="budget_frm_description" name="description"></div>';
    // starting balance (for periodic)
    frm += '<div class="form-group" id="budget_frm_group_starting_balance"><label>Starting Balance</label><input type="text" class="form-control" id="budget_frm_starting_balance" name="starting_balance"></div>';
    // current balance (for standing)
    frm += '<div class="form-group" id="budget_frm_group_current_balance" style="display: none;"><label>Current Balance</label><input type="text" class="form-control" id="budget_frm_current_balance" name="current_balance"></div>';
    // is_active checkbox
    frm += '<div class="form-group"><label class="checkbox-inline"><input type="checkbox" id="budget_frm_active" name="active" checked> Active?</label>';
    // account_id (select)
    frm += '<div class="form-group"><label>Account</label><select class="form-control" id="budget_frm_account" name="account">';
    frm += '<option value="None" selected="selected"></option>';
    Object.keys(acct_names_to_id).forEach(function (key) {
        frm += '<option value="' + acct_names_to_id[key] + '">' + key + '</option>';
    });
    frm += '</select></div>';
    frm += '</form>';
    return frm;
}

/**
 * Ajax callback to fill in the budgetModal with data on a budget.
 */
function budgetModalFillAndShow(msg) {
    $('#budgetModalLabel').text('Edit Budget ' + msg['id']);
    $('#budget_frm_name').val(msg['name']);
    if(msg['is_periodic'] === true) {
        $('#budget_frm_type_periodic').prop('checked', true);
    } else {
        $('#budget_frm_type_standing').prop('checked', true);
    }
    budgetModalHandleType();
    $('#budget_frm_description').val(msg['description']);
    $('#budget_frm_starting_balance').val(msg['starting_balance']);
    $('#budget_frm_current_balance').val(msg['current_balance']);
    if(msg['is_active'] === true) {
        $('#budget_frm_active').prop('checked', true);
    } else {
        $('#budget_frm_active').prop('checked', false);
    }
    $('#budget_frm_account option[value="' + msg['account_id'] + '"]').prop('selected', 'selected');
    $("#budgetModal").modal('show');
}

/**
 * Show the modal popup, populated with information for one Budget.
 */
function budgetModal(id) {
    $('#budgetModalBody').empty();
    $('#budgetModalBody').append(budgetModalForm());
    if(id) {
        var url = "/ajax/budget/" + id;
        $.ajax(url).done(budgetModalFillAndShow);
    } else {
        $('#budgetModalLabel').text('Add New Budget');
        $("#budgetModal").modal('show');
    }
}
