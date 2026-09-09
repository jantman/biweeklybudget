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

import logging
from collections import deque
from decimal import Decimal
from functools import cached_property

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.db import db_session
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.models.budget_account_link import budget_accounts
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.utils import dtnow

logger = logging.getLogger(__name__)

#: Zero, as a Decimal. Used everywhere a balance is missing, so that "no data"
#: contributes nothing without ever becoming a ``None`` in the arithmetic.
ZERO = Decimal('0.0')


def connected_components(pairs):
    """
    Group ``pairs`` into connected components, i.e. the maximal sets of budgets
    and accounts reachable from one another through the links.

    This is how :py:class:`~.CashPosition` reports balance deltas. The
    budget/account association is many-to-many and records **no split** of a
    budget's balance across the accounts it is linked to, so there is no
    defensible way to say how much of a given budget sits in a given account.
    What *is* well defined is the total on each side of a set that is closed
    under the links: take an account, every budget linked to it, every other
    account those budgets are linked to, and so on until nothing new is
    reachable. Comparing those two totals attributes nothing to anything.

    The common configurations fall out with no special-casing:

    * one account and one budget -- the delta is an exact per-account delta,
      the "this savings budget mirrors this savings account" case;
    * one account and several budgets -- still an exact per-account delta, the
      case of one savings account holding several earmarked funds;
    * several accounts and several budgets -- a group-level delta only, which
      is the most that can honestly be said.

    Implemented as an iterative breadth-first search rather than a recursive
    one purely so that a pathological configuration cannot exhaust the
    recursion limit; this application has tens of budgets, not thousands.

    This function is deliberately pure -- it touches no database and no model
    -- so that the grouping logic can be tested on its own. See GitHub issue
    #321.

    :param pairs: ``(budget_id, account_id)`` association pairs
    :type pairs: list
    :return: list of ``(budget_ids, account_ids)`` tuples, one per component,
      each a sorted list of IDs
    :rtype: list
    """
    adjacent = {}
    for budget_id, account_id in pairs:
        adjacent.setdefault(('b', budget_id), set()).add(('a', account_id))
        adjacent.setdefault(('a', account_id), set()).add(('b', budget_id))
    seen = set()
    components = []
    for start in sorted(adjacent.keys()):
        if start in seen:
            continue
        seen.add(start)
        component = {start}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in adjacent[node]:
                if neighbor in seen:
                    continue
                seen.add(neighbor)
                component.add(neighbor)
                queue.append(neighbor)
        components.append((
            sorted(n[1] for n in component if n[0] == 'b'),
            sorted(n[1] for n in component if n[0] == 'a')
        ))
    return components


