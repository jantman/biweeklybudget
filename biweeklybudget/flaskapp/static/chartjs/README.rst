Vendored charting libraries
===========================

The application's charts are drawn with `Chart.js <https://www.chartjs.org/>`_ and
three companion packages. They are vendored here, unmodified, so that every chart works
with no internet access. Each file keeps its own licence header, and each package's
licence is beside it as ``LICENSE-<package>.md``. All four are MIT licensed.

========================== ======= ============================================ ==========================================================
Package                    Version File                                         Source
========================== ======= ============================================ ==========================================================
chart.js                   4.5.1   ``chart.umd.min.js``                         https://www.npmjs.com/package/chart.js/v/4.5.1
chartjs-adapter-date-fns   3.0.0   ``chartjs-adapter-date-fns.bundle.min.js``   https://www.npmjs.com/package/chartjs-adapter-date-fns/v/3.0.0
hammerjs                   2.0.8   ``hammer.min.js``                            https://www.npmjs.com/package/hammerjs/v/2.0.8
chartjs-plugin-zoom        2.2.0   ``chartjs-plugin-zoom.min.js``               https://www.npmjs.com/package/chartjs-plugin-zoom/v/2.2.0
========================== ======= ============================================ ==========================================================

Pages load them in the order above: Chart.js, then the date adapter, which gives the time
axis its date parsing and formatting and includes date-fns. Next Hammer.js, which the zoom
plugin needs for panning. The zoom plugin itself goes last. The line-chart pages then load
``/static/js/charts.js``, which is where every chart option is set.

Updating
--------

For each package, fetch the new version and copy the same file out of it::

    npm pack chart.js@<version>                  # package/dist/chart.umd.min.js
    npm pack chartjs-adapter-date-fns@<version>  # package/dist/chartjs-adapter-date-fns.bundle.min.js
    npm pack hammerjs@<version>                  # package/hammer.min.js
    npm pack chartjs-plugin-zoom@<version>       # package/dist/chartjs-plugin-zoom.min.js

Copy each package's ``LICENSE.md`` over the matching ``LICENSE-<package>.md``, update the
table above, and run the acceptance tests for the charts
(``tox -e acceptance -- -k "Chart or chart or BudgetSpending or Fuel"``).
