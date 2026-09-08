# Implementation Plan: Correct the Unallocated-Funds Notification

**Branch**: `robot-army/issue-320-unallocated-funds-notification-reports` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260907-175428-unallocated-funds-notification/spec.md`

## Summary

The site-wide banner that compares available funds against committed funds omits
credit-account liabilities from the available side, and labels its pay-period
figure with a word that means a different quantity in the view it links to.

The fix is confined to `NotificationsController`. A new
`credit_account_sum()` static returns the combined recorded balance of active
credit accounts — stored negative when owed — and `get_notifications()` adds it
to the funding-account balance to produce the funds-available figure it compares
and reports. The sentence is rewritten so the credit deduction is a visible,
linked term and the pay-period figure is named "current pay period allocated but
unspent" instead of "remaining".

The issue's second defect (pseudo-transactions inflating the unreconciled figure)
was verified as already fixed on `master` by the #210/#319 work; it is covered
here by tests that pin the behaviour through the banner, not by new logic. See
[research.md](./research.md) R4.

No model, schema or migration change is involved.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask, SQLAlchemy, Jinja2 (server-rendered); no new dependency

**Storage**: MySQL/MariaDB — read-only for this feature; no schema change

**Testing**: pytest; unit (`biweeklybudget/tests/unit/`) and Selenium acceptance
(`biweeklybudget/tests/acceptance/`), run via `tox -e py314` and `tox -e acceptance`

**Target Platform**: Linux, self-hosted single-user web application on localhost

**Project Type**: Server-rendered Flask web application (single project, no separate frontend build)

**Performance Goals**: The notification is computed once per page render for every
page. The added work is one indexed query over the accounts table plus a
per-account latest-balance lookup — the same shape and order of magnitude as the
two account queries the controller already performs. No measurable change.

**Constraints**: All monetary arithmetic in `Decimal`, never float. Output must
pass pycodestyle and pyflakes under the exceptions in `pytest.ini`.

**Scale/Scope**: One module changed (~40 lines), one docs section added, two test
modules updated. Account counts are in the tens.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v1.0.0. Re-checked after Phase 1 design — result unchanged, recorded at the end of this section.*

| Principle | Status | How this plan satisfies it |
|---|---|---|
| **I. Spec-Driven Change** (NON-NEGOTIABLE) | PASS | Spec written and committed before planning; this plan precedes implementation; work is on feature branch `robot-army/issue-320-unallocated-funds-notification-reports`. Decomposed into milestones with human approval at each boundary (see Milestones below). One feature at a time. |
| **II. The Test Gate** (NON-NEGOTIABLE) | PASS | Full unit **and** acceptance suites must be run to completion and pass before the feature is declared done — not a filtered subset. New tests pin exact expected figures at three levels ([research.md](./research.md) R8). pycodestyle/pyflakes clean. If a suite times out, the timeout is raised and it is re-run; a timed-out run is not a pass. |
| **III. Schema Changes Ship With Reversible Migrations** | PASS (vacuous, stated explicitly) | **No change is made to `biweeklybudget/models/`.** Every input already exists as a model attribute or existing query; the new figure is derived at request time. Therefore **no Alembic migration is required or created**. The `migrations` tox environment must still pass unchanged, which is the check that no schema drift crept in. |
| **IV. Documentation Is Part Of The Change** | PASS | `docs/source/app_usage.rst` gains a section describing what the banner compares and what each figure means, in the same change. `tox -e docs` must build clean. The module's own docstrings are updated (Sphinx autodoc renders `biweeklybudget.flaskapp.notifications`). |
| **V. Escalate Instead Of Guessing** | PASS | Two decisions that could have been guessed were instead resolved against the code and recorded: the credit balance sign convention (R1, three independent confirmations) and whether defect #2 is still live (R4, verified fixed). Any further ambiguity — in particular if an acceptance fixture no longer demonstrates the case its class name claims — is raised rather than papered over. |
| **VI. Versioned, Changelogged Releases** | PASS | `biweeklybudget/version.py` bumped and a matching `CHANGES.rst` entry added at feature completion. This is a user-visible bug fix in reported figures with no API or schema change, so a **PATCH** bump is the correct SemVer scope. No new Python files, so no new copyright headers needed. |

**Technology & Security Constraints**: no new dependency (AGPLv3 compatibility not
at issue); no change to the localhost-only security posture; no credentials
involved; MySQL-specific behaviour untouched. **Financial correctness**: this is a
change to budget arithmetic, so per the constitution it ships with tests pinning
the expected numbers — that requirement is what drives Milestone 1 and the
`test_*_confirm_pp` additions in Milestone 2.

**Test data safety**: acceptance tests drop and reload the database and must only
ever be pointed at the throwaway test database, never a real one.

**Post-Phase-1 re-check**: The design adds one method to one existing class and
one docs section. It introduces no new project, no new abstraction layer, no new
dependency and no new data. There are no constitution violations to justify, so
the Complexity Tracking table is omitted.

## Project Structure

### Documentation (this feature)

```text
specs/20260907-175428-unallocated-funds-notification/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output — R1..R8
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── notification-content.md   # The banner's user-facing contract
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created here)
```

### Source Code (repository root)

```text
biweeklybudget/
├── flaskapp/
│   └── notifications.py                  # CHANGED: + credit_account_sum(),
│                                         #   get_notifications() rewritten
├── models/
│   └── account.py                        # UNCHANGED — active_credit_accounts()
│                                         #   and unreconciled_sum() reused as-is
├── tests/
│   ├── unit/flaskapp/
│   │   └── test_notifications.py         # CHANGED: new static in every
│   │                                     #   patch.multiple; new sentence
│   │                                     #   assertions; new credit_account_sum
│   │                                     #   tests incl. sign and None cases
│   └── acceptance/flaskapp/views/
│       └── test_base_template.py         # CHANGED: recomputed figures in the
│                                         #   three notification classes;
│                                         #   new no-cash-impact regression class
└── version.py                            # CHANGED: PATCH bump

