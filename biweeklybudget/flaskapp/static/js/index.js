/*
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016-2024 Jason Antman <http://www.jasonantman.com>

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
 * The Morris chart instance for the Account Balances chart, or null before it
 * has been drawn. Held so that a range change can call setData() on the
 * existing chart rather than building a new one over the top of it.
 */
var acctBalanceChart = null;

/**
 * Fetch account balance chart data for a given number of days of history.
 *
 * @param {number} days - days of history to request; 0 means all history.
 * @param {function} cb - callback, passed the decoded response object.
 */
function acctBalanceChartData(days, cb) {
  $.ajax(
    '/ajax/chart-data/account-balances', { data: { days: days } }
  ).done(cb);
}

/**
 * Draw or redraw the Account Balances chart from an endpoint response.
 *
 * On the first call this constructs the Morris.Line; on later calls it hands
 * the new data to the existing chart via setData(), which redraws in place
 * without a page reload. When the response holds no data at all, a plain
 * message is shown in place of the chart.
 *
 * @param {Object} ajaxdata - response from /ajax/chart-data/account-balances,
 *   with "data" (one object per date) and "keys" (account names) properties.
 */
function drawAcctBalanceChart(ajaxdata) {
  if (ajaxdata['data'].length === 0) {
    $('#account-balance-chart').hide();
    $('#account-balance-chart-nodata').show();
    return;
  }
  $('#account-balance-chart-nodata').hide();
  $('#account-balance-chart').show();
  if (acctBalanceChart !== null) {
    acctBalanceChart.setData(ajaxdata['data']);
    return;
  }
  acctBalanceChart = Morris.Line({
    element: 'account-balance-chart',
    data: ajaxdata['data'],
    xkey: 'date',
    ykeys: ajaxdata['keys'],
    labels: ajaxdata['keys'],
    pointSize: 2,
    hideHover: 'auto',
    resize: true,
    preUnits: CURRENCY_SYMBOL,
    continuousLine: true
  });
}

/**
 * Load the Account Balances chart for a given number of days of history.
 *
 * @param {number} days - days of history to show; 0 means all history.
 */
function updateAcctBalanceChart(days) {
  acctBalanceChartData(days, drawAcctBalanceChart);
}

$(function() {
  // Open on the configured default rather than letting the endpoint pick, so
  // the highlighted range button and the plotted data cannot disagree.
  updateAcctBalanceChart(ACCOUNT_BALANCE_CHART_DEFAULT_DAYS);
  $('#account-balance-chart-ranges button').on('click', function() {
    var btn = $(this);
    if (btn.hasClass('active')) { return; }
    btn.siblings().removeClass('active');
    btn.addClass('active');
    updateAcctBalanceChart(btn.data('days'));
  });
});
