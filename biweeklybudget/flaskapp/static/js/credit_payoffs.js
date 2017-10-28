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
 * Link handler to add another "starting on, increase payments by" form to
 * the credit payoff page.
 */
function addIncrease(settings) {
  idx = nextIndex("payoff_increase_frm_");
  var s = '<form id="payoff_increase_frm_' + idx + '" class="form-inline">';
  s = s + '<div class="form-group">';
  s = s + '<label for="payoff_increase_frm_' + idx + '_enable" class="control-label sr-only">Enable Payment Increase ' + idx + '</label>';
  s = s + '<input type="checkbox" id="payoff_increase_frm_' + idx + '_enable" name="payoff_increase_frm_' + idx + '_enable" onchange="setChanged()">';
  s = s + ' Starting on ';
  s = s + '<label for="payoff_increase_frm_' + idx + '_date" class="control-label sr-only">Payment Increase ' + idx + ' Date</label>';
  s = s + '<div class="input-group date" id="payoff_increase_frm_' + idx + '_date_input_group">';
  s = s + '<span class="input-group-addon"><i class="fa fa-calendar fa-fw"></i></span><input class="form-control" id="payoff_increase_frm_' + idx + '_date" name="payoff_increase_frm_' + idx + '_date" type="text" size="12" maxlength="10" style="width: auto;" onchange="setChanged()">';
  s = s + '</div>';
  s = s + ' , increase sum of monthly payments to ';
  s = s + '<label for="payoff_increase_frm_' + idx + '_amt" class="control-label sr-only">Payment Increase ' + idx + ' Amount</label>';
  s = s + '<div class="input-group">';
  s = s + '<span class="input-group-addon">' + CURRENCY_SYMBOL + '</span><input class="form-control" id="payoff_increase_frm_' + idx + '_amt" name="payoff_increase_frm_' + idx + '_amt" type="text" size="8" style="width: auto;" onchange="setChanged()">';
  s = s + '</div> . (<a href="#" onclick="removeIncrease(' + idx + ')" id="rm_increase_' + idx + '_link">remove</a>)</div></form>';
  s = s + '<!-- /#payoff_increase_frm_' + idx + ' -->';
  $('#payoff_increase_forms').append(s);
  if ( settings !== undefined ) {
    $('#payoff_increase_frm_' + idx + '_enable').prop('checked', settings['enabled']);
    $('#payoff_increase_frm_' + idx + '_date').val(settings['date']);
    $('#payoff_increase_frm_' + idx + '_amt').val(settings['amount']);
  }
  $('#payoff_increase_frm_' + idx + '_date').datepicker({
    todayBtn: "linked",
    autoclose: true,
    todayHighlight: true,
    format: 'yyyy-mm-dd'
  });
}

/**
 * Remove the specified Increase form.
 */
function removeIncrease(idx) {
  $('#payoff_increase_frm_' + idx).remove();
}

/**
 * Return the next index for the form with an ID beginning with a given string.
 *
 * @param {string} prefix - The prefix of the form IDs.
 * @return {int} next form index
 */
function nextIndex(prefix) {
  return $('form[id^="' + prefix + '"]').length + 1;
}

/**
 * Link handler to add another one time payment form to the credit payoff page.
 */
