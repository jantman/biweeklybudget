# Research: Balance-less Accounts Must Not Break The Landing Pages

**Feature**: `specs/20260917-075406-balanceless-account-pages`
**Date**: 2026-09-17
**Issue**: [#334](https://github.com/jantman/biweeklybudget/issues/334)

All findings below were produced by running the code, not by reading it. The reproduction
harness is a throwaway script that drops and reloads the test database with
`SampleDataLoader`, runs `init_db()`, and then requests pages through the Flask test client
against a `mariadb:10.4.7` container on port 13306. No acceptance-suite fixtures are
involved, so the results describe the templates, not the test harness.

## R1: Does the index page actually fail today?

**Question**: The issue asserts `/` returns 500 for an active account with no
`AccountBalance`. Verify rather than assume.

**Finding**: Confirmed. Against unmodified sample data:

| Database state | `/` | `/accounts` |
|---|---|---|
| Sample data as loaded | 200 | 200 |
| \+ **inactive** bank, credit and investment accounts, no balance | 200 | 200 |
| \+ **active** bank, credit and investment accounts, no balance | **500** | 200 |

The traceback is:

```
File ".../biweeklybudget/flaskapp/templates/index.html", line 147, in block 'body'
jinja2.exceptions.UndefinedError: 'None' has no attribute 'ledger'
```

**Decision**: The defect is real and is confined to `index.html`. It is reproduced by the
P1 scenario in the spec.

## R2: Which cells in `index.html` fail, and which merely look wrong?

**Question**: The issue lists six line numbers. Are all six fatal?

**Finding**: No — they split into two groups, and the distinction matters for what the fix
must change.

- **Fatal** — the cells that do arithmetic on the missing figure. `acct.balance` is `None`,
  so `acct.balance.ledger` is Jinja's `Undefined`, and `Undefined - something` raises. These
  are `index.html:147` (bank "Difference"), `:186` (credit "Available") and `:187` (credit
  "Avail - Unrec"). Line 147 is the one that fires first and is the line in the traceback.
- **Not fatal, but wrong** — the cells that only print. `{{ acct.balance.ledger|dollars }}`
  at `:139`, `:179` and `:218` survives, because `dollars_filter`
  (`biweeklybudget/flaskapp/filters.py:120`) returns `''` for `None` and for `Undefined`.
  They already render blank, which is the behaviour the spec wants.

A third problem is in the same cells and is not in the issue's list: the balance age,
`({{ acct.ofx_statement.as_of|ago }})`, is printed unconditionally at `:141`, `:181` and
`:220`. An account with no balance has no statement either, so `ago_filter` returns `''`
and the page renders a bare `()` beside the blank balance.

**Decision**: Guard the three arithmetic cells, and wrap the three age spans in a statement
check. The three printing cells need no change of their own but are covered by the same
`{% set %}` the arithmetic cells use.

**Alternative considered**: Guard only the three arithmetic cells named in the issue.
Rejected — it leaves `$ ()` rendering in the balance cell of every newly added account,
which is the exact row the operator is looking at, and the guard for it is one `{% if %}`
already written three times in the sibling template.

## R3: Is `accounts.html` already correct for an **active** balance-less account?

**Question**: The Accounts page was fixed for issue #276, but only inactive accounts were
exercised. An active account takes a different path through the staleness markup, so the
covered case does not prove this one.

**Finding**: It is correct. `/accounts` returned 200 in every row of the R1 table,
including with active bank, credit and investment accounts that have no balance. Reading
the template confirms why: each of the three tables does

```jinja
{% set ledger = acct.balance.ledger if acct.balance else None %}
```

at `accounts.html:60`, `:104` and `:147`, then guards every derived cell with
`{% if ledger is not none %}` (and `and acct.credit_limit is not none` where the credit
limit is also involved), and wraps the age span in `{% if acct.ofx_statement %}`. The
`acct.is_active and acct.is_stale` condition inside the age span's class is evaluated only
when a statement exists, so the active path adds no new dereference.

**Decision**: `accounts.html` is not changed. FR-002 is satisfied by existing code; what is
missing is FR-010's coverage, which is added as a test.

## R4: Where should the null handling live?

**Question**: The issue offers two shapes — guards in the template, or an `Account`
property returning the ledger balance or `Decimal('0.0')`.

**Decision**: Guards in the template, matching `accounts.html` exactly, cell for cell.

**Rationale**:

- The property returning `Decimal('0.0')` was already proposed and rejected for this same
  codebase, with reasons recorded in
  `specs/20260917-053603-show-inactive-accounts/research.md` R5: it makes "no balance has
  ever been recorded" indistinguishable from "the balance is $0.00", and `Account.balance`
  is read by the balance chart, the cash position page and the pay period code, each of
  which needs to know the difference. Adopting it now would either contradict that decision
  or require revisiting all of those call sites.
- Two templates that render the same three tables should read the same way. A reviewer
  looking at one should not have to work out whether the other is doing something
  different for a reason.
- The `{% set ledger = ... %}` form handles a second failure route for free: a balance row
  that exists with a `NULL` ledger yields `ledger = None` just as a missing row does. See
  R5.

**Alternatives considered**:

- *A read-only `Account` property returning the current ledger or `None`.* It would remove
  one expression from three template lines and could be reused by other call sites. Not
  worth a model change and a docs update for that; and `accounts.html` would then be the
  odd one out unless it were changed too, widening a bug fix into a refactor of a template
  that is not broken.
- *Filter balance-less accounts out of the index queries.* Rejected outright: it hides the
  account the operator has just created, from the page they went to in order to see it.

## R5: The second route — a balance row whose ledger is NULL

**Question**: `AccountBalance.ledger` is nullable. Is that a separate way to reach the same
500, and does the chosen fix close it?

**Finding**: It is the same 500. With an active account given a balance row via
`set_balance(ledger=None, avail=None)`, `/` returns 500 and `/accounts` returns 200 —
identical to the missing-row case. `Account.balance` returns the row, and `row.ledger` is
`None`, so the arithmetic fails one step later.

**Decision**: The `{% set ledger = acct.balance.ledger if acct.balance else None %}` form
resolves both routes to the same `ledger is none` test, so one guard closes both. This is
why the fix is written as a `{% set %}` rather than as `{% if acct.balance %}` wrapped
around the cells, which would close only the first route. It also matches how
`AcctBalanaceChartView` (`views/index.py:293`) already treats a null ledger, resolving the
inconsistency the issue notes.

## R6: Scope — what else touches a missing balance?

**Question**: The issue is scoped to `/` and `/accounts`. Is anything else reachably
broken by the same state, and does this change need to cover it?

**Finding**, by requesting every main page in the three database states of R1:

| Page | Sample data | \+ active balance-less accounts |
|---|---|---|
| `/` | 200 | **500** → fixed by this change |
| `/accounts` | 200 | 200 |
| `/cash-position` | 200 | 200 |
| `/budgets` | 200 | 200 |
| `/payperiods` | 200 | 200 |
| `/reconcile` | 200 | 200 |
| `/transactions` | 200 | 200 |
| `/accounts/1` | 200 | 200 |
| `/accounts/credit-payoff` | **500** | **500** |

`/cash-position` is unaffected because `cashposition.py:142` already reads the balance into
`None if balance is None else balance.ledger`.

`/accounts/credit-payoff` returns 500 *before* any balance-less account is added, so
nothing about it can be attributed to this issue. That 500 is deliberate, not a crash: the
view catches `NoInterestChargedError` and returns its own error page with a 500 status
(`views/credit_payoffs.py:157-163`), which is what happens when sample data has no recent
interest charge in this bare harness. Whether an active credit account with no balance
would break `InterestHelper._make_statements` (`interest.py:113` dereferences
`acct.balance.ledger_date`) could not be observed, because the page never gets that far
here.

**Decision**: This change covers `/` only, plus test coverage for `/accounts`. No claim is
made in the pull request about `/accounts/credit-payoff` being broken by #334, because none
was demonstrated. The spec's Out of Scope section is corrected to say that rather than to
assert a defect. This is recorded here per Principle V rather than investigated further,
since it is outside the issue and would need its own decision about what a payoff
projection means for an account with no balance.

## R7: How to test it

**Question**: What form should the acceptance coverage take, and what must it assert?

**Finding**: There is an exact precedent —
`biweeklybudget/tests/acceptance/flaskapp/views/test_accounts.py:2060`,
`TestAccountsMissingData`, added for issue #276. It uses `class_refresh_db`, adds three
balance-less accounts (inactive) in a first incremental test, asserts the page is 200 via
`requests.get`, then asserts each table row's exact cell text via `tbody2textlist`.

**Decision**: Add a sibling class in `test_index.py` that does the same for **active**
accounts and asserts both `/` and `/accounts` are 200, plus the exact row contents on the
index page. Asserting exact row text, not just the status code, is what pins FR-003 (blank,
not `$0.00`) and FR-005 (no bare `()`); a status-only test would pass against a fix that
printed a fabricated zero.

The three index tables have no "Active?" column, so the expected rows are
`['BankNoData', '', '$0.00', '']` for bank, `['CreditNoData', '', '', '']` for credit and
`['InvestmentNoData', '']` for investment. The `$0.00` in the bank row is the unreconciled
sum, which is a genuine zero — that account has no transactions — and not a balance.

**Alternative considered**: Adding the balance-less accounts to `sampledata.py` so every
test sees them. Rejected: it would shift the expected figures in every existing test that
asserts table contents, for no gain over a class-scoped fixture.

## R8: Constitution obligations this change does and does not incur

- **Principle III (migrations)**: not incurred. No file under `biweeklybudget/models/`
  changes — this is the direct consequence of R4's decision.
- **Principle IV (documentation)**: no user-facing behaviour is added or changed for a
  working account, so `README.rst`, `CLAUDE.md` and `docs/source/` have nothing to correct.
  The `docs` environment must still build.
- **Principle II (test gate)**: unit and acceptance suites in full. Migration and Docker
  suites are not triggered by a template change, though the repository's CI runs them
  anyway.
- **Principle VI (changelog)**: one `CHANGES.rst` bullet under `Unreleased`, no version
  bump.
- **Screenshots**: the documented screenshots are taken from sample data, which this change
  does not alter, so no screenshot changes.
