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

import sys
from decimal import Decimal

import pytest

from biweeklybudget.cashposition import (
    ZERO, AccountLine, BudgetLine, CashPosition, CoverageGroup,
    connected_components
)
from biweeklybudget.models.account import AcctType

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call, DEFAULT  # noqa
else:
    from unittest.mock import Mock, patch, call, DEFAULT  # noqa

pbm = 'biweeklybudget.cashposition'
pb = '%s.CashPosition' % pbm


def mock_account(name='acct', ledger=Decimal('0.0'), unreconciled=ZERO,
                 is_active=True, is_budget_source=True,
                 acct_type=AcctType.Bank, id=1):
    """
    Return a Mock Account. ``ledger`` of ``None`` models an AccountBalance row
    whose ledger column is NULL; pass ``balance=None`` via ``no_balance`` to
    model an account for which no balance has ever been recorded.
    """
    # Mock(name=...) sets the mock's own repr name, not a ``name``
    # attribute, so ``name`` must be assigned after construction.
    acct = Mock(
        id=id, is_active=is_active,
        is_budget_source=is_budget_source, acct_type=acct_type,
        unreconciled_sum=unreconciled,
        balance=Mock(ledger=ledger, ledger_date=None, overall_date=None)
    )
    acct.name = name
    return acct


def mock_balanceless_account(name='acct', id=1, is_active=True,
                             is_budget_source=True, acct_type=AcctType.Bank):
    """Return a Mock Account for which no balance has ever been recorded."""
    acct = Mock(
        id=id, is_active=is_active,
        is_budget_source=is_budget_source, acct_type=acct_type,
        unreconciled_sum=ZERO, balance=None
    )
    acct.name = name
    return acct


def mock_budget(name='budget', balance=Decimal('0.0'), id=1):
    budget = Mock(id=id, current_balance=balance)
    budget.name = name
    return budget


class TestConnectedComponents(object):
    """
    Tests for :py:func:`~.connected_components`, the grouping that lets the
    page report a delta without inventing an allocation rule.
    """

    def test_empty(self):
        assert connected_components([]) == []

    def test_one_budget_one_account(self):
        assert connected_components([(1, 10)]) == [([1], [10])]

    def test_one_account_many_budgets(self):
        """
        The motivating case: one savings account holding an emergency fund, a
        vacation fund and a car repair fund. All three budgets and the one
        account form a single group, so the delta is still an exact
        per-account delta.
        """
        res = connected_components([(1, 10), (2, 10), (3, 10)])
        assert res == [([1, 2, 3], [10])]

    def test_disjoint_pairs_are_separate_groups(self):
        res = connected_components([(1, 10), (2, 20)])
        assert res == [([1], [10]), ([2], [20])]

    def test_budget_spanning_two_accounts_merges_them(self):
        """
        A budget linked to two accounts pulls both accounts, and everything
        else linked to either of them, into one group. This is the case for
        which no per-account delta exists.
        """
        res = connected_components([(1, 10), (1, 20), (2, 20)])
        assert res == [([1, 2], [10, 20])]

    def test_long_chain(self):
        """
        Reachability is transitive: b1-a1, b2-a1, b2-a2, b3-a2 is one group,
        even though b1 and b3 share no account directly.
        """
        res = connected_components([(1, 10), (2, 10), (2, 20), (3, 20)])
        assert res == [([1, 2, 3], [10, 20])]

    def test_duplicate_pairs_are_idempotent(self):
        assert connected_components([(1, 10), (1, 10)]) == [([1], [10])]

    def test_is_pure(self):
        """
        The function must not touch the database or a model; it is given ints
        and returns ints, which is what makes the grouping testable at all.
        """
        pairs = [(1, 10), (2, 10)]
        connected_components(pairs)
        assert pairs == [(1, 10), (2, 10)]


