# Phase 0 Research: Plaid Item Last Successful Update Time

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-15

All questions below were resolved against the code and the installed dependencies in this
worktree. No `NEEDS CLARIFICATION` items remain.

---

## R1: What exactly does Plaid report, and where does the application already see it?

**Finding**: Plaid's `/item/get` response carries `status.transactions`, an
`ItemStatusTransactions` model whose fields are, per the installed `plaid` package:

```text
{'last_successful_update': (datetime, NoneType),
 'last_failed_update':     (datetime, NoneType)}
```

Both are optional. `last_successful_update` is the time Plaid last successfully pulled
transactions for that Item from the institution — exactly the value the issue asks for.

The application already retrieves this on every update. `plaid_updater.PlaidUpdater._do_item`
calls `item_get` and then logs the whole transactions-status object
(`biweeklybudget/plaid_updater.py:155-158`), discarding it afterwards. A second caller,
`PlaidUpdateItemInfo.post` (`biweeklybudget/flaskapp/views/plaid.py:206`), also calls
`item_get` — today only to read the institution ID — and logs the full response.

**Decision**: Read `status.transactions.last_successful_update` from the `item_get` response
in both callers and persist it on the `PlaidItem`.

**Alternatives considered**:

- *A separate Plaid call dedicated to fetching status.* Rejected: the value is already in a
  response both code paths make; a second call would add latency and API quota use for
  nothing.
- *Store the whole transactions-status object (including `last_failed_update`).* Rejected as
  out of scope by the spec's Assumptions. It would add a second column and a second UI
  column for a question the issue does not ask.

---

## R2: How should the value be accessed on the Plaid response object?

**Finding**: `plaid`'s generated models raise `ApiAttributeError` on attribute access for an
optional field that the server did not send, so `response.status.transactions.last_successful_update`
is unsafe. The models do implement `.get(name, default)`, which is what the existing code
already relies on: `iteminfo.get('status', {}).get('transactions')`.

There is a second trap: `.get('status', {})` returns the *default* only when the key is
absent, so a present-but-`None` value flows through and the chained `.get` raises
`AttributeError`. The existing log line is inside a `try`/`except` and so survives this; the
new code must not depend on that.

**Decision**: Extract the value through chained `.get()` calls with an explicit
falsy-to-empty-dict coercion at each level, so an absent, `None`, or empty status yields
`None` rather than raising:

```text
status      = iteminfo.get('status') or {}
txn_status  = status.get('transactions') or {}
value       = txn_status.get('last_successful_update')
```

**Alternatives considered**: direct attribute access with a `try`/`except ApiAttributeError`.
Rejected — it is more code, it does not handle the `None`-valued-key case, and it diverges
from the `.get()` idiom already used two lines away.

---

## R3: Naive vs. timezone-aware datetimes

**Finding**: `PlaidItem.last_updated` uses `sqlalchemy_utc.UtcDateTime`, whose
`process_bind_param` raises `ValueError('naive datetime is disallowed')` for any datetime
without `tzinfo`, and converts everything else to UTC. Plaid sends RFC-3339 timestamps with a
zone and the client deserializes them to aware datetimes, so the normal case is fine.

The failure mode if it were ever naive, however, is severe and disproportionate: the
`ValueError` would be raised at `db_session.commit()` inside `_do_item`'s broad
`except Exception`, turning a purely cosmetic field into a *whole-Item update failure* — no
transactions stored, the update reported as failed. Absorbing that risk costs two lines.

**Decision**: Normalise in the extraction helper — return the value unchanged if it is
already aware, and attach UTC if it is naive. Keep the same `UtcDateTime` column type as
`last_updated` so the two timestamps are stored and compared identically (FR-009).

**Alternatives considered**: trusting Plaid and letting a naive value raise. Rejected — the
blast radius (a failed financial update) is out of all proportion to the defect being
guarded against, and Principle II's "financial correctness" posture argues against it.

---

## R4: Where does the extraction logic live, given two callers?

