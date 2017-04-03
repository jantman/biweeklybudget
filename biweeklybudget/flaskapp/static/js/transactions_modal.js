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
function transModalDivForm() {
    var frm = '<form role="form" id="transForm">';
    // id
    frm += '<input type="hidden" id="trans_frm_id" name="id" value="">\n';
    // date
    frm += '<div class="form-group" id="trans_frm_group_date">';
    frm += '<label for="trans_frm_date" class="control-label">Date</label><div class="input-group date" id="trans_frm_group_date_input"><span class="input-group-addon"><i class="fa fa-calendar fa-fw"></i></span><input class="form-control" id="trans_frm_date" name="date" type="text" size="12" maxlength="10"></div>';
    frm += '</div>\n';
    // amount
    frm += '<div class="form-group"><label for="trans_frm_amount" class="control-label">Amount</label><div class="input-group"><span class="input-group-addon">$</span><input type="text" class="form-control" id="trans_frm_amount" name="amount"></div></div>\n';
    // description
    frm += '<div class="form-group"><label for="trans_frm_description" class="control-label">Description</label><input class="form-control" id="trans_frm_description" name="description" type="text"></div>\n';
    // account
    frm += '<div class="form-group"><label for="trans_frm_account" class="control-label">Account</label>';
    frm += '<select id="trans_frm_account" name="account" class="form-control">';
    frm += '<option value="None" selected="selected"></option>';
    Object.keys(acct_names_to_id).forEach(function (key) {
        frm += '<option value="' + acct_names_to_id[key] + '">' + key + '</option>';
    });
    frm += '</select>';
    frm += '</div>\n';
    // budget
    frm += '<div class="form-group"><label for="trans_frm_budget" class="control-label">Budget</label>';
    frm += '<select id="trans_frm_budget" name="budget" class="form-control">';
    frm += '<option value="None" selected="selected"></option>';
    Object.keys(budget_names_to_id).forEach(function (key) {
        frm += '<option value="' + budget_names_to_id[key] + '">' + key + '</option>';
    });
    frm += '</select>';
    frm += '</div>\n';
    // notes
    frm += '<div class="form-group"><label for="trans_frm_notes" class="control-label">Notes</label><input class="form-control" id="trans_frm_notes" name="notes" type="text"></div>\n';
    frm += '</form>\n';
    return frm;
}

/**
 * Ajax callback to fill in the modalDiv with data on a budget.
 */
function transModalDivFillAndShow(msg) {
    $('#modalLabel').text('Edit Transaction ' + msg['id']);
    $('#trans_frm_id').val(msg['id']);
    $('#trans_frm_description').val(msg['description']);
    $('#trans_frm_date').val(msg['date']['str']);
    $('#trans_frm_amount').val(msg['actual_amount']);
    $('#trans_frm_account option[value=' + msg['account_id'] + ']').prop('selected', 'selected').change();
    $('#trans_frm_budget option[value=' + msg['budget_id'] + ']').prop('selected', 'selected').change();
    $('#trans_frm_notes').val(msg['notes']);
    $("#modalDiv").modal('show');
}

/**
 * Show the ScheduledTransaction modal popup, optionally populated with
 * information for one ScheduledTransaction. This function calls
 * :js:func:`schedModalDivForm` to generate the form HTML,
 * :js:func:`schedModalDivFillAndShow` to populate the form for editing,
 * and :js:func:`handleForm` to handle the Submit action.
 *
 * @param {number} id - the ID of the ScheduledTransaction to show a modal for,
 *   or null to show modal to add a new ScheduledTransaction.
 * @param {(Object|null)} dataTableObj - passed on to :js:func:`handleForm`
 */
function transModal(id, dataTableObj) {
    $('#modalBody').empty();
    $('#modalBody').append(transModalDivForm());
    $('#trans_frm_date').val(isoformat(new Date()));
    $('#trans_frm_group_date_input').datepicker({
        todayBtn: "linked",
        autoclose: true,
        todayHighlight: true,
        format: 'yyyy-mm-dd'
    });
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'transForm', '/forms/transaction', dataTableObj);
    }).show();
    if(id) {
        var url = "/ajax/transactions/" + id;
        $.ajax(url).done(transModalDivFillAndShow);
    } else {
        $('#modalLabel').text('Add New Transaction');
        $("#modalDiv").modal('show');
    }
}
