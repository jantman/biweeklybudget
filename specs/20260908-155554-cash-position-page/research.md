# Phase 0 Research: Cash Position Page

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-08

All unknowns from the plan's Technical Context are resolved below. Each entry
records the decision, why it was made, and what was rejected.

---

## R1. Where the shared calculation lives

**Decision**: A new module `biweeklybudget/cashposition.py` holding a
`CashPosition` class that computes the complete statement — every term, both
subtotals, the final figure, the itemizations, and the diagnostics — from a
database session. `NotificationsController` is refactored to consume it.

**Rationale**: FR-005 requires the page and the banner to share one
calculation, and constitution "Financial correctness" wants that arithmetic
pinned by tests. `flaskapp/notifications.py` produces *UI strings*; putting
domain arithmetic there is what made the numbers unreviewable in the first
place, which is the complaint the issue opens with. A module beside
`biweeklypayperiod.py` — the other place financial arithmetic lives — is
testable without a Flask app or a browser.

**Compatibility constraint**: the six `NotificationsController` static methods
(`budget_account_sum`, `credit_account_sum`, `budget_account_unreconciled`,
`standing_budgets_sum`, `pp_sum`, `num_unreconciled_ofx`) are public,
documented in `docs/source/biweeklybudget.flaskapp.notifications.rst`, and
covered by existing tests including the ones just added under #320. They are
**kept**, re-expressed as thin delegations to `CashPosition`. The existing
tests keep testing something real, and no caller outside the package breaks.

**Alternatives rejected**:

- *Extend `NotificationsController` with the extra methods the page needs.*
  Leaves financial arithmetic in a view-content class and makes the page's
  tests need the Flask app. Rejected.
- *Compute the statement in the new view.* Directly violates FR-005: two
  implementations of the same arithmetic, free to drift, which is the exact
  failure mode #320 was.

---

## R2. Schema shape for the budget/account association

**Decision**: A plain association table `budget_accounts` with columns
`budget_id` and `account_id`, both non-null foreign keys with `ON DELETE
CASCADE`, and a composite primary key over the pair. Declared as a
`sqlalchemy.Table` on `Base.metadata` in a new module
`biweeklybudget/models/budget_account_link.py`, exposed through
`Budget.accounts` and `Account.budgets` via `relationship(secondary=...)`.

**Rationale**: The association carries no data of its own — it says only that
a budget's money is held in an account (FR-014). A composite primary key makes
the pairing unique for free, so the same link cannot be recorded twice.
`ON DELETE CASCADE` on both sides satisfies FR-016 (no dangling rows) at the
database level rather than relying on application code to remember.

**Alternatives rejected**:

- *A nullable `Budget.account_id` FK.* This was the original proposal and was
  explicitly rejected by the repository owner: one savings account commonly
  holds several earmarked standing budgets, so the relationship is not 1:1.
  See the spec's Clarifications section.
- *An association-object model class (like `BudgetTransaction`).* Justified
  only when the association carries its own columns. It does not, and a class
  would invite someone to later add an `amount` column, which is precisely the
  allocation rule FR-019 says the application does not hold.

**Alembic visibility**: `models/__init__.py` imports the new module, so the
table is on `Base.metadata` when `env.py` runs and `alembic-verify` compares
head against the models (constitution III).

---

## R3. Computing coverage groups

**Decision**: Connected components of the bipartite budget↔account graph,
computed in memory by iterative breadth-first search over the association
rows. A pure function taking the association pairs and returning a list of
`(account_ids, budget_ids)` groups, unit-testable with no database.

**Rationale**: FR-018/FR-019. With a many-to-many association and no recorded
split of a budget's balance, the only well-defined delta is over a set closed
under the links: take an account, every budget linked to it, every other
account those budgets are linked to, and so on until nothing new is reachable.
The sum of the accounts on one side and the sum of the budgets on the other
are then comparable, and no budget's balance is attributed to any particular
account.

The common cases fall out correctly with no special-casing:

| Configuration | Group | Delta reported |
|---|---|---|
| One account, one budget | that pair | exact per-account delta |
| One account, several budgets | account + all its budgets | exact per-account delta |
| Several accounts, several budgets | the whole closure | group-level delta only |
| Account with no budgets | account alone | reported as unlinked (FR-017) |

**Scale**: This application has tens of accounts and budgets, not thousands.
Iterative BFS over a dict-of-sets is the right amount of machinery; recursion
is avoided only so a pathological configuration cannot hit the recursion
limit.

**Alternatives rejected**:

- *Per-account deltas by splitting each budget evenly across its accounts.* An
  invented allocation rule the application does not record. FR-019 forbids it.
- *Report only the aggregate difference across all links.* Loses the
  per-savings-account answer that motivates the diagnostic.

---

## R4. Editing the association in the budget modal

**Decision**: One checkbox per active budget-funding account in the existing
budget modal, named `acct_<id>`, shown only when the budget's type is
Standing. `BudgetFormHandler.submit()` collects the `acct_<id>` keys and
replaces the budget's account set.

**Rationale**: `serializeForm()` in `static/js/forms.js` already serializes
checkboxes to booleans keyed by input name, and `FormBuilder.addCheckbox()`
already renders them — so this needs no change to either shared file, and no
new form-serialization path to test. `FormBuilder` has no multi-select
control, and `serializeForm()` reads `select` elements with
`.find(':selected').val()`, which returns only the *first* selection; a
`<select multiple>` would therefore silently drop every account but one. That
is a real trap, not a style preference.

The checkboxes are hidden for periodic budgets by the existing
`budgetModalDivHandleType()` show/hide mechanism, satisfying FR-015.