class AccountLine(object):
    """
    One account's contribution to the cash position, as the page itemizes it.

    Carries the raw ledger balance *and* the projected balance (ledger net of
    unreconciled transactions) side by side, because a ledger balance can lag
    reality by days and is misleading on its own.
    """

    def __init__(self, account, with_unreconciled=False):
        """
        :param account: the account
        :type account: biweeklybudget.models.account.Account
        :param with_unreconciled: whether to look up this account's
          unreconciled transaction sum. False for accounts that are only being
          displayed (credit accounts, coverage group members), for which the
          figure is not shown and the query would be wasted.
        :type with_unreconciled: bool
        """
        #: the :py:class:`~.Account` this line is for
        self.account = account
        balance = account.balance
        #: raw ledger balance, or None if no balance has ever been recorded
        self.ledger = None if balance is None else balance.ledger
        #: when that balance was recorded, or None
        self.as_of = None
        if balance is not None:
            self.as_of = balance.ledger_date or balance.overall_date
        self._with_unreconciled = with_unreconciled

    def __repr__(self):
        return '<AccountLine(account=%s, ledger=%s)>' % (
            self.account, self.ledger
        )

    @cached_property
    def unreconciled(self):
        """
        Return the sum of this account's unreconciled transactions, or zero
        for a line that does not display one.

        Computed on first access rather than in ``__init__``, and this is not
        an incidental optimization.
        :py:attr:`~.Account.unreconciled_sum` walks every unreconciled
        transaction in Python, checking each against
        :py:attr:`~.Transaction.is_excluded_from_budget`. The notification
        banner is rendered on *every* page and reads both
        :py:attr:`~.CashPosition.budget_account_ledger` and
        :py:attr:`~.CashPosition.unreconciled`; if the ledger term dragged
        this scan along with it, every page load would perform it twice where
        it previously performed it once. See GitHub issue #321.

        :return: sum of unreconciled transaction amounts, or zero
        :rtype: decimal.Decimal
        """
        if not self._with_unreconciled:
            return ZERO
        return self.account.unreconciled_sum

    @property
    def has_balance(self):
        """
        Return whether a balance has ever been recorded for this account.

        This is *not* the same question as whether the balance is zero, and
        the page must not conflate them: "no data" and "zero dollars" mean
        very different things when you are asking how much money you have.

        :return: whether a balance has been recorded
        :rtype: bool
        """
        return self.ledger is not None

    @property
    def amount(self):
        """
        Return this account's contribution to the totals: its ledger balance,
        or zero if none has been recorded.

        :return: contribution to the cash position totals
        :rtype: decimal.Decimal
        """
        return self.ledger if self.has_balance else ZERO

    @property
    def projected(self):
        """
        Return the ledger balance net of unreconciled transactions, or None if
        no balance has been recorded.

        :return: projected balance
        :rtype: decimal.Decimal or None
        """
        if not self.has_balance:
            return None
        return self.ledger - self.unreconciled

    @property
    def in_waterfall(self):
        """
        Return whether this account is one of those the waterfall counts:
        active, and either a budget funding source or a credit account.

        Investment accounts and inactive accounts are not counted. They can
        still appear on the page as members of a coverage group, where they
        are shown marked as not counted rather than quietly dropped -- an
        account you linked and then deactivated should not simply vanish from
        the explanation of your own configuration.

        :return: whether this account contributes to the waterfall
        :rtype: bool
        """
        if not self.account.is_active:
            return False
        return (
            self.account.is_budget_source or
            self.account.acct_type == AcctType.Credit
        )

    @property
    def counted(self):
        """
        Return whether this line actually contributes a figure to the totals.

        :return: whether this line contributes to the totals
        :rtype: bool
        """
        return self.in_waterfall and self.has_balance

    @property
    def exclusion_reason(self):
        """
        Return why this line contributes nothing, or None if it does.

        :return: human-readable reason, or None
        :rtype: str or None
        """
        if not self.account.is_active:
            return 'inactive account'
        if not self.in_waterfall:
            return 'not a budget-funding or credit account'
        if not self.has_balance:
            return 'no balance recorded'
        return None


class BudgetLine(object):
    """
    One standing budget's contribution to the cash position.
    """

    def __init__(self, budget):
        """
        :param budget: the standing budget
        :type budget: biweeklybudget.models.budget_model.Budget
        """
        #: the :py:class:`~.Budget` this line is for
        self.budget = budget
        #: its current balance; always a Decimal
        self.amount = (
            ZERO if budget.current_balance is None else budget.current_balance
        )

    def __repr__(self):
        return '<BudgetLine(budget=%s, amount=%s)>' % (
            self.budget, self.amount
        )


