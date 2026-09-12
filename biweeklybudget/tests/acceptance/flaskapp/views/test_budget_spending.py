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
"""

from datetime import date
from decimal import Decimal

import pytest
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper

URL = '/ajax/chart-data/budget-spending/by-period'

PERIOD_KEYS = [
    'current_pay_period', 'previous_pay_period', 'current_month',
    'previous_month', 'current_year', 'previous_year'
]

#: Sample data budget IDs (budgets are loaded in this order)
PERIODIC1 = 1
PERIODIC2 = 2
STANDING1 = 4
STANDING2 = 5
INCOME = 7


def load_page(helper, selenium, base_url):
    """Load the page and wait until the charts have been drawn."""
    helper.get(selenium, base_url + '/budgets/spending')
    WebDriverWait(selenium, 10).until(
        lambda d: d.find_element(
            By.ID, 'budget-spending-charts'
        ).get_attribute('data-loaded') == 'true'
    )


def table_rows(helper, selenium, key):
    """Return a period's table rows as lists of cell text."""
    return helper.tbody2textlist(
        selenium.find_element(By.ID, 'spending-%s-table' % key)
    )


def total(selenium, key):
    return Decimal(selenium.find_element(
        By.ID, 'spending-%s-total' % key
    ).get_attribute('data-amount'))


def is_nodata(selenium, key):
    return selenium.find_element(
        By.ID, 'spending-%s-nodata' % key
    ).is_displayed()


def credits(selenium, key):
    """Return a period's net credit list items' text, if shown."""
    div = selenium.find_element(By.ID, 'spending-%s-credits' % key)
    if not div.is_displayed():
        return []
    return [x.text for x in div.find_elements(By.TAG_NAME, 'li')]


def toggle(selenium, budget_id):
    selenium.find_element(
        By.ID, 'budget_spending_toggle_%d' % budget_id
    ).click()


#: What each period's table shows with the default selection (Standing1 is
#: marked "Omit from graphs" in the sample data, so it starts excluded).
DEFAULT_TABLES = {
    'current_pay_period': [
        ['Periodic2', '$222.22', '66.7%'],
        ['Periodic1', '$111.13', '33.3%'],
    ],
    'previous_pay_period': [],
    'current_month': [['Periodic2', '$222.22', '100.0%']],
    'previous_month': [
        ['Periodic2', '$222.22', '68.9%'],
        ['Periodic1', '$100.10', '31.1%'],
    ],
    'current_year': [
        ['Periodic2', '$444.44', '67.8%'],
        ['Periodic1', '$211.23', '32.2%'],
    ],
    'previous_year': [],
}

