/*
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2017 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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
function schedToTransModalDivForm() {
    return new FormBuilder('schedToTransForm')
        .addHidden('schedtotrans_frm_id', 'id', '')
        .addHidden('schedtotrans_frm_pp_date', 'payperiod_start_date', '')
        .addDatePicker('schedtotrans_frm_date', 'date', 'Date')
        .addCurrency('schedtotrans_frm_amount', 'amount', 'Amount')
        .addText('schedtotrans_frm_description', 'description', 'Description')
        .addText('schedtotrans_frm_notes', 'notes', 'Notes')
        .render();
}

/**
 * Ajax callback to fill in the modalDiv with data on a budget.
 */
function schedToTransModalDivFillAndShow(msg) {
    console.log(msg);
    $('#modalLabel').text('Scheduled Transaction ' + msg['id'] + ' to Transaction');
    $('#schedtotrans_frm_id').val(msg['id']);
    $('#schedtotrans_frm_description').val(msg['description']);
    if (msg['date'] != null) {
      $('#schedtotrans_frm_date').val(msg['date']['str']);
    }
    $('#schedtotrans_frm_amount').val(msg['amount']);
    $('#schedtotrans_frm_notes').val(msg['notes']);
    $("#modalDiv").modal('show');
}

/**
 * Show the Scheduled Transaction to Transaction modal popup. This function
 * calls :js:func:`schedToTransModalDivForm` to generate the form HTML,
 * :js:func:`schedToTransModalDivFillAndShow` to populate the form for editing,
 * and :js:func:`handleForm` to handle the Submit action.
 *
 * @param {number} id - the ID of the ScheduledTransaction to show a modal for.
 * @param {string} payperiod_start_date - The Y-m-d starting date of the pay
 *  period.
 */
function schedToTransModal(id, payperiod_start_date) {
    $('#modalBody').empty();
    $('#modalBody').append(schedToTransModalDivForm());
    $('#schedtotrans_frm_date').val(isoformat(BIWEEKLYBUDGET_DEFAULT_DATE));
    $('#schedtotrans_frm_date_input_group').datepicker({
        todayBtn: "linked",
        autoclose: true,
        todayHighlight: true,
        format: 'yyyy-mm-dd'
    });
    $('#schedtotrans_frm_pp_date').val(payperiod_start_date);
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm(
          'modalBody', 'schedToTransForm', '/forms/sched_to_trans', null
        );
    }).show();
    var url = "/ajax/scheduled/" + id;
    $.ajax(url).done(schedToTransModalDivFillAndShow);
}

/**
 * Generate the HTML for the form on the Modal
 */
function skipSchedTransModalDivForm() {
    return new FormBuilder('skipSchedTransForm')
        .addHidden('skipschedtrans_frm_id', 'id', '')
        .addHidden('skipschedtrans_frm_pp_date', 'payperiod_start_date', '')
        .addText('skipschedtrans_frm_description', 'description', 'Description')
        .addRadioInline(
            'type',
            'Type',
            [
                { id: 'skipschedtrans_frm_type_monthly', value: 'monthly', label: 'Monthly', checked: true, inputHtml: 'onchange="schedModalDivHandleType()"' },
                { id: 'skipschedtrans_frm_type_per_period', value: 'per_period', label: 'Per Period', inputHtml: 'onchange="schedModalDivHandleType()"' },
                { id: 'skipschedtrans_frm_type_date', value: 'date', label: 'Date', inputHtml: 'onchange="schedModalDivHandleType()"' },
            ]
        )
        .addText(
            'skipschedtrans_frm_day_of_month',
            'day_of_month',
            'Day of Month',
            {
                groupHtml: 'id="skipschedtrans_frm_group_monthly"',
                inputHtml: 'size="4" maxlength="2"'
            }
        )
        .addText(
            'skipschedtrans_frm_num_per_period',
            'num_per_period',
            'Number Per Pay Period',
            {
                groupHtml: 'id="skipschedtrans_frm_group_num_per_period" style="display: none;"',
                inputHtml: 'size="4" maxlength="2"'
            }
        )
        .addDatePicker('skipschedtrans_frm_date', 'date', 'Specific Date', { groupHtml: ' style="display: none;"' })
        .addCurrency('skipschedtrans_frm_amount', 'amount', 'Amount', { helpBlock: 'Transaction amount (positive for expenses, negative for income).' })
        .addLabelToValueSelect('skipschedtrans_frm_account', 'account', 'Account', acct_names_to_id, 'None', true)
        .addLabelToValueSelect('skipschedtrans_frm_budget', 'budget', 'Budget', budget_names_to_id, 'None', true)
        .addText('skipschedtrans_frm_notes', 'notes', 'Notes')
        .render();
}