function addOnetime(settings) {
  idx = nextIndex("payoff_onetime_frm_");
  var s = '<form id="payoff_onetime_frm_' + idx + '" class="form-inline">';
  s = s + '<div class="form-group">';
  s = s + '<label for="payoff_onetime_frm_' + idx + '_enable" class="control-label sr-only">Enable Onetime Payment ' + idx + '</label>';
  s = s + '<input type="checkbox" id="payoff_onetime_frm_' + idx + '_enable" name="payoff_onetime_frm_' + idx + '_enable" onchange="setChanged()">';
  s = s + ' On the first payment date on or after ';
  s = s + '<label for="payoff_onetime_frm_' + idx + '_date" class="control-label sr-only">Onetime Payment ' + idx + ' Date</label>';
  s = s + '<div class="input-group date" id="payoff_onetime_frm_' + idx + '_date_input_group">';
  s = s + '<span class="input-group-addon"><i class="fa fa-calendar fa-fw"></i></span><input class="form-control" id="payoff_onetime_frm_' + idx + '_date" name="payoff_onetime_frm_' + idx + '_date" type="text" size="12" maxlength="10" style="width: auto;" onchange="setChanged()">';
  s = s + '</div>';
  s = s + ' , add ';
  s = s + '<label for="payoff_onetime_frm_' + idx + '_amt" class="control-label sr-only">Onetime Payment ' + idx + ' Amount</label>';
  s = s + '<div class="input-group">';
  s = s + '<span class="input-group-addon">' + CURRENCY_SYMBOL + '</span><input class="form-control" id="payoff_onetime_frm_' + idx + '_amt" name="payoff_onetime_frm_' + idx + '_amt" type="text" size="8" style="width: auto;" onchange="setChanged()">';
  s = s + '</div> to the payment amount. (<a href="#" onclick="removeOnetime(' + idx + ')" id="rm_onetime_' + idx + '_link">remove</a>)</div></form>';
  s = s + '<!-- /#payoff_onetime_frm_' + idx + ' -->';
  $('#payoff_onetime_forms').append(s);
  if ( settings !== undefined ) {
    $('#payoff_onetime_frm_' + idx + '_enable').prop('checked', settings['enabled']);
    $('#payoff_onetime_frm_' + idx + '_date').val(settings['date']);
    $('#payoff_onetime_frm_' + idx + '_amt').val(settings['amount']);
  }
  $('#payoff_onetime_frm_' + idx + '_date').datepicker({
    todayBtn: "linked",
    autoclose: true,
    todayHighlight: true,
    format: 'yyyy-mm-dd'
  });
}

/**
 * Remove the specified Onetime form.
 */
function removeOnetime(idx) {
  $('#payoff_onetime_frm_' + idx).remove();
}

/**
 * Buttom handler to serialize and submit the forms, to save user input and
 * recalculate the payoff amounts.
 */
function recalcPayoffs() {
  formdata = serializeForms();
  $('.formfeedback').remove();
  $('.has-error').each(function(index) { $(this).removeClass('has-error'); });
  $.ajax({
    type: "POST",
    url: '/settings/credit-payoff',
    data: JSON.stringify(formdata),
    success: function(data) {
        if(data.hasOwnProperty('error_message')) {
            $('#settings-panel-body').prepend(
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
          location.reload();
        }
    },
    error: function(jqXHR, textStatus, errorThrown) {
        if($('#formStatus').length == 0) { $('#settings-panel-body').prepend('<div id="formStatus"></div>'); }
        $('#formStatus').html(
            '<div class="alert alert-danger formfeedback"><strong>Error submitting ' +
            'form:</strong> ' + textStatus + ': ' + jqXHR.status + ' ' + errorThrown + '</div>'
        );
    }
  });
}

/**
 * Serialize the form data into an object and return it.
 *
 * @return {Object} serialized forms.
 */
function serializeForms() {
  var data = {"increases": [], "onetimes": []};
  $('form[id^="payoff_increase_frm_"]').each(function(k, v) {
    frmid = $(v).prop('id');
    data["increases"].push({
      "date": $('#' + frmid + '_date').val(),
      "amount": $('#' + frmid + '_amt').val(),
      "enabled": $('#' + frmid + '_enable').prop('checked')
    });
  });
  $('form[id^="payoff_onetime_frm_"]').each(function(k, v) {
    frmid = $(v).prop('id');
    data["onetimes"].push({
      "date": $('#' + frmid + '_date').val(),
      "amount": $('#' + frmid + '_amt').val(),
      "enabled": $('#' + frmid + '_enable').prop('checked')
    });
  });
  return data;
}

/**
 * Event handler to activate the "Save & Recalculate" button when user input
 * fields have changed.
 */
function setChanged() {
  $('#btn_recalc_payoffs').removeClass('disabled btn-default').addClass('btn-primary');
}

/**
 * Load settings from embedded JSON. Called on page load.
 */
function loadSettings() {
  var settings = JSON.parse($('#pymt_settings_json').html());
  for (var s in settings["increases"]) { addIncrease(settings["increases"][s]); }
  if ( settings["increases"].length == 0 ) { addIncrease(); }
  for (var s in settings["onetimes"]) { addOnetime(settings["onetimes"][s]); }
  if ( settings["onetimes"].length == 0 ) { addOnetime(); }
}

$(document).ready(function() {
    loadSettings();
});
