# Phase 0 Research: Exclude Inactive Accounts From Dropdowns And The Balances Chart

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-19

The spec left no `NEEDS CLARIFICATION` markers. What this phase resolves instead is
*how* to implement each requirement inside the existing code, where more than one
mechanism was plausible and the choice materially changes the size and risk of the
change. Each section states the decision, why, and what was rejected.

---

## R1. How an inactive Account is kept on an existing record's form

**Decision**: On the three modals that edit or replay an existing record, keep the
Account select populated from an active-only map, and — when the record's own Account
is not among its options — append one option for it using the account name the AJAX
payload already carries, then select it.

`/ajax/transactions/<id>` sets `d['account_name']`
(`views/transactions.py:265`) and `/ajax/scheduled/<id>` sets `d['account_name']`
(`views/scheduled.py:206`). Both are already in the JSON the fill functions receive.

**Rationale**:

- It is the pattern this codebase already uses for exactly this problem, twice over:
  `selectBudget()` re-adds an inactive budget in `transactions_modal.js:142-159`, and
  `transModalDivFillAndShow()` already re-adds a deactivated credit-payment account in
  `transactions_modal.js:100-110` using `msg['credit_payment_acct_name']`. Following it
  means no new mechanism and no new vocabulary.
- Using `msg['account_name']` rather than a client-side lookup means the *full* account
  map does not have to be shipped to any page that only hosts entry forms. That turns
  out to remove work rather than add it (see R2).

**Alternatives considered**:

- *Ship both `acct_names_to_id` and `active_acct_names_to_id` to every page and look the
  name up client-side*, as `selectBudget()` does for budgets. Rejected: `selectBudget()`
  needs the lookup only because the budget AJAX payload does not carry the name for each
  split; the account payloads do. Doing the lookup anyway would require either moving
  `getObjectValueKey()` out of `transactions_modal.js` into `forms.js` (it is not loaded
  on `scheduled.html`), which churns the generated jsdoc, or duplicating it.
- *Mark the re-added option "(inactive)"*. Rejected: the spec's Assumptions rule it out,
  and no existing re-added option is marked either.

## R2. Which pages get which account map

**Decision**: Introduce a second template variable, `active_acct_names_to_id`, alongside
the existing `acct_names_to_id`, and give each page only the map(s) its scripts consume.
After R1 removed the need for a client-side name lookup, the full map is needed by
exactly two consumers, both of which filter a table of existing rows:
`transactions.js:164` and `ofx.js:127`.

| Template | `acct_names_to_id` | `active_acct_names_to_id` | Consumers |
|---|---|---|---|
| `index.html` | removed | added | `account_transfer_modal.js` |
| `accounts.html` | removed | added | `account_transfer_modal.js` |
| `budgets.html` | removed | added | `budget_transfer_modal.js` |
| `fuel.html` | removed | added | `fuel.js` |
| `scheduled.html` | removed | added | `scheduled_modal.js` |
| `payperiod.html` | removed | added | `transactions_modal.js`, `scheduled_modal.js`, `payperiod_modal.js`, `budget_transfer_modal.js` |
| `reconcile.html` | **kept** | added | `ofx.js` (filter) + `transactions_modal.js`, `scheduled_modal.js` |
| `transactions.html` | **kept** | added | `transactions.js` (filter) + `transactions_modal.js` |
| `ofx.html` | **kept** | not added | `ofx.js` (filter) only |

**Rationale**: A template variable with no consumer is dead code that the next reader has
to disprove. Removing `accts` where nothing reads it any more is part of making the
change honest, and the acceptance suite proves each removal (every one of these pages has
tests that read its selects).

**Alternatives considered**:

- *Leave `acct_names_to_id` on every page and just change what it contains per page.*
  Rejected outright: the same JavaScript global would mean "all accounts" on
  `transactions.html` and "active accounts" on `index.html`, with nothing in either file
  saying so. That is how this bug happens again.
- *Keep passing the full map everywhere for symmetry.* Rejected as above — six templates
  would carry a variable nothing reads.

## R3. Where the active-only query lives

**Decision**: Add a static method `Account.active_accounts(db)` returning a query for
active Accounts ordered by name, and build every active-only map from it.

**Rationale**: The same one-line dict comprehension over `db_session.query(Account)`
appears in eleven view methods; that duplication is what let the filter be forgotten in
all of them at once. `Account.active_credit_accounts(db)` (`models/account.py:264`)
already establishes the shape, name and docstring style for exactly this, and is used the
same way from four views. One method means one place to get the filter right, and it is
unit-testable without a browser.

**Alternatives considered**:

