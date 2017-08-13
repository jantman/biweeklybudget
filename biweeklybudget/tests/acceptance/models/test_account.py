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
from decimal import Decimal

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.models.account import Account
from biweeklybudget.models.ofx_transaction import OFXTransaction


@pytest.mark.acceptance
class TestLastOFXInterestCharge(AcceptanceHelper):

    def test_credit_one(self, testdb):
        acct = testdb.query(Account).get(3)
        latest_interest = acct.latest_ofx_interest_charge
        assert latest_interest is not None
        assert isinstance(latest_interest, OFXTransaction)
        assert latest_interest.account_id == 3
        assert latest_interest.fitid == 'T3'
        assert latest_interest.account_amount == Decimal('16.25')
        assert latest_interest.statement_id == 6

    def test_credit_two(self, testdb):
        acct = testdb.query(Account).get(4)
        latest_interest = acct.latest_ofx_interest_charge
        assert latest_interest is not None
        assert isinstance(latest_interest, OFXTransaction)
        assert latest_interest.account_id == 4
        assert latest_interest.fitid == '001'
        assert latest_interest.account_amount == Decimal('28.53')
        assert latest_interest.statement_id == 7
