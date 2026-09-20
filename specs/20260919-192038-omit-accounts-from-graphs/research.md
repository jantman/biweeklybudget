# Phase 0 Research: Omit Accounts From The Account Balances Chart

**Feature**: `specs/20260919-192038-omit-accounts-from-graphs`
**Spec**: [spec.md](./spec.md)
**Date**: 2026-09-19

The spec left no `[NEEDS CLARIFICATION]` markers — the two open questions in issue
#357 were answered by the maintainer before it was written. This document records
what was read in the existing code to turn those answers into a plan, and the
decisions that reading forced.

---

## R1: Where the flag lives on the model

**Decision**: `Account.omit_from_graphs = Column(Boolean, default=False)`, placed
immediately after `is_active` in `biweeklybudget/models/account.py`.

**Rationale**: Byte-identical to `Budget.omit_from_graphs`
(`biweeklybudget/models/budget_model.py:88`), which is the pattern the issue asks
to be mirrored and the name the maintainer chose. `default=False` is a Python-side
default applied on insert, so new Accounts are never omitted (FR-002). The column
is nullable, which is what makes FR-003 work without a data migration: every row
that exists at upgrade time gets `NULL`, and `NULL` is falsy everywhere it is read
(FR-004).

**Alternatives considered**:

- `nullable=False, server_default='0'` — would make the column tidier, but it
  departs from the Budget precedent, needs a server default that Alembic must keep
  in sync with the model (Constitution III requires an exact match), and buys
  nothing: no code path distinguishes `NULL` from `False`.
- A separate `account_chart_settings` table — a whole table for one boolean, with
  a join on the chart's hot path. Rejected as obviously disproportionate.

---

## R2: How the migration must be written

**Decision**: A single `op.add_column('accounts', sa.Column('omit_from_graphs',
sa.Boolean(), nullable=True))` with `op.drop_column` to reverse it, revising the
current head `3f7c2a91e04b` (`add_plaid_item_last_successful_update`).

**Rationale**: This is exactly the shape of
`6d37400ea9cd_add_omit_from_graphs_boolean_to_budget_.py`, the migration that added
the identical column to `budgets`. Constitution III requires the migration's column
definition to match the model's exactly; `Column(Boolean, default=False)` has no
server default and is nullable, so `sa.Boolean(), nullable=True` is the match. The
`migrations` tox environment compares head against the models and will catch any
drift.

**Alternatives considered**: Autogenerate. Per CLAUDE.md, autogenerate only works
if the test database is at head *before* the model changes. The manual route is
one `add_column` copied from an existing migration in the same repository, so the
setup cost of autogenerate buys nothing here. The generated file will still be run
in both directions before commit, and `tox -e migrations` remains the gate.

**Head verified**: `3f7c2a91e04b` is the sole head (confirmed by walking every
`revision`/`down_revision` pair under `biweeklybudget/alembic/versions/`). If
another feature merges a migration before this branch lands, `down_revision` must
be re-pointed at the new head.

---

## R3: How the chart endpoint excludes the account

**Decision**: Narrow the `accounts` name map in `AcctBalanaceChartView.get()`
(`biweeklybudget/flaskapp/views/index.py`) so that it holds only Accounts that are
both active and not omitted. The existing skip in the balance loop — which already
`continue`s when `accounts.get(bal.account_id)` returns `None` — then excludes the
omitted account from every row with no further change, and the pre-window seed
query `_balances_before()` is already driven by the same map.

**Rationale**: Issue #356 built precisely this mechanism one release ago and
documented why: the row is skipped rather than the `AccountBalance` query being
narrowed, so that a date whose *only* balance record belongs to an excluded account
still appears on the chart's horizontal axis. The spec commits to that same rule
for omitted accounts (FR-011, and the "Dates are anchored by all accounts"
assumption), so the two exclusions must feed the same map rather than become two
mechanisms with two behaviours. Composing them at the map (FR-013) also makes
"inactive *and* omitted" a non-event: the account is simply not in the map, once.

