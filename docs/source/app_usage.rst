.. _app_usage:

Application Usage
=================

This documentation is a work in progress. I suppose if anyone other than me
ever tries to use this, I'll document it a bit more.

.. _app_usage.l10n:

Currency Formatting and Localization
------------------------------------

biweeklybudget supports configurable currency symbols and display/formatting,
controlled by the :py:attr:`~biweeklybudget.settings.LOCALE_NAME` and
:py:attr:`~biweeklybudget.settings.CURRENCY_CODE` settings. The former must
specify a `RFC 5646 / BCP 47 <https://www.rfc-editor.org/info/bcp47>`_ language tag
with a region identifier (i.e. "en_US", "en_GB", "de_DE", etc.). If it is not
set in the settings module or via a ``LOCALE_NAME`` environment variable, it
will be looked up from the ``LC_ALL``, ``LC_MONETARY``, or ``LANG`` environment
variables, in that order. It cannot be a "C" or "C." locale, as these do not
specify currency formatting. The latter, ``CURRENCY_CODE``, must be a valid
`ISO 4217 <https://en.wikipedia.org/wiki/ISO_4217>`_ Currency Code (i.e.
"USD", "EUR", etc.) and can also be set via a ``CURRENCY_CODE`` environment
variable.

.. _app_usage.currency_input:

Entering Currency Amounts
+++++++++++++++++++++++++

Every currency input in the web UI accepts common formatting; you do not need to
type a bare, unformatted number. Amounts are interpreted using the same
``LOCALE_NAME`` and ``CURRENCY_CODE`` settings used to *display* them, by
:py:func:`biweeklybudget.utils.parse_currency` on the server and its
counterpart ``parse_currency()`` in ``static/js/custom.js`` in the browser.

For a ``en_US`` / ``USD`` configuration, all of the following are accepted and
mean the same thing:

.. code-block:: none

    1234.56    1,234.56    1 234.56    $1,234.56    $ 1,234.56    1,234.56 $

Bare integers are accepted; ``123`` does not have to be written as ``123.0``.
A negative amount may be written with a leading minus sign or wrapped in
parentheses, so ``-1,234.56``, ``-$1,234.56`` and ``(1,234.56)`` are equivalent.
Leading and trailing whitespace is ignored.

Input that cannot be interpreted *unambiguously* is rejected with a
field-level validation error rather than being guessed at. In particular,
values whose digit grouping is not valid for the locale - such as ``10,00``,
``1,23,4.56``, ``1,234,`` or ``,123`` - are errors, **not** silently read as
``1000``, ``1234.56``, ``1234`` and ``123``. This is deliberate: for an
application that tracks real money, quietly turning a typo into a plausible
number is worse than refusing it. Likewise ``1.2.3``, ``1 2 3``, ``1e5`` and
non-numeric text are rejected.

Configuring a different ``LOCALE_NAME`` changes what is accepted as well as
what is displayed. With ``de_DE``, ``1.234,56`` is 1234.56 and ``1,234.56`` is
an error.

In addition, the Fuel Log functionality supports customization of the volume,
distance and fuel economy units via a set of settings (which can also be set
via environment variables):

* :py:attr:`biweeklybudget.settings.FUEL_VOLUME_UNIT` and :py:attr:`biweeklybudget.settings.FUEL_VOLUME_ABBREVIATION`
* :py:attr:`biweeklybudget.settings.DISTANCE_UNIT` and :py:attr:`biweeklybudget.settings.DISTANCE_UNIT_ABBREVIATION`
* :py:attr:`biweeklybudget.settings.FUEL_ECO_ABBREVIATION`

These settings only effect the display of monetary units in the user interface
and in log files. I haven't made any attempt at actual internationalization of
the text, mainly because as far as I know I'm the only person in the world using
this software. If anyone else uses it, I'll be happy to work to accomodate users
of other languages or localities.

