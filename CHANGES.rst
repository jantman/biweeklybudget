Changelog
=========

1.12.0 (2026-09-08)
-------------------

* `Issue #321 <https://github.com/jantman/biweeklybudget/issues/321>`_ - Add a Cash Position page showing the full available-funds waterfall.

  * **The problem.** The banner on every page reports, in one sentence, whether the money you have differs from the money you have already committed. It quotes six figures and offers no way to see where any of them came from; when the number looks wrong the only recourse was to read the source and query the database by hand. "How much money do I actually have that isn't spoken for?" is the question this application exists to answer, and it was being answered only as a footnote to an error message.
  * The new **Cash Position** page, at ``/cash-position`` and linked from the sidebar and from the banner itself, lays the same calculation out as a waterfall: budget-funding account balances, the unreconciled adjustment that turns ledger into projected, credit account balances, a **Net liquid position** subtotal, then standing budgets and the current pay period's allocated-but-unspent, giving **Truly unallocated / uncommitted funds**. Each aggregate line links to the view it derives from, and each itemized account and budget links to its own detail view.
  * **The arithmetic moved out of the notification code.** The five figures the banner reports now come from :py:class:`~biweeklybudget.cashposition.CashPosition`, a new module beside ``biweeklypayperiod.py``, and ``NotificationsController``'s methods are thin delegations to it. Without that, the page would have been a *second* implementation of the same sums, free to drift from the first -- which is exactly what `#320 <https://github.com/jantman/biweeklybudget/issues/320>`_ turned out to be. A test asserts, over a matrix in which every term takes a zero, positive and negative value, that the page's bottom line equals the banner's available-minus-committed exactly. The six existing ``NotificationsController`` methods keep their names, signatures and behaviour; all sixteen pre-existing notification tests pass unchanged.
  * ``CashPosition`` computes each term lazily and caches it. That is load-bearing rather than an optimization: the banner reads five figures and nothing else, and the existing unit tests call ``credit_account_sum()`` with a mock session while patching only one query. A test pins that constructing a ``CashPosition`` runs no queries at all.
  * **Ledger and projected balances are shown side by side**, per account, with the date each balance was recorded. A ledger balance can lag by days and is misleading on its own. An account for which no balance has ever been recorded shows "no balance recorded" rather than ``$0.00`` -- it contributes nothing to the totals either way, but "no data" and "zero dollars" are very different answers to "how much money do I have".
  * **New many-to-many association between standing Budgets and Accounts** (``budget_accounts``, migration ``2d881fa466fe``), edited as checkboxes on the budget modal. This is what lets the page name the budget-funding accounts that no standing budget accounts for -- usually a savings account, whose balance otherwise sits in the uncommitted figure forever with no explanation.
  * **Many-to-many, not a foreign key on Budget.** One savings account commonly holds several earmarked standing budgets, and a budget may be spread across more than one account; a 1:1 link cannot express either. The table carries **no amount and no split**, deliberately, and is a plain association table rather than a model class for that reason -- a class invites someone to add an amount column later, and that column is precisely the allocation rule the application does not have.
  * **Differences are therefore reported over "coverage groups"** -- the maximal sets of accounts and budgets reachable through the links. Where one account holds three budgets the difference is exact and is labelled as a per-account difference; where a budget spans two accounts there is no honest way to say how much of it belongs to each, so the page compares the group as a whole and says so, rather than inventing a split. A group whose sides agree is still shown, marked balanced, so that a group's *absence* always means "not configured" and never "checked and fine". With no links configured at all -- the state of every installation on upgrade -- the waterfall is unaffected and the page says the links are not configured rather than listing every account as a problem.
  * The checkboxes are checkboxes rather than a multi-select because ``serializeForm()`` reads ``select`` elements with ``.find(':selected').val()``, which returns only the first selection; a ``<select multiple>`` would have silently dropped every account but one. ``Budget.account_ids`` is exposed through ``_dict_properties`` rather than left to the relationship, since ``as_dict`` is built from ``vars(self)`` and would otherwise return linked IDs only when they happened to be loaded.
  * **The notification banner's wording is unchanged.** That text was corrected only in 1.11.1 and is covered by tests; it gains one link to the new page and nothing else.
  * ``docs/source/app_usage.rst`` gains a Cash Position section explaining the waterfall, both counter-intuitive sign conventions, ledger versus projected balances, how to configure the links, and why differences are reported per group.

1.11.1 (2026-09-07)
-------------------

* `Issue #320 <https://github.com/jantman/biweeklybudget/issues/320>`_ - Correct the unallocated-funds notification: subtract credit account balances, and stop calling the pay-period figure "remaining". Also closes `Issue #209 <https://github.com/jantman/biweeklybudget/issues/209>`_, which was folded into #320 as a duplicate.

  * **The problem.** The banner on every page compared the combined balance of the budget-funding accounts against standing budgets plus the current pay period plus unreconciled transactions. Credit account balances appeared nowhere in that comparison. Every charge on a card is budgeted on the day it is made, so it is already counted on the committed side -- but the cash to settle it is still sitting in checking and was being counted as available. The banner therefore reported a surplus that did not exist, systematically, by roughly the outstanding card float: one to two pay periods of spending for anyone who puts most of their spending on cards, permanently. A banner that is always wrong in the same direction is worse than no banner, because it trains you to ignore the one signal that would tell you you had over-committed.
  * The combined balance of active credit accounts is now applied to the available side. Credit balances are stored **negative when money is owed**, and the new :py:meth:`~biweeklybudget.flaskapp.notifications.NotificationsController.credit_account_sum` adds them **with their own sign** rather than taking an absolute value. That is not incidental: it is what makes an overpaid card, or one holding a statement credit larger than its balance, correctly *increase* the funds available instead of decreasing them. The unit tests pin signed values and include the positive-balance case, precisely because an ``abs()``-based implementation would pass a test that only checked the figure got smaller.
  * The accounts are drawn from the existing :py:meth:`~biweeklybudget.models.account.Account.active_credit_accounts`, the same set the credit-payment feature uses, so the two cannot drift apart. Inactive accounts are excluded and an account with no recorded balance contributes zero without preventing the banner from rendering.
  * **The pay-period figure was mislabelled, not miscalculated.** The banner showed *allocated minus spent* under the words "current pay period remaining", linked to a view whose own "remaining" is *income minus budgeted*. These are unrelated quantities that can differ by thousands of dollars and even in sign. The quantity is right for this banner -- allocated-but-unspent is what is still committed against the cash on hand -- so it is the name that changed, to "current pay period allocated but unspent". The pay period view is untouched; its figure is correct for that view. This was originally reported in 2019 as #209 against code that had not changed since.
  * The banner now names the credit deduction as its own linked term, so the reported figure visibly accounts for the difference from the raw funding-account balance. It carries five links where it carried four.
  * **The issue's second defect -- pseudo-transactions inflating the unreconciled figure -- was already fixed** by the work for `#210 <https://github.com/jantman/biweeklybudget/issues/210>`_ and `#319 <https://github.com/jantman/biweeklybudget/issues/319>`_: ``Transaction.is_excluded_from_budget`` covers both no-budget-impact transactions and credit card payments, and ``Account.unreconciled_sum`` already skipped them. This was verified against the code rather than taken from the issue text. What was missing was any test connecting that behaviour to the banner that depends on it, so a regression would have silently reintroduced a multi-thousand-dollar error lasting days; ``TestNoCashImpactNotification`` is that test. The issue's fallback suggestion of filtering reconciles noted ``pseudo-trans`` is deliberately **not** implemented, as it would reintroduce a second, disagreeing definition of "no cash impact" alongside the explicit flag that replaced it.
  * Excluding those transactions from the banner's arithmetic does not hide them from reconciliation; they remain listed and reconcilable, and a test pins that too.
  * ``docs/source/app_usage.rst`` gains a section explaining what the banner compares, why card balances are subtracted, and why "allocated but unspent" is not the pay period view's "remaining" -- the confusion that #209 was filed about.
  * **Known limitation, pre-existing and not addressed here**: ``templates/index.html`` dereferences ``acct.balance.ledger`` in the credit accounts table with no ``None`` guard, so an *active* account that has never had a balance recorded makes the index page fail to render. This is unrelated to the notification and is out of scope for this change.
  * No schema change, no migration, no new dependency, and no new setting.

1.11.0 (2026-09-07)
-------------------

