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

var validation_count = 0; // helper for acceptance testing of validation logic

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
        .addCheckbox(
            'trans_frm_is_split', 'is_split', 'Budget Split?', false,
            { inputHtml: 'onchange="transModalHandleSplit()"' }
        )
        .addHTML('<div id="budgets-error-div-container"><div id="budgets-error-div" name="budgets"></div></div>')
        .addLabelToValueSelect('trans_frm_budget', 'budget', 'Budget', active_budget_names_to_id, 'None', true)
        .addHTML(
            '<div id="trans_frm_split_budget_container" style="display: none;">' +
            '<p style="font-weight: 700; margin-bottom: 5px;">Budgets</p>' +
            '<div id="trans_frm_budget_splits_div">' +
            transModalBudgetSplitRowHtml(0) +
            transModalBudgetSplitRowHtml(1) +
            '</div>' +
            '<div id="budget-split-feedback"></div>' +
            '<p><a href="#" onclick="transModalAddSplitBudget()" id="trans_frm_add_budget_link">Add Budget</a></p>' +
            '</div>'
        )
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
    $('#trans_frm_notes').val(msg['notes']);
    if(msg['transfer_id'] !== null) {
      $('#trans_frm_transfer_p').html(
        'This transaction is one half of a transfer, along with <a href="javascript:transModal(' +
        msg['transfer_id'] + ', mytable)">Transaction ' + msg['transfer_id'] + '</a>.'
      );
      $('#trans_frm_transfer_p').show();
    }
    if(msg['budgets'].length == 1) {
        selectBudget(null, msg['budgets'][0]['id']);
    } else {
        $('#trans_frm_is_split').prop('checked', true);
        $('#trans_frm_budget_group').hide();
        $('#trans_frm_split_budget_container').show();
        for(var i = 0; i < msg['budgets'].length; i++) {
            if(i > 1) { $('#trans_frm_budget_splits_div').append(transModalBudgetSplitRowHtml(i)); }
            var budg = msg['budgets'][i];
            selectBudget(i, budg['id']);
            $('#trans_frm_budget_amount_' + i).val(budg['amount']);
        }
    }
    $("#modalDiv").modal('show');
}

/**
 * Select a budget in a budget select element. If ``sel_num`` is null then
 * select in ``#trans_frm_budget``, else it is expected to be an integer
 * and the selection will be made in ``trans_frm_budget_<sel_num>``.
 *
 * @param {(number|null)} sel_num - The ``trans_frm_budget_`` Select element
 *   suffix, or else null for the ``trans_frm_budget`` select.
 * @param {number} budg_id - The ID of the budget to select.
 */
function selectBudget(sel_num, budg_id) {
    var budg_name = getObjectValueKey(active_budget_names_to_id, budg_id);
    if(sel_num == null) {
        if(budg_name == null) {
            // append the select option
            budg_name = getObjectValueKey(budget_names_to_id, budg_id);
            $('#trans_frm_budget').append('<option value="' + budg_id + '">' + budg_name + '</option>');
        }
        $('#trans_frm_budget option[value=' + budg_id + ']').prop('selected', 'selected').change();
    } else {
        if(budg_name == null) {
            // append the select option
            budg_name = getObjectValueKey(budget_names_to_id, budg_id);
            $('#trans_frm_budget_' + sel_num).append('<option value="' + budg_id + '">' + budg_name + '</option>');
        }
        $('#trans_frm_budget_' + sel_num + ' option[value=' + budg_id + ']').prop('selected', 'selected').change();
    }
}

/**
 * Return the first property of ``obj`` with ``val`` as its value, or null.
 * @param obj the object to check
 * @param val the value to look for
 */
function getObjectValueKey(obj, val) {
    var result = null;
    Object.keys(obj).forEach(function (key) {
        if(obj[key] == val || obj[key] == "" + val + "") {
            result = key;
        }
    });
    return result;
}

/**
 * Show the Transaction modal popup, optionally populated with
 * information for one Transaction. This function calls
 * :js:func:`transModalDivForm` to generate the form HTML,
 * :js:func:`transModalDivFillAndShow` to populate the form for editing,
 * and :js:func:`handleForm` to handle the Submit action (using
 * :js:func:`transModalFormSerialize` as a custom serialization function).
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
        var valid = validateTransModalSplits();
        if (valid == null) {
            $('#modalSaveButton').prop('disabled', false);
            $('#budget-split-feedback').html('');
            handleForm('modalBody', 'transForm', '/forms/transaction', dataTableObj, transModalFormSerialize);
        } else {
            $('#budget-split-feedback').html('<p class="text-danger">' + valid + '</p>');
            $('#modalSaveButton').prop('disabled', true);
        }
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

/**
 * Custom serialization function passed to :js:func:`handleForm` for
 * Transaction modal forms generated by :js:func:`transModal`. This handles
 * serialization of Transaction forms that may have a budget split, generating
 * data with a ``budgets`` Object (hash/mapping/dict) with budget ID keys and
 * amount values, suitable for passing directly to
 * :py:meth:`~.Transaction.set_budget_amounts`.
 *
 * @param {String} form_id the ID of the form on the page.
 */
