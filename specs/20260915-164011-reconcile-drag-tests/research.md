# Research: Restore Skipped Reconcile Drag-and-Drop Acceptance Tests

## R1. Why did the second drag-and-drop fail in 2022?

**Finding**: the failure came from the Selenium version the project used then, combined
with the tests reusing one `ActionChains` object. The Reconcile page and ChromeDriver
were not at fault.

- At the skip commits (1936e64, 91d737d, 2022-10-22) `requirements.txt` pinned
  `selenium==3.141.0`.
- In Selenium 3.141.0, `ActionChains.perform()` calls `ActionBuilder.perform()`. That
  encodes every input device's queued actions and sends them, but **never clears the
  queue**:

  ```python
  # selenium 3.141.0 webdriver/common/actions/action_builder.py
  def perform(self):
      enc = {"actions": []}
      for device in self.devices:
          encoded = device.encode()
          if encoded['actions']:
              enc["actions"].append(encoded)
      self.driver.execute(Command.W3C_ACTIONS, enc)
  ```

- Both tests built one `chain = ActionChains(selenium)` and called
  `chain.drag_and_drop(...).perform()` on it repeatedly. The second `perform()`
  resent the first drag, followed by the second.
- The first drag's source is the OFX card the first drop hid (`reconcileTransactions()`
  in `reconcile.js` calls `$(ofx_div).hide()`). Moving the pointer to a hidden element
  fails with `element not interactable: [object HTMLDivElement] has no size and
  location`. That explains every detail in the 2022 note: the first drag always
  worked, the second always failed, and it didn't matter which divs were used or in
  which order.
- The debugging scaffold added in 1936e64 (the wait, sleep and `move_to_element` on
  `trans-1`) queued yet another action on the same chain, so it could not help.
- Selenium 4.2.0 clears each device's queue after sending it (`device.actions = []`
  in `ActionBuilder.perform()`). The project moved to `selenium==4.7.2` in cc9c8e5 /
  9bdff25 (2024-01-24) and now pins 4.48.0, which does the same. Nobody re-enabled the
  skipped classes after that upgrade.

**Evidence**:

- Source of `ActionBuilder.perform()` read from the 3.141.0, 4.2.0 and 4.48.0 wheels.
- With only the two skip markers removed and nothing else changed, both classes pass
  locally on Selenium 4.48.0 / Chromium 152 / ChromeDriver 152: 18 passed (6 real tests
  plus 12 fixture-loading steps).

## R2. How should the restored tests avoid the trap?

**Decision**: start every drag from a fresh `ActionChains`, via one small
`ReconcileHelper` helper that the two restored classes use. A short comment on the
helper explains why.

**Rationale**:

- The tests no longer rely on a queue-clearing behaviour that the library only added
  in 4.2.0. A reader who sees a new chain per drag doesn't need to know that history.
- The helper is where the next drag test will be written, so the comment sits where
  the mistake would be repeated (spec FR-005).
- The old tests repeated a four-line `drag_and_drop(find_element(...),
  find_element(...).find_element(...))` block per drag. A helper makes each drag one
  readable line without changing what is dragged or where it lands.

**Alternatives considered**:

- *Only remove the skip markers.* That passes today, but it keeps the pattern that
  broke (a reused chain) and leaves nothing to warn the next person. Rejected as
  incomplete against FR-004/FR-005.
- *Call `chain.reset_actions()` between drags.* That works, but it is easier to forget
  than a fresh chain and needs the same explanatory comment. Rejected.
- *Convert the other single-drag tests in `TestDragLimitations` to the helper too.*
  Each of those builds a new chain for one drag, so they are not affected. Changing
  them is scope creep. Rejected.

## R3. Do the removed debug waits need replacing?

**Decision**: yes. The scaffold's specific waits on `trans-1` are removed. Instead,
the drag helper waits for its own source and target elements to be present before
dragging.

**Rationale**:

- The scaffold's waits were a guess at a timing problem R1 shows did not exist. They
  also only covered `trans-1`, one element of one drag.
- `AcceptanceHelper.get()` does **not** wait for the page's AJAX. Its
  `wait_for_load_complete()` / `wait_for_jquery_done()` calls come after a `return`
  inside the retry loop, so they never run. Both Reconcile columns load by AJAX after
  page load, so a drag issued right after `get()` can race the column it needs. The
  single passing run in R1 does not prove that race can't happen.
