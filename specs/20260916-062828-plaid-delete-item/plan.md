# Implementation Plan: Delete a Plaid Item

**Branch**: `robot-army/issue-269-plaid-add-ability-to-delete-an-item` | **Date**: 2026-09-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/20260916-062828-plaid-delete-item/spec.md`

## Summary

Add a `Delete` action to each row of the Plaid Items table on the Plaid Update page, which —
after an in-page confirmation naming the Item and the Accounts it will unlink — removes the
Item at Plaid and then removes it, its Plaid Accounts and its Account links from the database.

The whole feature is one new endpoint, one new template column, two new JavaScript functions
and their tests. **No schema change and no Alembic revision**: deleting an Item is expressible
with the tables and relationships that already exist (see [data-model.md](./data-model.md)).

The one design decision that matters is ordering. The manual procedure the issue documents
deletes the database rows *first* and then calls Plaid with an access token it has just
destroyed; this plan inverts that. Plaid is asked first, while the token is still stored, and
only a success (or a Plaid response saying the Item is already gone) proceeds to a single
local transaction. That is what turns a six-step procedure with an irrecoverable failure mode
into an action that either completes or changes nothing.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Flask (`MethodView`), SQLAlchemy, `plaid-python` 38.0.0
(`ItemRemoveRequest`, `PlaidApi.item_remove`, `ApiException`); Jinja2 templates with
jQuery and Bootstrap 3 on the frontend

**Storage**: MySQL/MariaDB — existing tables only. Rows deleted from `plaid_items` and
`plaid_accounts`; two nullable columns cleared on `accounts`. No DDL.

**Testing**: pytest — unit (`tox -e py314`), Selenium acceptance (`tox -e acceptance`), Plaid
sandbox (`tox -e plaid`), Docker (`tox -e docker`), docs (`tox -e docs`);
`pycodestyle`/`pyflakes` clean per `pytest.ini`

**Target Platform**: Linux, self-hosted, localhost-only single-operator web application

**Project Type**: Server-rendered Flask web application with a single Python package

**Performance Goals**: Not a factor. One Plaid call and a handful of row operations against a
table holding one row per linked institution (single digits in practice).

**Constraints**: The deletion order is forced by foreign keys that carry no `ON DELETE` action
and by a child primary key that cannot be nulled ([research.md](./research.md) R3). The Plaid
call must precede any local mutation, because step 4 of the deletion destroys the only copy of
the access token (R4). The acceptance suite cannot reach Plaid, so the endpoint's branches are
covered by unit tests and the UI's confirmation path by acceptance tests (R7).

**Scale/Scope**: 4 source files and 3 test files touched, 1 new endpoint, 2 new JS functions,
1 new doc subsection, 1 rewritten doc subsection, 1 screenshot regenerated. No new module, no
new dependency, no migration.

## Constitution Check

*Checked against `.specify/memory/constitution.md` v2.1.2. Gate evaluated before Phase 0 and
re-evaluated after Phase 1 design — see the re-check at the end of this section.*

### I. Spec-Driven Change (NON-NEGOTIABLE)

**PASS.** Written spec under `specs/20260916-062828-plaid-delete-item/`, committed before this
plan, which is itself written before any implementation. Work is on the feature branch
`robot-army/issue-269-plaid-add-ability-to-delete-an-item`; no other feature is in flight in
this worktree. The work is decomposed into the four milestones below, with milestone
boundaries as the review points and a full suite run at M4.

### II. The Test Gate (NON-NEGOTIABLE)

**PASS by construction; enforced at M4.** The complete unit and acceptance suites must run to
completion with everything passing before the feature is declared done, and `docs` must build.
`docker` is in the gate because the change alters packaged templates and static JavaScript.
`migrations` is **not** claimed as required-by-schema — there is no model change — but it costs
little and is run anyway to prove that claim rather than assert it.

No suite may be narrowed to a passing subset and a timeout is not a pass: a timed-out suite
gets a raised pytest timeout *and* a raised tool timeout, and is re-run until it completes.

Known-flaky tests in this repository (reconcile drag/unignore — most often
`test_36_ignore_and_unignore_ofx`, fuel-log search, Plaid `test_6_uncheck_all`, and the docs
linkcheck's transient link timeouts) are re-run in isolation before any failure is attributed
to this change. They are not waived.

New code is covered by real tests, not tests written to pass:

- Every branch of the endpoint (C1) and of the failure classifier (C2) gets a direct unit
  test, including the "nothing was written" assertion on the abort path — the exact ordered
  `db_session.mock_calls` list is what pins the mutation order the safety argument depends on.
- The rendered Delete link gets a template-render unit test in the style of
  `TestPlaidResultTemplate`, and an acceptance assertion in `test_4_table`.
- The confirmation modal's content and its Cancel path get acceptance tests; Cancel makes no
  request, so it is testable without Plaid.
- `TestSetUrlRules::test_rules` asserts routes as an exact ordered list and **must** be
  updated; that is a required edit, not an optional one.
- The real `item_remove` round trip is exercised in `tox -e plaid` against Plaid's sandbox.
  That class is `xfail`ed in CI for unrelated reasons (headless Chrome and Plaid's Link
  iframe), which is stated plainly rather than presented as coverage it is not.

### III. Schema Changes Ship With Reversible Migrations

**NOT ENGAGED — and verified, not assumed.** Nothing under `biweeklybudget/models/` changes:
no column, no type, no relationship, no `__table_args__`. The feature deletes rows through
relationships that already exist, so no Alembic revision is created.

The tempting change that would engage this principle — adding `cascade='all, delete-orphan'`
to `PlaidItem.all_accounts`, or `ON DELETE CASCADE` to the foreign keys — is deliberately
rejected in [research.md](./research.md) R3: it would alter the behaviour of every other path
that deletes a `PlaidAccount` (including `PlaidRefreshAccounts`), and an implicit cascade
reaching from `plaid_items` into `accounts` is exactly the action-at-a-distance a financial
database should not have. Explicit, ordered deletion in the one view that wants it is both
safer and schema-free.

`tox -e migrations` is run at M4 to demonstrate that head still matches the models.

### IV. Documentation Is Part Of The Change

**PASS.** In the same change:

- `docs/source/plaid.rst` gains a "Deleting a Plaid Item" subsection under Usage.
- The same file's "Changing Plaid Environments" steps 1-2 — currently raw
  `UPDATE accounts SET plaid_item_id=NULL...` and `DELETE FROM plaid_accounts; DELETE FROM
  plaid_items;` — are rewritten to use the new UI action, including the ordering caveat that
  Items must be deleted *before* `PLAID_ENV`/`PLAID_SECRET` change. Leaving that SQL in place
  while shipping a UI action for it would be documentation corrected never.
- `docs/make_screenshots.py`'s Plaid Update caption is extended, and the `plaid-update`
  PNGs are regenerated, because the table gains a column. `docs/source/screenshots.rst` is
  generated from that script, so the caption is edited there and the `.rst` regenerated.
- `docs/source/jsdoc.plaid_prod.rst` is regenerated for the two new JSDoc'd functions.
- The `automodule` API stubs pick the new view class up with no manual edit.
- No prose in `README.rst` or `CLAUDE.md` enumerates the Plaid Items table's actions
  ([research.md](./research.md) R8), so nothing else needs rewriting.

`tox -e docs` must build clean.

### V. Escalate Instead Of Guessing

**PASS.** Every open question was resolved against the repository or the installed
dependencies and recorded in [research.md](./research.md) R1-R9 — the Plaid client's actual
API surface, the exact shape of `ApiException`, the foreign-key constraints that force the
deletion order, the flush hooks that do *not* fire, and every other module that references
Plaid models. Three judgement calls are recorded explicitly rather than made silently:

- Which Plaid error codes count as "already gone" (`ITEM_NOT_FOUND`, `INVALID_ACCESS_TOKEN`)
  and, just as importantly, which does not (`INVALID_API_KEYS`) — R2.
- Accepting the one irreducible window, Plaid-succeeded-then-commit-failed, on the grounds
  that a retry self-heals through R2 — R4.
- Not covering the delete round trip in the acceptance suite, because doing so would make it
  depend on outbound network and on Plaid's availability — R7.

Any deviation encountered during implementation is written into this feature's spec as a side
quest and committed *before* the deviation begins.

### VI. Changelog Every Change; Release Only On Request

**PASS.** One concise `CHANGES.rst` bullet under `Unreleased`, led by the issue #269 link,
naming the user-visible change and the fact that it also removes the Item at Plaid.
`biweeklybudget/version.py` is **not** touched, no tag is created, and no release is cut —
none was requested.

### Technology & Security Constraints

**PASS.**

- Python 3.14 and MariaDB throughout; **no new dependency**, so no AGPLv3 licence question
  arises. `plaid-python` is already a requirement and `ItemRemoveRequest` ships in it.
- The UI change follows the existing Bootstrap 3 modal and Jinja table patterns and reuses the
  `#modalDiv` the page already includes — no parallel frontend stack, no new library.
