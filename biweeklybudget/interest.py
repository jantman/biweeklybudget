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

import logging
import os
from datetime import timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)


class _InterestCalculation(object):

    #: Human-readable string name of the interest calculation type.
    description = None

    def __init__(self, apr):
        """
        :param apr: Annual Percentage Rate as a decimal
        :type apr: Decimal
        """
        self._apr = apr

    def __repr__(self):
        return '<%s(decimal.Decimal(\'%s\'))>' % (
            self.__class__.__name__, self.apr
        )

    @property
    def apr(self):
        return self._apr

    def calculate(self, principal, first_d, last_d, transactions={}):
        """
        Calculate compound interest for the specified principal.

        :param principal: balance at beginning of statement period
        :type principal: Decimal
        :param first_d: date of beginning of statement period
        :type first_d: datetime.date
        :param last_d: last date of statement period
        :type last_d: datetime.date
        :param transactions: dict of datetime.date to float amount adjust
          the balance by on the specified dates.
        :type transactions: dict
        :return: result of compound interest
        :rtype: InterestResult
        """
        raise NotImplementedError("Must implement in subclass")


class AdbCompoundedDaily(_InterestCalculation):
    """
    Average Daily Balance method, compounded daily (like American Express).
    """

    #: Human-readable string name of the interest calculation type.
    description = 'Average Daily Balance Compounded Daily (AmEx)'

    def calculate(self, principal, first_d, last_d, transactions={}):
        """
        Calculate compound interest for the specified principal.

        :param principal: balance at beginning of statement period
        :type principal: Decimal
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
        dpr = self._apr / Decimal(365.0)
        interest = Decimal(0.0)
        num_days = 0
        bal_total = Decimal(0.0)
        bal = principal

        d = first_d
        while d <= last_d:
            num_days += 1
            if d in transactions:
                bal += transactions[d]
            int_amt = bal * dpr
            interest += int_amt
            bal += int_amt
            bal_total += bal
            d += timedelta(days=1)
        adb = bal_total / Decimal(num_days)
        final = adb * self._apr * num_days / Decimal(365.0)
        bal += final * dpr
        return {
            'interest_paid': final,
            'end_balance': bal
        }


class _BillingPeriod(object):

    #: human-readable string description of the billing period type
    description = None

    def __init__(self):
        self._start_date = None
        self._end_date = None

    @property
    def start_date(self):
        return self._start_date

    @property
    def end_date(self):
        return self._end_date

    @property
    def next_period(self):
        """
        Return the next billing period after the specified billing period.

        :return: next billing period
        :rtype: _BillingPeriod
        """
        raise NotImplementedError()

    @property
    def payment_date(self):
        period_length = (self._end_date - self._start_date).days
        return self._start_date + timedelta(days=int(period_length / 2))


class BillingPeriodNumDays(_BillingPeriod):
    """
    Represents a billing period that is defined by a fixed number of days.
    """

    #: human-readable string description of the billing period type
    description = 'Number of Days'

    def __init__(self, end_date, num_days):
        """
        Construct a billing period that is defined by a number of days.

        :param end_date: end date of the billing period
        :type end_date: datetime.date
        :param num_days: number of days in the billing period
        :type num_days: int
        """
        super(BillingPeriodNumDays).__init__()
        self.num_days = num_days
        self._end_date = end_date
        self._start_date = end_date - timedelta(days=self.num_days)

    @property
    def next_period(self):
        """
        Return the next billing period after this one.

        :return: next billing period
        :rtype: BillingPeriodNumDays
        """
        ed = self.end_date + timedelta(days=(self.num_days + 1))
        return BillingPeriodNumDays(ed, self.num_days)

    @property
    def prev_period(self):
        """
        Return the previous billing period before this one.

        :return: previous billing period
        :rtype: BillingPeriodNumDays
        """
        return BillingPeriodNumDays(
            (self.start_date - timedelta(days=1)), self.num_days
        )


class _MinPaymentFormula(object):

    #: human-readable string description of the formula
    description = None

    def __init__(self):
        pass

    def calculate(self, balance, interest):
        """
        Calculate the minimum payment for a statement with the given balance
        and interest amount.

        :param balance: balance amount for the statement
        :type balance: decimal.Decimal
        :param interest: interest charged for the statement period
        :type interest: decimal.Decimal
        :return: minimum payment for the statement
        :rtype: decimal.Decimal
        """
        raise NotImplementedError()


class MinPaymentAmEx(_MinPaymentFormula):
    """
    Interest on last statement plus 1% of balance,
    or $35 if balance is less than $35.
    """

    #: human-readable string description of the formula
    description = 'AmEx - Greatest of Interest Plus 1% of Principal, or $35'

    def __init__(self):
        super(MinPaymentAmEx).__init__()

    def calculate(self, balance, interest):
        """
        Calculate the minimum payment for a statement with the given balance
        and interest amount.

        :param balance: balance amount for the statement
        :type balance: decimal.Decimal
        :param interest: interest charged for the statement period
        :type interest: decimal.Decimal
        :return: minimum payment for the statement
        :rtype: decimal.Decimal
        """
        amt = interest + (balance * Decimal('.01'))
        if amt < 35:
            amt = 35
        return amt


class MinPaymentDiscover(_MinPaymentFormula):
    """
    Greater of:
    - $35; or
    - 2% of the New Balance shown on your billing statement; or
    - $20, plus any of the following charges as shown on your billing statement:
     fees for any debt protection product that you enrolled in on or after
     2/1/2015; Interest Charges; and Late Fees.
    """

    #: human-readable string description of the formula
    description = 'Discover - Greatest of 2% of Principal, or $20 plus ' \
                  'Interest, or $35'

    def __init__(self):
        super(MinPaymentDiscover).__init__()

    def calculate(self, balance, interest):
        """
        Calculate the minimum payment for a statement with the given balance
        and interest amount.

        :param balance: balance amount for the statement
        :type balance: decimal.Decimal
        :param interest: interest charged for the statement period
        :type interest: decimal.Decimal
        :return: minimum payment for the statement
        :rtype: decimal.Decimal
        """
        options = [
            Decimal(35),
            balance * Decimal('0.02'),
            Decimal(20) + interest
        ]
        return max(options)


class MinPaymentCiti(_MinPaymentFormula):
    """
    Greater of:
    - $25;
    - The new balance, if it's less than $25;
    - 1 percent of the new balance, plus the current statement's interest
      charges or minimum interest charges, plus late fees;
    - 1.5% of the new balance, rounded to the nearest dollar amount.

    In all cases, add past fees and finance charges due, plus any amount in
    excess of credit line.
    """

    #: human-readable string description of the formula
    description = 'Citi - Greatest of 1.5% of Principal, or 1% of Principal ' \
                  'plus interest and fees, or $25, or Principal'

    def __init__(self):
        super(MinPaymentCiti).__init__()

    def calculate(self, balance, interest):
        """
        Calculate the minimum payment for a statement with the given balance
        and interest amount.

        :param balance: balance amount for the statement
        :type balance: decimal.Decimal
        :param interest: interest charged for the statement period
        :type interest: decimal.Decimal
        :return: minimum payment for the statement
        :rtype: decimal.Decimal
        """
        options = [
            25,
            (balance * Decimal('0.01')) + interest,
            round(balance * Decimal('0.015'))
        ]
        if balance < Decimal('25'):
            options.append(balance)
        return max(options)


class _PayoffMethod(object):
    """
    A payoff method for multiple cards; a method of figuring out how much to
    pay on each card, each month.
    """

    #: human-readable string name of the payoff method
    description = None

    def __init__(self, max_total_payment=None):
        """
        Initialize a payment method.

        :param max_total_payment: maximum total payment for all statements
        :type max_total_payment: decimal.Decimal
        """
        self._max_total = max_total_payment

    def find_payments(self, statements):
        """
        Given a list of statements, return a list of payment amounts to make
        on each of the statements.

        :param statements: statements to pay, list of :py:class:`~.CCStatement`
        :type statements: list
        :return: list of payment amounts to make, same order as ``statements``
        :rtype: list
        """
        raise NotImplementedError()


class MinPaymentMethod(_PayoffMethod):
    """
    Pay only the minimum on each statement.
    """

    description = 'Minimum Payment'

    def __init__(self, max_total_payment=None):
        """
        Initialize a payment method.

        :param max_total_payment: IGNORED.
        """
        super(MinPaymentMethod).__init__()

    def find_payments(self, statements):
        """
        Given a list of statements, return a list of payment amounts to make
        on each of the statements.

        :param statements: statements to pay, list of :py:class:`~.CCStatement`
        :type statements: list
        :return: list of payment amounts to make, same order as ``statements``
        :rtype: list
        """
        return [s.minimum_payment for s in statements]


class FixedPaymentMethod(_PayoffMethod):
    """
    TESTING ONLY - pay the same amount on every statement.
    """

    description = 'TESTING ONLY - Fixed Payment for All Statements'

    def __init__(self, pay_amount):
        """
        :param pay_amount: The amount to pay on each statement.
        :type pay_amount: decimal.Decimal
        """
        super(FixedPaymentMethod).__init__()
        self.amount = pay_amount

    def find_payments(self, statements):
        """
        Given a list of statements, return a list of payment amounts to make
        on each of the statements.

        :param statements: statements to pay, list of :py:class:`~.CCStatement`
        :type statements: list
        :return: list of payment amounts to make, same order as ``statements``
        :rtype: list
        """
        return [self.amount for _ in statements]


class LowestBalanceFirstMethod(_PayoffMethod):
    """
    Pay statements off from lowest to highest balance, a.k.a. the "snowball"
    method.
    """

    description = 'Lowest to Highest Balance (a.k.a. Snowball Method)'

    def __init__(self, max_total_payment):
        """
        :param max_total_payment: maximum total payment for all statements
        :type max_total_payment: decimal.Decimal
        """
        super(LowestBalanceFirstMethod).__init__()
        self._max_total = max_total_payment

    def find_payments(self, statements):
        """
        Given a list of statements, return a list of payment amounts to make
        on each of the statements.

        :param statements: statements to pay, list of :py:class:`~.CCStatement`
        :type statements: list
        :return: list of payment amounts to make, same order as ``statements``
        :rtype: list
        """
        min_sum = sum([s.minimum_payment for s in statements])
        if min_sum > self._max_total:
            raise TypeError(
                'ERROR: Max total payment of %s is less than sum of minimum '
                'payments (%s)' % (self._max_total, min_sum)
            )
        max_bal = Decimal('0.00')
        max_idx = None
        for idx, stmt in enumerate(statements):
            if stmt.principal > max_bal:
                max_bal = stmt.principal
                max_idx = idx
        res = [None for _ in statements]
        max_pay = self._max_total - (
            min_sum - statements[max_idx].minimum_payment
        )
        for idx, stmt in enumerate(statements):
            if idx == max_idx:
                res[idx] = max_pay
            else:
                res[idx] = statements[idx].minimum_payment
        return res


def calculate_payoffs(payment_method, statements):
    """
    Calculate the amount of time (in years) and total amount of money required
    to pay off the cards associated with the given list of statements. Return a
    list of (`float` number of years, `decimal.Decimal` amount paid) tuples for
    each item in `statements`.

    :param payment_method: method used for calculating payment amount to make
      on each statement; subclass of _PayoffMethod
    :type payment_method: _PayoffMethod
    :param statements: list of :py:class:`~.CCStatement` objects to pay off.
    :type statements: list
    :return: list of (`float` number of billing periods, `decimal.Decimal`
      amount paid) tuples for each item in `statements`
    :rtype: list
    """
    def unpaid(s): return [x for x in s.keys() if s[x]['done'] is False]
    payoffs = {}
    for idx, stmt in enumerate(statements):
        payoffs[stmt] = {
            'months': 0, 'amt': Decimal('0.0'), 'idx': idx, 'done': False
        }
    while len(unpaid(payoffs)) > 0:
        u = unpaid(payoffs)
        for stmt, p_amt in dict(
            zip(u, payment_method.find_payments(u))
        ).items():
            if stmt.principal <= Decimal('0'):
                payoffs[stmt]['done'] = True
                continue
            if stmt.principal <= p_amt:
                payoffs[stmt]['done'] = True
                payoffs[stmt]['months'] += 1  # increment months
                payoffs[stmt]['amt'] += stmt.principal
                continue
            payoffs[stmt]['months'] += 1  # increment months
            payoffs[stmt]['amt'] += p_amt
            new_s = stmt.pay(Decimal('-1') * p_amt)
            payoffs[new_s] = payoffs[stmt]
            del payoffs[stmt]
    return [
        (payoffs[s]['months'], payoffs[s]['amt'])
        for s in sorted(payoffs, key=lambda x: payoffs[x]['idx'])
    ]


class CCStatement(object):
    """
    Represent a credit card statement (one billing period).
    """

    def __init__(self, interest_cls, principal, min_payment_cls, billing_period,
                 transactions={}, end_balance=None, interest_amt=None):
        """
        Initialize a CCStatement. At least one of `start_date` and `end_date`
        must be specified.

        :param interest_cls: Interest calculation method
        :type interest_cls: _InterestCalculation
        :param principal: starting principal for this billing period
        :type principal: decimal.Decimal
        :param min_payment_cls: Minimum payment calculation method
        :type min_payment_cls: _MinPaymentFormula
        :param billing_period: Billing period
        :type billing_period: _BillingPeriod
        :param transactions: transactions applied during this statement. Dict
          of :py:class:`datetime.date` to :py:class:`decimal.Decimal`.
        :type transactions: dict
        :param end_balance: the ending balance of the statement, if known. If
          not specified, this value will be calculated.
        :type end_balance: decimal.Decimal
        :param interest_amt: The amount of interest charged this statement. If
          not specified, this value will be calculated.
        :type interest_amt: decimal.Decimal
        """
        if not isinstance(billing_period, _BillingPeriod):
            raise TypeError(
                'billing_period must be an instance of _BillingPeriod'
            )
        self._billing_period = billing_period
        if not isinstance(interest_cls, _InterestCalculation):
            raise TypeError(
                'interest_cls must be an instance of _InterestCalculation'
            )
        self._interest_cls = interest_cls
        if not isinstance(min_payment_cls, _MinPaymentFormula):
            raise TypeError(
                'min_payment_cls must be an instance of _MinPaymentFormula'
            )
        self._min_pay_cls = min_payment_cls
        self._orig_principal = principal
        self._min_pay = None
        self._transactions = transactions
        self._principal = end_balance
        self._interest_amt = interest_amt
        if end_balance is None or interest_amt is None:
            res = self._interest_cls.calculate(
                principal, self._billing_period.start_date,
                self._billing_period.end_date, self._transactions
            )
            if end_balance is None:
                self._principal = res['end_balance']
            if interest_amt is None:
                self._interest_amt = res['interest_paid']

    @property
    def principal(self):
        return self._principal

    @property
    def interest(self):
        return self._interest_amt

    @property
    def start_date(self):
        return self._billing_period.start_date

    @property
    def end_date(self):
        return self._billing_period.end_date

    @property
    def apr(self):
        return self._interest_cls.apr

    @property
    def minimum_payment(self):
        """
        Return the minimum payment for the next billing cycle.

        :return: minimum payment for the next billing cycle
        :rtype: decimal.Decimal
        """
        return self._min_pay_cls.calculate(
            self._principal, self._interest_amt
        )

    def next_with_transactions(self, transactions={}):
        """
        Return a new CCStatement reflecting the next billing period, with a
        payment of `amount` applied to it.

        :param transactions: dict of transactions, `datetime.date` to `Decimal`
        :type transactions: dict
        :return: next period statement, with transactions applied
        :rtype: CCStatement
        """
        return CCStatement(
            self._interest_cls,
            self._principal,
            self._min_pay_cls,
            self._billing_period.next_period,
            transactions=transactions
        )

    def pay(self, amount):
        """
        Return a new CCStatement reflecting the next billing period, with a
        payment of `amount` applied to it at the middle of the period.

        :param amount: amount to pay during the next statement period
        :type amount: decimal.Decimal
        :return: next period statement, with payment applied
        :rtype: CCStatement
        """
        return self.next_with_transactions({
            self._billing_period.next_period.payment_date: amount
        })


def subclass_dict(klass):
    d = {}
    for cls in klass.__subclasses__():
        d[cls.__name__] = {
            'description': cls.description,
            'doc': cls.__doc__.strip()
        }
    return d


#: Dict mapping interest calculation class names to their description and
#: docstring.
INTEREST_CALCULATION_NAMES = subclass_dict(_InterestCalculation)

#: Dict mapping billing period class names to their description and docstring.
BILLING_PERIOD_NAMES = subclass_dict(_BillingPeriod)

#: Dict mapping Minimum Payment Formula class names to their description and
#: docstring.
MIN_PAYMENT_FORMULA_NAMES = subclass_dict(_MinPaymentFormula)

#: Dict mapping Payoff Method class names to their description and docstring.
PAYOFF_METHOD_NAMES = subclass_dict(_PayoffMethod)