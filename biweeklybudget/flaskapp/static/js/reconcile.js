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
 * Show unreconciled transactions in the proper div. Empty the div, then
 * load transactions via ajax. Uses :js:func:`reconcileShowTransactions` as the
 * ajax callback.
 */
function reconcileGetTransactions() {
  $.ajax("/ajax/unreconciled/trans").done(reconcileShowTransactions);
}

/**
 * Ajax callback handler for :js:func:`reconcileGetTransactions`. Display the
 * returned data in the proper div.
 *
 * Sets each Transaction div as ``droppable``, using
 * :js:func:`reconcileTransHandleDropEvent` as the drop event handler and
 * :js:func:`reconcileTransDroppableAccept` to test if a draggable is droppable
 * on the element.
 *
 * @param {Object} data - ajax response (JSON array of Transaction Objects)
 */
function reconcileShowTransactions(data) {
  $('#trans-panel').empty();
  for (var i in data) {
    var t = data[i];
    $('#trans-panel').append(
      '<div class="reconcile reconcile-trans" id="trans-' + t['id'] + '" ' +
      'data-trans-id="' + t['id'] + '" data-acct-id="' + t['account_id'] + '" data-amt="' + t['actual_amount'] + '">' +
      reconcileTransDiv(t) + '</div>\n'
    );
  }
  $('.reconcile-trans').droppable({
    drop: reconcileTransHandleDropEvent,
    accept: reconcileTransDroppableAccept
  });
}

/**
 * Accept function for droppables, to determine if a given draggable can be
 * dropped on it.
 *
 * @param {Object} drag - the draggable element being dropped.
 */
function reconcileTransDroppableAccept(drag) {
  var drop_acct = $(this).attr('data-acct-id');
  var drop_amt = $(this).attr('data-amt');
  var drag_acct = $(drag).attr('data-acct-id');
  var drag_amt = $(drag).attr('data-amt');
  return (
    drop_acct === drag_acct &&
    drop_amt === drag_amt &&
    $(this).find('.reconcile-drop-target').is(':empty')
  );
}

/**
 * Handler for Drop events on reconcile Transaction divs. Setup as handler
 * via :js:func:`reconcileShowTransactions`. This just gets the draggable and
 * the target from the ``event`` and ``ui``, and then passes them on to
 * :js:func:`reconcileTransactions`.
 *
 * @param {Object} event - the drop event
 * @param {Object} ui - the UI element, containing the draggable
 */
function reconcileTransHandleDropEvent(event, ui) {
  reconcileTransactions(ui.draggable[0], event.target);
}

/**
 * Reconcile a transaction; move the divs and other elements as necessary,
 * and updated the ``reconciled`` variable.
 *
 * @param {Object} ofx_div - the OFXTransaction div element (draggable)
 * @param {Object} target - the Transaction div (drop target)
 */
function reconcileTransactions(ofx_div, target) {
  // get the droppable's transaction_id
  var trans_id = parseInt($(target).attr('data-trans-id'));
  // get the contents of the draggable and relevant attributes
  var content = $(ofx_div).html();
  var acct_id = parseInt($(ofx_div).attr('data-acct-id'));
  var fitid = $(ofx_div).attr('data-fitid');
  var cfitid = clean_fitid(fitid);
  var amt = $(ofx_div).attr('data-amt');
  // create a new div to put in the Transaction
  var newdiv = $('<div class="reconcile reconcile-ofx-dropped" id="dropped-ofx-' + acct_id + '-' + cfitid + '" data-acct-id="' + acct_id + '" data-amt="' + amt + '" data-fitid="' + fitid + '" style="" />').html(content);
  // remove the (make trans) link
  $(newdiv).find('.make-trans-link').remove();
  // hide the source draggable
  $(ofx_div).hide();
  // append the new div to the droppable
  var droppable = $(target).find('.reconcile-drop-target');
  $(droppable).html('<div style="text-align: right;"><a href="javascript:reconcileDoUnreconcile(' + trans_id + ', ' + acct_id + ', \'' + fitid + '\')">Unreconcile</a></div>');
  $(newdiv).appendTo(droppable);
  var editLink = $(target).find('a:contains("Trans ' + trans_id + '")');
  editLink.replaceWith(
    $('<span class="disabledEditLink">Trans ' + trans_id + '</span>')
  );
  $(target).find('a:contains("(no OFX)")').hide();
  reconciled[trans_id] = [acct_id, fitid];
}