class TestAccountLine(object):

    def test_ledger_and_projected(self):
        line = AccountLine(
            mock_account(ledger=Decimal('1000.00'),
                         unreconciled=Decimal('123.45')),
            with_unreconciled=True
        )
        assert line.ledger == Decimal('1000.00')
        assert line.unreconciled == Decimal('123.45')
        assert line.projected == Decimal('876.55')
        assert line.has_balance is True
        assert line.counted is True
        assert line.exclusion_reason is None

    def test_unreconciled_not_looked_up_when_not_wanted(self):
        """
        Credit accounts and coverage group members do not display an
        unreconciled figure, so the query is not made for them.
        """
        acct = mock_account(ledger=Decimal('50.00'),
                            unreconciled=Decimal('9.99'))
        line = AccountLine(acct)
        assert line.unreconciled == ZERO
        assert line.projected == Decimal('50.00')

    def test_no_balance_recorded(self):
        line = AccountLine(mock_balanceless_account())
        assert line.ledger is None
        assert line.has_balance is False
        assert line.amount == ZERO
        assert line.projected is None
        assert line.counted is False
        assert line.exclusion_reason == 'no balance recorded'

    def test_null_ledger(self):
        line = AccountLine(mock_account(ledger=None))
        assert line.ledger is None
        assert line.has_balance is False
        assert line.amount == ZERO
        assert line.projected is None
        assert line.counted is False

    def test_negative_ledger_is_kept(self):
        line = AccountLine(mock_account(ledger=Decimal('-42.00')))
        assert line.amount == Decimal('-42.00')

    def test_inactive_account_not_counted(self):
        line = AccountLine(mock_account(is_active=False))
        assert line.in_waterfall is False
        assert line.counted is False
        assert line.exclusion_reason == 'inactive account'

    def test_investment_account_not_counted(self):
        line = AccountLine(mock_account(
            is_budget_source=False, acct_type=AcctType.Investment
        ))
        assert line.in_waterfall is False
        assert line.counted is False
        assert line.exclusion_reason == (
            'not a budget-funding or credit account'
        )

    def test_credit_account_is_counted(self):
        line = AccountLine(mock_account(
            is_budget_source=False, acct_type=AcctType.Credit,
            ledger=Decimal('-500.00')
        ))
        assert line.in_waterfall is True
        assert line.counted is True

    def test_as_of_prefers_ledger_date(self):
        acct = mock_account()
        acct.balance = Mock(
            ledger=Decimal('1.00'), ledger_date='LEDGERDATE',
            overall_date='OVERALLDATE'
        )
        assert AccountLine(acct).as_of == 'LEDGERDATE'

    def test_as_of_falls_back_to_overall_date(self):
        acct = mock_account()
        acct.balance = Mock(
            ledger=Decimal('1.00'), ledger_date=None,
            overall_date='OVERALLDATE'
        )
        assert AccountLine(acct).as_of == 'OVERALLDATE'

    def test_as_of_none_without_balance(self):
        assert AccountLine(mock_balanceless_account()).as_of is None


class TestBudgetLine(object):

    def test_balance(self):
        line = BudgetLine(mock_budget(balance=Decimal('123.45')))
        assert line.amount == Decimal('123.45')

    def test_negative_balance_is_kept(self):
        line = BudgetLine(mock_budget(balance=Decimal('-10.00')))
        assert line.amount == Decimal('-10.00')

    def test_null_balance_is_zero(self):
        assert BudgetLine(mock_budget(balance=None)).amount == ZERO


