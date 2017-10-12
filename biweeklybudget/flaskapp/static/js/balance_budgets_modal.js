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
function balanceBudgetsDivForm() {
    return new FormBuilder('balanceBudgetsForm')
        .addHidden('bal_budg_frm_pp_start_date', 'pp_start_date', '')
        .addLabelToValueSelect('bal_budg_frm_standing_budget', 'standing_budget', 'Standing Source/Destination Budget', standing_name_to_id, 'None', true)
        .render();
}

/**
 * Show the modal popup for balancing budgets for a specified payperiod.
 * Uses :js:func:`balanceBudgetsDivForm` to generate the form.
 *
 * @param {string} pp_start_date - The date, as a "yyyy-mm-dd" string, that the
 * pay period to balance starts on.
 */
function balanceBudgetsModal(pp_start_date) {
    $('#modalBody').empty();
    $('#modalBody').append(balanceBudgetsDivForm());
    $('#bal_budg_frm_pp_start_date').val(pp_start_date);
    $('#modalSaveButton').off();
    $('#modalSaveButton').html('Calculate');
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'balanceBudgetsForm', '/forms/balance_budgets/calculate', null);
    }).show();
    $('#modalLabel').text('Balance Budgets (' + pp_start_date + ')');
    $("#modalDiv").modal('show');
}