- **Secrets**: the Item's `access_token` is read from the database, passed to Plaid, and never
  placed in a response body, a log line added by this feature, a template, or an error message
  (contract G1). This is a stated guarantee with a test, because the feature's whole reason for
  existing is that the current workaround makes the maintainer handle that token by hand.
- **Security posture**: unchanged. The endpoint is a localhost-only POST like every other in
  the application; no authentication model is introduced or weakened, and nothing here presumes
  safe public exposure. It is a destructive endpoint, which is why the confirmation is a
  functional requirement rather than a nicety.
- **Financial correctness**: untouched. No pay-period arithmetic, budget allocation, interest
  or payoff calculation is involved. The adjacent hazard — destroying financial history — is
  closed structurally: Accounts are only ever *unlinked*, and `db_event_handlers`' flush hooks
  ignore Plaid models, so no budget balance moves ([data-model.md](./data-model.md) invariants
  4 and 6, asserted in tests).
- **Test data safety**: acceptance and Plaid suites continue to run only against the disposable
  test database. The Plaid sandbox test deletes only the sandbox Item it created in the same
  incremental run.

### Post-Design Re-check

Re-evaluated after Phase 1. The design adds one endpoint, one private helper, one table
column, two JavaScript functions and one doc subsection. It introduces no new module, no new
abstraction layer, no new dependency, no migration and no change to any existing endpoint's
behaviour. **No violations; the Complexity Tracking table below is empty and stays that way.**

