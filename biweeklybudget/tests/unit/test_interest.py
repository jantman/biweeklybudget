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
from datetime import date, timedelta
from sqlalchemy.orm.session import Session
import pytest
from math import ceil
from decimal import Decimal
from copy import deepcopy

from biweeklybudget.interest import (
    InterestHelper,
    _InterestCalculation, AdbCompoundedDaily, SimpleInterest,
    _BillingPeriod,
    _MinPaymentFormula, MinPaymentAmEx, MinPaymentCiti, MinPaymentDiscover,
    _PayoffMethod, MinPaymentMethod, FixedPaymentMethod,
    LowestBalanceFirstMethod, HighestBalanceFirstMethod,
    LowestInterestRateFirstMethod, HighestInterestRateFirstMethod,
    calculate_payoffs, CCStatement,
    INTEREST_CALCULATION_NAMES, MIN_PAYMENT_FORMULA_NAMES,
    PAYOFF_METHOD_NAMES
)
from biweeklybudget.utils import dtnow
from biweeklybudget.models.account import Account, AcctType
from biweeklybudget.tests.unit_helpers import binexp_to_dict
from biweeklybudget.models.account_balance import AccountBalance


# https://code.google.com/p/mock/issues/detail?id=249
# py>=3.4 should use unittest.mock not the mock package on pypi
if (
        sys.version_info[0] < 3 or
        sys.version_info[0] == 3 and sys.version_info[1] < 4
):
    PY34PLUS = False
    from mock import Mock, PropertyMock, call, patch
else:
    PY34PLUS = True
    from unittest.mock import Mock, PropertyMock, call, patch


pbm = 'biweeklybudget.interest'
pb = '%s.InterestHelper' % pbm


def pctdiff(a, b):
    """Return the percent difference of two Decimals, as a Decimal percent"""
    return abs(a - b) / abs(a)


class FixedInterest(_InterestCalculation):
    """
    Test class for fixed interest amount.
    """

    #: Human-readable string name of the interest calculation type.
    description = 'Test class for fixed interest amount.'

    def calculate(self, principal, first_d, last_d, transactions={}):
        """
        Calculate compound interest for the specified principal.

        :param principal: balance at beginning of statement period
        :type principal: decimal.Decimal
        :param first_d: date of beginning of statement period
        :type first_d: datetime.date
        :param last_d: last date of statement period
        :type last_d: datetime.date
        :param transactions: dict of datetime.date to float amount adjust
          the balance by on the specified dates.
        :type transactions: dict
        :return: dict describing the result: end_balance (float),
          interest_paid (float)
        :rtype: dict
        """
        num_days = 0

        d = first_d
        while d <= last_d:
            num_days += 1
            if d in transactions:
                principal += transactions[d]
            d += timedelta(days=1)
        return {
            'interest_paid': self.apr,
            'end_balance': principal + self.apr
        }


class TestInterestHelper(object):

    def setup(self):
        bal3 = Mock(
            spec_set=AccountBalance,
            ledger=Decimal('-952.06'),
            ledger_date=(dtnow() - timedelta(hours=13))
        )
        bal4 = Mock(
            spec_set=AccountBalance,
            ledger=Decimal('-5498.65'),
            ledger_date=(dtnow() - timedelta(hours=36))
        )
        self.accts = {
            3: Mock(
                spec_set=Account,
                id=3,
                description='First Credit Card, limit 2000',
                name='CreditOne',
                ofx_cat_memo_to_name=False,
                acct_type=AcctType.Credit,
                credit_limit=Decimal('2000.00'),
                is_active=True,
                apr=Decimal('0.0100'),
                negate_ofx_amounts=True,
                interest_class_name='AdbCompoundedDaily',
                min_payment_class_name='MinPaymentAmEx',
                balance=bal3,
                effective_apr=Decimal('0.0100')
            ),
            4: Mock(
                spec_set=Account,
                id=4,
                description='Credit 2 limit 5500',
                name='CreditTwo',
                ofx_cat_memo_to_name=False,
                ofxgetter_config_json='',
                vault_creds_path='/foo/bar',
                acct_type=AcctType.Credit,
                credit_limit=Decimal('5500'),
                is_active=True,
                apr=Decimal('0.1000'),
                interest_class_name='AdbCompoundedDaily',
                min_payment_class_name='MinPaymentDiscover',
                balance=bal4,
                effective_apr=Decimal('0.1000')
            )
        }
        self.mock_sess = Mock(spec_set=Session)
        self.mock_sess.query.return_value.filter.return_value.all.\
            return_value = self.accts.values()
        self.cls = InterestHelper(self.mock_sess)

    def test_init(self):
        assert self.cls._increases == {}
        assert self.cls._onetimes == {}
        assert self.mock_sess.mock_calls[0] == call.query(Account)
        kall = self.mock_sess.mock_calls[1]
        assert kall[0] == 'query().filter'
        assert len(kall[1]) == 2
        assert binexp_to_dict(kall[1][0]) == binexp_to_dict(
            Account.acct_type.__eq__(AcctType.Credit)
        )
        assert str(kall[1][1]) == 'accounts.is_active = true'
        assert self.mock_sess.mock_calls[2] == call.query().filter().all()
        assert self.cls.accounts == {
            3: self.accts[3],
            4: self.accts[4]
        }
        assert len(self.cls._statements) == 2
        s3 = self.cls._statements[3]
        assert isinstance(s3, CCStatement)
        assert isinstance(s3._billing_period, _BillingPeriod)
        assert s3._billing_period._period_for_date == date(2017, 7, 27)
        assert isinstance(s3._interest_cls, AdbCompoundedDaily)
        assert s3._interest_cls.apr == Decimal('0.0100')
        assert isinstance(s3._min_pay_cls, MinPaymentAmEx)
        assert s3._orig_principal == Decimal('952.06')
        assert s3._min_pay is None
        assert s3._transactions == {}
        assert s3._principal == Decimal('952.06')
        s4 = self.cls._statements[4]
        assert isinstance(s4, CCStatement)
        assert isinstance(s4._billing_period, _BillingPeriod)
        assert s4._billing_period._period_for_date == date(2017, 7, 26)
        assert isinstance(s4._interest_cls, AdbCompoundedDaily)
        assert s4._interest_cls.apr == Decimal('0.1000')
        assert isinstance(s4._min_pay_cls, MinPaymentDiscover)
        assert s4._orig_principal == Decimal('5498.65')
        assert s4._min_pay is None
        assert s4._transactions == {}
        assert s4._principal == Decimal('5498.65')

    def test_init_increases_onetimes(self):
        cls = InterestHelper(
            self.mock_sess,
            increases={'foo': 'bar'},
            onetimes={'baz': 'blam'}
        )
        assert cls._increases == {'foo': 'bar'}
        assert cls._onetimes == {'baz': 'blam'}

    def test_min_payments(self):
        res = self.cls.min_payments
        assert res == {
            3: Decimal('35'),
            4: Decimal('109.9730')
        }

    def test_calculate_payoffs(self):
        pm1 = Mock()
        pm2 = Mock()
        pm3 = Mock()
        type(pm3).show_in_ui = False
        meth_names = {
            'PM1': {
                'description': 'pm1desc',
                'doc': 'pm1doc',
                'cls': pm1
            },
            'PM2': {
                'description': 'pm2desc',
                'doc': 'pm2doc',
                'cls': pm2
            },
            'PM3': {
                'description': 'pm3desc',
                'doc': 'pm3doc',
                'cls': pm3
            }
        }
        with patch('%s.PAYOFF_METHOD_NAMES' % pbm, meth_names):
            with patch('%s._calc_payoff_method' % pb) as mock_cpm:
                mock_cpm.side_effect = ['res1', 'res2']
                res = self.cls.calculate_payoffs()
        assert res == {
            'PM1': {
                'description': 'pm1desc',
                'doc': 'pm1doc',
                'results': 'res1'
            },
            'PM2': {
                'description': 'pm2desc',
                'doc': 'pm2doc',
                'results': 'res2'
            }
        }
        assert mock_cpm.mock_calls == [
            call(pm1.return_value),
            call(pm2.return_value)
        ]

    def test_calculate_payoff_method(self):
        mock_m = Mock()
        with patch('%s.calculate_payoffs' % pbm) as mock_calc:
            mock_calc.return_value = [
                (28, Decimal('963.2130700030116938658705389')),
                (164, Decimal('8764.660910733671904414120065'))
            ]
            res = self.cls._calc_payoff_method(mock_m)
        assert res == {
            3: {
                'payoff_months': 28,
                'total_payments': Decimal('963.2130700030116938658705389'),
                'total_interest': Decimal('11.1530700030116938658705389')
            },
            4: {
                'payoff_months': 164,
                'total_payments': Decimal('8764.660910733671904414120065'),
                'total_interest': Decimal('3266.010910733671904414120065')
            }
        }


