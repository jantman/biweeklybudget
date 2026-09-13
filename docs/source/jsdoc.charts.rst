jsdoc.charts
============

File: ``biweeklybudget/flaskapp/static/js/charts.js``

.. js:function:: .........r(idx)

   Return the colour for the series at a given index on a chart. The first
   ``CHART_COLORS.length`` series use that palette; later ones step around
   the hue circle by the golden angle, so that however many series a chart
   has, each keeps a colour distinct from its neighbours.

   :param idx: zero-based index of the series on its chart
   :type idx: **number**
   :returns: **string** -- a CSS colour
.. js:function:: ...................n(chart, e, options, useFinalPosition)

   Chart.js interaction mode ``date``, used for every line chart's hover and
   tooltip: every point, in every visible series, on the date nearest the
   pointer. Chart.js's own ``nearest`` mode (along the x axis) finds that date,
   but where a series has several points on one date, such as several fuel
   fills on the same day, it returns only some of them, and which ones depends
   on the exact pointer position. Points on the same date always have exactly
   the same x pixel, so this collects them all.

   :param chart: the Chart.js instance
   :param e: the pointer event
   :param options: the chart's interaction options
   :param useFinalPosition: passed through to ``nearest``
   :type chart: **Object**
   :type e: **Object**
   :type options: **Object**
   :type useFinalPosition: **boolean**
   :returns: **Array** -- interaction items: ``{element, datasetIndex, index}``
.. js:function:: ..........s(s)

   Convert a chart data date string, ``YYYY-MM-DD`` or ``YYYY-MM``, to epoch
   milliseconds at local midnight on that day (the first of the month for
   ``YYYY-MM``). This is how the date-fns adapter reads the same strings for
   the time axis, so values from here can be compared with the axis's.

   :param s: date string from a chart data endpoint
   :type s: **string**
   :returns: **number** -- epoch milliseconds
.. js:function:: ..............e(elementId, ajaxdata, opts)

   Draw a zoomable, pannable line chart inside an existing element, replacing
   anything already in it. The element gets a row with the hint and a
   "Reset zoom" button (ID ``<elementId>-reset``), and a canvas (ID
   ``<elementId>-canvas``) in a fixed-height wrapper that follows the width
   of its panel.

   Plain drag zooms the date axis to the dragged range, Ctrl+scroll zooms it
   in or out around the pointer, and Ctrl+drag pans it; scrolling without Ctrl
   scrolls the page. The date axis never goes past the first or last date of
   the data, nor narrower than :js:func:`lineChartMinRange`. The value axis
   always fits the visible series within the visible dates. Clicking a legend
   entry hides or shows its series.

   :param elementId: ID of the element to draw the chart in
   :param ajaxdata: chart data endpoint response, as for :js:func:`lineChartDatasets`
   :param opts: options: ``currency`` (bool) formats values with :js:func:`fmt_currency` rather than to two decimal places; ``dateFormat`` (string) is the date-fns format for dates in tooltips, e.g. ``yyyy-MM-dd``; ``minUnit`` (string, default ``'day'``) is the smallest unit the date axis labels, ``'month'`` for monthly data. No chart's data is finer than a day, so the axis never labels times of day, even when it spans only a day or two.
   :type elementId: **string**
   :type ajaxdata: **Object**
   :type opts: **Object**
   :returns: **Object** -- the Chart.js instance
.. js:function:: ................s(ajaxdata)

   Convert a chart data endpoint response into Chart.js datasets: one per
   entry in ``keys``, in the same order. A dataset's points are the rows that
   have a non-null value for its key; a row without one is a gap in that
   series, which the line joins across, never a zero.

   :param ajaxdata: endpoint response, with ``keys`` (series names) and ``data`` (one object per date, with a ``date`` property and a property per series that has a value on that date)
   :type ajaxdata: **Object**
   :returns: **Array** -- Chart.js dataset objects
.. js:function:: ................e(ajaxdata)

   The narrowest date range, in milliseconds, that a chart may be zoomed to:
   the widest gap between consecutive dates in its data. Any window at least
   that wide contains a data point, so a chart can never be zoomed into a
   stretch with nothing to show, which would leave its value axis with no
   values to fit. Zero when there are fewer than two dates.

   :param ajaxdata: endpoint response, as for :js:func:`lineChartDatasets`
   :type ajaxdata: **Object**
   :returns: **number** -- milliseconds
.. js:function:: ...............a(chart, ajaxdata)

   Replace a line chart's data in place, as when the Index page's range
   buttons load a different span of history or a fuel fill is added. The
   chart returns to its full view over the new data. Series hidden from the
   legend are shown again, since the new data may have different series. The
   canvas and the Chart.js instance are kept, so the container still holds
   exactly one chart.

   :param chart: Chart.js instance made by :js:func:`lineChartCreate`
   :param ajaxdata: chart data endpoint response, as for :js:func:`lineChartDatasets`
   :type chart: **Object**
   :type ajaxdata: **Object**
.. js:function:: ...................t(chart)

   Enable a chart's "Reset zoom" button exactly when the chart is zoomed or
   panned away from its full view.

   :param chart: Chart.js instance made by :js:func:`lineChartCreate`
   :type chart: **Object**