class TestCoverageGroup(object):

    def _group(self, accounts, budgets):
        return CoverageGroup(
            [AccountLine(a) for a in accounts],
            [BudgetLine(b) for b in budgets]
        )

    def test_exact_match(self):
        g = self._group(
            [mock_account(ledger=Decimal('5000.00'))],
            [mock_budget(balance=Decimal('5000.00'))]
        )
        assert g.account_total == Decimal('5000.00')
        assert g.budget_total == Decimal('5000.00')
        assert g.delta == ZERO
        assert g.is_balanced is True
        assert g.is_simple is True

    def test_one_account_many_budgets_delta(self):
        g = self._group(
            [mock_account(ledger=Decimal('12400.00'))],
            [
                mock_budget(balance=Decimal('10000.00'), id=1),
                mock_budget(balance=Decimal('1500.00'), id=2),
                mock_budget(balance=Decimal('800.00'), id=3)
            ]
        )
        assert g.account_total == Decimal('12400.00')
        assert g.budget_total == Decimal('12300.00')
        assert g.delta == Decimal('100.00')
        assert g.is_balanced is False
        assert g.is_simple is True

    def test_many_accounts_is_not_simple(self):
        g = self._group(
            [
                mock_account(ledger=Decimal('100.00'), id=1),
                mock_account(ledger=Decimal('200.00'), id=2)
            ],
            [mock_budget(balance=Decimal('250.00'))]
        )
        assert g.account_total == Decimal('300.00')
        assert g.delta == Decimal('50.00')
        assert g.is_simple is False

    def test_negative_delta(self):
        g = self._group(
            [mock_account(ledger=Decimal('100.00'))],
            [mock_budget(balance=Decimal('175.00'))]
        )
        assert g.delta == Decimal('-75.00')

    def test_excluded_account_does_not_contribute_but_is_kept(self):
        """
        An account that was linked and later deactivated must still be shown,
        marked as not counted -- silently dropping it would make the group's
        own arithmetic look wrong to whoever configured it.
        """
        g = self._group(
            [
                mock_account(ledger=Decimal('100.00'), id=1),
                mock_account(ledger=Decimal('999.00'), id=2, is_active=False)
            ],
            [mock_budget(balance=Decimal('100.00'))]
        )
        assert len(g.accounts) == 2
        assert len(g.counted_accounts) == 1
        assert len(g.excluded_accounts) == 1
        assert g.account_total == Decimal('100.00')
        assert g.is_balanced is True

    def test_balanceless_account_contributes_nothing(self):
        g = self._group(
            [mock_balanceless_account()],
            [mock_budget(balance=ZERO)]
        )
        assert g.account_total == ZERO
        assert g.is_balanced is True

    def test_empty_group_totals_are_zero(self):
        g = self._group([], [])
        assert g.account_total == ZERO
        assert g.budget_total == ZERO
        assert g.delta == ZERO
        assert g.is_balanced is True
        assert g.is_simple is False


class CashPositionFixture(object):
    """
    Base class providing a :py:class:`~.CashPosition` whose five terms are
    stubbed, for testing the arithmetic that combines them.
    """

    def position(self, budget_lines=None, credit_lines=None,
                 standing_lines=None, pp_allocated=ZERO, pp_spent=ZERO):
        cp = CashPosition(Mock())
        cp.__dict__['budget_account_lines'] = budget_lines or []
        cp.__dict__['credit_account_lines'] = credit_lines or []
        cp.__dict__['standing_budget_lines'] = standing_lines or []
        cp.__dict__['pay_period'] = Mock(overall_sums={
            'allocated': pp_allocated, 'spent': pp_spent
        })
        return cp