**Data flow**: `budgets.html` gains a `budget_source_accounts` JS global
(id → name for active budget-funding accounts), alongside the
`acct_names_to_id` global it already defines. `GET /ajax/budget/<id>` gains an
`account_ids` key via `Budget._dict_properties`, so the modal can check the
right boxes. `budgets_modal.js` is only ever loaded by `budgets.html`, so the
global is guaranteed present wherever the modal exists.

**Alternatives rejected**:

- *A `<select multiple>`.* Broken by `serializeForm()` as described above.
- *A separate management page for links.* More surface area for a
  configuration setting that belongs next to the budget it configures.

---

## R5. URL, navigation, and page identity

**Decision**: URL `/cash-position`; view class `CashPositionView` in a new
`biweeklybudget/flaskapp/views/cashposition.py`; template
`cash-position.html`; nav entry "Cash Position" with the `fa-balance-scale`
icon, placed immediately after "Home".

**Rationale**: The page answers "what do I have right now", which is the same
altitude as the index page, so it belongs at the top of the nav rather than
buried among the per-record views. Font Awesome 4's `fa-balance-scale` is
available in the bundled icon set and reads as "reconciling two sides", which
is what the page is.

**Consequence**: `tests/acceptance/flaskapp/views/test_base_template.py`
asserts the exact nav link list; that assertion must be updated in the same
change or the acceptance suite fails.

---

## R6. Ledger vs. projected balances

**Decision**: Each budget-funding account row shows its raw ledger balance,
its unreconciled adjustment, and the projected balance (ledger minus
unreconciled). The waterfall's second term is the negated total of
`Account.unreconciled_sum` across those accounts.

**Rationale**: FR-008 and the issue's fourth bullet. The sign works out
exactly: the banner computes `available - (standing + pp + unreconciled)`, so
the unreconciled term is subtracted from the funds side, and ledger minus
unreconciled *is* the projected balance. The page therefore reorganizes the
banner's arithmetic without changing it (FR-004).

`Account.unreconciled_sum` already excludes transactions marked
`no_budget_impact` and payments toward credit accounts (issues #210, #319), so
using it directly keeps the page consistent with the banner by construction
rather than by a second filter that could drift.

---

## R7. Missing and unknown balances

**Decision**: An account whose `balance` is `None`, or whose `balance.ledger`
is `None`, contributes `Decimal('0')` to every total and is rendered with the
text "no balance recorded" in place of an amount.

**Rationale**: FR-023. `NotificationsController.budget_account_sum` and
`credit_account_sum` already skip these accounts, so the totals are unchanged;
what is new is that the page says *why* an account contributed nothing. This
also avoids reproducing the known `index.html` crash noted in the 1.11.1
changelog, where `acct.balance.ledger` is dereferenced with no `None` guard.

---

## R8. Testing strategy

**Decision**:

| Layer | Location | Covers |
|---|---|---|
| Unit — arithmetic | `tests/unit/test_cashposition.py` | every term, both subtotals, the final figure, coverage grouping, sign handling, empty/None cases |
| Unit — notification parity | extend `tests/unit/flaskapp/test_notifications.py` | the delegating `NotificationsController` methods still return what they did |
| Migration | `tests/migrations/test_migration_<rev>.py` | `budget_accounts` absent before, present after, both directions |
| Acceptance — page | `tests/acceptance/flaskapp/views/test_cash_position.py` | rendered rows, totals, links, diagnostics, against `sampledata` |
| Acceptance — nav/banner | `tests/acceptance/flaskapp/views/test_base_template.py` | new nav entry, new banner link |
| Acceptance — modal | `tests/acceptance/flaskapp/views/test_budgets.py` | link checkboxes appear for standing budgets, save round-trips |

The unit tests pin *signed* values, including a credit account in credit and a
standing budget with a negative balance. The 1.11.1 changelog records that an
`abs()`-based implementation passed a test that only checked a figure got
smaller; the same trap applies to every term here.

**Sample data**: `tests/fixtures/sampledata.py` gains budget/account links so
the acceptance tests have a non-empty coverage group and at least one unlinked
budget-funding account to assert on.

---

## R9. Documentation

**Decision**:

- `docs/source/app_usage.rst` gains a "Cash Position" section, cross-linked
  from the existing "The Unallocated Funds Notification" section (added under
  #320), explaining the waterfall, coverage groups, and why deltas are
  reported per group rather than per account.
- New API stubs `docs/source/biweeklybudget.cashposition.rst`,
  `biweeklybudget.flaskapp.views.cashposition.rst`, and
  `biweeklybudget.models.budget_account_link.rst`, referenced from
  `biweeklybudget.rst`, `...views.rst`, and `...models.rst`.
- `docs/source/screenshots.rst` and `docs/make_screenshots.py` gain the new
  page.
- `CLAUDE.md` is not affected: no new command, environment variable, or
  workflow.

**Rationale**: Constitution IV. `tox -e docs` must build clean; a new module
with no `.rst` stub produces a coverage warning.

---

## R10. Version and changelog

**Decision**: `1.11.1` → `1.12.0`, with a `CHANGES.rst` entry in the
established format.

**Rationale**: Constitution VI and SemVer. New user-facing page, new schema,
new relationship on two models — additive, backward compatible, so MINOR.

---

## R11. Milestone authorization

**Decision**: Implementation runs through all milestones without pausing for
per-milestone approval, and the resulting branch is pushed and opened as a PR.

**Rationale**: Constitution I requires human approval to advance between
milestones. The instruction that dispatched this session explicitly directs
implementation to run to completion, commit, push, open a pull request,
monitor CI, and answer reviews. That is the human approval, given up front for
the whole run, and it is recorded here rather than assumed. Every other
milestone-close obligation — full suites green, docs updated, spec artifacts
updated, committed together (constitution workflow step 5) — still applies at
each milestone boundary.