class TestInterestCalculation(object):

    def test_init(self):
        cls = _InterestCalculation(Decimal('1.23'))
        assert cls._apr == Decimal('1.23')

    def test_description(self):
        cls = _InterestCalculation(Decimal('0.1000'))
        assert hasattr(cls, 'description')

    def test_repr(self):
        cls = _InterestCalculation(Decimal('0.1000'))
        assert str(cls) == '<_InterestCalculation(decimal.Decimal(\'0.1000\'))>'


class TestAdbCompoundedDaily(object):

    def test_description(self):
        cls = AdbCompoundedDaily(Decimal('0.1000'))
        assert hasattr(cls, 'description')

    def test_repr(self):
        cls = AdbCompoundedDaily(Decimal('0.1000'))
        assert str(cls) == '<AdbCompoundedDaily(decimal.Decimal(\'0.1000\'))>'

    def test_calculate(self):
        cls = AdbCompoundedDaily(Decimal('0.1000'))
        res = cls.calculate(
            Decimal('100.00'),
            date(2017, 1, 1),
            (date(2017, 1, 1) + timedelta(days=365))
        )
        assert res == {
            'end_balance': Decimal('110.5487464695276899243379188'),
            'interest_paid': Decimal('10.54874567794529906536521621')
        }

    def test_calculate_transactions(self):
        cls = AdbCompoundedDaily(Decimal('0.1000'))
        end_d = date(2017, 1, 1) + timedelta(days=365)
        res = cls.calculate(
            Decimal('100.00'),
            date(2017, 1, 1),
            end_d,
            transactions={
                date(2017, 6, 1): Decimal('-50.00'),
                (end_d - timedelta(days=1)): Decimal('50.00')
            }
        )
        assert res == {
            'end_balance': Decimal('107.5420752170470026908058809'),
            'interest_paid': Decimal('7.542074651086492634526111808')
        }


class TestSimpleInterest(object):

    def test_description(self):
        cls = SimpleInterest(Decimal('0.1200'))
        assert hasattr(cls, 'description')

    def test_repr(self):
        cls = SimpleInterest(Decimal('0.1200'))
        assert str(cls) == '<SimpleInterest(decimal.Decimal(\'0.1200\'))>'

    def test_calculate(self):
        cls = SimpleInterest(Decimal('0.0100'))
        res = cls.calculate(
            Decimal('100.00'),
            date(2017, 1, 1),
            (date(2017, 1, 1) + timedelta(days=364))
        )
        assert res == {
            'end_balance': Decimal('101.0'),
            'interest_paid': Decimal('1.0')
        }

    def test_calculate_transactions(self):
        cls = SimpleInterest(Decimal('0.0100'))
        end_d = date(2017, 1, 1) + timedelta(days=364)
        res = cls.calculate(
            Decimal('100.00'),
            date(2017, 1, 1),
            end_d,
            transactions={
                date(2017, 6, 1): Decimal('-50.00')
            }
        )
        assert res == {
            'end_balance': Decimal('50.5'),
            'interest_paid': Decimal('0.5')
        }


class TestBillingPeriod(object):

    def test_init(self):
        cls = _BillingPeriod(date(2017, 1, 20))
        assert cls._end_date == date(2017, 1, 31)
        assert cls._start_date == date(2017, 1, 1)
        cls = _BillingPeriod(date(2017, 1, 5))
        assert cls._end_date == date(2016, 12, 31)
        assert cls._start_date == date(2016, 12, 1)

    def test_description(self):
        cls = _BillingPeriod(date(2017, 1, 20))
        assert hasattr(cls, 'description')

    def test_start_date(self):
        cls = _BillingPeriod(date(2017, 1, 20))
        cls._start_date = 'foo'
        assert cls.start_date == 'foo'

    def test_end_date(self):
        cls = _BillingPeriod(date(2017, 1, 20))
        cls._end_date = 'bar'
        assert cls.end_date == 'bar'

    def test_payment_date(self):
        cls = _BillingPeriod(date(2017, 1, 20))
        cls._start_date = date(2017, 1, 1)
        cls._end_date = date(2017, 1, 31)
        assert cls.payment_date == date(2017, 1, 16)

    def test_next(self):
        cls = _BillingPeriod(date(2017, 1, 1))
        cls._start_date = date(2017, 1, 1)
        cls._end_date = date(2017, 1, 31)
        n = cls.next_period
        assert n.start_date == date(2017, 2, 1)
        assert n.end_date == date(2017, 2, 28)

    def test_previous(self):
        cls = _BillingPeriod(date(2017, 1, 1))
        cls._start_date = date(2017, 1, 1)
        cls._end_date = date(2017, 1, 31)
        n = cls.prev_period
        assert n.start_date == date(2016, 12, 1)
        assert n.end_date == date(2016, 12, 31)


class TestMinPaymentFormula(object):

    def test_init(self):
        res = _MinPaymentFormula()
        assert isinstance(res, _MinPaymentFormula)

    def test_type(self):
        cls = _MinPaymentFormula()
        assert hasattr(cls, 'description')


class TestMinPaymentAmEx(object):

    def test_init(self):
        cls = MinPaymentAmEx()
        assert isinstance(cls, _MinPaymentFormula)

    def test_type(self):
        cls = MinPaymentAmEx()
        assert hasattr(cls, 'description')

    def test_calculate_over_35(self):
        cls = MinPaymentAmEx()
        res = cls.calculate(Decimal('10000.00'), Decimal('22.00'))
        assert res == Decimal('122.00')

    def test_calculate_under_35(self):
        cls = MinPaymentAmEx()
        res = cls.calculate(Decimal('100.00'), Decimal('22.00'))
        assert res == Decimal('35.00')


class TestMinPaymentDiscover(object):

    def test_init(self):
        cls = MinPaymentDiscover()
        assert isinstance(cls, _MinPaymentFormula)

    def test_type(self):
        cls = MinPaymentDiscover()
        assert hasattr(cls, 'description')

    def test_calculate_under_35(self):
        cls = MinPaymentDiscover()
        res = cls.calculate(Decimal('1.00'), Decimal('2.00'))
        assert res == Decimal('35.00')

    def test_calculate_2_percent(self):
        cls = MinPaymentDiscover()
        res = cls.calculate(Decimal('10000.00'), Decimal('2.00'))
        assert res == Decimal('200.00')

    def test_calculate_interest_plus_20(self):
        cls = MinPaymentDiscover()
        res = cls.calculate(Decimal('1.00'), Decimal('20.00'))
        assert res == Decimal('40.00')


class TestMinPaymentCiti(object):

    def test_init(self):
        cls = MinPaymentCiti()
        assert isinstance(cls, _MinPaymentFormula)

    def test_type(self):
        cls = MinPaymentCiti()
        assert hasattr(cls, 'description')

    def test_1point5_percent(self):
        cls = MinPaymentCiti()
        res = cls.calculate(Decimal('10000.00'), Decimal('2.00'))
        assert res == Decimal('150.00')

    def test_1percent_plus_interest(self):
        cls = MinPaymentCiti()
        res = cls.calculate(Decimal('10000.00'), Decimal('300.00'))
        assert res == Decimal('400.00')

    def test_25(self):
        cls = MinPaymentCiti()
        res = cls.calculate(Decimal('1.00'), Decimal('2.00'))
        assert res == Decimal('25.00')


class TestPayoffMethod(object):

    def test_init(self):
        cls = _PayoffMethod(Decimal('1.23'))
        assert isinstance(cls, _PayoffMethod)
        assert cls._max_total == Decimal('1.23')

    def test_description(self):
        cls = _PayoffMethod()
        assert hasattr(cls, 'description')

    def test_repr(self):
        cls = _PayoffMethod()
        assert 'PayoffMethod' in cls.__repr__()


