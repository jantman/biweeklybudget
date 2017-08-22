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
function schedModalDivHandleType() {
    if($('#sched_frm_type_monthly').is(':checked')) {
        $('#sched_frm_day_of_month_group').show();
        $('#sched_frm_num_per_period_group').hide();
        $('#sched_frm_date_group').hide();
    } else if($('#sched_frm_type_per_period').is(':checked')) {
        $('#sched_frm_day_of_month_group').hide();
        $('#sched_frm_num_per_period_group').show();
        $('#sched_frm_date_group').hide();
    } else {
        $('#sched_frm_day_of_month_group').hide();
        $('#sched_frm_num_per_period_group').hide();
        $('#sched_frm_date_group').show();
    }
}

/**
 * Generate the HTML for the form on the Modal
 */
function schedModalDivForm() {
    return new FormBuilder('schedForm')
        .addHidden('sched_frm_id', 'id', '')
        .addText('sched_frm_description', 'description', 'Description')
        .addRadioInline(
            'type',
            'Type',
            [
                { id: 'sched_frm_type_monthly', value: 'monthly', label: 'Monthly', checked: true, inputHtml: 'onchange="schedModalDivHandleType()"' },
                { id: 'sched_frm_type_per_period', value: 'per_period', label: 'Per Period', inputHtml: 'onchange="schedModalDivHandleType()"' },
                { id: 'sched_frm_type_date', value: 'date', label: 'Date', inputHtml: 'onchange="schedModalDivHandleType()"' },
            ]
        )
        .addText(
            'sched_frm_day_of_month',
            'day_of_month',
            'Day of Month',
            {
                groupHtml: 'id="sched_frm_group_monthly"',
                inputHtml: 'size="4" maxlength="2"'
            }
        )
        .addText(
            'sched_frm_num_per_period',
            'num_per_period',
            'Number Per Pay Period',
            {
                groupHtml: 'id="sched_frm_group_num_per_period" style="display: none;"',
                inputHtml: 'size="4" maxlength="2"'
            }
        )
        .addDatePicker('sched_frm_date', 'date', 'Specific Date', { groupHtml: ' style="display: none;"' })
        .addCurrency('sched_frm_amount', 'amount', 'Amount', { helpBlock: 'Transaction amount (positive for expenses, negative for income).' })
        .addLabelToValueSelect('sched_frm_account', 'account', 'Account', acct_names_to_id, 'None', true)
        .addLabelToValueSelect('sched_frm_budget', 'budget', 'Budget', budget_names_to_id, 'None', true)
        .addText('sched_frm_notes', 'notes', 'Notes')
        .addCheckbox('sched_frm_active', 'is_active', 'Active?', true)
        .render();
}

/**
 * Ajax callback to fill in the modalDiv with data on a budget.
 */
function schedModalDivFillAndShow(msg) {
    $('#modalLabel').text('Edit Scheduled Transaction ' + msg['id']);
    $('#sched_frm_id').val(msg['id']);
    $('#sched_frm_description').val(msg['description']);
    if(msg['date'] != null) {
        $('#sched_frm_type_monthly').prop('checked', false);
        $('#sched_frm_type_per_period').prop('checked', false);
        $('#sched_frm_type_date').prop('checked', true);
        $('#sched_frm_date').val(msg['date']['str']);
    } else if(msg['day_of_month'] != null) {
        $('#sched_frm_type_per_period').prop('checked', false);
        $('#sched_frm_type_date').prop('checked', false);
        $('#sched_frm_type_monthly').prop('checked', true);
        $('#sched_frm_day_of_month').val(msg['day_of_month']);
    } else {
        // num_per_period
        $('#sched_frm_type_monthly').prop('checked', false);
        $('#sched_frm_type_date').prop('checked', false);
        $('#sched_frm_type_per_period').prop('checked', true);
        $('#sched_frm_num_per_period').val(msg['num_per_period']);
    }
    schedModalDivHandleType();
    $('#sched_frm_amount').val(msg['amount']);
    $('#sched_frm_account option[value=' + msg['account_id'] + ']').prop('selected', 'selected').change();
    $('#sched_frm_budget option[value=' + msg['budget_id'] + ']').prop('selected', 'selected').change();
    $('#sched_frm_notes').val(msg['notes']);
    if(msg['is_active'] === true) {
        $('#sched_frm_active').prop('checked', true);
    } else {
        $('#sched_frm_active').prop('checked', false);
    }
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
function schedModal(id, dataTableObj) {
    $('#modalBody').empty();
    $('#modalBody').append(schedModalDivForm());
    $('#sched_frm_date_input_group').datepicker({
        todayBtn: "linked",
        autoclose: true,
        todayHighlight: true,
        format: 'yyyy-mm-dd'
    });
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'schedForm', '/forms/scheduled', dataTableObj);
    }).show();
    if(id) {
        var url = "/ajax/scheduled/" + id;
        $.ajax(url).done(schedModalDivFillAndShow);
    } else {
        $('#modalLabel').text('Add New Scheduled Transaction');
        $('#sched_frm_account option[value=' + default_account_id + ']').prop('selected', 'selected').change();
        schedModalDivHandleType();
        $("#modalDiv").modal('show');
    }
}
