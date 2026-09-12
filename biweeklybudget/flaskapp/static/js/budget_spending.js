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

/*
 * Spending By Budget pie charts (GitHub issue #214). All amounts come from
 * GET /ajax/chart-data/budget-spending/by-period; this file only filters them
 * by the budget checkboxes, adds them up, and draws them. Nothing is saved.
 */

/**
 * Categorical slice colours, in fixed order. These are assigned to the
 * budgets with the most spending on the page, largest first; they are never
 * cycled or generated. The order is part of what keeps adjacent colours
 * distinguishable with colour vision deficiencies, so do not re-order it.
 */
var BUDGET_SPENDING_COLORS = [
    '#2a78d6', '#eb6834', '#1baf7a', '#eda100',
    '#e87ba4', '#008300', '#4a3aa7', '#e34948'
];

/**
 * Colour for every budget beyond the length of ``BUDGET_SPENDING_COLORS``.
 * Such budgets are still separate slices, named in the chart's hover label
 * and in the table under it.
 */
var BUDGET_SPENDING_OTHER_COLOR = '#898781';

/** Response of the by-period endpoint, once loaded. */
var budgetSpendingData = null;

/** Budget ID to whether the budget is currently included in the charts. */
var budgetSpendingIncluded = {};

/** Budget ID to budget name. */
var budgetSpendingNames = {};

/** Budget ID to slice colour; fixed for the life of the page. */
var budgetSpendingColors = {};

/**
 * Compare two objects with ``name`` and ``budget_id`` properties, by name
 * then ID, for sorting.
 *
 * @param {Object} a - first object
 * @param {Object} b - second object
 * @returns {number} negative, zero or positive, as for ``Array.sort``
 */
function budgetSpendingCompareNames(a, b) {
    if (a.name < b.name) { return -1; }
    if (a.name > b.name) { return 1; }
    return a.budget_id - b.budget_id;
}

/**
 * Assign each budget its slice colour. Budgets are ranked by their total
 * positive spending across every period on the page, and the categorical
 * colours are given out in that order; the rest get
 * ``BUDGET_SPENDING_OTHER_COLOR``. This depends only on the loaded data, never
 * on which budgets are ticked, so a budget keeps its colour in every chart
 * and unticking one budget never repaints the others.
 *
 * @param {Object} data - by-period endpoint response
 * @returns {Object} budget ID to colour
 */
function budgetSpendingAssignColors(data) {
    var totals = {};
    var colors = {};
    data.budgets.forEach(function(b) { totals[b.id] = 0; });
    data.periods.forEach(function(p) {
        p.spending.forEach(function(s) {
            if (s.amount > 0) { totals[s.budget_id] += s.amount; }
        });
    });
    var ranked = data.budgets.map(function(b) {
        return { budget_id: b.id, name: b.name, total: totals[b.id] };
    });
    ranked.sort(function(a, b) {
        return (b.total - a.total) || budgetSpendingCompareNames(a, b);
    });
    ranked.forEach(function(b, idx) {
        colors[b.budget_id] = idx < BUDGET_SPENDING_COLORS.length ?
            BUDGET_SPENDING_COLORS[idx] : BUDGET_SPENDING_OTHER_COLOR;
    });
    return colors;
}

/**
 * Split one period's spending into chart slices and net credits, over the
 * included budgets only. Amounts are converted to integer cents before they
 * are added up, so that floating point error cannot creep into a total.
 *
 * @param {Object} period - one element of the endpoint's ``periods`` list
 * @returns {Object} with ``slices`` (positive nets, largest first, each with
 *   ``budget_id``, ``name``, ``cents`` and ``percent``), ``credits``
 *   (negative nets, by name) and ``totalCents`` (sum of the slices)
 */
function budgetSpendingSummarize(period) {
    var slices = [];
    var credits = [];
    var totalCents = 0;
    period.spending.forEach(function(s) {
        if (!budgetSpendingIncluded[s.budget_id]) { return; }
        var item = {
            budget_id: s.budget_id,
            name: budgetSpendingNames[s.budget_id],
            cents: Math.round(s.amount * 100)
        };
        if (item.cents > 0) {
            slices.push(item);
            totalCents += item.cents;
        } else if (item.cents < 0) {
            credits.push(item);
        }
    });
    slices.sort(function(a, b) {
        return (b.cents - a.cents) || budgetSpendingCompareNames(a, b);
    });
    credits.sort(budgetSpendingCompareNames);
    slices.forEach(function(s) { s.percent = s.cents / totalCents * 100; });
    return { slices: slices, credits: credits, totalCents: totalCents };
}

/**
 * Return a small colour swatch element identifying a budget's slices.
 *
 * @param {number} budgetId - the budget ID
 * @returns {jQuery} the swatch span
 */
function budgetSpendingSwatch(budgetId) {
    return $('<span class="budget-spending-swatch" aria-hidden="true"></span>')
        .css('background-color', budgetSpendingColors[budgetId]);
}

/**
 * Format an integer number of cents as currency.
 *
 * @param {number} cents - amount in cents
 * @returns {string} the formatted amount
 */
