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
function accountModalDivHandleType() {
    if($('#account_frm_type_credit').is(':checked')) {
        $('#account_frm_credit_limit_group').show();
        $('#account_frm_apr_group').show();
        $('#account_frm_margin_group').show();
        $('#account_frm_int_class_name_group').show();
        $('#account_frm_min_pay_class_name_group').show();
    } else {
        $('#account_frm_credit_limit_group').hide();
        $('#account_frm_apr_group').hide();
        $('#account_frm_margin_group').hide();
        $('#account_frm_int_class_name_group').hide();
        $('#account_frm_min_pay_class_name_group').hide();
    }
}

/**
 * Generate the HTML for the form on the Modal
 */
function accountModalDivForm() {
    return new FormBuilder('accountForm')
        .addHidden('account_frm_id', 'id', '')
        .addText('account_frm_name', 'name', 'Name')
        .addText('account_frm_description', 'description', 'Description')
        .addRadioInline(
            'acct_type',
            'Type',
            [
                { id: 'account_frm_type_bank', label: 'Bank', value: 'Bank', inputHtml: 'onchange="accountModalDivHandleType()"', checked: true },
                { id: 'account_frm_type_credit', label: 'Credit', value: 'Credit', inputHtml: 'onchange="accountModalDivHandleType()"' },
                { id: 'account_frm_type_investment', label: 'Investment', value: 'Investment', inputHtml: 'onchange="accountModalDivHandleType()"' }
            ]
        )
        .addCheckbox(
            'account_frm_ofx_cat_memo',
            'ofx_cat_memo_to_name',
            'OFX Cat Memo to Name'
        )
        .addText('account_frm_vault_creds_path', 'vault_creds_path', 'Vault Creds Path')
        .addTextArea(
            'account_frm_ofxgetter_config_json',
            'ofxgetter_config_json',
            'OFXGetter Config (JSON)'
        )
        .addCheckbox('account_frm_negate_ofx', 'negate_ofx_amounts', 'Negate OFX Amounts', false)
        .addCheckbox('account_frm_reconcile_trans', 'reconcile_trans', 'Reconcile Transactions?', true)
        .addCurrency('account_frm_credit_limit', 'credit_limit', 'Credit Limit')
        .addText('account_frm_apr', 'apr', 'APR', { helpBlock: 'If you know the margin added to the Prime Rate for this card, use the Margin field instead.'})
        .addText('account_frm_margin', 'prime_rate_margin', 'Margin', { helpBlock: 'If known, the margin added to the US Prime Rate to determine the APR.'})
        .addLabelToValueSelect(
            'account_frm_int_class_name',
            'interest_class_name',
            'Interest Class Name',
            interest_class_names
        )
        .addLabelToValueSelect(
            'account_frm_min_pay_class_name',
            'min_payment_class_name',
            'Minimum Payment Class Name',
            min_pay_class_names
        )
        .addCheckbox('account_frm_active', 'is_active', 'Active?', true)
        .render();
}

/**
 * Ajax callback to fill in the modalDiv with data on a account.
 * Callback for ajax call in :js:func:`accountModal`.
 */
function accountModalDivFillAndShow(msg) {
    $('#modalLabel').text('Edit Account ' + msg['id']);
    if(msg['acct_type']['name'] == 'Bank') {
        $('#account_frm_type_bank').prop('checked', true);
        $('#account_frm_type_credit').prop('checked', false);
        $('#account_frm_type_investment').prop('checked', false);
    } else if (msg['acct_type']['name'] == 'Credit') {
        $('#account_frm_type_bank').prop('checked', false);
        $('#account_frm_type_credit').prop('checked', true);
        $('#account_frm_type_investment').prop('checked', false);
    } else {
        $('#account_frm_type_bank').prop('checked', false);
        $('#account_frm_type_credit').prop('checked', false);
        $('#account_frm_type_investment').prop('checked', true);
    }
    accountModalDivHandleType();
    $('#account_frm_apr').val(msg['apr']);
    $('#account_frm_credit_limit').val(msg['credit_limit']);
    $('#account_frm_description').val(msg['description']);
    $('#account_frm_id').val(msg['id']);
    $('#account_frm_int_class_name option[value=' + msg['interest_class_name'] + ']').prop('selected', 'selected').change();
    if(msg['is_active'] === true) {
        $('#account_frm_active').prop('checked', true);
    } else {
        $('#account_frm_active').prop('checked', false);
    }
    $('#account_frm_min_pay_class_name option[value=' + msg['min_payment_class_name'] + ']').prop('selected', 'selected').change();
    $('#account_frm_name').val(msg['name']);
    if(msg['negate_ofx_amounts'] === true) {
        $('#account_frm_negate_ofx').prop('checked', true);
    } else {
        $('#account_frm_negate_ofx').prop('checked', false);
    }
    if(msg['ofx_cat_memo_to_name'] === true) {
        $('#account_frm_ofx_cat_memo').prop('checked', true);
    } else {
        $('#account_frm_ofx_cat_memo').prop('checked', false);
    }
    $('#account_frm_ofxgetter_config_json').val(msg['ofxgetter_config_json']);
    $('#account_frm_margin').val(msg['prime_rate_margin']);
    if(msg['reconcile_trans'] === true) {
        $('#account_frm_reconcile_trans').prop('checked', true);
    } else {
        $('#account_frm_reconcile_trans').prop('checked', false);
    }
    $('#account_frm_vault_creds_path').val(msg['vault_creds_path']);
    $("#modalDiv").modal('show');
}

/**
 * Show the modal popup, populated with information for one account.
 * Uses :js:func:`accountModalDivFillAndShow` as ajax callback.
 *
 * @param {number} id - the ID of the account to show modal for, or null to
 *   show a modal to add a new account.
 * @param {(Object|null)} dataTableObj - passed on to ``handleForm()``
 */
function accountModal(id, dataTableObj) {
    console.log("accountModal(" + id + ")");
    $('#modalBody').empty();
    $('#modalBody').append(accountModalDivForm());
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        handleForm('modalBody', 'accountForm', '/forms/account', dataTableObj);
    }).show();
    if(id) {
        var url = "/ajax/account/" + id;
        $.ajax(url).done(accountModalDivFillAndShow);
    } else {
        $('#modalLabel').text('Add New Account');
        accountModalDivHandleType();
        $("#modalDiv").modal('show');
    }
}
