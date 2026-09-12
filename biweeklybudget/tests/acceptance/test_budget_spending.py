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

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.budget_spending import (
    spending_by_budget, budget_spending_by_period
)
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.utils import do_budget_transfer
from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.utils import dtnow


def budget(db, name):
    return db.query(Budget).filter(Budget.name == name).one()


def account(db, name):
    return db.query(Account).filter(Account.name == name).one()


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestSpendingByBudgetRules(AcceptanceHelper):
    """
    Pin every counting rule of :py:func:`~.spending_by_budget` (GitHub issue
    #214) with exact numbers. Everything is added in March 2016, well before
    the sample data, so the sample data cannot contribute to these sums.
    """

    def test_0_add_data(self, testdb):
        bank = account(testdb, 'BankOne')
        credit = account(testdb, 'CreditOne')
        p1 = budget(testdb, 'Periodic1')
        p2 = budget(testdb, 'Periodic2')
        p3 = budget(testdb, 'Periodic3 Inactive')
        s1 = budget(testdb, 'Standing1')
        s2 = budget(testdb, 'Standing2')
        s3 = budget(testdb, 'Standing3 Inactive')
        income = budget(testdb, 'Income')

        def add(dt, amounts, desc, **kwargs):
            testdb.add(Transaction(
                date=dt, budget_amounts=amounts, description=desc,
                account=kwargs.pop('acct', bank), **kwargs
            ))

        # counted: ordinary transaction
        add(date(2016, 3, 10), {p1: Decimal('10.00')}, 'ordinary')
        # counted: split, each budget its own share
        add(
            date(2016, 3, 11),
            {p1: Decimal('5.25'), p2: Decimal('7.75')}, 'split'
        )
        # not counted in March: one day either side
        add(date(2016, 2, 29), {p1: Decimal('1000.00')}, 'day before')
        add(date(2016, 4, 1), {p1: Decimal('2000.00')}, 'day after')
        # not counted: income budget
        add(date(2016, 3, 12), {income: Decimal('500.00')}, 'income')
        # not counted: either half of a budget transfer
        do_budget_transfer(
            testdb, date(2016, 3, 13), Decimal('50.00'), bank, s2, p2
        )
        # not counted: explicitly no budget impact
        add(
            date(2016, 3, 14), {p2: Decimal('99.99')}, 'no impact',
            no_budget_impact=True
        )
        # not counted: credit card payment
        add(
            date(2016, 3, 15), {p2: Decimal('88.88')}, 'card payment',
            credit_payment_acct=credit
        )
        # counted: inactive budget
        add(date(2016, 3, 16), {p3: Decimal('3.33')}, 'inactive')
        # counted: a refund reduces the net
        add(date(2016, 3, 17), {s2: Decimal('20.00')}, 'purchase')
        add(date(2016, 3, 18), {s2: Decimal('-5.00')}, 'refund')
        # omitted: a net of exactly zero
        add(date(2016, 3, 19), {s3: Decimal('12.00')}, 'purchase')
        add(date(2016, 3, 20), {s3: Decimal('-12.00')}, 'full refund')
        # counted, negative: refunds exceeding spending
        add(date(2016, 3, 21), {s1: Decimal('-40.00')}, 'net credit')
        testdb.flush()
        testdb.commit()

    def test_1_march_totals(self, testdb):
        res = spending_by_budget(testdb, date(2016, 3, 1), date(2016, 3, 31))
        assert res == {
            budget(testdb, 'Periodic1').id: Decimal('15.25'),
            budget(testdb, 'Periodic2').id: Decimal('7.75'),
            budget(testdb, 'Periodic3 Inactive').id: Decimal('3.33'),
            budget(testdb, 'Standing2').id: Decimal('15.00'),
            budget(testdb, 'Standing1').id: Decimal('-40.00'),
        }

    def test_2_amounts_are_rounded_to_cents(self, testdb):
        res = spending_by_budget(testdb, date(2016, 3, 1), date(2016, 3, 31))
        assert sorted(str(x) for x in res.values()) == [
            '-40.00', '15.00', '15.25', '3.33', '7.75'
        ]

    def test_3_both_ends_inclusive(self, testdb):
        p1 = budget(testdb, 'Periodic1').id
        assert spending_by_budget(
            testdb, date(2016, 2, 29), date(2016, 2, 29)
        ) == {p1: Decimal('1000.00')}
        assert spending_by_budget(
            testdb, date(2016, 4, 1), date(2016, 4, 1)
        ) == {p1: Decimal('2000.00')}
        assert spending_by_budget(
            testdb, date(2016, 2, 29), date(2016, 3, 10)
        ) == {p1: Decimal('1010.00')}

    def test_4_single_day(self, testdb):
        assert spending_by_budget(
            testdb, date(2016, 3, 10), date(2016, 3, 10)
        ) == {budget(testdb, 'Periodic1').id: Decimal('10.00')}

    def test_5_empty_range(self, testdb):
        assert spending_by_budget(
            testdb, date(2015, 1, 1), date(2015, 12, 31)
        ) == {}


