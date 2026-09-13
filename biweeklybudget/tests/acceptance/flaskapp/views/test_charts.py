"""
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

Acceptance tests for the zoomable, pannable line charts (GitHub issue #215),
drawn by ``static/js/charts.js``.

Every interaction is performed with real browser input -- drags, Ctrl+drags,
wheel turns and clicks -- and the result is read back from the Chart.js
instance through its public API. Chart animation is off, so a chart's state is
final as soon as an action returns, except for the zoom plugin's 250ms
debounce of the wheel's zoom-complete callback, which is waited for.
"""

import re
from datetime import date, timedelta
from decimal import Decimal

import pytest
import requests
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait

from biweeklybudget.models.account import Account
from biweeklybudget.models.account_balance import AccountBalance
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.utils import dtnow

#: (page, chart container ID, data endpoint, whether values are money) for
#: every line chart in the application
CHARTS = [
    ('/', 'account-balance-chart', '/ajax/chart-data/account-balances', True),
    (
        '/budgets', 'budget-per-period-chart',
        '/ajax/chart-data/budget-spending/by-pay-period', True
    ),
    (
        '/budgets', 'budget-per-month-chart',
        '/ajax/chart-data/budget-spending/by-month', True
    ),
    ('/fuel', 'mpg-chart', '/ajax/chart-data/fuel-economy', False),
    ('/fuel', 'fuel-price-chart', '/ajax/chart-data/fuel-prices', True),
]

#: Charts whose sample data has at least one point to hover. The sample data
#: has no fuel fill with a calculated MPG; TestFuelChartRefresh adds one.
HOVERABLE = [c for c in CHARTS if c[1] != 'mpg-chart']

HINT = 'Drag to zoom · Ctrl+drag to pan · Ctrl+scroll to zoom in/out'

#: The interaction settings every line chart must share (FR-001).
EXPECTED_INTERACTIONS = {
    'zoomMode': 'x',
    'drag': True,
    'wheel': True,
    'wheelKey': 'ctrl',
    'pan': True,
    'panKey': 'ctrl',
    'panMode': 'x',
    'limitMin': 'original',
    'limitMax': 'original',
    'legend': True,
    'legendPosition': 'bottom',
}

#: One day, in milliseconds.
DAY_MS = 86400000

STATE_JS = """
var c = Chart.getChart(arguments[0] + '-canvas');
if (!c) { return null; }
var z = c.options.plugins.zoom;
return {
  labels: c.data.datasets.map(function(d) { return d.label; }),
  data: c.data.datasets.map(function(d) {
    return d.data.map(function(p) { return [p.x, p.y]; });
  }),
  ms: c.data.datasets.map(function(d) {
    return d.data.map(function(p) { return c.scales.x.parse(p.x); });
  }),
  visible: c.data.datasets.map(function(d, i) {
    return c.isDatasetVisible(i);
  }),
  xmin: c.scales.x.min, xmax: c.scales.x.max,
  ymin: c.scales.y.min, ymax: c.scales.y.max,
  yticks: c.scales.y.ticks.map(function(t) { return t.value; }),
  zoomed: c.isZoomedOrPanned(),
  area: {
    left: c.chartArea.left, right: c.chartArea.right,
    top: c.chartArea.top, bottom: c.chartArea.bottom
  },
  canvasWidth: c.canvas.clientWidth, canvasHeight: c.canvas.clientHeight,
  minRange: z.limits.x.minRange,
  interactions: {
    zoomMode: z.zoom.mode, drag: !!z.zoom.drag.enabled,
    wheel: !!z.zoom.wheel.enabled, wheelKey: z.zoom.wheel.modifierKey,
    pan: !!z.pan.enabled, panKey: z.pan.modifierKey, panMode: z.pan.mode,
    limitMin: z.limits.x.min, limitMax: z.limits.x.max,
    legend: c.options.plugins.legend.display !== false,
    legendPosition: c.options.plugins.legend.position
  }
};
"""

