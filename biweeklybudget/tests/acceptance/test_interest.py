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
from datetime import date
from decimal import Decimal

from biweeklybudget.tests.acceptance_helpers import AcceptanceHelper
from biweeklybudget.interest import (
    InterestHelper, CCStatement, _BillingPeriod, AdbCompoundedDaily,
    MinPaymentAmEx, MinPaymentDiscover
)
from biweeklybudget.models import Account


@pytest.mark.acceptance
class TestInterestHelper(AcceptanceHelper):

    def test_init_accounts(self, testdb):
        cls = InterestHelper(testdb)
        assert cls._sess == testdb
        res = cls.accounts
        assert sorted(res.keys()) == [3, 4]
        assert isinstance(res[3], Account)
        assert res[3].id == 3
        assert isinstance(res[4], Account)
        assert res[4].id == 4

    def test_init_statements(self, testdb):
        cls = InterestHelper(testdb)
        res = cls._statements
        assert sorted(res.keys()) == [3, 4]
        s3 = res[3]
        assert isinstance(s3, CCStatement)
        assert isinstance(s3._billing_period, _BillingPeriod)
        assert s3._billing_period._end_date == date(2017, 7, 31)
        assert s3._billing_period._start_date == date(2017, 7, 1)
        assert isinstance(s3._interest_cls, AdbCompoundedDaily)
        assert s3._interest_cls.apr == Decimal('0.0100')
        assert isinstance(s3._min_pay_cls, MinPaymentAmEx)
        assert s3._orig_principal == Decimal('952.06')
        assert s3._min_pay is None
        assert s3._transactions == {}
        assert s3._principal == Decimal('952.06')
        s4 = res[4]
        assert isinstance(s4, CCStatement)
        assert isinstance(s4._billing_period, _BillingPeriod)
        assert s4._billing_period._end_date == date(2017, 7, 31)
        assert s4._billing_period._start_date == date(2017, 7, 1)
        assert isinstance(s4._interest_cls, AdbCompoundedDaily)
        assert s4._interest_cls.apr == Decimal('0.1000')
        assert isinstance(s4._min_pay_cls, MinPaymentDiscover)
        assert s4._orig_principal == Decimal('5498.65')
        assert s4._min_pay is None
        assert s4._transactions == {}
        assert s4._principal == Decimal('5498.65')

    def test_min_payments(self, testdb):
        cls = InterestHelper(testdb)
        assert cls.min_payments == {
            3: Decimal('35'),
            4: Decimal('109.9730')
        }

    def test_payoffs_simple(self, testdb):
        cls = InterestHelper(testdb)
        assert cls.calculate_payoffs() == {
            'HighestBalanceFirstMethod': {
                'description': 'Highest to Lowest Balance',
                'doc': 'Pay statements off from highest to lowest balance.',
                'results': {
                    3: {
                        'payoff_months': 28,
                        'total_interest': Decimal(
                            '10.9388625702411101133192793'
                        ),
                        'total_payments': Decimal(
                            '962.9988625702411101133192793'
                        )
                    },
                    4: {
                        'payoff_months': 55,
                        'total_interest': Decimal(
                            '1457.695228060182432444990377'
                        ),
                        'total_payments': Decimal(
                            '6956.345228060182432444990377'
                        )
                    }
                }
            },
            'HighestInterestRateFirstMethod': {
                'description': 'Highest to Lowest Interest Rate',
                'doc': 'Pay statements off from highest to lowest interest '
                       'rate.',
                'results': {
                    3: {
                        'payoff_months': 28,
                        'total_interest': Decimal(
                            '10.9388625702411101133192793'
                        ),
                        'total_payments': Decimal(
                            '962.9988625702411101133192793'
                        )
                    },
                    4: {
                        'payoff_months': 55,
                        'total_interest': Decimal(
                            '1457.695228060182432444990377'
                        ),
                        'total_payments': Decimal(
                            '6956.345228060182432444990377'
                        )
                    }
                }
            },
            'LowestBalanceFirstMethod': {
                'description': 'Lowest to Highest Balance (a.k.a. '
                               'Snowball Method)',
                'doc': 'Pay statements off from lowest to highest balance, '
                       'a.k.a. the "snowball"\n    method.',
                'results': {
                    3: {
                        'payoff_months': 21,
                        'total_interest': Decimal(
                            '8.8578327498502165965138131'
                        ),
                        'total_payments': Decimal(
                            '960.9178327498502165965138131'
                        )
                    },
                    4: {
                        'payoff_months': 56,
                        'total_interest': Decimal(
                            '1489.587124948955044765363412'
                        ),
                        'total_payments': Decimal(
                            '6988.237124948955044765363412'
                        )
                    }
                }
            },
            'LowestInterestRateFirstMethod': {
                'description': 'Lowest to Highest Interest Rate',
                'doc': 'Pay statements off from lowest to highest '
                       'interest rate.',
                'results': {
                    3: {
                        'payoff_months': 21,
                        'total_interest': Decimal(
                            '8.8578327498502165965138131'
                        ),
                        'total_payments': Decimal(
                            '960.9178327498502165965138131'
                        )
                    },
                    4: {
                        'payoff_months': 56,
                        'total_interest': Decimal(
                            '1489.587124948955044765363412'
                        ),
                        'total_payments': Decimal(
                            '6988.237124948955044765363412'
                        )
                    }
                }
            },
            'MinPaymentMethod': {
                'description': 'Minimum Payment Only',
                'doc': 'Pay only the minimum on each statement.',
                'results': {
                    3: {
                        'payoff_months': 28,
                        'total_interest': Decimal(
                            '10.9388625702411101133192793'
                        ),
                        'total_payments': Decimal(
                            '962.9988625702411101133192793'
                        )
                    },
                    4: {
                        'payoff_months': 162,
                        'total_interest': Decimal(
                            '3166.211877369277471400473622'
                        ),
                        'total_payments': Decimal(
                            '8664.861877369277471400473622'
                        )
                    }
                }
            }
        }
