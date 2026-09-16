---

description: "Task list for Delete a Plaid Item (issue #269)"
---

# Tasks: Delete a Plaid Item

**Input**: Design documents from `specs/20260916-062828-plaid-delete-item/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md),
[contracts/plaid-delete-item.md](./contracts/plaid-delete-item.md),
[quickstart.md](./quickstart.md)

**Status**: Complete through M4.

**Tests**: Included, and not optional here. Constitution Principle II requires new code to be
covered by valid tests. This feature deletes rows from a financial database, so the tests that
pin the *order* of those deletions and the "nothing was written" abort path are the substance
of the change, not an afterthought.

**Organization**: Phases map onto the milestones in `plan.md`. Commit messages use the prefix
`Plaid Delete Item - M{milestone}.{task}` per Constitution Workflow step 4. Human approval is
required to advance from one milestone to the next (Principle I).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task serves (US1, US2, US3, US4)
- Paths are relative to the repository root

---

## Phase 1: Setup

**Purpose**: Make the environment able to run and verify the change. No source edits.

- [X] T001 Start the MariaDB test container and export the test-database environment described in `CLAUDE.md`, then run `python dev/setup_test_db.py`; in a worktree use the main checkout's tox at `/home/jantman/GIT/biweeklybudget/venv/bin/tox` and `touch .tox/acceptance/liveserver.log` before the first acceptance run (per [quickstart.md](./quickstart.md))
- [X] T002 Record a pre-change baseline by running `tox -e py314 -- biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` and `tox -e acceptance -- biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py`, redirecting output to the scratchpad per `CLAUDE.md`

**Checkpoint**: Test database up, both suites runnable from the worktree, baseline recorded.

---

## Phase 2: Foundational — Plaid failure classification (Milestone M1, part 1)

**Purpose**: The endpoint cannot be written until it is decided, in code, which Plaid failures
mean "this Item is already gone" and which mean "abort". Everything in Phase 3 depends on it.

**⚠️ BLOCKING**: T003–T004 must complete before Phase 3 begins.

- [X] T003 [US2] Add the module-private failure classifier to `biweeklybudget/flaskapp/views/plaid.py` implementing contract C2 in [contracts/plaid-delete-item.md](./contracts/plaid-delete-item.md): parse `ApiException.body` as JSON (decoding `bytes` first), return `True` only for `error_code` in `ITEM_NOT_FOUND` and `INVALID_ACCESS_TOKEN`, and return `False` — never raise — for every other code, a missing `error_code`, a `None` body, a non-object body, and unparseable JSON; docstring in the file's existing style naming why `INVALID_API_KEYS` is excluded
- [X] T004 [US2] Add `TestPlaidDeleteItemRecoverable` (or equivalent) to `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` with one test per row of contract C2's table, including the three "must not raise" rows, constructing `ApiException` the way the existing Plaid tests do

**Checkpoint**: The classifier exists and every branch of it is covered.

---

## Phase 3: User Stories 2, 3 and 4 — the endpoint (Priority: P1/P2, Milestone M1, part 2)

**Goal**: Deleting an Item removes it at Plaid, unlinks its Accounts without touching anything
else about them, removes its Plaid rows, and either completes fully or changes nothing.

**Independent Test**: POST `/ajax/plaid/delete_item` directly (no UI) with the Plaid client
mocked and confirm: the Plaid removal is requested with the Item's access token before any
local write; the unlink/delete/commit sequence happens in the order
[data-model.md](./data-model.md) requires; and a non-recoverable Plaid failure leaves the
session untouched.

### Implementation for User Stories 2, 3 and 4

- [X] T005 [US2] Add `ItemRemoveRequest` to the `plaid.models` import block in `biweeklybudget/flaskapp/views/plaid.py`
- [X] T006 [US2] Add `PlaidDeleteItem(MethodView)` to `biweeklybudget/flaskapp/views/plaid.py` implementing contract C1, modelled on `PlaidRefreshAccounts`: read `item_id` from the JSON body (400 if absent), look the Item up with `db_session.query(PlaidItem).get(item_id)` (404 if `None`), then call `plaid_client().item_remove(ItemRemoveRequest(access_token=item.access_token))` inside `try`/`except ApiException`, aborting with 400 unless the T003 classifier says the Item is already gone — with a class docstring in the file's existing style
- [X] T007 [US3] In `PlaidDeleteItem.post`, after a successful Plaid removal, collect the `Account` rows with `plaid_item_id == item_id`, record their `"Name (id)"` strings for the response, and set **only** `plaid_item_id` and `plaid_account_id` to `None` on each — the same two assignments `biweeklybudget/flaskapp/views/accounts.py:286-288` makes for the "none" choice
- [X] T008 [US4] In `PlaidDeleteItem.post`, after the unlink, `db_session.delete()` each `PlaidAccount` with `item_id == item_id`, then `db_session.delete(item)`, then a single `db_session.commit()` covering all three — the order and the single commit are what give contract guarantee G2
- [X] T009 [US2] Return `{'success': True, 'item_id': ..., 'accounts_unlinked': [...]}` on success, and log the deletion at info level **without** the access token (contract guarantee G1)
- [X] T010 [US2] Register the route in `set_url_rules` in `biweeklybudget/flaskapp/views/plaid.py` as `a.add_url_rule('/ajax/plaid/delete_item', view_func=PlaidDeleteItem.as_view('plaid_delete_item'))`

### Tests for User Stories 2, 3 and 4

- [X] T011 [US2] Update `TestSetUrlRules::test_rules` in `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` — add `PlaidDeleteItem=DEFAULT` to the `patch.multiple` call and the new `add_url_rule` call to the exact ordered assertion list. This is a required edit; the test fails without it
- [X] T012 [US2] Add `TestPlaidDeleteItem::test_normal` to `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` following the `TestPlaidRefreshAccounts::test_normal` mocking style (`patch.multiple(pbm, jsonify=DEFAULT, request=mock_req, plaid_client=DEFAULT, PlaidItem=DEFAULT, PlaidAccount=DEFAULT, Account=DEFAULT, ItemRemoveRequest=DEFAULT, db_session=mock_sess)`), asserting the Plaid client received `item_remove` with the Item's access token **and** the exact ordered `db_session.mock_calls` list: query, unlink, delete each PlaidAccount, delete the Item, one commit
- [X] T013 [P] [US3] Add `TestPlaidDeleteItem::test_no_linked_accounts` asserting the deletion succeeds, `accounts_unlinked` is `[]`, and no Account is written
- [X] T014 [P] [US3] Add `TestPlaidDeleteItem::test_unlink_touches_only_plaid_columns` asserting that exactly `plaid_item_id` and `plaid_account_id` are assigned `None` on each affected Account and that no other attribute is set
- [X] T015 [P] [US2] Add `TestPlaidDeleteItem::test_item_not_found_at_plaid` and `test_invalid_access_token`, each raising an `ApiException` whose body carries that `error_code`, asserting the local deletion still completes
- [X] T016 [P] [US4] Add `TestPlaidDeleteItem::test_plaid_exception` raising a non-recoverable `ApiException` (use `INVALID_API_KEYS`), asserting a 400 response whose message matches the existing `'Exception: Status Code: ...'` format **and** that `db_session.mock_calls` contains no write — the "changes nothing" guarantee
- [X] T017 [P] [US4] Add `TestPlaidDeleteItem::test_missing_item_id` (400) and `test_unknown_item_id` (404, no Plaid call, no DB write)
- [X] T018 [P] [US2] Add `TestPlaidDeleteItem::test_access_token_not_in_response` asserting the token string appears in no response body on either the success or the failure path
- [X] T019 Run `tox -e py314` to completion and confirm it passes, redirecting output to the scratchpad

**Checkpoint (Milestone M1)**: The endpoint is complete and fully covered. Deleting an Item is
possible by POSTing it directly; nothing in the UI offers it yet.

---

## Phase 4: User Story 1 — the UI (Priority: P1, Milestone M2)

**Goal**: The maintainer can delete an Item from the Plaid Update page, after a confirmation
that tells them exactly what will happen.

**Independent Test**: Load `/plaid-update`, confirm every Item row offers `Delete`, open the
confirmation for an Item with a linked Account and check it names the Item, the institution,
the Account to be unlinked, the Plaid-side removal and the irreversibility — then dismiss it
and confirm nothing was requested and nothing changed.

### Implementation for User Story 1

- [X] T020 [US1] Add the `Delete` column to `biweeklybudget/flaskapp/templates/plaid_form.html` per contract C3.1 — a `<th>Delete</th>` after `Refresh Accounts`, and a cell rendering `<a onclick="plaidDeleteConfirm(...)">Delete</a>` passing the item id, `i.institution_name` and `accounts[i.item_id]` through `|tojson` (institution names are free text from Plaid and can contain apostrophes)
- [X] T021 [US1] Add `plaidDeleteConfirm(item_id, institution_name, account_names)` to `biweeklybudget/flaskapp/static/js/plaid_prod.js` per contract C3.2/C3.3 — populate the shared `#modalDiv` following the `creditPayoffErrorModal.js` pattern, state the Accounts that will be unlinked or that there are none, state that the Item will also be removed at Plaid and that the action cannot be undone, show and relabel `#modalSaveButton` as a destructive `Delete`, and make **no** request
- [X] T022 [US1] Add `plaidDelete(item_id)` to `biweeklybudget/flaskapp/static/js/plaid_prod.js` — POST `/ajax/plaid/delete_item` in the style of `plaidRefresh`, `location.reload()` on success, and on failure surface the server's `message` **without** reloading so the unchanged page stays in front of the maintainer; JSDoc both functions in the file's existing style

