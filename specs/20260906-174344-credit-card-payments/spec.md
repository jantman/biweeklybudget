# Feature Specification: Special Handling of Credit Card Payments

**Feature Branch**: `robot-army/issue-210-special-handling-of-credit-card-payments`

**Created**: 2026-09-06

**Status**: Draft

**Input**: GitHub issue [#210](https://github.com/jantman/biweeklybudget/issues/210) ("Special handling of credit card payments"), together with its open sub-issue [#319](https://github.com/jantman/biweeklybudget/issues/319) ("Add a 'no budget impact' flag to Transaction for cash-only entries"), which is not yet implemented and is therefore in scope here.

## Overview

Every transaction recorded in the application is counted against the income available in
the pay period it falls in. That is correct for money spent from a budget-funding account,
but it double-counts money spent on a credit account: the purchase is one transaction and
the cash payment that later settles it is another, and today both are charged to a budget.

The rule this feature establishes is: **a payment toward a credit account has zero budget
impact.** Each charge is already budgeted on its own charge date, in its own pay period.
The payment that settles it is a movement of cash between two accounts the application
already tracks, and must not be charged to any budget in any period.

Reaching that rule requires a general capability first — the ability to record a
transaction that exists for reconciliation purposes but is excluded from all budget and
pay-period arithmetic. That capability is issue #319, it is not present in the code today,
and it has uses beyond credit cards (statement credits, cash-back redemptions applied as a
statement credit, manual balance-reconcile adjustments). This specification covers both
layers: the general exclusion capability, and the credit-payment designation built on top
of it.

### Explicitly rejected approach

Issue #210 originally proposed *netting*: subtracting the sum of a credit account's charges
in a period from the sum of payments toward that account in the same period. **This
specification rejects that approach and it MUST NOT be implemented.** It is correct only
when a card is paid off inside the same pay period its charges were made. For the ordinary
cross-period case — charges `C(n)` in period N, paid in period N+1 which has its own
charges `C(n+1)` — netting charges period N+1 with `C(n+1) + (P − C(n+1)) = P`, when the
correct answer is `C(n+1)`. It recreates the double-count it was meant to remove, displaced
by one period, because it nets the payment against the wrong period's charges.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record a transaction that has no budget impact (Priority: P1)

A person records a transaction that must exist so it can be matched against a real bank or
card transaction during reconciliation, but that does not represent spending or income
against any budget — a statement credit, a cash-back redemption, or a manual adjustment
that corrects a balance. They mark the transaction as having no budget impact. The
transaction is still stored against an account, still appears in the transaction list, and
is still available to reconcile, but it contributes nothing to any budget's spent or
allocated amount, nothing to any pay period's totals, and nothing to the account's
unreconciled sum.

**Why this priority**: This is the mechanism every other part of the feature is built on.
Delivered alone it already removes a class of silent mis-statement from the data, and it is
independently useful for the non-credit-card cases the person already has in their records.

**Independent Test**: Create a transaction with the no-budget-impact designation set,
against an active periodic budget, dated inside a pay period that has other transactions.
Confirm the pay period's budget sums, overall sums, and remaining amounts are identical to
what they were before the transaction existed, that the account's unreconciled sum is
unchanged, and that the transaction is still listed and still reconcilable.

**Acceptance Scenarios**:

1. **Given** a pay period whose budget "Groceries" shows $100 spent, **When** a $40
   transaction against "Groceries" dated in that period is created with no budget impact,
   **Then** the period continues to show $100 spent against "Groceries", and the period's
   overall remaining and allocated figures are unchanged.
2. **Given** an account with an unreconciled sum of $250, **When** a $40 no-budget-impact
   transaction is created against that account, **Then** the account's unreconciled sum
   remains $250.
3. **Given** a no-budget-impact transaction, **When** the transaction list and the
   reconcile view are displayed, **Then** the transaction appears in both, and is visually
   distinguished from ordinary transactions in the transaction list.
4. **Given** an existing ordinary transaction that is counted in a pay period, **When** it
   is edited to set the no-budget-impact designation, **Then** the pay period totals drop
   by that transaction's amount; **and when** the designation is removed again, **Then**
   the totals return to their original values.
5. **Given** a no-budget-impact transaction, **When** it is reconciled against a downloaded
   bank transaction, **Then** the reconciliation succeeds exactly as it does for an
   ordinary transaction.

---

### User Story 2 - Record a credit card payment without double-counting (Priority: P1)

A person pays a credit card. They record the payment as a transaction on the bank account
the money left, and designate it as a payment toward that specific credit account, choosing
the card from a list of the credit accounts the application knows about. Making that
designation is by itself sufficient: the payment has no budget impact in the pay period it
falls in, or in any other. The person does not create, calculate, or maintain any
offsetting entry.

**Why this priority**: This is the substance of issue #210 and the reason the feature
exists. It removes the recurring, silent overstatement of a pay period's spending, and it
eliminates the manual pseudo-transaction workaround along with the arithmetic mistake that
workaround invites.

**Independent Test**: With charges recorded on a credit account in one pay period, record a
payment toward that account in a later pay period and confirm the later period's totals
reflect only that period's own charges, unchanged by the payment; then repeat with the
payment in the same period as the charges and confirm the charges are counted exactly once.

**Acceptance Scenarios**:

1. **Given** pay period N containing $500 of charges on credit account "Visa" and pay
   period N+1 containing $300 of its own charges on "Visa", **When** a $500 payment toward
   "Visa" is recorded in period N+1, **Then** period N+1's spending totals reflect $300 of
   "Visa" charges and are not increased by the $500 payment, and period N's totals are
   unchanged at $500.
2. **Given** a pay period containing a $200 charge on credit account "Visa", **When** a
   $200 payment toward "Visa" is recorded in that same pay period, **Then** the period's
   spending totals include the $200 charge exactly once and are not increased by the
   payment.
3. **Given** the Add Transaction form, **When** it is opened, **Then** it offers a control
   for designating the transaction as a payment toward a credit account, listing the credit
   accounts and no others, and defaulting to no designation.
4. **Given** a transaction designated as a payment toward a credit account, **When** it is
   saved, **Then** it is treated as having no budget impact without the person having to
   set that separately, and the Edit form for it shows both the credit account it pays and
   its no-budget-impact state.
5. **Given** an existing payment transaction designated toward a credit account, **When**
   the designation is removed, **Then** the transaction resumes counting against its budget
   in its pay period.
6. **Given** a payment designated toward a credit account, **When** the account it is
   recorded against is inspected, **Then** it is still the funding account the money left,
   and the payment is still reconcilable against the corresponding downloaded bank
   transaction.

---

### User Story 3 - See what a payment covers, and be warned when it cannot be right (Priority: P2)

While entering a payment toward a credit account, the person is shown how the amount they
have entered maps onto the charges the application has recorded for that card: how much of
it settles charges from pay periods that have already closed, and how much of it settles
charges in the currently-open period. If the amount is larger than every unpaid charge the
application knows about for that card, they are warned, because that reliably means charges
are missing from the records or have been recorded against the wrong account.

**Why this priority**: This is the part that prevents mistakes rather than merely making
them representable. The historical failure it addresses — a missed payment cycle whose next
payment covered three periods of residual charges — produced an overstatement on the order
of a third of a pay period's income, and surfaced only days later as an unexplained
shortfall. It depends on User Story 2 being in place, so it follows it.

**Independent Test**: With a known set of charges on a credit account spread across a closed
period and the open period, enter payments of several amounts and confirm the displayed
breakdown attributes the correct amount to each period and that the over-payment warning
appears when, and only when, the amount exceeds the total recorded unpaid charges.

**Acceptance Scenarios**:

1. **Given** credit account "Visa" with $400 of unpaid charges in a closed pay period and
   $150 of charges in the currently-open pay period, **When** a payment of $400 toward
   "Visa" is being entered, **Then** the person is shown that the full $400 settles charges
   from closed periods and $0 applies to the open period, and no warning is shown.
2. **Given** the same state, **When** a payment of $500 is being entered, **Then** the
   person is shown that $400 settles closed-period charges and $100 applies to the
   currently-open period, and no warning is shown.
3. **Given** the same state, **When** a payment of $600 is being entered, **Then** the
   person is warned that the amount exceeds the $550 of unpaid charges recorded for "Visa"
   by $50, and told that this usually means charges are missing or recorded against the
   wrong account.
4. **Given** credit account "Visa" with unpaid charges spanning three closed pay periods,
   **When** a payment covering all three is being entered, **Then** the breakdown shows the
   amount attributed to each closed period, oldest first.
5. **Given** the over-payment warning is shown, **When** the person saves the transaction
   anyway, **Then** the transaction is saved; the warning is advisory and does not block
   recording a payment the person knows to be correct.
6. **Given** a payment transaction already saved and designated toward a credit account,
   **When** it is reopened for editing, **Then** the breakdown and any warning are computed
   without counting that transaction itself as an already-recorded payment.

---

### Edge Cases

- **Payment amount of zero or negative.** The existing rule that a transaction amount
  cannot be zero continues to apply. A negative amount designated as a payment toward a
  credit account represents a refund flowing back from the card; it is still zero
  budget impact and is included in the unpaid-charge arithmetic with its sign.
- **Payment designated toward a credit account, but recorded against that same credit
  account.** This is a data-entry error — a payment leaves a funding account. The person is
  warned but not blocked.
- **Credit account with no recorded charges at all.** Any payment toward it exceeds the
  recorded unpaid charges, so the over-payment warning is shown; the breakdown reports zero
  attributable to any period.
- **No credit accounts exist.** The credit-account control is present but offers only the
  "not a credit card payment" choice.
- **The designated credit account is later made inactive.** Existing payments toward it
  keep their designation and keep their zero budget impact. Inactive credit accounts are
  not offered when creating a new payment, but an existing payment being edited continues
  to show the account it points at.
- **Both the no-budget-impact designation and a credit-account designation are set.** These
  are consistent, not conflicting: the credit designation implies the exclusion. Clearing
  the credit designation on a transaction leaves the person's explicit no-budget-impact
  choice, if they made one, intact.
- **A no-budget-impact transaction against a budget that is not active.** The existing
  rules about inactive budgets are unchanged; excluding a transaction from the sums does
  not change which budgets may be selected.
- **A no-budget-impact transaction with a budgeted amount** (created from a scheduled
  transaction). It contributes neither spent nor allocated amounts to its budget.
- **Split transactions.** A transaction split across several budgets that is marked no
  budget impact contributes nothing to any of them.
- **Charges predating the tracked window.** Charges dated before the configured start of
  credit-payment tracking are not counted as unpaid, so payments settling them will trip the
  over-payment warning; the person may save regardless.

## Requirements *(mandatory)*

### Functional Requirements

#### Layer 1 — General exclusion from budget arithmetic (issue #319)

- **FR-001**: A transaction MUST be able to carry a designation meaning "this transaction
  has no impact on any budget or pay period total". The designation MUST default to absent
  for every transaction, existing and new.
- **FR-002**: A transaction carrying that designation MUST be excluded from the per-budget
  sums a pay period reports — its amount MUST contribute nothing to any budget's spent,
  allocated, or transaction totals, and MUST NOT change any budget's remaining amount.
- **FR-003**: A transaction carrying that designation MUST be excluded from a pay period's
  overall sums, including allocated, spent, income, and remaining figures.
- **FR-004**: A transaction carrying that designation MUST be excluded from the
  unreconciled sum reported for the account it belongs to.
- **FR-005**: A transaction carrying that designation MUST still belong to an account, MUST
  still appear in the transaction list and in the pay period's transaction listing, and
  MUST still be available for, and behave normally during, reconciliation.
- **FR-006**: A transaction carrying that designation MUST still be assigned to at least one
  budget and MUST still satisfy the existing rule that its budget allocations sum to its
  amount; the designation changes how the transaction is counted, not how it is recorded.
- **FR-007**: A transaction carrying that designation MUST be visually distinguished from
  ordinary transactions wherever transactions are listed, so that a reader can tell at a
  glance why the listed amounts do not sum to the reported totals.
- **FR-008**: Users MUST be able to set and clear the designation when creating a
  transaction and when editing an existing, unreconciled one, and the current state MUST be
  shown when an existing transaction is opened for editing.

#### Layer 2 — Payment toward a credit account (issue #210)

- **FR-009**: A transaction MUST be able to record which credit account, if any, it is a
  payment toward. The default MUST be that it is not a payment toward any credit account.
- **FR-010**: Users MUST be able to choose the credit account from a list presented on the
  Add and Edit Transaction forms. The list MUST offer credit accounts only, MUST NOT offer
  accounts of any other type, and MUST include an explicit "not a credit card payment"
  choice which is the default.
- **FR-011**: A transaction designated as a payment toward a credit account MUST be treated
  as having no budget impact — the whole of Layer 1's exclusions MUST apply to it —
  automatically, without the user separately setting the Layer 1 designation, and without
  the user creating any offsetting entry.
- **FR-012**: The zero budget impact of a credit payment MUST NOT depend on the pay period
  the payment falls in, on the pay period any charge falls in, on the relative order of the
  payment and the charges, or on any comparison between the payment amount and any period's
  charge total.
- **FR-013**: The system MUST NOT net a credit account's charges against payments toward
  that account in any pay period's arithmetic.
- **FR-014**: Clearing the credit-account designation from a transaction MUST restore that
  transaction's ordinary budget impact, unless the user has also set the Layer 1
  designation explicitly, in which case that choice stands.
- **FR-015**: The system MUST reject a credit-account designation that names an account
  which is not a credit account.

#### Layer 3 — Payment amount feedback and validation

- **FR-016**: While a payment toward a credit account is being entered or edited, the system
  MUST show how the entered amount is attributed across pay periods: the portion settling
  charges in pay periods that have already closed, broken down by period from oldest to
  newest, and the portion applying to the currently-open pay period.
- **FR-017**: Attribution MUST work by applying the payment to the credit account's
  outstanding recorded charges in date order, oldest first, until the payment amount is
  exhausted.
- **FR-018**: The system MUST determine a credit account's unpaid recorded charges as the
  sum of all transactions recorded against that account, less the sum of all payments
  already designated toward that account, counting only transactions dated on or after the
  configured start of credit-payment tracking.
- **FR-019**: When editing an existing payment, the payment being edited MUST be excluded
  from the already-recorded payments used in FR-018, so that its own amount is not counted
  against itself.
- **FR-020**: The system MUST warn the user when the payment amount exceeds the credit
  account's unpaid recorded charges, MUST state the amount of the excess, and MUST explain
  that this ordinarily indicates charges missing from the records or recorded against the
  wrong account.
- **FR-021**: The over-payment warning MUST be advisory: the user MUST be able to save the
  transaction with the warning showing.
- **FR-022**: The system MUST warn when a transaction designated as a payment toward a
  credit account is itself recorded against that same credit account, and MUST allow the
  user to save it anyway.
- **FR-023**: The start of credit-payment tracking MUST be configurable through the
  application's settings, and MUST default to the existing reconcile begin date so that no
  new configuration is required to adopt the feature.

#### Data, migration, documentation

- **FR-024**: The stored form of both designations MUST be added by a reversible schema
  migration that can be applied to and rolled back from an existing database, leaving every
  existing transaction with neither designation set — that is, behaving exactly as it does
  today.
- **FR-025**: Documentation MUST describe the credit card payment workflow — designate the
  payment, no offsetting entry, zero budget impact in every period — and MUST describe the
  general no-budget-impact designation and when to use it. Any documented description of
  the pseudo-transaction workaround MUST be replaced by the new workflow.

### Key Entities

- **Transaction**: An actual movement of money against one account, allocated across one or
  more budgets. Gains two new properties: whether it is excluded from all budget and pay
  period arithmetic, and which credit account (if any) it is a payment toward. The second
  implies the first.
- **Account**: A financial account. Accounts of the credit type are the ones a payment may
  be designated toward, and are the accounts whose recorded charges the payment feedback is
  computed from. Accounts of the bank and cash types remain the budget funding sources.
- **Budget**: Unchanged in structure. Its spent, allocated, and remaining figures now ignore
  excluded transactions.
- **Pay Period**: Unchanged in structure. Its per-budget and overall sums now ignore
  excluded transactions.
- **Credit payment attribution** (derived, not stored): For a given credit account and
  candidate payment amount, the mapping of that amount onto the account's outstanding
  recorded charges by pay period, oldest first, plus any excess beyond all recorded charges.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A credit card charge made in one pay period and paid in a later one is
  counted against exactly one pay period's available income — the period of the charge —
  in 100% of cases, regardless of how many periods separate the charge from the payment.
- **SC-002**: A credit card charge made and paid within a single pay period is counted
  against that period's available income exactly once.
- **SC-003**: Recording a credit card payment requires one entry, not two; the number of
  manually-created offsetting entries needed to keep pay period totals correct drops to
  zero.
- **SC-004**: A payment whose amount exceeds the total unpaid charges recorded for the card
  produces a visible warning before it is saved, in 100% of such cases, stating the size of
  the excess.
- **SC-005**: For any payment covering charges from more than one pay period, the person
  can see, before saving, how much of the payment is attributed to each of those periods.
- **SC-006**: Applying the schema change to an existing database leaves every pay period
  total, budget total, and account unreconciled sum identical to its value before the
  change.
- **SC-007**: Rolling the schema change back returns the database to a state the previous
  release can use.
- **SC-008**: The complete unit and acceptance test suites pass, with new coverage pinning
  the pay period arithmetic for both the same-period and cross-period payoff cases.

## Assumptions

These were chosen as reasonable defaults where the source issues did not specify. Each is a
decision that can be revisited without reworking the rest of the feature.

- **Issue #319 is in scope.** It is declared a dependency of #210 and is not implemented in
  the codebase; #210 cannot be delivered without it, so both layers are specified and built
  together.
- **A payment still needs a budget.** A transaction's amount is carried by its budget
  allocations, so an excluded transaction is still recorded against a budget and still
  obeys the rule that allocations sum to the amount. The budget simply does not count it.
  The alternative — allowing budget-less transactions — would be a much larger change to
  the transaction model and is not required to fix the double-count.
- **Warnings are advisory, never blocking.** The person entering a payment knows things the
  application does not, including charges that have not yet been downloaded. A hard error
  would make correct payments unrecordable. Only the pre-existing hard validations (amount
  not zero, account required, budget allocations sum to amount, valid date) continue to
  block.
- **The credit-account designation is not restricted by the account the payment is recorded
  against.** A payment normally leaves a bank or cash account, but restricting this would
  block legitimate cases such as a balance transfer between cards. The mismatch case that
  is always an error — paying a card from itself — is warned about instead (FR-022).
- **Unpaid charges are a running total, bounded by a configurable start date.** Payments
  recorded before this feature existed carry no designation and so are not subtracted,
  which would make a card's unpaid-charge total drift upward without bound. Bounding the
  window by a configurable date, defaulting to the existing reconcile begin date, keeps the
  figure meaningful and lets the person move the boundary forward once historical payments
  have been designated or written off.
- **The warning's failure mode is a false negative, not a false positive.** Undesignated
  historical payments inflate the apparent unpaid-charge total, so the warning fires less
  often than it ideally would rather than firing spuriously on correct payments.
- **Two separate controls, not one.** The general no-budget-impact designation is exposed
  on its own because #319's non-credit-card uses — statement credits, cash-back
  redemptions, balance-reconcile adjustments — have no credit account to designate. The
  credit-account control is the credit-card-specific layer on top of it.
- **The excluded-transaction indicator follows the existing UI conventions** of the
  application's transaction tables rather than introducing a new visual language.
- **Scope boundary — the unallocated-funds notification (issue #320) is not changed here.**
  Removing pseudo-transactions improves its inputs, but netting credit account balances into
  that notification is separate work.
- **Scope boundary — detecting a closed pay period with unpaid card charges (issue #322) is
  not built here.** The unpaid-charge calculation this feature introduces (FR-018) is the
  shared foundation that work will build on, and is specified so it can be reused rather
  than reimplemented.
- **Scope boundary — no retroactive data migration.** Existing pseudo-transaction pairs in
  the person's data are left exactly as they are; they already net to zero and are correct.
  The feature changes how new payments are recorded, and existing unreconciled payments may
  be updated by hand if the person chooses.

## Dependencies

- Issue #319's no-budget-impact designation, built here as Layer 1.
- The existing pay period arithmetic, account unreconciled sums, transaction forms, and
  reconciliation workflow, all of which this feature modifies rather than replaces.
- A schema migration applied to the existing database before the new behaviour is available.