## Project Structure

### Documentation (this feature)

```text
specs/20260916-062828-plaid-delete-item/
├── spec.md                          # Feature specification
├── plan.md                          # This file
├── research.md                      # Phase 0: R1-R9
├── data-model.md                    # Phase 1: entities, mutation order, invariants
├── quickstart.md                    # Phase 1: how to validate it
├── contracts/
│   └── plaid-delete-item.md         # Phase 1: C1 endpoint, C2 classifier, C3 UI
├── checklists/
│   └── requirements.md              # Spec quality checklist
└── tasks.md                         # Phase 2 (/speckit-tasks — not created here)
```

### Source code (repository root)

```text
biweeklybudget/
├── flaskapp/
│   ├── views/plaid.py               # + PlaidDeleteItem, + failure classifier,
│   │                                #   + ItemRemoveRequest import, + url rule
│   ├── templates/plaid_form.html    # + "Delete" column
│   └── static/js/plaid_prod.js      # + plaidDeleteConfirm(), + plaidDelete()
└── tests/
    ├── unit/flaskapp/views/test_plaid.py        # TestSetUrlRules (required edit),
    │                                            #   + TestPlaidDeleteItem,
    │                                            #   + plaid_form.html render test
    ├── acceptance/flaskapp/views/test_plaid.py  # test_4_table + modal/cancel tests
    └── acceptance/test_plaidlink.py             # + sandbox delete steps

docs/
├── make_screenshots.py              # extended Plaid Update caption (source of
│                                    #   the generated screenshots.rst)
└── source/
    ├── plaid.rst                    # + "Deleting a Plaid Item"; change-env rewritten
    ├── screenshots.rst              # regenerated
    ├── jsdoc.plaid_prod.rst         # regenerated
    ├── plaid-update.png             # regenerated
    └── plaid-update_sm.png          # regenerated

CHANGES.rst                          # + Unreleased entry
```

**Structure Decision**: The existing single-package layout is used unchanged. Every file above
already exists; the feature adds no file, no directory and no module.

## Implementation Approach

### M1 — The endpoint

The server side, complete and fully unit-tested, with no UI yet. Independently verifiable by
POSTing the endpoint directly.

