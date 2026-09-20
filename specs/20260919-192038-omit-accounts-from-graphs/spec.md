# Feature Specification: Omit Accounts From The Account Balances Chart

**Feature Branch**: `robot-army/issue-357-allow-excluding-accounts-from-the-index`

**Created**: 2026-09-19

**Status**: Draft

**Input**: GitHub issue [#357](https://github.com/jantman/biweeklybudget/issues/357) — "Allow excluding Accounts from the index page Account Balances chart" (labels: enhancement, robot-army). Found while working through the 2.0.0 release verification checklist, [#353](https://github.com/jantman/biweeklybudget/issues/353).

## Background

The **Account Balances** chart on the index page plots one line per account. A
single account whose balances are orders of magnitude larger than the rest — a
mortgage is the example the issue gives — sets the vertical scale for every
other line, flattening them into an unreadable band along the bottom. The chart
is then close to useless for the accounts the user actually wants to watch day
to day.

Two things already exist and neither solves it:

- Legend click-to-hide (issue [#215](https://github.com/jantman/biweeklybudget/issues/215),
  documented under "Charts" in the usage guide) hides a line for the current visit
  only. Nothing is saved, so the chart comes back at full size on the next page
  load, and the user re-hides the same account every time.
- Deactivating the account (issue [#356](https://github.com/jantman/biweeklybudget/issues/356))
  does remove it from the chart, but it also removes it from every account
  picker and every balance total. A mortgage a user is actively paying is not
  an account they are finished with, so that is the wrong tool.

What is missing is a persistent, per-account "don't plot this" preference that
changes nothing else about the account. The Budgets page already has exactly
this shape of setting — the **Omit from graphs?** checkbox on the Budget modal,
which keeps a budget out of the Budgets-page line charts and starts it unticked
on the Spending Charts page — so an Account-level equivalent is the consistent
answer rather than a new mechanism.

### Decisions taken during specification

The issue explicitly left two things to be settled here. Both were put to the
maintainer and answered:

1. **What the flag means**: the omitted account is **not in the chart data at
   all** — no series, no values, no legend entry — rather than being sent and
   drawn hidden. This is the reading the issue itself leaned toward, it is the
   only one that makes the endpoint cheaper (the concern behind issue
   [#279](https://github.com/jantman/biweeklybudget/issues/279)), and it matches
   what `Budget.omit_from_graphs` already does to the Budgets-page line charts.
2. **What the flag is called**: `omit_from_graphs`, the same name and the same
   modal label as the Budget flag, described as covering charts that plot
   accounts. Today that is only the Account Balances chart.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A dominating account stops flattening the chart (Priority: P1)

A user whose mortgage balance dwarfs every other account opens the Account
modal for it, ticks **Omit from graphs?**, and saves. Back on the index page,
the Account Balances chart no longer plots the mortgage: its line and its
legend entry are gone, and the remaining accounts are rescaled to fill the
chart instead of being pressed flat along the bottom.

**Why this priority**: This is the whole point of the feature. Everything else
in this spec exists to make this change safe.

**Independent Test**: With sample data in which one account is flagged, request
the Account Balances chart data: the flagged account is in neither the series
list nor any data point, and the unflagged accounts' values are identical to
what they were before the flag was set.

**Acceptance Scenarios**:

1. **Given** an Account marked omit-from-graphs that has recorded balance history, **When** the Account Balances chart data is requested, **Then** that Account appears neither in the chart's series list nor in any data point.
2. **Given** several Accounts of which one is marked omit-from-graphs, **When** the chart data is requested for any history window, **Then** every other Account's series is identical to what it was before the flag was set.
3. **Given** an Account marked omit-from-graphs whose only balance records fall before the requested history window, **When** the chart data is requested, **Then** no carried-forward value for it is emitted either.
4. **Given** the index page is open, **When** the flag is changed and the page is reloaded, **Then** the chart reflects the change immediately, with no cache to clear and no stored data removed.

---

### User Story 2 - Setting and clearing the flag (Priority: P1)

A user opens an Account from the Accounts page, sees an **Omit from graphs?**
checkbox on the modal showing that account's current setting, ticks or unticks
it, and saves. The setting sticks: reopening the modal shows it as saved, and
it survives until the user changes it again.

**Why this priority**: Without a way to set it the flag is unreachable, so this
ships in the same change as User Story 1, not after it.

**Independent Test**: Open an Account's modal, tick the checkbox, save, reopen
the modal; the checkbox is ticked and the stored Account records it. Untick,
save, reopen; it is unticked.

**Acceptance Scenarios**:

1. **Given** the Add Account modal, **When** it is opened, **Then** it shows an **Omit from graphs?** checkbox, unticked.
2. **Given** a new Account saved with the checkbox unticked, **When** it is stored, **Then** it is not omitted from graphs, and it is plotted on the chart.
3. **Given** an existing Account that is not omitted, **When** its modal is opened, **Then** the checkbox is unticked; **When** it is ticked and saved, **Then** the Account is stored as omitted.
4. **Given** an existing Account that is omitted, **When** its modal is opened, **Then** the checkbox is ticked; **When** it is unticked and saved, **Then** the Account is stored as not omitted and its line returns to the chart.
5. **Given** an Account's modal is saved with no change to the checkbox, **When** the Account is reloaded, **Then** its omit-from-graphs setting is unchanged.

---

### User Story 3 - The flag changes nothing but the chart (Priority: P1)

A user flags their mortgage. It is still listed on the Accounts page with its
balance, still counted in every total, still offered in every account picker,
still reconcilable, and still updated by Plaid. Only its line on the Account
Balances chart is gone.

**Why this priority**: The feature is only safe if its blast radius is exactly
one chart. An account the user is actively paying must not quietly drop out of
their balances or their arithmetic — that would make this setting dangerous to
use, which is the failure mode that made deactivation the wrong tool in the
first place.

**Independent Test**: Flag an account in sample data and compare the Accounts
page, Cash Position page, pay period figures, account pickers and stale-data
warnings against the same pages before the flag was set. All are unchanged.

**Acceptance Scenarios**:

1. **Given** an Account marked omit-from-graphs, **When** the Accounts page is loaded, **Then** the Account is listed exactly as before, with its balance, unreconciled sum and difference.
2. **Given** an Account marked omit-from-graphs, **When** any form with an Account picker is opened, **Then** the Account is offered exactly as before (subject to the active/inactive rules from issue [#356](https://github.com/jantman/biweeklybudget/issues/356), which this feature does not change).
3. **Given** an Account marked omit-from-graphs, **When** the index page, Cash Position page or any pay period page is loaded, **Then** every balance, total and projection including that Account is unchanged.
4. **Given** an Account marked omit-from-graphs, **When** its data is downloaded, reconciled, or transferred to and from, **Then** all of that behaves exactly as before.
5. **Given** an Account marked omit-from-graphs whose data is stale, **When** any page is loaded, **Then** the stale-data warning for it still appears.

---

### User Story 4 - Existing accounts keep their chart line after upgrade (Priority: P1)

A user upgrades to a version containing this feature. Their Account Balances
chart looks exactly as it did before: every account they had is still plotted,
because none of them is flagged.

**Why this priority**: A schema change that silently changed which accounts are
charted would be a data-presentation regression delivered by an upgrade, with
no action by the user and nothing on screen to explain it.

**Independent Test**: Upgrade a database populated before this change, then
request the chart data. Every account that was plotted before is plotted after.

**Acceptance Scenarios**:

1. **Given** a database created before this feature, **When** it is upgraded, **Then** every existing Account is not omitted from graphs, and the chart's series list is unchanged.
2. **Given** an upgraded database, **When** an Account whose flag has never been set is charted, **Then** it is plotted.
3. **Given** a database upgraded and then reverted to the previous schema version, **When** the revert completes, **Then** it succeeds and no Account data other than the flag itself is lost.

---

### Edge Cases

- **Every Account is flagged.** The chart data comes back with an empty series list and an empty set of rows, with a success status rather than an error — the same shape as a database with no balance records at all.
- **A flagged Account is the only one with a balance recorded on some date.** That date is still returned, carrying the other accounts' forward-filled values, so flagging an account does not punch holes in the chart's horizontal axis. This is the same rule issue #356 established for inactive accounts, and it is deliberately the same mechanism.
- **An Account is both inactive and flagged.** It is excluded once, not twice; there is no error and no duplicate handling. Either condition alone is enough to keep it off the chart.
- **A flagged Account's balance records.** They are stored, kept and never deleted. Unticking the flag restores the account's full line, including the history recorded while it was flagged.
- **The flag is changed while the index page is open.** The open page keeps the data it was drawn with; the chart reflects the change on the next load or the next time the range buttons refetch it. No live push is added.
- **A script reading the chart endpoint directly.** The response keeps its existing shape — `data` and `keys` — so a caller that does not know about this feature keeps working; it simply receives fewer series once the user flags an account.

## Requirements *(mandatory)*

### Functional Requirements

**The setting itself**

- **FR-001**: An Account MUST carry a persistent boolean setting indicating that it is to be omitted from charts that plot accounts, named and labelled consistently with the equivalent Budget setting.
- **FR-002**: The setting MUST default to "not omitted" for a newly created Account.
- **FR-003**: Every Account that exists before this feature is installed MUST be treated as "not omitted", so that upgrading changes nothing about what is charted.
- **FR-004**: An Account whose setting has never been recorded MUST be treated as "not omitted" wherever it is read, rather than raising an error or being skipped.

**Setting it from the UI**

- **FR-005**: The Add/Edit Account modal MUST offer a checkbox for this setting, unticked when adding a new Account.
- **FR-006**: Opening the modal for an existing Account MUST show the checkbox in the state that Account is stored with.
- **FR-007**: Saving the modal MUST store the checkbox's state on the Account, whether it was changed or left alone.
- **FR-008**: The setting MUST be readable from, and writable through, the existing single-Account and Account-form HTTP endpoints, alongside the Account's other fields.

**The chart**

- **FR-009**: The Account Balances chart data MUST exclude every omitted Account from its series list.
- **FR-010**: The Account Balances chart data MUST exclude every omitted Account from every data point, including the carried-forward values used to keep a line continuous across a history window.
- **FR-011**: Excluding an omitted Account MUST NOT change any other Account's values, the set of dates returned, the ordering of dates, or the response's overall shape.
- **FR-012**: Balance records belonging to omitted Accounts MUST remain stored and MUST NOT cause an error when encountered; they are skipped, not deleted.
- **FR-013**: Exclusion by this setting MUST compose with the existing exclusion of inactive Accounts: an Account is charted only if it is active *and* not omitted, and an Account that is both inactive and omitted MUST be handled without error.

**What must not change**

- **FR-014**: The setting MUST have no effect on anything but charts that plot accounts. Account balances, totals, pay period arithmetic, Cash Position, reconciliation, transfers, Plaid updates, stale-data warnings and every Account picker MUST behave exactly as they do today for an omitted Account.
- **FR-015**: The Accounts page MUST continue to list omitted Accounts exactly as it lists any other Account; no new column, greying or marking is added to its tables.
- **FR-016**: Legend click-to-hide on the Account Balances chart MUST continue to work as it does today for the Accounts that are plotted, and MUST remain unsaved between visits.
- **FR-017**: The chart response MUST keep its existing `data`/`keys` shape so that existing callers of the endpoint keep working.

**Schema and documentation**

- **FR-018**: The schema change MUST ship with a reversible migration whose upgrade and downgrade are both exercised, and whose column definition matches the model exactly.
- **FR-019**: The documentation describing the Account Balances chart, the Accounts page and the affected HTTP endpoints MUST be updated in the same change to describe the new setting.
- **FR-020**: The HTTP API documentation's existing claim that the chart's `keys` "Includes inactive accounts" MUST be corrected, since issue #356 already made it untrue and this feature narrows `keys` further.

### Key Entities

- **Account**: A financial account. Gains one new attribute — whether to omit it from charts that plot accounts — which is presentation-only and never enters any financial calculation.
- **Account Balance**: A dated ledger balance belonging to an Account. Unchanged. Records belonging to omitted Accounts are retained and simply not charted.
- **Budget**: Unchanged, but the source of the pattern being followed: its existing "omit from graphs" setting defines the name, the modal label and the meaning adopted here.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With sample data containing one Account marked omit-from-graphs, the Account Balances chart data contains that Account in zero series and zero data points, while every other Account's data is byte-for-byte what it was before the flag was set.
- **SC-002**: A user can turn the setting on and off for an Account entirely from the Account modal, in one save each way, with the result visible on the index page after a reload.
- **SC-003**: With an Account flagged, the Accounts page, Cash Position page, pay period pages, account pickers and stale-data warnings are all identical to their output with the flag cleared — the only difference anywhere in the application is the chart.
- **SC-004**: The migration applies to a database at the previous head and reverses back to it, both directions verified, and the `migrations` suite confirms the schema matches the models.
- **SC-005**: A database upgraded from the previous schema charts exactly the Accounts it charted before the upgrade.
- **SC-006**: The complete unit and acceptance suites pass, with new tests covering the endpoint's exclusion of flagged Accounts and the modal's read/write of the checkbox, and with no existing assertion weakened or removed to accommodate a failure.
- **SC-007**: The `docs` suite builds without errors, and the Account Balances chart, Accounts page and HTTP API documentation each describe the new setting.

## Departures taken during implementation

Recorded late, and that is itself the first thing to note. Constitution V
requires a deviation to be recorded here and committed *before* it is acted on.
Both of these were made mid-implementation and written up afterwards, once
[#366](https://github.com/jantman/biweeklybudget/pull/366) had already merged
the code containing them. Whether Constitution V reaches them at all is
arguable, since it governs "side quests" that depart from the feature and both
of these stayed inside it -- but that is a reason the rule may not apply, not a
reason to have claimed it was followed.

1. **A migration round-trip test was added**
   (`biweeklybudget/tests/migrations/test_migration_8a3d61c0fe57.py`), which the
   task breakdown did not call for. Constitution III requires both migration
   directions to be tested before commit, and this repository's mechanism for
   that is a per-migration test class; the task as written would have satisfied
   the principle by running the migration by hand, leaving nothing behind. The
   test also asserts the `IS NOT true` / `= false` divergence on a `NULL` row
   directly, so the constraint the chart view has to satisfy is pinned in the
   migration's own test rather than only in a comment.

2. **`AccountFormHandler.submit()` reads the new field with
   `data.get('omit_from_graphs', False)`**, not `data['omit_from_graphs']` as
   the task specified. Written as specified -- mirroring the adjacent
   `data['is_active']` -- it raises `KeyError` for any POST that omits the key,
   which several existing tests do and any external script written against an
   older version would. FR-008 and the HTTP contract both describe the field as
   optional, so `.get()` is what they require. Found by running the full
   acceptance suite, not by review.

## Assumptions

- **The Budget flag is the model, deliberately.** The issue asks for "an Account-level equivalent" of `Budget.omit_from_graphs`, and the maintainer confirmed the same name and the same modal label. This buys a user one concept rather than two, and a reviewer one pattern rather than two.
- **"Omitted" means absent from the data, not hidden in the UI.** Confirmed with the maintainer. The endpoint stops returning the account; nothing is sent to the browser to be drawn hidden. A one-off look at an omitted account is had by unticking the flag, not from the legend — the legend remains the tool for a temporary hide of a *plotted* account.
- **The name is broader than today's single use.** `omit_from_graphs` is documented as covering charts that plot accounts. Only one such chart exists today, so today the setting means exactly "keep this off the Account Balances chart". A future account chart would be expected to honour it rather than grow a second flag.
- **Dates are anchored by all accounts, not just charted ones.** A date whose only balance record belongs to an omitted account is still returned. This matches what issue #356 settled for inactive accounts and reuses the same mechanism, so there is one rule about the chart's horizontal axis rather than two.
- **No new column on the Accounts page.** The setting is visible on the modal, which is where every other Account setting lives. The Accounts page tables show balances and reconciliation state, and adding a graph-presentation column to all three of them would cost more than it tells the user. The Budgets page makes the same choice for the Budget flag.
- **Sample data will carry a flagged Account.** Acceptance coverage of the exclusion needs an account that is flagged, which means the test fixture data grows one such account or flags an existing one. Assertions elsewhere that enumerate the chart's accounts will need updating to match, and that is part of this change rather than a weakening of those tests.
- **This feature is independent of issue #356 and builds on it.** #356 is already merged; its active-account filter is in place and is extended, not replaced. Nothing here reopens or revises it.
- **No setting, environment variable or configuration is added.** The choice is per-account and lives with the account.