/**
 * Unreconcile a reconciled OFXTransaction/Transaction. This removes
 * ``trans_id`` from the ``reconciled`` variable, empties the Transaction div's
 * reconciled div, and shows the OFX div.
 *
 * @param {Integer} trans_id - the transaction id
 * @param {Integer} acct_id - the account id
 * @param {String} fitid - the FITID
 */
function reconcileDoUnreconcile(trans_id, acct_id, fitid) {
  // remove from the reconciled object
  delete reconciled[trans_id];
  // change the transaction link back to a real link
  var editText = $('#trans-' + trans_id).find('.disabledEditLink');
  editText.replaceWith(
    $('<a href="javascript:transModal(' + trans_id + ', function () { updateReconcileTrans(' + trans_id + ') })">Trans ' + trans_id + '</a>')
  );
  // remove the dropped OFX
  $('#trans-' + trans_id).find('.reconcile-drop-target').empty();
  // make the OFX visible again
  $('#ofx-' + acct_id + '-' + clean_fitid(fitid)).show();
  $('#trans-' + trans_id).find('a:contains("(no OFX)")').show();
}

/**
 * Generate a div for an individual Transaction, to display on the reconcile
 * view.
 *
 * @param {Object} trans - ajax JSON object representing one Transaction
 */
function reconcileTransDiv(trans) {
  var div = '<div class="row">'
  div += '<div class="col-lg-3">' + trans['date']['str'] + '</div>';
  div += '<div class="col-lg-3">' + fmt_currency(trans['actual_amount']) + '</div>';
  div += '<div class="col-lg-3"><strong>Acct:</strong> <span style="white-space: nowrap;"><a href="/accounts/' + trans['account_id'] + '">' + trans['account_name'] + ' (' + trans['account_id'] + ')</a></span></div>';
  div += '<div class="col-lg-3"><strong>Budget:</strong> <span style="white-space: nowrap;"><a href="/budgets/' + trans['budget_id'] + '">' + trans['budget_name'] + ' (' + trans['budget_id'] + ')</a></span></div>';
  div += '</div>';
  div += '<div class="row"><div class="col-lg-12">';
  div += '<div style="float: left;"><a href="javascript:transModal(' + trans['id'] + ', function () { updateReconcileTrans(' + trans['id'] + ') })">Trans ' + trans['id'] + '</a>: ' + trans['description'] + '</div>';
  div += '<div style="float: right;" class="trans-no-ofx"><a href="javascript:transNoOfx(' + trans['id'] + ')" style="" title="Reconcile as never having a matching OFX Transaction">(no OFX)</a></div>';
  div += '</div></div>';
  div += '<div class="reconcile-drop-target"></div>';
  return div;
}

/**
 * Trigger update of a single Transaction on the reconcile page.
 *
 * @param {Integer} trans_id - the Transaction ID to update.
 */
function updateReconcileTrans(trans_id) {
  var url = "/ajax/transactions/" + trans_id;
  $.ajax(url).done(function(data) {
    $('#trans-' + data['id']).html(reconcileTransDiv(data));
    $('#trans-' + data['id']).attr('data-acct-id', data['account_id']);
    $('#trans-' + data['id']).attr('data-amt', data['actual_amount']);
  });
}

/**
 * Show unreconciled OFX transactions in the proper div. Empty the div, then
 * load transactions via ajax. Uses :js:func:`reconcileShowOFX` as the
 * ajax callback.
 */
function reconcileGetOFX() {
  $.ajax("/ajax/unreconciled/ofx").done(reconcileShowOFX);
}

