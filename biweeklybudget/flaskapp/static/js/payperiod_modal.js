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
    var frm = '<form role="form" id="schedToTransForm">';
    // id
    frm += '<input type="hidden" id="schedtotrans_frm_id" name="id" value="">\n';
    // payperiod
    frm += '<input type="hidden" id="schedtotrans_frm_pp_date" name="payperiod_start_date" value="">\n';
    // date
    frm += '<div class="form-group" id="schedtotrans_frm_group_date">';
    frm += '<label for="schedtotrans_frm_date" class="control-label">Date</label><div class="input-group date" id="schedtotrans_frm_group_date_input"><span class="input-group-addon"><i class="fa fa-calendar fa-fw"></i></span><input class="form-control" id="schedtotrans_frm_date" name="date" type="text" size="12" maxlength="10"></div>';
    frm += '</div>\n';
    // amount
    frm += '<div class="form-group"><label for="schedtotrans_frm_amount" class="control-label">Amount</label><div class="input-group"><span class="input-group-addon">$</span><input type="text" class="form-control" id="schedtotrans_frm_amount" name="amount"></div></div>\n';
    // description
    frm += '<div class="form-group"><label for="schedtotrans_frm_description" class="control-label">Description</label><input class="form-control" id="schedtotrans_frm_description" name="description" type="text"></div>\n';
    // notes
    frm += '<div class="form-group"><label for="schedtotrans_frm_notes" class="control-label">Notes</label><input class="form-control" id="schedtotrans_frm_notes" name="notes" type="text"></div>\n';
    frm += '</form>\n';
    return frm;
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
    $('#schedtotrans_frm_date').val(isoformat(new Date()));
    $('#schedtotrans_frm_group_date_input').datepicker({
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