1. Add `ItemRemoveRequest` to the `plaid.models` import in `views/plaid.py`.
2. Add the module-private failure classifier per
   [contracts/plaid-delete-item.md](./contracts/plaid-delete-item.md) C2, with a unit test for
   every input shape listed there including the ones that must not raise.
3. Add `PlaidDeleteItem(MethodView)` per C1, modelled on `PlaidRefreshAccounts`, performing the
   mutation order from [data-model.md](./data-model.md) with one commit.
4. Register the route in `set_url_rules` and update `TestSetUrlRules::test_rules`.
5. Add `TestPlaidDeleteItem` covering: success with linked Accounts; success with none;
   success via each recoverable Plaid error code; abort on a non-recoverable `ApiException`
   asserting `db_session.mock_calls == []`; missing `item_id`; unknown `item_id`; and that no
   access token appears in any response.

### M2 — The UI

6. Add the `Delete` column to `plaid_form.html` per C3.1, passing the item id, institution name
   and the existing `accounts[i.item_id]` string through `|tojson`.
7. Add `plaidDeleteConfirm()` and `plaidDelete()` to `plaid_prod.js` per C3.3, JSDoc'd in the
   file's existing style, reusing the shared modal.
8. Add the template-render unit test for the Delete link.
9. Update `test_4_table` for the eighth cell, and add acceptance tests for opening the modal,
   its content, and Cancel leaving the page unchanged.

### M3 — End-to-end and documentation

10. Append delete steps to the `tox -e plaid` incremental sandbox class: delete the linked
    Item through the UI, then assert the Plaid tables are empty and the previously linked
    Accounts survive unlinked with their transactions intact.
11. Add the "Deleting a Plaid Item" subsection to `docs/source/plaid.rst` and rewrite
    "Changing Plaid Environments" steps 1-2.
12. Extend the Plaid Update caption in `docs/make_screenshots.py`; regenerate the screenshots
    and `jsdoc.plaid_prod.rst`. Commit the PNGs before running `docs`.

### M4 — Gate and deliver

13. Run the full gate: `py314`, `acceptance`, `migrations`, `docs`, `docker`. Re-run any
    known-flaky failure in isolation before attributing it to this change. Report honestly
    what could not be run locally (`plaid`, which needs credentials not present here).
14. Add the `CHANGES.rst` entry under `Unreleased`; do not touch `version.py`.
15. Record progress in the spec artifacts, commit, push, open the PR, watch CI.

## Risks

| Risk | Handling |
|------|----------|
| Deleting rows in the wrong order raises a foreign key error mid-way, leaving half-deleted state | Order is fixed in [data-model.md](./data-model.md), pinned by the exact ordered `db_session.mock_calls` assertion, and all inside one commit |
| A local failure after Plaid has already removed the Item leaves an undeletable row | The retry gets `ITEM_NOT_FOUND`, which C2 classifies as recoverable, so the retry completes ([research.md](./research.md) R4) |
| Treating too many Plaid errors as "already gone" silently sheds Items on a transient outage | Only `ITEM_NOT_FOUND` and `INVALID_ACCESS_TOKEN`; `INVALID_API_KEYS` and everything else abort (R2), each a unit test |
| The access token leaks into a response or a log line | Contract guarantee G1 with an explicit unit assertion |
| Unlinking an Account clobbers another field | Only the two Plaid columns are assigned, as `views/accounts.py:286-288` already does; asserted in tests |
| Adding a table column silently breaks the acceptance row assertions | `test_4_table` is updated in the same milestone as the template (M2) |
| An acceptance test that POSTs the endpoint makes a real network call to Plaid | Acceptance covers only up to the confirmation; the POST is unit- and sandbox-tested (R7) |
| `tox -e jsdoc` with the system jsdoc 3.6.3 deletes the committed `jsdoc.*.rst` files | Use jsdoc 4.0.4 from a scratch prefix; recovery command in [quickstart.md](./quickstart.md) |
| Regenerating screenshots destroys the PNGs or drags unrelated ones into the PR | Documented ordering constraint; commit only the `plaid-update` PNGs this change alters |
| A pre-existing flaky test is blamed on this change, or masks a real break | Known flaky tests listed in the Test Gate note and re-run in isolation |

## Complexity Tracking

No Constitution Check violations. Nothing to justify.