**Finding**: The two callers are `biweeklybudget/plaid_updater.py` and
`biweeklybudget/flaskapp/views/plaid.py`. Both already import from `biweeklybudget.utils`
(`plaid_client`, `dtnow`), and `utils.py` is already the home of the other Plaid-facing
helper, `plaid_client()`. `views/plaid.py` additionally imports `plaid_updater`, so either
module would work as a home.

**Decision**: Add one module-level function to `biweeklybudget/utils.py`:

```text
plaid_last_successful_update(item_get_response) -> Optional[datetime]
```

It performs the R2 extraction and the R3 normalisation and nothing else. One function, unit
tested directly, called from both places.

**Alternatives considered**:

- *Duplicate three lines in each caller.* Rejected: the `None`-handling and tz-normalisation
  are exactly the details that drift apart when duplicated.
- *A method on `PlaidItem`.* Rejected: it would put Plaid API response parsing into the model
  layer, which no other model does.
- *In `plaid_updater.py`.* Workable, but would mean the view imports a loose function from a
  module it currently uses only for the `PlaidUpdater` class. `utils.py` is the established
  home for this shape of helper.

---

## R5: Schema change and migration

**Finding**: The current Alembic head is `c5e3a9b1d7f2`
(`c5e3a9b1d7f2_remove_ofxgetter_account_fields.py`) — verified by scanning every revision in
`biweeklybudget/alembic/versions/` for one that no other revision names as its
`down_revision`. The existing `plaid_items.last_updated` column was created in
`f5a002127934_plaid_models.py` as `sa.Column('last_updated', UtcDateTime(timezone=True), nullable=True)`,
which is the exact form the new column must take so that the `migrations` tox environment's
head-vs-models comparison passes (Principle III).