docs/source/app_usage.rst                  # CHANGED: new banner section
CHANGES.rst                                # CHANGED: entry for this fix
```

**Structure Decision**: Single-project layout, unchanged. The application is a
server-rendered Flask app with no separate frontend build, so the whole change
lands in `biweeklybudget/` plus docs. No new module or package is created: the new
figure belongs on `NotificationsController` beside the other four figures it is
compared against, and putting it anywhere else would separate a term from the sum
it is part of.

## Design

### The computation

```
funds_available = budget_account_sum() + credit_account_sum()
funds_committed = standing_budgets_sum() + pp_sum() + budget_account_unreconciled()
```

`credit_account_sum()` returns a `Decimal` that is **negative when money is owed**,
because that is how the balances are stored (verified three ways — [research.md](./research.md) R1).
Adding it therefore performs the subtraction FR-001 requires, and handles the
overpaid-card edge case correctly without a sign branch.

Accounts are drawn from `Account.active_credit_accounts(db_session)`, the existing
static that the credit-payment feature uses (R2). Accounts with no recorded
balance, or a `NULL` ledger, contribute zero (R3).

Verdict, per FR-005 and unchanged in shape:

| Condition | Result |
|---|---|
| `funds_available < funds_committed` | `alert alert-danger`, "is less than" |
| `funds_available > funds_committed` | `alert alert-info`, "is more than" |
| equal | no notification |

The stale-account and unreconciled-OFX notifications are untouched.

### The sentence

The exact user-facing wording, link targets and link texts are specified in
[contracts/notification-content.md](./contracts/notification-content.md), which is
the artifact the tests assert against.

### What is deliberately *not* done

- No note-text matching on `pseudo-trans`. The explicit `no_budget_impact` flag
  replaced that workaround; adding the string match back would create two
  disagreeing definitions of "no cash impact" (R4).
- No change to `budget_account_sum()`, `standing_budgets_sum()`, `pp_sum()` or
  `budget_account_unreconciled()`. The committed-side quantities are correct
  (FR-004).
- No change to the pay period view's own "remaining" figure — correct for that
  view, and out of scope.

## Milestones

Human approval is required to advance between milestones (Constitution I). Each
milestone closes with the relevant suites run to completion and passing, docs
updated, spec artifacts updated, and the whole committed together (Constitution
Workflow step 5).

**M1 — The credit-account figure. [COMPLETE]** Add `credit_account_sum()` with its
docstring. Add unit tests covering: money owed reduces the figure with the correct
sign; multiple accounts sum; inactive credit accounts excluded; non-credit
accounts excluded; an account with no balance row contributes zero; an account
with a `NULL` ledger contributes zero; a positive (overpaid) balance increases the
figure. Delivers FR-001, FR-002, FR-003 and the R1 sign guarantee independently
of any wording change.

**M2 — The corrected notification. [COMPLETE]** Rewrite `get_notifications()` to compare
funds available against funds committed and to emit the sentence from the
contract. Update the unit tests (including adding the new static to every
`patch.multiple`) and the three acceptance notification classes, recomputing each
expected figure from the actual fixture data and confirming each class still
demonstrates the case its name claims. Delivers FR-004 through FR-008 and FR-011.

**M3 — No-cash-impact regression coverage. [COMPLETE]** Add the acceptance coverage that
ties `is_excluded_from_budget` to the banner: a no-budget-impact transaction and a
credit-card payment, both unreconciled in a funding account, must leave the
banner's unreconciled figure and its verdict unmoved, while both remain listed and
reconcilable in the reconcile view. Delivers FR-009 and FR-010 (User Story 3).

**M4 — Documentation, version, changelog and close-out. [COMPLETE]** Add the
`app_usage.rst` section describing the comparison and each figure (FR-012). Bump
`version.py` (PATCH) and add the `CHANGES.rst` entry. Run the full unit and
acceptance suites to completion, plus `tox -e docs` and `tox -e migrations`.
Then push and open the pull request.

## Final suite results

Run to completion on the final tree, per Constitution principle II. No suite was
narrowed and none timed out.

| Suite | Result |
|---|---|
| `tox -e py314` | 624 passed, 139 skipped |
| `tox -e acceptance` | 752 passed, 24 skipped, 0 failed (16m18s) |
| `tox -e docs` | OK, zero errors |
| `tox -e migrations` | 7 passed |

Note on `TestPayPeriodsIndex::test_6_notification_panels`, corrected below:
it **passed** in the full run, and it is neither flaky nor date-dependent. The
two earlier failures were an artifact of how it was invoked; see the Outcome
notes.

## Outcome notes

Recorded during implementation, as Constitution principle V requires for
anything the plan did not anticipate:

- **The verdicts did not flip.** The plan flagged as a risk that subtracting the
  sample data's $6,450.71 of credit balances might flip the over/under verdict
  the three acceptance classes were written to demonstrate. Measured against the
  fixtures, all three keep their verdict (two shortfall, one surplus), so no
  fixture needed adjusting and no assertion was relabelled.
- **FR-002 moved from the unit layer to the acceptance layer.** The task list
  put the inactive-account and non-credit-account exclusions in the unit tests.
  Since `credit_account_sum()` delegates that filtering to
  `Account.active_credit_accounts()`, asserting it there would have meant mocking
  that helper and then asserting it filtered — a test of the mock. The coverage
  moved to a new acceptance class against the real database (T014a).
- **A pre-existing defect was found and deliberately not fixed; now filed as
  issue #334.** Both `templates/index.html` and `templates/accounts.html`
  dereference `acct.balance.ledger` with no `None` guard, so an *active* account
  that has never had an `AccountBalance` row makes **both** `/` and `/accounts`
  return HTTP 500 — verified by request, and true for any active account type,
  not only credit. Confirmed present on `master` and untouched by this change.
  Out of scope here; the affected test uses `/budgets` instead and says why.
- **A supposed pre-existing acceptance failure turned out to be a testing
  error, not a defect.** `TestPayPeriodsIndex::test_6_notification_panels`
  failed in two runs that were narrowed with `-k`, and was initially recorded
  here as date-dependent flakiness. It is neither. `TestPayPeriodsIndex` is an
  `@pytest.mark.incremental` class whose `test_0_clean_db` restores an *empty*
  schema and whose `test_1`..`test_3` then build the exact fixture the
  assertions expect. Only `test_6_notification_panels` matches `-k
  "Notification"`, so those runs executed it without its setup chain, against
  unrelated leftover data. Running the whole class passes (7 passed), as does
  the full suite and CI.

  Nor is it date-dependent: `tox.ini` sets
  `BIWEEKLYBUDGET_TEST_TIMESTAMP=1501223084` in `setenv`, and
  `biweeklybudget/utils.py:247` makes `dtnow()` return that fixed instant, so
  "now" is frozen for every tox run.

  **Lesson for this repo**: never narrow an acceptance run with `-k` across an
  incremental class. Filter by class name (`-k "TestPayPeriodsIndex"`) or by
  file, never by a pattern that matches only some of its methods.
- **`tox -e docs` emitted seven RST heading-level errors**, three of them
  pre-existing. `docs/source/app_usage.rst` establishes `+` as its level-3
  underline; four new subsections and three older ones used backticks, which
  RST reads as level 4 under a level-2 section. All seven were converted, so the
  docs build is now error-free rather than merely exit-zero.

## Risks

- **Acceptance fixture verdicts flip.** Subtracting `$6,450.71` of sample credit
  balances moves funds available from `$12,889.24` to `$6,438.53`, which may flip
  the over/under verdict a test class was written to demonstrate (R5). Mitigation:
  recompute every expected value from the fixtures, and if a class no longer
  demonstrates its named case, adjust that class's own fixture setup so it still
  does — never relabel the assertion to match whatever the code now produces.
- **Silent sign error.** An `abs()`-based implementation would pass any test that
  only checks the figure got smaller. Mitigation: the M1 tests pin signed values
  and include the positive-balance case, which an `abs()` implementation fails.
- **Tests that pass by mocking away the bug.** Every `TestNotifications` test
  patches the controller's statics, so a new static missing from a
  `patch.multiple` would silently hit the real database. Mitigation: M2 updates
  all six, and the acceptance layer exercises the unmocked path.
