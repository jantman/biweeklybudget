# Feature Specification: Correct the Unallocated-Funds Notification

**Feature Branch**: `robot-army/issue-320-unallocated-funds-notification-reports`

**Created**: 2026-09-07

**Status**: Draft

**Input**: GitHub issue [#320](https://github.com/jantman/biweeklybudget/issues/320) ("Unallocated-funds notification reports wrong numbers: credit balances, pseudo-transactions, and a mislabeled pay-period figure"), which folds in the closed duplicate [#209](https://github.com/jantman/biweeklybudget/issues/209) and relates to [#210](https://github.com/jantman/biweeklybudget/issues/210), [#319](https://github.com/jantman/biweeklybudget/issues/319), and [#321](https://github.com/jantman/biweeklybudget/issues/321).

## Overview

Every page of the application carries a banner comparing the money the person actually has
available against the money they have already committed. It states whether the two are equal
and, when they are not, by how much and to what the commitments break down.

That banner is the single at-a-glance answer to "do I have unallocated money, and how much?".
Today it answers wrongly, and the error is not random: it is systematically biased toward
reporting a surplus that does not exist, by an amount equal to the outstanding credit-card
balance. For a person who puts most spending on cards and pays them off each period, that is
one to two pay periods of spending — a large, permanent, misleading "you have more than you've
allocated" message. A banner that is always wrong in the same direction is worse than no
banner: it trains the reader to ignore the one signal that would tell them they had
over-committed.

Separately, one of the figures the banner breaks the total down into is labelled with a word
that means something different everywhere else in the application, and is hyperlinked to a page
that reports a different number under that same word. The two quantities can differ by
thousands of dollars and can even have opposite signs at the same moment.

### The comparison, stated correctly

The banner compares **funds available** against **funds committed**.

**Funds available** is the money the person could spend right now if they stopped spending:
the combined balance of the accounts that fund the budget (checking, savings, cash), *less
what they already owe on their credit accounts*. Money sitting in checking that is already
spoken for by a card statement is not available. Today the second term is simply absent.

**Funds committed** is unchanged in quantity and is the sum of three things: the balances
remaining in standing budgets, the amount allocated but not yet spent in the current pay
period, and the net of transactions that have been entered but not yet reconciled against the
bank.

### What is already fixed

The issue's second defect — that "pseudo-transactions" entered to cancel the budget impact of a
credit-card payment were counted as real money movement in the unreconciled figure — has
already been resolved on `master` by the work for issues #210 and #319. A transaction can now
be designated as having no budget impact, and payments toward a credit account carry that
designation implicitly; the unreconciled sum already skips both. This specification therefore
does **not** re-implement that fix. It does require that the behaviour be pinned by a test that
exercises it through the notification, so that the correction cannot silently regress, since
until now nothing tied that model-level behaviour to the banner that depends on it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The banner accounts for money owed on credit accounts (Priority: P1)

A person pays for nearly everything with a credit card and clears the card in full each pay
period. Each charge is budgeted on the day it is made. The cash to settle the card is still in
their checking account, waiting for the statement. They open any page of the application.

Today the banner tells them they have well over a thousand dollars more than they have
allocated, every single day, because the card balance appears nowhere in the comparison. After
this change the banner subtracts what they owe on their active credit accounts from the funds
available, and reports the true difference — which, when their budgeting is in order, is zero
or close to it.

**Why this priority**: This is the defect that makes the banner unusable. It is present
continuously, it is large, and it is in the direction that suppresses a real warning. The other
two items are correctness and clarity improvements on a banner that this story makes
trustworthy in the first place.

**Independent Test**: With budget-funding accounts holding a known combined balance and active
credit accounts carrying a known combined amount owed, confirm the funds-available figure the
banner reports equals the funding-account balance minus the amount owed, and that the banner's
surplus/shortfall verdict is computed from that reduced figure.

**Acceptance Scenarios**:

1. **Given** budget-funding accounts holding $3,000 combined and one active credit account with
   $1,000 owed, **When** the banner is displayed, **Then** the funds-available figure it
   reports is $2,000, not $3,000.
2. **Given** funds available of $2,000 after subtracting credit balances and committed funds
   totalling $2,000, **When** the banner is displayed, **Then** no surplus or shortfall banner
   appears at all, where previously a $1,000 surplus was reported.
3. **Given** the same accounts but with the credit account *inactive*, **When** the banner is
   displayed, **Then** that account's balance is not subtracted, matching how inactive accounts
   are excluded everywhere else.
4. **Given** an active credit account for which no balance has ever been recorded, **When** the
   banner is displayed, **Then** it is treated as nothing owed and the banner is still produced
   rather than failing.
5. **Given** the amount owed on credit accounts exceeds the funding-account balances, **When**
   the banner is displayed, **Then** funds available is reported as a negative figure and the
   shortfall banner is shown.

---

### User Story 2 - The banner names the quantities it reports (Priority: P2)

A person reads the banner, sees a figure labelled "current pay period remaining", clicks the
link to the pay period, and finds a different number under the heading "remaining". They cannot
tell which is wrong, or whether the banner is trustworthy at all.

After this change, the figure is labelled for what it actually is — the amount allocated in the
current pay period that has not yet been spent — and the banner as a whole reads as a
comparison of available funds against committed funds, with the amount owed on credit accounts
shown as part of that breakdown so the reader can see where the number came from.

**Why this priority**: The quantity is already correct; only the naming is wrong. It costs the
reader confidence rather than money. It ships alongside P1 because P1 changes the same sentence
and re-labelling it separately would mean writing the sentence twice.

**Independent Test**: Display the banner and confirm no figure in it is described by a word
that names a different quantity elsewhere in the application, and that every figure shown is
identified by what it measures.

**Acceptance Scenarios**:

1. **Given** the banner is displayed, **When** its text is read, **Then** the pay-period figure
   is described as allocated-but-unspent for the current pay period and is not called
   "remaining".
2. **Given** the banner is displayed, **When** its text is read, **Then** the amount subtracted
   for credit accounts is shown as a named part of the breakdown, linked to the accounts view.
3. **Given** the banner is displayed, **When** its links are followed, **Then** each link leads
   to a view that reports the figure it was attached to, under a compatible name.

---

### User Story 3 - Transactions with no cash impact stay out of the comparison (Priority: P3)

A person records a credit-card payment from checking, together with the offsetting entry that
keeps it from being charged twice against a budget. Between entering it and reconciling it days
later, the banner must not shift by the size of the payment.

**Why this priority**: The mechanism for this already exists on `master`; this story is
verification, not construction. It is nonetheless in scope because nothing currently connects
that mechanism to the banner, and a regression there would reintroduce a multi-thousand-dollar
error silently.

**Independent Test**: With unreconciled transactions in a funding account, some of which carry
the no-budget-impact designation or are payments toward a credit account, confirm the banner's
unreconciled figure counts only the transactions that represent real cash movement.

**Acceptance Scenarios**:

1. **Given** a funding account with $250 of ordinary unreconciled transactions and a $2,000
   unreconciled transaction marked as having no budget impact, **When** the banner is displayed,
   **Then** the unreconciled figure it reports is $250.
2. **Given** a funding account with a $2,000 unreconciled transaction that is a payment toward
   an active credit account, **When** the banner is displayed, **Then** that payment is not
   included in the unreconciled figure.
3. **Given** the transactions above, **When** the reconcile view is displayed, **Then** those
   transactions still appear there and remain reconcilable — excluding them from the banner
   must not hide them from reconciliation.

---

### Edge Cases

- **No credit accounts at all**: the amount owed is zero and the banner behaves exactly as it
  does today. Existing users without credit accounts must see no change in the numbers.
- **A credit account with a positive balance** (overpaid, or carrying a statement credit): the
  balance is added to funds available rather than subtracted, since that money genuinely is
  available. The rule is uniform — the recorded balance of every active credit account is
  applied to funds available with its own sign — rather than special-cased.
- **A credit account with no recorded balance**: contributes nothing. It must not cause the
  banner to fail or to be omitted, matching how funding accounts without balances are already
  handled.
- **Funds available and funds committed exactly equal**: no banner is shown, as today. This
  becomes materially more likely once credit balances are subtracted, which is the point.
- **Funds available negative**: the shortfall banner is shown with a negative available figure,
  formatted as currency the way negative figures are formatted elsewhere.
- **Amounts that are zero**: a zero credit-owed figure still appears in the breakdown rather
  than being suppressed, so the breakdown always sums visibly to the stated total.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The funds-available figure in the notification MUST be the combined recorded
  balance of all active budget-funding accounts, adjusted by the combined recorded balance of
  all active credit accounts, such that an amount owed on a credit account reduces the funds
  available by that amount.
- **FR-002**: Only accounts marked active MUST contribute to either term of the funds-available
  figure. Inactive accounts of any type MUST be excluded.
- **FR-003**: An active credit account with no recorded balance MUST contribute zero to the
  funds-available figure, and MUST NOT prevent the notification from being produced.
- **FR-004**: The funds-committed total MUST remain the sum of standing budget balances, the
  current pay period's allocated-but-unspent amount, and the unreconciled transaction sum. The
  quantities MUST NOT change.
- **FR-005**: The notification MUST report a shortfall when funds available is less than funds
  committed, a surplus when it is greater, and no notification when the two are equal —
  preserving today's three-way behaviour and the existing visual severity of each case.
- **FR-006**: The notification text MUST describe the pay-period figure as the amount allocated
  but not yet spent in the current pay period, and MUST NOT describe it as "remaining".
- **FR-007**: The notification MUST display the credit-account amount applied to funds available
  as a named, separately visible part of its breakdown, so that the reported figures visibly
  account for the difference between the funding-account balance and the funds available.
- **FR-008**: Every figure in the notification MUST be linked, if linked at all, to a view that
  reports that same quantity; a link MUST NOT lead to a view whose identically-named figure is a
  different quantity.
- **FR-009**: The unreconciled figure contributing to funds committed MUST exclude transactions
  that carry no real cash impact — those designated as having no budget impact and those that
  are payments toward an active credit account — and this exclusion MUST be covered by a test
  that exercises it through the notification.
- **FR-010**: Excluding a transaction from the notification's unreconciled figure MUST NOT
  remove it from the reconcile view or make it unreconcilable.
- **FR-011**: All monetary figures in the notification MUST be formatted as currency using the
  application's existing formatting, including negative figures.
- **FR-012**: The user-facing documentation that describes the notification's meaning MUST be
  updated in the same change to state the corrected comparison.

### Key Entities

- **Budget-funding account**: an active account of a type that holds spendable cash (bank or
  cash). Its recorded balance contributes positively to funds available.
- **Credit account**: an active account representing a revolving credit line. Its recorded
  balance — negative when money is owed — is applied to funds available, so an amount owed
  reduces it.
- **Standing budget**: a budget that carries a balance across pay periods. The sum of active
  standing budget balances is committed money.
- **Current pay period**: the biweekly period containing today. Its allocated-but-unspent amount
  is committed money.
- **Unreconciled transaction**: a recorded transaction not yet matched to a bank record.
  Contributes to committed money only when it represents real cash movement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a person whose budgeting is fully in order but who carries an outstanding
  credit-card balance, the application displays no surplus or shortfall banner, where before
  this change it displayed a surplus equal to the amount owed.
- **SC-002**: When a surplus or shortfall is reported, the reported difference between funds
  available and funds committed is accurate to the cent for any combination of funding-account
  balances, credit-account balances, standing budget balances, pay-period allocation, and
  unreconciled transactions.
- **SC-003**: Every figure in the notification can be reconciled by a reader against the view it
  links to: following any link shows the same quantity under a compatible name.
- **SC-004**: Entering a credit-card payment together with its offsetting no-budget-impact entry
  changes the reported surplus or shortfall by zero, both immediately and after those entries
  are reconciled.
- **SC-005**: For a person with no credit accounts, every figure in the notification is
  identical to what it was before this change.
- **SC-006**: The complete unit and acceptance suites pass, with new tests that pin the exact
  expected figures for each scenario above.

## Assumptions

- Credit-account balances are recorded with the sign convention already used throughout the
  application, in which an amount owed is stored as a negative balance. Applying the recorded
  balance to funds available with its own sign therefore subtracts what is owed. Existing code
  that takes the absolute value of these balances confirms this convention.
- "Active credit accounts" means the same set of accounts the application already identifies for
  the purpose of determining what a transaction may be a payment toward. No new notion of which
  accounts count is introduced.
- The pay-period quantity in the notification is correct as it stands and is not being changed;
  only its name and its link are at issue. The alternative — changing the quantity to match the
  pay-period view's "remaining" — is explicitly rejected, because allocated-but-unspent is what
  is actually still committed against cash on hand.
- The offsetting-entry mechanism delivered for issues #210 and #319 is present on `master` and
  is the correct exclusion rule; this change consumes it rather than replacing it or
  reintroducing any note-text-matching workaround.
- Reordering or rewording the notification sentence is acceptable. No stored data, schema, or
  API contract depends on its exact wording; the tests that assert it will be updated as part of
  this change.
- This change affects only the notification banner. It does not alter any account balance, any
  budget figure, any pay-period calculation, or the pay-period view itself.

## Out of Scope

- Changing what the pay-period view reports under the heading "remaining". That figure is
  correct for that view.
- Any change to how credit-account balances are recorded, updated, or displayed elsewhere.
- Any change to the reconcile view, to which transactions are reconcilable, or to the
  no-budget-impact designation itself.
- Issue #321 and any other notification not concerned with the funds-available comparison; the
  stale-account and unreconciled-count notifications are untouched.