The fuel level choices on the Fuel Log's Add Fuel Fill form can also be
configured, for vehicles whose fuel gauge isn't marked in tenths, via
:py:attr:`biweeklybudget.settings.FUEL_LEVELS` (for example
``FUEL_LEVELS="E:0,1/4:25,1/2:50,3/4:75,F:100"`` as an environment variable).
Each choice is a label paired with the percentage of a full tank it stands for,
and that percentage is what is stored for the fill.

Right now, regarding localization and currency formatting, please keep in mind
the following caveats (which I'd be happy to fix if anyone needs it):

* The currency specified in downloaded OFX files is ignored. Since currency
  conversion and exchange rates are far outside the scope of this application,
  it's assumed that all accounts will be in the currency defined in settings.
* The ``wishlist2project`` console script that parses Amazon Wishlists and
  updates Projects / BoMs with their contents currently only supports items
  priced in USD, and currently only supports wishlists on the US amazon.com
  site; these are limitations of the upstream project used for wishlist
  parsing.
* The database storage of monetary values assumes that they will all be a
  decimal number, and currently only allows for six digits to the left of the
  decimal and four digits to the right; this applies to all monetary units from
  transaction amounts to account balances. As such, if you have any
  transactions, budgets or accounts (including bank and investment accounts
  imported via OFX) with values outside of 999999.9999 to -999999.9999
  (inclusive), the application will not function. If anyone needs support for
  larger numbers (or, at the rate I'm going, I'm still working and paying into
  my pension in about 300 years), the change shouldn't be terribly difficult.

.. _app_usage.credit_card_payments:

Credit Card Payments
--------------------

When you pay a credit card, record the payment as an ordinary transaction on
the bank account the money left, and set **Credit Card Payment For** on the
Add/Edit Transaction form to the card being paid. That is the whole workflow.
Do not create an offsetting entry of any kind.

.. _app_usage.credit_card_payments.why:

Why a payment has no budget impact
++++++++++++++++++++++++++++++++++

Every transaction is counted against the income available in the pay period it
falls in. That is right for money spent from a bank account, but a credit card
purchase and the cash payment that settles it are two separate transactions, so
counting both charges the same money against your income twice.

Marking a transaction as a payment toward a credit account excludes it from
every budget and every pay period total. Each charge is already budgeted on its
own charge date, in its own pay period; the payment is a movement of cash
between two accounts the application already tracks.

This holds exactly as long as everything the payment settles was recorded as a
charge. That is true of purchases. It is *not* automatically true of interest
and fees — see :ref:`app_usage.credit_card_payments.balance` below if you carry
a balance on any card.

This holds however the dates fall:

* **Paid in the same pay period as the charge.** A $100 charge is counted once,
  in that period. The $100 payment adds nothing.
* **Paid after the period closed**, which is the normal case. Charges made in
  period N are counted in period N. The payment lands in period N+1 and adds
  nothing there, so N+1 is charged only its own purchases.

There is deliberately no netting of a card's charges against payments toward
it. Netting is correct only when a card is paid inside the same period its
charges were made; across periods it charges a period the payment amount rather
than that period's own purchases, which recreates the double-count one period
later.

.. _app_usage.credit_card_payments.balance:

If you carry a balance: interest and fees
+++++++++++++++++++++++++++++++++++++++++

.. warning::

   If you carry a balance on a credit card, read this. The zero-budget-impact
   rule is exact for the *purchases* a payment settles, and this application
   does not, on its own, account for the interest and fees you pay on top of
   them.

When a card is paid in full every month, everything a payment settles is a
purchase, and every purchase was recorded and budgeted on its charge date. The
payment really is nothing but a movement of cash, and excluding it from budget
totals is exactly right.

Carrying a balance breaks that premise. The card charges interest, and may
charge late fees or other fees, and those are amounts you owe *on top of* your
purchases. They are real money leaving your bank account — but this application
does not record them as budgeted charges.

That is deliberate and predates this feature.
:py:meth:`OFXTransaction.unreconciled() <biweeklybudget.models.ofx_transaction.OFXTransaction.unreconciled>`
excludes any downloaded transaction flagged as an interest charge, interest
payment, late fee, other fee, or payment. Those flags are set automatically from
the ``re_interest_charge``, ``re_interest_paid``, ``re_late_fee``,
``re_other_fee`` and ``re_payment`` regular expressions on the
:py:class:`~biweeklybudget.models.account.Account`. So an interest charge never
appears in the Reconcile view, is never matched to a
:py:class:`~biweeklybudget.models.transaction.Transaction`, and is never
counted against a budget.

**The consequence.** The interest portion of a card payment leaves your bank
account, and no budget or pay period records it. Your budget will show more
money available than you actually have, by the amount of interest and fees you
paid. Before this feature existed, card payments were counted against a budget
in full, which double-counted the purchases — the bug this feature fixes — but
did incidentally capture the interest. That side effect is now gone along with
the double-count.

**What to do about it.** Record the interest charge yourself, as an ordinary
transaction against the credit account, dated the day it was charged, against
whatever budget you want to carry your interest cost. Once it is recorded, it is
budgeted on its charge date like any other charge on that card, and the payment
that settles it correctly has no further impact. Nothing else about the workflow
changes.

You will also see the over-payment warning described below until you do, because
the payment genuinely does exceed the charges the application has on record.

.. _app_usage.credit_card_payments.validation:

What the payment panel tells you
++++++++++++++++++++++++++++++++

Once a card is selected, the form shows how the amount you have entered maps
onto the charges recorded for that card: how much settles charges from pay
periods that have already closed, broken down by period from oldest to newest,
and how much applies to the currently-open period.

If the amount is larger than every unpaid charge recorded for that card, you
are warned, and told by how much. On a card you pay in full, that reliably means
charges are missing from your records or were recorded against the wrong
account — for example, charges made near the end of a period that have not
posted yet, or a payment covering several periods at once after a missed cycle.
On a card carrying a balance it will also include the interest and fees
described above, which are not recorded as charges unless you record them
yourself.

The warning is advisory. You can always save the transaction: you know things
the application does not, including charges it has not downloaded yet.

Unpaid charges are counted from
:py:attr:`~biweeklybudget.settings.CREDIT_PAYMENT_BEGIN_DATE`, which defaults to
:py:attr:`~biweeklybudget.settings.RECONCILE_BEGIN_DATE`. Payments recorded
before this feature existed carry no card designation, so they are not
subtracted from a card's charge total; without a lower bound, a card's apparent
unpaid charges would drift upward without limit and the warning would stop
meaning anything. Move the date forward once historical payments have been
designated or written off.

.. _app_usage.no_budget_impact:

Transactions With No Budget Impact
----------------------------------

Some transactions need to exist so they can be reconciled against a real
downloaded bank or card transaction, but do not represent spending or income
against any budget. Check **No Budget Impact?** on the Add/Edit Transaction
form for these. Typical cases are statement credits, cash-back redemptions
applied as a statement credit, and manual adjustments made to bring a recorded
balance into line with the real one.

Such a transaction still belongs to an account, still needs a budget and an
amount like any other, still appears in the transaction list, and is still
available to reconcile. What changes is that it contributes nothing to any
budget's spent, allocated or remaining amounts, nothing to any pay period's
totals, and nothing to the account's unreconciled sum. It is marked as
*(no budget impact)* wherever transactions are listed, so it is clear why the
listed amounts do not add up to the totals above them.

Credit card payments get this behaviour automatically from the **Credit Card
Payment For** field and do not need the checkbox as well. The two fields are
independent: clearing the card designation from a transaction restores its
ordinary budget impact, unless you had also checked **No Budget Impact?**
yourself, in which case that choice stands.

.. _app_usage.per_account_totals:

Per-Account Transaction Totals
------------------------------

Each pay period view carries a **Per-Account Transaction Totals** table, below
the income/allocated/spent/remaining summary and above the budget and
transaction tables. It answers a question the rest of the page does not: how
much money moved through each of your accounts.

There is one row per account with any activity, and one column per pay period —
the same five periods, in the same order, as the *Remaining Balances* table at
the top of the page: the previous period, the one being viewed, and the three
that follow. The column headers link to those periods, and the account names
link to the accounts, so an unexpected number is one click from its detail.

An account with no transactions in any of the five periods gets no row at all;
one with no transactions in a particular period shows ``$0.00`` in that column.
Amounts keep their usual sign, so spending is positive, income is negative and
shown in red, and the bottom row totals each column.

.. _app_usage.per_account_totals.not_budget_totals:

Why these totals do not match the budget totals
+++++++++++++++++++++++++++++++++++++++++++++++

They are not supposed to, and the difference is deliberate.

The budget figures elsewhere on the page exclude credit card payments and any
transaction marked :ref:`No Budget Impact <app_usage.no_budget_impact>`,
because counting a card payment as well as the charges it settles would charge
the same money against your income twice.

The per-account totals include them. That exclusion is a statement about
budgets; the money leaves the paying account either way, and a total that
omitted it would not match the account's statement. An account whose only
activity in a period is a card payment therefore shows that payment in full
here, while contributing nothing to the period's *spent* figure above.

The totals do reconcile, exactly, with the Transactions table further down the
same page. They are that same list of transactions, grouped by account and
added up — including the scheduled transactions the period projects, and
including the rows marked *(no budget impact)*. If you want to check a cell,
add up the visible rows for that account.

.. _app_usage.account_balance_chart:

Account Balances Chart
----------------------

The **Account Balances** chart on the index page plots one line per account,
using the balances recorded each time account data is downloaded.

By default it shows the last year of history, not everything ever recorded. The
buttons in the panel heading — ``1m``, ``3m``, ``6m``, ``1y``, ``2y``, ``5y``
and ``All`` — change the span, redrawing the chart in place without reloading
the page. The button for the range currently displayed is highlighted. The
selection is not remembered: every visit to the index page starts on the
configured default again.

Two settings control this, and both are ordinary integers that can also be set
by environment variable:
:py:const:`~biweeklybudget.settings.ACCOUNT_BALANCE_CHART_DEFAULT_DAYS`, the
number of days shown on page load (``0`` for all history), and
:py:const:`~biweeklybudget.settings.ACCOUNT_BALANCE_CHART_MAX_POINTS`, the
largest number of dates the chart will ever plot.

.. _app_usage.account_balance_chart.sampling:

Why not every date is plotted
+++++++++++++++++++++++++++++

When the selected range holds more dates than
:py:const:`~biweeklybudget.settings.ACCOUNT_BALANCE_CHART_MAX_POINTS`, the chart
samples them at a regular interval instead of drawing them all. Five years of
daily balances is around 1,800 dates per account; drawn in full the chart is
both slow to load and too dense to read, which is what
`issue #279 <https://github.com/jantman/biweeklybudget/issues/279>`_ reported.

Sampling, rather than averaging into weekly or monthly buckets, is deliberate.
Every point on the chart is a balance that really was recorded on the date it
sits above, so a hovered value is a fact rather than a summary statistic.

**The most recent date is always plotted**, whatever the sampling interval works
out to. The right-hand edge of the chart therefore always agrees with the
account tables immediately below it on the same page.

.. _app_usage.account_balance_chart.dormant:

Accounts with no recent balances
++++++++++++++++++++++++++++++++

An account with no balance recorded inside the selected range still gets a line.
It is drawn flat at that account's most recent known balance from before the
range began, which is the same carry-forward the chart has always applied to
dates where an account has no record of its own.

This matters when narrowing the range: an account you stopped downloading a year
ago holds a flat line at its last known value rather than disappearing or
dropping to zero. A line at zero would say the account was emptied, which is a
very different statement from "nothing new has been recorded".

An account whose data begins part-way through the selected range is not treated
this way — its line simply starts where its data starts, rather than being
extended back over dates when the account had no recorded balance.

.. _app_usage.unallocated_funds:

The Unallocated Funds Notification
----------------------------------

Every page carries a banner at the top comparing the money you actually have
available against the money you have already committed. When the two are equal
no banner appears at all; that is the state to aim for.

.. _app_usage.unallocated_funds.available:

What counts as available
++++++++++++++++++++++++

**Funds available** is the combined balance of your budget-funding accounts --
the bank and cash accounts -- *less what you currently owe on your active
credit accounts*.

Subtracting the card balances matters more than it might appear. Every charge
you make on a card is budgeted on the day you make it, in the pay period it
falls in, so it is already accounted for on the committed side. The cash to
settle that charge, however, is still sitting in your checking account. If the
card balance were left out, that cash would be counted as available when it is
already spoken for, and the banner would report a surplus you do not have --
roughly one to two pay periods of card spending, permanently, for anyone who
puts most of their spending on cards. See `issue #320
<https://github.com/jantman/biweeklybudget/issues/320>`_.

A credit account carrying a *positive* balance -- an overpaid card, or one
holding a statement credit larger than its balance -- adds to the funds
available, because that money really is yours. Inactive accounts are ignored,
and a credit account with no recorded balance contributes nothing.

.. _app_usage.unallocated_funds.committed:

What counts as committed
++++++++++++++++++++++++

**Funds committed** is the sum of three figures, each shown in the banner and
linked to the view it comes from:

* **standing budgets** -- the combined current balance of your active standing
  budgets, which carry over from period to period.
* **current pay period allocated but unspent** -- what you have allocated in
  the current pay period minus what you have spent against it. This is money
  still committed against the cash you are holding.
* **unreconciled** -- the net of transactions you have entered but not yet
  matched to a real bank transaction.

.. _app_usage.unallocated_funds.not_pp_remaining:

"Allocated but unspent" is not the pay period's "remaining"
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

These are two different quantities and they routinely disagree, sometimes by
thousands of dollars and sometimes in sign. The banner reports *allocated minus
spent*. The pay period view's own **remaining** figure is *income minus
budgeted*. Neither is wrong; they answer different questions.

Allocated-but-unspent is the right figure for this banner because it is what is
still committed against the cash you are holding right now. The pay period's
remaining figure tells you instead whether that period's income covers what you
budgeted for it.

The banner used to call its figure "current pay period remaining" while linking
to a view that showed a different number under that word, which was the whole
of `issue #209 <https://github.com/jantman/biweeklybudget/issues/209>`_.

.. _app_usage.unallocated_funds.no_cash_impact:

Transactions that move no real cash
+++++++++++++++++++++++++++++++++++

The unreconciled figure counts only transactions that actually move money.
Transactions marked :ref:`No Budget Impact <app_usage.no_budget_impact>`, and
payments toward a credit account, are excluded from it -- otherwise entering a
card payoff would swing the banner by the full amount of the payoff for the
days between entering it and reconciling it.

They are excluded from this figure only. Both still appear in the reconcile
view and still need to be reconciled against the real bank transaction.

.. _app_usage.cash_position:

The Cash Position Page
----------------------

The :ref:`unallocated funds banner <app_usage.unallocated_funds>` compresses a
six-term calculation into one sentence. When the number in it looks wrong,
there is nothing in the sentence that tells you which term is responsible. The
**Cash Position** page, linked from the sidebar and from the banner itself,
lays the same calculation out in full.

.. _app_usage.cash_position.waterfall:

The waterfall
+++++++++++++

Read top to bottom, each line adding to or subtracting from a running total::

    Budget-funding account balances (itemized by account)      +
    Adjustment for unreconciled transactions                   -
    Outstanding credit account balances                        +
    ------------------------------------------------------------
    Net liquid position
    Standing budget balances (itemized)                        -
    Current pay period: allocated but not yet spent            -
    ------------------------------------------------------------
    Truly unallocated / uncommitted funds

Two things about the signs are worth stating plainly, because both look wrong
until you know why:

* **Credit balances are added, not subtracted.** Money owed on a card is
  *recorded* as a negative balance, so adding it performs the subtraction. The
  reason for applying the recorded sign rather than negating is that a card
  carrying a *positive* balance -- overpaid, or holding a statement credit
  larger than the balance -- really does hold money you can spend, and adding
  it with its own sign gets that case right without a special case.
* **The unreconciled adjustment is subtracted**, because spending is entered
  positive. Ledger minus unreconciled is the projected balance, which is why
  the per-account table shows the same subtraction one account at a time.

The bottom line is, by construction, the exact amount by which the banner says
available funds differ from allocated funds. The page and the banner are the
same calculation -- both read
:py:class:`~biweeklybudget.cashposition.CashPosition` -- rather than two
implementations that happen to agree, which is the arrangement that let
`issue #320 <https://github.com/jantman/biweeklybudget/issues/320>`_ go
unnoticed. A test asserts the identity directly.

Every aggregate line links to the view it comes from, and each itemized
account and budget links to its own detail view, so a figure that looks wrong
can be tracked down rather than just observed.

.. _app_usage.cash_position.ledger_vs_projected:

Ledger versus projected balances
++++++++++++++++++++++++++++++++

The account table shows the raw ledger balance, that account's unreconciled
total, and the projected balance side by side, along with the date the balance
was recorded. A ledger balance can lag reality by days, and on its own it is
misleading; the projected figure is what you will actually have once the
transactions you have already entered land.

An account for which no balance has ever been recorded shows **no balance
recorded** rather than ``$0.00``. It contributes nothing to the totals, but
"no data" and "zero dollars" are very different answers to "how much money do
I have", and the page does not conflate them.

.. _app_usage.cash_position.links:

Telling the app which accounts hold which budgets
+++++++++++++++++++++++++++++++++++++++++++++++++

The most common reason the uncommitted figure is stubbornly non-zero is a
budget-funding account whose balance no standing budget accounts for -- a
savings account, typically. Its balance sits in the uncommitted total forever
with no explanation.

To let the page explain that, edit a standing budget on the Budgets page and
tick the accounts its money is held in, under **Held in accounts**. The
relationship is **many-to-many**: one savings account commonly holds several
earmarked standing budgets (an emergency fund, a vacation fund, a car repair
fund), and a budget may be spread across more than one account. The links are
entirely optional, and the waterfall is identical whether or not you configure
any.

With links configured, the page reports:

* **Budget-funding accounts nothing allocates** -- active accounts that no
  active standing budget is linked to, named with their balances.
* **Coverage groups** -- each set of accounts and standing budgets reachable
  from one another through the links, with the total each side holds and the
  difference between them.

.. _app_usage.cash_position.coverage_groups:

Why differences are reported per group
++++++++++++++++++++++++++++++++++++++

A link records only that a budget's money is held in an account. It does not
record *how much* of that budget sits in that account, and nothing else in the
application does either.

So where one account holds three budgets, the difference between the account
balance and the three budget balances is exact and is reported for that
account. But where a budget spans two accounts, there is no honest way to say
how much of it belongs to each. Rather than invent an allocation rule, the
page groups everything reachable through the links and compares the two sides
of the group as a whole. A group holding a single account is labelled as a
per-account difference; a larger one says explicitly that the difference is
for the group.

A group whose two sides agree is still shown, marked as balanced. That is
deliberate: it means a group's *absence* from the page always tells you the
links are not configured, and never that they were checked and found fine. If
no links exist at all, the page says so rather than listing every account as a
problem.