* `Issue #322 <https://github.com/jantman/biweeklybudget/issues/322>`_ - Accept Accounts and Budgets by name as well as by ID when creating a Transaction over HTTP, and ship ``addtrans``, a console script that does so.

  * **The problem.** ``POST /forms/transaction`` has been documented as the scriptable way to create a Transaction since 1.5.1, but it identified Accounts and Budgets only by numeric database ID. External tooling knows them by the names on screen, so using the endpoint meant first scraping IDs out of the application -- which made it unusable for the case that motivated the issue: a script that computes each credit card's charges for a pay period and enters the payment and its negating offset itself, instead of leaving the most error-prone step in the workflow to be typed by hand (`#210 <https://github.com/jantman/biweeklybudget/issues/210>`_, `#319 <https://github.com/jantman/biweeklybudget/issues/319>`_, `#320 <https://github.com/jantman/biweeklybudget/issues/320>`_).
  * ``account``, ``credit_payment_acct``, and every key of the ``budgets`` mapping now take an ID **or** a name, and the two may be mixed freely within one request. Resolution is digits-first: an all-digits value is looked up as a primary key and a hit ends the search, so IDs keep the precedence they have always had on these fields and the web UI's own requests take exactly the path they did before. Only when that misses -- or when the value was never all digits -- is the value matched against the name, whole and case-insensitively after stripping surrounding whitespace.
  * **Running the name lookup after a** *missed* **ID lookup is deliberate.** Nothing stops a budget being named "2024", and a rule of "digits are always IDs, full stop" would leave such a record permanently unreachable by name with no recourse. The residual ambiguity -- Budget 12 existing alongside a *different* budget named "12" -- resolves to the ID, and is documented as doing so.
  * **No fuzzy matching.** Names match whole or not at all. This endpoint moves money, and a typo that quietly lands on the nearest budget is worse in every way than one that fails with an error. For the same reason ``func.lower()`` is applied to the column explicitly rather than trusting the database collation to be case-insensitive, so the behaviour is a property of the code and is pinned by a test.
  * The lookup itself is :py:func:`~biweeklybudget.models.utils.resolve_by_name_or_id`, a single function usable by the next form handler that needs it. ``TransactionFormHandler.validate()`` calls it first and **rewrites the submitted data in place to canonical numeric IDs** -- the same in-place normalization ``FormHandlerView.normalize_currency()`` already performs for currency fields. Everything downstream, ``submit()`` included, therefore still deals only in IDs and is unchanged; backward compatibility for existing callers falls out of the diff rather than resting on tests to notice a regression.
  * **The one genuinely new error condition**: two keys of ``budgets`` that resolve to the same Budget are rejected with ``Budget <name> specified more than once.`` Rekeying by resolved ID would otherwise collapse them into one allocation and leave a Transaction whose budget amounts no longer sum to its amount. This was unreachable before, since two distinct ID keys could not denote one record.
  * **Two error messages changed wording.** ``Budget ID %s is invalid.`` and ``Account ID %s is invalid.`` are now ``Budget "%s" is invalid.`` and ``Account "%s" is invalid.``; the old text would have read "Account ID CHASE is invalid" once names were accepted.
  * **``notes`` and ``sales_tax`` are now genuinely optional.** Both were documented as optional, but ``submit()`` indexed them directly, so a request that actually omitted either got a 500 rather than the documented default -- ``docs/source/http_api.rst`` said so of ``notes`` in as many words. An external caller has no reason to send an empty string for a field it does not use.
  * The new ``addtrans`` console entrypoint creates a Transaction from the command line, taking the inputs of the Add Transaction form: ``addtrans CHASE 123.45 'Groceries' -b Food``. It deliberately speaks HTTP rather than touching the database -- talking to the database would be simpler and would prove nothing about the API -- and so imports neither :py:mod:`biweeklybudget.db` nor :py:mod:`biweeklybudget.settings` and needs no settings module. The application's address comes from ``--url``, else the ``BIWEEKLYBUDGET_URL`` environment variable, else ``http://127.0.0.1:8080``. ``--dry-run`` prints the request without sending it. Amounts are passed through verbatim, so the server keeps sole ownership of what an amount is; parsing them client-side would create a second, subtly different definition.
  * Note that the endpoint answers a *validation failure* with HTTP 200 and ``"success": false``, so ``addtrans`` reads the outcome from the body rather than the status code. Validation errors are printed one line per field and exit 1; an unreachable server produces one readable line naming the URL rather than a traceback.
  * ``docs/source/http_api.rst`` gains an "Identifying Accounts and Budgets" section stating the resolution rule, the ID-over-name precedence, the exact-match rule, and the fact that the UI's ``(income)`` suffix is a display label rather than part of a budget's name. ``docs/source/getting_started.rst`` lists the new entrypoint.
  * The issue's "Follow-on" -- warning that a closed pay period's credit card charges have no corresponding payment -- is **not** included. This change is the building block it needs, not that feature.
  * No schema change, no migration, no new dependency, no new setting, and no change to the endpoint's response shape.

1.10.0 (2026-09-07)
-------------------

* `Issue #279 <https://github.com/jantman/biweeklybudget/issues/279>`_ - Bound the index page "Account Balances" chart by time window and by point count, and add a range selector to widen it again.

  * **The problem.** With five years of daily balances the chart took tens of seconds to appear and was too dense to read anything from. The issue proposed limiting the history shown, summarising it, or -- conditional on `Issue #215 <https://github.com/jantman/biweeklybudget/issues/215>`_ -- adopting a chart library with interactive zoom. The first two are implemented, and the zoom-out is delivered on the existing library.
  * **The largest cost was not the volume of data.** ``AcctBalanaceChartView.get()`` resolved each balance's account name through ``AccountBalance.account``, a relationship with SQLAlchemy's default ``lazy='select'``, so it issued one ``SELECT`` per balance row -- for a name the method already held in a dict it had built two lines earlier. At roughly 18,000 balance rows that is 18,000 round trips to the database. Reading from the dict is a one-line change and was by far the biggest single win; it was committed on its own so it is visible as such in the history.
  * ``GET /ajax/chart-data/account-balances`` now takes an optional ``days`` parameter, applied as a filter on ``overall_date`` in SQL rather than by loading everything and discarding most of it. ``days=0`` means all recorded history. Anything that is not a non-negative integer -- absent, negative, ``abc``, ``1.5`` -- falls back to the configured default rather than returning an error, because for a read-only chart endpoint a mistyped URL is better served by the default view than by a traceback.
  * The assembled rows are then sampled at a regular interval down to at most :py:const:`~biweeklybudget.settings.ACCOUNT_BALANCE_CHART_MAX_POINTS` dates. The window alone does not bound anything, since ``days=0`` has no upper limit; the point cap is what actually bounds transfer size and draw time. Sampling rather than averaging into weekly or monthly buckets is deliberate: every plotted point stays a balance that really was recorded on the date it sits above, so a hovered value is a fact rather than a summary statistic.
  * **The most recent date is always kept**, whatever the sampling interval works out to. The right-hand edge of this chart sits directly above the account tables on the same page, and a stride that happened to stop two days short would make the chart silently disagree with them.
  * **Windowing breaks the forward-fill unless it is handled explicitly, and does so in a way that misstates money.** An account whose most recent balance predates the window has no in-window row to carry forward from, so it would be reported as ``null`` on every date -- which on a chart of account balances reads as the account having been emptied. That is worst for dormant accounts, exactly the ones nobody would notice being wrong. ``AcctBalanaceChartView._balances_before()`` therefore fetches each account's last balance from before the window and seeds the carry-forward with it: one query grouped by ``account_id``, bounded by the number of accounts and never by the amount of history. ``test_dormant_account_keeps_its_line`` pins it. An account whose data *begins* part-way through the window is not back-filled, since it had no balance to report on those dates.
  * With an explicit seed, the old trick of consuming the first date row to prime the carry-forward is no longer needed, so the earliest date in the window is now plotted rather than silently dropped. Responses gain one point at the left edge; this is a deliberate improvement, not a regression.
  * A Bootstrap 3 button group in the panel heading offers ``1m``/``3m``/``6m``/``1y``/``2y``/``5y``/``All``, redrawing the chart in place via Morris's ``setData()`` -- no page reload, and no second chart drawn over the first. The selection is not persisted between page loads. An empty response shows a "No account balance data to display." message where the chart would be.
  * **Issue #215 is deliberately not folded in.** Adopting a more capable chart library means a licence review, a new bundled asset, rewriting the budgets and fuel charts too for consistency, and a much larger acceptance-test surface -- all to deliver a zoom that a seven-button range selector delivers adequately. The constitution requires new UI work to follow the existing frontend stack rather than introducing a parallel one. The server side is library-agnostic, so #215 can later replace the button group without touching the view.
  * Add :py:const:`~biweeklybudget.settings.ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` (default ``365``) and :py:const:`~biweeklybudget.settings.ACCOUNT_BALANCE_CHART_MAX_POINTS` (default ``300``), following the ``DEFAULT_ACCOUNT_ID``/``FUEL_BUDGET_ID`` pattern: module-level defaults, listed in ``_INT_VARS`` so environment variables override them, and absent from ``_REQUIRED_VARS`` so a settings module predating this feature keeps working untouched.
  * ``static/js/index.js`` moves from an anonymous IIFE body to named, JSDoc-commented functions. Beyond readability, this is what makes the file visible to ``tox -e jsdoc``, which documents named functions and so produced nothing at all for it before; ``docs/source/jsdoc.index.rst`` is new.
  * ``docs/source/http_api.rst`` gains an entry for this endpoint, which it did not previously document. **The one behaviour change for existing callers**: a request with no ``days`` parameter now returns only the default window rather than all history. Pass ``days=0`` for the previous response.
  * ``docs/source/app_usage.rst`` gains an "Account Balances Chart" section explaining the sampling and the dormant-account line, both of which would otherwise reasonably read as bugs.
  * Two bugs found in review of `PR #331 <https://github.com/jantman/biweeklybudget/pull/331>`_ and fixed before merge. A ``days`` value large enough to put the window start below ``datetime.MINYEAR`` made ``dtnow() - timedelta(days=days)`` raise ``OverflowError``, so ``?days=999999`` answered with an HTTP 500 instead of a chart -- exactly the outcome the parameter handling exists to prevent. ``parse_chart_days()`` now collapses anything above ``MAX_CHART_DAYS`` (36,500) to ``0``, which is also the honest answer: such a window reaches back before every recorded balance. The ceiling is applied to the fallback default as well as to the query parameter, since ``ACCOUNT_BALANCE_CHART_DEFAULT_DAYS`` is operator-settable and clamping only the parameter would have left the same crash reachable through a misconfigured setting. Separately, the range buttons fired unsequenced AJAX requests, so clicking **All** (the slowest query) and then **1m** (among the fastest) could leave the chart showing all history beneath a highlighted **1m** button; requests now carry a sequence number and stale responses are discarded.
  * No schema change, no migration, no new dependency, and no change to the endpoint's response shape.

