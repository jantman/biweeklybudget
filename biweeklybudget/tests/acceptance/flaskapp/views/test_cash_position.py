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

from decimal import Decimal

import pytest
from selenium.webdriver.common.by import By

from biweeklybudget.cashposition import CashPosition
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.utils import fmt_currency


def amount(elem):
    """Return an element's ``data-amount`` as a Decimal."""
    return Decimal(elem.get_attribute('data-amount'))


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestCashPositionWaterfall(AcceptanceHelper):
    """
    User Story 1: see the whole calculation, not just its conclusion.
    """

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/cash-position')

    def test_heading(self, selenium):
        assert selenium.title == 'Cash Position - BiweeklyBudget'

    def test_waterfall_rows_present_and_ordered(self, selenium):
        """
        The five terms and two subtotals, in the order the contract fixes.
        """
        table = selenium.find_element(By.ID, 'cash-position-waterfall')
        ids = [
            row.get_attribute('id')
            for row in table.find_elements(By.XPATH, './/tbody/tr')
        ]
        assert ids == [
            'waterfall-budget-accounts',
            'waterfall-unreconciled',
            'waterfall-credit',
            'subtotal-net-liquid',
            'waterfall-standing',
            'waterfall-payperiod',
            'total-uncommitted'
        ]

    def test_terms_match_the_calculation(self, selenium, testdb):
        cp = CashPosition(testdb)
        expected = {
            'waterfall-budget-accounts': cp.budget_account_ledger,
            'waterfall-unreconciled': cp.unreconciled,
            'waterfall-credit': cp.credit_balance,
            'subtotal-net-liquid': cp.net_liquid,
            'waterfall-standing': cp.standing_total,
            'waterfall-payperiod': cp.pay_period_allocated_unspent,
            'total-uncommitted': cp.uncommitted
        }
        for elem_id, value in expected.items():
            assert amount(
                selenium.find_element(By.ID, elem_id)
            ) == value, elem_id

    def test_subtotals_follow_from_the_terms(self, selenium):
        """
        The two subtotals must be what the rows above them actually add up
        to. Read off the page rather than from the model, so that a template
        that displayed the right numbers in the wrong places would fail.
        """
        ledger = amount(
            selenium.find_element(By.ID, 'waterfall-budget-accounts')
        )
        unrec = amount(selenium.find_element(By.ID, 'waterfall-unreconciled'))
        credit = amount(selenium.find_element(By.ID, 'waterfall-credit'))
        net = amount(selenium.find_element(By.ID, 'subtotal-net-liquid'))
        standing = amount(selenium.find_element(By.ID, 'waterfall-standing'))
        pp = amount(selenium.find_element(By.ID, 'waterfall-payperiod'))
        uncommitted = amount(
            selenium.find_element(By.ID, 'total-uncommitted')
        )
        assert net == ledger - unrec + credit
        assert uncommitted == net - standing - pp

    def test_bottom_line_matches_the_notification_banner(self, selenium,
                                                         base_url, testdb):
        """
        The whole point of the page (FR-004). Its final figure must equal the
        amount by which the banner says available funds differ from allocated
        funds -- the two are the same calculation, and a page that disagreed
        with the banner would be worse than no page.
        """
        uncommitted = amount(
            selenium.find_element(By.ID, 'total-uncommitted')
        )
        cp = CashPosition(testdb)
        banner_difference = (
            (cp.budget_account_ledger + cp.credit_balance) - (
                cp.standing_total +
                cp.pay_period_allocated_unspent +
                cp.unreconciled
            )
        )
        assert uncommitted == banner_difference

    def test_negative_amounts_are_distinguished(self, selenium):
        """
        A negative subtotal is a legitimate and important state; it must be
        visually distinct rather than clamped or shown unsigned.
        """
        row = selenium.find_element(By.ID, 'total-uncommitted')
        assert amount(row) < Decimal('0')
        assert len(row.find_elements(By.CLASS_NAME, 'text-danger')) > 0

    def test_credit_sign_is_explained(self, selenium):
        """
        The sign convention on credit balances is the source of the error
        corrected in issue #320, so the page must say what it is.
        """
        text = selenium.find_element(By.ID, 'waterfall-credit').text
        assert 'negative' in text

    def test_pay_period_is_reported(self, selenium):
        elem = selenium.find_element(By.ID, 'cash-position-as-of')
        assert 'Current pay period' in elem.text


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestCashPositionItemization(AcceptanceHelper):
    """
    User Story 2: trace any line back to where it came from.
    """

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/cash-position')

    def _rows(self, selenium, table_id):
        table = selenium.find_element(By.ID, table_id)
        return table.find_elements(By.XPATH, './/tbody/tr[@data-amount]')

    def test_budget_accounts_itemized_by_name(self, selenium, testdb):
        cp = CashPosition(testdb)
        rows = self._rows(selenium, 'table-budget-account-detail')
        names = [r.find_elements(By.TAG_NAME, 'td')[0].text for r in rows]
        assert names == [x.account.name for x in cp.budget_account_lines]

    def test_budget_account_rows_sum_to_the_waterfall_term(self, selenium):
        rows = self._rows(selenium, 'table-budget-account-detail')
        total = sum((amount(r) for r in rows), Decimal('0'))
        assert total == amount(
            selenium.find_element(By.ID, 'waterfall-budget-accounts')
        )
        assert total == amount(
            selenium.find_element(By.ID, 'total-budget-account-detail')
        )

    def test_credit_account_rows_sum_to_the_waterfall_term(self, selenium):
        rows = self._rows(selenium, 'table-credit-account-detail')
        total = sum((amount(r) for r in rows), Decimal('0'))
        assert total == amount(selenium.find_element(By.ID, 'waterfall-credit'))
        assert total == amount(
            selenium.find_element(By.ID, 'total-credit-account-detail')
        )

    def test_standing_budget_rows_sum_to_the_waterfall_term(self, selenium):
        rows = self._rows(selenium, 'table-standing-budget-detail')
        total = sum((amount(r) for r in rows), Decimal('0'))
        assert total == amount(
            selenium.find_element(By.ID, 'waterfall-standing')
        )
        assert total == amount(
            selenium.find_element(By.ID, 'total-standing-budget-detail')
        )

    def fmt(self, value):
        """Format a Decimal the way the ``dollars`` template filter does."""
        return fmt_currency(value)

    def test_projected_balance_shown_beside_ledger(self, selenium, testdb):
        """
        A ledger balance days out of date is misleading on its own, so each
        account shows what it is projected to hold once its unreconciled
        transactions land.
        """
        cp = CashPosition(testdb)
        by_name = {x.account.name: x for x in cp.budget_account_lines}
        rows = self._rows(selenium, 'table-budget-account-detail')
        checked = 0
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            line = by_name[cells[0].text]
            if not line.has_balance:
                continue
            assert cells[1].text == self.fmt(line.ledger)
            assert cells[2].text == self.fmt(line.unreconciled)
            assert cells[3].text == self.fmt(line.projected)
            checked += 1
        assert checked > 0

    def test_aggregate_links(self, selenium):
        expected = {
            'waterfall-budget-accounts': '/accounts',
            'waterfall-unreconciled': '/reconcile',
            'waterfall-credit': '/accounts',
            'waterfall-standing': '/budgets',
            'waterfall-payperiod': '/pay_period_for'
        }
        for elem_id, url in expected.items():
            row = selenium.find_element(By.ID, elem_id)
            link = row.find_element(By.TAG_NAME, 'a')
            assert self.relurl(link.get_attribute('href')) == url, elem_id

    def test_account_rows_link_to_their_own_view(self, selenium, testdb):
        cp = CashPosition(testdb)
        by_name = {x.account.name: x for x in cp.budget_account_lines}
        for row in self._rows(selenium, 'table-budget-account-detail'):
            link = row.find_element(By.TAG_NAME, 'a')
            expected = '/accounts/%d' % by_name[link.text].account.id
            assert self.relurl(link.get_attribute('href')) == expected

    def test_budget_rows_link_to_their_own_view(self, selenium, testdb):
        cp = CashPosition(testdb)
        by_name = {x.budget.name: x for x in cp.standing_budget_lines}
        for row in self._rows(selenium, 'table-standing-budget-detail'):
            link = row.find_element(By.TAG_NAME, 'a')
            expected = '/budgets/%d' % by_name[link.text].budget.id
            assert self.relurl(link.get_attribute('href')) == expected


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb', 'testflask')
class TestCashPositionDiagnostics(AcceptanceHelper):
    """
    User Story 3: explain structurally unallocated money.

    The sample data links both standing budgets to BankOne and leaves
    BankTwoStale linked to nothing, which exercises the coverage group and
    the unlinked-account call-out at once.
    """

    @pytest.fixture(autouse=True)
    def get_page(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/cash-position')

    def test_diagnostics_panel_present(self, selenium):
        assert selenium.find_element(
            By.ID, 'cash-position-diagnostics'
        ) is not None

    def test_not_configured_message_absent(self, selenium):
        """
        Links *are* configured in the sample data, so the "not configured"
        message must not appear -- otherwise it would be shown to somebody
        who had configured them.
        """
        assert selenium.find_elements(
            By.ID, 'diagnostics-not-configured'
        ) == []

    def test_unlinked_account_is_named(self, selenium, testdb):
        cp = CashPosition(testdb)
        expected = [x.account.name for x in cp.unlinked_accounts]
        assert expected != []
        table = selenium.find_element(By.ID, 'table-unlinked-accounts')
        rows = table.find_elements(By.XPATH, './/tbody/tr')
        names = [r.find_elements(By.TAG_NAME, 'td')[0].text for r in rows]
        assert names == expected

    def test_unlinked_account_is_explained(self, selenium):
        panel = selenium.find_element(By.ID, 'cash-position-diagnostics')
        assert 'nothing allocates' in panel.text

    def test_coverage_group_rendered(self, selenium, testdb):
        cp = CashPosition(testdb)
        assert len(cp.coverage_groups) == 1
        group = cp.coverage_groups[0]
        elem = selenium.find_element(By.ID, 'coverage-group-1')
        assert Decimal(elem.get_attribute('data-delta')) == group.delta
        assert elem.get_attribute('data-simple') == 'true'
        assert elem.get_attribute('data-balanced') == (
            'true' if group.is_balanced else 'false'
        )

    def test_single_account_group_reports_a_per_account_delta(self, selenium):
        """
        A group holding one account has a well-defined per-account delta and
        should say so. A multi-account group must not, since nothing records
        how a budget's balance splits across its accounts.
        """
        elem = selenium.find_element(By.ID, 'coverage-group-1')
        assert elem.get_attribute('data-simple') == 'true'
        assert 'Unexplained difference for this account' in elem.text

    def test_group_shows_both_sides_and_the_difference(self, selenium,
                                                       testdb):
        cp = CashPosition(testdb)
        group = cp.coverage_groups[0]
        text = selenium.find_element(By.ID, 'coverage-group-1').text
        assert 'Accounts hold' in text
        assert 'Budgets claim' in text
        for line in group.budgets:
            assert line.budget.name in text
        for line in group.accounts:
            assert line.account.name in text


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb', 'testflask')
@pytest.mark.incremental
class TestCashPositionNoLinks(AcceptanceHelper):
    """
    The state of every installation immediately after the migration that
    added budget/account links: none configured. The waterfall must be
    unaffected, and the page must say the links are not configured rather
    than implying every account is a problem.
    """

    def test_0_remove_links(self, testdb):
        for budget in testdb.query(Budget).all():
            budget.accounts = []
            testdb.add(budget)
        testdb.flush()
        testdb.commit()

    def test_1_waterfall_unaffected(self, base_url, selenium, testdb):
        self.baseurl = base_url
        self.get(selenium, base_url + '/cash-position')
        cp = CashPosition(testdb)
        assert amount(
            selenium.find_element(By.ID, 'total-uncommitted')
        ) == cp.uncommitted

    def test_2_not_configured_message(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/cash-position')
        elem = selenium.find_element(By.ID, 'diagnostics-not-configured')
        assert 'No budget/account links are configured' in elem.text

    def test_3_every_funding_account_unlinked(self, base_url, selenium,
                                              testdb):
        self.baseurl = base_url
        self.get(selenium, base_url + '/cash-position')
        cp = CashPosition(testdb)
        table = selenium.find_element(By.ID, 'table-unlinked-accounts')
        rows = table.find_elements(By.XPATH, './/tbody/tr')
        assert len(rows) == len(cp.budget_account_lines)

    def test_4_no_coverage_groups(self, base_url, selenium):
        self.baseurl = base_url
        self.get(selenium, base_url + '/cash-position')
        assert selenium.find_elements(By.ID, 'coverage-group-1') == []