class TestCashPositionTerms(CashPositionFixture):

    def test_all_terms_zero(self):
        cp = self.position()
        assert cp.budget_account_ledger == ZERO
        assert cp.unreconciled == ZERO
        assert cp.credit_balance == ZERO
        assert cp.net_liquid == ZERO
        assert cp.standing_total == ZERO
        assert cp.pay_period_allocated_unspent == ZERO
        assert cp.uncommitted == ZERO

    def test_budget_account_ledger_sums_lines(self):
        cp = self.position(budget_lines=[
            AccountLine(mock_account(ledger=Decimal('1000.00'))),
            AccountLine(mock_account(ledger=Decimal('234.56')))
        ])
        assert cp.budget_account_ledger == Decimal('1234.56')

    def test_unreconciled_sums_lines(self):
        cp = self.position(budget_lines=[
            AccountLine(
                mock_account(ledger=Decimal('1000.00'),
                             unreconciled=Decimal('100.00')),
                with_unreconciled=True
            ),
            AccountLine(
                mock_account(ledger=Decimal('1000.00'),
                             unreconciled=Decimal('-25.00')),
                with_unreconciled=True
            )
        ])
        assert cp.unreconciled == Decimal('75.00')

    def test_unreconciled_is_subtracted(self):
        """
        Spending is entered positive, so ledger *minus* unreconciled is the
        projected balance. An implementation that added it would report more
        money than exists.
        """
        cp = self.position(budget_lines=[
            AccountLine(
                mock_account(ledger=Decimal('1000.00'),
                             unreconciled=Decimal('300.00')),
                with_unreconciled=True
            )
        ])
        assert cp.net_liquid == Decimal('700.00')

    def test_credit_balance_owed_reduces_net_liquid(self):
        cp = self.position(
            budget_lines=[AccountLine(mock_account(ledger=Decimal('1000.00')))],
            credit_lines=[AccountLine(mock_account(
                ledger=Decimal('-200.00'), is_budget_source=False,
                acct_type=AcctType.Credit
            ))]
        )
        assert cp.credit_balance == Decimal('-200.00')
        assert cp.net_liquid == Decimal('800.00')

    def test_positive_credit_balance_raises_net_liquid(self):
        """
        An overpaid card, or one carrying a statement credit larger than its
        balance, holds money that really is available. This is the case an
        abs()-based implementation gets backwards, and the substance of
        GitHub issue #320.
        """
        cp = self.position(
            budget_lines=[AccountLine(mock_account(ledger=Decimal('1000.00')))],
            credit_lines=[AccountLine(mock_account(
                ledger=Decimal('250.00'), is_budget_source=False,
                acct_type=AcctType.Credit
            ))]
        )
        assert cp.credit_balance == Decimal('250.00')
        assert cp.net_liquid == Decimal('1250.00')

    def test_standing_total_is_subtracted(self):
        cp = self.position(
            budget_lines=[AccountLine(mock_account(ledger=Decimal('1000.00')))],
            standing_lines=[BudgetLine(mock_budget(balance=Decimal('600.00')))]
        )
        assert cp.standing_total == Decimal('600.00')
        assert cp.uncommitted == Decimal('400.00')

    def test_negative_standing_budget_raises_uncommitted(self):
        """
        Subtracting a negative. Correct, and deliberately not special-cased.
        """
        cp = self.position(
            budget_lines=[AccountLine(mock_account(ledger=Decimal('1000.00')))],
            standing_lines=[BudgetLine(mock_budget(balance=Decimal('-50.00')))]
        )
        assert cp.uncommitted == Decimal('1050.00')

    def test_pay_period_allocated_unspent(self):
        cp = self.position(
            budget_lines=[AccountLine(mock_account(ledger=Decimal('1000.00')))],
            pp_allocated=Decimal('700.00'), pp_spent=Decimal('250.00')
        )
        assert cp.pay_period_allocated_unspent == Decimal('450.00')
        assert cp.uncommitted == Decimal('550.00')

    def test_empty_pay_period(self):
        cp = self.position(pp_allocated=ZERO, pp_spent=ZERO)
        assert cp.pay_period_allocated_unspent == ZERO

    def test_net_liquid_may_be_negative(self):
        cp = self.position(
            budget_lines=[AccountLine(mock_account(ledger=Decimal('100.00')))],
            credit_lines=[AccountLine(mock_account(
                ledger=Decimal('-500.00'), is_budget_source=False,
                acct_type=AcctType.Credit
            ))]
        )
        assert cp.net_liquid == Decimal('-400.00')

    def test_uncommitted_may_be_negative(self):
        cp = self.position(
            budget_lines=[AccountLine(mock_account(ledger=Decimal('100.00')))],
            standing_lines=[BudgetLine(mock_budget(balance=Decimal('900.00')))]
        )
        assert cp.uncommitted == Decimal('-800.00')

    def test_balanceless_account_contributes_zero(self):
        cp = self.position(budget_lines=[
            AccountLine(mock_account(ledger=Decimal('100.00'))),
            AccountLine(mock_balanceless_account(id=2))
        ])
        assert cp.budget_account_ledger == Decimal('100.00')

    def test_null_ledger_account_contributes_zero(self):
        cp = self.position(budget_lines=[
            AccountLine(mock_account(ledger=Decimal('100.00'))),
            AccountLine(mock_account(ledger=None, id=2))
        ])
        assert cp.budget_account_ledger == Decimal('100.00')