1.9.0 (2026-09-07)
------------------

* `Issue #213 <https://github.com/jantman/biweeklybudget/issues/213>`_ - Add a per-account transaction totals table to the single pay period view.

  * The pay period view could say how much was budgeted, spent and remaining overall, and how much per budget, but not how much moved through each account. Answering that meant scanning the transaction list and adding amounts up by hand -- exactly the sort of thing to get wrong when reconciling a statement or checking a card's activity before its payment comes due.
  * The new **Per-Account Transaction Totals** table sits below the income/allocated/spent/remaining tiles. Accounts are rows, ordered by name; the columns are the same five pay periods the *Remaining Balances* table at the top of the page already shows -- previous, current, and the three following -- with the same labels, the same ``(prev.)``/``(curr.)``/``(next)`` suffixes, the same links to those periods and the same emphasis on the current one. Account names link to the account, empty account/period combinations show ``$0.00``, negatives are red, and the bottom row totals each column.
  * The issue asked for "the per-account transaction totals for each payperiod", which could be read as one column or several. Five columns was chosen because it is a superset of the narrower reading, gives the period-over-period comparison that makes an account total actionable, and costs nothing: the view already computes all five periods' data in full in order to render the *Remaining Balances* table.
  * **These totals deliberately do not match the budget totals on the same page.** ``_make_budget_sums()`` excludes credit card payments and transactions flagged as having no budget impact, because counting a payment as well as the charges it settles would charge the same money against income twice (issues #210 and #319). That exclusion is a statement about budgets. The money leaves the paying account either way, so an account activity total that omitted it would not match the account's statement. ``docs/source/app_usage.rst`` gains a section saying so, since the discrepancy would otherwise read as a bug.
  * Add ``BiweeklyPayPeriod.account_sums``, returning ``{account_id: {'name': str, 'total': Decimal}}`` for the accounts with activity in the period, cached in ``_data_cache`` alongside ``budget_sums`` and ``overall_sums``. It is computed by summing ``transactions_list`` -- the same list the page's transaction table renders -- rather than by a query of its own. That is what makes every cell verifiable by adding up the rows on screen, keeps scheduled transactions and split transactions handled identically to the rest of the page, and adds no database round trip.
  * Accounts with no activity are absent from ``account_sums`` rather than present with a zero; the zeros are supplied by the view, which is the only thing that knows which accounts are on screen and therefore need one.
  * ``PayPeriodView.get()`` now binds its five pay period objects once rather than re-walking ``pp.next.next.next`` for each value it needs. ``next`` and ``previous`` construct a new object on every read, and each object builds and caches its own data on first use, so without this, reading both ``overall_sums`` and ``account_sums`` from a period would compute that period's data twice. The values passed to the template are unchanged.
  * No schema change, no migration, no new endpoint, no new setting, no new dependency, and no JavaScript: the table is plain server-rendered Bootstrap markup.

1.8.0 (2026-09-06)
------------------

* `Issue #210 <https://github.com/jantman/biweeklybudget/issues/210>`_ and `Issue #319 <https://github.com/jantman/biweeklybudget/issues/319>`_ - Special handling of credit card payments, built on a general "no budget impact" flag.

  * **The problem.** Every transaction is counted against the income available in the pay period it falls in. That is right for money spent from a budget-funding account, but a credit card purchase and the cash payment that settles it are two separate transactions, so both were counted and the same money was charged against available income twice. The workaround was to enter the payment plus a hand-calculated "pseudo-transaction" of equal negative amount cancelling it, which is correct only while the payment happens to equal the total of that card's charges in the period being paid off. In practice those diverge routinely, and when they do nothing warns about it.
  * **The rule now implemented.** A payment toward a credit account has zero budget impact, in every pay period, regardless of when the payment falls relative to the charges. Each charge is budgeted on its own charge date, in its own pay period; the payment is a movement of cash between two accounts the application already tracks.
  * **Not implemented: the netting approach** #210 originally proposed, of subtracting a credit account's charges in a period from payments toward it. It is correct only when a card is paid inside the same pay period its charges were made. Across periods, with charges ``C(n)`` in period N paid in N+1 which has its own charges ``C(n+1)``, netting charges N+1 with ``C(n+1) + (P - C(n+1))`` = ``P``, when the correct answer is ``C(n+1)`` -- recreating the double-count it exists to remove, displaced by one period. ``test_credit_payment_is_not_netted_against_period_charges`` is a named regression guard against reintroducing it.
  * Add ``Transaction.no_budget_impact``, a general flag for transactions that need to exist so they can be reconciled against a real OFX/Plaid transaction but represent no spending or income -- statement credits, cash-back redemptions applied as a statement credit, manual balance reconcile adjustments. This is issue #319, which #210 depends on and which had no implementation.
  * Add ``Transaction.credit_payment_acct_id``, recording which credit account a transaction is a payment toward, surfaced as a "Credit Card Payment For" dropdown of active credit accounts on the Add/Edit Transaction form. Setting it applies zero-budget-impact behaviour automatically; no offsetting transaction is entered.
  * The effective answer is a derived ``Transaction.is_excluded_from_budget`` hybrid property over both fields, not a stored value. Keeping them separate is what lets clearing the card designation restore a transaction's ordinary budget impact while a flag the user set themselves survives that change.
  * Standing budget balances are corrected too. ``Budget.current_balance`` is persisted state maintained by ``db_event_handlers``, not computed on read like periodic budget totals, so all three handlers now skip a ``BudgetTransaction`` whose ``Transaction`` is excluded, and a new ``handle_transaction_budget_exclusion_change()`` refunds or re-applies the debit when the designation is toggled on an existing transaction. Without the latter, clearing a credit card payment designation would leave a standing budget permanently over-credited.
  * Excluded transactions are omitted from ``BiweeklyPayPeriod._make_budget_sums()`` -- and so from ``_make_overall_sums()``, which derives from it -- and from ``Account.unreconciled_sum``. They remain listed in the transactions table and the pay period's transaction table, marked *(no budget impact)*, and remain available to reconcile: the filter is applied to the sums, not to the queries, so a reader can see why the listed amounts do not add up to the totals above them.
  * Add ``biweeklybudget.credit_payment.CreditPaymentAttribution`` and a read-only ``GET /ajax/credit-payment-info`` endpoint driving a live panel in the transaction modal. While a payment is being entered it shows how the amount maps onto the card's recorded charges -- how much settles already-closed pay periods, broken down oldest first, and how much applies to the currently-open one -- and warns, stating the excess, when the amount exceeds every unpaid charge recorded for that card, which reliably indicates missing or misattributed transactions. The warning is advisory and never blocks saving.
  * Add the optional ``CREDIT_PAYMENT_BEGIN_DATE`` setting, defaulting to ``RECONCILE_BEGIN_DATE``, bounding the window over which a card's unpaid charges are computed. Payments recorded before this feature carry no card designation and so are never subtracted; without a lower bound a card's apparent unpaid total would drift upward without limit and the warning would stop meaning anything.
  * Alembic migration ``f9df90273cdd``, with both directions tested. Existing rows come through with ``no_budget_impact = 0`` and ``credit_payment_acct_id = NULL``, so every existing pay period total, budget total and account unreconciled sum is unchanged by the upgrade.
  * ``transactions`` now holds two foreign keys to ``accounts.id``, so the existing ``Transaction.account`` relationship gained an explicit ``foreign_keys``; without it SQLAlchemy cannot infer the join condition for either relationship.
  * ``FormBuilder`` gained ``inputHtml`` on ``addSelect`` and ``addCurrency``, and ``helpBlock`` on ``addCheckbox``, following the convention ``addText`` already established.
  * Document the credit card payment workflow and the no-budget-impact flag in ``docs/source/app_usage.rst``.
  * **Known limitation, documented rather than fixed:** the zero-budget-impact rule is exact for the purchases a payment settles; it does not account for interest or fees on a carried balance. ``OFXTransaction.unreconciled()`` has always excluded transactions flagged as interest charges, interest payments, late fees, other fees and payments, so an interest charge never reaches the Reconcile view and never becomes a budgeted ``Transaction``. Anyone carrying a balance therefore has the interest portion of a payment leave their bank account with no budget recording it. Previously card payments counted in full, which double-counted the purchases but incidentally captured the interest; that side effect goes away along with the double-count. ``docs/source/app_usage.rst`` gains a section telling balance-carriers to record the interest charge themselves as an ordinary transaction on the credit account, after which the rule holds again.

1.7.0 (2026-09-06)
------------------

* `Issue #323 <https://github.com/jantman/biweeklybudget/issues/323>`_ - Normalize currency values entered in the UI, so that all currency inputs accept common formatting.

  * Entering a currency value containing thousands separators, such as ``1,234.56``, previously produced a 500 Internal Server Error. ``FormHandlerView.post()`` wrapped ``submit()`` in a ``try``/``except`` but called ``validate()`` unguarded, and ``TransactionFormHandler.validate()`` calls ``Decimal(data['amount'])`` directly, so ``decimal.InvalidOperation`` propagated out to Flask. Six other validators had the same shape with unguarded ``float()``.
  * Bare integers were rejected by several inputs; ``123`` had to be entered as ``123.0``. ``FormHandlerView._validate_float()`` asserted ``data[key].startswith('%s' % float(data[key]))``, and ``'123'.startswith('123.0')`` is ``False``.
  * Add :py:func:`biweeklybudget.utils.parse_currency` and ``CurrencyParseError``, the single server-side authority for interpreting a user-entered amount, alongside the existing ``fmt_currency()``. It wraps ``babel.numbers.parse_decimal(..., strict=True)`` and returns an exact ``Decimal``. Babel was already a dependency; nothing new is added.
  * Add a matching ``parse_currency()`` to ``biweeklybudget/flaskapp/static/js/custom.js``, alongside its ``fmt_currency()`` counterpart, and use it in place of ``parseFloat()`` in ``transactions_modal.js``. ``parseFloat('1,234.56')`` is ``1``, so budget split validation previously disabled the Save button for any separator-formatted amount, making the fix unreachable in that flow.
  * Normalize in one place on the server: ``FormHandlerView`` gains ``currency_fields`` and ``decimal_fields`` class attributes and a ``normalize_currency()`` hook that runs before ``validate()``. Every form handler declares its own fields, so all existing ``Decimal()``/``float()`` conversions in ``validate()`` and ``submit()`` are left untouched, and the complete set of currency fields can be found by grepping for those attributes.
  * Also wrap the ``validate()`` call in ``FormHandlerView.post()`` in a ``try``/``except``, so that no conversion anywhere can produce a 500 again.
  * All of the following are now accepted (for a ``en_US``/``USD`` configuration): bare integers, comma or space thousands separators (including Unicode spaces), a leading or trailing currency symbol or ISO code, a leading ``+`` or ``-``, parentheses denoting a negative, and surrounding whitespace.
  * Ambiguously grouped values such as ``10,00``, ``1,23,4.56``, ``1,234,`` and ``,123`` are rejected with a field-level validation error rather than being silently read as ``1000``, ``1234.56``, ``1234`` and ``123``. For an application that tracks real money, guessing at a typo is worse than refusing it.
  * Locale conventions are read from ``LOCALE_NAME`` and ``CURRENCY_CODE`` on both the server and the client, so adding another locale is a configuration change; this is covered by tests against ``de_DE``.
  * Reword the validation messages ``Invalid float value: "..."`` and ``Invalid Decimal value: "..."``, which leaked Python type names, to ``Invalid number: "..."`` and ``Invalid amount: "..."``.
  * Fuel Log ``gallons`` and ``reported_mpg`` are not currency, but shared the validation helper responsible for the bare-integer defect; they are fixed too.
  * Add unit tests covering the accept/reject matrix and the normalization hook, and Selenium browser tests covering the Transaction modal (including budget splits) plus every other currency input in the application.
  * Document the accepted input formats in ``docs/source/app_usage.rst``.

1.6.2 (2026-09-06)
------------------

* `Issue #324 <https://github.com/jantman/biweeklybudget/issues/324>`_ - Update all dependencies to their latest versions, including all packages with open GitHub Dependabot security alerts.

  * ``requirements.txt``: Flask 3.1.2 to 3.1.3, Mako 1.3.10 to 1.4.1, PyMySQL 1.1.2 to 1.2.0, SQLAlchemy 2.0.45 to 2.0.52, alembic 1.18.1 to 1.19.2, babel 2.17.0 to 2.18.0, beautifulsoup4 4.14.3 to 4.15.0, cffi 2.0.0 to 2.1.1, click 8.3.1 to 8.5.0, httplib2 0.31.1 to 0.32.0, humanize 4.15.0 to 4.16.0, idna 3.11 to 3.19, lxml 6.0.2 to 6.1.3, newrelic 11.2.0 to 13.5.0, plaid-python 38.0.0 to 44.0.0, pycparser 2.23 to 3.0, pyparsing 3.3.1 to 3.3.2, selenium 4.39.0 to 4.48.0, and Werkzeug 3.1.5 to 3.1.8.
  * This resolves the Dependabot alerts for Flask, Werkzeug, httplib2, idna, Mako (two alerts), and lxml, superseding Dependabot PRs `#316 <https://github.com/jantman/biweeklybudget/pull/316>`_, `#317 <https://github.com/jantman/biweeklybudget/pull/317>`_, and `#318 <https://github.com/jantman/biweeklybudget/pull/318>`_.
  * Remove ``biweeklybudget/flaskapp/static/jquery-ui-1.12.1.custom/package.json``. Only ``jquery-ui.min.js`` from that custom jQuery UI download is used; the manifest declared jQuery UI's own build-time ``devDependencies`` (including a vulnerable ``grunt``), which this project never installs, and was the source of three Dependabot npm alerts.
  * ``tox.ini``: alembic-verify 0.1.4 to 1.0.2, sqlalchemy-diff 0.1.5 to 1.1.1, selenium 4.39.0 to 4.48.0, Pillow 12.1.0 to 12.3.0, sphinx 8.1.3 to 9.1.0, docutils 0.21.2 to 0.22.4 (0.23 is incompatible with Sphinx 9), pygments 2.19.2 to 2.21.0, and sphinx-js 5.0.2 to 5.0.3.
  * Update the migration tests for the sqlalchemy-diff 1.0 API: ``sqlalchemydiff.compare()`` is replaced by ``sqlalchemydiff.comparer.Comparer``, the removed ``sqlalchemydiff.util.prepare_schema_from_models()`` helper is reimplemented locally in ``test_alembic_verify.py``, and the constraint ignore clauses use the new ``check_constraints`` inspector key instead of ``cons``.
  * Add ``biweeklybudget/tests/migrations/conftest.py`` defining ``alembic_config_left`` and ``alembic_config_right``. alembic-verify 1.0 deprecated its own fixtures of those names and resolves the Alembic script location relative to the current working directory; ours use the absolute path from the ``alembic_root`` fixture.
  * Docker image: base image ``python:3.14-alpine3.23`` to ``python:3.14-alpine3.24``, and gunicorn 22.0.0 to 26.2.0.
  * GitHub Actions: ``actions/checkout`` to v7, ``actions/setup-python`` to v7, ``actions/upload-artifact`` to v7, ``actions/download-artifact`` to v8, ``actions/github-script`` to v9, ``docker/login-action`` to v4, and ``pypa/gh-action-pypi-publish`` to v1.14.2.
  * Regenerate the ``sphinx-apidoc``-generated ``docs/source/*.rst`` files with Sphinx 9.

1.6.1 (2026-09-06)
------------------

* `Issue #325 <https://github.com/jantman/biweeklybudget/issues/325>`_ - Fix the tox test suite so that all environments pass locally and in CI.

  * ``docs`` environment: the ``linkcheck`` build was failing because Stack Overflow now returns HTTP 403 to automated requests; add ``stackoverflow.com`` to ``linkcheck_ignore`` in ``docs/source/conf.py``.
  * Update all documentation links that had moved or now redirect: Docker ``docker run`` reference, Flask server docs, tox docs (``tox.wiki``), chromedriver docs, Alembic docs, the startbootstrap-sb-admin-2 repository, the BCP 47 spec (``rfc-editor.org``), and ``http://`` links to sites that now redirect to ``https://``.
  * Add ``linkcheck_timeout`` and ``linkcheck_retries`` to ``docs/source/conf.py`` so that a transient network error no longer fails the whole docs build.
  * Fix Sphinx deprecation warnings: set ``language = 'en'`` instead of ``None``, drop the deprecated ``sphinx_rtd_theme.get_html_theme_path()`` call, and point the intersphinx SQLAlchemy/selenium inventories at ``https://`` URLs.
  * Pin the ``jsdoc`` version installed in CI to 4.0.4 and document that jsdoc 4.x is required (jsdoc 3.x crashes on Node.js 22+).
  * Update the GitHub Actions used by the workflow off of the deprecated Node 20 runtime.
  * ``plaid`` environment: wrap the raw SQL statements in ``test_plaidlink.py`` in ``sqlalchemy.text()``; SQLAlchemy 2.0 rejects bare textual SQL passed to ``Session.execute()``. This failure was masked in CI because the whole test class is marked ``xfail`` when ``CI=true``.
  * ``docker`` environment: allow ``docker_build.py`` to run from a Git worktree, where ``.git`` is a file pointing at the real Git directory rather than a directory itself.

1.6.0 (2026-02-14)
------------------

* **Standing Budget Plans** - Add optional one-to-one relationship from Project to Standing Budget, allowing users to associate a project with the standing budget used to fund it.

  * Add ``standing_budget_id`` nullable foreign key on ``projects`` table pointing to ``budgets``
  * Add standing budget dropdown to the project inline add form on ``/projects``
  * Add project edit modal for editing name, notes, standing budget, and active status
  * Display linked standing budget name in the projects DataTable
  * Database migration ``a1b2c3d4e5f6`` adds ``standing_budget_id`` column and foreign key constraint

1.5.1 (2026-02-11)
------------------

* Add HTTP API documentation page (``docs/source/http_api.rst``) documenting all Flask endpoints useful for external scripts and tools, including complete request/response data shapes and curl examples.
* Replace deprecated ``pkg_resources`` with ``importlib.resources`` in ``biweeklybudget/db.py`` for compatibility with setuptools >= 82.0 on Python 3.14.

1.5.0 (2026-01-19)
------------------

* `PR #309 <https://github.com/jantman/biweeklybudget/pull/309>`_ - **Add weekly and annual scheduled transaction types**

  * **Weekly (Day of Week)**: Transactions that recur every week on a specified day (e.g., every Monday). Weekly transactions appear twice per pay period since each weekday occurs exactly twice in a 14-day biweekly period.
  * **Annual**: Transactions that recur on a specific month and day each year (e.g., April 15th). For February 29th, the transaction is skipped in non-leap years.
  * Database migration adds ``day_of_week``, ``annual_month``, ``annual_day`` columns to ``scheduled_transactions`` table
  * Updated frontend modal with day-of-week dropdown and month/day inputs for new transaction types
  * Added type filter options for weekly and annual transactions

1.4.0 (2026-01-18)
------------------

This release upgrades the project from Python 3.10 to Python 3.14 with all dependencies updated to their latest compatible versions.

Breaking Changes
++++++++++++++++

* **Python 3.14 Required** - This release requires Python 3.14 or later. Python 3.10-3.13 are no longer supported.
* **SQLAlchemy 2.0** - Upgraded from SQLAlchemy 1.x to 2.0, which includes significant API changes.
* **Flask 3.x** - Upgraded from Flask 2.x to 3.x with updated JSON handling.

Dependency Updates
++++++++++++++++++

* Upgrade Python from 3.10 to 3.14
* Upgrade SQLAlchemy from 1.4.x to 2.0.45
* Upgrade Flask from 2.x to 3.1.2
* Upgrade Selenium from 3.x to 4.39.0
* Upgrade pytest-selenium from 2.x to 4.1.0
* Upgrade pytest-flask from 1.2.0 to 1.3.0
* Upgrade Sphinx from 1.8.5 to 8.1.3
* Upgrade sphinx-js from 3.x to 5.0.2
* Upgrade humanize from 3.x to 4.15.0
* Upgrade gunicorn from 19.7.1 to 22.0.0
* Upgrade all other dependencies to latest compatible versions

SQLAlchemy 2.0 Compatibility
++++++++++++++++++++++++++++

* Add monkey-patch for ``datatables`` package to fix ``query.join()`` calls that now require relationship attributes instead of string names
* Add explicit ``session.add()`` call in ``Transaction.set_budgets()`` as SQLAlchemy 2.0 no longer auto-adds objects via relationship cascade
* Update all query patterns for SQLAlchemy 2.0 compatibility

Flask 3.x Compatibility
+++++++++++++++++++++++

* Change ``request.get_json()`` to ``request.get_json(silent=True)`` in form handlers to handle non-JSON requests gracefully
* Update JSON provider from ``json_encoder`` to ``json_provider_class`` for Flask 3.x

Selenium 4.x Compatibility
++++++++++++++++++++++++++

* Remove deprecated ``desired_capabilities`` parameter from WebDriver initialization
* Update to use ``ChromeOptions`` for all browser configuration
* Set logging preferences via ``set_capability('goog:loggingPrefs', ...)`` instead of ``desired_capabilities``

Testing Improvements
++++++++++++++++++++

* Add ``wait_for_datatable_rows()`` helper method to AcceptanceHelper for waiting on DataTables client-side filtering
* Add retry logic for DataTable cell population timing issues in Docker tests
* Fix pytest-flask LiveServer fixture for Python 3.14 multiprocessing (set start method to 'fork')
* Pin alembic-verify to 0.1.4 and sqlalchemy-diff to 0.1.5 for compatibility
* Update test assertions for humanize 4.15.0 decimal formatting (``intword`` now formats with 1 decimal place)

Docker Test Infrastructure
++++++++++++++++++++++++++

* Update gunicorn from 19.7.1 to 22.0.0 for Python 3.14 compatibility
* Fix ``_container_ip()`` method to handle new Docker API structure where IP addresses are in Networks dict
* Add ``SETTINGS_MODULE`` and ``BIWEEKLYBUDGET_TEST_TIMESTAMP`` environment variables to Docker container
* Add ``BIWEEKLYBUDGET_TEST_BASE_URL`` to tox passenv for proper Docker test execution
* Fix ``testflask`` fixture to yield ``None`` when running against external URL

Documentation
+++++++++++++

* Update Sphinx configuration for 8.1.3 compatibility
* Update sphinx-js integration for 5.0.2 compatibility
* Regenerate JavaScript documentation with updated tooling

1.3.0 (2026-01-16)
------------------

Main Feature
++++++++++++

* **Add sales_tax field to ScheduledTransaction** - ScheduledTransaction now tracks sales tax separately, allowing scheduled transactions to store sales tax values that are automatically transferred to Transactions when converted. This provides consistency with the existing sales tax tracking on Transactions and enables better budgeting for purchases that include sales tax.

Infrastructure and CI Improvements
+++++++++++++++++++++++++++++++++++

* Replace Codecov with custom PR coverage comments in GitHub Actions
* Update GitHub Actions workflow to only run CI on PRs and master branch pushes
* Add NewRelic APM agent support (automatically initialized if ``NEW_RELIC_LICENSE_KEY`` environment variable is set)
* Improve test artifact collection and GitHub Actions upload behavior
* Enhance Chrome stability options for CI test environments

Testing Improvements
++++++++++++++++++++

* Fix Plaid Link integration tests for updated Plaid UI using ActionChains for custom input fields
* Mark Plaid Link tests as xfail in CI due to headless Chrome incompatibility with Plaid's JavaScript flow
* Improve test reliability with better handling of Plaid modal flows and success messages
* Fix acceptance test timeouts and race conditions
* Update sample data to include sales_tax values for comprehensive testing

Bug Fixes and Maintenance
++++++++++++++++++++++++++

* Fix mysqldump SSL flag differences between MySQL and MariaDB in test helpers
* Fix pycodestyle line length violations (increased max line length to 100)
* Update Sphinx from 1.5.5 to 1.8.5 to fix documentation build
* Fix documentation link checker exclusions for sites that block automated requests (Wikipedia, NIST NVD, Flaticon)
* Update Hashicorp Vault documentation URLs from www.vaultproject.io to developer.hashicorp.com/vault
* Update copyright years to 2016-2024
* Bump newrelic to version 11.2.0

Documentation
+++++++++++++

* Add comprehensive ``CLAUDE.md`` file with development guidance for AI coding assistants
* Add ``docs/features/`` directory structure for feature planning and tracking
* Add detailed database migration workflows and troubleshooting guidance to development documentation
* Document the importance of setting up test database before model changes when using Alembic autogenerate
* Add Claude Code configuration file (``.claude/settings.json``) with approved command permissions

Database Migration
++++++++++++++++++

* Migration ``1bb9e6a1c07c_add_scheduledtransaction_sales_tax_field`` adds the ``sales_tax`` column (Numeric(10,4), nullable=False, default=0.0) to the ``scheduled_transactions`` table

1.2.0 (2024-01-25)
------------------

* Add tracking of sales tax paid on each transaction.
* Minor build fixes to get this building again.

1.1.1 (2022-12-30)
------------------

* Docker build - don't include ``-dirty`` in version/tag when building in GHA
* Document how to change Plaid environments
* GHA - Push built Docker images to Docker Hub, for builds of master branch
* Document triggering a Plaid update via the ``/plaid-update`` endpoint.
* Change ``/plaid-update`` endpoint argument name from ``account_ids`` to ``item_ids``.
* Add ``num_days`` parameter support to ``/plaid-update`` endpoint.

1.1.0 (2022-12-29)
------------------

Breaking Changes
++++++++++++++++

* Support for Python versions prior to 3.8 have been dropped; Docker image and testing is now done against Python 3.10.
* Valid values for the ``PLAID_ENV`` setting / environment variable are now the strings "Production", "Development", or "Sandbox" to match the attribute names of ``plaid.configuration.Environment``. Previously these were lower-case instead of capitalized.
* The ``PLAID_PUBLIC_KEY`` setting / environment variable has been removed.
* OFX support is now **deprecated**; going forward, only Plaid will be supported.

All Changes
+++++++++++

* **Drop Python 2 Support and Python 3.5 Support** - biweeklybudget no longer supports Python 2 (2.7) or Python 3.5. Python versions 3.6-3.8 are tested, and development is now done on 3.8.
* `Issue #201 <https://github.com/jantman/biweeklybudget/issues/201>`_ - Fix **major** bug in calculation of "Remaining" amount for pay periods, when one or more periodic budgets have a greater amount spent than allocated and a $0 starting balance. In that case, we were using the allocated amount instead of the spent amount (i.e. if we had a periodic budget with a $0 starting balance and a $2 ScheduledTransaction, and converted that ScheduledTransaction to a $1000 Transaction, the overall PayPeriod remaining amount would be based on the $2 not the $1000).
* Add testing for Python 3.7 and 3.8, and make 3.8 the default for tests and tox environments.
* TravisCI updates for Python 3.7 and 3.8.
* Switch base image for Docker from ``python:3.6.4-alpine3.7`` to ``python:3.8.1-alpine3.11``.
* `Issue #198 <https://github.com/jantman/biweeklybudget/issues/198>`_ - Fix broken method of retrieving current US Prime Rate. Previously we used marketwatch.com for this but they've introduced javascript-based bot protection on their site (which is ironic since we were reading a value from the page's ``meta`` tags, which are specifically intended to be read by machines). Switch to using wsj.com instead and (ugh) parsing a HTML table. This *will* break when the format of the table changes. As previously, we cache this value in the DB for 48 hours in order to be a good citizen.
* `Issue #197 <https://github.com/jantman/biweeklybudget/issues/197>`_ - Add notification for case where balance of all budget-funding accounts is *more* than sum of standing budgets, current payperiod remaining, and unreconciled. This is the opposite of the similar notification that already exists, intended to detect if there is money in accounts not accounted for in the budgets.
* `Issue #196 <https://github.com/jantman/biweeklybudget/issues/196>`_ - Don't include inactive budgets in Budget select elements on Transaction Modal form, unless it's an existing Transaction using that budget.
* `Issue #204 <https://github.com/jantman/biweeklybudget/issues/204>`_ - Add support for account transfer between non-Credit accounts.
* Many dependency updates:

  * Upgrade SQLAlchemy from 1.2.0 to 1.2.11 for `python 3 bug fix (4291) <https://docs.sqlalchemy.org/en/latest/changelog/changelog_12.html#change-2cca6c216347ab83d04c766452b48c1a>`_.
  * Upgrade SQLAlchemy from 1.2.11 to 1.3.13 for `CVE-2019-7548 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-7548>`_ and `CVE-2019-7164 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-7164>`_.
  * Upgrade Flask from 0.12.2 to 1.0.2 for `CVE-2018-1000656 <https://nvd.nist.gov/vuln/detail/CVE-2018-1000656>`_.
  * Upgrade cryptography from 2.1.4 to 2.3.1 for `CVE-2018-10903 <https://nvd.nist.gov/vuln/detail/CVE-2018-10903>`_.
  * Upgrade Jinja2 from 2.10 to 2.10.3 for `CVE-2019-10906 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-10906>`_.
  * Upgrade to latest version for all dependencies.

* Remove ``convert_unicode`` argument from SQLAlchemy DB engine arguments per SQLAlchemy 1.3 upgrade guide / `SQLAlchemy #4393 <https://github.com/sqlalchemy/sqlalchemy/issues/4393>`_.
* Numerous updates to fix ``tox`` tests.
* Implement transaction downloading via `Plaid <https://plaid.com/>`__.
* Switch tests from deprecated ``pep8`` / ``pytest-pep8`` packages to ``pycodestyle`` / ``pytest-pycodestyle``.
* Add optional ``VERSIONFINDER_DEBUG`` env var; set to ``true`` to enable logging for versionfinder / pip / git.
* Drop testing for Python 3.6; move default test environment to 3.9.
* Add ``git`` to Docker image.
* Move testing and runtime to Python 3.10, and get all test environments running successfully.
* Move CI from TravisCI to GitHub Actions and remove all traces of TravisCI.
* Add acceptance test coverage of the Plaid Link process.
* Updates for ``tox`` 4.0.6.
* Update Plaid API client to latest version

  * Valid values for the ``PLAID_ENV`` setting / environment variable are now the strings "Production", "Development", or "Sandbox" to match the attribute names of ``plaid.configuration.Environment``.
  * The ``PLAID_PUBLIC_KEY`` setting / environment variable has been removed.

1.0.0 (2018-07-07)
------------------

* Fix major logic error in Credit Card Payoff calculations; interest fees were ignored for the current month/statement, resulting in "Next Payment" values significantly lower than they should be. Fixed to use the last Interest Charge retrieved via OFX (or, if no interest charges present in OFX statements, prompt users to manually enter the last Interest Charge via a new modal that will create an OFXTransaction for it) as the interest amount on the first month/statement when calculating payoffs. This fix now returns Next Payment values that aren't identical to sample cards, but are significantly closer (within 1-2%).
* `Issue #105 <https://github.com/jantman/biweeklybudget/issues/105>`_ - Major refactor to the Transaction database model. This is transparent to users, but causes massive database and code changes. This is the first step in supporting Transaction splits between multiple budgets:

  * A new BudgetTransaction model has been added, which will support a one-to-many association between Transactions and Budgets. This model associates a Transaction with a Budget, and a currency amount counted against that Budget. This first step only supports a one-to-one relationship, but a forthcoming change will implement the one-to-many budget split for Transactions.
  * The database migration for this creates BudgetTransactions for every current Transaction, migrating data to the new format.
  * The ``budget_id`` attribute and ``budget`` relationship of the Transaction model has been removed, as that information is now in the related BudgetTransactions.
  * A new ``planned_budget_id`` attribute (and ``planned_budget`` relationship) has been added to the Transaction model. For Transactions that were created from ScheduledTransactions, this attribute/relationship stores the original planned budget (distinct from the actual budget now stored in BudgetTransactions).
  * The Transaction model now has a ``budget_transactions`` back-populated property, containing a list of all associated BudgetTransactions.
  * The Transaction model now has a ``set_budget_amounts()`` method which takes a single dict mapping either integer Budget IDs or Budget objects, to the Decimal amount of the Transaction allocated to that Budget. While the underlying API supports an arbitrary number of budgets, the UI and codebase currently only supports one.
  * The Transaction constructor now accepts a ``budget_amounts`` keyword argument that passes its value through to ``set_budget_amounts()``, for ease of creating Transactions in one call.
  * ``Transaction.actual_amount`` is no longer an attribute stored in the database, but now a hybrid property (read-only) generated from the sum of amounts of all related BudgetTransactions.
  * Add support to serialize property values of models, in addition to attributes.

* Relatively major and sweeping code refactors to support the above.
* Switch tests from using deprecated pytest-capturelog to using pytest built-in log capturing.
* Miscellaneous fixes to unit and acceptance tests, and docs build.
* Finish converting *all* code, including tests and sample data, from using floats to Decimals.
* Acceptance test fix so that pytest-selenium can take full page screenshots with Chromedriver.
* `PR #180 <https://github.com/jantman/biweeklybudget/pull/180>`_ - Acceptance test fix so that the testflask LiveServer fixture captures server logs, and includes them in test HTML reports (this generates a temporary file per-test-run outside of pytest's control).
* Fix bug found where simultaneously editing the Amount and Budget of an existing Transaction against a Standing Budget would result in incorrect changes to the balances of the Budgets.
* Add a new ``migrations`` tox environment that automatically tests all database migrations (forward and reverse) and also validates that the database schema created from the migrations matches the one created from the models.
* Add support for writing tests of data manipulation during database migrations, and write tests for the migration in for Issue 105, above.
* Add support for ``BIWEEKLYBUDGET_LOG_FILE`` environment variable to cause Flask application logs to go to a file *in addition to* STDOUT.
* Add support for ``SQL_POOL_PRE_PING`` environment variable to enable SQLAlchemy ``pool_pre_ping`` feature (see `Disconnect Handling - Pessimistic <http://docs.sqlalchemy.org/en/latest/core/pooling.html#pool-disconnects-pessimistic>`_) for resource-constrained systems.
* Modify acceptance tests to retry up to 3 times, 3 seconds apart, if a ConnectionError (or subclass thereof) is raised when constructing the Selenium driver instance. This is a workaround for intermittent ConnectionResetErrors in TravisCI.
* `Issue #177 <https://github.com/jantman/biweeklybudget/issues/177>`_

  * Add SQL query timing support via ``SQL_QUERY_PROFILE`` environment variable.
  * When running under ``flask rundev``, append the number of milliseconds taken to serve the request to the werkzeug access log.
  * When running under Docker/Gunicorn, append the decimal number of seconds taken to serve the request to the Gunicorn access log.

* `Issue #184 <https://github.com/jantman/biweeklybudget/issues/184>`_ - Redact database password from ``/help`` view, and change ``/help`` view to show Version containing git commit hash for pre-release/development Docker builds.
* `Issue #183 <https://github.com/jantman/biweeklybudget/issues/183>`_

  * Add UI link to ignore reconciling an OFXTransaction if there will not be a matching Transaction.
  * Remove default values for the ``Account`` model's ``re_`` fields in preparation for actually using them.
  * Replace the ``Account`` model's ``re_fee`` field with separate ``re_late_fee`` and ``re_other_fee`` fields.
  * Add UI support for specifying Interest Charge, Interest Paid, Payment, Late Fee, and Other Fee regexes on each account.
  * Add DB event handler on new or changed OFXTransaction, to set ``is_*`` fields according to Account ``re_*`` fields.
  * Add DB event handler on change to Account model ``re_*`` fields, that triggers ``OFXTransaction.update_is_fields()`` to recalculate using the new regex.
  * Change ``OFXTransaction.unreconciled`` to filter out OFXTransactions with any of the ``is_*`` set to True.

* Upgrade chromedriver in TravisCI builds from 2.33 to 2.36, to fix failing acceptance tests caused by Ubuntu upgrade from Chrome 64 to 65.
* Fix bug in ``/budgets`` view where "Spending By Budget, Per Calendar Month" chart was showing only inactive budgets instead of only active budgets.
* `Issue #178 <https://github.com/jantman/biweeklybudget/issues/178>`_ - UI support for splitting Transactions between multiple Budgets.
* Have frontend forms submit as JSON POST instead of urlencoded.
* Properly capture Chrome console logs during acceptance tests.
* Bump ``versionfinder`` requirement version to 0.1.3 to work with pip 9.0.2.
* On help view, show long version string if we have it.
* `Issue #177 <https://github.com/jantman/biweeklybudget/issues/177>`_ - Fix bug in ``flask rundev`` logging.
* Many workarounds for flaky acceptance tests, including some for the selenium/Chrome "Element is not clickable at point... Other element would receive the click" error.
* ``biweeklybudget.screenscraper.ScreenScraper`` - Save webdriver and browser logs on failure, and set Chrome to capture all logs.
* ``biweeklybudget.screenscraper.ScreenScraper`` - Add option to explicitly set a User-Agent on Chrome or PhantomJS.
* `Issue #192 <https://github.com/jantman/biweeklybudget/issues/192>`_ - Fix bug where the ``is_`` fields weren't set on OFXTransactions when created via ofxgetter remote API.
* ``ofxgetter`` - add support to list all accounts at the Institution of one account
* ``ofxgetter`` - add ability to specify how many days of data to retrieve

0.7.1 (2018-01-10)
------------------

* `Issue #170 <https://github.com/jantman/biweeklybudget/issues/170>`_ - Upgrade **all** python dependencies to their latest versions.
* `Issue #171 <https://github.com/jantman/biweeklybudget/issues/171>`_ - Upgrade Docker base image from ``python:3.6.3-alpine3.4`` to ``python:3.6.4-alpine3.7``.
* `Issue #157 <https://github.com/jantman/biweeklybudget/issues/157>`_ - Remove PhantomJS from Docker image, as it's broken and shouldn't be needed.
* Switch TravisCI builds from Docker (``sudo: false``) to VM (``sudo: enabled``) infrastructure.

0.7.0 (2018-01-07)
------------------

**This version has a remote OFX upload incompatibility. See below.**

* `Issue #156 <https://github.com/jantman/biweeklybudget/issues/156>`_ - Add headless chrome support to ``screenscraper.py``.
* Remove ``pluggy`` transient dependency from requirements.txt; was breaking builds.
* Following pytest, drop testing of and support for Python 3.3.
* `Issue #159 <https://github.com/jantman/biweeklybudget/issues/159>`_ - Implement internationalization of volume and distance units for Fuel Log pages. This change introduces five new settings: ``FUEL_VOLUME_UNIT``, ``FUEL_VOLUME_ABBREVIATION``, ``DISTANCE_UNIT``, ``DISTANCE_UNIT_ABBREVIATION`` and ``FUEL_ECO_ABBREVIATION``.
* `Issue #154 <https://github.com/jantman/biweeklybudget/issues/154>`_ - Fix documentation errors on the Getting Started page, "Running ofxgetter in Docker" section.
* `Issue #152 <https://github.com/jantman/biweeklybudget/issues/152>`_ - Fix for bug where new Transactions could be entered against inactive budgets. Ensure that existing transactions against inactive budgets can still be edited, but existing transactions cannot be changed to an inactive budget.
* `Issue #161 <https://github.com/jantman/biweeklybudget/issues/161>`_ - Fix bug where Transactions against inactive budgets weren't counted towards payperiod overall or per-budget totals.
* `Issue #163 <https://github.com/jantman/biweeklybudget/issues/163>`_ - Include next payment amount on Credit Payoffs view.
* `Issue #84 <https://github.com/jantman/biweeklybudget/issues/84>`_ - Remove vendored-in ``ofxparse`` package now that `my PR #127 <https://github.com/jseutter/ofxparse/pull/127>`_ has been merged and released on PyPI. **Important note:** The version of ofxparse is changed in this release. If you are using ``ofxgetter -r`` (remote API mode), the versions of ofxparse (and therefore biweeklybudget/ofxgetter) must match between the client and server.
* `Issue #165 <https://github.com/jantman/biweeklybudget/issues/165>`_ - Remove vendored-in ``wishlist`` package now that `my PR #8 <https://github.com/Jaymon/wishlist/pull/8>`_ has been merged and released on PyPI.
* `Issue #155 <https://github.com/jantman/biweeklybudget/issues/155>`_ - Refactor ofxgetter to fix bug where ``SETTINGS_MODULE`` was still required even if running remotely.

0.6.0 (2017-11-11)
------------------

* `PR #140 <https://github.com/jantman/biweeklybudget/issues/140>`_ - Support user-configurable currencies and currency formatting.
  This isn't all-out localization, but adds ``CURRENCY_CODE`` and ``LOCALE_NAME`` configuration settings to control the currency symbol
  and formatting used in the user interface and logs.
* `PR #141 <https://github.com/jantman/biweeklybudget/pull/141>`_ - Switch acceptance tests from PhantomJS to headless Chrome.
* Switch docs build screenshot script to use headless Chrome instead of PhantomJS.
* `Issue #142 <https://github.com/jantman/biweeklybudget/issues/142>`_ - Speed up acceptance tests. The acceptance tests recently crossed the 20-minute barrier, which is unacceptable. This makes some improvements to the tests, mainly around combining classes that can be combined and also using mysql/mysqldump to refresh the DB, instead of refreshing and recreating via the ORM. That offers a approximately 50-90% speed improvement for each of the 43 refreshes. Unfortunately, it seems that the majority of time is taken up by pytest-selenium; see Issue 142 for further information.
* `Issue #125 <https://github.com/jantman/biweeklybudget/issues/125>`_ - Switch Docker image base from ``python:3.6.1`` (Debian) to ``python:3.6.3-alpine3.4`` (Alpine Linux); drops final image size from 876MB to 274MB. (*Note:* Alpine linux does not have ``/bin/bash``.)
* `Issue #138 <https://github.com/jantman/biweeklybudget/issues/138>`_ - Improvements to build process

  * Run acceptance tests against the built Docker container during runs of the ``docker`` tox environment / ``tests/docker_build.py``.
  * Reminder to sign git release tags
  * Add ``dev/release.py`` script to handle GitHub releases.

* `Issue #139 <https://github.com/jantman/biweeklybudget/issues/139>`_ - Add field to Budget model to allow omitting specific budgets from spending graphs (the graphs on the Budgets view).

0.5.0 (2017-10-28)
------------------

**This release includes database migrations.**

* `Issue #118 <https://github.com/jantman/biweeklybudget/issues/118>`_ - PR to fix bugs in the
  `wishlist <https://github.com/Jaymon/wishlist>`_ dependency package, and vendor that patched
  version in under ``biweeklybudget.vendored.wishlist``.
* `Issue #113 <https://github.com/jantman/biweeklybudget/issues/113>`_ - vendor in other
  git requirements (ofxclient and ofxparse) that seem unmaintained or inactive, so we can install via ``pip``.
* `Issue #115 <https://github.com/jantman/biweeklybudget/issues/115>`_ - In Transactions view, add ability to filter by budget.
* Change ``BiweeklyPayPeriod`` class to never convert to floats (always use decimal.Decimal types).
* `Issue #124 <https://github.com/jantman/biweeklybudget/issues/124>`_ - Major changes to the ``ofxgetter`` and ``ofxbackfiller`` console scripts; centralize all database access in them to the new ``biweeklybudget.ofxapi.local.OfxApiLocal`` class and allow these scripts to function remotely, interacting with the ReST API instead of requiring direct database access.
* `Issue #123 <https://github.com/jantman/biweeklybudget/issues/123>`_ - Modify the Credit Payoffs view to allow removal of Increase and Onetime Payment settings lines.
* `Issue #131 <https://github.com/jantman/biweeklybudget/issues/131>`_ - Add better example data for screenshots.
* `Issue #117 <https://github.com/jantman/biweeklybudget/issues/117>`_ and `#133 <https://github.com/jantman/biweeklybudget/issues/133>`_ - Implement and then revert out a failed attempt at automatic balancing of budgets in the previous pay period.
* `Issue #114 <https://github.com/jantman/biweeklybudget/issues/114>`_

  * Add ``transfer_id`` field and ``transfer`` relationship to Transaction model, to link the halves of budget transfer transactions in the database. The alembic migration for this release iterates all Transactions in the database, and populates these links based on inferences of the description, date, account_id and notes fields of sequential pairs of Transactions. (Note: this migration would likely miss some links if two transfers were created simultaneously, and ended up with the Transaction IDs interleaved).
  * Identify transfer Transactions on the Edit Transaction modal, and provide link to the matching Transaction.
  * Add graph of spending by budget to Budgets view.
* `Issue #133 <https://github.com/jantman/biweeklybudget/issues/133>`_ - Change BiweeklyPayPeriod model to only use actual spent amount when creating remaining amount on payperiods in the past. Previously, all pay periods calculated the overall "remaining" amount as income minus the greater of ``allocated`` or ``spent``; this resulted in pay periods in the past still including allocated-but-not-spent amounts counted against "remaining".

0.4.0 (2017-08-22)
------------------

* Have ``ofxgetter`` enable ofxclient logging when running at DEBUG level (``-vv``).
* Bump ofxclient requirement to my `vanguard-fix <https://github.com/jantman/ofxclient/tree/vanguard-fix>`_ branch
  for `PR #47 <https://github.com/captin411/ofxclient/pull/47>`_.
* `Issue #101 <https://github.com/jantman/biweeklybudget/issues/101>`_ - Fix static example amounts on ``/projects`` view.
* `Issue #103 <https://github.com/jantman/biweeklybudget/issues/103>`_ - Show most recent MPG in notification box after adding fuel fill.
* `Issue #97 <https://github.com/jantman/biweeklybudget/issues/97>`_ - Fix integration tests that are date-specific and break on certain dates (run all integration tests as if it were a fixed date).
* `Issue #104 <https://github.com/jantman/biweeklybudget/issues/104>`_ - Relatively major changes to add calculation of Credit account payoff times and amounts.
* `Issue #107 <https://github.com/jantman/biweeklybudget/issues/107>`_ - Fix bug where Budget Transfer modal dialog would always default to current date, even when viewing past or future pay periods.
* `Issue #48 <https://github.com/jantman/biweeklybudget/issues/48>`_ - UI support for adding and editing accounts.

0.3.0 (2017-07-09)
------------------

* `Issue #88 <https://github.com/jantman/biweeklybudget/issues/88>`_ - Add tracking of cost for Projects and Bills of Materials (BoM) for them.
* Add script / entry point to sync Amazon Wishlist with a Project.
* `Issue #74 <https://github.com/jantman/biweeklybudget/issues/74>`_ - Another attempt at working over-balance notification.

0.2.0 (2017-07-02)
------------------

* Fix ``/pay_period_for`` redirect to be a 302 instead of 301, add redirect logging, remove some old debug logging from that view.
* Fix logging exception in db_event_handlers on initial data load.
* Switch ofxparse requirement to use upstream repo now that https://github.com/jseutter/ofxparse/pull/127 is merged.
* `Issue #83 <https://github.com/jantman/biweeklybudget/issues/83>`_ - Fix 500 error preventing display of balance chart on ``/`` view when an account has a None ledger balance.
* `Issue #86 <https://github.com/jantman/biweeklybudget/issues/86>`_ - Allow budget transfers to periodic budgets.
* `Issue #74 <https://github.com/jantman/biweeklybudget/issues/74>`_ - Warning notification for low balance should take current pay period's overall allocated sum, minus reconciled transactions, into account.
* Fix some template bugs that were causing HTML to be escaped into plaintext.
* `Issue #15 <https://github.com/jantman/biweeklybudget/issues/15>`_ - Add pay period totals table to index page.
* Refactor form generation in UI to use new FormBuilder javascript class (DRY).
* Fix date-sensitive acceptance test.
* `Issue #87 <https://github.com/jantman/biweeklybudget/issues/87>`_ - Add fuel log / fuel economy tracking.

0.1.2 (2017-05-28)
------------------

* Minor fix to instructions printed after release build in ``biweeklybudget/tests/docker_build.py``
* `Issue #61 <https://github.com/jantman/biweeklybudget/issues/61>`_ - Document running ``ofxgetter`` in the Docker container.
* fix ReconcileRule repr for uncommited (id is None)
* `Issue #67 <https://github.com/jantman/biweeklybudget/issues/67>`_ - ofxgetter logging -
  suppress DB and Alembic logging at INFO and above; log number of inserted  and updated transactions.
* `Issue #71 <https://github.com/jantman/biweeklybudget/issues/71>`_ - Fix display text next to prev/curr/next periods on ``/payperiod/YYYY-mm-dd`` view; add 6 more future pay periods to the ``/payperiods`` table.
* `Issue #72 <https://github.com/jantman/biweeklybudget/issues/72>`_ - Add a built-in method for transferring money from periodic (per-pay-period) to standing budgets; add budget Transfer buttons on Budgets and Pay Period views.
* `Issue #75 <https://github.com/jantman/biweeklybudget/issues/75>`_ - Add link on payperiod views to skip a ScheduledTransaction instance this period.
* `Issue #57 <https://github.com/jantman/biweeklybudget/issues/57>`_ - Ignore future transactions from unreconciled transactions list.
* Transaction model - fix default for ``date`` field to actually be just a date; previously, Transactions with ``date`` left as default would attempt to put a full datetime into a date column, and throw a data truncation warning.
* Transaction model - Fix ``__repr__`` to not throw exception on un-persisted objects.
* When adding or updating the ``actual_amount`` of a Transaction against a Standing Budget, update the ``current_balance`` of the budget.
* Fix ordering of Transactions table on Pay Period view, to properly sort by date and then amount.
* Numerous fixes to date-sensitive acceptance tests.
* `Issue #79 <https://github.com/jantman/biweeklybudget/issues/79>`_ - Update ``/pay_period_for`` view to redirect to current pay period when called with no query parameters; add bookmarkable link to current pay period to Pay Periods view.

0.1.1 (2017-05-20)
------------------

* Improve ofxgetter/ofxupdater error handling; catch OFX files with error messages in them.
* `Issue #62 <https://github.com/jantman/biweeklybudget/issues/62>`_ - Fix phantomjs in Docker image.
  * Allow docker image tests to run against an existing image, defined by ``DOCKER_TEST_TAG``.
  * Retry MySQL DB creation during Docker tests until it succeeds, or fails 10 times.
  * Add testing of PhantomJS in Docker image testing; check version and that it actually works (GET a page).
  * More reliable stopping and removing of Docker containers during Docker image tests.
* `Issue #63 <https://github.com/jantman/biweeklybudget/issues/63>`_ - Enable gunicorn request logging in Docker container.
* Switch to my fork of ofxclient in requirements.txt, to pull in `ofxclient PR #41 <https://github.com/captin411/ofxclient/pull/41>`_
* `Issue #64 <https://github.com/jantman/biweeklybudget/issues/64>`_ - Fix duplicate/multiple on click event handlers in UI that were causing duplicate transactions.

0.1.0 (2017-05-07)
------------------

* Initial Release