**Where the filter goes**: on the query that builds the map, not in a Python
comprehension guard. `Account.active_accounts(db_session)` already returns a
`Query`, so the view adds one `.filter()` for the omit flag. The filter must be
written to treat `NULL` as "not omitted" — `Account.omit_from_graphs.isnot(True)`
rather than `== False`, because in SQL `NULL = 0` is `NULL`, not true, and a
`== False` filter would silently drop every pre-upgrade Account from the chart.
**This is the single most dangerous line in the feature**, and User Story 4 exists
to catch it.

Verified against SQLAlchemy 2.0.52 with the MySQL dialect rather than assumed,
because the two candidate spellings differ exactly on the pre-upgrade rows:

| Written as | Compiles to | `NULL` row is |
|---|---|---|
| `omit_from_graphs.isnot(True)` | `omit_from_graphs IS NOT true` | charted (correct) |
| `omit_from_graphs.__eq__(False)` | `omit_from_graphs = false` | **dropped (wrong)** |

`IS NOT true` is valid MySQL and MariaDB syntax and yields true for `NULL`, so the
first spelling is the one to use. If a future dialect change makes it unavailable,
`or_(omit_from_graphs.is_(None), omit_from_graphs.__eq__(False))` is the portable
equivalent, confirmed to compile to `IS NULL OR = false`.

**Alternatives considered**:

- Extending `Account.active_accounts()` itself to also exclude omitted accounts.
  Rejected: that helper is the definition of "an Account that may be chosen" and is
  used by every account picker. Folding a chart-presentation concern into it would
  make flagging an account remove it from every dropdown, which is exactly the
  FR-014 violation this feature must not commit.
- A new `Account.charted_accounts()` static method alongside `active_accounts()`.
  Considered seriously and rejected for now: one caller, and the name would have to
  claim more than one chart's behaviour. The view composes `active_accounts()` with
  one filter, which keeps the "may be chosen" and "is plotted" rules visibly
  separate. If a second account chart ever appears, that is the moment to extract
  the helper.

---

## R4: The modal checkbox

**Decision**: Add `.addCheckbox('account_frm_omit_from_graphs',
'omit_from_graphs', 'Omit from graphs?')` to `accountModalDivForm()` in
`accounts_modal.js`, directly after the existing `Active?` checkbox, and the
matching read in `accountModalDivFillAndShow()`:

```js
if(msg['omit_from_graphs'] === true) { ...prop('checked', true); }
else { ...prop('checked', false); }
```

plus `account.omit_from_graphs = data['omit_from_graphs']` in
`AccountFormHandler.submit()` next to the existing `account.is_active` line.

**Rationale**: Identical in shape, wording and ordering to
`budgets_modal.js:114` and `budgets.py:274`. The strict `=== true` test is what
makes a `NULL` flag render as unticked rather than as `undefined` (FR-004); a
truthiness test would behave the same today but would not say so.

**No change needed** to `ModelAsDict.as_dict` or to the `/ajax/account/<id>`
endpoint: `as_dict` walks `vars(self)`, so a newly added column appears in the
response automatically. That is what makes FR-008 free.

**No validation** is added in `AccountFormHandler.validate()`. A checkbox arrives
as a JSON boolean and there is no invalid value to reject, which is why the Budget
handler does not validate its equivalent either.

---

## R5: Where the acceptance coverage goes, and why sample data is not changed

**Decision**: Add a new acceptance class beside the existing
`TestAcctBalanceChartExcludesInactiveAccounts` in
`biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`, using
`class_refresh_db` so it may set the flag on a sample Account and have the database
restored afterwards. **No Account in `sampledata.py` is flagged, and no Account is
added to it.**