LEGEND_JS = """
var c = Chart.getChart(arguments[0] + '-canvas');
return c.legend.legendItems.map(function(item, i) {
  var box = c.legend.legendHitBoxes[i];
  return {
    text: item.text, datasetIndex: item.datasetIndex, hidden: item.hidden,
    x: box.left + box.width / 2, y: box.top + box.height / 2
  };
});
"""

TOOLTIP_JS = """
var t = Chart.getChart(arguments[0] + '-canvas').tooltip;
return {
  opacity: t.opacity,
  title: t.title,
  lines: (t.body || []).map(function(b) { return b.lines.join(''); })
};
"""


def chart_state(selenium, elem_id):
    """Return the chart's state (see ``STATE_JS``), or None if not drawn."""
    return selenium.execute_script(STATE_JS, elem_id)


def wait_for_chart(selenium, elem_id):
    """Wait for a chart to be drawn and return its state."""
    WebDriverWait(selenium, 10).until(
        lambda d: chart_state(d, elem_id) is not None
    )
    return chart_state(selenium, elem_id)


def endpoint_datasets(base_url, url):
    """
    Return ``(keys, points)`` for what a chart must show: the endpoint's series
    names and, per series, ``[date, value]`` for every row with a value.
    """
    j = requests.get(base_url + url).json()
    keys = j.get('keys', ['price'])
    return keys, [
        [[r['date'], r[k]] for r in j['data'] if r.get(k) is not None]
        for k in keys
    ]


def to_canvas_offset(state, x, y):
    """Convert canvas pixel coordinates to an offset from its centre."""
    return (
        int(round(x - state['canvasWidth'] / 2.0)),
        int(round(y - state['canvasHeight'] / 2.0))
    )


def plot_x(state, fraction):
    """X pixel at ``fraction`` of the way across the plot area."""
    a = state['area']
    return a['left'] + fraction * (a['right'] - a['left'])


def drag(selenium, elem_id, x1, x2, ctrl=False):
    """
    Press the left button at canvas pixel x1 (half way down the plot area),
    move to x2 in several steps, and release; with Ctrl held if ``ctrl``.
    """
    state = chart_state(selenium, elem_id)
    canvas = selenium.find_element(By.ID, elem_id + '-canvas')
    y = (state['area']['top'] + state['area']['bottom']) / 2.0
    dx, dy = to_canvas_offset(state, x1, y)
    actions = ActionChains(selenium)
    if ctrl:
        actions.key_down(Keys.CONTROL)
    actions.move_to_element_with_offset(canvas, dx, dy).click_and_hold()
    steps = 5
    moved = 0
    for i in range(1, steps + 1):
        target = int(round((x2 - x1) * i / float(steps)))
        actions.move_by_offset(target - moved, 0)
        moved = target
    actions.release()
    if ctrl:
        actions.key_up(Keys.CONTROL)
    actions.perform()


def wheel(selenium, elem_id, delta_y, ctrl=False):
    """Turn the wheel over the centre of a chart, with Ctrl if ``ctrl``."""
    canvas = selenium.find_element(By.ID, elem_id + '-canvas')
    actions = ActionChains(selenium)
    if ctrl:
        actions.key_down(Keys.CONTROL)
    actions.scroll_from_origin(ScrollOrigin.from_element(canvas), 0, delta_y)
    if ctrl:
        actions.key_up(Keys.CONTROL)
    actions.perform()


def click_canvas(selenium, elem_id, x, y):
    """Click at canvas pixel coordinates."""
    state = chart_state(selenium, elem_id)
    canvas = selenium.find_element(By.ID, elem_id + '-canvas')
    dx, dy = to_canvas_offset(state, x, y)
    ActionChains(selenium).move_to_element_with_offset(
        canvas, dx, dy
    ).click().perform()


def reset_enabled(selenium, elem_id):
    return selenium.find_element(By.ID, elem_id + '-reset').is_enabled()


def wait_reset_enabled(selenium, elem_id, enabled):
    """The wheel's zoom-complete callback is debounced by 250ms."""
    WebDriverWait(selenium, 5).until(
        lambda d: reset_enabled(d, elem_id) == enabled
    )


