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

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func

from biweeklybudget import settings
from biweeklybudget.biweeklypayperiod import BiweeklyPayPeriod
from biweeklybudget.models.transaction import Transaction
from biweeklybudget.utils import dtnow, fmt_currency

logger = logging.getLogger(__name__)

#: Maximum number of pay periods the payment panel lists individually. Six
#: biweekly periods is about three months -- enough to show a card carried
#: across a few cycles, few enough to fit in a modal. Everything older is
#: collapsed into a single summary row. This is a display cap, not a setting:
#: it never changes an amount. See GitHub issue #358.
CREDIT_PAYMENT_MAX_PERIODS = 6


def _as_date(value):
    """
    Return ``value`` as a :py:class:`datetime.date`.

    Date settings are not consistently typed: a settings module assigns them as
    ``date(...)`` literals, but
    :py:mod:`biweeklybudget.settings`'s environment-variable handling stores
    ``datetime.strptime(...)`` without calling ``.date()``, so the same setting
    is a :py:class:`datetime.datetime` when it comes from the environment.
    Comparing the two raises ``TypeError``, and
    :py:meth:`~.CreditPaymentAttribution._effective_begin_date` compares them.

    :param value: a date or datetime
    :type value: datetime.date or datetime.datetime
    :return: the equivalent date
    :rtype: datetime.date
    """
    if isinstance(value, datetime):
        return value.date()
    return value


