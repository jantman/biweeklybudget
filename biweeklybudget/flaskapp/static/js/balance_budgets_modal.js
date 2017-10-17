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
 * Uses :js:func:`balanceBudgetsDivForm` to generate the form. Uses
 * :js:func:`handleBalanceBudgetsFormSubmitted` as the form submission handler.
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
        var data = serializeForm('balanceBudgetsForm');
        $('.formfeedback').remove();
        $('.has-error').each(function(index) { $(this).removeClass('has-error'); });
        $.ajax({
            type: "POST",
            url: '/forms/balance_budgets/calculate',
            data: data,
            success: function(data) {
                handleBalanceBudgetsFormSubmitted(data, 'modalBody', 'balanceBudgetsForm', false);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                handleFormError(jqXHR, textStatus, errorThrown, 'modalBody', 'balanceBudgetsForm');
            }
        });
    }).show();
    $('#modalLabel').text('Balance Budgets (' + pp_start_date + ')');
    $("#modalDiv").modal('show');
}

/**
 * Form submission handler for :js:func:`balanceBudgetsModal`. On success,
 * empties the modal and passes the server response data to
 * :js:func:`balanceBudgetsConfirmationModal`.
 *
 * This should either display one or more error messages, or call a success
 * callback.
 *
 * @param {Object} data - response data
 * @param {string} container_id - the ID of the modal container on the page
 * @param {string} form_id - the ID of the form on the page
 * @param {Object} dataTableObj - A reference to the DataTable on the page, that
 *   needs to be refreshed. If null, reload the whole page. If a function, call
 *   that function. If false, do nothing.
 */
function handleBalanceBudgetsFormSubmitted(data, container_id, form_id, dataTableObj) {
    if(data.hasOwnProperty('error_message')) {
        $('#' + container_id).prepend(
            '<div class="alert alert-danger formfeedback">' +
            '<strong>Server Error: </strong> ' + data.error_message + '</div>');
    } else if (data.hasOwnProperty('errors')) {
        var form = $('#' + form_id);
        Object.keys(data.errors).forEach(function (key) {
            var elem = form.find('[name=' + key + ']');
            data.errors[key].forEach( function(msg) {
                elem.parent().append('<p class="text-danger formfeedback">' + msg + '</p>');
                elem.parent().addClass('has-error');
            });
        });
    } else {
        $('#' + container_id).empty();
        $('#modalSaveButton').hide();
        balanceBudgetsConfirmationModal(data);
    }
}

/**
 * Generate the HTML for the form on the Confirmation Modal.
 */
function balanceBudgetsConfirmationDivForm(data) {
    var content = '';
    // budgets
    content += '<div class="panel panel-info">' + "\n";
    content += '<div class="panel-heading">Budget Balances</div>' + "\n";
    content += '<div class="table-responsive">' + "\n";
    content += '<table class="table table-bordered">' + "\n";
    content += "<thead><tr><th>Budget</th><th>Before</th><th>After</th></tr></thead>\n";
    content += "<tbody>\n";
    Object.keys(data.budgets).forEach(function (budg_id) {
        content += '<tr>';
        content += '<td>' + budg_id + '</td>';
        content += '<td>' + fmt_currency(data.budgets[budg_id]['before']) + '</td>';
        content += '<td>' + fmt_currency(data.budgets[budg_id]['after']) + '</td>';
        content += "</tr>\n";
    });
    content += '<tr style="font-weight: bold;">';
    content += '<td>' + data.standing_name + ' (' + data.standing_id + ')</td>';
    content += '<td>' + fmt_currency(data.standing_before) + '</td>';
    content += '<td>' + fmt_currency(data.standing_after) + '</td>';
    content += '</tr>' + "\n";
    content += "</tbody></table>\n";
    content += "</div><!-- /table-responsive -->\n";
    content += "</div><!-- /panel -->\n";
    // transfers
    content += '<div class="panel panel-info" style="padding-top: 1em;">' + "\n";
    content += '<div class="panel-heading">Transfers</div>' + "\n";
    content += '<div class="table-responsive">' + "\n";
    content += '<table class="table table-bordered">' + "\n";
    content += "<thead><tr><th>Amount</th><th>From</th><th>To</th></tr></thead>\n";
    content += "<tbody>\n";
    for (var txfr in data.transfers) {
        content += "<tr><td>" + txfr + "</tr></td>\n";
    }
    content += "</tbody></table>\n";
    content += "</div><!-- /table-responsive -->\n";
    content += "</div><!-- /panel -->\n";
    return new FormBuilder('balanceBudgetsConfirmationForm')
        .addHidden('bal_budg_frm_pp_start_date', 'pp_start_date', data.pp_start_date)
        .addHidden('bal_budg_frm_plan_json', 'plan_json', JSON.stringify(data))
        .addHTML(content)
        .render();
}

/**
 * Show the modal popup for balancing budgets for a specified payperiod.
 * Uses :js:func:`balanceBudgetsConfirmationDivForm` to generate the form. Uses
 * :js:func:`handleBalanceBudgetsFormSubmitted` as the form submission handler.
 *
 * @param {string} pp_start_date - The date, as a "yyyy-mm-dd" string, that the
 * pay period to balance starts on.
 */
function balanceBudgetsConfirmationModal(data) {
    console.log("balanceBudgetsConfirmationModal()");
    console.log(data);
    $('#modalBody').empty();
    $('#modalBody').append(balanceBudgetsConfirmationDivForm(data));
    $('#modalSaveButton').off();
    $('#modalSaveButton').html('Confirm');
    $('#modalSaveButton').click(function() {
        var data = serializeForm('balanceBudgetsConfirmationForm');
        $('.formfeedback').remove();
        $('.has-error').each(function(index) { $(this).removeClass('has-error'); });
        $.ajax({
            type: "POST",
            url: '/forms/balance_budgets/confirm',
            data: data,
            success: function(data) {
                handleFormSubmitted(data, 'modalBody', 'balanceBudgetsConfirmationForm', null);
            },
            error: function(jqXHR, textStatus, errorThrown) {
                handleFormError(jqXHR, textStatus, errorThrown, 'modalBody', 'balanceBudgetsConfirmationForm');
            }
        });
    }).show();
    $('#modalLabel').text('Confirm Balance Budgets (' + data.pp_start_date + ')');
    $("#modalDiv").modal('show');
}