class CoverageGroup(object):
    """
    A set of accounts and standing budgets that are reachable from one another
    through budget/account links, along with the difference between what those
    accounts hold and what those budgets claim.

    See :py:func:`~.connected_components` for why the comparison is made over
    a group rather than per account.
    """

    def __init__(self, account_lines, budget_lines):
        #: :py:class:`~.AccountLine` for every account in the group
        self.accounts = account_lines
        #: :py:class:`~.BudgetLine` for every standing budget in the group
        self.budgets = budget_lines

    def __repr__(self):
        return '<CoverageGroup(accounts=%s, budgets=%s, delta=%s)>' % (
            [x.account.name for x in self.accounts],
            [x.budget.name for x in self.budgets],
            self.delta
        )

    @property
    def counted_accounts(self):
        """
        Return the account lines in this group that contribute to the totals.

        :return: contributing account lines
        :rtype: list
        """
        return [x for x in self.accounts if x.counted]

    @property
    def excluded_accounts(self):
        """
        Return the account lines in this group that contribute nothing.

        :return: non-contributing account lines
        :rtype: list
        """
        return [x for x in self.accounts if not x.counted]

    @property
    def account_total(self):
        """
        Return the combined balance of the counted accounts in this group.

        :return: combined account balance
        :rtype: decimal.Decimal
        """
        return sum((x.amount for x in self.counted_accounts), ZERO)

    @property
    def budget_total(self):
        """
        Return the combined balance of the standing budgets in this group.

        :return: combined budget balance
        :rtype: decimal.Decimal
        """
        return sum((x.amount for x in self.budgets), ZERO)

    @property
    def delta(self):
        """
        Return how much the accounts hold beyond what the budgets claim.

        Positive means the accounts hold more than the budgets account for --
        that surplus is what turns up in the uncommitted figure. Negative
        means the budgets claim more than the accounts hold.

        :return: account total minus budget total
        :rtype: decimal.Decimal
        """
        return self.account_total - self.budget_total

    @property
    def is_balanced(self):
        """
        Return whether the two sides of this group agree exactly.

        :return: whether the delta is zero
        :rtype: bool
        """
        return self.delta == ZERO

    @property
    def is_simple(self):
        """
        Return whether this group contains exactly one account, in which case
        the delta *is* a per-account delta and can be described as one.

        :return: whether the group holds a single account
        :rtype: bool
        """
        return len(self.accounts) == 1


