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
from datetime import date
from sqlalchemy.orm.session import Session
from decimal import Decimal

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.models.utils import do_budget_transfer
from biweeklybudget.models.budget_model import Budget

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call
else:
    from unittest.mock import Mock, patch, call

pbm = 'biweeklybudget.models.utils'


class TestDoBudgetTransfer(object):

    def test_simple(self):
        mock_sess = Mock(spec_set=Session)
        pp = Mock(spec_set=BiweeklyPayPeriod)
        type(pp).start_date = date(2017, 1, 1)
        type(pp).end_date = date(2017, 1, 13)
        standing = Mock(spec_set=Budget, is_periodic=False)
        type(standing).id = 9
        type(standing).name = 'standingBudget'
        budg1 = Mock(spec_set=Budget)
        type(budg1).id = 1
        type(budg1).name = 'one'
        t1 = Mock()
        t2 = Mock()
        tr1 = Mock()
        tr2 = Mock()
        acct = Mock()
        desc = 'Budget Transfer - 123.45 from one (1) to standingBudget (9)'
        with patch('%s.Transaction' % pbm, autospec=True) as mock_t:
            with patch('%s.TxnReconcile' % pbm, autospec=True) as mock_tr:
                mock_t.side_effect = [t1, t2]
                mock_tr.side_effect = [tr1, tr2]
                res = do_budget_transfer(
                    mock_sess,
                    pp.start_date,
                    Decimal('123.45'),
                    acct,
                    budg1,
                    standing,
                    notes='foo'
                )
        assert res == [t1, t2]
        assert mock_t.mock_calls == [
            call(
                date=pp.start_date,
                actual_amount=Decimal('123.45'),
                budgeted_amount=Decimal('123.45'),
                description=desc,
                account=acct,
                budget=budg1,
                notes='foo'
            ),
            call(
                date=pp.start_date,
                actual_amount=Decimal('-123.45'),
                budgeted_amount=Decimal('-123.45'),
                description=desc,
                account=acct,
                budget=standing,
                notes='foo'
            )
        ]
        assert mock_tr.mock_calls == [
            call(transaction=t1, note=desc),
            call(transaction=t2, note=desc)
        ]
        assert mock_sess.mock_calls == [
            call.add(t1),
            call.add(t2),
            call.add(t1),
            call.add(t2),
            call.add(tr1),
            call.add(tr2)
        ]