@pytest.mark.acceptance
@pytest.mark.usefixtures('refreshdb')
class TestSpendingByBudgetSampleData(AcceptanceHelper):
    """
    The sample data, at the acceptance test timestamp of 2017-07-28 (pay
    period start date 2017-07-21).
    """

    def test_current_pay_period(self, testdb):
        res = spending_by_budget(testdb, date(2017, 7, 21), date(2017, 8, 3))
        assert res == {
            budget(testdb, 'Periodic1').id: Decimal('111.13'),
            budget(testdb, 'Periodic2').id: Decimal('222.22'),
            budget(testdb, 'Standing1').id: Decimal('-333.33'),
        }

    def test_matches_pay_period_spent(self, testdb):
        """
        SC-002: for periodic budgets with no transfers in the period, the
        amount charted is the pay period view's "spent" figure, to the cent.
        The sample data has no transfers.
        """
        pp = BiweeklyPayPeriod.period_for_date(dtnow(), testdb)
        assert pp.start_date == date(2017, 7, 21)
        res = spending_by_budget(testdb, pp.start_date, pp.end_date)
        compared = 0
        for budget_id, sums in pp.budget_sums.items():
            if sums['is_income']:
                continue
            assert res.get(budget_id, Decimal('0')) == sums['spent'], \
                budget_id
            compared += 1
        # all three active non-income periodic budgets were compared
        assert compared == 2
        assert sum(
            1 for s in pp.budget_sums.values() if s['spent'] != 0
        ) == 2

    def test_budget_spending_by_period(self, testdb):
        p1 = budget(testdb, 'Periodic1').id
        p2 = budget(testdb, 'Periodic2').id
        s1 = budget(testdb, 'Standing1').id
        res = budget_spending_by_period(testdb, date(2017, 7, 28))
        assert res['budgets'] == [
            {'id': p1, 'name': 'Periodic1', 'omit_from_graphs': False},
            {'id': p2, 'name': 'Periodic2', 'omit_from_graphs': False},
            {'id': s1, 'name': 'Standing1', 'omit_from_graphs': True},
        ]

        def spend(*pairs):
            return sorted(
                [{'budget_id': b, 'amount': Decimal(a)} for b, a in pairs],
                key=lambda x: x['budget_id']
            )

        assert res['periods'] == [
            {
                'key': 'current_pay_period', 'name': 'Current Pay Period',
                'start_date': '2017-07-21', 'end_date': '2017-08-03',
                'spending': spend(
                    (p1, '111.13'), (p2, '222.22'), (s1, '-333.33')
                )
            },
            {
                'key': 'previous_pay_period', 'name': 'Previous Pay Period',
                'start_date': '2017-07-07', 'end_date': '2017-07-20',
                'spending': []
            },
            {
                'key': 'current_month', 'name': 'Current Month',
                'start_date': '2017-07-01', 'end_date': '2017-07-31',
                'spending': spend((p2, '222.22'), (s1, '-333.33'))
            },
            {
                'key': 'previous_month', 'name': 'Previous Month',
                'start_date': '2017-06-01', 'end_date': '2017-06-30',
                'spending': spend((p1, '100.10'), (p2, '222.22'))
            },
            {
                'key': 'current_year', 'name': 'Current Year',
                'start_date': '2017-01-01', 'end_date': '2017-12-31',
                'spending': spend(
                    (p1, '211.23'), (p2, '444.44'), (s1, '-333.33')
                )
            },
            {
                'key': 'previous_year', 'name': 'Previous Year',
                'start_date': '2016-01-01', 'end_date': '2016-12-31',
                'spending': []
            },
        ]
