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

/*
 * Show unreconciled transactions in the proper div. Empty the div, then
 * load transactions via ajax. Uses :js:func:`reconcileShowTransactions` as the
 * ajax callback.
 */
function reconcileGetTransactions() {
  $.ajax("/ajax/unreconciled/trans").done(reconcileShowTransactions);
}

/*
 * Ajax callback handler for :js:func:`reconcileGetTransactions`. Display the
 * returned data in the proper div.
 *
 * @param {Object} data - ajax response (JSON array of Transaction Objects)
 */
function reconcileShowTransactions(data) {
  $('#trans-panel').empty();
  for (var i in data) {
    var t = data[i];
    $('#trans-panel').append(
      '<div class="reconcile reconcile-trans" id="trans-' + t['id'] + '" ' +
      'ondrop="handleReconcileTransOnDrop(' + t['id'] + ', event)" ' +
      'ondragover="handleReconcileTransOnDragOver(' + t['id'] + ', event)" ' +
      'ondragenter="handleReconcileTransOnDragEnter(' + t['id'] + ', event)" ' +
      'data-trans-id="' + t['id'] + '" >' +
      reconcileTransDiv(t) + '</div>\n'
    );
  }
}

/*
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
  div += '<div class="row"><div class="col-lg-12"><a href="javascript:transModal(' + trans['id'] + ', function () { updateReconcileTrans(' + trans['id'] + ') })">Trans ' + trans['id'] + '</a>: ' + trans['description'] + '</div></div>';
  div += '<div class="reconcile-drop-target"></div>';
  return div;
}

/*
 * Trigger update of a single Transaction on the reconcile page.
 *
 * @param {Integer} trans_id - the Transaction ID to update.
 */
function updateReconcileTrans(trans_id) {
  var url = "/ajax/transactions/" + trans_id;
  $.ajax(url).done(function(data) {
    $('#trans-' + data['id']).html(reconcileTransDiv(data));
  });
}

/*
 * Show unreconciled OFX transactions in the proper div. Empty the div, then
 * load transactions via ajax. Uses :js:func:`reconcileShowOFX` as the
 * ajax callback.
 */
function reconcileGetOFX() {
  $.ajax("/ajax/unreconciled/ofx").done(reconcileShowOFX);
}

/*
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
}

/*
 * Generate a div for an individual OFXTransaction, to display on the reconcile
 * view.
 *
 * @param {Object} ofxtrans - ajax JSON object representing one OFXTransaction
 */
function reconcileOfxDiv(trans) {
  var fitid = clean_fitid(trans['fitid']);
  var div = '<div class="reconcile reconcile-ofx" id="ofx-' + trans['account_id'] + '-' + fitid + '" draggable="true" ondragstart="handleReconcileOfxDrag(event)">';
  div += '<div class="row">'
  div += '<div class="col-lg-3">' + trans['date_posted']['ymdstr'] + '</div>';
  div += '<div class="col-lg-3">' + fmt_currency(trans['account_amount']) + '</div>';
  div += '<div class="col-lg-3"><strong>Acct:</strong> <span style="white-space: nowrap;"><a href="/accounts/' + trans['account_id'] + '">' + trans['account_name'] + ' (' + trans['account_id'] + ')</a></span></div>';
  div += '<div class="col-lg-3"><strong>Type:</strong> ' + trans['trans_type'] + '</div>';
  div += '</div>';
  div += '<div class="row"><div class="col-lg-12"><a href="javascript:ofxTransModal(' + trans['account_id'] + ', \'' + trans['fitid'] + '\', false)">' + trans['fitid'] + '</a>: ' + trans['name'] + '</div></div>';
  div += '</div>\n';
  return div;
}

/*
 * Handler for ``ondragstart`` of OFXTransaction divs (``div.reconcile-ofx``).
 *
 * Sets the drag data to the ID of the div.
 *
 * @param {Object} event - the drag event
 */
function handleReconcileOfxDrag(event) {
  event.dataTransfer.setData("text", event.target.id);
}

/*
 * Handler for ``ondragover`` event on Transaction divs
 * (``div.reconcile-trans``; drop target). Determines whether or not to allow
 * a drop onto this div.
 *
 * Calling ``event.preventDefault()`` *allows* the drop.
 *
 * @param {Integer} trans_id - the (target) Transaction ID
 * @param {Object} event - the drop event.
 */
function handleReconcileTransOnDragOver(trans_id, event) {
  event.stopPropagation();
  event.preventDefault();
}

/*
 * Handler for ``ondragenter`` event on Transaction divs
 * (``div.reconcile-trans``; drop target).
 *
 * @param {Integer} trans_id - the (target) Transaction ID
 * @param {Object} event - the drop event.
 */
function handleReconcileTransOnDragEnter(trans_id, event) {
  event.stopPropagation();
  event.preventDefault();
  return false;
}

/*
 * Handler for ``ondrop`` event on Transaction divs(``div.reconcile-trans``;
 * drop target).
 *
 * @param {Integer} trans_id - the (target) Transaction ID
 * @param {Object} event - the drop event.
 */
function handleReconcileTransOnDrop(trans_id, event) {
  event.preventDefault();
  event.stopPropagation();
  var div_id = event.dataTransfer.getData("text");
  console.log("Dropped " + trans_id + " (div id " + div_id + "):");
  console.log(event);
  console.log("Event target:");
  console.log(event.target);
  console.log("$(event.target)");
  console.log($(event.target));
  console.log("event target .reconcole-drop-target");
  console.log($(event.target).find('.reconcile-drop-target'));
  $(event.target).find('.reconcile-drop-target').append($(div_id));
}

/*
 * Given an OFXTransaction fitid, return a "clean" (alphanumeric) version of it,
 * suitable for use as an HTML element id.
 *
 * @param {String} fitid - original, unmodified OFXTransaction fitid.
 */
function clean_fitid(fitid) {
  return fitid.replace(/\W/g, '')
}

$(document).ready(function() {
  reconcileGetTransactions();
  reconcileGetOFX();
});