**Rationale**: This was the main design question of the whole feature, and the
answer is not the obvious one. Flagging an existing sample Account, or adding a
new "Mortgage" one, would look like the natural way to cover the feature — but the
sample data is shared by the entire acceptance suite. Flagging `InvestmentOne`
would break the chart key lists asserted in at least
`test_response_shape_is_unchanged` and
`TestAcctBalanceChartExcludesInactiveAccounts.test_inactive_account_is_not_a_series`;
adding an account would additionally change the Accounts page, the Cash Position
page, every pay period total and every account dropdown, across dozens of tests.
Every one of those edits would be a test changed to accommodate the feature rather
than to describe it — the thing Constitution II and SC-006 forbid.

`class_refresh_db` exists in `conftest.py` for exactly this ("to be used on classes
that alter data") and is already used by five classes in this same file. The new
class sets the flag, asserts the exclusion, and the dump is restored for whatever
runs next.

**Which account to flag in the test**: `InvestmentOne` (id 5). It is active, has
recorded balances inside the window, and — unlike `BankOne` — is not the account
whose specific values other tests in the file assert. Flagging an *active* account
is also the point: it proves the new exclusion is doing the work rather than
`is_active` doing it.

**Alternatives considered**: a unit test against the view. Rejected as
insufficient rather than wrong — the endpoint's contract is a JSON document, and
the existing coverage for both #279 and #356 tests it by fetching that document.
A unit test that stubbed the session would not have caught the `NULL`-handling
trap in R3.

---

## R6: Documentation surface

**Decision**: Four documentation touches, all required in this change by
Constitution IV:

1. `docs/source/app_usage.rst` — the **Account Balances Chart** section gains a
   short subsection on leaving an account out, written to sit alongside the
   existing "Accounts with no recent balances", and pointing at the Account modal.
   The **Charts** section's legend bullet gains a pointer to it, mirroring how the
   Spending Charts section already points at the Budget flag.
2. `docs/source/http_api.rst` — the `POST /forms/account` request-field list gains
   `omit_from_graphs`; the Account Balance Chart Data section's `keys` description
   is corrected.
3. Screenshots — `account1` and `account1-plaid` both show the Edit Account modal
   and will both change, so both are regenerated and committed (per the
   maintainer's standing preference to review screenshot changes in the PR). The
   index-page screenshot does **not** change, because no sample Account is flagged.
4. `CHANGES.rst` — one concise bullet under `Unreleased`, per Constitution VI.

**A pre-existing documentation defect is fixed here** (FR-020):
`http_api.rst` currently says the chart's `keys` "Includes inactive accounts". That
became untrue when #356 merged and was missed. This change narrows `keys` again, so
the sentence is rewritten once to describe both exclusions rather than left to
accumulate a second error.

**Changelog link caution**: the `CHANGES.rst` entry must *not* link to the new
`app_usage.rst` subsection. A changelog link to a docs anchor added in the same
pull request fails `tox -e docs` linkcheck; the section is named in prose instead.

---

## R7: What this feature must be able to prove it did not touch

**Decision**: User Story 3 (FR-014) is verified by *absence of change*, which needs
a deliberate statement of where to look rather than a test that can be written
mechanically.

The paths that read Accounts and must be unaffected, confirmed by reading them:

| Path | Reads accounts via | Affected? |
|---|---|---|
| Accounts page tables | `db_session.query(Account).filter(acct_type==...)` | No — never consults the flag |
| Account pickers (6 forms) | `Account.active_accounts()` | No — R3 keeps the filter out of that helper |
| Cash Position, pay periods, index totals | their own active-account queries | No |
| Transactions / OFX table filters | unfiltered `query(Account)` | No |
| Reconcile, transfers, Plaid updater | account id lookups | No |
| Stale-data warnings | `Account.is_stale` | No |
| Account Balances chart | `AcctBalanaceChartView.get()` | **Yes — the only one** |

**Rationale**: the single-call-site table above is the real argument that this
feature is safe, and it is only true because of the R3 decision to keep the filter
in the view rather than in `active_accounts()`. It is reproduced in the plan's
Constitution Check for that reason.
