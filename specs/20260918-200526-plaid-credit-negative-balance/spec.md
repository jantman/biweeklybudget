# Feature Specification: Plaid Credit Card Balances Recorded As Negative

**Feature Branch**: `robot-army/issue-354-cash-position-adds-plaid-sourced-credit`

**Created**: 2026-09-18

**Status**: Draft

**Input**: GitHub issue [#354](https://github.com/jantman/biweeklybudget/issues/354) — "Cash Position adds Plaid-sourced credit card balances instead of subtracting them" (labels: bug, robot-army). Found while working the 2.0.0 release verification checklist, [#353](https://github.com/jantman/biweeklybudget/issues/353).

## Background

Throughout biweeklybudget, money **owed** on an account is recorded as a **negative**
balance. Every consumer of a credit account's balance is built on that convention:

* The unallocated-funds notification (`biweeklybudget/flaskapp/notifications.py`) *adds*
  the combined credit balance to available funds, relying on it being negative so that
  what is owed is effectively subtracted.
* The Cash Position waterfall (`biweeklybudget/cashposition.py`, `CashPosition.credit_balance`)
  uses the balance "with the sign in which each is recorded -- negative in the ordinary
  case, where money is owed", as term 3, added.
* The Account Balances chart on the index page plots the recorded balances directly.

Plaid does not use that convention. For a `credit`-type account Plaid reports
`balances.current` as the **positive amount owed**. The Plaid updater records that number
verbatim for credit cards, so a card with $1,000 owed is stored as `+1000.00` instead of
`-1000.00`.

Issue [#263](https://github.com/jantman/biweeklybudget/issues/263) already corrected
exactly this for Plaid **loan** accounts — the loan branch of the updater negates Plaid's
balance and the Plaid documentation grew a "Loan Accounts" section explaining the
convention and giving corrective SQL for pre-upgrade rows. Credit cards were never given
the same treatment.

### Why the sign rule is safe to apply to every institution

Plaid states the credit sign as a rule, not an observation. The `AccountBalance.current`
field description in the pinned `plaid-python==44.0.0` (generated from Plaid's OpenAPI
spec, matching the published API reference) reads:

> The total amount of funds in or owed by the account. For `credit`-type accounts, a
> positive balance indicates the amount owed; a negative amount indicates the lender
> owing the account holder. For `loan`-type accounts, the current balance is the
> principal remaining on the loan, except in the case of student loan accounts at Sallie
> Mae (`ins_116944`). [...] Similar to `credit`-type accounts, a positive balance is
> *typically* expected, while a negative amount indicates the lender owing the account
> holder.

The `credit` wording carries no "typically" and no institution qualifier; the hedging and
the single named institution-specific carve-out belong to `loan`, which #263 already
handled. No Plaid documentation, changelog entry or errors page describes an institution
that reverses the credit sign.

Plaid also documents a relation between the balance fields for credit accounts — "the
`available` balance typically equals the `limit` less the `current` balance, less any
pending outflows plus any pending inflows" — which gives a cheap, non-fatal way to notice
an institution that ever does break the rule.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cash Position and the unallocated-funds notification tell the truth (Priority: P1)

A user whose credit cards are linked through Plaid runs a Plaid update, then looks at the
Cash Position page and the unallocated-funds notification. The figures must treat what is
owed on those cards as money that is *not* available, exactly as they already do for
credit balances entered by hand.

**Why this priority**: This is the reported defect. Until the recorded sign is right,
every downstream figure that touches a Plaid credit balance is wrong by twice the amount
owed, and the release verification checklist in #353 cannot be worked at all.

**Independent Test**: Run a Plaid update for an account linked to a Plaid `credit` item
whose reported `balances.current` is a positive amount owed, then read back the recorded
account balance and the Cash Position figures. The balance is negative and the Cash
Position available-funds figure is reduced by the amount owed.

**Acceptance Scenarios**:

1. **Given** a Plaid credit account reporting a current balance of `1000.00` (the amount
   owed), **When** a Plaid update runs, **Then** the statement's ledger balance and the
   account's recorded balance are both `-1000.00`.
2. **Given** that same update has run, **When** the user views the Cash Position page,
   **Then** the credit-accounts term of the waterfall contributes `-1000.00` and
   available funds are $1,000 lower than the bank balances alone.
3. **Given** that same update has run, **When** the unallocated-funds notification is
   rendered, **Then** its figure subtracts the $1,000 owed rather than adding it.
4. **Given** a Plaid credit account that is overpaid, reporting a current balance of
   `-50.00`, **When** a Plaid update runs, **Then** the recorded balance is `+50.00` and
   that $50 raises available funds — an overpaid card really does hold money the user can
   spend.
5. **Given** a Plaid credit account reporting a current balance of `0`, **When** a Plaid
   update runs, **Then** the recorded balance is `0.00` and is not displayed or stored as
   a negative zero.
6. **Given** a Plaid **depository** (bank) account reporting a current balance of
   `1234.56`, **When** a Plaid update runs, **Then** the recorded balance is `+1234.56` —
   unchanged by this feature.
7. **Given** a Plaid credit account with transactions, **When** a Plaid update runs,
   **Then** the recorded transaction amounts are unchanged by this feature; only the
   statement balance's sign differs from the previous behaviour.

---

### User Story 2 - An operator upgrading knows what happens to years of existing balances (Priority: P1)

A user who has been running biweeklybudget with Plaid-linked credit cards for years
upgrades. Every historical balance for those cards is stored in the old, positive sign,
and the Account Balances chart plots them. The user needs to be told plainly that those
rows are not touched automatically, what they will see if they do nothing, and exactly how
to correct them if they want to.

**Why this priority**: Without this, the upgrade silently produces a chart whose credit
card lines flip from positive to negative mid-history, and a user has no documented way to
reconcile it. The same need was met for loans by #263 and there is an established model to
follow.

**Independent Test**: Read the Plaid documentation page. It states the credit sign
convention, states that pre-upgrade rows keep the old sign, and gives SQL that an operator
can run once to correct them, with the conditions under which it is safe to run.

**Acceptance Scenarios**:

1. **Given** the published documentation, **When** a user reads the Plaid page, **Then**
   a section explains that Plaid reports a credit card balance as a positive amount owed
   and that biweeklybudget records it negated, with a worked example.
2. **Given** the same section, **When** a user looks for upgrade guidance, **Then** it
   states that balances recorded before the upgrade keep their old sign, that this is
   visible as a jump on the Account Balances chart at the first update after upgrading,
   and gives corrective SQL covering both the recorded account balances and the stored
   statements.
3. **Given** the corrective SQL, **When** a user reads its surrounding text, **Then** it
   says the SQL must be run once, after upgrading and before the next Plaid update, that
   running it twice undoes it, and how to limit it to the Plaid-sourced period if some of
   an account's balances came from elsewhere.
4. **Given** the changelog, **When** a user reads the entry for this change, **Then** it
   names the corrected behaviour and points at the documentation for the historical-data
   step.

---

### User Story 3 - An institution that breaks the documented sign rule is noticeable (Priority: P3)

If some institution ever did report a credit balance with the opposite sign, the user would
see a card's balance shown as money available. A cheap consistency check, logged rather
than enforced, makes that discoverable from the update logs instead of only from a wrong
total.

**Why this priority**: Speculative — no such institution is known. It costs almost
nothing, uses data already stored, and is strictly diagnostic, so it must never fail an
update or alter a recorded figure.

**Independent Test**: Feed the updater a credit account whose available balance, credit
limit and current balance are consistent only with a reversed sign, and confirm a log
message is emitted and nothing else about the update changes.

**Acceptance Scenarios**:

1. **Given** a Plaid credit account with a known credit limit and an available balance
   that matches `limit - owed`, **When** a Plaid update runs, **Then** no anomaly is
   logged.
2. **Given** a Plaid credit account whose available balance matches `limit + current`
   far better than `limit - current`, **When** a Plaid update runs, **Then** a message is
   logged identifying the account and the three figures, **and** the balance is still
   recorded per the documented rule, **and** the update succeeds.
3. **Given** a Plaid credit account with no credit limit recorded, or with no available
   balance reported, **When** a Plaid update runs, **Then** no check is attempted and
   nothing is logged about it.

---

### Edge Cases

- **Zero balance**: a card with nothing owed must record `0.00`, never `-0.00`.
- **Overpaid card / statement credit**: a negative Plaid balance must become a positive
  recorded balance. It must never be collapsed to "amount owed" by taking an absolute
  value — that would silently turn a credit in the user's favour into a debt.
- **Depository accounts share the same update path**: the change must not alter the sign
  recorded for bank/cash accounts, which use the same code path in the updater.
- **Transaction amounts are a separate concern**: the per-transaction amounts recorded for
  a credit account, and the existing per-account "negate amounts" setting that applies to
  them, are untouched.
- **Available balance**: only the ledger/current balance's sign is at issue. The available
  balance is recorded as Plaid reports it, as it is today.
- **Mixed-source accounts**: an account whose history contains balances from before it was
  linked to Plaid needs the corrective SQL scoped by date; the documentation must say so.
- **Running the corrective SQL twice**, or after a post-upgrade update, re-breaks the data;
  the documentation must warn about both.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When recording a balance for an account linked to a Plaid item of type
  `credit`, the system MUST record the negation of the balance Plaid reports, so that an
  amount owed is stored as a negative balance.
- **FR-002**: The negation MUST be a true sign reversal, not an absolute value: a negative
  reported balance (an overpaid card or a statement credit) MUST be recorded as a positive
  balance.
- **FR-003**: A reported balance of zero MUST be recorded as zero, without a negative sign.
- **FR-004**: The negated balance MUST be used consistently for both the stored statement's
  ledger balance and the account's recorded balance, so that the Account Balances chart and
  the Cash Position figures agree.
- **FR-005**: The system MUST NOT change the sign recorded for Plaid `depository` accounts,
  which are updated by the same path.
- **FR-006**: The system MUST NOT change the amounts recorded for individual transactions
  downloaded from Plaid, nor the behaviour of the existing per-account setting that negates
  transaction amounts.
- **FR-007**: The system MUST NOT change how a credit account's available balance is
  recorded.
- **FR-008**: The system SHOULD log a diagnostic message when a Plaid credit account's
  available balance, credit limit and current balance are together consistent only with a
  reversed sign convention. This check MUST be skipped when the credit limit or the
  available balance is unavailable, MUST NOT change any recorded value, and MUST NOT cause
  the update to fail or be reported as failed.
- **FR-009**: The project documentation MUST describe the credit-card balance sign
  convention on the Plaid page, alongside the existing description of the loan convention.
- **FR-010**: The documentation MUST state that balances recorded before this change keep
  their previous sign, describe the effect on the Account Balances chart, and provide SQL
  that corrects the historical recorded balances and stored statements for Plaid credit
  accounts.
- **FR-011**: The documentation for that SQL MUST state that it is run once, after
  upgrading and before the next Plaid update; that running it a second time reverses its
  effect; and how to scope it by date for accounts with balances from other sources.
- **FR-012**: The change MUST add an entry to the changelog under the `Unreleased`
  heading, naming the corrected behaviour and pointing at the documented step for existing
  data.
- **FR-013**: Automated tests MUST pin the recorded sign for each of: a positive reported
  credit balance, a negative reported credit balance, a zero reported credit balance, and
  a depository balance.

### Key Entities

- **Plaid account type**: the kind of account Plaid reports for a linked item — `credit`,
  `depository`, `investment` or `loan`. It determines the sign convention that applies.
- **Reported current balance**: the balance Plaid reports for an account. For `credit`,
  positive means owed.
- **Recorded account balance**: the balance biweeklybudget stores for an account and plots
  on the Account Balances chart. Negative means owed.
- **Stored statement**: the record of one Plaid update for one account, holding the ledger
  balance, the available balance and the time they were retrieved.
- **Credit limit**: the limit recorded for a credit account, used only by the diagnostic
  consistency check.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After a Plaid update, the balance recorded for a credit card carrying an
  amount owed is negative, and the Cash Position available-funds figure is lower than the
  sum of bank balances by exactly that amount — previously it was higher by that amount,
  an error of twice the balance owed.
- **SC-002**: A card that is overpaid by a given amount raises the Cash Position
  available-funds figure by exactly that amount.
- **SC-003**: Balances recorded for bank and cash accounts, and all transaction amounts,
  are byte-for-byte identical to what the previous behaviour recorded for the same Plaid
  data.
- **SC-004**: An operator upgrading can, from the documentation alone and without reading
  source code, determine what happens to their existing credit balances and correct them
  in a single documented step.
- **SC-005**: The two release-verification checklist items in #353 that depend on credit
  balances being subtracted ("the unallocated-funds notification now subtracts active
  credit balances" and the credit-related pay-period spot checks) can be carried out as
  written.
- **SC-006**: The full unit and acceptance suites pass, and the documentation build
  succeeds.

## Assumptions

- Plaid's documented sign convention for `credit`-type accounts holds for every
  institution, as researched in the issue and recorded in the Background above. The
  diagnostic check in User Story 3 exists to surface a counter-example if one ever appears,
  rather than to hedge the main behaviour.
- Correcting historical rows is an operator action, performed with documented SQL, not an
  automatic data migration. This matches how #263 handled the identical situation for
  loans, keeps a schema-free change schema-free, and avoids a migration that would corrupt
  data for anyone who had already corrected it by hand. An Alembic migration that rewrote
  financial history could not be safely reversed for a user who had mixed manual and
  Plaid-sourced balances.
- No database schema change is required, so no Alembic migration is part of this change.
- The Cash Position page, the unallocated-funds notification and the Account Balances chart
  need no code change: each already implements the negative-means-owed convention
  correctly, and each becomes correct for Plaid-sourced credit balances once the recorded
  sign is fixed.
- Screenshots in the documentation are generated from the test fixture data, which does not
  come from Plaid, so this change does not alter them.