class TestNotificationIdentity(CashPositionFixture):
    """
    The identity that makes the Cash Position page and the notification
    banner incapable of disagreeing (FR-004). The banner computes
    ``available - bal_sum``; the waterfall is a reassociation of those same
    terms and must produce exactly the same number, including sign.
    """

    def assert_identity(self, cp):
        assert cp.uncommitted == (
            (cp.budget_account_ledger + cp.credit_balance) - (
                cp.standing_total +
                cp.pay_period_allocated_unspent +
                cp.unreconciled
            )
        )

    AMOUNTS = [Decimal('0.0'), Decimal('137.42'), Decimal('-98.13')]

    @pytest.mark.parametrize('ledger', AMOUNTS)
    @pytest.mark.parametrize('credit', AMOUNTS)
    @pytest.mark.parametrize('unrec', AMOUNTS)
    def test_identity_over_funds_terms(self, ledger, credit, unrec):
        cp = self.position(
            budget_lines=[AccountLine(
                mock_account(ledger=ledger, unreconciled=unrec),
                with_unreconciled=True
            )],
            credit_lines=[AccountLine(mock_account(
                ledger=credit, is_budget_source=False,
                acct_type=AcctType.Credit
            ))]
        )
        self.assert_identity(cp)

    @pytest.mark.parametrize('standing', AMOUNTS)
    @pytest.mark.parametrize('allocated', AMOUNTS)
    @pytest.mark.parametrize('spent', AMOUNTS)
    def test_identity_over_committed_terms(self, standing, allocated, spent):
        cp = self.position(
            budget_lines=[AccountLine(
                mock_account(ledger=Decimal('1234.56'),
                             unreconciled=Decimal('78.90')),
                with_unreconciled=True
            )],
            standing_lines=[BudgetLine(mock_budget(balance=standing))],
            pp_allocated=allocated, pp_spent=spent
        )
        self.assert_identity(cp)

    def test_identity_with_everything_empty(self):
        self.assert_identity(self.position())

    def test_known_worked_example(self):
        """
        The scenario from the existing notification tests, pinned end to end:
        $1000 in funding accounts, $200 owed on cards, $700 unreconciled,
        $500 standing, $600 allocated-unspent. The banner calls that $800
        available against $1800 committed, i.e. $1000 short.
        """
        cp = self.position(
            budget_lines=[AccountLine(
                mock_account(ledger=Decimal('1000.00'),
                             unreconciled=Decimal('700.00')),
                with_unreconciled=True
            )],
            credit_lines=[AccountLine(mock_account(
                ledger=Decimal('-200.00'), is_budget_source=False,
                acct_type=AcctType.Credit
            ))],
            standing_lines=[BudgetLine(mock_budget(balance=Decimal('500.00')))],
            pp_allocated=Decimal('600.00'), pp_spent=ZERO
        )
        assert cp.net_liquid == Decimal('100.00')
        assert cp.uncommitted == Decimal('-1000.00')
        self.assert_identity(cp)


class TestCashPositionSession(object):

    def test_defaults_to_db_session(self):
        with patch('%s.db_session' % pbm) as mock_db:
            cp = CashPosition()
        assert cp._sess is mock_db

    def test_uses_given_session(self):
        sess = Mock()
        assert CashPosition(sess)._sess is sess

    def test_terms_are_lazy(self):
        """
        Constructing a CashPosition must run no queries. The notification
        banner reads five attributes and nothing else, and
        NotificationsController delegates one method to one property each, so
        asking for one figure must not run every other query.
        """
        sess = Mock()
        CashPosition(sess)
        assert sess.mock_calls == []

    def test_credit_balance_touches_only_credit_accounts(self):
        sess = Mock()
        with patch('%s.Account.active_credit_accounts' % pbm) as mock_aca:
            mock_aca.return_value = []
            res = CashPosition(sess).credit_balance
        assert res == ZERO
        assert mock_aca.mock_calls == [call(sess)]
        assert sess.mock_calls == []

    def test_terms_are_cached(self):
        cp = CashPosition(Mock())
        with patch('%s.Account.active_credit_accounts' % pbm) as mock_aca:
            mock_aca.return_value = []
            cp.credit_balance
            cp.credit_balance
        assert mock_aca.call_count == 1