/**
 * Ajax callback to fill in the modalDiv with data on a budget.
 */
function skipSchedTransModalDivFillAndShow(msg) {
    console.log(msg);
    $('#modalLabel').text('Skip Scheduled Transaction ' + msg['id'] + ' in period ' + $('#skipschedtrans_frm_pp_date').val());
    $('#skipschedtrans_frm_id').val(msg['id']);
    $('#skipschedtrans_frm_description').val(msg['description']);
    $('#skipschedtrans_frm_description').prop('disabled', true);
    if(msg['date'] != null) {
        $('#skipschedtrans_frm_type_monthly').prop('checked', false);
        $('#skipschedtrans_frm_type_per_period').prop('checked', false);
        $('#skipschedtrans_frm_type_date').prop('checked', true);
        $('#skipschedtrans_frm_date').val(msg['date']['str']);
    } else if(msg['day_of_month'] != null) {
        $('#skipschedtrans_frm_type_per_period').prop('checked', false);
        $('#skipschedtrans_frm_type_date').prop('checked', false);
        $('#skipschedtrans_frm_type_monthly').prop('checked', true);
        $('#skipschedtrans_frm_day_of_month').val(msg['day_of_month']);
    } else {
        // num_per_period
        $('#skipschedtrans_frm_type_monthly').prop('checked', false);
        $('#skipschedtrans_frm_type_date').prop('checked', false);
        $('#skipschedtrans_frm_type_per_period').prop('checked', true);
        $('#skipschedtrans_frm_num_per_period').val(msg['num_per_period']);
    }
    // schedModalDivHandleType()
    if($('#skipschedtrans_frm_type_monthly').is(':checked')) {
        $('#skipschedtrans_frm_group_monthly').show();
        $('#skipschedtrans_frm_group_num_per_period').hide();
        $('#skipschedtrans_frm_date_group').hide();
    } else if($('#skipschedtrans_frm_type_per_period').is(':checked')) {
        $('#skipschedtrans_frm_group_monthly').hide();
        $('#skipschedtrans_frm_group_num_per_period').show();
        $('#skipschedtrans_frm_date_group').hide();
    } else {
        $('#skipschedtrans_frm_group_monthly').hide();
        $('#skipschedtrans_frm_group_num_per_period').hide();
        $('#skipschedtrans_frm_date_group').show();
    }
    // END schedModalDivHandleType()
    // disable date inputs
    $('#skipschedtrans_frm_type_monthly').prop('disabled', true);
    $('#skipschedtrans_frm_type_per_period').prop('disabled', true);
    $('#skipschedtrans_frm_type_date').prop('disabled', true);
    $('#skipschedtrans_frm_date').prop('disabled', true);
    $('#skipschedtrans_frm_day_of_month').prop('disabled', true);
    $('#skipschedtrans_frm_num_per_period').prop('disabled', true);
    // end disable date inputs
    $('#skipschedtrans_frm_amount').val(msg['amount']);
    $('#skipschedtrans_frm_amount').prop('disabled', true);
    $('#skipschedtrans_frm_account option[value=' + msg['account_id'] + ']').prop('selected', 'selected').change();
    $('#skipschedtrans_frm_account').prop('disabled', true);
    $('#skipschedtrans_frm_budget option[value=' + msg['budget_id'] + ']').prop('selected', 'selected').change();
    $('#skipschedtrans_frm_budget').prop('disabled', true);
    $("#modalDiv").modal('show');
}

/**
 * Show the Skip Scheduled Transaction modal popup. This function
 * calls :js:func:`skipSchedTransModalDivForm` to generate the form HTML,
 * :js:func:`skipSchedTransModalDivFillAndShow` to populate the form for
 * editing, and :js:func:`handleForm` to handle the Submit action.
 *
 * @param {number} id - the ID of the ScheduledTransaction to show a modal for.
 * @param {string} payperiod_start_date - The Y-m-d starting date of the pay
 *  period.
 */
function skipSchedTransModal(id, payperiod_start_date) {
    $('#modalBody').empty();
    $('#modalBody').append(skipSchedTransModalDivForm());
    $('#skipschedtrans_frm_date_input_group').datepicker({
        todayBtn: "linked",
        autoclose: true,
        todayHighlight: true,
        format: 'yyyy-mm-dd'
    });
    $('#skipschedtrans_frm_pp_date').val(payperiod_start_date);
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm(
          'modalBody', 'skipSchedTransForm', '/forms/skip_sched_trans', null
        );
    }).show();
    var url = "/ajax/scheduled/" + id;
    $.ajax(url).done(skipSchedTransModalDivFillAndShow);
}
