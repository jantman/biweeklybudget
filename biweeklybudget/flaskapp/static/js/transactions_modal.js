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
    return new FormBuilder('transForm')
        .addHidden('trans_frm_id', 'id', '')
        .addDatePicker('trans_frm_date', 'date', 'Date')
        .addCurrency('trans_frm_amount', 'amount', 'Amount', { helpBlock: 'Transaction amount (positive for expenses, negative for income).' })
        .addText('trans_frm_description', 'description', 'Description')
        .addLabelToValueSelect('trans_frm_account', 'account', 'Account', acct_names_to_id, 'None', true)
        .addLabelToValueSelect('trans_frm_budget', 'budget', 'Budget', budget_names_to_id, 'None', true)
        .addText('trans_frm_notes', 'notes', 'Notes')
        .addHTML('<p id="trans_frm_transfer_p" style="display: none;"></p>')
        .render();
}

/**
 * Ajax callback to fill in the modalDiv with data on a Transaction.
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
    if(msg['transfer_id'] !== null) {
      $('#trans_frm_transfer_p').html(
        'This transaction is one half of a transfer, along with <a href="javascript:transModal(' +
        msg['transfer_id'] + ', mytable)">Transaction ' + msg['transfer_id'] + '</a>.'
      );
      $('#trans_frm_transfer_p').show();
    }
    $("#modalDiv").modal('show');
}

/**
 * Show the Transaction modal popup, optionally populated with
 * information for one Transaction. This function calls
 * :js:func:`transModalDivForm` to generate the form HTML,
 * :js:func:`transModalDivFillAndShow` to populate the form for editing,
 * and :js:func:`handleForm` to handle the Submit action.
 *
 * @param {number} id - the ID of the Transaction to show a modal for,
 *   or null to show modal to add a new Transaction.
 * @param {(Object|null)} dataTableObj - passed on to :js:func:`handleForm`
 */
function transModal(id, dataTableObj) {
    $('#modalBody').empty();
    $('#modalBody').append(transModalDivForm());
    $('#trans_frm_date').val(isoformat(BIWEEKLYBUDGET_DEFAULT_DATE));
    $('#trans_frm_date_input_group').datepicker({
        todayBtn: "linked",
        autoclose: true,
        todayHighlight: true,
        format: 'yyyy-mm-dd'
    });
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'transForm', '/forms/transaction', dataTableObj);
    }).show();
    if(id) {
        var url = "/ajax/transactions/" + id;
        $.ajax(url).done(transModalDivFillAndShow);
    } else {
        $('#modalLabel').text('Add New Transaction');
        $('#trans_frm_account option[value=' + default_account_id + ']').prop('selected', 'selected').change();
        $("#modalDiv").modal('show');
    }
}
