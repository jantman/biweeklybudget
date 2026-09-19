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

from biweeklybudget.flaskapp.views.payperiods import build_account_sums


class StubPeriod(object):
    """
    Stand-in for :py:class:`~.BiweeklyPayPeriod` exposing only ``account_sums``.

    Deliberately minimal: ``build_account_sums()`` is contracted to read that
    one property and nothing else, so any other attribute these tests provoke
    it into touching raises ``AttributeError`` rather than passing quietly.
    """

    def __init__(self, account_sums):
        self.account_sums = account_sums


class TestBuildAccountSums(object):
    """
    Tests for :py:func:`~.build_account_sums`; see GitHub issue #355.

    These cover the contract in the feature's ``contracts/view-model.md``: one
    column per account with transactions in the period, ordered by name, and a
    grand total that is their exact sum.
    """

    def test_empty_period_has_no_columns_and_a_zero_total(self):
        # C-5: an empty period returns a zero rather than raising
        assert build_account_sums(StubPeriod({})) == ([], Decimal('0.0'))

    def test_single_account(self):
        period = StubPeriod({
            4: {'name': 'BankOne', 'total': Decimal('123.45')}
        })
        assert build_account_sums(period) == (
            [{'id': 4, 'name': 'BankOne', 'total': Decimal('123.45')}],
            Decimal('123.45')
        )

    def test_columns_are_sorted_by_account_name(self):
        # C-2: ordering is by name, not by account id and not by insertion
        period = StubPeriod({
            7: {'name': 'Zebra', 'total': Decimal('1.00')},
            2: {'name': 'Apple', 'total': Decimal('2.00')},
            5: {'name': 'Mango', 'total': Decimal('3.00')}
        })
        columns, _ = build_account_sums(period)
        assert [c['name'] for c in columns] == ['Apple', 'Mango', 'Zebra']
        assert [c['id'] for c in columns] == [2, 5, 7]

    def test_total_is_the_sum_of_the_columns(self):
        # C-3
        period = StubPeriod({
            1: {'name': 'A', 'total': Decimal('10.01')},
            2: {'name': 'B', 'total': Decimal('20.02')},
            3: {'name': 'C', 'total': Decimal('30.03')}
        })
        columns, total = build_account_sums(period)
        assert total == Decimal('60.06')
        assert total == sum([c['total'] for c in columns])

    def test_income_makes_an_account_total_negative(self):
        period = StubPeriod({
            1: {'name': 'BankOne', 'total': Decimal('-2345.67')}
        })
        columns, total = build_account_sums(period)
        assert columns[0]['total'] == Decimal('-2345.67')
        assert total == Decimal('-2345.67')

    def test_mixed_signs_net_out_in_the_total(self):
        period = StubPeriod({
            1: {'name': 'BankOne', 'total': Decimal('-2215.67')},
            3: {'name': 'CashOne', 'total': Decimal('100.00')}
        })
        columns, total = build_account_sums(period)
        assert [c['total'] for c in columns] == [
            Decimal('-2215.67'), Decimal('100.00')
        ]
        assert total == Decimal('-2115.67')

    def test_arithmetic_stays_in_decimal(self):
        # C-3: money never becomes a float on this path. 0.1 + 0.2 is the
        # canonical value that a float sum gets wrong.
        period = StubPeriod({
            1: {'name': 'A', 'total': Decimal('0.1')},
            2: {'name': 'B', 'total': Decimal('0.2')}
        })
        _, total = build_account_sums(period)
        assert isinstance(total, Decimal)
        assert total == Decimal('0.3')

    def test_does_not_mutate_the_periods_sums(self):
        # C-4: the function reads account_sums; it does not write to it
        sums = {1: {'name': 'BankOne', 'total': Decimal('5.00')}}
        build_account_sums(StubPeriod(sums))
        assert sums == {1: {'name': 'BankOne', 'total': Decimal('5.00')}}


class TestBuildAccountSumsColumnMembership(object):
    """
    Which accounts get a column; GitHub issue #355, FR-003 and contract C-1.

    Membership follows the period's own ``account_sums`` exactly: no zero-filling
    for accounts the period never saw, and no dropping of an account whose
    transactions happen to cancel out.
    """

    def test_an_account_absent_from_the_period_gets_no_column(self):
        period = StubPeriod({
            1: {'name': 'BankOne', 'total': Decimal('10.00')}
        })
        columns, _ = build_account_sums(period)
        assert [c['name'] for c in columns] == ['BankOne']

    def test_an_account_netting_exactly_zero_keeps_its_column(self):
        # Presence is decided by having transactions, not by a non-zero total:
        # an account whose spending and income cancel is a fact worth showing.
        period = StubPeriod({
            1: {'name': 'BankOne', 'total': Decimal('0.00')},
            2: {'name': 'CreditOne', 'total': Decimal('25.00')}
        })
        columns, total = build_account_sums(period)
        assert columns == [
            {'id': 1, 'name': 'BankOne', 'total': Decimal('0.00')},
            {'id': 2, 'name': 'CreditOne', 'total': Decimal('25.00')}
        ]
        assert total == Decimal('25.00')

    def test_every_column_carries_id_name_and_total(self):
        period = StubPeriod({
            9: {'name': 'BankOne', 'total': Decimal('1.00')},
            8: {'name': 'CashOne', 'total': Decimal('2.00')}
        })
        columns, _ = build_account_sums(period)
        for col in columns:
            assert sorted(col.keys()) == ['id', 'name', 'total']