/**
 * Ajax callback handler for :js:func:`reconcileGetOFX`. Display the
 * returned data in the proper div.
 *
 * @param {Object} data - ajax response (JSON array of OFXTransaction Objects)
 */
function reconcileShowOFX(data) {
  $('#ofx-panel').empty();
  for (var i in data) {
    var t = data[i];
    $('#ofx-panel').append(reconcileOfxDiv(t));
  }
  $('.reconcile-ofx').each(function(index) {
    $(this).draggable({
      cursor: 'move',
      // start: dragStart,
      // containment: '#content-row',
      revert: 'invalid',
      helper: 'clone'
    });
  });
}

/**
 * Generate a div for an individual OFXTransaction, to display on the reconcile
 * view.
 *
 * @param {Object} ofxtrans - ajax JSON object representing one OFXTransaction
 */
function reconcileOfxDiv(trans) {
  var fitid = clean_fitid(trans['fitid']);
  var div = '<div class="reconcile reconcile-ofx" id="ofx-' + trans['account_id'] + '-' + fitid + '" data-acct-id="' + trans['account_id'] + '" data-amt="' + trans['account_amount'] + '" data-fitid="' + trans['fitid'] + '" style="">';
  div += '<div class="row">'
  div += '<div class="col-lg-3">' + trans['date_posted']['ymdstr'] + '</div>';
  div += '<div class="col-lg-3">' + fmt_currency(trans['account_amount']) + '</div>';
  div += '<div class="col-lg-3"><strong>Acct:</strong> <span style="white-space: nowrap;"><a href="/accounts/' + trans['account_id'] + '">' + trans['account_name'] + ' (' + trans['account_id'] + ')</a></span></div>';
  div += '<div class="col-lg-3"><strong>Type:</strong> ' + trans['trans_type'] + '</div>';
  div += '</div>';
  div += '<div class="row"><div class="col-lg-12">';
  div += '<div style="float: left;"><a href="javascript:ofxTransModal(' + trans['account_id'] + ', \'' + trans['fitid'] + '\', false)">' + trans['fitid'] + '</a>: ' + trans['name'] + '</div>';
  div += '<div style="float: right;" class="make-trans-link"><a href="javascript:makeTransFromOfx(' + trans['account_id'] + ', \'' + trans['fitid'] + '\')" title="Create Transaction from this OFX">(make trans)</a></div>';
  div += '</div></div>';
  div += '</div>\n';
  return div;
}

/**
 * Given an OFXTransaction fitid, return a "clean" (alphanumeric) version of it,
 * suitable for use as an HTML element id.
 *
 * @param {String} fitid - original, unmodified OFXTransaction fitid.
 */
function clean_fitid(fitid) {
  return fitid.replace(/\W/g, '')
}

/**
 * Handle click of the Submit button on the reconcile view. This POSTs to
 * ``/ajax/reconcile`` via ajax. Feedback is provided by appending a div with
 * id ``reconcile-msg`` to ``div#notifications-row/div.col-lg-12``.
 */
function reconcileHandleSubmit() {
  $('body').find('#reconcile-msg').remove();
  if (jQuery.isEmptyObject(reconciled)) {
    var container = $('#notifications-row').find('.col-lg-12');
    var newdiv = $(
      '<div class="alert alert-warning" id="reconcile-msg">' +
      '<strong>Warning:</strong> No reconciled transactions; did not submit form.</div>'
    );
    $(container).append(newdiv);
    newdiv.effect("shake");
    return;
  }
  $.ajax({
        type: "POST",
        url: '/ajax/reconcile',
        data: JSON.stringify(reconciled),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function(data) {
            var container = $('#notifications-row').find('.col-lg-12');
            if(!data['success']) {
                var newdiv = $(
                  '<div class="alert alert-danger" id="reconcile-msg">' +
                  '<strong>Error:</strong> ' + data['error_message'] + '</div>'
                );
                $(container).append(newdiv);
                newdiv.effect("shake");
            } else {
                $(container).append(
                  '<div class="alert alert-success" id="reconcile-msg">' +
                  data['success_message'] + '</div>'
                );
                reconciled = {};
                reconcileGetTransactions();
                reconcileGetOFX();
            }
        },
        error: function(jqXHR, textStatus, errorThrown) {
            var container = $('#notifications-row').find('.col-lg-12');
            if(jqXHR.responseText.indexOf('{') == 0) {
                // JSON response
                var resp = JSON.parse(jqXHR.responseText);
                var newdiv = $(
                  '<div class="alert alert-danger" id="reconcile-msg">' +
                  '<strong>Error ' + jqXHR.status +
                  ':</strong> ' + resp['error_message'] + '</div>'
                );
            } else {
                var newdiv = $(
                  '<div class="alert alert-danger" id="reconcile-msg">' +
                  '<strong>Error submitting form:</strong> ' + textStatus +
                  ': ' + jqXHR.status + ' ' + errorThrown + '</div>'
                );
            }
            $(container).append(newdiv);
            newdiv.effect("shake");
        }
    });
}