### Tests for User Story 1

- [X] T023 [P] [US1] Add a `plaid_form.html` render test to `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` in the style of `TestPlaidResultTemplate`, asserting the Delete link and its arguments appear for each Item, including correct escaping for an institution name containing an apostrophe
- [X] T024 [US1] Update `test_4_table` in `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py` for the new eighth cell, `'Delete'`
- [X] T025 [US1] Add acceptance tests to `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py` that click `Delete` on a fixture Item, assert the modal is shown and its body names the Item, the institution and the Account that would be unlinked, then dismiss it and assert the Plaid Items table is unchanged and no request was made
- [X] T026 [P] [US1] Add an acceptance test for an Item whose Plaid Accounts are linked to no Account, asserting the modal says so explicitly rather than showing an empty list
- [X] T027 Run `tox -e py314` and then `tox -e acceptance` to completion (they share the test database, so run them in sequence) and confirm both pass, redirecting output to the scratchpad

**Checkpoint (Milestone M2)**: The feature is usable end to end in the UI, with the delete
round trip proven by unit tests and the confirmation proven by acceptance tests.

---

## Phase 5: End-to-end and documentation (Milestone M3)

**Purpose**: Prove the real Plaid call works, and stop the documentation recommending the raw
SQL this feature replaces.

- [X] T028 [P] [US2] Append delete steps to the incremental sandbox class in `biweeklybudget/tests/acceptance/test_plaidlink.py` — delete the linked Item through the UI after `test_19_update_transactions`, then assert `plaid_items` and `plaid_accounts` are empty, that the previously linked Accounts still exist with `plaid_item_id`/`plaid_account_id` `None`, and that their `OFXTransaction`/`OFXStatement` rows are unchanged in number
- [X] T029 [P] Add a `.. _plaid.deleting:` "Deleting a Plaid Item" subsection to `docs/source/plaid.rst` after "Linking Accounts to Plaid", describing the UI steps, what the confirmation shows, that the Item is removed at Plaid, that Accounts are unlinked but keep their data, and that the action cannot be undone
- [X] T030 Rewrite steps 1-2 of `.. _plaid.change-env:` ("Changing Plaid Environments") in `docs/source/plaid.rst` to delete each Item through the UI instead of running `UPDATE accounts SET plaid_item_id=NULL...` and `DELETE FROM plaid_accounts; DELETE FROM plaid_items;`, and say explicitly that Items must be deleted **before** `PLAID_ENV`/`PLAID_SECRET` change — noting that an Item stranded by an already-completed switch is still deletable, because Plaid's `INVALID_ACCESS_TOKEN` counts as already-removed ([research.md](./research.md) R2)
- [X] T031 Extend the `/plaid-update` entry's `description` in `docs/make_screenshots.py` to mention the Delete action; do **not** hand-edit `docs/source/screenshots.rst`, which that script generates
- [X] T032 Regenerate `docs/source/jsdoc.plaid_prod.rst` with `tox -e jsdoc` using jsdoc **4.0.4** from a scratch prefix on `PATH` (the system 3.6.3 deletes every committed `jsdoc.*.rst` and then fails); commit only `jsdoc.plaid_prod.rst` and revert any unrelated `jsdoc.*.rst` the run rewrites
- [X] T033 Regenerate the Plaid Update screenshots with `tox -e screenshots`; commit only `docs/source/plaid-update.png`, `docs/source/plaid-update_sm.png` and the `screenshots.rst` change this feature's caption produces, reverting the unrelated drift the generator introduces. Never run `docs` while `screenshots` is running

