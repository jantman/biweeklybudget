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
from datetime import date
from sqlalchemy.orm.session import Session
from decimal import Decimal

from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.models.utils import (
    do_budget_transfer, resolve_by_name_or_id
)
from biweeklybudget.models.budget_model import Budget
from biweeklybudget.models.account import Account

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
                budget_amounts={budg1: Decimal('123.45')},
                budgeted_amount=Decimal('123.45'),
                description=desc,
                account=acct,
                notes='foo',
                planned_budget=budg1
            ),
            call(
                date=pp.start_date,
                budget_amounts={standing: Decimal('-123.45')},
                budgeted_amount=Decimal('-123.45'),
                description=desc,
                account=acct,
                notes='foo',
                planned_budget=standing
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


class TestResolveByNameOrId(object):
    """
    Tests for :py:func:`~.resolve_by_name_or_id`.

    The rules under test are R1-R4 of the feature data model: strip and coerce,
    try an all-digits value as a primary key, then fall back to a
    case-insensitive whole-name match, then give up.
    """

    def setup_method(self):
        self.mock_sess = Mock(spec_set=Session)
        self.mock_query = Mock()
        self.mock_sess.query.return_value = self.mock_query
        self.mock_query.filter.return_value = self.mock_query

    def _set_results(self, by_id=None, by_name=None):
        self.mock_query.get.return_value = by_id
        self.mock_query.one_or_none.return_value = by_name

    def test_digits_resolve_by_id(self):
        budg = Mock(spec_set=Budget)
        self._set_results(by_id=budg)
        assert resolve_by_name_or_id(self.mock_sess, Budget, '7') == budg
        assert self.mock_query.get.mock_calls == [call(7)]
        # the name path must not have been touched at all
        assert self.mock_query.filter.mock_calls == []

    def test_name_resolves_by_name(self):
        budg = Mock(spec_set=Budget)
        self._set_results(by_name=budg)
        assert resolve_by_name_or_id(
            self.mock_sess, Budget, 'Groceries'
        ) == budg
        assert self.mock_query.get.mock_calls == []
        assert len(self.mock_query.filter.mock_calls) == 1
        assert self.mock_query.one_or_none.mock_calls == [call()]

    def test_digits_missing_by_id_fall_back_to_name(self):
        """A Budget literally named "2024" must stay reachable (rule R3)."""
        budg = Mock(spec_set=Budget)
        self._set_results(by_id=None, by_name=budg)
        assert resolve_by_name_or_id(
            self.mock_sess, Budget, '2024'
        ) == budg
        assert self.mock_query.get.mock_calls == [call(2024)]
        assert len(self.mock_query.filter.mock_calls) == 1

    def test_whitespace_is_stripped(self):
        acct = Mock(spec_set=Account)
        self._set_results(by_name=acct)
        assert resolve_by_name_or_id(
            self.mock_sess, Account, '  CHASE  '
        ) == acct
        # the stripped value is what gets compared; confirmed by the fact that
        # the ID path was skipped for a non-digit value and the name path ran
        assert len(self.mock_query.filter.mock_calls) == 1

    def test_whitespace_stripped_digits_still_hit_id(self):
        acct = Mock(spec_set=Account)
        self._set_results(by_id=acct)
        assert resolve_by_name_or_id(
            self.mock_sess, Account, ' 3 '
        ) == acct
        assert self.mock_query.get.mock_calls == [call(3)]

    def test_name_match_is_case_insensitive(self):
        acct = Mock(spec_set=Account)
        self._set_results(by_name=acct)
        res = resolve_by_name_or_id(self.mock_sess, Account, 'ChAsE')
        assert res == acct
        assert len(self.mock_query.filter.mock_calls) == 1
        criterion = self.mock_query.filter.call_args[0][0]
        sql = str(criterion.compile(compile_kwargs={'literal_binds': True}))
        # lower() is applied to the column explicitly, rather than the match
        # being left to depend on the database's collation
        assert 'lower(accounts.name)' in sql.lower()
        assert "'chase'" in sql

    def test_no_match_returns_none(self):
        self._set_results(by_id=None, by_name=None)
        assert resolve_by_name_or_id(
            self.mock_sess, Budget, 'Nope'
        ) is None

    def test_none_returns_none_without_querying(self):
        assert resolve_by_name_or_id(self.mock_sess, Budget, None) is None
        assert self.mock_sess.mock_calls == []

    def test_empty_string_returns_none_without_querying(self):
        assert resolve_by_name_or_id(self.mock_sess, Budget, '') is None
        assert self.mock_sess.mock_calls == []

    def test_whitespace_only_returns_none_without_querying(self):
        assert resolve_by_name_or_id(self.mock_sess, Budget, '   ') is None
        assert self.mock_sess.mock_calls == []

    def test_non_string_value_is_coerced(self):
        """Form data is strings, but JSON bodies can carry a real integer."""
        budg = Mock(spec_set=Budget)
        self._set_results(by_id=budg)
        assert resolve_by_name_or_id(self.mock_sess, Budget, 5) == budg
        assert self.mock_query.get.mock_calls == [call(5)]

    def test_negative_number_is_treated_as_a_name(self):
        """"-1" is not all-digits, so it can only be a name."""
        self._set_results(by_id=None, by_name=None)
        assert resolve_by_name_or_id(self.mock_sess, Budget, '-1') is None
        assert self.mock_query.get.mock_calls == []
        assert len(self.mock_query.filter.mock_calls) == 1
