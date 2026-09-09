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

from sqlalchemy import Column, ForeignKey, Integer, Table

from biweeklybudget.models.base import Base

#: Association table linking a standing :py:class:`~.Budget` to the
#: :py:class:`~.Account` or accounts that physically hold its money.
#:
#: The relationship is deliberately **many-to-many**. One savings account
#: commonly holds several earmarked standing budgets -- an emergency fund, a
#: vacation fund and a car repair fund can all live in the same account -- and
#: a single budget may be spread across more than one account. A one-to-one
#: link cannot express either case.
#:
#: The association carries **no amount and no split**, and it must stay that
#: way. Nothing in this application records how much of a budget's balance
#: sits in which of its accounts, so attributing part of a budget's balance to
#: an individual account would mean inventing an allocation rule. That is why
#: :py:class:`~biweeklybudget.cashposition.CashPosition` reports balance
#: deltas over *coverage groups* -- the maximal sets of accounts and budgets
#: reachable through these links -- rather than per account. See GitHub issue
#: #321.
#:
#: The composite primary key makes each pairing unique for free, so the same
#: link cannot be recorded twice. ``ON DELETE CASCADE`` on both foreign keys
#: means deleting either a Budget or an Account takes its association rows
#: with it, so no row can outlive the record it refers to.
budget_accounts = Table(
    'budget_accounts',
    Base.metadata,
    Column(
        'budget_id',
        Integer,
        ForeignKey('budgets.id', ondelete='CASCADE'),
        primary_key=True,
        nullable=False
    ),
    Column(
        'account_id',
        Integer,
        ForeignKey('accounts.id', ondelete='CASCADE'),
        primary_key=True,
        nullable=False
    ),
    mysql_engine='InnoDB'
)