def visible_values_in_view(state):
    """Every value of a visible series whose date is in the visible range."""
    vals = []
    for idx, pts in enumerate(state['data']):
        if not state['visible'][idx]:
            continue
        for (_, y), ms in zip(pts, state['ms'][idx]):
            if state['xmin'] <= ms <= state['xmax']:
                vals.append(y)
    return vals


def assert_value_axis_fits(state):
    """
    FR-005: the value axis spans the visible values in view, extended by no
    more than Chart.js's rounding out to the next tick at either end.
    """
    vals = visible_values_in_view(state)
    assert vals, 'no visible data in view'
    step = state['yticks'][1] - state['yticks'][0]
    lo, hi = min(vals), max(vals)
    assert state['ymin'] <= lo
    assert state['ymax'] >= hi
    assert state['ymin'] > lo - step - 0.01
    assert state['ymax'] < hi + step + 0.01


def severe_browser_errors(selenium):
    return [
        x for x in selenium.get_log('browser')
        if x['level'] == 'SEVERE' and 'favicon' not in x['message']
    ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestLineChartsCommon(AcceptanceHelper):
    """
    What every one of the five line charts must have in common: the same
    markup, the endpoint's data, and the same interactions (FR-001).
    """

    def load(self, selenium, base_url, page, elem_id):
        self.get(selenium, base_url + page)
        self.wait_for_jquery_done(selenium)
        return wait_for_chart(selenium, elem_id)

    @pytest.mark.parametrize('page,elem_id,url,currency', CHARTS)
    def test_markup(self, selenium, base_url, page, elem_id, url, currency):
        self.load(selenium, base_url, page, elem_id)
        container = selenium.find_element(By.ID, elem_id)
        assert len(container.find_elements(By.TAG_NAME, 'canvas')) == 1
        hint = container.find_element(By.CSS_SELECTOR, '.chart-hint')
        assert hint.text == HINT
        reset = container.find_element(By.ID, elem_id + '-reset')
        assert reset.text == 'Reset zoom'
        assert not reset.is_enabled()

    @pytest.mark.parametrize('page,elem_id,url,currency', CHARTS)
    def test_datasets_match_endpoint(
        self, selenium, base_url, page, elem_id, url, currency
    ):
        state = self.load(selenium, base_url, page, elem_id)
        keys, points = endpoint_datasets(base_url, url)
        assert state['labels'] == keys
        assert state['data'] == points
        assert all(state['visible'])

    @pytest.mark.parametrize('page,elem_id,url,currency', CHARTS)
    def test_same_interactions(
        self, selenium, base_url, page, elem_id, url, currency
    ):
        state = self.load(selenium, base_url, page, elem_id)
        assert state['interactions'] == EXPECTED_INTERACTIONS
        assert state['zoomed'] is False

    @pytest.mark.parametrize('page,elem_id,url,currency', HOVERABLE)
    def test_tooltip(self, selenium, base_url, page, elem_id, url, currency):
        state = self.load(selenium, base_url, page, elem_id)
        # hover the first series' last point
        idx = len(state['data'][0]) - 1
        when, _ = state['data'][0][idx]
        x = selenium.execute_script(
            "var c = Chart.getChart(arguments[0] + '-canvas');"
            "return c.scales.x.getPixelForValue(arguments[1]);",
            elem_id, state['ms'][0][idx]
        )
        y = (state['area']['top'] + state['area']['bottom']) / 2.0
        canvas = selenium.find_element(By.ID, elem_id + '-canvas')
        dx, dy = to_canvas_offset(state, x, y)
        ActionChains(selenium).move_to_element_with_offset(
            canvas, dx, dy
        ).perform()
        tip = selenium.execute_script(TOOLTIP_JS, elem_id)
        assert tip['opacity'] > 0
        assert tip['title'] == [when]
        # one line per visible series with a point on that date
        expected = [
            state['labels'][i] for i, pts in enumerate(state['data'])
            if when in [p[0] for p in pts]
        ]
        assert [x.split(': ')[0] for x in tip['lines']] == expected
        if currency:
            pattern = r'^.+: -?\$[0-9,]+\.[0-9]{2}$'
        else:
            pattern = r'^.+: -?[0-9]+\.[0-9]{2}$'
        for line in tip['lines']:
            assert re.match(pattern, line), line

    @pytest.mark.parametrize('page,elem_id,url,currency', CHARTS)
    def test_fits_panel_after_resize(
        self, selenium, base_url, page, elem_id, url, currency
    ):
        state = self.load(selenium, base_url, page, elem_id)
        before = state['canvasWidth']

        def assert_fits():
            container = selenium.find_element(By.ID, elem_id)
            canvas = selenium.find_element(By.ID, elem_id + '-canvas')
            assert canvas.rect['width'] <= container.rect['width'] + 1
            # The chart never reaches past the window. (Whether the page as
            # a whole scrolls sideways is not the chart's doing: at 1100px
            # the Fuel Log's own table is wider than the window.)
            assert container.rect['x'] + container.rect['width'] <= \
                selenium.execute_script(
                    'return document.documentElement.clientWidth;'
                ) + 1

        assert_fits()
        selenium.set_window_size(1100, 900)
        WebDriverWait(selenium, 5).until(
            lambda d: chart_state(d, elem_id)['canvasWidth'] != before
        )
        assert_fits()

    @pytest.mark.parametrize('page', ['/', '/budgets', '/fuel'])
    def test_no_browser_errors(self, selenium, base_url, page):
        self.get(selenium, base_url + page)
        self.wait_for_jquery_done(selenium)
        assert severe_browser_errors(selenium) == []


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'testflask')
class TestLineChartInteraction(AcceptanceHelper):
    """
    Zoom, pan, reset and legend behaviour (US1-US3), on the Account Balances
    chart. Every line chart is built by the same function with the same
    options (TestLineChartsCommon.test_same_interactions), so these hold for
    all five. The sample data has only five balance dates, too few to zoom
    into, so these tests add ``SEED_DAYS`` of daily balances to BankOne.
    ``class_refresh_db`` restores the database afterwards.
    """

    ELEM = 'account-balance-chart'
    SEED_DAYS = 200

    @pytest.fixture
    def seed(self, refreshdb, testdb):
        # after refreshdb has restored the sample data, whatever its scope
        if testdb.query(AccountBalance).filter(
            AccountBalance.account_id == 1
        ).count() >= self.SEED_DAYS:
            return
        end = dtnow()
        for i in range(0, self.SEED_DAYS):
            d = end - timedelta(days=i)
            testdb.add(AccountBalance(
                account_id=1,
                ledger=Decimal('3000.00') - Decimal(5 * i),
                ledger_date=d,
                avail=Decimal('3000.00') - Decimal(5 * i),
                avail_date=d,
                overall_date=d
            ))
        testdb.commit()

    @pytest.fixture(autouse=True)
    def get_page(self, seed, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url)
        self.wait_for_jquery_done(selenium)
        self.full = wait_for_chart(selenium, self.ELEM)
        assert len(self.full['data'][0]) >= self.SEED_DAYS - 1

    def state(self, selenium):
        return chart_state(selenium, self.ELEM)

    def zoom_to(self, selenium, f1, f2):
        """Drag-select from fraction f1 to f2 of the plot area's width."""
        drag(selenium, self.ELEM, plot_x(self.full, f1), plot_x(self.full, f2))
        return self.state(selenium)

    def test_drag_zooms_to_the_selection(self, selenium):
        full = self.full
        span = full['xmax'] - full['xmin']
        lo = full['xmin'] + 0.1 * span
        hi = full['xmin'] + 0.4 * span
        s = self.zoom_to(selenium, 0.1, 0.4)
        assert s['zoomed'] is True
        # the new range is the selection, to within a pixel's worth of time
        pixel = span / (full['area']['right'] - full['area']['left'])
        assert abs(s['xmin'] - lo) < 3 * pixel
        assert abs(s['xmax'] - hi) < 3 * pixel
        assert reset_enabled(selenium, self.ELEM)

    def test_value_axis_follows_the_zoom(self, selenium):
        # the full view includes InvestmentOne's ~$10k balance, at the right
        assert self.full['ymax'] > 10000
        s = self.zoom_to(selenium, 0.1, 0.4)
        # zoomed into the seeded-only stretch at the left, the axis fits
        # BankOne's balances there rather than the full view's
        assert s['ymax'] < 3000
        assert (s['ymax'] - s['ymin']) < (self.full['ymax'] - self.full['ymin'])
        assert_value_axis_fits(s)

    def test_second_drag_narrows_further(self, selenium):
        first = self.zoom_to(selenium, 0.1, 0.6)
        drag(
            selenium, self.ELEM, plot_x(first, 0.25), plot_x(first, 0.75)
        )
        second = self.state(selenium)
        assert second['xmin'] > first['xmin']
        assert second['xmax'] < first['xmax']
        assert_value_axis_fits(second)

    def test_reset_returns_to_full_view(self, selenium):
        assert not reset_enabled(selenium, self.ELEM)
        self.zoom_to(selenium, 0.2, 0.5)
        selenium.find_element(By.ID, self.ELEM + '-reset').click()
        s = self.state(selenium)
        assert s['zoomed'] is False
        assert (s['xmin'], s['xmax']) == (self.full['xmin'], self.full['xmax'])
        assert (s['ymin'], s['ymax']) == (self.full['ymin'], self.full['ymax'])
        assert not reset_enabled(selenium, self.ELEM)

    def test_plain_wheel_scrolls_the_page_not_the_chart(self, selenium):
        selenium.set_window_size(1920, 600)
        self.full = wait_for_chart(selenium, self.ELEM)
        assert selenium.execute_script('return window.scrollY;') == 0
        wheel(selenium, self.ELEM, 200)
        WebDriverWait(selenium, 5).until(
            lambda d: d.execute_script('return window.scrollY;') > 0
        )
        s = self.state(selenium)
        assert s['zoomed'] is False
        assert (s['xmin'], s['xmax']) == (self.full['xmin'], self.full['xmax'])

    def test_ctrl_wheel_zooms_in_and_out(self, selenium):
        full_span = self.full['xmax'] - self.full['xmin']
        wheel(selenium, self.ELEM, -200, ctrl=True)
        wait_reset_enabled(selenium, self.ELEM, True)
        zin = self.state(selenium)
        assert (zin['xmax'] - zin['xmin']) < full_span
        # the page did not zoom or scroll instead
        assert selenium.execute_script('return window.scrollY;') == 0
        for _ in range(10):
            wheel(selenium, self.ELEM, 200, ctrl=True)
        zout = self.state(selenium)
        assert (zout['xmax'] - zout['xmin']) > (zin['xmax'] - zin['xmin'])
        # never past the ends of the data
        assert zout['xmin'] >= self.full['xmin']
        assert zout['xmax'] <= self.full['xmax']

    def test_zoom_in_stops_at_the_widest_gap(self, selenium):
        # daily data: the narrowest allowed range is one day
        assert self.full['minRange'] == DAY_MS
        for _ in range(40):
            wheel(selenium, self.ELEM, -300, ctrl=True)
        s = self.state(selenium)
        assert (s['xmax'] - s['xmin']) >= DAY_MS - 1
        # and there is still data in view to fit the value axis to
        assert_value_axis_fits(s)

    def test_ctrl_drag_pans_keeping_the_width(self, selenium):
        z = self.zoom_to(selenium, 0.4, 0.6)
        width = z['xmax'] - z['xmin']
        # dragging the plot to the right brings earlier dates into view
        drag(selenium, self.ELEM, plot_x(z, 0.3), plot_x(z, 0.6), ctrl=True)
        p = self.state(selenium)
        pixel = width / (z['area']['right'] - z['area']['left'])
        assert p['xmin'] < z['xmin'] - 10 * pixel
        assert abs((p['xmax'] - p['xmin']) - width) < pixel
        assert_value_axis_fits(p)
        assert reset_enabled(selenium, self.ELEM)

    def test_pan_stops_at_the_start_of_the_data(self, selenium):
        self.zoom_to(selenium, 0.4, 0.6)
        for _ in range(4):
            z = self.state(selenium)
            drag(
                selenium, self.ELEM, plot_x(z, 0.05), plot_x(z, 0.95),
                ctrl=True
            )
        p = self.state(selenium)
        assert p['xmin'] == self.full['xmin']
        assert p['zoomed'] is True

    def test_legend_hides_and_shows_a_series(self, selenium):
        items = selenium.execute_script(LEGEND_JS, self.ELEM)
        assert [i['text'] for i in items] == self.full['labels']
        # the series with the highest value sets the top of the axis
        maxes = [max(p[1] for p in pts) for pts in self.full['data']]
        big = maxes.index(max(maxes))
        others = max(m for i, m in enumerate(maxes) if i != big)
        assert others < maxes[big]
        click_canvas(selenium, self.ELEM, items[big]['x'], items[big]['y'])
        s = self.state(selenium)
        assert s['visible'][big] is False
        assert selenium.execute_script(LEGEND_JS, self.ELEM)[big]['hidden']
        # the axis refits to the series still shown
        assert s['ymax'] < self.full['ymax']
        assert_value_axis_fits(s)
        # and a legend click is not a drag-zoom
        assert s['zoomed'] is False
        click_canvas(selenium, self.ELEM, items[big]['x'], items[big]['y'])
        s = self.state(selenium)
        assert all(s['visible'])
        assert (s['ymin'], s['ymax']) == (self.full['ymin'], self.full['ymax'])

    def test_reset_keeps_hidden_series_hidden(self, selenium):
        items = selenium.execute_script(LEGEND_JS, self.ELEM)
        big = self.full['labels'].index('InvestmentOne')
        click_canvas(selenium, self.ELEM, items[big]['x'], items[big]['y'])
        self.zoom_to(selenium, 0.2, 0.5)
        selenium.find_element(By.ID, self.ELEM + '-reset').click()
        s = self.state(selenium)
        assert s['zoomed'] is False
        assert s['visible'][big] is False

    def test_reload_restores_full_view_and_all_series(self, selenium):
        items = selenium.execute_script(LEGEND_JS, self.ELEM)
        click_canvas(selenium, self.ELEM, items[0]['x'], items[0]['y'])
        self.zoom_to(selenium, 0.2, 0.5)
        selenium.refresh()
        self.wait_for_jquery_done(selenium)
        s = wait_for_chart(selenium, self.ELEM)
        assert all(s['visible'])
        assert s['zoomed'] is False
        assert (s['xmin'], s['xmax']) == (self.full['xmin'], self.full['xmax'])

    def test_new_range_resets_view_and_limits(self, selenium):
        self.zoom_to(selenium, 0.2, 0.5)
        selenium.find_element(
            By.CSS_SELECTOR, '#account-balance-chart-ranges button[data-days="30"]'
        ).click()
        self.wait_for_jquery_done(selenium)
        s = self.state(selenium)
        assert s['zoomed'] is False
        assert not reset_enabled(selenium, self.ELEM)
        assert len(selenium.find_element(By.ID, self.ELEM).find_elements(
            By.TAG_NAME, 'canvas'
        )) == 1
        assert s['xmin'] > self.full['xmin']
        # the pan limits follow the new data, not the old
        month = s
        drag(selenium, self.ELEM, plot_x(month, 0.4), plot_x(month, 0.6))
        for _ in range(3):
            z = self.state(selenium)
            drag(
                selenium, self.ELEM, plot_x(z, 0.05), plot_x(z, 0.95),
                ctrl=True
            )
        assert self.state(selenium)['xmin'] == month['xmin']


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestLineChartLiteralNames(AcceptanceHelper):
    """Series names are drawn as literal text, never parsed as HTML."""

    NAME = 'Evil <b>Budget</b> & Co'

    def test_0_add_data(self, testdb):
        evil = Budget(
            name=self.NAME, is_periodic=True, description='x',
            starting_balance=Decimal('10.00')
        )
        testdb.add(evil)
        testdb.add(Transaction(
            date=date(2017, 7, 27), budget_amounts={evil: Decimal('10.00')},
            description='evil', account=testdb.query(Account).get(1)
        ))
        testdb.flush()
        testdb.commit()

    def test_1_names_are_literal(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        self.wait_for_jquery_done(selenium)
        state = wait_for_chart(selenium, 'budget-per-month-chart')
        assert self.NAME in state['labels']
        items = selenium.execute_script(LEGEND_JS, 'budget-per-month-chart')
        assert self.NAME in [i['text'] for i in items]
        assert selenium.find_element(
            By.ID, 'budget-per-month-chart'
        ).find_elements(By.TAG_NAME, 'b') == []


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
class TestFuelChartRefresh(AcceptanceHelper):
    """FR-012: adding a fuel fill redraws both fuel charts in place."""

    CHARTS = [
        ('mpg-chart', '/ajax/chart-data/fuel-economy'),
        ('fuel-price-chart', '/ajax/chart-data/fuel-prices'),
    ]

    def test_adding_a_fill_updates_both_charts(self, base_url, selenium):
        self.get(selenium, base_url + '/fuel')
        self.wait_for_jquery_done(selenium)
        before = {
            elem_id: wait_for_chart(selenium, elem_id)['data']
            for elem_id, _ in self.CHARTS
        }
        when = (dtnow() - timedelta(days=3)).date().strftime('%Y-%m-%d')
        link = selenium.find_element(By.ID, 'btn-add-fuel')
        self.wait_until_clickable(selenium, 'btn-add-fuel')
        modal, title, body = self.try_click_and_get_modal(selenium, link)
        self.assert_modal_displayed(modal, title, body)
        Select(
            selenium.find_element(By.ID, 'fuel_frm_vehicle')
        ).select_by_value('2')
        for elem_id, value in [
            ('fuel_frm_date', when),
            ('fuel_frm_odo_miles', '1123'),
            ('fuel_frm_reported_miles', '123'),
            ('fuel_frm_fill_loc', 'Fill Location'),
            ('fuel_frm_cost_per_gallon', '1.239'),
            ('fuel_frm_total_cost', '12.34'),
            ('fuel_frm_gallons', '6.789'),
            ('fuel_frm_reported_mpg', '34.5'),
        ]:
            elem = selenium.find_element(By.ID, elem_id)
            elem.clear()
            elem.send_keys(value)
        Select(
            selenium.find_element(By.ID, 'fuel_frm_level_before')
        ).select_by_value('50')
        Select(
            selenium.find_element(By.ID, 'fuel_frm_level_after')
        ).select_by_value('90')
        add_trans = selenium.find_element(By.ID, 'fuel_frm_add_trans')
        add_trans.click()
        assert add_trans.is_selected() is False
        selenium.find_element(By.ID, 'modalSaveButton').click()
        self.wait_for_jquery_done(selenium)
        _, _, body = self.get_modal_parts(selenium)
        x = body.find_elements(By.TAG_NAME, 'div')[0]
        assert 'alert-success' in x.get_attribute('class')
        selenium.find_element(By.ID, 'modalCloseButton').click()
        self.wait_for_jquery_done(selenium)

        for elem_id, url in self.CHARTS:
            # the endpoint now has different data, and the chart shows it
            _, points = endpoint_datasets(base_url, url)
            assert points != before[elem_id], elem_id
            WebDriverWait(selenium, 10).until(
                lambda d: chart_state(d, elem_id)['data'] == points
            )
        # including the new fill's price, on its date
        assert [when, 1.239] in chart_state(
            selenium, 'fuel-price-chart'
        )['data'][0]
        for elem_id, _ in self.CHARTS:
            assert len(selenium.find_element(By.ID, elem_id).find_elements(
                By.TAG_NAME, 'canvas'
            )) == 1
            assert chart_state(selenium, elem_id)['zoomed'] is False