- *A module-level helper in a views module*, like `budget_source_accounts()` in
  `views/budgets.py:77`. Rejected: it would have to be imported across eight view
  modules, whereas `Account` already is.
- *Inline `.filter(Account.is_active.__eq__(True))` in each view*, matching how the
  `budgets`/`active_budgets` loop is duplicated. Rejected: that duplication is the
  precedent that caused this bug, not one to extend.

## R4. How the chart excludes inactive Accounts

**Decision**: In `AcctBalanaceChartView.get()`, build `accounts` from
`Account.active_accounts()` instead of all Accounts, keep the `AccountBalance` query
unchanged, and skip any balance row whose `account_id` is not in `accounts`
(`accounts.get(...)` → `continue`).

**Rationale**: `keys`, `datedict` and the forward-fill are all derived from `accounts`,
so filtering that one dict excludes the account from the series list, from every data
point and from the carried-forward seed in one move. `_balances_before()` already guards
with `accounts.get(bal.account_id)` and `continue` (`views/index.py:357-359`), so it needs
no change at all — it simply stops seeing inactive accounts.

Leaving the `AccountBalance` query unfiltered is deliberate. The set of dates in the
response is the set of dates on which *some* balance row exists; narrowing the query to
active accounts would silently drop any date whose only balance row belonged to an
inactive account, which FR-003 forbids. Skipping the row after it is read preserves the
date set exactly while still excluding the account from every row's values.

**Alternatives considered**:

- *Filter the query with `AccountBalance.account_id.in_(accounts.keys())`*. Slightly
  cheaper, and tempting. Rejected because of the date-set change described above: on an
  installation where a closed account's last balance landed on a date no active account
  recorded, the chart would lose a date it shows today. Cheaper is not worth a silent
  change to the x-axis, and the cost saved is bounded by rows this endpoint already reads.
- *Delete inactive accounts' `AccountBalance` rows.* Rejected outright — destructive, and
  FR-004/FR-016 forbid it. Reactivating an account must restore its full history.

## R5. Whether to reject inactive Accounts server-side on save

**Decision**: No new server-side validation. Only the client-side lists change.

**Rationale**: `AccountTransferFormHandler.validate()` (`views/accounts.py:338`, `:355`)
already rejects inactive accounts, and that stays. Adding the same rejection to the
transaction, scheduled-transaction or fuel-fill handlers would break FR-011 directly: a
user opening an old transaction whose account has since been closed must be able to save
it, and that save posts the inactive account id. There is no way to distinguish "chose an
inactive account" from "left the inactive account alone" on the wire, so the correct
place for this rule is the list of options, which is where the spec puts it.

## R6. Existing tests that assert the current (wrong) behaviour

**Decision**: Update the assertions to the new expected behaviour, and add new tests for
what is newly guaranteed. Twenty-two acceptance assertions currently expect
`['6', 'DisabledBank']` in an account select; twenty of them are entry forms and must
lose it, and two are table filters and must keep it:

| Keeps `DisabledBank` (filters) | Loses `DisabledBank` (entry forms) |
|---|---|
| `test_ofx.py:204` (`account_filter`) | `test_index.py:526,545`; `test_accounts.py:1144,1163,1300,1319` (`acct_txfr_frm_*`) |
| `test_transactions.py:197` (`account_filter`) | `test_budgets.py:626,775`; `test_payperiods.py:2223` (`budg_txfr_frm_account`) |
| | `test_transactions.py:358,430,554,1581,1756`; `test_payperiods.py:1139,1327,1461` (`trans_frm_account`) |
| | `test_scheduled.py:202` (`sched_frm_account`) |
| | `test_fuel.py:464` (`fuel_frm_account`) |
| | `test_payperiods.py:2880` (`skipschedtrans_frm_account`) |

`test_index.py:655-656` asserts the chart's `keys` and must drop `'DisabledBank'`.

**Rationale**: These assertions are correct records of today's behaviour, which is the
bug. Changing them is the point of the change, not an accommodation to it — and the split
above is itself the evidence that FR-014's boundary is respected, since two of them do
not change.

## R7. Suites to run

**Decision**: Unit and acceptance suites in full. Migrations and Docker suites are not
required.

**Rationale**: Constitution Principle II requires unit and acceptance in full for any
feature, and migrations/Docker "for any change that touches schema or packaging". This
change touches neither — no model column, no migration, no packaging file (FR-016). Per
the project memory note, `tox -e docker`'s final acceptance step is also known to be
killed for low memory on this host and is left to CI.

`tox -e docs` must build clean (Principle IV). No `docs/source/` prose describes the
account dropdown contents, so the documentation obligation for this change is the
`CHANGES.rst` entry plus the spec artifacts; this is confirmed in T-docs during
implementation rather than assumed.