/**
 * Link function to create a Transaction from a specified OFXTransaction,
 * and then reconcile them.
 *
 * @param {Integer} acct_id - the OFXTransaction account ID
 * @param {String} fitid - the OFXTransaction fitid
 */
function makeTransFromOfx(acct_id, fitid) {
    $('#modalBody').empty();
    $('#modalBody').append(transModalDivForm());
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(
        function() {
            handleForm(
                'modalBody', 'transForm', '/forms/transaction',
                function(data) {
                    makeTransSaveCallback(data, acct_id, fitid);
                }
            );
        }
    ).show();
    $('#trans_frm_date_input_group').datepicker({
        todayBtn: "linked",
        autoclose: true,
        todayHighlight: true,
        format: 'yyyy-mm-dd'
    });
    var url = "/ajax/ofx/" + acct_id + "/" + encodeURIComponent(fitid);
    $.ajax(url).done(transModalOfxFillAndShow);
}

/**
 * Callback for the GET /ajax/ofx/<acct_id>/<fitid> from
 * :js:func:`makeTransFromOfx`. Receives the OFXTransaction data and populates
 * it into the Transaction modal form.
 *
 * @param {Object} data - OFXTransaction response data
 */
function transModalOfxFillAndShow(data) {
    $('#modalLabel').text('Add Transaction for OFX (' + data['txn']['account_id'] + ', ' + data['txn']['fitid'] + ')');
    $('#trans_frm_description').val(data['txn']['name']);
    $('#trans_frm_date').val(data['txn']['date_posted']['ymdstr']);
    $('#trans_frm_amount').val(data['account_amount']);
    $('#trans_frm_account option[value=' + data['acct_id'] + ']').prop('selected', 'selected').change();
    $('#trans_frm_notes').val('created from OFXTransaction(' + data['txn']['account_id'] + ', ' + data['txn']['fitid'] + ')');
    $("#modalDiv").modal('show');
}

/**
 * Callback for the "Save" button on the Transaction modal created by
 * :js:func:`makeTransFromOfx`. Displays the new Transaction at the bottom
 * of the Transactions list, then reconciles it with the original OFXTransaction
 *
 * @param {Object} data - response data from POST to /forms/transaction
 * @param {Integer} acct_id - the OFXTransaction account ID
 * @param {String} fitid - the OFXTransaction fitid
 */
function makeTransSaveCallback(data, acct_id, fitid) {
  var trans_id = data['trans_id'];
  // add the transaction to the Transactions column
  $.ajax("/ajax/transactions/" + trans_id).done(function(data) {
    $('#trans-panel').append(
      '<div class="reconcile reconcile-trans" id="trans-' + data['id'] + '" ' +
      'data-trans-id="' + data['id'] + '" data-acct-id="' + data['account_id'] + '" data-amt="' + data['actual_amount'] + '">' +
      reconcileTransDiv(data) + '</div>\n'
    );
    $('#trans-' + data['id']).droppable({
      drop: reconcileTransHandleDropEvent,
      accept: reconcileTransDroppableAccept
    });
    // reconcile the OFXTrans with the Transaction
    reconcileTransactions($('#ofx-' + acct_id + '-' + clean_fitid(fitid)), $('#trans-' + trans_id));
  });
}

