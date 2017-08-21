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
function budgetTransferDivForm() {
    return new FormBuilder('budgetTransferForm')
        .addDatePicker('budg_txfr_frm_date', 'date', 'Date')
        .addCurrency('budg_txfr_frm_amount', 'amount', 'Amount', { helpBlock: 'Transfer amount relative to from account; must be positive.' })
        .addLabelToValueSelect('budg_txfr_frm_account', 'account', 'Account', acct_names_to_id, 'None', true)
        .addLabelToValueSelect('budg_txfr_frm_from_budget', 'from_budget', 'From Budget', budget_names_to_id, 'None', true)
        .addLabelToValueSelect('budg_txfr_frm_to_budget', 'to_budget', 'To Budget', budget_names_to_id, 'None', true)
        .addText('budg_txfr_frm_notes', 'notes', 'Notes')
        .render();
}

/**
 * Show the modal popup for transferring between budgets.
 * Uses :js:func:`budgetTransferDivForm` to generate the form.
 *
 * @param {string} txfr_date - The date, as a "yyyy-mm-dd" string, to default
 *  the form to. If null or undefined, will default to
 *  ``BIWEEKLYBUDGET_DEFAULT_DATE``.
 */
function budgetTransferModal(txfr_date) {
    if (txfr_date === undefined || txfr_date === null) {
      txfr_date = isoformat(BIWEEKLYBUDGET_DEFAULT_DATE);
    }
    $('#modalBody').empty();
    $('#modalBody').append(budgetTransferDivForm());
    $('#budg_txfr_frm_date').val(txfr_date);
    $('#budg_txfr_frm_date_input_group').datepicker({
        todayBtn: "linked",
        autoclose: true,
        todayHighlight: true,
        format: 'yyyy-mm-dd'
    });
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'budgetTransferForm', '/forms/budget_transfer', null);
    }).show();
    $('#modalLabel').text('Budget Transfer');
    $('#budg_txfr_frm_account option[value=' + default_account_id + ']').prop('selected', 'selected').change();
    $("#modalDiv").modal('show');
}
