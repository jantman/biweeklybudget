# Phase 0 Research: Show Inactive Accounts So They Can Be Re-Activated

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-17 | **Issue**: [#276](https://github.com/jantman/biweeklybudget/issues/276)

All Technical Context entries were resolved from the existing codebase; nothing required
an outside source. Findings below are recorded as Decision / Rationale / Alternatives.

---

## R1: Where the account actually disappears

**Finding**: `is_active` persists correctly. `AccountFormHandler.submit()`
(`biweeklybudget/flaskapp/views/accounts.py:281`) writes `account.is_active = data['is_active']`
on every save, and `accountModalDivFillAndShow()`
(`biweeklybudget/flaskapp/static/js/accounts_modal.js:131`) reads it back into the checkbox.
The account is lost purely because the Accounts page filters it out of its own queries.

Both `AccountsView.get()` and `OneAccountView.get()` render `accounts.html` with three
queries each, all carrying `Account.is_active == True`
(`views/accounts.py:94,97,100` and `:137,140,143`). Nothing else has to change for the
account to become reachable again.

**Decision**: Drop the `is_active` filter from those six queries. No model change, no
form-handler change, no JavaScript change to the modal.

**Rationale**: The narrowest edit that fixes the reported defect. The modal already round-trips
the flag; the only broken link in the chain is the listing query.

**Alternatives considered**:
- *A separate "Inactive Accounts" panel or an `/accounts/inactive` page.* Rejected: a second
  place to look for accounts, when the issue's complaint is that accounts are not where you
  look for them. The issue explicitly asks for them inline and greyed.
- *A "reactivate" button or endpoint.* Rejected: the edit modal already has the checkbox that
  does this; it is only unreachable. Adding a second write path for one boolean would mean
  two ways to set the same field.

---

## R2: The two near-identical view methods

**Finding**: `AccountsView.get()` and `OneAccountView.get()` are the same 35 lines twice,
differing only in `OneAccountView` also passing `account_id` to the template. Both contain the
three filtered queries, so the fix has to be applied identically in both places — which is the
same duplication that let the defect exist in two routes at once.

**Decision**: Extract the shared body into one module-level helper that both `get()` methods
call, with `account_id` as an optional argument. Remove the `is_active` filter once, in the
helper.

**Rationale**: The duplicate is the direct cause of having to make the same edit twice, and it
is six lines from the code being changed. Leaving it means the next change to this page has
the same chance of being half-applied. The refactor is mechanical, and both routes already
have acceptance coverage (`TestAccountsMainPage` for `/accounts`, `test_11_get_acct1_url` and
`test_41_get_acct4_url` for `/accounts/<id>`).

**Alternatives considered**:
- *Edit both copies and leave them duplicated.* Rejected as above; it is more total lines
  changed than the extraction, for a worse result.
- *A wider refactor of the other views that build the same `accts`/`budgets` dictionaries
  (`index.py`, `reconcile.py`, `budgets.py`, `payperiods.py`).* Rejected: out of scope, and
  Principle V treats undirected scope growth as a defect. Confined to the two methods that
  render `accounts.html`.

---

## R3: How to present "inactive" — which existing pattern

**Finding**: Three existing patterns grey inactive rows with the same CSS class,
`tr.inactive` (`static/css/custom.css:7`, `background-color: #d9d9d9 !important`):

| Page | Mechanism | Also shows an "Active?" column |
|------|-----------|-------------------------------|
| Scheduled Transactions | `static/js/scheduled.js:92`, DataTables `fnRowCallback` adds the class | no |
| Projects / BoM Items | `static/js/projects.js:201`, `static/js/bom_items.js:129`, same | no |
| Budgets | `templates/budgets.html:80,109`, server-rendered `{% if b.is_active %}<tr>{% else %}<tr class="inactive">{% endif %}` | **yes**, first column, `yes` / `NO` in `#a94442` |

**Decision**: Follow the **Budgets** pattern exactly — a server-rendered conditional `tr`
class plus a leading "Active?" column rendering `yes`, or `NO` in the same red
(`style="color: #a94442;"`).

**Rationale**: The issue names Scheduled Transactions, but that page is DataTables-driven and
Accounts is a plain server-rendered Jinja table; the Budgets page is the same shape and
already pairs the greyed row with an explicit column. Grey alone is a weak signal on a page
of striped rows (`table-striped` already alternates greys), so the column is what actually
makes the state readable — which is why Budgets has it. Reusing `tr.inactive` means no new
CSS.

**Alternatives considered**:
- *Grey row only, no column.* Rejected: `table-striped` alternates row backgrounds already,
  so `#d9d9d9` against the striped `#f9f9f9` is a subtle difference to hang a financial
  distinction on. Spec SC-003 requires identifying inactive accounts from the page alone.
- *A new CSS class or a badge.* Rejected: new styling for a state the application already
  styles three ways.
- *"Active?" as the last column.* Rejected: Budgets puts it first; matching it costs nothing.

---

## R4: Stale-data highlighting on inactive rows

**Finding**: Each account row renders `{% if acct.is_stale %}<span class="data_age text-danger">`
— red italic text saying how old the balance is. `Account.is_stale`
(`models/account.py:216`) is true when the newest statement is older than
`STALE_DATA_TIMEDELTA`. An inactive account is by definition one that is no longer being
updated, so essentially every inactive row would render red.

**Decision**: Gate the `text-danger` class on `acct.is_active` as well, so inactive rows show
the age in plain `data_age` styling. The age itself is still shown.

**Rationale**: A warning that fires on every row of a category warns about nothing, and red on
a finance page should mean "look at this". The age is still useful information — it says how
recent the frozen figure is — so it stays; only the alarm is dropped. Spec FR-007.

**Alternatives considered**:
- *Leave the warning on.* Rejected: every inactive account permanently red, for a condition
  that is expected rather than wrong.
- *Hide the age entirely on inactive rows.* Rejected: the age is exactly what tells you how
  stale the balance you are looking at is.

---

## R5: Rows with no balance, statement, or credit limit

**Finding**: The template dereferences `acct.balance.ledger` unguarded, and the credit table
computes `acct.credit_limit + acct.balance.ledger`. `Account.balance`
(`models/account.py:252`) returns `None` when no `AccountBalance` row exists, and
`credit_limit` is nullable. The `dollars` / `reddollars` / `ago` filters handle `None` and
Jinja `Undefined` (`flaskapp/filters.py`), but the **arithmetic** does not: `None + Undefined`
raises and takes the whole page down with a 500.

This is a latent bug today — a credit account saved with the Credit Limit field left blank
already breaks `/accounts`. It is only near-unreachable because `AccountFormHandler.submit()`
calls `set_balance(ledger=0, avail=0)` for every account it creates
(`views/accounts.py:298`). Surfacing inactive accounts widens the exposure: accounts loaded
by `loaddata` or created before that line existed need not have a balance.

**Decision**: Guard the balance-derived cells in the template — render the row with those
cells blank when the underlying value is missing, rather than failing the page.

**Rationale**: Spec FR-006. A missing figure should cost one cell, not the page, on the one
page that is now the only way to reach a mis-configured account. Guarding in the template
keeps `Account.balance` honest about returning `None` rather than inventing a zero balance
that was never recorded — which on a finance application is a meaningfully different claim.

**Alternatives considered**:
- *Have `Account.balance` return a zero `AccountBalance` when none exists.* Rejected: it would
  make "no balance has ever been recorded" indistinguishable from "the balance is $0.00",
  and `balance` is read by the charts, the cash position page and the pay period code.
- *Add a Jinja filter or macro for the guard.* Rejected: three tables, one guard each; a
  `{% if %}` reads more plainly than indirection here.

---

## R6: What else queries accounts (confirming FR-009 needs no code)

**Finding**: Every other consumer of `is_active` filters it itself and is untouched by this
change:

- `flaskapp/views/index.py:91,94,97` — dashboard panels, active only. Left as-is
  (the maintainer confirmed Accounts-page-only scope on 2026-09-17).
- `cashposition.py:233,258,457` — already handles inactive accounts deliberately, showing
  them in coverage groups marked "inactive account" and excluding them from the waterfall.
- `interest.py:93`, `models/account.py:278` (`active_credit_accounts`) — credit payoff,
  active only.
- `views/budgets.py:80` — budget-source picker, active only.
- `AccountTransferFormHandler.validate()` (`views/accounts.py:352,369`) — the transfer form's
  dropdown is built from `accts`, which *already* contains every account including inactive
  ones (`views/accounts.py:73`, `templates/accounts.html:12-15`); an inactive account is
  rejected on submit with "From Account must be active" / "To Account must be active", covered
  by `test_accounts.py` `test_09_non_transferrable_from_account` and siblings.

**Decision**: Change none of these. Spec FR-009 is satisfied by leaving them alone.

**Rationale**: The one behaviour being changed is the Accounts page listing. Spec SC-005
requires no figure anywhere else to move; the cheapest way to guarantee that is to touch
nothing that computes one.

**Note on the spec**: FR-009 was amended on 2026-09-17 after this finding — it originally said
the transaction and transfer pickers "exclude" inactive accounts, which is not what they do.
They list them and reject them on submit. The requirement now says that behaviour is
unchanged, which is both accurate and what the maintainer asked for.

---

## R7: Existing tests that will need updating

**Finding**: The sample data already contains exactly the fixture this feature needs —
`DisabledBank` (id 6, `is_active=False`, a Bank account with one statement, a recorded balance
of $10.00 and two OFX transactions), at `tests/fixtures/sampledata.py:714`. It is the same
account the issue's own workaround example names. It becomes visible on `/accounts` the moment
the filter is dropped, so every test asserting exact Accounts-page table content changes:

| Location | What changes |
|----------|--------------|
| `test_accounts.py:84` `test_bank_table` | adds the `DisabledBank` row and the `Active?` cell to each row |
| `test_accounts.py:105` `test_bank_stale_span` | row indices shift; `DisabledBank` sorts after `BankTwoStale` so indices hold, but the assertion on the stale span is re-checked |
| `test_accounts.py:115` `test_credit_table`, `:143` `test_investment_table` | `Active?` cell added to each row |
| `test_accounts.py:1060, 1167, 1312` (`TestAccountTransfer`) | bank-table content assertions gain the `DisabledBank` row and `Active?` cells |

`test_index.py:91-143` asserts the *dashboard's* panels, which share element IDs with the
Accounts page but come from `index.html` and a different view. Unchanged.

**Decision**: Update those assertions, and add new coverage for the behaviour this feature
introduces (see quickstart.md).

**Rationale**: Principle II — new code covered by valid tests. Updating an assertion to match
a deliberate change is correct; the new behaviour needs its own tests rather than riding on
the updated ones.

---

## R8: Documentation and screenshots

**Finding**:
- `docs/source/app_usage.rst` is the "how the application behaves" document, organised by
  page/feature. It has no section on account activation.
- `docs/source/screenshots.rst` is **generated** by `docs/make_screenshots.py`; captions are
  edited in the `SCREENSHOTS` list there, not in the `.rst`. The `/accounts` entry
  (`make_screenshots.py:262`) has a title and no description.
- The `accounts.png` / `accounts_sm.png` screenshot will visibly change — the sample data's
  `DisabledBank` appears as a greyed row and every table gains a column.

**Decision**: Add an "Inactive Accounts" section to `app_usage.rst` (Principle IV, spec
FR-010); add a description to the `/accounts` screenshot entry in `make_screenshots.py`; and
regenerate and commit the `/accounts` screenshots.

**Rationale**: Principle IV requires documentation in the same change. The screenshots are
regenerated and committed per the repository's established practice for changes that alter a
captured page.

**Operational notes** (from prior work in this repository):
- `tox -e docs` must never run in the same invocation as `tox -e screenshots` — `docs` cleans
  the build directory and deletes the generated PNGs.
- `screenshots.rst` is generated; edit `docs/make_screenshots.py`.
- Commit only the screenshots this change actually alters.

---

## R9: Schema and migrations

**Decision**: No change to `biweeklybudget/models/`, therefore no Alembic migration, and the
`migrations` tox environment is not a gate for this feature.

**Rationale**: `Account.is_active` (`models/account.py:148`) already exists, is already
written by the form handler and already read by the modal. Constitution Principle III applies
only to changes under `models/`; there are none.
