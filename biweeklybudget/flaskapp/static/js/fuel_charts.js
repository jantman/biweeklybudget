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

/** The Fuel Economy chart's Chart.js instance, once drawn. */
var ecoChart;

/** The Fuel Prices chart's Chart.js instance, once drawn. */
var priceChart;

/**
 * Draw the Fuel Economy and Fuel Prices charts with :js:func:`lineChartCreate`.
 */
function initCharts() {
  $.ajax('/ajax/chart-data/fuel-economy').done(function(ajaxdata) {
    ecoChart = lineChartCreate(
      'mpg-chart', ajaxdata, { currency: false, dateFormat: 'yyyy-MM-dd' }
    );
  });

  $.ajax('/ajax/chart-data/fuel-prices').done(function(ajaxdata) {
    priceChart = lineChartCreate(
      'fuel-price-chart', fuelPriceChartData(ajaxdata),
      { currency: true, dateFormat: 'yyyy-MM-dd' }
    );
  });
}

/**
 * The fuel prices endpoint returns only ``data``, one ``price`` per date, with
 * no ``keys``; add the single series name that :js:func:`lineChartCreate`
 * expects.
 *
 * @param {Object} ajaxdata - response from /ajax/chart-data/fuel-prices
 * @returns {Object} the same data, with ``keys`` of ``['price']``
 */
function fuelPriceChartData(ajaxdata) {
  return { keys: ['price'], data: ajaxdata['data'] };
}

/**
 * Reload both fuel charts' data in place, after a fuel fill is added.
 */
function updateCharts() {
  $.ajax('/ajax/chart-data/fuel-economy').done(function(ajaxdata) {
    lineChartSetData(ecoChart, ajaxdata);
  });

  $.ajax('/ajax/chart-data/fuel-prices').done(function(ajaxdata) {
    lineChartSetData(priceChart, fuelPriceChartData(ajaxdata));
  });
}

$(function() {
  initCharts();
});
