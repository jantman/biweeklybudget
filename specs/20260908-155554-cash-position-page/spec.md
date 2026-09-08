# Feature Specification: Cash Position Page

**Feature Branch**: `robot-army/issue-321-add-a-cash-position-page-showing-the`

**Created**: 2026-09-08

**Status**: Draft

**Input**: GitHub issue #321 — "Add a Cash Position page showing the full available-funds waterfall"

## Overview

The application already computes, on every page load, the difference between the money
sitting in budget-funding accounts and the money that has been spoken for. When those two
figures disagree it says so in a one-sentence banner at the top of the page. That sentence
is the only place the calculation surfaces, and it shows six numbers with no way to see
where any of them came from.

This feature adds a dedicated page that lays the same calculation out as a waterfall —
every input itemized, every subtotal named, and every line linked to the view it was
derived from — so the operator can answer "how much money do I actually have that isn't
spoken for?" and, when the answer looks wrong, find out why.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See the whole calculation, not just its conclusion (Priority: P1)

The operator loads the application, sees the banner saying available funds do not match
allocated funds, and wants to know which term is responsible. They open the Cash Position
page and read the calculation top to bottom: the starting account balances, each
adjustment applied to them, the named subtotals, and the final uncommitted figure. Every
number the banner quotes appears on the page in context, and the page's bottom line is the
same number the banner is complaining about.

**Why this priority**: This is the entire point of the issue. Without it there is no way to
inspect the calculation short of reading source and querying the database by hand. On its
own — with no itemization, no links, and no diagnostics — a page showing the terms and
subtotals already delivers the core value.

**Independent Test**: Load the page against a database with known balances and confirm every
term, subtotal, and the final figure match values computed independently from the same data,
and that the final figure equals the discrepancy the notification banner reports.

**Acceptance Scenarios**:

1. **Given** a database in which budget-funding balances, credit balances, unreconciled
   transactions, standing budgets, and current pay period allocations all hold non-zero
   values, **When** the operator opens the Cash Position page, **Then** the page shows each
   of those terms as its own line with its own value, the two named subtotals ("Net liquid
   position" and the final uncommitted total), and each line labeled with whether it adds to
   or subtracts from the running total.
2. **Given** the same database, **When** the operator compares the page's final uncommitted
   figure to the amount by which the notification banner says available funds differ from
   allocated funds, **Then** the two agree exactly, including sign.
3. **Given** a database in which available funds exactly equal allocated funds — so no
   discrepancy banner is shown at all — **When** the operator opens the Cash Position page,
   **Then** the page still renders the full waterfall and shows a final uncommitted figure
   of zero.
4. **Given** a credit account carrying a positive balance (overpaid, or holding a statement
   credit larger than its balance), **When** the operator opens the page, **Then** that
   balance increases rather than decreases the net liquid position, matching the corrected
   arithmetic established in issue #320.

---

### User Story 2 - Trace any line back to where it came from (Priority: P2)

A term in the waterfall looks wrong. The operator wants to see the individual accounts,
budgets, or transactions that produced it, and to get to the view that manages them without
hunting through the navigation.

**Why this priority**: Itemization and links turn the page from a statement into a
diagnostic tool, which is what the issue asks for. It depends on Story 1 existing but adds
distinct, separately testable value.

**Independent Test**: Load the page and confirm each itemized line names the individual
account or budget it came from, that the itemized values sum to the aggregate they sit
under, and that each aggregate line carries a working link to the corresponding view.

**Acceptance Scenarios**:

1. **Given** multiple active budget-funding accounts, **When** the operator opens the page,
   **Then** each account is listed by name with its own balance, and those balances sum to
   the aggregate budget-funding line.
2. **Given** multiple active standing budgets, **When** the operator opens the page,
   **Then** each standing budget is listed by name with its own current balance, and those
   balances sum to the aggregate standing budget line.
3. **Given** any account row in the itemization, **When** the operator looks at it,
   **Then** it shows both the raw ledger balance and the projected balance (ledger net of
   that account's unreconciled transactions), so a ledger figure that is several days stale
   cannot be mistaken for the current position.
4. **Given** any aggregate line in the waterfall, **When** the operator follows its link,
   **Then** they arrive at the view that manages the underlying data — accounts, reconcile,
   budgets, or the current pay period as appropriate.

---

### User Story 3 - Explain structurally unallocated money (Priority: P3)

The uncommitted figure is persistently non-zero and the operator wants to know whether that
is a real surplus or an artifact of the way accounts and budgets are set up — for instance a
savings account holding several earmarked standing budgets that no longer add up to its
balance, or a checking account that no standing budget claims at all.

**Why this priority**: This is the "why is it always off by this much" question. It is the
most valuable diagnostic on the page but also the one that depends on the most judgement,
so it is sequenced last and can ship after the waterfall itself is proven correct.

**Independent Test**: With a budget-funding account that no standing budget is linked to,
and separately with an account linked to standing budgets whose balances do not sum to it,
load the page and confirm each situation is called out by name with the amount involved.

**Acceptance Scenarios**:

1. **Given** an active budget-funding account that no standing budget is linked to,
   **When** the operator opens the page, **Then** the account is called out by name with its
   balance and an explanation that this balance is included in the uncommitted total with
   nothing allocating it.
2. **Given** a savings account linked to three standing budgets whose current balances sum
   to less than the account balance, **When** the operator opens the page, **Then** the page
   shows the account, each linked budget, the two totals, and the difference between them.
3. **Given** two standing budgets that are each linked to both of two accounts, **When** the
   operator opens the page, **Then** the page reports a single coverage group containing
   both accounts and both budgets, with the combined account total, the combined budget
   total, and the difference — rather than attempting to attribute any budget's balance to
   an individual account.
4. **Given** no structural mismatches of either kind exist, **When** the operator opens the
   page, **Then** the diagnostics section says so rather than rendering an empty region.

---

### Edge Cases

- **No accounts, no budgets, empty database**: every term is zero and the page renders a
  complete waterfall of zeros rather than failing or omitting lines.
- **An account that has never had a balance recorded**: the account contributes nothing to
  the totals, and the page says its balance is unknown rather than silently showing zero,
  because "no data" and "zero dollars" have very different meanings here.
- **Inactive accounts and inactive budgets**: excluded from every term, exactly as the
  notification excludes them, so the page and the banner cannot disagree.
- **The current date falls in a pay period with no transactions or allocations at all**:
  the pay period term is zero and the line still appears.
- **Negative running subtotals**: a net liquid position or uncommitted total below zero is
  a legitimate state (overdrawn, or over-allocated) and MUST be displayed as a negative
  amount, visually distinguished, not suppressed or shown as an absolute value.
- **A standing budget with a negative current balance**: subtracts a negative, i.e. raises
  the uncommitted total, and is displayed without special-casing.
- **No budget/account associations configured anywhere** (the state of every existing
  installation on upgrade): the waterfall is unaffected, every budget-funding account is
  reported as unlinked, and the page says the associations are not configured rather than
  implying every account is a problem.
- **A standing budget linked to an account that is inactive, or to a credit or investment
  account**: the association is still recorded and reported, but only active budget-funding
  accounts contribute to the waterfall, so the coverage group must show which of its
  accounts are excluded from the totals rather than quietly dropping them.
- **A standing budget linked to an account, where one of them is subsequently deleted**:
  the association disappears with it; no orphaned row and no error on the page.

## Requirements *(mandatory)*

### Functional Requirements

**The page and its arithmetic**

- **FR-001**: The application MUST provide a Cash Position page reachable from the main
  navigation of every page, at a stable URL.
- **FR-002**: The page MUST present the available-funds calculation as an ordered waterfall
  in which each line is a labeled term, each term shows whether it is added or subtracted,
  and a running total is carried down through two named subtotals to a final figure.
- **FR-003**: The waterfall MUST consist of these terms in this order: (1) combined ledger
  balances of active budget-funding accounts, added; (2) the adjustment for unreconciled
  transactions against those accounts, which converts ledger balances to projected
  balances; (3) the combined balances of active credit accounts, applied with the sign in
  which they are recorded — money owed is recorded negative and therefore reduces the
  total, while a credit account in credit raises it; giving the subtotal **Net liquid
  position**; then (4) the combined current balances of active standing budgets,
  subtracted; (5) the current pay period's allocated-but-not-yet-spent amount, subtracted;
  giving the final figure, **Truly unallocated / uncommitted funds**.
- **FR-004**: The final uncommitted figure MUST be numerically identical, including sign, to
  the difference between "available" and "allocated" that the existing notification banner
  reports, for every possible database state.
- **FR-005**: The page and the notification banner MUST derive their terms from a single
  shared calculation, so that the two can never drift apart as either changes.
- **FR-006**: The page MUST include exactly the same accounts and budgets that the
  notification includes — active budget-funding accounts, active credit accounts, active
  standing budgets, and the pay period containing the current date — and MUST NOT silently
  widen or narrow that set.
- **FR-007**: All monetary amounts on the page MUST be rendered in the application's
  configured currency format, and negative amounts MUST be visually distinguishable from
  positive ones.
- **FR-025**: The existing notification banner MUST keep its current wording and its
  existing per-term links, and MUST additionally link to the Cash Position page, so the
  page is discoverable at the moment the question arises. No other change to the banner is
  in scope.

**Itemization and traceability**

- **FR-008**: The budget-funding account term MUST be itemized by account, showing each
  account's name, its raw ledger balance, its unreconciled adjustment, and its resulting
  projected balance.
- **FR-009**: The credit account term MUST be itemized by account, showing each account's
  name and its balance.
- **FR-010**: The standing budget term MUST be itemized by budget, showing each budget's
  name and its current balance.
- **FR-011**: Every itemized group MUST display its own total, and that total MUST equal
  the corresponding aggregate term in the waterfall.
- **FR-012**: Each aggregate term MUST link to the view it derives from: account terms to
  the accounts view, the unreconciled adjustment to the reconcile view, the standing budget
  term to the budgets view, and the pay period term to the current pay period view.
  Individual itemized accounts and budgets MUST link to their own detail views where the
  application already provides them.
- **FR-013**: The page MUST state, in plain language next to the relevant lines, what each
  term means and why it is added or subtracted — in particular that credit balances are
  recorded negative when money is owed, since that sign convention is the source of the
  error corrected in issue #320.

**Standing budget / account links**

- **FR-014**: The application MUST allow a standing budget to be associated with the
  account or accounts that physically hold its money, and an account to be associated with
  any number of standing budgets. The association MUST be many-to-many: one savings account
  commonly holds several earmarked standing budgets, and a single budget may be spread
  across more than one account.
- **FR-015**: The association MUST be editable through the application's existing budget
  editing interface, MUST be optional (a standing budget with no linked account is a valid
  and expected state), and MUST NOT be offered for periodic budgets, which do not hold a
  balance.
- **FR-016**: Deleting or deactivating an account or a budget MUST NOT leave a dangling
  association or prevent the page from rendering.

**Diagnostics**

- **FR-017**: The page MUST identify active budget-funding accounts that no active standing
  budget is linked to, list them by name with their balances, and state that those balances
  are contributing to the uncommitted total with nothing allocating them.
- **FR-018**: The page MUST group linked accounts and standing budgets into **coverage
  groups** -- the maximal sets reachable from one another through the links -- and, for each
  group, show the accounts and their combined balance, the standing budgets and their
  combined balance, and the difference between the two totals.
- **FR-019**: Coverage groups MUST be reported at group level only. Because the
  many-to-many association records no split of a budget's balance across accounts, the page
  MUST NOT attribute any portion of a budget's balance to an individual account, and MUST
  NOT display a per-account delta for an account that shares a group with others.
- **FR-020**: A coverage group whose account total and budget total agree exactly MUST be
  shown as balanced rather than omitted, so that a group's absence from the page always
  means "not configured", never "checked and fine".
- **FR-021**: When no unlinked budget-funding account exists and every coverage group
  balances, the page MUST say so explicitly rather than rendering an empty section.

**Behaviour and robustness**

- **FR-022**: The page MUST render successfully against an empty database, an
  all-zero database, and a database in which any individual term is zero, missing, or
  negative — never a traceback in place of the calculation.
- **FR-023**: An account with no recorded balance MUST be shown as having an unknown
  balance and MUST contribute zero to the totals, so that missing data cannot be read as a
  balance of zero.
- **FR-024**: The page MUST report the point in time the figures represent (the current
  pay period, and the as-of dates of the underlying account balances), because a ledger
  balance days out of date is the single most likely reason a correct figure looks wrong.

### Key Entities

- **Cash position line**: One row of the waterfall. Has a label, an amount, a direction
  (added, subtracted, or a subtotal), an optional link to the view it derives from, an
  optional explanation, and optional itemized child lines.
- **Cash position statement**: The complete ordered set of lines, the two named subtotals,
  the final uncommitted figure, and the accompanying diagnostics. This is the single shared
  calculation that both the page and the notification banner consume.
- **Budget/account association**: A many-to-many relationship recording that a standing
  budget's money is held in a given account. Carries no amount and no split; it says only
  that the two are related. Optional on both sides.
- **Coverage group**: A maximal set of accounts and standing budgets reachable from one
  another through budget/account associations. Carries its accounts, its standing budgets,
  the combined balance of each side, and the difference between them. A group of one
  account and one budget reduces to the simple "this budget mirrors this account" case; a
  group with no budgets is an unallocated account.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Given any state of the operator's financial data, the page's final figure
  matches the discrepancy reported by the notification banner exactly — verified across a
  set of test scenarios that includes zero, positive, and negative values for every term.
- **SC-002**: An operator who wants to know why the available-funds figure looks wrong can
  reach every intermediate value from the main navigation in two clicks or fewer, without
  reading source code or issuing a database query.
- **SC-003**: Every aggregate term on the page can be followed to the view that produced it
  in a single click; 100% of the links resolve to a valid page.
- **SC-004**: The itemized values under each aggregate sum to that aggregate to the cent,
  in every test scenario.
- **SC-005**: The page renders without error for an empty database and for a database in
  which any single term is zero, absent, or negative.
- **SC-006**: A persistently non-zero uncommitted figure caused by an unallocated
  budget-funding account is explained on the page itself, with the responsible account
  named — no external investigation required.
- **SC-007**: For an account linked to several standing budgets, the page states the
  account total, the combined budget total, and their difference, and that difference
  matches an independent hand calculation to the cent.
- **SC-008**: An installation that has configured no budget/account associations at all
  sees a complete, correct waterfall and a diagnostics section that says the links are not
  configured — the feature degrades to exactly its pre-link behaviour rather than breaking
  or misreporting.
- **SC-009**: The schema change ships with a migration whose upgrade and downgrade paths
  both run cleanly against a database at the previous revision.

## Assumptions

- The page is read-only. It presents a calculation and links to the views where the
  underlying data is edited; it does not offer any way to change accounts, budgets, or
  transactions.
- The calculation is for the pay period containing the current date only. Choosing an
  arbitrary pay period is out of scope; the question the page answers is about now.
- The set of accounts and budgets included mirrors the existing notification exactly. Any
  change to *what* is counted belongs in a separate change, so that this feature can be
  verified purely as "the same number, shown in full".
- Investment accounts are neither budget-funding nor credit accounts and so appear nowhere
  in this calculation, matching the existing behaviour. The page does not attempt to
  account for them.
- The existing notification banner continues to appear on every page, with its wording
  unchanged; see the Clarifications section.
- Budget/account associations start out empty for every existing installation. The page
  must therefore be fully useful with none configured, and the diagnostics section must
  distinguish "not configured" from "configured and balanced".
- The page follows the application's existing visual conventions rather than introducing a
  new presentation style.
- Performance is not a design constraint: this is a single-operator, localhost application
  and the calculation already runs on every page load today.

## Clarifications

Resolved with the repository owner on 2026-09-08, before planning.

**Q1 — How is the correspondence between a standing budget and an account established?**
FR-017 and FR-018 both depend on knowing which standing budget, if any, accounts for a
given account's balance, and nothing records that relationship today.

*Answer*: Record it explicitly as a **many-to-many** association between standing budgets
and accounts. A single 1:1 link was rejected: one savings account commonly holds several
earmarked standing budgets, and the relationship is not necessarily 1:1 in either
direction.

*Consequence*: This feature includes a schema change and an Alembic migration with tested
upgrade and downgrade paths (constitution principle III). Because a many-to-many
association records no split of a budget's balance across the accounts it is linked to,
per-account deltas are not well defined; the page therefore reports deltas over **coverage
groups** (FR-018, FR-019) — the maximal sets of accounts and budgets reachable through the
links. This reduces to an exact per-account delta in the common one-account/one-budget and
one-account/many-budget cases, and stays honest in the general case instead of inventing
an allocation rule the application does not hold.

**Q2 — Does the existing notification banner's wording change?**

*Answer*: No. The banner keeps its current wording and its existing per-term links — that
text was corrected only recently under issue #320 and is covered by tests — and gains one
additional link to the new page (FR-025).

## Out of Scope

- Changing which accounts or budgets count toward available or allocated funds.
- Historical or projected cash position for any period other than the one containing today.
- Charts or graphs of the waterfall.
- Any editing capability on the new page. Budget/account associations are edited in the
  existing budget interface, not here.
- Recording how a standing budget's balance is split across the accounts it is linked to.
  The association says only that they are related; deltas are reported per coverage group
  because of that (FR-019).
- Any change to the notification banner beyond adding a link to the new page.