**Decision**: One new revision with `down_revision = 'c5e3a9b1d7f2'`, adding a nullable
`last_successful_update` `UtcDateTime` column to `plaid_items` in `upgrade()` and dropping it
in `downgrade()`. Nullable is required, not merely convenient: existing rows have no value
and none can be invented (FR-010, and the spec's "no backfill is possible" assumption).

**Alternatives considered**: a non-null column with a sentinel default (e.g. the epoch).
Rejected — it would make "never successfully updated" indistinguishable from "successfully
updated in 1970", defeating FR-008.

---

## R6: How the time should be displayed

**Finding**: `plaid_form.html` renders the Plaid Items table with a "Last Polled" column as
`{{ i.last_updated|ago }}`. The `ago` filter (`biweeklybudget/flaskapp/filters.py:96-108`)
formats via `humanize.naturaltime` and returns `''` for `None`, `''`, or an undefined value.

An empty string is precisely what FR-008 forbids for the new column: a blank cell reads as a
rendering bug, not as information.

**Decision**: Add a "Last Successful Update" column immediately after "Last Polled", rendered
with the same `ago` filter so the two are directly comparable (FR-007), wrapped in a
conditional that emits the literal `unknown` when no value is stored (FR-008). "unknown"
covers both cases that produce an empty value — never recorded by us, and reported absent by
Plaid — without asserting which one it is.

**Alternatives considered**:

- *Change the `ago` filter to return a placeholder.* Rejected: `ago` is used across the
  application, and changing it would put "unknown" into unrelated columns, including "Last
  Polled" on this same table.
- *A new `ago_or` filter.* Rejected as more machinery than one Jinja conditional needs.
- *"never" as the placeholder text.* Rejected: it asserts that no successful update has ever
  happened, which is not knowable for an Item that simply has not been polled since the
  upgrade.

---

## R7: Which tests are affected, and what new coverage is needed

**Finding**:

- `biweeklybudget/tests/unit/test_plaid_updater.py` — `TestDoItem`'s three tests each stub
  `item_get` as `{'item': {}, 'status': {'transactions': {'foo': 'bar'}}}` and assert the
  exact `db_session` call list. They must gain the new field and an assertion on it.
- `biweeklybudget/tests/unit/flaskapp/views/test_plaid.py` — `TestPlaidUpdateItemInfo`'s
  `item_get` stubs return dicts with only an `'item'` key, and assert per-Item attribute
  values. Same treatment.
- `biweeklybudget/tests/acceptance/flaskapp/views/test_plaid.py` — `test_4_table` asserts the
  Plaid Items table's rows as exact lists of cell text. Adding a column changes every row, so
  this assertion must be updated.
- `biweeklybudget/tests/fixtures/sampledata.py` — `_plaid_items()` builds `PlaidItem1` and
  `PlaidItem2`, both with `last_updated=self.dt` (which renders as "now").
- `biweeklybudget/tests/acceptance/test_plaidlink.py` — the live-Plaid (`plaid` marker) suite;
  `test_11`/`test_12` exercise "Update Item Information from Plaid" against Plaid's sandbox.

**Decision**:

- Give `PlaidItem1` a `last_successful_update` of `self.dt - timedelta(days=3)` and leave
  `PlaidItem2`'s unset. This is chosen deliberately: one fixture row then covers the recorded
  case, the other covers the placeholder case, and the two rows together demonstrate the
  feature's whole point — a recent poll next to an older Plaid-side refresh. Three days is far
  enough from "now" that `humanize` renders the stable string "3 days ago" with no clock-race.
- Add unit tests for `plaid_last_successful_update` covering: a populated value, an absent
  `status` key, a `None`-valued `status`, an absent `transactions` key, an absent
  `last_successful_update`, an already-aware datetime (passed through unchanged), and a naive
  datetime (returned as UTC-aware).
- Extend the existing updater and view unit tests rather than adding parallel ones, so the
  strict `mock_calls` assertions stay authoritative.
- No new acceptance test file: `test_4_table` already asserts the full table and, once the
  fixtures above are in place, covers both the value and the placeholder end to end.

**Alternatives considered**: setting `last_successful_update` on both fixture Items.
Rejected — nothing would then exercise the placeholder path in an acceptance test, and that
path is a named functional requirement (FR-008).

---

## R8: Documentation impact

**Finding**: Principle IV requires documentation to ship with the change, and the `docs` tox
environment must build clean. Relevant surfaces:

- `docs/source/screenshots.rst` has a "Plaid Update" section pointing at
  `plaid-update.png` / `plaid-update_sm.png`. That screenshot shows the Plaid Items table, so
  the new column changes it. Screenshots are produced by `tox -e screenshots`
  (`docs/make_screenshots.py`).
- `docs/source/biweeklybudget.models.plaid_items.rst` and the other API pages are
  `automodule`-generated, so the new column's docstring comment flows through with no manual
  edit.
- No prose in `docs/source/` or `README.rst` enumerates the Plaid Items table's columns
  (a repository-wide search for "Last Polled" finds only the template), so no prose needs
  rewriting — though the screenshot caption can usefully say what the new column means.

**Decision**: Regenerate the two `plaid-update` screenshots, commit them (the maintainer wants
changed screenshots reviewed in the PR, not deferred to a release), and extend the "Plaid
Update" caption in `screenshots.rst` to name the distinction between the two time columns.

**Known operational hazard**: `tox -e docs` deletes generated PNGs, so the `screenshots` and
`docs` environments must not be run in the same chained invocation, and `docs` must not run
after `screenshots` before the PNGs are committed.

---

## R9: Which test suites gate this change

**Finding**: Principle II requires the full unit and acceptance suites; migration and Docker
suites are additionally required for "any change that touches schema or packaging". This
change adds a column and a migration.

**Decision**: The gate for this feature is `py314` (unit), `acceptance`, and `migrations`.
`docs` must also build. The `plaid` environment requires live Plaid sandbox credentials and is
not part of the local gate; `test_plaidlink.py` is reviewed for compatibility but not run.
`docker` is run because the constitution names it for schema changes — the Docker image ships
the migration.