- Waiting for the two elements a drag uses, inside the helper, covers the edge case
  that "a drag must not start until the element it targets exists". It works whether
  the drag is the first after a page load or follows a submit that re-renders both
  columns.
- `TestUIReconcileMulti.test_07`'s existing `wait_for_id(selenium, 'ofx-1-OFX2')` after
  the first submit is kept. It is the original author's wait and still correct.
- Fixing `get()`'s unreachable waits changes the timing of every acceptance test.
  That is out of scope. It is noted for the PR, not fixed here.
- Stability is checked by SC-002 (five consecutive isolated runs), not assumed.

## R5. Why do the Plaid Update Check/Uncheck All tests fail in full local runs? (side quest)

**Finding**: this is a timing race in `test_plaid.py::TestPlaidUpdateView`. It has
nothing to do with this feature.

- The failures:
  - `test_6_uncheck_all` failed in both full local acceptance runs, at line 116:
    `assert not any(b.is_selected() ...)` saw a box still checked.
  - `test_8_check_all` also failed in run 2, at line 135: `all(...)` saw a box still
    unchecked.
  - They run at about 54%, before any reconcile test (about 62%). The modules before
    them are the same as on `master`.
  - The class passed 3/3 isolated runs. It has no failures in the last 24 CI
    `acceptance`/`docker` jobs.
- The links are `<a href="javascript:plaidSetAllItems(true|false);">` in
  `plaid_form.html`. Navigating to a `javascript:` URL is queued as a task by the
  browser. It does not run synchronously inside the WebDriver click, so the tests race
  it by reading `is_selected()` immediately.
- The test results fit that explanation:
  - In `test_8`, the native checkbox click on `item_PlaidItem1` took effect at once
    (`assert not one.is_selected()` passed). Only the `javascript:` link lagged.
  - `test_7` makes a second WebDriver click after Uncheck All, which gives the queued
    task time to run, and it passed both times.
- The driver's defaults rule out the page not being loaded: the page-load strategy is
  "normal", so `get()` waits for `load` and `plaidSetAllItems` is defined before any
  click.

**Decision**: add a test helper, `click_set_all()`. It wraps the page's global
`plaidSetAllItems` so that every call's argument is recorded in
`window.plaidSetAllCalls`, clicks the link, then waits (up to 5 s) until that list is
exactly `[checked]`. Use it for every Check/Uncheck All click in the class (tests 6, 7
and 8). `test_7` needs it too, or a late Uncheck All could clear the box it checks
next. The original assertions stay unchanged.

- **Why wait on the call, not the checkbox state** (from the PR #346 review): a
  state-based wait passes immediately for a click that changes nothing. `test_8`'s
  second Check All click happens with every box already checked, so its assertion
  would pass even if the link were broken.
- **Why the assertions then see final state**: the javascript: URL looks up
  `plaidSetAllItems` on the page's global scope when it runs, so it calls the wrapper.
  The wrapper records the call and runs the original in the same JS task, so when the
  wait sees the call the checkboxes are already set, and the tests' assertions check
  real state.
- **Wrapped once**: the wrapper is installed only once per page, so calling the helper
  twice (`test_8`) doesn't wrap the wrapper and record each click twice.

**Alternatives considered**:

- *Change the links to `onclick` handlers.* That is an application change, which
  FR-006 rules out. It would also be a UI change nobody asked for.
- *Re-run until green / call it a flake.* Principle II rules that out, and it failed in
  2 of 2 full runs.
- *`sleep()` after the click.* Slower and still racy. An explicit wait for the state
  is exact.

## R4. Does the same cause affect other tests?

**Finding**: no. Every other `ActionChains` use in the acceptance tests
(`TestDragLimitations`, `test_charts.py`, `test_budget_spending.py`,
`test_plaidlink.py`) and in `docs/make_screenshots.py` either builds a new chain per
`perform()` or performs once. The known flaky reconcile tests (`test_11_unreconcile`,
`test_36_ignore_and_unignore_ofx`) are missing-wait races after a click. They are
unrelated and stay out of scope.