/**
 * Show the modal for reconciling a Transaction without a matching
 * OFXTransaction. Calls :js:func:`transNoOfxDivForm` to generate the modal form
 * div content. Uses an inline function to handle the save action, which calls
 * :js:func:`reconcileTransNoOfx` to perform the reconcile action.
 *
 * @param {number} trans_id - the ID of the Transaction
 */
function transNoOfx(trans_id) {
    console.log("transNoOfx(" + trans_id + ")");
    $('#modalBody').empty();
    $('#modalBody').append(transNoOfxDivForm(trans_id));
    $('#modalLabel').text('Reconcile Transaction ' + trans_id + ' Without OFX');
    $('#modalSaveButton').off();
    $('#modalSaveButton').click(function() {
        $('.has-error').each(function(index) { $(this).removeClass('has-error'); });
        var note = $('#trans_frm_note').val().trim();
        if (note == "") {
            $('#trans_frm_note').parent().append('<p class="text-danger formfeedback">Note cannot be empty.</p>');
            $('#trans_frm_note').parent().addClass('has-error');
            return;
        } else {
            reconcileTransNoOfx(trans_id, note);
            $("#modalDiv").modal('hide');
        }
    }).show();
    $("#modalDiv").modal('show');
}

/**
 * Generate the modal form div content for the modal to reconcile a Transaction
 * without a matching OFXTransaction. Called by :js:func:`transNoOfx`.
 *
 * @param {number} trans_id - the ID of the Transaction
 */
function transNoOfxDivForm(trans_id) {
    return new FormBuilder('transForm')
        .addP('Mark Transaction as reconciled with no OFX (i.e. Transaction that will never be seen on any OFX statement).')
        .addHidden('trans_frm_id', 'id', trans_id)
        .addText('trans_frm_note', 'note', 'Note')
        .render();
}

/**
 * Reconcile a Transaction without a matching OFXTransaction. Called from
 * the Save button handler in :js:func:`transNoOfx`.
 */
function reconcileTransNoOfx(trans_id, note) {
  var target = $('#trans-' + trans_id);
  var newdiv = $('<div class="reconcile" id="trans-' + trans_id + '-noOFX" style="" />').html('<p><strong>No OFX:</strong> ' + note + '</p>');
  var droppable = $(target).find('.reconcile-drop-target');
  $(droppable).html('<div style="text-align: right;"><a href="javascript:reconcileDoUnreconcileNoOfx(' + trans_id + ')">Unreconcile</a></div>');
  $(newdiv).appendTo(droppable);
  var editLink = $(target).find('a:contains("Trans ' + trans_id + '")');
  editLink.replaceWith(
    $('<span class="disabledEditLink">Trans ' + trans_id + '</span>')
  );
  $(target).find('a:contains("(no OFX)")').hide();
  reconciled[trans_id] = note;
}

/**
 * Unreconcile a reconciled NoOFX Transaction. This removes
 * ``trans_id`` from the ``reconciled`` variable and empties the Transaction
 * div's reconciled div.
 *
 * @param {Integer} trans_id - the transaction id
 */
function reconcileDoUnreconcileNoOfx(trans_id) {
  // remove from the reconciled object
  delete reconciled[trans_id];
  // change the transaction link back to a real link
  var editText = $('#trans-' + trans_id).find('.disabledEditLink');
  editText.replaceWith(
    $('<a href="javascript:transModal(' + trans_id + ', function () { updateReconcileTrans(' + trans_id + ') })">Trans ' + trans_id + '</a>')
  );
  // remove the dropped OFX
  $('#trans-' + trans_id).find('.reconcile-drop-target').empty();
  $('#trans-' + trans_id).find('a:contains("(no OFX)")').show();
}

$(document).ready(function() {
  reconcileGetTransactions();
  reconcileGetOFX();
  $('#reconcile-submit').click(reconcileHandleSubmit);
});