class TestDiagnostics(CashPositionFixture):

    def position_with_links(self, pairs, accounts, budget_lines,
                            budget_account_lines=None):
        cp = self.position(
            budget_lines=budget_account_lines or [],
            standing_lines=budget_lines
        )
        cp.__dict__['_link_pairs'] = pairs
        sess = Mock()
        query = Mock()
        query.filter.return_value.all.return_value = accounts
        sess.query.return_value = query
        cp._sess = sess
        return cp

    def test_no_links_configured(self):
        cp = self.position()
        cp.__dict__['_link_pairs'] = []
        assert cp.has_links_configured is False
        assert cp.coverage_groups == []
        assert cp.diagnostics_all_clear is False

    def test_no_links_means_every_account_unlinked(self):
        lines = [
            AccountLine(mock_account(name='Checking', id=1)),
            AccountLine(mock_account(name='Savings', id=2))
        ]
        cp = self.position(budget_lines=lines)
        cp.__dict__['_link_pairs'] = []
        assert [x.account.name for x in cp.unlinked_accounts] == [
            'Checking', 'Savings'
        ]

    def test_unlinked_accounts_excludes_linked_ones(self):
        lines = [
            AccountLine(mock_account(name='Checking', id=1)),
            AccountLine(mock_account(name='Savings', id=2))
        ]
        cp = self.position(budget_lines=lines)
        cp.__dict__['_link_pairs'] = [(100, 2)]
        assert [x.account.name for x in cp.unlinked_accounts] == ['Checking']

    def test_coverage_group_one_account_many_budgets(self):
        acct = mock_account(name='Savings', id=2,
                            ledger=Decimal('12400.00'))
        budget_lines = [
            BudgetLine(mock_budget(
                name='Emergency', id=100, balance=Decimal('10000.00')
            )),
            BudgetLine(mock_budget(
                name='Vacation', id=101, balance=Decimal('1500.00')
            )),
            BudgetLine(mock_budget(
                name='Car Repair', id=102, balance=Decimal('800.00')
            ))
        ]
        cp = self.position_with_links(
            [(100, 2), (101, 2), (102, 2)], [acct], budget_lines
        )
        groups = cp.coverage_groups
        assert len(groups) == 1
        assert groups[0].is_simple is True
        assert groups[0].account_total == Decimal('12400.00')
        assert groups[0].budget_total == Decimal('12300.00')
        assert groups[0].delta == Decimal('100.00')

    def test_coverage_group_many_to_many_is_not_simple(self):
        accts = [
            mock_account(name='Checking', id=1, ledger=Decimal('2400.00')),
            mock_account(name='Savings', id=2, ledger=Decimal('5000.00'))
        ]
        budget_lines = [
            BudgetLine(mock_budget(
                name='Emergency', id=100, balance=Decimal('7000.00')
            ))
        ]
        cp = self.position_with_links(
            [(100, 1), (100, 2)], accts, budget_lines
        )
        groups = cp.coverage_groups
        assert len(groups) == 1
        assert groups[0].is_simple is False
        assert groups[0].account_total == Decimal('7400.00')
        assert groups[0].delta == Decimal('400.00')

    def test_balanced_group_is_still_emitted(self):
        """
        A group that agrees must be shown as balanced rather than omitted, so
        that a group's absence always means "not configured" and never
        "checked and fine".
        """
        acct = mock_account(name='Savings', id=2, ledger=Decimal('500.00'))
        budget_lines = [BudgetLine(mock_budget(
            name='Emergency', id=100, balance=Decimal('500.00')
        ))]
        cp = self.position_with_links([(100, 2)], [acct], budget_lines)
        groups = cp.coverage_groups
        assert len(groups) == 1
        assert groups[0].is_balanced is True

    def test_group_with_no_active_budget_is_not_emitted(self):
        """
        A component whose budgets are all inactive produces no group; its
        account is reported as unlinked instead, so every account appears in
        exactly one place.
        """
        acct = mock_account(name='Savings', id=2, ledger=Decimal('500.00'))
        cp = self.position_with_links([], [acct], [])
        assert cp.coverage_groups == []

    def test_all_clear_requires_links_and_balance(self):
        acct = mock_account(name='Savings', id=2, ledger=Decimal('500.00'))
        budget_lines = [BudgetLine(mock_budget(
            name='Emergency', id=100, balance=Decimal('500.00')
        ))]
        cp = self.position_with_links([(100, 2)], [acct], budget_lines)
        cp.__dict__['budget_account_lines'] = [AccountLine(acct)]
        assert cp.diagnostics_all_clear is True

    def test_not_all_clear_with_unlinked_account(self):
        acct = mock_account(name='Savings', id=2, ledger=Decimal('500.00'))
        other = mock_account(name='Checking', id=1, ledger=Decimal('100.00'))
        budget_lines = [BudgetLine(mock_budget(
            name='Emergency', id=100, balance=Decimal('500.00')
        ))]
        cp = self.position_with_links([(100, 2)], [acct], budget_lines)
        cp.__dict__['budget_account_lines'] = [
            AccountLine(other), AccountLine(acct)
        ]
        assert cp.diagnostics_all_clear is False

    def test_not_all_clear_with_unbalanced_group(self):
        acct = mock_account(name='Savings', id=2, ledger=Decimal('600.00'))
        budget_lines = [BudgetLine(mock_budget(
            name='Emergency', id=100, balance=Decimal('500.00')
        ))]
        cp = self.position_with_links([(100, 2)], [acct], budget_lines)
        cp.__dict__['budget_account_lines'] = [AccountLine(acct)]
        assert cp.diagnostics_all_clear is False
