# Feature Specification: Credit Payment Panel Window

**Feature Branch**: `robot-army/issue-358-credit-payment-this-payment-covers`

**Created**: 2026-09-19

**Status**: Draft

**Input**: GitHub issue #358 — *Credit payment "This payment covers:" panel lists every
pay period since CREDIT_PAYMENT_BEGIN_DATE and attributes payments oldest-first* — plus
three design decisions taken by the maintainer before specification (recorded under
[Maintainer Decisions](#maintainer-decisions)).

## Problem

Entering a credit card payment in the **Add/Edit Transaction** modal renders a
"This payment covers:" panel. Against a database with years of history the panel is
unusable:

- The table lists every pay period that had a charge on that account since
  `CREDIT_PAYMENT_BEGIN_DATE`. For the maintainer that is every period back to 2018 —
  over 200 rows inside a modal.
- The closing line reports an unpaid total covering the whole of that span, a figure
  bearing no relation to the card's balance, which makes the over-payment warning
  meaningless.

The cause is that the feature counts a payment as a payment only when the transaction
carries a card designation, a field that did not exist before 2.0.0. Every payment made
before upgrading is invisible, so almost nothing is ever subtracted from the recorded
charges and every historical period keeps its full charge total. The documented lower
bound was meant to prevent exactly this, but its default — the reconcile begin date —
does not bound anything for an install that has been running since 2018.

This is an advisory panel only. Nothing here changes what a payment does to budgets: a
payment toward a credit account has no budget impact regardless of what this panel says.

## Maintainer Decisions

These were settled before specification and are not open questions:

- **D-1 — Window lower bound is per-account and self-healing.** The effective begin date
  for an account is the later of the configured begin date and the start of the pay
  period *following* the one containing the earliest designated payment recorded for
  that account. Once one payment has been recorded for a card, the card is treated as
  settled through that payment's period — by that payment together with the untracked
  payments that predate the feature — and the window tightens by itself with no operator
  action.
- **D-1a — The boundary sits after the first payment's period, not at its start.** This
  was refined during planning. Anchoring the window at the *start* of the period holding
  the first designated payment leaves that payment inside the window, where it is
  subtracted from charges a second time: once implicitly (the charges it settled are
  excluded) and once explicitly (as a prior payment). The surplus then spills forward
  into later periods, understating unpaid charges and suppressing the over-payment
  warning on every payment thereafter. Starting at the following period puts the first
  payment outside the window, so it is counted exactly once, and keeps every rendered row
  a whole pay period. The cost — charges made later in that boundary period, after the
  payment, fall outside the window — is accepted.
- **D-2 — Attribution stays oldest-first.** A payment settles the oldest unpaid charges
  first. This is correct accounting and does not change.
- **D-3 — The table is capped with a rollup row.** The panel renders a bounded number of
  the most recent periods individually and collapses everything older into a single
  summary row.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A payment panel that reflects the card, not the archive (Priority: P1)

Someone who has used the application for years upgrades, records one payment toward a
credit card, and from then on every payment they enter for that card shows a panel
scoped to the charges that payment could plausibly settle: the periods since that first
recorded payment, with an unpaid total in the neighbourhood of the card's balance rather
than the neighbourhood of a decade of spending.

**Why this priority**: this is the defect. Without it the panel is noise on every
payment the maintainer enters, and the over-payment warning — the reason the panel
exists — fires every time and means nothing.

**Independent Test**: record one designated payment for a card with years of prior
charges, then open the modal for a second payment toward that card. The panel's unpaid
total and its period list both start after the first payment's period, not at the
configured begin date.

**Acceptance Scenarios**:

1. **Given** a credit account with charges every period since 2018 and no transaction
   designated as a payment toward it, **When** a payment for that account is entered,
   **Then** the panel behaves as it does today — charges are counted from the configured
   begin date — because there is nothing yet from which to derive a tighter bound.
2. **Given** the same account after one payment has been designated toward it in the pay
   period 2026-08-21 to 2026-09-03, **When** a later payment for that account is entered,
   **Then** only charges dated on or after 2026-09-04 — the start of the following
   period — are counted as unpaid, and the unpaid total, the period rows, and the
   over-payment warning all reflect that window.
3. **Given** the same account, **When** a later payment for it is entered, **Then** the
   payment that anchored the window is itself outside the window and is not subtracted
   from the charges a second time.
4. **Given** an account whose configured begin date is *later* than the derived bound,
   **When** a payment for that account is entered, **Then** the configured begin date
   wins: it remains the operator's floor and is never overridden by a payment recorded
   before it.
5. **Given** an account whose only designated payment is dated after the payment being
   entered — a payment being back-dated before the first one ever recorded — **When**
   that back-dated payment is entered, **Then** the configured begin date is used, so
   the panel does not present an empty window in which every cent of the payment is
   excess.
6. **Given** the earliest designated payment for an account is itself the transaction
   being edited, **When** that transaction is opened for editing, **Then** the window is
   still derived from it, so the panel shown while editing matches the panel shown when
   it was entered.

---

### User Story 2 - A panel that fits in the modal (Priority: P2)

Whatever the window turns out to be, the panel stays a modal-sized panel: a short table
of the most recent periods, with everything older stated in one summary row rather than
a row apiece.

**Why this priority**: the window fix (P1) makes a long table rare, but it does not make
it impossible — an operator may set the begin date early deliberately, or carry a card
unpaid for a long time. The cap is what guarantees the panel is always readable, and it
is what the maintainer asked for.

**Independent Test**: construct an account whose window spans more periods than the cap
and confirm the rendered table has the capped number of period rows plus exactly one
summary row, and that the summary row's amounts plus the individual rows' amounts equal
the totals line.

**Acceptance Scenarios**:

1. **Given** a window spanning more periods with charges than the display cap, **When**
   the panel is rendered, **Then** the most recent capped-number of periods appear as
   individual rows in chronological order as they do today, and all older periods are
   replaced by a single summary row standing at the top of the table, where those periods
   would have been.
2. **Given** that summary row, **When** it is read, **Then** it states how many periods
   it stands for, the date range they span, their combined unpaid charges, and their
   combined amount covered by this payment — so a payment that landed on old charges is
   visible rather than hidden.
3. **Given** a window spanning no more periods than the cap, **When** the panel is
   rendered, **Then** no summary row appears and the table is exactly what it is today.
4. **Given** any panel with a summary row, **When** the individually-listed unpaid
   amounts and the summary row's unpaid amount are added up, **Then** they equal the
   unpaid total stated in the closing line; the same holds for the covered amounts and
   the amount stated as settling recorded charges.

---

### User Story 3 - Knowing what window you are looking at (Priority: P3)

The panel states the date from which it is counting charges, so the numbers can be
understood without reading the source or the settings file.

**Why this priority**: valuable, but the panel is usable without it. It also does the
explanatory work that otherwise falls entirely to documentation, and it is what makes
the self-healing bound comprehensible the first time someone meets it.

**Independent Test**: open the panel for an account with a derived window and confirm
the stated date matches the start of the pay period following the one containing that
account's earliest designated payment.

**Acceptance Scenarios**:

1. **Given** a panel for any credit account, **When** it renders, **Then** it states the
   date from which unpaid charges are being counted.
2. **Given** an account whose window was derived from its earliest designated payment,
   **When** the panel renders, **Then** the stated date is the start of the period after
   that payment's, not the configured begin date.

---

### Edge Cases

- **No designated payments at all for the account.** The configured begin date is used
  unchanged. This is the one noisy panel an upgrading install still sees, once per card,
  and the documentation says so.
- **Back-dated payment.** Only designated payments dated on or before the payment being
  evaluated take part in deriving the bound; a payment recorded later cannot narrow the
  window for one entered earlier.
- **Charges made after the first payment but inside its period.** These fall outside the
  window and are not counted as unpaid. This is the accepted cost of D-1a; the
  alternative double-counts the payment itself, which is worse.
- **A second payment inside the first payment's own period.** The derived bound then
  falls after the payment being entered, so the window is empty: the panel reports no
  unpaid charges and the whole amount is excess. This is the honest reading of the rule —
  as far as the application knows, the card was settled by the payment that anchored the
  window — and it is pinned by a test rather than special-cased.
- **The transaction being edited is the earliest designated payment.** It still takes
  part in deriving the bound, even though it is excluded from the prior-payments sum, so
  that the panel does not lurch when a payment is opened for editing.
- **Derived bound earlier than the configured begin date.** The configured begin date
  wins. It is a floor, and an operator who has set it forward has said they do not want
  anything before it counted.
- **No charges inside the window.** The panel says no unpaid charges are recorded, as it
  does today, and the whole payment is excess.
- **Exactly the cap number of periods.** No summary row; the boundary is inclusive.
- **A summary row covering periods that absorbed the entire payment.** The summary row
  carries the full covered amount and the totals still reconcile, so the payment is
  never shown as having gone nowhere.
- **Charges dated after the payment.** Unchanged: a payment cannot settle a charge that
  had not been made when it was paid.

## Requirements *(mandatory)*

### Functional Requirements

#### Window derivation

- **FR-001**: The set of charges considered for a credit account MUST be bounded below
  by an *effective begin date* derived per account, rather than by the configured begin
  date alone.
- **FR-002**: The effective begin date MUST be the later of (a) the configured credit
  payment begin date and (b) the start date of the pay period *following* the one
  containing the earliest transaction designated as a payment toward that account.
- **FR-003**: Only transactions designated as payments toward the account and dated on
  or before the payment being evaluated MUST take part in deriving the effective begin
  date.
- **FR-004**: If no such transaction exists, the effective begin date MUST be the
  configured begin date, preserving today's behaviour exactly.
- **FR-005**: The transaction being edited MUST take part in deriving the effective
  begin date even though it is excluded from the prior-payments sum.
- **FR-005a**: The transaction that anchors the effective begin date MUST fall outside
  the resulting window, so that it is never also counted in the prior-payments sum. No
  payment may reduce a card's unpaid charges twice.
- **FR-005b**: When the derived begin date falls after the payment date, the window MUST
  simply be empty; the configured begin date MUST NOT be reinstated as a fallback, which
  would swing the panel back to the whole of recorded history.
- **FR-006**: The upper bound of the window (the payment date) MUST be unchanged.
- **FR-007**: The configured begin date MUST keep its present meaning and remain the
  operator's manual floor; no setting is renamed, removed, or given a new default.
- **FR-008**: The unpaid total, the per-period rows, the amount attributed, the excess,
  and the over-payment warning MUST all be computed from the effective begin date, so
  that every figure the panel shows describes the same window.

#### Attribution

- **FR-009**: Attribution MUST remain oldest-first: prior payments settle the oldest
  charges in the window first, and the payment being entered is then applied to what
  remains, oldest first. No change.

#### Panel rendering

- **FR-010**: The panel MUST render at most a fixed number of individual period rows,
  and that number MUST be a single named constant rather than a figure repeated at each
  use.
- **FR-011**: The periods rendered individually MUST be the most recent ones in the
  window; all older periods MUST be collapsed into exactly one summary row. Rows MUST
  stay in chronological order, so the summary row — standing for the oldest periods —
  MUST be the first row of the table.
- **FR-012**: The summary row MUST state the number of periods it stands for, the date
  range those periods span, their combined unpaid charges, and their combined amount
  covered by this payment.
- **FR-013**: When the window holds no more periods than the cap, no summary row MUST be
  rendered and the table MUST be identical to today's.
- **FR-014**: The individual rows' amounts plus the summary row's amounts MUST equal the
  totals stated in the closing line, for both unpaid charges and amount covered.
- **FR-015**: A summary row carrying a non-zero covered amount MUST be visually
  distinguishable from one carrying none, so that a payment which landed entirely on old
  charges is apparent at a glance rather than having to be inferred from the totals line.
- **FR-016**: The panel MUST state the date from which unpaid charges are being counted.
- **FR-017**: The existing warnings, the "no unpaid charges are recorded" case, the
  closing totals line, and the ability to save the transaction regardless MUST be
  unchanged.

#### Documentation

- **FR-018**: The credit card payments section of the usage documentation MUST explain
  that payments recorded before the feature existed carry no card designation and are
  not subtracted, that the window therefore starts at the first payment recorded for
  each card, and what an upgrading user will see on the first payment they enter for a
  card.
- **FR-019**: The configured begin date's own documentation MUST describe its new role
  as a floor beneath a per-account derived bound.
- **FR-020**: The changelog MUST record the fix under `Unreleased`, naming the
  user-visible consequence for someone upgrading.

### Worked Examples

These pin the intended behaviour; they are requirements, not illustrations.

**Example A — the upgrading install.** Card with charges in every period from 2018 to
today. Configured begin date 2018-01-06. One payment designated toward the card on
2026-08-25, in the period 2026-08-21 to 2026-09-03. A new $500 payment is entered dated
2026-09-18.

- Effective begin date: `max(2018-01-06, 2026-09-04)` = **2026-09-04**, the start of the
  period following the one holding the first designated payment.
- Charges counted: those dated 2026-09-04 through 2026-09-18 only.
- Prior payments consumed: **none**. The 2026-08-25 payment is outside the window, which
  is the point — the charges it settled are outside the window too, so subtracting it as
  well would discount it twice.
- Rows: one period. No summary row.
- The unpaid total is a fortnight of charges, not eight years of them.

**Example B — the first payment for a card.** Same card, but the 2026-08-25 payment does
not exist and the $500 payment dated 2026-09-18 is the first ever designated toward it.

- Effective begin date: **2018-01-06**, the configured floor. Nothing has been recorded
  from which to derive anything tighter.
- The panel is as noisy as it is today — once. Every subsequent payment for this card
  gets Example A's window.

**Example C — the cap, with the payment landing on old charges.** Effective begin date
gives twenty periods with charges. Cap is six. The payment is $400 and, attributed
oldest-first, is entirely absorbed by the four oldest periods.

- First row: the summary row — *14 older periods (2026-01-02 – 2026-07-10)*, combined
  unpaid $1,380.00, combined covered $400.00 — rendered so the $400.00 is conspicuous.
- Then six rows for the six most recent periods, each showing its unpaid charges and
  $0.00 covered.
- Closing line: $400.00 of $400.00 settles recorded charges; $1,380.00 plus the six
  listed periods' unpaid charges are recorded for the account. The rows add up to the
  totals.

**Example D — the configured floor wins.** Configured begin date 2026-06-01; earliest
designated payment 2026-03-14, in the period 2026-03-07 to 2026-03-20.

- Effective begin date: `max(2026-06-01, 2026-03-21)` = **2026-06-01**.

**Example E — back-dating.** Earliest designated payment 2026-08-25. A payment is being
entered dated 2026-05-01.

- No designated payment is dated on or before 2026-05-01, so the effective begin date is
  the configured begin date. The window is not empty and the payment is not reported as
  entirely excess.

### Key Entities

- **Credit account**: the card being paid. Gains a derived per-account window start; no
  stored attribute changes.
- **Designated payment**: a transaction marked as a payment toward a credit account. The
  earliest one for an account now determines that account's window start: the window
  begins with the pay period after the one containing it.
- **Period row**: one pay period in the panel, carrying its unpaid charges and the amount
  this payment covers.
- **Summary row**: a new, at-most-one row standing for all periods older than the cap,
  carrying a count, a date range, and the summed amounts of the periods it replaces.

## Success Criteria *(mandatory)*

- **SC-001**: For an account that has had at least one payment recorded against it, the
  panel lists only periods after that payment's period — for the maintainer's database,
  single digits of rows instead of over 200.
- **SC-002**: The panel never renders more than the cap plus one rows, for any account,
  any window, and any history length.
- **SC-003**: The unpaid total shown for a card paid in full each cycle is within one
  billing cycle of charges, rather than the whole of the recorded history.
- **SC-004**: The over-payment warning fires only when the payment genuinely exceeds the
  charges in the derived window, so it becomes a signal again rather than a constant.
- **SC-005**: The rows shown — individual and summary together — always sum to the
  totals line, verifiable by inspection in the panel.
- **SC-006**: A reader of the credit card payments documentation can predict what the
  panel will show for their own first post-upgrade payment, and what will change for the
  second.
- **SC-007**: Existing behaviour for an account with no designated payments, and for an
  account whose window is short, is unchanged — no existing expectation is invalidated
  beyond the window narrowing.

## Assumptions

- The display cap is **6 periods** — roughly three months of biweekly periods, enough to
  cover a card carried across a few cycles while still fitting a modal. It is a constant
  in the code, not a user-facing setting; no evidence suggests operators would want to
  tune it, and the constitution's guidance is against adding settings speculatively.
- "Most recent periods" means the last entries of the existing oldest-first period list;
  the rendered order of rows is unchanged from today, with the summary row taking the
  place of the collapsed periods at the head of the table.
- Aligning the derived bound to a pay period boundary — rather than to the day after the
  first designated payment — keeps every rendered row a whole pay period, which is what
  the table's "Pay Period" column claims each row to be.
- No database schema change is required; the derivation reads existing columns. No
  Alembic migration is therefore in scope.
- The panel remains advisory. Nothing in this change affects budget impact, account
  balances, reconciliation, or what is saved.
- Plaid-derived balances are explicitly out of scope; issue #354 covers those and is
  independent of this change.
- The `CREDIT_PAYMENT_BEGIN_DATE` setting keeps its name, its default, and its meaning,
  so no upgrade step is required of anyone.

## Out of Scope

- Changing attribution order (settled: it stays oldest-first).
- Changing the default or semantics of `CREDIT_PAYMENT_BEGIN_DATE`.
- Any backfill or migration that would assign card designations to historical payments.
- Any change to how Plaid balances are recorded or signed (issue #354).
- Making the display cap configurable.
