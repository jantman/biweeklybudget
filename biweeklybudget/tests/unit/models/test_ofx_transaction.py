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
from datetime import datetime, date
from decimal import Decimal

from biweeklybudget.vendored.ofxparse.ofxparse import Transaction
from pytz import UTC
from sqlalchemy.orm.query import Query
from sqlalchemy.sql.expression import null

from biweeklybudget.models.ofx_transaction import OFXTransaction
from biweeklybudget.models.ofx_statement import OFXStatement
from biweeklybudget.models.account import Account
from biweeklybudget.tests.unit_helpers import binexp_to_dict

# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    from mock import Mock, patch, call  # noqa
else:
    from unittest.mock import Mock, patch, call  # noqa

pbm = 'biweeklybudget.models.ofx_transaction'


class TestParamsFromOfxparserTransaction(object):

    def setup(self):
        trans = Transaction()
        trans.payee = 'PayeeName'
        trans.type = 'TType'
        trans.date = datetime(2017, 3, 10, 14, 15, 16)
        trans.amount = 123.45
        trans.id = 'ABC123'
        trans.memo = 'TMemo'
        self.trans = trans
        self.stmt = Mock(spec_set=OFXStatement)
        self.acct_id = 2

    def test_simple(self):
        res = OFXTransaction.params_from_ofxparser_transaction(
            self.trans, self.acct_id, self.stmt
        )
        assert res == {
            'account_id': self.acct_id,
            'statement': self.stmt,
            'memo': 'TMemo',
            'name': 'PayeeName',
            'amount': 123.45,
            'trans_type': 'TType',
            'date_posted': datetime(2017, 3, 10, 14, 15, 16, tzinfo=UTC),
            'fitid': 'ABC123',
            'sic': None,
            'mcc': ''
        }

    def test_cat_memo(self):
        res = OFXTransaction.params_from_ofxparser_transaction(
            self.trans, self.acct_id, self.stmt, cat_memo=True
        )
        assert res == {
            'account_id': self.acct_id,
            'statement': self.stmt,
            'name': 'PayeeNameTMemo',
            'amount': 123.45,
            'trans_type': 'TType',
            'date_posted': datetime(2017, 3, 10, 14, 15, 16, tzinfo=UTC),
            'fitid': 'ABC123',
            'sic': None,
            'mcc': ''
        }

    def test_extra_attrs(self):
        self.trans.mcc = 'TMCC'
        self.trans.sic = 456
        self.trans.checknum = 789
        res = OFXTransaction.params_from_ofxparser_transaction(
            self.trans, self.acct_id, self.stmt
        )
        assert res == {
            'account_id': self.acct_id,
            'statement': self.stmt,
            'memo': 'TMemo',
            'name': 'PayeeName',
            'amount': 123.45,
            'trans_type': 'TType',
            'date_posted': datetime(2017, 3, 10, 14, 15, 16, tzinfo=UTC),
            'fitid': 'ABC123',
            'sic': 456,
            'mcc': 'TMCC',
            'checknum': 789
        }

    def test_account_amount(self):
        ot = OFXTransaction(
            account=Mock(spec_set=Account, negate_ofx_amounts=False),
            amount=Decimal(123.45)
        )
        assert ot.account_amount == 123.45

    def test_account_amount_negated(self):
        ot = OFXTransaction(
            account=Mock(spec_set=Account, negate_ofx_amounts=True),
            amount=Decimal(123.45)
        )
        assert float(ot.account_amount) == -123.45

    @patch('%s.RECONCILE_BEGIN_DATE' % pbm, date(2017, 3, 17))
    def test_unreconciled(self):
        m_db = Mock()
        m_q = Mock(spec_set=Query)
        m_filt = Mock(spec_set=Query)
        m_db.query.return_value = m_q
        m_q.filter.return_value = m_filt
        res = OFXTransaction.unreconciled(m_db)
        assert res == m_filt
        assert len(m_db.mock_calls) == 2
        assert m_db.mock_calls[0] == call.query(OFXTransaction)
        kall = m_db.mock_calls[1]
        assert kall[0] == 'query().filter'
        expected1 = OFXTransaction.reconcile.__eq__(null())
        cutoff = datetime(2017, 3, 17, 0, 0, 0, tzinfo=UTC)
        expected2 = OFXTransaction.date_posted.__ge__(cutoff)
        expected3 = OFXTransaction.account.has(reconcile_trans=True)
        assert len(kall[1]) == 3
        assert str(expected1) == str(kall[1][0])
        assert binexp_to_dict(expected2) == binexp_to_dict(kall[1][1])
        assert str(kall[1][2]) == str(expected3)