class TestMinPaymentMethod(object):

    def test_init(self):
        cls = MinPaymentMethod()
        assert isinstance(cls, _PayoffMethod)

    def test_description(self):
        cls = MinPaymentMethod()
        assert hasattr(cls, 'description')

    def test_find_payments(self):
        cls = MinPaymentMethod()
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('1.11'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('2.22'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('3.33'))
        assert cls.find_payments([s1, s2, s3]) == [
            Decimal('1.11'), Decimal('2.22'), Decimal('3.33')
        ]


class TestFixedPaymentMethod(object):

    def test_init(self):
        cls = FixedPaymentMethod(Decimal('12.34'))
        assert isinstance(cls, _PayoffMethod)
        assert cls._max_total == Decimal('12.34')

    def test_description(self):
        cls = FixedPaymentMethod(Decimal('12.34'))
        assert hasattr(cls, 'description')

    def test_find_payments(self):
        cls = FixedPaymentMethod(Decimal('12.34'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('1.11'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('2.22'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('3.33'))
        assert cls.find_payments([s1, s2, s3]) == [
            Decimal('12.34'), Decimal('12.34'), Decimal('12.34')
        ]


class TestLowestBalanceFirstMethod(object):

    def test_init(self):
        cls = LowestBalanceFirstMethod(Decimal('100.00'))
        assert isinstance(cls, _PayoffMethod)
        assert cls._max_total == Decimal('100.00')

    def test_description(self):
        cls = LowestBalanceFirstMethod(Decimal('100.00'))
        assert hasattr(cls, 'description')

    def test_find_payments(self):
        cls = LowestBalanceFirstMethod(Decimal('100.00'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s1).principal = PropertyMock(return_value=Decimal('10.00'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('5.00'))
        type(s2).principal = PropertyMock(return_value=Decimal('25.00'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s3).principal = PropertyMock(return_value=Decimal('1234.56'))
        s4 = Mock(spec_set=CCStatement)
        type(s4).minimum_payment = PropertyMock(return_value=Decimal('7.00'))
        type(s4).principal = PropertyMock(return_value=Decimal('3.00'))
        assert cls.find_payments([s1, s2, s3, s4]) == [
            Decimal('2.00'),
            Decimal('5.00'),
            Decimal('2.00'),
            Decimal('91.00')
        ]

    def test_find_payments_total_too_low(self):
        cls = LowestBalanceFirstMethod(Decimal('3.00'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s1).principal = PropertyMock(return_value=Decimal('10.00'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('5.00'))
        type(s2).principal = PropertyMock(return_value=Decimal('25.00'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s3).principal = PropertyMock(return_value=Decimal('1234.56'))
        s4 = Mock(spec_set=CCStatement)
        type(s4).minimum_payment = PropertyMock(return_value=Decimal('7.00'))
        type(s4).principal = PropertyMock(return_value=Decimal('3.00'))
        with pytest.raises(TypeError):
            cls.find_payments([s1, s2, s3, s4])


class TestHighestBalanceFirstMethod(object):

    def test_init(self):
        cls = HighestBalanceFirstMethod(Decimal('100.00'))
        assert isinstance(cls, _PayoffMethod)
        assert cls._max_total == Decimal('100.00')

    def test_description(self):
        cls = HighestBalanceFirstMethod(Decimal('100.00'))
        assert hasattr(cls, 'description')

    def test_find_payments(self):
        cls = HighestBalanceFirstMethod(Decimal('100.00'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s1).principal = PropertyMock(return_value=Decimal('10.00'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('5.00'))
        type(s2).principal = PropertyMock(return_value=Decimal('25.00'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s3).principal = PropertyMock(return_value=Decimal('1234.56'))
        s4 = Mock(spec_set=CCStatement)
        type(s4).minimum_payment = PropertyMock(return_value=Decimal('7.00'))
        type(s4).principal = PropertyMock(return_value=Decimal('3.00'))
        assert cls.find_payments([s1, s2, s3, s4]) == [
            Decimal('2.00'),
            Decimal('5.00'),
            Decimal('86.00'),
            Decimal('7.00')
        ]

    def test_find_payments_total_too_low(self):
        cls = HighestBalanceFirstMethod(Decimal('3.00'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s1).principal = PropertyMock(return_value=Decimal('10.00'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('5.00'))
        type(s2).principal = PropertyMock(return_value=Decimal('25.00'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s3).principal = PropertyMock(return_value=Decimal('1234.56'))
        s4 = Mock(spec_set=CCStatement)
        type(s4).minimum_payment = PropertyMock(return_value=Decimal('7.00'))
        type(s4).principal = PropertyMock(return_value=Decimal('3.00'))
        with pytest.raises(TypeError):
            cls.find_payments([s1, s2, s3, s4])


class TestHighestInterestRateFirstMethod(object):

    def test_init(self):
        cls = HighestInterestRateFirstMethod(Decimal('100.00'))
        assert isinstance(cls, _PayoffMethod)
        assert cls._max_total == Decimal('100.00')

    def test_description(self):
        cls = HighestInterestRateFirstMethod(Decimal('100.00'))
        assert hasattr(cls, 'description')

    def test_find_payments(self):
        cls = HighestInterestRateFirstMethod(Decimal('100.00'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s1).apr = PropertyMock(return_value=Decimal('0.0100'))
        type(s1).principal = PropertyMock(return_value=Decimal('10.00'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('5.00'))
        type(s2).apr = PropertyMock(return_value=Decimal('0.0200'))
        type(s2).principal = PropertyMock(return_value=Decimal('25.00'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s3).apr = PropertyMock(return_value=Decimal('0.0800'))
        type(s3).principal = PropertyMock(return_value=Decimal('1234.56'))
        s4 = Mock(spec_set=CCStatement)
        type(s4).minimum_payment = PropertyMock(return_value=Decimal('7.00'))
        type(s4).apr = PropertyMock(return_value=Decimal('0.0300'))
        type(s4).principal = PropertyMock(return_value=Decimal('3.00'))
        assert cls.find_payments([s1, s2, s3, s4]) == [
            Decimal('2.00'),
            Decimal('5.00'),
            Decimal('86.00'),
            Decimal('7.00')
        ]

    def test_find_payments_total_too_low(self):
        cls = HighestInterestRateFirstMethod(Decimal('3.00'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s1).principal = PropertyMock(return_value=Decimal('10.00'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('5.00'))
        type(s2).principal = PropertyMock(return_value=Decimal('25.00'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s3).principal = PropertyMock(return_value=Decimal('1234.56'))
        s4 = Mock(spec_set=CCStatement)
        type(s4).minimum_payment = PropertyMock(return_value=Decimal('7.00'))
        type(s4).principal = PropertyMock(return_value=Decimal('3.00'))
        with pytest.raises(TypeError):
            cls.find_payments([s1, s2, s3, s4])


class TestLowestInterestRateFirstMethod(object):

    def test_init(self):
        cls = LowestInterestRateFirstMethod(Decimal('100.00'))
        assert isinstance(cls, _PayoffMethod)
        assert cls._max_total == Decimal('100.00')

    def test_description(self):
        cls = LowestInterestRateFirstMethod(Decimal('100.00'))
        assert hasattr(cls, 'description')

    def test_find_payments(self):
        cls = LowestInterestRateFirstMethod(Decimal('100.00'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s1).apr = PropertyMock(return_value=Decimal('0.0100'))
        type(s1).principal = PropertyMock(return_value=Decimal('10.00'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('5.00'))
        type(s2).apr = PropertyMock(return_value=Decimal('0.0200'))
        type(s2).principal = PropertyMock(return_value=Decimal('25.00'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s3).apr = PropertyMock(return_value=Decimal('0.0800'))
        type(s3).principal = PropertyMock(return_value=Decimal('1234.56'))
        s4 = Mock(spec_set=CCStatement)
        type(s4).minimum_payment = PropertyMock(return_value=Decimal('7.00'))
        type(s4).apr = PropertyMock(return_value=Decimal('0.0300'))
        type(s4).principal = PropertyMock(return_value=Decimal('3.00'))
        assert cls.find_payments([s1, s2, s3, s4]) == [
            Decimal('86.00'),
            Decimal('5.00'),
            Decimal('2.00'),
            Decimal('7.00')
        ]

    def test_find_payments_total_too_low(self):
        cls = LowestInterestRateFirstMethod(Decimal('3.00'))
        s1 = Mock(spec_set=CCStatement)
        type(s1).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s1).principal = PropertyMock(return_value=Decimal('10.00'))
        s2 = Mock(spec_set=CCStatement)
        type(s2).minimum_payment = PropertyMock(return_value=Decimal('5.00'))
        type(s2).principal = PropertyMock(return_value=Decimal('25.00'))
        s3 = Mock(spec_set=CCStatement)
        type(s3).minimum_payment = PropertyMock(return_value=Decimal('2.00'))
        type(s3).principal = PropertyMock(return_value=Decimal('1234.56'))
        s4 = Mock(spec_set=CCStatement)
        type(s4).minimum_payment = PropertyMock(return_value=Decimal('7.00'))
        type(s4).principal = PropertyMock(return_value=Decimal('3.00'))
        with pytest.raises(TypeError):
            cls.find_payments([s1, s2, s3, s4])


class TestCCStatement(object):

    def test_init(self):
        b = Mock(spec_set=_BillingPeriod)
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        assert cls._billing_period == b
        assert cls._interest_cls == i
        assert cls._min_pay_cls == p
        assert cls._orig_principal == Decimal('1.23')
        assert cls._min_pay is None
        assert cls._transactions == {}
        assert cls._principal == Decimal('1.50')
        assert cls._interest_amt == Decimal('0.27')
        assert i.mock_calls == []

    def test_init_end_none(self):
        b = Mock(spec_set=_BillingPeriod)
        type(b).start_date = PropertyMock(return_value=date(2017, 1, 1))
        type(b).end_date = PropertyMock(return_value=date(2017, 1, 29))
        i = Mock(spec_set=_InterestCalculation)
        i.calculate.return_value = {
            'end_balance': Decimal('100.11'),
            'interest_paid': Decimal('23.45')
        }
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            interest_amt=Decimal('0.27')
        )
        assert cls._billing_period == b
        assert cls._interest_cls == i
        assert cls._min_pay_cls == p
        assert cls._orig_principal == Decimal('1.23')
        assert cls._min_pay is None
        assert cls._transactions == {}
        assert cls._principal == Decimal('100.11')
        assert cls._interest_amt == Decimal('0.27')
        assert i.mock_calls == [
            call.calculate(
                Decimal('1.23'),
                date(2017, 1, 1),
                date(2017, 1, 29),
                {}
            )
        ]
        assert 'CCStatement' in str(cls)

    def test_init_int_none(self):
        b = Mock(spec_set=_BillingPeriod)
        type(b).start_date = PropertyMock(return_value=date(2017, 1, 1))
        type(b).end_date = PropertyMock(return_value=date(2017, 1, 29))
        i = Mock(spec_set=_InterestCalculation)
        i.calculate.return_value = {
            'end_balance': Decimal('100.11'),
            'interest_paid': Decimal('23.45')
        }
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50')
        )
        assert cls._billing_period == b
        assert cls._interest_cls == i
        assert cls._min_pay_cls == p
        assert cls._orig_principal == Decimal('1.23')
        assert cls._min_pay is None
        assert cls._transactions == {}
        assert cls._principal == Decimal('1.50')
        assert cls._interest_amt == Decimal('23.45')
        assert i.mock_calls == [
            call.calculate(
                Decimal('1.23'),
                date(2017, 1, 1),
                date(2017, 1, 29),
                {}
            )
        ]

    def test_init_interest_wrong_class(self):
        b = Mock(spec_set=_BillingPeriod)
        i = None
        p = Mock(spec_set=_MinPaymentFormula)
        with pytest.raises(TypeError):
            CCStatement(
                i, Decimal('1.23'), p, b,
                end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
            )

    def test_init_payment_wrong_class(self):
        b = Mock(spec_set=_BillingPeriod)
        i = Mock(spec_set=_InterestCalculation)
        p = None
        with pytest.raises(TypeError):
            CCStatement(
                i, Decimal('1.23'), p, b,
                end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
            )

    def test_init_billing_wrong_class(self):
        b = None
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        with pytest.raises(TypeError):
            CCStatement(
                i, Decimal('1.23'), p, b,
                end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
            )

    def test_principal(self):
        b = Mock(spec_set=_BillingPeriod)
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        assert cls._principal == Decimal('1.50')
        assert cls.principal == Decimal('1.50')

    def test_interest(self):
        b = Mock(spec_set=_BillingPeriod)
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        assert cls._interest_amt == Decimal('0.27')
        assert cls.interest == Decimal('0.27')

    def test_start_date(self):
        b = Mock(spec_set=_BillingPeriod)
        type(b).start_date = PropertyMock(return_value=date(2017, 1, 1))
        type(b).end_date = PropertyMock(return_value=date(2017, 1, 29))
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        assert cls.start_date == date(2017, 1, 1)

    def test_end_date(self):
        b = Mock(spec_set=_BillingPeriod)
        type(b).start_date = PropertyMock(return_value=date(2017, 1, 1))
        type(b).end_date = PropertyMock(return_value=date(2017, 1, 29))
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        assert cls.end_date == date(2017, 1, 29)

    def test_apr(self):
        b = Mock(spec_set=_BillingPeriod)
        i = Mock(spec_set=_InterestCalculation)
        type(i).apr = PropertyMock(return_value=Decimal('0.1234'))
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        assert cls.apr == Decimal('0.1234')

    def test_minimum_payment(self):
        b = Mock(spec_set=_BillingPeriod)
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        p.calculate.return_value = Decimal('123.45')
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        assert cls._min_pay_cls == p
        assert cls._principal == Decimal('1.50')
        assert cls._interest_amt == Decimal('0.27')
        assert cls.minimum_payment == Decimal('123.45')
        assert p.mock_calls == [
            call.calculate(Decimal('1.50'), Decimal('0.27'))
        ]

    def test_next_with_transactions(self):
        b = Mock(spec_set=_BillingPeriod)
        b_next = Mock(spec_set=_BillingPeriod)
        type(b).next_period = PropertyMock(return_value=b_next)
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        mock_stmt = Mock(spec_set=CCStatement)
        with patch('biweeklybudget.interest.CCStatement', autospec=True) as m:
            m.return_value = mock_stmt
            res = cls.next_with_transactions({'foo': 'bar'})
        assert res == mock_stmt
        assert m.mock_calls == [
            call(
                i, Decimal('1.50'), p, b_next, transactions={'foo': 'bar'}
            )
        ]

    def test_pay(self):
        b = Mock(spec_set=_BillingPeriod)
        b_next = Mock(spec_set=_BillingPeriod)
        type(b_next).payment_date = PropertyMock(return_value=date(2017, 1, 15))
        type(b).next_period = PropertyMock(return_value=b_next)
        i = Mock(spec_set=_InterestCalculation)
        p = Mock(spec_set=_MinPaymentFormula)
        cls = CCStatement(
            i, Decimal('1.23'), p, b,
            end_balance=Decimal('1.50'), interest_amt=Decimal('0.27')
        )
        mock_stmt = Mock(spec_set=CCStatement)
        with patch(
            'biweeklybudget.interest.CCStatement.next_with_transactions',
            autospec=True
        ) as m:
            m.return_value = mock_stmt
            res = cls.pay(Decimal('98.76'))
        assert res == mock_stmt
        assert m.mock_calls == [
            call(cls, {date(2017, 1, 15): Decimal('98.76')})
        ]


class TestCalculatePayoffs(object):

    def test_simple(self):
        def se_interest(bal, *args, **kwargs):
            return {
                'end_balance': bal - Decimal('1.00'),
                'interest_paid': Decimal('1.00')
            }

        def se_minpay_A(*args):
            return Decimal('3.00')

        def se_minpay_B(*args):
            return Decimal('60.00')
        b1 = _BillingPeriod(date(2017, 1, 2))
        i1 = Mock(spec_set=_InterestCalculation)
        i1.calculate.side_effect = se_interest
        p1 = Mock(spec_set=_MinPaymentFormula)
        p1.calculate.side_effect = se_minpay_A
        s1 = CCStatement(
            i1, Decimal('10.00'), p1, b1,
            end_balance=Decimal('10.00'), interest_amt=Decimal('1.00')
        )
        p2 = Mock(spec_set=_MinPaymentFormula)
        p2.calculate.side_effect = se_minpay_B
        s2 = CCStatement(
            i1, Decimal('20.00'), p2, b1,
            end_balance=Decimal('20.00'), interest_amt=Decimal('2.00')
        )
        s3 = CCStatement(
            i1, Decimal('-1.00'), p2, b1,
            end_balance=Decimal('-1.00'), interest_amt=Decimal('2.00')
        )
        meth = MinPaymentMethod()
        res = calculate_payoffs(meth, [s1, s2, s3])
        assert res == [
            (8, Decimal('24.00')),
            (1, Decimal('20.00')),
            (0, Decimal('0.0'))
        ]


class TestModuleConstants(object):

    def test_interest(self):
        assert INTEREST_CALCULATION_NAMES == {
            'AdbCompoundedDaily': {
                'description': AdbCompoundedDaily.description,
                'doc': AdbCompoundedDaily.__doc__.strip(),
                'cls': AdbCompoundedDaily
            },
            'SimpleInterest': {
                'description': SimpleInterest.description,
                'doc': SimpleInterest.__doc__.strip(),
                'cls': SimpleInterest
            }
        }

    def test_min_payment(self):
        assert MIN_PAYMENT_FORMULA_NAMES == {
            'MinPaymentAmEx': {
                'description': MinPaymentAmEx.description,
                'doc': MinPaymentAmEx.__doc__.strip(),
                'cls': MinPaymentAmEx
            },
            'MinPaymentDiscover': {
                'description': MinPaymentDiscover.description,
                'doc': MinPaymentDiscover.__doc__.strip(),
                'cls': MinPaymentDiscover
            },
            'MinPaymentCiti': {
                'description': MinPaymentCiti.description,
                'doc': MinPaymentCiti.__doc__.strip(),
                'cls': MinPaymentCiti
            }
        }

    def test_payoff(self):
        assert PAYOFF_METHOD_NAMES == {
            'MinPaymentMethod': {
                'description': MinPaymentMethod.description,
                'doc': MinPaymentMethod.__doc__.strip(),
                'cls': MinPaymentMethod
            },
            'FixedPaymentMethod': {
                'description': FixedPaymentMethod.description,
                'doc': FixedPaymentMethod.__doc__.strip(),
                'cls': FixedPaymentMethod
            },
            'HighestBalanceFirstMethod': {
                'description': HighestBalanceFirstMethod.description,
                'doc': HighestBalanceFirstMethod.__doc__.strip(),
                'cls': HighestBalanceFirstMethod
            },
            'LowestBalanceFirstMethod': {
                'description': LowestBalanceFirstMethod.description,
                'doc': LowestBalanceFirstMethod.__doc__.strip(),
                'cls': LowestBalanceFirstMethod
            },
            'LowestInterestRateFirstMethod': {
                'description': LowestInterestRateFirstMethod.description,
                'doc': LowestInterestRateFirstMethod.__doc__.strip(),
                'cls': LowestInterestRateFirstMethod
            },
            'HighestInterestRateFirstMethod': {
                'description': HighestInterestRateFirstMethod.description,
                'doc': HighestInterestRateFirstMethod.__doc__.strip(),
                'cls': HighestInterestRateFirstMethod
            }
        }


class TestAcceptanceData(object):

    def setup(self):
        self.stmt_cc_one = CCStatement(
            AdbCompoundedDaily(Decimal('0.0100')),
            Decimal('952.06'),
            MinPaymentAmEx(),
            _BillingPeriod(date(2017, 7, 31)),
            transactions={},
            end_balance=Decimal('952.06'),
            interest_amt=Decimal('16.25')
        )
        self.stmt_cc_two = CCStatement(
            AdbCompoundedDaily(Decimal('0.1000')),
            Decimal('5498.65'),
            MinPaymentDiscover(),
            _BillingPeriod(date(2017, 7, 31)),
            transactions={},
            end_balance=Decimal('5498.65'),
            interest_amt=Decimal('28.53')
        )

    def test_cc_one_minimum(self):
        assert self.stmt_cc_one.minimum_payment == Decimal('35')

    def test_cc_two_minimum(self):
        assert self.stmt_cc_two.minimum_payment == Decimal('109.9730')

    def test_cc_one_pay_min(self):
        res = calculate_payoffs(
            MinPaymentMethod(),
            [self.stmt_cc_one]
        )
        assert res == [(28, Decimal('962.9988625702411101133192793'))]

    def test_cc_two_pay_min(self):
        res = calculate_payoffs(
            MinPaymentMethod(),
            [self.stmt_cc_two]
        )
        assert res == [(162, Decimal('8664.861877369277471400473622'))]

    def test_cc_combined_minimum(self):
        assert (
            self.stmt_cc_one.minimum_payment + self.stmt_cc_two.minimum_payment
        ) == Decimal('144.9730')

    def test_combined_pay_min(self):
        res = calculate_payoffs(
            MinPaymentMethod(),
            [self.stmt_cc_one, self.stmt_cc_two]
        )
        assert res == [
            (28, Decimal('962.9988625702411101133192793')),
            (162, Decimal('8664.861877369277471400473622'))
        ]

    def test_combined_pay_lowest_ir(self):
        res = calculate_payoffs(
            LowestInterestRateFirstMethod(Decimal('144.9730')),
            [self.stmt_cc_one, self.stmt_cc_two]
        )
        assert res == [
            (21, Decimal('960.9178327498502165965138131')),
            (56, Decimal('6988.237124948955044765363412'))
        ]

    def test_combined_pay_lowest_bal(self):
        res = calculate_payoffs(
            LowestBalanceFirstMethod(Decimal('144.9730')),
            [self.stmt_cc_one, self.stmt_cc_two]
        )
        assert res == [
            (21, Decimal('960.9178327498502165965138131')),
            (56, Decimal('6988.237124948955044765363412'))
        ]

    def test_combined_pay_highest_ir(self):
        res = calculate_payoffs(
            HighestInterestRateFirstMethod(Decimal('144.9730')),
            [self.stmt_cc_one, self.stmt_cc_two]
        )
        assert res == [
            (28, Decimal('962.9988625702411101133192793')),
            (55, Decimal('6956.345228060182432444990377'))
        ]

    def test_combined_pay_highest_bal(self):
        res = calculate_payoffs(
            HighestBalanceFirstMethod(Decimal('144.9730')),
            [self.stmt_cc_one, self.stmt_cc_two]
        )
        assert res == [
            (28, Decimal('962.9988625702411101133192793')),
            (55, Decimal('6956.345228060182432444990377'))
        ]


class TestSimpleData(object):

    def setup(self):
        self.mpm = Mock(spec_set=MinPaymentAmEx)
        self.mpm.calculate.return_value = Decimal('200.00')
        self.stmt_cc_one = CCStatement(
            FixedInterest(Decimal('10.00')),
            Decimal('1000.00'),
            self.mpm,
            _BillingPeriod(date(2017, 7, 3)),
            transactions={},
            end_balance=Decimal('1010.00'),
            interest_amt=Decimal('10.00')
        )
        self.stmt_cc_two = CCStatement(
            FixedInterest(Decimal('40.00')),
            Decimal('2000.00'),
            self.mpm,
            _BillingPeriod(date(2017, 7, 14)),
            transactions={},
            end_balance=Decimal('2040.00'),
            interest_amt=Decimal('40.00')
        )
        self.mpm2 = Mock(spec_set=MinPaymentAmEx)
        self.mpm2.calculate.return_value = Decimal('500.00')
        self.stmt_cc_three = CCStatement(
            FixedInterest(Decimal('100.00')),
            Decimal('10000.00'),
            self.mpm2,
            _BillingPeriod(date(2017, 7, 7)),
            transactions={},
            end_balance=Decimal('10100.00'),
            interest_amt=Decimal('100.00')
        )

    def test_cc_one_minimum(self):
        assert self.stmt_cc_one.minimum_payment == Decimal('200.0')

    def test_cc_two_minimum(self):
        assert self.stmt_cc_two.minimum_payment == Decimal('200.0')

    def test_cc_three_minimum(self):
        assert self.stmt_cc_three.minimum_payment == Decimal('500.0')

    def test_cc_one_pay_min(self):
        res = calculate_payoffs(
            MinPaymentMethod(),
            [self.stmt_cc_one]
        )
        assert res == [(6, Decimal('1060.0'))]

    def test_cc_two_pay_min(self):
        res = calculate_payoffs(
            MinPaymentMethod(),
            [self.stmt_cc_two]
        )
        assert res == [(13, Decimal('2520.0'))]

    def test_cc_three_pay_min(self):
        res = calculate_payoffs(
            MinPaymentMethod(),
            [self.stmt_cc_three]
        )
        assert res == [(25, Decimal('12500.0'))]

    def test_combined_pay_min(self):
        res = calculate_payoffs(
            MinPaymentMethod(),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (6, Decimal('1060.0')),
            (13, Decimal('2520.0')),
            (25, Decimal('12500.0'))
        ]

    def test_lowest_balance_first(self):
        res = calculate_payoffs(
            LowestBalanceFirstMethod(Decimal('1000.0')),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (4, Decimal('1040.0')),
            (7, Decimal('2280.0')),
            (15, Decimal('11500.0'))
        ]

    def test_highest_balance_first(self):
        res = calculate_payoffs(
            HighestBalanceFirstMethod(Decimal('1000.0')),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (6, Decimal('1060.0')),
            (13, Decimal('2520.0')),
            (16, Decimal('11600.0'))
        ]

    def test_lowest_interest_rate_first(self):
        res = calculate_payoffs(
            LowestInterestRateFirstMethod(Decimal('1000.0')),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (4, Decimal('1040.0')),
            (7, Decimal('2280.0')),
            (15, Decimal('11500.0'))
        ]

    def test_highest_interest_rate_first(self):
        res = calculate_payoffs(
            HighestInterestRateFirstMethod(Decimal('1000.0')),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (6, Decimal('1060.0')),
            (13, Decimal('2520.0')),
            (16, Decimal('11600.0'))
        ]

    def test_lowest_balance_first_with_increases(self):
        res = calculate_payoffs(
            LowestBalanceFirstMethod(
                Decimal('1000.0'),
                increases={
                    date(2017, 8, 1): Decimal('1200.0'),  # bill 3
                    date(2018, 2, 1): Decimal('1500.0'),  # bill 9
                }
            ),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (3, Decimal('1030.0')),
            (6, Decimal('2240.0')),
            (12, Decimal('11200.0'))
        ]

    def test_highest_balance_first_with_increases(self):
        res = calculate_payoffs(
            HighestBalanceFirstMethod(
                Decimal('1000.0'),
                increases={
                    date(2017, 8, 1): Decimal('1200.0'),  # bill 3
                    date(2018, 2, 1): Decimal('1500.0'),  # bill 9
                }
            ),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (6, Decimal('1060.0')),
            (13, Decimal('2520.0')),
            (12, Decimal('11200.0'))
        ]

    def test_lowest_balance_first_with_onetimes(self):
        res = calculate_payoffs(
            LowestBalanceFirstMethod(
                Decimal('1000.0'),
                onetimes={
                    date(2017, 7, 1): Decimal('500.0'),  # bill 2
                    date(2017, 10, 1): Decimal('1000.0'),  # bill 5
                    date(2018, 4, 1): Decimal('3000.0')  # bill 11
                }
            ),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (2, Decimal('1020.0')),
            (5, Decimal('2200.0')),
            (11, Decimal('11100.0'))
        ]

    def test_highest_balance_first_with_onetimes(self):
        res = calculate_payoffs(
            HighestBalanceFirstMethod(
                Decimal('1000.0'),
                onetimes={
                    date(2017, 7, 1): Decimal('500.0'),  # bill 2
                    date(2017, 10, 1): Decimal('1000.0'),  # bill 5
                    date(2018, 4, 1): Decimal('3000.0')  # bill 11
                }
            ),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (6, Decimal('1060.0')),
            (12, Decimal('2480.0')),
            (11, Decimal('11100.0'))
        ]

    def test_lowest_balance_first_with_increases_and_onetimes(self):
        res = calculate_payoffs(
            LowestBalanceFirstMethod(
                Decimal('1000.0'),
                onetimes={
                    date(2017, 6, 1): Decimal('200.0'),  # bill 1
                    date(2017, 9, 1): Decimal('1000.0'),  # bill 4
                    date(2018, 4, 1): Decimal('1500.0')  # bill 11
                },
                increases={
                    date(2017, 8, 1): Decimal('1200.0'),  # bill 3
                    date(2018, 2, 1): Decimal('1500.0'),  # bill 9
                }
            ),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (3, Decimal('1030.0')),
            (4, Decimal('2160.0')),
            (11, Decimal('11100.0'))
        ]

    def test_highest_balance_first_with_increases_and_onetimes(self):
        res = calculate_payoffs(
            HighestBalanceFirstMethod(
                Decimal('1000.0'),
                onetimes={
                    date(2017, 10, 1): Decimal('7000.0'),  # bill 5
                    date(2017, 11, 1): Decimal('240.0'),  # bill 6
                },
                increases={
                    date(2017, 8, 1): Decimal('1200.0'),  # bill 3
                    date(2018, 2, 1): Decimal('1500.0'),  # bill 9
                }
            ),
            [self.stmt_cc_one, self.stmt_cc_two, self.stmt_cc_three]
        )
        assert res == [
            (6, Decimal('1060.0')),
            (6, Decimal('2240.0')),
            (5, Decimal('10500.0'))
        ]


class InterestData(object):
    """
    Some example data for interest and payoff calculations.
    """

    citi = [
        {
            'start': date(2016, 12, 24),
            'end': date(2017, 1, 24),
            'apr': Decimal("0.1574"),
            'start_bal': Decimal("5542.78"),
            'bal_subj_to_int': Decimal("5551.84"),
            'transactions': {
                date(2017, 1, 20): -180,
            },
            'interest_amt': Decimal("76.61"),
            'end_balance': Decimal("5439.39"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("130.61"), 19, 11650],
                [191, 3, 6876]
            ]
        },
        {
            'start': date(2017, 1, 25),
            'end': date(2017, 2, 23),
            'apr': Decimal("0.1574"),
            'start_bal': Decimal("5439.39"),
            'bal_subj_to_int': Decimal("5499.95"),
            'transactions': {
                date(2017, 2, 17): -140,
                date(2017, 1, 25): Decimal("58.75")
            },
            'interest_amt': Decimal("71.15"),
            'end_balance': Decimal("5429.29"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("125.15"), 19, 11628],
                [190, 3, 6840]
            ]
        },
        {
            'start': date(2017, 2, 24),
            'end': date(2017, 3, 23),
            'apr': Decimal("0.1599"),
            'start_bal': Decimal("5429.29"),
            'bal_subj_to_int': Decimal("5419.22"),
            'transactions': {
                date(2017, 3, 17): -169,
            },
            'interest_amt': Decimal("66.48"),
            'end_balance': Decimal("5326.77"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("119.48"), 19, 11506],
                [187, 3, 6732]
            ]
        },
        {
            'start': date(2017, 3, 24),
            'end': date(2017, 4, 25),
            'apr': Decimal("0.1599"),
            'start_bal': Decimal("5326.77"),
            'bal_subj_to_int': Decimal("5320.73"),
            'transactions': {
                date(2017, 4, 14): Decimal("-119.48"),
            },
            'interest_amt': Decimal("76.92"),
            'end_balance': Decimal("5284.21"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("128.92"), 19, 11393],
                [186, 3, 6696]
            ]
        },
        {
            'start': date(2017, 4, 26),
            'end': date(2017, 5, 23),
            'apr': Decimal("0.1599"),
            'start_bal': Decimal("5284.21"),
            'bal_subj_to_int': Decimal("5260.20"),
            'transactions': {
                date(2017, 5, 12): Decimal("-128.92"),
            },
            'interest_amt': Decimal("64.53"),
            'end_balance': Decimal("5219.82"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("116.53"), 19, 11259],
                [183, 3, 6588]
            ]
        },
        {
            'start': date(2017, 5, 24),
            'end': date(2017, 6, 23),
            'apr': Decimal("0.1624"),
            'start_bal': Decimal("5219.82"),
            'bal_subj_to_int': Decimal("5192.23"),
            'transactions': {
                date(2017, 6, 9): Decimal("-128.92"),
            },
            'interest_amt': Decimal("71.61"),
            'end_balance': Decimal("5162.51"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("122.61"), 19, 11209],
                [182, 3, 6552]
            ]
        },
        {
            'start': date(2017, 6, 24),
            'end': date(2017, 7, 25),
            'apr': Decimal("0.1624"),
            'start_bal': Decimal("5162.51"),
            'bal_subj_to_int': Decimal("5178.1"),
            'transactions': {
                date(2017, 7, 21): -129,
            },
            'interest_amt': Decimal("73.72"),
            'end_balance': Decimal("5107.23"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("124.72"), 18, 11079],
                [180, 3, 6480]
            ]
        },
        {
            'start': date(2016, 7, 26),
            'end': date(2016, 8, 23),
            'apr': Decimal("0.1549"),
            'start_bal': Decimal("5450.1"),
            'bal_subj_to_int': Decimal("5490.59"),
            'transactions': {
                date(2016, 8, 19): Decimal("-128.64"),
                date(2016, 8, 1): Decimal("13.89"),
                date(2016, 8, 3): (Decimal("18.89") + Decimal("7.39"))
            },
            'interest_amt': Decimal("67.58"),
            'end_balance': Decimal("5429.21"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("121.58"), 19, 11529],
                [190, 3, 6840]
            ]
        },
        {
            'start': date(2016, 8, 24),
            'end': date(2016, 9, 23),
            'apr': Decimal("0.1549"),
            'start_bal': Decimal("5429.21"),
            'bal_subj_to_int': Decimal("5469.66"),
            'transactions': {
                date(2016, 9, 16): -200,
                date(2016, 8, 27): Decimal("59.8"),
                date(2016, 9, 9): Decimal("6.41")
            },
            'interest_amt': Decimal("71.96"),
            'end_balance': Decimal("5367.38"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("124.96"), 19, 11380],
                [187, 3, 6732]
            ]
        },
        {
            'start': date(2016, 9, 24),
            'end': date(2016, 10, 25),
            'apr': Decimal("0.1549"),
            'start_bal': Decimal("5367.38"),
            'bal_subj_to_int': Decimal("5423.19"),
            'transactions': {
                date(2016, 10, 14): -180,
                date(2016, 9, 27): Decimal("21.9"),
                date(2016, 10, 6): Decimal("76.93"),
                date(2016, 10, 7): Decimal("33.16")
            },
            'interest_amt': Decimal("73.65"),
            'end_balance': Decimal("5393.02"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("126.65"), 19, 11440],
                [188, 3, 6768]
            ]
        },
        {
            'start': date(2016, 10, 26),
            'end': date(2016, 11, 23),
            'apr': Decimal("0.1549"),
            'start_bal': Decimal("5393.02"),
            'bal_subj_to_int': Decimal("5422.18"),
            'transactions': {
                date(2016, 11, 10): -180,
                date(2016, 10, 26): Decimal("17.52"),
                date(2016, 11, 4): Decimal("85.57"),
                date(2016, 11, 18): 35
            },
            'interest_amt': Decimal("66.73"),
            'end_balance': Decimal("5417.84"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("120.73"), 19, 11500],
                [189, 3, 6804]
            ]
        },
        {
            'start': date(2016, 11, 24),
            'end': date(2016, 12, 23),
            'apr': Decimal("0.1574"),
            'start_bal': Decimal("5417.84"),
            'bal_subj_to_int': Decimal("5464.87"),
            'transactions': {
                date(2016, 12, 9): -160,
                date(2016, 11, 24): Decimal("43.31"),
                date(2016, 12, 11): 44,
                date(2016, 12, 14): Decimal("82.68"),
                date(2016, 12, 22): Decimal("44.26")
            },
            'interest_amt': Decimal("70.69"),
            'end_balance': Decimal("5542.78"),
            'payoffs': [
                # amt, time, total_paid
                [Decimal("168.47"), 19, 11840],
                [194, 3, 6984]
            ]
        }
    ]

    amex = [
        {
            'start': date(2017, 7, 28) - timedelta(days=30),
            'end': date(2017, 7, 28),
            'apr': Decimal("0.1824"),
            'start_bal': Decimal("1856.23"),
            'bal_subj_to_int': Decimal("1821.35"),
            'transactions': {
                date(2017, 7, 21): Decimal("-189.0"),
            },
            'interest_amt': Decimal("28.23"),
            'end_balance': Decimal("1695.46"),
            'payoffs': [
                # amt, time, total_paid
                [45, 7, 2924],
                [62, 3, 2216]
            ]
        },
        {
            'start': date(2017, 4, 27) - timedelta(days=29),
            'end': date(2017, 4, 27),
            'apr': Decimal("0.1799"),
            'start_bal': Decimal("1917.31"),
            'bal_subj_to_int': Decimal("1908.13"),
            'transactions': {
                date(2017, 4, 14): Decimal("-49.0"),
            },
            'interest_amt': Decimal("28.22"),
            'end_balance': Decimal("1896.53"),
            'payoffs': [
                # amt, time, total_paid
                [47, 8, 3403],
                [69, 3, 2471]
            ]
        },
        {
            'start': date(2017, 2, 24) - timedelta(days=27),
            'end': date(2017, 2, 24),
            'apr': Decimal("0.1774"),
            'start_bal': Decimal("1977.06"),
            'bal_subj_to_int': Decimal("1969.76"),
            'transactions': {
                date(2017, 2, 17): Decimal("-71.0"),
            },
            'interest_amt': Decimal("26.8"),
            'end_balance': Decimal("1932.86"),
            'payoffs': [
                # amt, time, total_paid
                [46, 8, 3466],
                [70, 3, 2509]
            ]
        },
        {
            'start': date(2017, 6, 27) - timedelta(days=29),
            'end': date(2017, 6, 27),
            'apr': Decimal("0.1824"),
            'start_bal': Decimal("1878.33"),
            'bal_subj_to_int': Decimal("1860.2"),
            'transactions': {
                date(2017, 6, 9): Decimal("-50.0"),
            },
            'interest_amt': Decimal("27.9"),
            'end_balance': Decimal("1856.23"),
            'payoffs': [
                # amt, time, total_paid
                [46, 8, 3334],
                [67, 3, 2427]
            ]
        },
        {
            'start': date(2017, 3, 28) - timedelta(days=31),
            'end': date(2017, 3, 28),
            'apr': Decimal("0.1799"),
            'start_bal': Decimal("1932.86"),
            'bal_subj_to_int': Decimal("1930.4"),
            'transactions': {
                date(2017, 3, 17): Decimal("-46.0"),
            },
            'interest_amt': Decimal("30.45"),
            'end_balance': Decimal("1917.31"),
            'payoffs': [
                # amt, time, total_paid
                [49, 8, 3452],
                [69, 3, 2498]
            ]
        },
        {
            'start': date(2017, 5, 28) - timedelta(days=30),
            'end': date(2017, 5, 28),
            'apr': Decimal("0.1799"),
            'start_bal': Decimal("1896.53"),
            'bal_subj_to_int': Decimal("1884.74"),
            'transactions': {
                date(2017, 5, 12): Decimal("-47.0"),
            },
            'interest_amt': Decimal("28.8"),
            'end_balance': Decimal("1878.33"),
            'payoffs': [
                # amt, time, total_paid
                [47, 8, 3357],
                [68, 3, 2447]
            ]
        }
    ]

    discover = [
        {
            'start': date(2016, 12, 19),
            'end': date(2017, 1, 18),
            'apr': Decimal("0.1949"),
            'start_bal': Decimal("7160.59"),
            'bal_subj_to_int': Decimal("7149.14"),
            'transactions': {
                date(2017, 1, 6): -150,
                date(2016, 12, 29): Decimal("9.98"),
                date(2017, 1, 16): Decimal("6.86"),
                date(2017, 1, 3): 10,
                date(2017, 1, 17): Decimal("67.5")
            },
            'interest_amt': Decimal("118.53"),
            'end_balance': Decimal("7212.01"),
            'payoffs': [
                # amt, time, total_paid
                [145, 28, 26912],
                [266, 3, 9582]
            ]
        },
        {
            'start': date(2017, 1, 19),
            'end': date(2017, 2, 18),
            'apr': Decimal("0.1949"),
            'start_bal': Decimal("7236.56"),
            'bal_subj_to_int': Decimal("7212.01"),
            'transactions': {
                date(2017, 2, 3): Decimal("-184.95"),
                date(2017, 2, 7): Decimal("21.12"),
                date(2017, 1, 17): Decimal("53.7")
            },
            'interest_amt': Decimal("119.8"),
            'end_balance': Decimal("7221.68"),
            'payoffs': [
                # amt, time, total_paid
                [145, 28, 26952],
                [267, 3, 9595]
            ]
        },
        {
            'start': date(2017, 2, 19),
            'end': date(2017, 3, 18),
            'apr': Decimal("0.1949"),
            'start_bal': Decimal("7190.79"),
            'bal_subj_to_int': Decimal("7221.68"),
            'transactions': {
                date(2017, 3, 3): Decimal("-145.0"),
            },
            'interest_amt': Decimal("107.52"),
            'end_balance': Decimal("7184.2"),
            'payoffs': [
                # amt, time, total_paid
                [144, 28, 26800],
                [265, 3, 9588]
            ]
        },
        {
            'start': date(2017, 3, 19),
            'end': date(2017, 4, 18),
            'apr': Decimal("0.1974"),
            'start_bal': Decimal("7154.09"),
            'bal_subj_to_int': Decimal("7184.2"),
            'transactions': {
                date(2017, 3, 31): Decimal("-144.0"),
            },
            'interest_amt': Decimal("119.94"),
            'end_balance': Decimal("7160.14"),
            'payoffs': [
                # amt, time, total_paid
                [144, 28, 27291],
                [265, 3, 9545]
            ]
        },
        {
            'start': date(2017, 4, 19),
            'end': date(2017, 5, 18),
            'apr': Decimal("0.1974"),
            'start_bal': Decimal("7182.91"),
            'bal_subj_to_int': Decimal("7160.14"),
            'transactions': {
                date(2017, 5, 12): Decimal("-144.0"),
            },
            'interest_amt': Decimal("116.54"),
            'end_balance': Decimal("7132.68"),
            'payoffs': [
                # amt, time, total_paid
                [143, 28, 27144],
                [264, 3, 9509]
            ]
        },
        {
            'start': date(2017, 5, 19),
            'end': date(2017, 6, 18),
            'apr': Decimal("0.1974"),
            'start_bal': Decimal("7144.28"),
            'bal_subj_to_int': Decimal("7132.68"),
            'transactions': {
                date(2017, 6, 9): Decimal("-144.0"),
            },
            'interest_amt': Decimal("119.77"),
            'end_balance': Decimal("7108.45"),
            'payoffs': [
                # amt, time, total_paid
                [143, 28, 26991],
                [263, 3, 9476]
            ]
        },
        {
            'start': date(2017, 6, 19),
            'end': date(2017, 7, 18),
            'apr': Decimal("0.1999"),
            'start_bal': Decimal("7107.42"),
            'bal_subj_to_int': Decimal("7108.45"),
            'transactions': {
                date(2017, 7, 7): Decimal("-144.0"),
            },
            'interest_amt': Decimal("116.78"),
            'end_balance': Decimal("7081.23"),
            'payoffs': [
                # amt, time, total_paid
                [142, 28, 27398],
                [263, 3, 9472]
            ]
        }
    ]


@pytest.mark.skipif(PY34PLUS is False,
                    reason='py3.4+ only due to Decimal rounding')
class TestDataAmEx(object):

    def test_calculate(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentAmEx()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = deepcopy(data['start'])
        res = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions']
        )
        assert res.start_date == data['start']
        assert res.end_date == data['end']
        assert pctdiff(
            round(res.principal, 2), data['end_balance']) < Decimal('0.01')
        assert pctdiff(
            round(res.interest, 2), data['interest_amt']) < Decimal('0.01')

    def test_calculate_min_payment(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentAmEx()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = deepcopy(data['start'])
        res = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        assert res.start_date == data['start']
        assert res.end_date == data['end']
        assert int(res.minimum_payment) == data['payoffs'][0][0]

    def test_calculate_payoff_min(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentAmEx()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = deepcopy(data['start'])
        stmt = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        res = calculate_payoffs(
            MinPaymentMethod(),
            [stmt]
        )
        if data['end'] == date(2017, 6, 27):
            # difference based on our estimated billing periods
            data['payoffs'][0][1] = 7
        assert stmt.start_date == data['start']
        assert stmt.end_date == data['end']
        assert int(round(res[0][0]/12)) == data['payoffs'][0][1]
        assert pctdiff(res[0][1], data['payoffs'][0][2]) < Decimal('0.03')

    def test_calculate_payoff_recommended(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentAmEx()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = deepcopy(data['start'])
        stmt = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        res = calculate_payoffs(
            FixedPaymentMethod(data['payoffs'][1][0]),
            [stmt]
        )
        assert stmt.start_date == data['start']
        assert stmt.end_date == data['end']
        assert int(round(res[0][0]/12)) == data['payoffs'][1][1]
        assert pctdiff(res[0][1], data['payoffs'][1][2]) < Decimal('0.03')


@pytest.mark.skipif(PY34PLUS is False,
                    reason='py3.4+ only due to Decimal rounding')
class TestDataCiti(object):

    def test_calculate(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentCiti()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = data['start']
        res = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions']
        )
        assert res.start_date == data['start']
        assert res.end_date == data['end']
        assert pctdiff(
            round(res.principal, 2), data['end_balance']) < Decimal('0.01')
        assert pctdiff(
            round(res.interest, 2), data['interest_amt']) < Decimal('0.01')

    def test_calculate_min_payment(self, data):
        if data['end'] == date(2016, 12, 23):
            pytest.skip("Strange minimum payment; outliar.")
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentCiti()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = data['start']
        res = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        assert res.start_date == data['start']
        assert res.end_date == data['end']
        assert pctdiff(
            res.minimum_payment, data['payoffs'][0][0]
        ) < Decimal('0.01')

    def test_calculate_payoff_min(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentCiti()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = data['start']
        stmt = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        res = calculate_payoffs(
            MinPaymentMethod(),
            [stmt]
        )
        assert stmt.start_date == data['start']
        assert stmt.end_date == data['end']
        if data['end'] == date(2017, 7, 25):
            pytest.skip('Strange data.')
        assert ceil(res[0][0]/12) == data['payoffs'][0][1]
        assert pctdiff(res[0][1], data['payoffs'][0][2]) < Decimal('0.03')

    def test_calculate_payoff_recommended(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentCiti()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = data['start']
        stmt = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        res = calculate_payoffs(
            FixedPaymentMethod(data['payoffs'][1][0]),
            [stmt]
        )
        assert stmt.start_date == data['start']
        assert stmt.end_date == data['end']
        assert int(round(res[0][0]/12)) == data['payoffs'][1][1]
        assert pctdiff(res[0][1], data['payoffs'][1][2]) < Decimal('0.03')


@pytest.mark.skipif(PY34PLUS is False,
                    reason='py3.4+ only due to Decimal rounding')
class TestDataDiscover(object):

    def test_calculate(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentDiscover()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = data['start']
        res = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions']
        )
        assert res.start_date == data['start']
        assert res.end_date == data['end']
        assert pctdiff(
            round(res.principal, 2), data['end_balance']) < Decimal('0.01')
        assert pctdiff(
            round(res.interest, 2), data['interest_amt']) < Decimal('0.01')

    def test_calculate_min_payment(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentDiscover()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = data['start']
        res = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        assert res.start_date == data['start']
        assert res.end_date == data['end']
        assert pctdiff(
            res.minimum_payment, data['payoffs'][0][0]
        ) < Decimal('0.01')

    def test_calculate_payoff_min(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentDiscover()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = data['start']
        stmt = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        res = calculate_payoffs(
            MinPaymentMethod(),
            [stmt]
        )
        # fix discover calculation
        data['payoffs'][0][1] -= 1
        assert stmt.start_date == data['start']
        assert stmt.end_date == data['end']
        assert int(round(res[0][0]/12)) == data['payoffs'][0][1]
        assert pctdiff(res[0][1], data['payoffs'][0][2]) < Decimal('0.04')

    def test_calculate_payoff_recommended(self, data):
        icls = AdbCompoundedDaily(data['apr'])
        mpc = MinPaymentDiscover()
        bp = _BillingPeriod(data['end'])
        bp._end_date = deepcopy(data['end'])
        bp._start_date = data['start']
        stmt = CCStatement(
            icls,
            data['start_bal'],
            mpc,
            bp,
            transactions=data['transactions'],
            end_balance=data['end_balance'],
            interest_amt=data['interest_amt']
        )
        res = calculate_payoffs(
            FixedPaymentMethod(data['payoffs'][1][0]),
            [stmt]
        )
        assert stmt.start_date == data['start']
        assert stmt.end_date == data['end']
        assert int(round(res[0][0]/12)) == data['payoffs'][1][1]
        assert pctdiff(res[0][1], data['payoffs'][1][2]) < Decimal('0.03')