class CashPosition(object):
    """
    The full available-funds waterfall: how much money there is, what is
    already spoken for, and what is left over.

    This is the single calculation behind both the Cash Position page and the
    unallocated-funds notification banner. It exists because those two were
    otherwise two implementations of the same arithmetic, free to disagree --
    which is exactly what GitHub issue #320 turned out to be. Anything that
    reports these figures must go through here.

    The waterfall, in the order the page presents it:

    ============================================  =========================
    Term                                          Attribute
    ============================================  =========================
    Budget-funding account balances       ``+``   :py:attr:`~.budget_account_ledger`
    Adjustment for unreconciled txns      ``-``   :py:attr:`~.unreconciled`
    Outstanding credit account balances   ``+``   :py:attr:`~.credit_balance`
    **Net liquid position**                       :py:attr:`~.net_liquid`
    Standing budget balances              ``-``   :py:attr:`~.standing_total`
    Current pay period allocated, unspent ``-``   :py:attr:`~.pay_period_allocated_unspent`
    **Truly unallocated / uncommitted**           :py:attr:`~.uncommitted`
    ============================================  =========================

    **Credit balances are added with the sign in which they are recorded.**
    Money owed is stored negative, so adding subtracts what is owed. Do not
    negate and do not take an absolute value: a credit account carrying a
    *positive* balance -- an overpaid card, or one holding a statement credit
    larger than its balance -- really does hold money that is available to
    spend, and applying the recorded balance with its own sign gets that case
    right for free. See GitHub issue #320.

    Every term is computed on first access and cached on the instance. That is
    deliberate rather than incidental: the notification banner reads five of
    these attributes and nothing else, and
    :py:class:`~biweeklybudget.flaskapp.notifications.NotificationsController`
    delegates one method to one property each, so a caller must be able to ask
    for a single figure without every other query running.

    :param sess: database session to use; defaults to
      :py:data:`biweeklybudget.db.db_session`
    :type sess: sqlalchemy.orm.session.Session
    """

    def __init__(self, sess=None):
        if sess is None:
            sess = db_session
        self._sess = sess

    def __repr__(self):
        return '<CashPosition(uncommitted=%s)>' % self.uncommitted

    #
    # Term 1: budget-funding accounts
    #

    @cached_property
    def budget_account_lines(self):
        """
        Return an :py:class:`~.AccountLine` for each active budget-funding
        account, ordered by name.

        :return: budget-funding account lines
        :rtype: list
        """
        accts = self._sess.query(Account).filter(
            Account.is_budget_source.__eq__(True),
            Account.is_active.__eq__(True)
        ).order_by(Account.name).all()
        return [AccountLine(a, with_unreconciled=True) for a in accts]

    @cached_property
    def budget_account_ledger(self):
        """
        Return the combined ledger balance of all active budget-funding
        accounts. Waterfall term 1, added.

        :return: combined ledger balance
        :rtype: decimal.Decimal
        """
        return sum((x.amount for x in self.budget_account_lines), ZERO)

    #
    # Term 2: unreconciled adjustment
    #

    @cached_property
    def unreconciled(self):
        """
        Return the combined unreconciled transaction total for all active
        budget-funding accounts. Waterfall term 2, **subtracted**: spending is
        entered positive, so ledger minus this is the projected balance.

        Transactions that move no real cash -- those marked
        :py:attr:`~.Transaction.no_budget_impact`, and payments toward a
        credit account -- are already excluded by
        :py:attr:`~.Account.unreconciled_sum` (GitHub issues #210 and #319).
        No second filter is applied here, deliberately: a second definition of
        "no cash impact" alongside the first is free to drift from it.

        :return: combined unreconciled amount
        :rtype: decimal.Decimal
        """
        return sum((x.unreconciled for x in self.budget_account_lines), ZERO)

    #
    # Term 3: credit accounts
    #

    @cached_property
    def credit_account_lines(self):
        """
        Return an :py:class:`~.AccountLine` for each active credit account.

        :return: credit account lines
        :rtype: list
        """
        return [
            AccountLine(a) for a in Account.active_credit_accounts(self._sess)
        ]

    @cached_property
    def credit_balance(self):
        """
        Return the combined balance of all active credit accounts, **with the
        sign in which each is recorded** -- negative in the ordinary case,
        where money is owed. Waterfall term 3, added.

        :return: combined credit account balance
        :rtype: decimal.Decimal
        """
        return sum((x.amount for x in self.credit_account_lines), ZERO)

    @cached_property
    def net_liquid(self):
        """
        Return the net liquid position: what the budget-funding accounts are
        projected to hold, less what is owed on credit accounts.

        May legitimately be negative. Never clamp it.

        :return: net liquid position
        :rtype: decimal.Decimal
        """
        return (
            self.budget_account_ledger - self.unreconciled + self.credit_balance
        )

    #
    # Term 4: standing budgets
    #

    @cached_property
    def standing_budget_lines(self):
        """
        Return a :py:class:`~.BudgetLine` for each active standing budget,
        ordered by name.

        :return: standing budget lines
        :rtype: list
        """
        budgets = self._sess.query(Budget).filter(
            Budget.is_periodic.__eq__(False),
            Budget.is_active.__eq__(True)
        ).order_by(Budget.name).all()
        return [BudgetLine(b) for b in budgets]

    @cached_property
    def standing_total(self):
        """
        Return the combined current balance of all active standing budgets.
        Waterfall term 4, subtracted.

        A standing budget with a negative balance therefore *raises* the
        uncommitted figure, by subtracting a negative. That is correct and
        needs no special case.

        :return: combined standing budget balance
        :rtype: decimal.Decimal
        """
        return sum((x.amount for x in self.standing_budget_lines), ZERO)

    #
    # Term 5: the current pay period
    #

    @cached_property
    def pay_period(self):
        """
        Return the :py:class:`~.BiweeklyPayPeriod` containing today.

        :return: the current pay period
        :rtype: biweeklybudget.biweeklypayperiod.BiweeklyPayPeriod
        """
        return BiweeklyPayPeriod.period_for_date(dtnow(), self._sess)

    @cached_property
    def pay_period_allocated_unspent(self):
        """
        Return what the current pay period has allocated minus what has been
        spent against it. Waterfall term 5, subtracted.

        This is *not* the pay period view's own "remaining" figure, which is
        income minus budgeted. The two answer different questions and
        routinely disagree, which was the whole of GitHub issue #209.
        Allocated-but-unspent is the right one here because it is what is
        still committed against the cash on hand right now.

        :return: allocated minus spent for the current pay period
        :rtype: decimal.Decimal
        """
        sums = self.pay_period.overall_sums
        logger.debug(
            'PayPeriod=%s; allocated=%s; spent=%s',
            self.pay_period, sums['allocated'], sums['spent']
        )
        return sums['allocated'] - sums['spent']

    #
    # The bottom line
    #

    @cached_property
    def uncommitted(self):
        """
        Return the money that is genuinely not spoken for.

        This is identical, including sign, to the amount by which the
        notification banner says available funds differ from allocated funds:

        .. code-block:: python

            uncommitted == (budget_account_ledger + credit_balance) - (
                standing_total + pay_period_allocated_unspent + unreconciled
            )

        The waterfall is a reassociation of the banner's own terms, not a
        second calculation. A unit test asserts that identity directly.

        May legitimately be negative, meaning more is committed than is held.

        :return: truly unallocated / uncommitted funds
        :rtype: decimal.Decimal
        """
        return (
            self.net_liquid -
            self.standing_total -
            self.pay_period_allocated_unspent
        )

    #
    # Diagnostics
    #

    @cached_property
    def _link_pairs(self):
        """
        Return the ``(budget_id, account_id)`` association pairs whose budget
        is an active standing budget.

        Links belonging to inactive or periodic budgets are filtered out here
        rather than in the grouping, so that an account linked *only* to
        inactive budgets is correctly reported as unlinked: an inactive budget
        allocates nothing, so it explains nothing.

        :return: association pairs for active standing budgets
        :rtype: list
        """
        active_ids = {x.budget.id for x in self.standing_budget_lines}
        rows = self._sess.query(
            budget_accounts.c.budget_id, budget_accounts.c.account_id
        ).all()
        return [
            (row[0], row[1]) for row in rows if row[0] in active_ids
        ]

    @cached_property
    def unlinked_accounts(self):
        """
        Return an :py:class:`~.AccountLine` for each active budget-funding
        account that no active standing budget is linked to.

        These are the accounts whose balances sit permanently in the
        uncommitted figure with nothing allocating them, which is the usual
        reason that figure is stubbornly non-zero.

        :return: unlinked budget-funding account lines
        :rtype: list
        """
        linked = {pair[1] for pair in self._link_pairs}
        return [
            x for x in self.budget_account_lines
            if x.account.id not in linked
        ]

    @cached_property
    def coverage_groups(self):
        """
        Return a :py:class:`~.CoverageGroup` for each set of accounts and
        active standing budgets that are reachable from one another through
        budget/account links.

        A component containing no budgets is not emitted; its accounts are
        reported through :py:attr:`~.unlinked_accounts` instead, so that every
        account appears in exactly one place on the page.

        :return: coverage groups, ordered by first account name
        :rtype: list
        """
        pairs = self._link_pairs
        if not pairs:
            return []
        budgets_by_id = {
            x.budget.id: x for x in self.standing_budget_lines
        }
        account_ids = {pair[1] for pair in pairs}
        accounts_by_id = {
            a.id: AccountLine(a) for a in self._sess.query(Account).filter(
                Account.id.in_(account_ids)
            ).all()
        }
        groups = []
        for budget_ids, acct_ids in connected_components(pairs):
            budget_lines = [
                budgets_by_id[i] for i in budget_ids if i in budgets_by_id
            ]
            if not budget_lines:
                continue
            account_lines = [
                accounts_by_id[i] for i in acct_ids if i in accounts_by_id
            ]
            groups.append(CoverageGroup(
                sorted(account_lines, key=lambda x: x.account.name),
                sorted(budget_lines, key=lambda x: x.budget.name)
            ))
        return sorted(
            groups,
            key=lambda g: g.accounts[0].account.name if g.accounts else ''
        )

    @cached_property
    def has_links_configured(self):
        """
        Return whether any link to an *active standing* budget exists.

        Distinguishes "checked, and everything is accounted for" from "nothing
        has been configured yet", which are very different messages to show
        somebody looking at an unexplained surplus. Every installation is in
        the latter state immediately after the migration that added the links.

        Links belonging to inactive or periodic budgets do not count, for the
        same reason they are excluded from the association pairs the
        diagnostics are built from: an inactive budget allocates nothing, so
        it explains nothing, and a
        configuration made up entirely of such links leaves the page with
        nothing to say. Deactivating every linked budget therefore returns
        this to False.

        :return: whether any link to an active standing budget exists
        :rtype: bool
        """
        return len(self._link_pairs) > 0

    @cached_property
    def diagnostics_all_clear(self):
        """
        Return whether there is nothing structural to report: every
        budget-funding account is linked, and every coverage group balances.

        :return: whether there is no structural mismatch
        :rtype: bool
        """
        if not self.has_links_configured:
            return False
        if self.unlinked_accounts:
            return False
        return all(g.is_balanced for g in self.coverage_groups)
