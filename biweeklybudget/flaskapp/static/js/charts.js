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
 * Zoomable, pannable line charts (GitHub issue #215), drawn with the Chart.js
 * files vendored in /static/chartjs/. Every line chart in the application is
 * built by lineChartCreate(), so they all behave the same way: drag to zoom
 * to a range of dates, Ctrl+drag to pan, Ctrl+scroll to zoom in and out, a
 * reset button, and a legend whose entries hide and show series. Nothing
 * about a chart's view is saved.
 */

/**
 * Categorical series colours, in fixed order. The same colours, in the same
 * order, as the Spending Charts page's donuts; the order keeps adjacent
 * colours distinguishable with colour vision deficiencies. Series beyond the
 * end of this list get colours from :js:func:`chartColor`.
 */
var CHART_COLORS = [
  '#2a78d6', '#eb6834', '#1baf7a', '#eda100',
  '#e87ba4', '#008300', '#4a3aa7', '#e34948'
];

/**
 * The hint shown above every line chart, saying how to use its controls.
 */
var CHART_HINT = 'Drag to zoom · Ctrl+drag to pan · ' +
  'Ctrl+scroll to zoom in/out';

/**
 * Return the colour for the series at a given index on a chart. The first
 * ``CHART_COLORS.length`` series use that palette; later ones step around
 * the hue circle by the golden angle, so that however many series a chart
 * has, each keeps a colour distinct from its neighbours.
 *
 * @param {number} idx - zero-based index of the series on its chart
 * @returns {string} a CSS colour
 */
function chartColor(idx) {
  if (idx < CHART_COLORS.length) { return CHART_COLORS[idx]; }
  var hue = Math.round(((idx - CHART_COLORS.length) * 137.508 + 20) % 360);
  return 'hsl(' + hue + ', 65%, 42%)';
}

/**
 * Convert a chart data date string, ``YYYY-MM-DD`` or ``YYYY-MM``, to epoch
 * milliseconds at local midnight on that day (the first of the month for
 * ``YYYY-MM``). This is how the date-fns adapter reads the same strings for
 * the time axis, so values from here can be compared with the axis's.
 *
 * @param {string} s - date string from a chart data endpoint
 * @returns {number} epoch milliseconds
 */
function chartDateMs(s) {
  var parts = s.split('-');
  return new Date(
    parseInt(parts[0], 10), parseInt(parts[1], 10) - 1,
    parts.length > 2 ? parseInt(parts[2], 10) : 1
  ).getTime();
}

/**
 * Convert a chart data endpoint response into Chart.js datasets: one per
 * entry in ``keys``, in the same order. A dataset's points are the rows that
 * have a non-null value for its key; a row without one is a gap in that
 * series, which the line joins across, never a zero.
 *
 * @param {Object} ajaxdata - endpoint response, with ``keys`` (series names)
 *   and ``data`` (one object per date, with a ``date`` property and a
 *   property per series that has a value on that date)
 * @returns {Array} Chart.js dataset objects
 */
function lineChartDatasets(ajaxdata) {
  return ajaxdata['keys'].map(function(key, idx) {
    var color = chartColor(idx);
    return {
      label: key,
      data: ajaxdata['data'].filter(function(row) {
        return row[key] !== undefined && row[key] !== null;
      }).map(function(row) {
        return { x: row['date'], y: row[key] };
      }),
      borderColor: color,
      backgroundColor: color,
      borderWidth: 2,
      pointRadius: 2,
      pointHoverRadius: 4,
      spanGaps: true
    };
  });
}

/**
 * The narrowest date range, in milliseconds, that a chart may be zoomed to:
 * the widest gap between consecutive dates in its data. Any window at least
 * that wide contains a data point, so a chart can never be zoomed into a
 * stretch with nothing to show, which would leave its value axis with no
 * values to fit. Zero when there are fewer than two dates.
 *
 * @param {Object} ajaxdata - endpoint response, as for
 *   :js:func:`lineChartDatasets`
 * @returns {number} milliseconds
 */
function lineChartMinRange(ajaxdata) {
  var times = ajaxdata['data'].map(function(row) {
    return chartDateMs(row['date']);
  }).sort(function(a, b) { return a - b; });
  var widest = 0;
  for (var i = 1; i < times.length; i++) {
    widest = Math.max(widest, times[i] - times[i - 1]);
  }
  return widest;
}

/**
 * Chart.js interaction mode ``date``, used for every line chart's hover and
 * tooltip: every point, in every visible series, on the date nearest the
 * pointer. Chart.js's own ``nearest`` mode (along the x axis) finds that date,
 * but where a series has several points on one date, such as several fuel
 * fills on the same day, it returns only some of them, and which ones depends
 * on the exact pointer position. Points on the same date always have exactly
 * the same x pixel, so this collects them all.
 *
 * @param {Object} chart - the Chart.js instance
 * @param {Object} e - the pointer event
 * @param {Object} options - the chart's interaction options
 * @param {boolean} useFinalPosition - passed through to ``nearest``
 * @returns {Array} interaction items: ``{element, datasetIndex, index}``
 */
function chartDateInteraction(chart, e, options, useFinalPosition) {
  var nearest = Chart.Interaction.modes.nearest(
    chart, e, { axis: 'x', intersect: false }, useFinalPosition
  );
  if (nearest.length === 0) { return []; }
  var x = nearest[0].element.x;
  var items = [];
  chart.data.datasets.forEach(function(ds, datasetIndex) {
    if (!chart.isDatasetVisible(datasetIndex)) { return; }
    chart.getDatasetMeta(datasetIndex).data.forEach(function(element, index) {
      if (element.x === x) {
        items.push(
          { element: element, datasetIndex: datasetIndex, index: index }
        );
      }
    });
  });
  return items;
}

Chart.Interaction.modes.date = chartDateInteraction;

/**
 * Enable a chart's "Reset zoom" button exactly when the chart is zoomed or
 * panned away from its full view.
 *
 * @param {Object} chart - Chart.js instance made by :js:func:`lineChartCreate`
 */
function lineChartUpdateReset(chart) {
  var elementId = chart.canvas.id.replace(/-canvas$/, '');
  $('#' + elementId + '-reset').prop('disabled', !chart.isZoomedOrPanned());
}

/**
 * Draw a zoomable, pannable line chart inside an existing element, replacing
 * anything already in it. The element gets a row with the hint and a
 * "Reset zoom" button (ID ``<elementId>-reset``), and a canvas (ID
 * ``<elementId>-canvas``) in a fixed-height wrapper that follows the width
 * of its panel.
 *
 * Plain drag zooms the date axis to the dragged range, Ctrl+scroll zooms it
 * in or out around the pointer, and Ctrl+drag pans it; scrolling without Ctrl
 * scrolls the page. The date axis never goes past the first or last date of
 * the data, nor narrower than :js:func:`lineChartMinRange`. The value axis
 * always fits the visible series within the visible dates. Clicking a legend
 * entry hides or shows its series.
 *
 * @param {string} elementId - ID of the element to draw the chart in
 * @param {Object} ajaxdata - chart data endpoint response, as for
 *   :js:func:`lineChartDatasets`
 * @param {Object} opts - options: ``currency`` (bool) formats values with
 *   :js:func:`fmt_currency` rather than to two decimal places;
 *   ``dateFormat`` (string) is the date-fns format for dates in tooltips,
 *   e.g. ``yyyy-MM-dd``; ``minUnit`` (string, default ``'day'``) is the
 *   smallest unit the date axis labels, ``'month'`` for monthly data. No
 *   chart's data is finer than a day, so the axis never labels times of day,
 *   even when it spans only a day or two.
 * @returns {Object} the Chart.js instance
 */
function lineChartCreate(elementId, ajaxdata, opts) {
  var container = $('#' + elementId);
  var old = Chart.getChart(elementId + '-canvas');
  if (old) { old.destroy(); }
  container.empty();
  var reset = $(
    '<button type="button" class="btn btn-default btn-xs chart-reset" ' +
    'disabled>Reset zoom</button>'
  ).attr('id', elementId + '-reset');
  container.append(
    $('<div class="chart-controls"></div>')
      .append($('<span class="chart-hint text-muted"></span>').text(CHART_HINT))
      .append(reset)
  );
  var canvas = $('<canvas></canvas>').attr('id', elementId + '-canvas');
  container.append($('<div class="chart-canvas-wrap"></div>').append(canvas));
  var fmtValue = opts.currency ? fmt_currency : function(value) {
    return Number(value).toFixed(2);
  };
  var chart = new Chart(canvas[0], {
    type: 'line',
    data: { datasets: lineChartDatasets(ajaxdata) },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      // every visible point on the date nearest the pointer; see
      // chartDateInteraction()
      interaction: { mode: 'date', intersect: false },
      scales: {
        x: {
          type: 'time',
          time: {
            tooltipFormat: opts.dateFormat,
            minUnit: opts.minUnit || 'day'
          },
          ticks: { maxRotation: 0, autoSkipPadding: 12 }
        },
        y: {
          ticks: { callback: function(value) { return fmtValue(value); } }
        }
      },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: function(ctx) {
              return ctx.dataset.label + ': ' + fmtValue(ctx.parsed.y);
            }
          }
        },
        zoom: {
          limits: {
            x: {
              min: 'original',
              max: 'original',
              minRange: lineChartMinRange(ajaxdata)
            }
          },
          zoom: {
            mode: 'x',
            drag: { enabled: true },
            wheel: { enabled: true, modifierKey: 'ctrl' },
            pinch: { enabled: true },
            onZoomComplete: function(ctx) { lineChartUpdateReset(ctx.chart); }
          },
          pan: {
            enabled: true,
            mode: 'x',
            modifierKey: 'ctrl',
            onPanComplete: function(ctx) { lineChartUpdateReset(ctx.chart); }
          }
        }
      }
    }
  });
  reset.on('click', function() {
    chart.resetZoom('none');
    lineChartUpdateReset(chart);
  });
  return chart;
}

/**
 * Replace a line chart's data in place, as when the Index page's range
 * buttons load a different span of history or a fuel fill is added. The
 * chart returns to its full view over the new data. Series hidden from the
 * legend are shown again, since the new data may have different series. The
 * canvas and the Chart.js instance are kept, so the container still holds
 * exactly one chart.
 *
 * @param {Object} chart - Chart.js instance made by :js:func:`lineChartCreate`
 * @param {Object} ajaxdata - chart data endpoint response, as for
 *   :js:func:`lineChartDatasets`
 */
function lineChartSetData(chart, ajaxdata) {
  // Reset first: the zoom plugin re-reads a scale's "original" limits the
  // next time it is zoomed, but only if it is not zoomed now.
  chart.resetZoom('none');
  chart.data.datasets = lineChartDatasets(ajaxdata);
  chart.options.plugins.zoom.limits.x.minRange = lineChartMinRange(ajaxdata);
  chart.update('none');
  lineChartUpdateReset(chart);
}
