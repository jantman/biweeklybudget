"""
The latest version of this package is available at:
<http://github.com/jantman/biweeklybudget>

################################################################################
Copyright 2016 Jason Antman <jason@jasonantman.com> <http://www.jasonantman.com>

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
from datetime import date
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import null

from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.budget_transaction import BudgetTransaction
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.tests.unit_helpers import binexp_to_dict

import pytest

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call  # noqa
else:
    from unittest.mock import Mock, patch, call  # noqa

pbm = 'biweeklybudget.models.transaction'


class TestTransactionModel(object):

    @patch('%s.RECONCILE_BEGIN_DATE' % pbm, date(2017, 3, 17))
    def test_unreconciled(self):
        Transaction()
        m_db = Mock()
        m_q = Mock(spec_set=Query)
        m_filt = Mock(spec_set=Query)
        m_db.query.return_value = m_q
        m_q.filter.return_value = m_filt
        res = Transaction.unreconciled(m_db)
        assert res == m_filt
        assert len(m_db.mock_calls) == 2
        assert m_db.mock_calls[0] == call.query(Transaction)
        kall = m_db.mock_calls[1]
        assert kall[0] == 'query().filter'
        expected1 = Transaction.reconcile.__eq__(null())
        expected2 = Transaction.date.__ge__(date(2017, 3, 17))
        expected3 = Transaction.account.has(reconcile_trans=True)
        assert len(kall[1]) == 3
        assert str(expected1) == str(kall[1][0])
        assert binexp_to_dict(expected2) == binexp_to_dict(kall[1][1])
        assert str(expected3) == str(kall[1][2])


class TestSetBudgetAmounts(object):

    def test_none(self):
        mock_sess = Mock()
        with patch('%s.inspect' % pbm) as mock_inspect:
            type(mock_inspect.return_value).session = mock_sess
            t = Transaction()
            with pytest.raises(AssertionError):
                t.set_budget_amounts({})
        assert mock_sess.mock_calls == []

    def test_none_but_existing(self):
        mock_sess = Mock()
        with patch('%s.inspect' % pbm) as mock_inspect:
            type(mock_inspect.return_value).session = mock_sess
            b1 = Budget(name='my_budg')
            b2 = Budget(name='my_budg2')
            t = Transaction(
                budget_amounts={
                    b1: Decimal('10.00'),
                    b2: Decimal('90.00')
                }
            )
            assert len(t.budget_transactions) == 2
            for bt in t.budget_transactions:
                assert isinstance(bt, BudgetTransaction)
                assert bt.transaction == t
            assert {
                bt.budget: bt.amount for bt in t.budget_transactions
            } == {
                b1: Decimal('10.00'),
                b2: Decimal('90.00')
            }
            mock_sess.reset_mock()
            with pytest.raises(AssertionError):
                t.set_budget_amounts({})
        assert mock_sess.mock_calls == []

    def test_add_one(self):
        mock_sess = Mock()
        with patch('%s.inspect' % pbm) as mock_inspect:
            type(mock_inspect.return_value).session = mock_sess
            b1 = Budget(name='my_budg')
            t = Transaction(
                budget_amounts={b1: Decimal('10.00')}
            )
            assert len(t.budget_transactions) == 1
            assert t.budget_transactions[0].transaction == t
            assert t.budget_transactions[0].budget == b1
            assert t.budget_transactions[0].amount == Decimal('10.00')
        assert mock_sess.mock_calls == []

    def test_add_three(self):
        mock_sess = Mock()
        with patch('%s.inspect' % pbm) as mock_inspect:
            type(mock_inspect.return_value).session = mock_sess
            b1 = Budget(name='my_budg')
            b2 = Budget(name='my_budg2')
            b3 = Budget(name='my_budg3')
            t = Transaction(
                budget_amounts={
                    b1: Decimal('50.00'),
                    b2: Decimal('10.00'),
                    b3: Decimal('40.00')
                }
            )
            assert len(t.budget_transactions) == 3
            for bt in t.budget_transactions:
                assert isinstance(bt, BudgetTransaction)
                assert bt.transaction == t
            assert {
                bt.budget: bt.amount for bt in t.budget_transactions
            } == {
                b1: Decimal('50.00'),
                b2: Decimal('10.00'),
                b3: Decimal('40.00')
            }
        assert mock_sess.mock_calls == []

    def test_sync(self):
        mock_sess = Mock()
        with patch('%s.inspect' % pbm) as mock_inspect:
            type(mock_inspect.return_value).session = mock_sess
            b1 = Budget(name='my_budg')
            b2 = Budget(name='my_budg2')
            b3 = Budget(name='my_budg3')
            t = Transaction(
                budget_amounts={
                    b1: Decimal('10.00'),
                    b2: Decimal('90.00')
                }
            )
            mock_sess.reset_mock()
            t.set_budget_amounts({
                b1: Decimal('40.00'),
                b3: Decimal('60.00')
            })

        assert len(t.budget_transactions) == 3
        for bt in t.budget_transactions:
            assert isinstance(bt, BudgetTransaction)
            assert bt.transaction == t
        assert {
            bt.budget: bt.amount for bt in t.budget_transactions
        } == {
            b1: Decimal('40.00'),
            b2: Decimal('90.00'),
            b3: Decimal('60.00')
        }

        assert len(mock_sess.mock_calls) == 1
        assert mock_sess.mock_calls[0][0] == 'delete'
        assert mock_sess.mock_calls[0][1][0].budget == b2
        assert mock_sess.mock_calls[0][1][0].amount == Decimal('90.00')
