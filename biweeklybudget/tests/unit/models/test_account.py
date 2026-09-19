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
from sqlalchemy.orm.query import Query

from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.tests.unit_helpers import binexp_to_dict

from unittest.mock import Mock, call


class TestActiveAccounts(object):
    """
    Tests for :py:meth:`~.Account.active_accounts`, the single definition of
    "an Account that may be chosen" added for GitHub issue #356.
    """

    def test_filters_on_is_active_and_orders_by_name(self):
        m_db = Mock()
        m_q = Mock(spec_set=Query)
        m_filt = Mock(spec_set=Query)
        m_order = Mock(spec_set=Query)
        m_db.query.return_value = m_q
        m_q.filter.return_value = m_filt
        m_filt.order_by.return_value = m_order
        res = Account.active_accounts(m_db)
        # a Query is returned, not a list; callers compose or call .all()
        assert res == m_order
        assert m_db.mock_calls[0] == call.query(Account)
        kall = m_db.mock_calls[1]
        assert kall[0] == 'query().filter'
        assert len(kall[1]) == 1
        assert str(Account.is_active.__eq__(True)) == str(kall[1][0])
        assert m_db.mock_calls[2] == call.query().filter().order_by(
            Account.name
        )
        assert len(m_db.mock_calls) == 3

    def test_does_not_filter_on_account_type(self):
        """
        Unlike :py:meth:`~.Account.active_credit_accounts`, every type of
        Account may be chosen; only ``is_active`` narrows the result.
        """
        m_db = Mock()
        m_q = Mock(spec_set=Query)
        m_filt = Mock(spec_set=Query)
        m_db.query.return_value = m_q
        m_q.filter.return_value = m_filt
        Account.active_accounts(m_db)
        filter_args = m_db.mock_calls[1][1]
        for a in filter_args:
            assert 'acct_type' not in str(a)

    def test_active_credit_accounts_is_unchanged(self):
        """
        The credit-only query this one is modelled on still filters on both
        type and active state; the two are not interchangeable.
        """
        m_db = Mock()
        m_q = Mock(spec_set=Query)
        m_filt = Mock(spec_set=Query)
        m_db.query.return_value = m_q
        m_q.filter.return_value = m_filt
        Account.active_credit_accounts(m_db)
        kall = m_db.mock_calls[1]
        assert kall[0] == 'query().filter'
        assert len(kall[1]) == 2
        assert binexp_to_dict(
            Account.acct_type.__eq__(AcctType.Credit)
        ) == binexp_to_dict(kall[1][0])
        assert str(Account.is_active.__eq__(True)) == str(kall[1][1])