DEFAULT_TOTALS = {
    'current_pay_period': Decimal('333.35'),
    'previous_pay_period': Decimal('0.00'),
    'current_month': Decimal('222.22'),
    'previous_month': Decimal('322.32'),
    'current_year': Decimal('655.67'),
    'previous_year': Decimal('0.00'),
}


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestBudgetSpendingEndpoint(AcceptanceHelper):
    """
    ``GET /ajax/chart-data/budget-spending/by-period``, against the sample
    data at the acceptance test timestamp of 2017-07-28. The expected numbers
    are worked out by hand from ``tests/fixtures/sampledata.py``.
    """

    def test_response(self, base_url):
        r = requests.get(base_url + URL)
        assert r.status_code == 200
        assert r.json() == {
            'budgets': [
                {'id': PERIODIC1, 'name': 'Periodic1',
                 'omit_from_graphs': False},
                {'id': PERIODIC2, 'name': 'Periodic2',
                 'omit_from_graphs': False},
                {'id': STANDING1, 'name': 'Standing1',
                 'omit_from_graphs': True},
            ],
            'periods': [
                {
                    'key': 'current_pay_period',
                    'name': 'Current Pay Period',
                    'start_date': '2017-07-21', 'end_date': '2017-08-03',
                    'spending': [
                        {'budget_id': PERIODIC1, 'amount': 111.13},
                        {'budget_id': PERIODIC2, 'amount': 222.22},
                        {'budget_id': STANDING1, 'amount': -333.33},
                    ]
                },
                {
                    'key': 'previous_pay_period',
                    'name': 'Previous Pay Period',
                    'start_date': '2017-07-07', 'end_date': '2017-07-20',
                    'spending': []
                },
                {
                    'key': 'current_month', 'name': 'Current Month',
                    'start_date': '2017-07-01', 'end_date': '2017-07-31',
                    'spending': [
                        {'budget_id': PERIODIC2, 'amount': 222.22},
                        {'budget_id': STANDING1, 'amount': -333.33},
                    ]
                },
                {
                    'key': 'previous_month', 'name': 'Previous Month',
                    'start_date': '2017-06-01', 'end_date': '2017-06-30',
                    'spending': [
                        {'budget_id': PERIODIC1, 'amount': 100.1},
                        {'budget_id': PERIODIC2, 'amount': 222.22},
                    ]
                },
                {
                    'key': 'current_year', 'name': 'Current Year',
                    'start_date': '2017-01-01', 'end_date': '2017-12-31',
                    'spending': [
                        {'budget_id': PERIODIC1, 'amount': 211.23},
                        {'budget_id': PERIODIC2, 'amount': 444.44},
                        {'budget_id': STANDING1, 'amount': -333.33},
                    ]
                },
                {
                    'key': 'previous_year', 'name': 'Previous Year',
                    'start_date': '2016-01-01', 'end_date': '2016-12-31',
                    'spending': []
                },
            ]
        }

    def test_existing_by_month_unchanged(self, base_url):
        """FR-014: the Budgets page line charts' data does not change."""
        r = requests.get(
            base_url + '/ajax/chart-data/budget-spending/by-month'
        )
        assert r.json() == {
            'data': [
                {'date': '2017-06', 'Periodic1': 100.1,
                 'Periodic2': 222.22},
                {'date': '2017-07', 'Periodic2': 222.22},
            ],
            'keys': ['Periodic1', 'Periodic2']
        }

    def test_existing_by_pay_period_unchanged(self, base_url):
        """FR-014: the Budgets page line charts' data does not change."""
        r = requests.get(
            base_url + '/ajax/chart-data/budget-spending/by-pay-period'
        )
        assert r.json() == {
            'data': [
                {'date': '2017-06-23', 'Periodic1': 100.1,
                 'Periodic2': 222.22},
                {'date': '2017-07-07', 'Periodic1': 0.0, 'Periodic2': 0.0},
            ],
            'keys': ['Periodic1', 'Periodic2']
        }


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestBudgetSpendingPage(AcceptanceHelper):
    """
    The page with its default selection, and the budget checkboxes. Each test
    loads the page afresh, which also resets the selection.
    """

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        load_page(self, selenium, base_url)

    def test_heading(self, selenium):
        assert selenium.title == 'Spending By Budget - BiweeklyBudget'

    def test_titles_and_dates(self, selenium):
        expected = {
            'current_pay_period': (
                'Current Pay Period', '2017-07-21 to 2017-08-03'),
            'previous_pay_period': (
                'Previous Pay Period', '2017-07-07 to 2017-07-20'),
            'current_month': ('Current Month', '2017-07-01 to 2017-07-31'),
            'previous_month': ('Previous Month', '2017-06-01 to 2017-06-30'),
            'current_year': ('Current Year', '2017-01-01 to 2017-12-31'),
            'previous_year': ('Previous Year', '2016-01-01 to 2016-12-31'),
        }
        for key, (title, dates) in expected.items():
            assert selenium.find_element(
                By.ID, 'spending-%s-title' % key
            ).text == title
            assert selenium.find_element(
                By.ID, 'spending-%s-dates' % key
            ).text == dates

    def test_default_tables_and_totals(self, selenium):
        for key in PERIOD_KEYS:
            assert table_rows(self, selenium, key) == DEFAULT_TABLES[key], key
            assert total(selenium, key) == DEFAULT_TOTALS[key], key

    def test_rows_sum_to_total(self, selenium):
        for key in PERIOD_KEYS:
            table = selenium.find_element(By.ID, 'spending-%s-table' % key)
            amounts = [
                Decimal(td.get_attribute('data-amount'))
                for td in table.find_elements(
                    By.CSS_SELECTOR, 'tbody td[data-amount]'
                )
            ]
            assert sum(amounts, Decimal('0')) == total(selenium, key), key

    def test_charts_and_nodata(self, selenium):
        for key in PERIOD_KEYS:
            chart = selenium.find_element(By.ID, 'spending-%s-chart' % key)
            if DEFAULT_TABLES[key]:
                assert not is_nodata(selenium, key), key
                assert chart.is_displayed(), key
                # one donut segment per table row
                assert len(chart.find_elements(By.TAG_NAME, 'path')) >= len(
                    DEFAULT_TABLES[key]
                ), key
            else:
                assert is_nodata(selenium, key), key
                assert not chart.is_displayed(), key

    def test_default_selection(self, selenium):
        boxes = selenium.find_elements(
            By.CSS_SELECTOR, '#budget-spending-selection input'
        )
        assert [
            (int(b.get_attribute('data-budget-id')), b.is_selected())
            for b in boxes
        ] == [(PERIODIC1, True), (PERIODIC2, True), (STANDING1, False)]
        labels = selenium.find_elements(
            By.CSS_SELECTOR, '#budget-spending-selection label'
        )
        assert [x.text.strip() for x in labels] == [
            'Periodic1', 'Periodic2', 'Standing1'
        ]

    def test_omitted_budget_is_excluded_until_ticked(self, selenium):
        # excluded by default: not a slice and not a credit anywhere
        for key in PERIOD_KEYS:
            assert credits(selenium, key) == [], key
        toggle(selenium, STANDING1)
        # a net credit; listed, but neither charted nor in the total
        for key in ['current_pay_period', 'current_month', 'current_year']:
            assert credits(selenium, key) == ['Standing1: -$333.33'], key
        for key in PERIOD_KEYS:
            assert table_rows(self, selenium, key) == DEFAULT_TABLES[key]
            assert total(selenium, key) == DEFAULT_TOTALS[key]

    def test_untick_and_retick(self, selenium):
        toggle(selenium, PERIODIC2)
        assert table_rows(self, selenium, 'current_pay_period') == [
            ['Periodic1', '$111.13', '100.0%']
        ]
        assert total(selenium, 'current_pay_period') == Decimal('111.13')
        assert table_rows(self, selenium, 'current_month') == []
        assert is_nodata(selenium, 'current_month')
        assert table_rows(self, selenium, 'previous_month') == [
            ['Periodic1', '$100.10', '100.0%']
        ]
        assert total(selenium, 'current_year') == Decimal('211.23')
        # every total drops by exactly Periodic2's amount in that period
        p2 = {
            'current_pay_period': '222.22', 'previous_pay_period': '0',
            'current_month': '222.22', 'previous_month': '222.22',
            'current_year': '444.44', 'previous_year': '0'
        }
        for key in PERIOD_KEYS:
            assert total(selenium, key) == DEFAULT_TOTALS[key] - Decimal(
                p2[key]
            ), key
        toggle(selenium, PERIODIC2)
        for key in PERIOD_KEYS:
            assert table_rows(self, selenium, key) == DEFAULT_TABLES[key]
            assert total(selenium, key) == DEFAULT_TOTALS[key]
            assert is_nodata(selenium, key) == (not DEFAULT_TABLES[key])

    def test_untick_everything(self, selenium):
        toggle(selenium, PERIODIC1)
        toggle(selenium, PERIODIC2)
        for key in PERIOD_KEYS:
            assert is_nodata(selenium, key), key
            assert table_rows(self, selenium, key) == [], key
            assert total(selenium, key) == Decimal('0.00'), key

    def test_charts_fit_their_panels(self, selenium):
        """
        Each donut is drawn at its final width, after the tables that make
        the page tall enough to need a scrollbar. Drawn first, the charts
        kept a width from before the columns narrowed, overflowed them, and
        scrolled the page sideways.
        """

        def assert_fit():
            for key in PERIOD_KEYS:
                if not DEFAULT_TABLES[key]:
                    continue
                chart = selenium.find_element(
                    By.ID, 'spending-%s-chart' % key
                )
                svg = chart.find_element(By.TAG_NAME, 'svg')
                assert svg.rect['width'] <= chart.rect['width'] + 1, key
            assert selenium.execute_script(
                'return document.documentElement.scrollWidth <= '
                'document.documentElement.clientWidth;'
            )

        assert_fit()
        toggle(selenium, STANDING1)
        assert_fit()

    def test_colours_follow_the_budget(self, selenium):
        """FR-011: unticking one budget does not recolour the others."""

        def colour(budget_id):
            return selenium.find_element(
                By.CSS_SELECTOR,
                '#spending-current_year-table tr[data-budget-id="%d"] '
                '.budget-spending-swatch' % budget_id
            ).value_of_css_property('background-color')

        p1 = colour(PERIODIC1)
        assert p1 != colour(PERIODIC2)
        toggle(selenium, PERIODIC2)
        assert colour(PERIODIC1) == p1

    def test_reload_restores_default(self, selenium, base_url):
        toggle(selenium, PERIODIC2)
        toggle(selenium, STANDING1)
        load_page(self, selenium, base_url)
        for key in PERIOD_KEYS:
            assert table_rows(self, selenium, key) == DEFAULT_TABLES[key]
        assert not selenium.find_element(
            By.ID, 'budget_spending_toggle_%d' % STANDING1
        ).is_selected()


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestBudgetSpendingAddedData(AcceptanceHelper):
    """
    A budget whose name contains HTML, and a net credit on a budget that is
    included by default.
    """

    def test_0_add_data(self, testdb):
        acct = testdb.query(Account).get(1)
        evil = Budget(
            name='Evil <b>Budget</b> & Co', is_periodic=True,
            description='x', starting_balance=Decimal('10.00')
        )
        testdb.add(evil)
        testdb.add(Transaction(
            date=date(2017, 7, 27), budget_amounts={evil: Decimal('10.00')},
            description='evil', account=acct
        ))
        testdb.add(Transaction(
            date=date(2017, 7, 27),
            budget_amounts={
                testdb.query(Budget).get(STANDING2): Decimal('-15.00')
            },
            description='refund', account=acct
        ))
        testdb.flush()
        testdb.commit()

    def test_1_page(self, base_url, selenium):
        load_page(self, selenium, base_url)
        name = 'Evil <b>Budget</b> & Co'
        assert table_rows(self, selenium, 'current_pay_period') == [
            ['Periodic2', '$222.22', '64.7%'],
            ['Periodic1', '$111.13', '32.4%'],
            [name, '$10.00', '2.9%'],
        ]
        assert total(selenium, 'current_pay_period') == Decimal('343.35')
        # displayed as literal text, not markup
        table = selenium.find_element(
            By.ID, 'spending-current_pay_period-table'
        )
        assert table.find_elements(By.CSS_SELECTOR, 'tbody b') == []
        labels = [
            x.text.strip() for x in selenium.find_elements(
                By.CSS_SELECTOR, '#budget-spending-selection label'
            )
        ]
        assert name in labels
        # Standing2 is included by default; its net credit is listed, not
        # charted
        assert credits(selenium, 'current_pay_period') == [
            'Standing2: -$15.00'
        ]


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestBudgetSpendingLinks(AcceptanceHelper):

    def test_nav_link(self, base_url, selenium):
        self.get(selenium, base_url + '/')
        link = selenium.find_element(
            By.XPATH, '//ul[@id="side-menu"]//a[@href="/budgets/spending"]'
        )
        assert link.text.strip() == 'Spending Charts'
        link.click()
        assert selenium.current_url == base_url + '/budgets/spending'

    def test_budgets_page_link(self, base_url, selenium):
        self.get(selenium, base_url + '/budgets')
        link = selenium.find_element(By.ID, 'link-budget-spending')
        link.click()
        assert selenium.current_url == base_url + '/budgets/spending'
