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
import logging
from decimal import Decimal
from datetime import date

from biweeklybudget.tests.migrations.migration_test_helpers import MigrationTest

logger = logging.getLogger(__name__)


@pytest.mark.migrations
class TestAddBudgetTransactionModel(MigrationTest):
    """
    Test for revision 04e61490804b
    """

    migration_rev = '04e61490804b'

    def data_setup(self, engine):
        """method to setup sample data in empty tables"""
        sql = [
            "INSERT INTO accounts SET name='acct1', acct_type=1, "
            "reconcile_trans=0;",
            "INSERT INTO accounts SET name='acct2', acct_type=2, "
            "reconcile_trans=1;",
            "INSERT INTO budgets SET name='budg1';",
            "INSERT INTO budgets SET name='budg2';",
            "INSERT INTO scheduled_transactions SET amount=567.34, "
            "description='st1', account_id=2, budget_id=1, is_active=1, "
            "num_per_period=1;",
            "INSERT INTO transactions SET description='t1', account_id=1, "
            "budget_id=1, actual_amount=123.45;",
            "INSERT INTO transactions SET description='t2', account_id=1, "
            "budget_id=2, actual_amount=345.67, budgeted_amount=567.89;",
            "INSERT INTO transactions SET description='t3', account_id=2, "
            "budget_id=1, actual_amount=345.19, budgeted_amount=567.34, "
            "date='2018-02-24', notes='myNotes', scheduled_trans_id=1;",
        ]
        conn = engine.connect()
        for s in sql:
            logger.debug('Executing: %s', s)
            conn.execute(s)
        conn.close()

    def verify_before(self, engine):
        """method to verify data before forward migration, and after reverse"""
        conn = engine.connect()
        txns = [
            dict(r) for r in conn.execute('SELECT * FROM transactions')
        ]
        conn.close()
        assert txns == [
            {
                'id': 1,
                'date': None,
                'actual_amount': Decimal('123.4500'),
                'budgeted_amount': None,
                'description': 't1',
                'notes': None,
                'account_id': 1,
                'scheduled_trans_id': None,
                'budget_id': 1,
                'transfer_id': None
            },
            {
                'id': 2,
                'date': None,
                'actual_amount': Decimal('345.67'),
                'budgeted_amount': Decimal('567.89'),
                'description': 't2',
                'notes': None,
                'account_id': 1,
                'scheduled_trans_id': None,
                'budget_id': 2,
                'transfer_id': None
            },
            {
                'id': 3,
                'date': date(2018, 2, 24),
                'actual_amount': Decimal('345.19'),
                'budgeted_amount': Decimal('567.34'),
                'description': 't3',
                'notes': 'myNotes',
                'account_id': 2,
                'scheduled_trans_id': 1,
                'budget_id': 1,
                'transfer_id': None
            }
        ]

    def verify_after(self, engine):
        """method to verify data after forward migration"""
        conn = engine.connect()
        txns = [
            dict(r) for r in conn.execute('SELECT * FROM transactions')
        ]
        bts = [
            dict(r) for r in conn.execute('SELECT * FROM budget_transactions')
        ]
        conn.close()
        assert txns == [
            {
                'id': 1,
                'date': None,
                'budgeted_amount': None,
                'description': 't1',
                'notes': None,
                'account_id': 1,
                'scheduled_trans_id': None,
                'transfer_id': None,
                'planned_budget_id': None
            },
            {
                'id': 2,
                'date': None,
                'budgeted_amount': Decimal('567.89'),
                'description': 't2',
                'notes': None,
                'account_id': 1,
                'scheduled_trans_id': None,
                'planned_budget_id': 2,
                'transfer_id': None
            },
            {
                'id': 3,
                'date': date(2018, 2, 24),
                'budgeted_amount': Decimal('567.34'),
                'description': 't3',
                'notes': 'myNotes',
                'account_id': 2,
                'scheduled_trans_id': 1,
                'planned_budget_id': 1,
                'transfer_id': None
            }
        ]
        assert bts == [
            {
                'id': 1,
                'trans_id': 1,
                'amount': Decimal('123.4500'),
                'budget_id': 1
            },
            {
                'id': 2,
                'trans_id': 2,
                'amount': Decimal('345.6700'),
                'budget_id': 2
            },
            {
                'id': 3,
                'trans_id': 3,
                'amount': Decimal('345.19'),
                'budget_id': 1
            }
        ]