function transModalFormSerialize(form_id) {
    var data = serializeForm(form_id);
    data['budgets'] = {};
    var num_rows = $('.budget_split_row').length;
    var rownum = 0;
    if($('#trans_frm_is_split').prop('checked')) {
        for (rownum = 0; rownum < num_rows; rownum++) {
            var bid = $('#trans_frm_budget_' + rownum).find(':selected').val();
            if(bid != 'None') {
                data['budgets'][bid] = $('#trans_frm_budget_amount_' + rownum).val();
            }
        }
    } else {
        data['budgets'][data['budget']] = data['amount'];
    }
    // strip out the budget_ and amount_ items
    delete data['budget'];
    delete data['is_split'];
    for (rownum = 0; rownum < num_rows; rownum++) {
        delete data['budget_' + rownum];
        delete data['amount_' + rownum];
    }
    return data;
}

/**
 * Handler for change of the "Budget Split?" (``#trans_frm_is_split``) checkbox.
 */
function transModalHandleSplit() {
    if($('#trans_frm_is_split').prop('checked')) {
        // split
        $('#trans_frm_budget_group').hide();
        $('#trans_frm_split_budget_container').show();
        var oldid = $('#trans_frm_budget').find(':selected').val();
        if(oldid != 'None') { $('#trans_frm_budget_0 option[value=' + oldid + ']').prop('selected', 'selected').change(); }
    } else {
        // not split
        $('#trans_frm_split_budget_container').hide();
        $('#trans_frm_budget_group').show();
    }
}

/**
 * Function to validate Transaction modal split budgets. Returns null if valid
 * or otherwise a String error message.
 */
function validateTransModalSplits() {
    if(! $('#trans_frm_is_split').prop('checked')) { return null; }
    var budget_ids = [];
    var total = 0.0;
    for (rownum = 0; rownum < $('.budget_split_row').length; rownum++) {
        var bid = $('#trans_frm_budget_' + rownum).find(':selected').val();
        if(bid != 'None') {
            if(budget_ids.indexOf(bid) > -1) {
                return 'Error: A given budget may only be specified once.';
            }
            budget_ids.push(bid);
        }
        if($('#trans_frm_budget_amount_' + rownum).val() != '') {
            total = total + parseFloat($('#trans_frm_budget_amount_' + rownum).val());
        }
    }
    var amt = parseFloat($('#trans_frm_amount').val());
    // Note: workaround for JS floating point math issues...
    if(amt.toFixed(4) != total.toFixed(4)) {
        return 'Error: Sum of budget allocations (' + total.toFixed(4) + ') must equal transaction amount (' + amt.toFixed(4) + ').';
    }
    return null;
}

/**
 * Handler for the "Add Budget" link on trans modal when using budget split.
 */
function transModalAddSplitBudget() {
    var next_row_num = $('.budget_split_row').length;
    $('#trans_frm_budget_splits_div').append(transModalBudgetSplitRowHtml(next_row_num));
    transModalSplitBudgetChanged(next_row_num);
}

/**
 * Triggered when a form element for budget splits loses focus. Calls
 * :js:func:`validateTransModalSplits` and updates the warning div with the
 * result.
 */
function budgetSplitBlur() {
    var res = validateTransModalSplits();
    if (res == null) {
        $('#budget-split-feedback').html('');
        $('#modalSaveButton').prop('disabled', false);
        validation_count = validation_count + 1;
        return null;
    }
    $('#budget-split-feedback').html('<p class="text-danger">' + res + '</p>');
    $('#modalSaveButton').prop('disabled', true);
    validation_count = validation_count + 1;
}

/**
 * Generate HTML for a budget div inside the split budgets div.
 *
 * @param {Integer} row_num - the budget split row number
 */
function transModalBudgetSplitRowHtml(row_num) {
    var html = '<div style="clear: both;" class="budget_split_row">';
    // budget select
    html += '<div class="form-group" id="trans_frm_budget_group_' + row_num + '" style="float: left; width: 75%;">';
    html += '<select id="trans_frm_budget_' + row_num + '" name="budget_' + row_num + '" class="form-control" onblur="budgetSplitBlur()" onchange="transModalSplitBudgetChanged(' + row_num + ')">';
    html += '<option value="None"></option>';
    Object.keys(active_budget_names_to_id).forEach(function (key) {
        html += '<option value="' + active_budget_names_to_id[key] + '">' + key + '</option>'
    });
    html += '</select>';
    html += '</div>'; // .form-group #trans_frm_budget_group
    // amount
    html += '<div class="form-group" id="trans_frm_budget_amount_group_' + row_num + '" style="float: left; width: 25%;">';
    html += '<div class="input-group">';
    html += '<span class="input-group-addon">$</span>';
    html += '<input class="form-control" id="trans_frm_budget_amount_' + row_num + '" name="amount_' + row_num + '" type="text" onblur="budgetSplitBlur()">';
    html += '</div>'; // .input-group
    html += '</div>'; // .form-group #trans_frm_budget_amount_group
    // close overall div
    html += '</div>'; // .budget_split_row
    return html;
}

/**
 * Called when a budget split dropdown is changed. If its amount box is empty,
 * set it to the transaction amount minus the sum of all other budget splits.
 *
 * @param {Integer} row_num - the budget split row number
 */
function transModalSplitBudgetChanged(row_num) {
    if($('#trans_frm_budget_amount_' + row_num).val() != '') { return null; }
    var amt = parseFloat($('#trans_frm_amount').val());
    var total = 0.0;
    for (var rownum = 0; rownum < $('.budget_split_row').length; rownum++) {
        if($('#trans_frm_budget_amount_' + rownum).val() != '') {
            total = total + parseFloat($('#trans_frm_budget_amount_' + rownum).val());
        }
    }
    var remainder = amt - total;
    if(remainder > 0) {
        $('#trans_frm_budget_amount_' + row_num).val(remainder.toFixed(2));
    }
}