function budgetSpendingFmtCents(cents) {
    return fmt_currency(cents / 100);
}

/**
 * Draw one period's panel: dates, total, donut chart, table and net credits.
 * Budget names are always inserted as text, never as HTML.
 *
 * @param {Object} period - one element of the endpoint's ``periods`` list
 */
function budgetSpendingDrawPeriod(period) {
    var prefix = '#spending-' + period.key;
    var summary = budgetSpendingSummarize(period);
    $(prefix + '-dates').text(period.start_date + ' to ' + period.end_date);
    $(prefix + '-total')
        .text(budgetSpendingFmtCents(summary.totalCents))
        .attr('data-amount', (summary.totalCents / 100).toFixed(2));
    var chart = $(prefix + '-chart');
    chart.empty();
    if (summary.slices.length === 0) {
        chart.hide();
        $(prefix + '-nodata').show();
    } else {
        $(prefix + '-nodata').hide();
        chart.show();
        Morris.Donut({
            element: 'spending-' + period.key + '-chart',
            data: summary.slices.map(function(s) {
                return { label: s.name, value: s.cents / 100, percent: s.percent };
            }),
            colors: summary.slices.map(function(s) {
                return budgetSpendingColors[s.budget_id];
            }),
            formatter: function(y, row) {
                return fmt_currency(y) + ' (' + row.percent.toFixed(1) + '%)';
            }
        });
    }
    var tbody = $(prefix + '-table tbody');
    tbody.empty();
    summary.slices.forEach(function(s) {
        tbody.append(
            $('<tr></tr>').attr('data-budget-id', s.budget_id).append(
                $('<td></td>')
                    .append(budgetSpendingSwatch(s.budget_id))
                    .append(document.createTextNode(s.name)),
                $('<td class="num"></td>')
                    .text(budgetSpendingFmtCents(s.cents))
                    .attr('data-amount', (s.cents / 100).toFixed(2)),
                $('<td class="num"></td>').text(s.percent.toFixed(1) + '%')
            )
        );
    });
    var credits = $(prefix + '-credits');
    var ul = credits.find('ul');
    ul.empty();
    summary.credits.forEach(function(s) {
        ul.append(
            $('<li></li>')
                .attr('data-budget-id', s.budget_id)
                .attr('data-amount', (s.cents / 100).toFixed(2))
                .text(s.name + ': ' + budgetSpendingFmtCents(s.cents))
        );
    });
    if (summary.credits.length > 0) { credits.show(); } else { credits.hide(); }
}

/**
 * Redraw every period's panel from the loaded data.
 */
function budgetSpendingDrawAll() {
    if (budgetSpendingData === null) { return; }
    budgetSpendingData.periods.forEach(budgetSpendingDrawPeriod);
}

/**
 * Build the budget checkboxes: one per budget in the endpoint's ``budgets``
 * list, ticked unless the budget is marked "Omit from graphs". Changing one
 * redraws all the charts from the data already loaded; nothing is saved.
 */
function budgetSpendingBuildSelection() {
    var div = $('#budget-spending-selection');
    div.empty();
    if (budgetSpendingData.budgets.length === 0) {
        div.append(
            $('<p class="text-muted"></p>').text('No spending in any period.')
        );
    }
    budgetSpendingData.budgets.forEach(function(b) {
        var input = $('<input type="checkbox" class="budget-spending-toggle">')
            .attr('id', 'budget_spending_toggle_' + b.id)
            .attr('data-budget-id', b.id)
            .prop('checked', budgetSpendingIncluded[b.id]);
        div.append(
            $('<label class="checkbox-inline"></label>')
                .append(input)
                .append(budgetSpendingSwatch(b.id))
                .append(document.createTextNode(b.name))
        );
    });
    div.on('change', '.budget-spending-toggle', function() {
        budgetSpendingIncluded[$(this).data('budget-id')] = $(this).prop('checked');
        budgetSpendingDrawAll();
    });
}

/**
 * Load the chart data and draw the page. Sets ``data-loaded`` on
 * ``#budget-spending-charts`` once drawn.
 */
function budgetSpendingLoad() {
    $.ajax('/ajax/chart-data/budget-spending/by-period').done(function(data) {
        budgetSpendingData = data;
        data.budgets.forEach(function(b) {
            budgetSpendingNames[b.id] = b.name;
            budgetSpendingIncluded[b.id] = !b.omit_from_graphs;
        });
        budgetSpendingColors = budgetSpendingAssignColors(data);
        budgetSpendingBuildSelection();
        budgetSpendingDrawAll();
        $('#budget-spending-charts').attr('data-loaded', 'true');
    }).fail(function() {
        $('#budget-spending-error').show();
    });
}

$(function() {
    budgetSpendingLoad();
    // Morris charts do not follow their container's width on their own here:
    // its "resize" option would leave a handler behind for every chart that a
    // checkbox change replaces. Redraw everything instead, once resizing stops.
    var resizeTimer = null;
    $(window).on('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(budgetSpendingDrawAll, 250);
    });
});