class CreditPaymentAttribution(object):
    """
    Work out which pay periods' charges a payment toward a credit account
    settles, and whether the amount can possibly be right.

    A payment toward a credit account has zero budget impact regardless of what
    this class computes; see :py:attr:`~.Transaction.credit_payment_acct_id`.
    This is purely advisory: it shows the person entering a payment how the
    amount maps onto the charges the application has recorded, and warns when
    the amount exceeds every unpaid charge it knows about -- which reliably
    means charges are missing from the records, or were recorded against the
    wrong account. See GitHub issue #210.

    The algorithm:

    1. **Window.** Only transactions dated on or after the *effective* begin
       date for this account, and on or before the payment date, are
       considered. The effective begin date is derived per account by
       :py:meth:`~._effective_begin_date`: the later of
       :py:attr:`biweeklybudget.settings.CREDIT_PAYMENT_BEGIN_DATE` and the
       start of the pay period following the one holding the earliest payment
       designated toward this account. A lower bound is needed because payments
       recorded before this feature carry no
       :py:attr:`~.Transaction.credit_payment_acct_id` and so are never
       subtracted; without one a card's apparent unpaid total would drift
       upward without limit. Deriving it per account is what makes the bound
       actually bind for an install upgraded from before 2.0.0, whose whole
       history would otherwise be counted as unpaid; the setting remains the
       operator's floor. See GitHub issue #358. The upper bound exists because
       a payment cannot settle a charge that had not yet been made when it was
       paid.
    2. **Charges.** Every transaction recorded *against* the credit account
       inside the window, grouped by the pay period its date falls in, summed
       per period, oldest period first.
    3. **Prior payments.** Every transaction inside the window designated as a
       payment toward this account, excluding the one being edited, summed. The
       payment that anchors the window falls outside it by construction, so no
       payment is ever subtracted twice. The transaction being edited is
       excluded from deriving the window as well as from this sum, so that
       editing a payment shows the same panel as entering it did.
    4. **Consume** those prior payments against the per-period charge totals,
       oldest first, leaving each period's outstanding charges.
    5. **Attribute** this payment against those remainders, oldest first, until
       it is exhausted. Whatever is left over is the excess.
    6. **Cap** the result for display: the most recent
       :py:const:`~.CREDIT_PAYMENT_MAX_PERIODS` periods are kept in
       :py:attr:`~.periods` and everything older is collapsed into
       :py:attr:`~.rollup`, a summary carrying the collapsed periods' count,
       date range and summed amounts. This never changes an amount;
       :py:attr:`~.total_unpaid`, :py:attr:`~.total_attributed` and
       :py:attr:`~.excess` are computed over the whole window.

    Because both charges and prior payments are bounded the same way and
    consumed in date order, the result does not depend on the order in which
    payments were entered.

    :param db: active database session to use for queries
    :type db: sqlalchemy.orm.session.Session
    :param account: the credit Account being paid
    :type account: biweeklybudget.models.account.Account
    :param amount: the candidate payment amount
    :type amount: decimal.Decimal
    :param payment_date: the date of the payment
    :type payment_date: datetime.date
    :param exclude_txn_id: ID of the Transaction being edited, if any; it is
      excluded from the prior payments so that it is not counted against
      itself.
    :type exclude_txn_id: int
    :param payer_account_id: ID of the Account the payment is recorded against,
      if known; used only for the self-payment check.
    :type payer_account_id: int
    """

    def __init__(self, db, account, amount, payment_date,
                 exclude_txn_id=None, payer_account_id=None):
        self._db = db
        self.account = account
        self.amount = Decimal(amount)
        self.payment_date = payment_date
        self.exclude_txn_id = exclude_txn_id
        self.payer_account_id = payer_account_id
        self.configured_begin_date = _as_date(
            settings.CREDIT_PAYMENT_BEGIN_DATE
        )
        self.begin_date = self._effective_begin_date()
        self.periods = []
        self.rollup = None
        self.total_unpaid = Decimal('0.0')
        self.total_attributed = Decimal('0.0')
        self.excess = Decimal('0.0')
        self.pays_itself = (
            payer_account_id is not None and
            payer_account_id == account.id
        )
        self.warnings = []
        self._calculate()

    def _effective_begin_date(self):
        """
        Return the date from which this account's charges are counted: the
        later of :py:attr:`~.configured_begin_date` and the start of the pay
        period *following* the one holding the earliest payment designated
        toward this account.

        Payments made before this feature existed carry no
        :py:attr:`~.Transaction.credit_payment_acct_id`, so they are invisible
        to :py:meth:`~._prior_payments` and nothing ever settles the charges
        they paid. The first payment recorded toward a card is therefore taken
        as the point from which the application's own records are complete:
        everything charged up to and including that payment's pay period is
        treated as settled, by that payment together with the untracked ones
        before it.

        The bound sits *after* that payment's period rather than at its start
        so that the anchoring payment falls outside the window. Were it inside,
        it would reduce the card's unpaid charges twice -- once implicitly,
        because the charges it settled are excluded, and once explicitly, as a
        prior payment -- and the surplus would spill forward into later periods,
        understating unpaid charges on every payment thereafter. The cost is
        that charges made later in that period, after the payment, fall outside
        the window too.

        Only payments dated on or before :py:attr:`~.payment_date` are
        considered, so a payment recorded later cannot narrow the window for one
        entered earlier. :py:attr:`~.exclude_txn_id` is applied here as well as
        to :py:meth:`~._prior_payments`, so that the panel shown while editing a
        payment matches the one shown when it was entered: a payment being
        entered is not yet in the database and cannot anchor anything, so
        neither may the same payment once saved and reopened. Without this,
        reopening the payment that anchors a card's window would derive a bound
        after its own date, empty the window, and warn that the payment exceeds
        $0.00 of unpaid charges.

        An account with no designated payment at all gets
        :py:attr:`~.configured_begin_date` unchanged, which is the behaviour
        every account had before GitHub issue #358. The derived bound may fall
        after the payment date, leaving the window empty; the configured date is
        not reinstated in that case, as doing so would swing the panel back to
        the whole of recorded history.

        :return: the effective start of this account's charge window
        :rtype: datetime.date
        """
        q = self._db.query(func.min(Transaction.date)).filter(
            Transaction.credit_payment_acct_id.__eq__(self.account.id),
            Transaction.date.__le__(self.payment_date)
        )
        if self.exclude_txn_id is not None:
            q = q.filter(Transaction.id.__ne__(self.exclude_txn_id))
        first = q.scalar()
        if first is None:
            return self.configured_begin_date
        return max(
            self.configured_begin_date,
            BiweeklyPayPeriod.period_for_date(
                _as_date(first), self._db
            ).next.start_date
        )

    def _charges_by_period(self):
        """
        Return a list of dicts, one per pay period holding charges on this
        account inside the window, ordered oldest first. Each dict has keys
        ``period`` (:py:class:`~.BiweeklyPayPeriod`) and ``charges``
        (:py:class:`decimal.Decimal`).

        :return: per-period charge totals, oldest first
        :rtype: list
        """
        txns = self._db.query(Transaction).filter(
            Transaction.account_id.__eq__(self.account.id),
            Transaction.date.__ge__(self.begin_date),
            Transaction.date.__le__(self.payment_date)
        ).all()
        by_start = {}
        for t in txns:
            pp = BiweeklyPayPeriod.period_for_date(t.date, self._db)
            by_start.setdefault(pp.start_date, {
                'period': pp, 'charges': Decimal('0.0')
            })
            by_start[pp.start_date]['charges'] += t.actual_amount
        return [by_start[k] for k in sorted(by_start.keys())]

    def _prior_payments(self):
        """
        Return the sum of payments already recorded toward this account inside
        the window, excluding the transaction being edited.

        :return: sum of prior payments toward this account
        :rtype: decimal.Decimal
        """
        q = self._db.query(Transaction).filter(
            Transaction.credit_payment_acct_id.__eq__(self.account.id),
            Transaction.date.__ge__(self.begin_date),
            Transaction.date.__le__(self.payment_date)
        )
        if self.exclude_txn_id is not None:
            q = q.filter(Transaction.id.__ne__(self.exclude_txn_id))
        total = Decimal('0.0')
        for t in q.all():
            total += t.actual_amount
        return total

    @staticmethod
    def _consume(periods, amount, key):
        """
        Apply ``amount`` to each period's outstanding charges in order, oldest
        first, recording what each period absorbed under ``key``. Returns
        whatever is left over.

        :param periods: per-period dicts with an ``outstanding`` key
        :type periods: list
        :param amount: amount to apply
        :type amount: decimal.Decimal
        :param key: dict key under which to record what each period absorbed,
          or None to only reduce ``outstanding``
        :type key: str
        :return: the unapplied remainder of ``amount``
        :rtype: decimal.Decimal
        """
        remaining = amount
        for p in periods:
            if remaining <= Decimal('0.0'):
                break
            if p['outstanding'] <= Decimal('0.0'):
                continue
            applied = min(remaining, p['outstanding'])
            p['outstanding'] -= applied
            if key is not None:
                p[key] += applied
            remaining -= applied
        return remaining

    @staticmethod
    def _split_for_display(periods):
        """
        Split an oldest-first list of rendered period dicts into the most
        recent :py:const:`~.CREDIT_PAYMENT_MAX_PERIODS` of them and a summary
        of everything older.

        The cap exists so that the payment panel stays a modal-sized panel
        however wide the window turns out to be; before GitHub issue #358 a
        card with years of history produced a row per pay period. It is purely
        a display concern and never changes an amount: the collapsed periods'
        charges and attributions are carried in the summary, and
        :py:attr:`~.total_unpaid`, :py:attr:`~.total_attributed` and
        :py:attr:`~.excess` are computed over the whole window regardless.

        Because attribution is oldest-first, the periods a payment actually
        settles are the oldest ones -- exactly those this cap collapses -- so
        the summary carries its own ``attributed`` total rather than hiding
        where the payment went.

        :param periods: rendered period dicts, oldest first
        :type periods: list
        :return: 2-tuple of (periods to render individually, summary dict or
          None if nothing was collapsed)
        :rtype: tuple
        """
        if len(periods) <= CREDIT_PAYMENT_MAX_PERIODS:
            return periods, None
        older = periods[:-CREDIT_PAYMENT_MAX_PERIODS]
        return periods[-CREDIT_PAYMENT_MAX_PERIODS:], {
            'count': len(older),
            'start_date': older[0]['start_date'],
            'end_date': older[-1]['end_date'],
            'outstanding': sum(
                [p['outstanding'] for p in older], Decimal('0.0')
            ),
            'attributed': sum(
                [p['attributed'] for p in older], Decimal('0.0')
            )
        }

    def _calculate(self):
        today = dtnow().date()
        current = BiweeklyPayPeriod.period_for_date(today, self._db)
        periods = [
            {
                'period': x['period'],
                'outstanding': x['charges'],
                'attributed': Decimal('0.0')
            }
            for x in self._charges_by_period()
        ]
        # Settle what earlier payments already covered, oldest charges first.
        self._consume(periods, self._prior_payments(), None)
        self.total_unpaid = sum(
            [p['outstanding'] for p in periods], Decimal('0.0')
        )
        # Now attribute this payment against what is left.
        remaining = self._consume(periods, self.amount, 'attributed')
        self.excess = remaining
        self.total_attributed = self.amount - remaining
        self.periods, self.rollup = self._split_for_display([
            {
                'start_date': p['period'].start_date,
                'end_date': p['period'].end_date,
                'is_closed': p['period'].start_date < current.start_date,
                'outstanding': p['outstanding'] + p['attributed'],
                'attributed': p['attributed']
            }
            for p in periods
            if p['outstanding'] + p['attributed'] > Decimal('0.0')
        ])
        self._make_warnings()

    def _make_warnings(self):
        if self.excess > Decimal('0.0'):
            self.warnings.append(
                'This payment exceeds the %s of unpaid charges recorded for '
                '%s by %s. This usually means charges are missing from your '
                'records, or were recorded against the wrong account.' % (
                    fmt_currency(self.total_unpaid),
                    self.account.name,
                    fmt_currency(self.excess)
                )
            )
        if self.pays_itself:
            self.warnings.append(
                'This transaction is recorded against %s and is also marked '
                'as a payment toward %s. A payment should be recorded against '
                'the account the money came from.' % (
                    self.account.name, self.account.name
                )
            )

    @property
    def as_dict(self):
        """
        Return a dict representation of this attribution, for serialization to
        the Add/Edit Transaction modal.

        :return: dict describing this attribution
        :rtype: dict
        """
        return {
            'account_id': self.account.id,
            'account_name': self.account.name,
            'amount': self.amount,
            'begin_date': self.begin_date,
            'configured_begin_date': self.configured_begin_date,
            'periods': self.periods,
            'rollup': self.rollup,
            'total_unpaid': self.total_unpaid,
            'total_attributed': self.total_attributed,
            'excess': self.excess,
            'pays_itself': self.pays_itself,
            'warnings': self.warnings
        }
