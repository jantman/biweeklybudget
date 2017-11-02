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

import pytest

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.models.account import Account
from biweeklybudget.models.budget_model import Budget


@pytest.mark.acceptance
@pytest.mark.usefixtures('class_refresh_db', 'refreshdb')
@pytest.mark.incremental
class TestTransStandingBudgetBalanceUpdate(AcceptanceHelper):

    def test_0_verify_db(self, testdb):
        """initial state verification"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 3
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert float(standing.current_balance) == 9482.29
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None

    def test_1_add_trans_periodic_budget(self, testdb):
        """add a transaction against a periodic budget"""
        testdb.add(Transaction(
            actual_amount=222.22,
            budgeted_amount=123.45,
            description='T4',
            notes='notesT4',
            account=testdb.query(Account).get(1),
            budget=testdb.query(Budget).get(2)
        ))
        testdb.flush()
        testdb.commit()

    def test_2_verify_db(self, testdb):
        """verify no budget objects changed"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 4
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert float(standing.current_balance) == 9482.29
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None

    def test_3_add_trans_standing_budget(self, testdb):
        """add a transaction against a standing budget"""
        testdb.add(Transaction(
            actual_amount=222.22,
            budgeted_amount=123.45,
            description='T5',
            notes='notesT5',
            account=testdb.query(Account).get(1),
            budget=testdb.query(Budget).get(5)
        ))
        testdb.flush()
        testdb.commit()

    def test_4_verify_db(self, testdb):
        """verify the standing budget balance was updated"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 5
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert float(standing.current_balance) == 9260.07
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None

    def test_5_edit_trans_standing_budget(self, testdb):
        """edit a transaction against a standing budget"""
        t = testdb.query(Transaction).get(5)
        t.actual_amount = 111.11
        testdb.add(t)
        testdb.flush()
        testdb.commit()

    def test_6_verify_db(self, testdb):
        """verify the standing budget balance was updated"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 5
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert float(standing.current_balance) == 9371.18
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None

    def test_7_edit_trans_standing_budget(self, testdb):
        """edit a transaction against a standing budget"""
        t = testdb.query(Transaction).get(5)
        t.actual_amount = -111.11
        testdb.add(t)
        testdb.flush()
        testdb.commit()

    def test_8_verify_db(self, testdb):
        """verify the standing budget balance was updated"""
        max_t = max([
            t.id for t in testdb.query(Transaction).all()
        ])
        assert max_t == 5
        standing = testdb.query(Budget).get(5)
        assert standing.is_periodic is False
        assert standing.name == 'Standing2'
        assert float(standing.current_balance) == 9593.40
        periodic = testdb.query(Budget).get(2)
        assert periodic.is_periodic is True
        assert periodic.name == 'Periodic2'
        assert periodic.current_balance is None