**Checkpoint (Milestone M3)**: The real Plaid round trip is covered, and no documentation still
tells the maintainer to delete Plaid rows by hand.

---

## Phase 6: Gate and deliver (Milestone M4)

**Purpose**: Constitution Principle II — no feature is complete while any test fails.

- [X] T034 Run `tox -e py314` to completion and confirm it passes, redirecting output to the scratchpad
- [X] T035 Run `tox -e acceptance` to completion and confirm it passes (~17 min; start it in the background). Re-run any known-flaky failure (reconcile drag/unignore, fuel-log search, Plaid `test_6_uncheck_all`) in isolation before attributing it to this change
- [X] T036 [P] Run `tox -e migrations` to confirm the migration head still matches the models — demonstrating rather than asserting that this change needs no migration
- [X] T037 [P] Run `tox -e docs` **after** T033's screenshots are committed, and confirm it builds clean. Re-run on a transient linkcheck timeout
- [X] T038 Run `tox -e docker` with the main checkout's `venv/bin` first on `PATH` so its final acceptance step can find tox, and not while T035 is still running. If this host kills it for low memory, say so plainly and let the CI `docker` job be the gate
- [X] T039 Add the `CHANGES.rst` entry under `Unreleased` — one concise bullet led by the issue #269 link, naming the new Delete action, that it also removes the Item at Plaid, and that linked Accounts are unlinked but keep their data. Do **not** touch `biweeklybudget/version.py`
- [ ] T040 Update this file and `spec.md` to record completion, commit the whole of Milestones M1-M4, push the branch with `git push -u origin HEAD:refs/heads/robot-army/issue-269-plaid-add-ability-to-delete-an-item` (the branch's upstream is `origin/master`, so a bare `git push` would target master), and open the pull request
- [X] T041 Watch the PR's CI jobs to completion; investigate any failure, re-running known-flaky jobs before attributing them to this change
- [X] T042 Run `/answer-reviews` on the PR and repeat until Claude's review reports "No issues found" and Copilot's, if present, recommends approval

**Checkpoint (Milestone M4)**: Green suites, documentation shipped, PR open and reviewed.

### Gate results (2026-09-16)

| Suite | Result |
|---|---|
| `py314` | 993 passed, 4 skipped; pycodestyle and pyflakes clean (cache cleared, so every style check ran) |
| `acceptance` | 905 passed, 0 failed, 21m10s — first attempt, no known-flaky test needed a re-run |
| `migrations` | 10 passed — head still matches the models, demonstrating that no revision is needed |
| `docs` | builds clean; linkcheck clean; `sphinx-apidoc` regenerated no tracked file |
| `docker` | `docker: OK` — image builds, `GET /` and the console-script checks pass, and the full acceptance suite run against the container exits 0 |
| `plaid` | **not run locally** — needs Plaid sandbox credentials that are not available on this machine. The two new steps in `test_plaidlink.py` are therefore unexercised here; CI runs this job with the repository's secrets, though the class is `xfail`ed there for an unrelated reason. |

---

## Dependencies

```text
Phase 1 (Setup)
   └─▶ Phase 2 (classifier)          BLOCKING
          └─▶ Phase 3 (endpoint)     US2, US3, US4
                 └─▶ Phase 4 (UI)    US1 — needs the endpoint to POST to
                        └─▶ Phase 5 (e2e + docs)
                               └─▶ Phase 6 (gate + deliver)
```

**Story dependencies**: US2 (removal at Plaid), US3 (Accounts survive) and US4 (failure changes
nothing) are all properties of the endpoint and are delivered together in Phase 3; they are
independently *testable* but not independently *shippable*, because they are three guarantees
about one operation. US1 (the UI) depends on the endpoint existing.

**Within-phase parallelism**: T013–T018 are separate test methods and can be written in
parallel once T006–T010 are in place. T028–T031 touch four different files. T036 and T037 are
independent tox environments, but neither may overlap T035 (shared test database) and T037 must
not overlap T033 (`make_screenshots.py` deletes every PNG at start).

## Implementation Strategy

**MVP**: Phases 1–4. That is the whole user-visible feature: a Delete action that works, is
confirmed, and is safe. Phase 5 adds the sandbox proof and the documentation; Phase 6 is the
constitution's gate.

**Not an MVP shortcut**: Phase 3 cannot be trimmed to "delete the rows and skip the Plaid
call". A local-only delete is worse than no delete — it strands a live, billable Item at Plaid
and destroys the only access token that could reach it. US2 ships with US1 or neither does.

### CI results on PR #348

All eleven checks pass: `py314`, `acceptance`, `docker`, `docs`, `jsdoc`, `screenshots`,
`migrations`, `plaid`, `coverage`, `claude-review`, Snyk.

Two things worth recording:

- **`docker` failed on the first run and passed on a re-run**, with a single failure out of
  905: `test_reconcile.py::TestOFXMakeTransAndIgnore::test_36_ignore_and_unignore_ofx`
  (`assert {'2%OFX30': 'My Note'} == {}` — the unignore had not landed when the assertion
  ran). That is the repository's most frequently flaky test, it is in reconcile, which this
  change does not touch, and the **same test passed in the `acceptance` job on the same
  commit** as well as in both local runs. Re-run in isolation via `gh run rerun --failed`,
  per the Test Gate note in [plan.md](./plan.md); it passed.
- **The `plaid` job passed in CI**, where the sandbox credentials exist. Its
  `TestLinkAndUpdateSimple` class is `xfail`ed when `CI == 'true'`, so the two delete steps
  added in M3.1 did not actually execute there — that coverage remains local-only in
  practice, as recorded above.

- **Review**: Claude's automated review reported "No issues found. Checked for bugs and
  CLAUDE.md compliance." No Copilot review was requested on this repository, and no inline
  review comments were left, so there was nothing for `/answer-reviews` to address.

The `coverage` check passes; its 57% comment is a pre-existing project-wide figure against an
aspirational 80% threshold, not a regression from this change.
