# Phase 0 Research: Index Page Account Balances Chart — History Limiting

**Feature**: `specs/20260907-122155-index-chart-history-limit`
**Date**: 2026-09-07

## R1: Where the time actually goes today

**Finding**: The reported slowness has three distinct causes, and the largest one is not
the one the issue names.

`AcctBalanaceChartView.get()` in `biweeklybudget/flaskapp/views/index.py`:

```python
for bal in db_session.query(AccountBalance).order_by(
    asc(AccountBalance.overall_date)
).all():
    ...
    data[ds][bal.account.name] = float(bal.ledger)
```

1. **N+1 queries (dominant cost).** `AccountBalance.account` is declared as
   `relationship("Account", backref="all_balances")` with SQLAlchemy's default
   `lazy='select'` loading. `bal.account.name` therefore issues a `SELECT` per balance
   row. At the reporter's scale — five years of daily balances across ten accounts,
   ≈18,000 rows — that is ≈18,000 round trips to MariaDB for data the method has
   *already* loaded into its own `accounts` dict two lines earlier.
2. **Unbounded fetch.** Every `AccountBalance` row ever recorded is loaded and
   materialised, then almost all of it is discarded by the chart being unreadable anyway.
3. **Unbounded payload and render.** ≈1,825 dates × ~10 series is serialised to JSON and
   handed to Morris, which draws every point. This is the "almost illegible" half of the
   complaint.

**Decision**: Fix all three. (1) is a one-line change (`accounts[bal.account_id]` instead
of `bal.account.name`) with an outsized payoff and no behavioural change; it is worth
doing on its own merits and would help even without the rest of the feature. (2) becomes a
date-bounded query. (3) becomes interval sampling.

**Rationale**: Doing only the windowing the issue asks for would leave the N+1 in place,
so "all history" would remain as slow as it is today — and "all history" is exactly the
view the issue's own suggested UX ("allow the user to zoom out") makes reachable in one
click. Fixing the query is what makes the zoom-out affordance honest.

**Alternatives considered**: `joinedload(AccountBalance.account)` would also eliminate the
N+1, but it fetches and constructs `Account` objects that are not needed at all — the
view already has an `{id: name}` map. Using the map is both faster and less code.

## R2: Chart library — keep Morris, do not wait for #215

**Decision**: Implement on the bundled Morris.js, unchanged. Do not adopt a new charting
library as part of this feature.

**Rationale**:

- The constitution's Technology & Security Constraints require that "New UI work MUST
  follow the existing modal/DataTables patterns rather than introducing a parallel
  frontend stack". Morris is the charting library this application uses, in `index.html`,
  `budgets.html` and `fuel.html`.
- The issue frames the library swap as conditional ("It's possible that **if we do #215**
  …"), not as a requirement of this fix. #215 is separate work with its own scope
  covering three pages, not just this chart.
- Morris exposes `setData(data)` on an existing chart instance (verified present in the
  bundled `static/startbootstrap-sb-admin-2/vendor/morrisjs/morris.min.js`), which is all
  the "zoom out" behaviour needs: redraw in place, no page reload, no new dependency.

**Alternatives considered**:

- *Chart.js / ECharts / Plotly with built-in brush-zoom.* Gives interactive zoom for free
  and is genuinely nicer, but it is a new AGPL-compatible-licence review, a new bundled
  asset, a rewrite of three charts to stay consistent, and a much larger acceptance-test
  surface — all to deliver a UX that a seven-button range selector delivers adequately.
  That is #215's job, and this feature is explicitly built so that #215 can replace the
  selector later without revisiting the server side.
- *Server-side rendered static image.* Loses hover values entirely; regression in
  usability.

**Consequence recorded for #215**: the endpoint's `days` parameter and the sampling logic
are library-agnostic. Whoever does #215 replaces the button group and the `Morris.Line`
call; the view does not change.

## R3: Windowing strategy — days back from today, not "last N points"

**Decision**: The window is expressed as a number of **days back from now**, with `0`
meaning "all recorded history". Not a count of data points.

**Rationale**: The issue offers both framings ("last N data points (or days/months/years)").
Days are the better primitive here because balance records are not evenly spaced — an
account updated by OFX daily and one updated manually every few months both contribute
rows, so "the last 500 points" is a different amount of history depending on which
accounts are active. A user reasoning about "the last year" wants a year. Point count is
still bounded, separately, by the sampling limit (R4), which is the thing that actually
protects render time.

**Alternatives considered**: A `start_date`/`end_date` pair. More general, but the spec
scopes out arbitrary custom ranges, and a single integer keeps the fallback rule (R6)
trivial.

## R4: Sampling strategy — regular interval, last point pinned

**Decision**: After the in-window data is assembled and forward-filled, if the number of
dates exceeds `ACCOUNT_BALANCE_CHART_MAX_POINTS`, keep every *n*-th date where
`n = ceil(total_dates / max_points)`, and always append the final date if the stride
skipped it.

**Rationale**:

- Regular striding preserves the *shape* of a slow-moving balance series. Account balances
  are not spiky signals where a skipped sample loses an event; they are step functions
  that change by small amounts day to day.
- Pinning the last point matters disproportionately: the right-hand edge of this chart is
  "what are my balances now", and a stride that happened to land two days short would make
  the chart silently disagree with the account tables directly below it on the same page.
  This is FR-005 and it is the one sampling rule that is not merely cosmetic.
- `ceil` rather than `floor` guarantees the result is ≤ `max_points`; `floor` can overshoot.

**Alternatives considered**:

- *Averaging / bucketing into weeks or months.* Produces a smoother line but reports
  balances that were never actually held on any date. For a financial application where a
  hovered value should be a real recorded balance, that is the wrong trade.
- *Min/max envelope per bucket (as used for waveform display).* Doubles the series count
  and is designed for high-frequency signals; overkill here.
- *`LIMIT`/`OFFSET` or SQL-side modulo sampling.* Sampling must happen after
  forward-filling (R5), so it cannot be pushed into the row query without changing the
  values produced.

**Chosen defaults**: `ACCOUNT_BALANCE_CHART_DEFAULT_DAYS = 365` and
`ACCOUNT_BALANCE_CHART_MAX_POINTS = 300`. A year is the smallest window in which seasonal
shape is visible and it is what "how am I doing" questions are asked over. 300 points is
roughly one pixel-column per point at the panel's rendered width on a typical screen —
enough that the line looks continuous, and 6× below the ≈1,825 points that make the
current chart illegible. Both are settings, so neither is a one-way door.

## R5: Forward-fill correctness at the window boundary

**Finding**: Today's code forward-fills each account's last known balance across dates
where that account has no record, so lines stay continuous (FR-011). Naively adding a
`WHERE overall_date >= window_start` filter breaks this: an account whose most recent
balance predates the window has no in-window row at all, so it would either vanish from
the chart or be plotted as `None`/zero — which for a financial chart reads as "this
account went to zero", a materially wrong statement.

**Decision**: Issue a second, small "seed" query for each account's most recent balance
strictly *before* the window start, and use those values to initialise the forward-fill
carry-over before walking the in-window dates.

**Rationale**: This is the difference between a windowed chart that is correct and one
that is quietly wrong for dormant accounts — precisely the accounts a user is least likely
to notice being wrong. The seed query is bounded by account count, not by history size.

**Implementation note**: the seed is naturally expressed as a grouped sub-query
(`MAX(overall_date) per account_id WHERE overall_date < window_start`) joined back to the
balances, or, given that account count is small (tens), as one small ordered query per
account. The grouped form is preferred; either is O(accounts), not O(history).

**Existing quirk to preserve deliberately**: the current implementation drops the very
first date in the result set, using it only as the forward-fill seed and never plotting
it. With an explicit seed query that hack is no longer needed, and the first in-window date
becomes plottable. This is a small, strictly-better behaviour change (one more point at
the left edge) and is called out here so it is not mistaken for a regression when
acceptance-test expectations shift by one row.

## R6: Parameter validation and fallback

**Decision**: `days` is read from the query string. It falls back to
`ACCOUNT_BALANCE_CHART_DEFAULT_DAYS` when absent, non-integer, or negative. `days=0` is
the explicit, valid "all history" value. There is no upper clamp, because `0` already
means unbounded and any large positive value is therefore equivalent to a value the user
can already request.

**Rationale**: FR-010 requires predictable handling of bad input. Silently defaulting is
right for a chart — an error page or a 400 in place of a chart is a worse outcome for a
mistyped URL than simply showing the default view, and this endpoint has no side effects.

## R7: Settings mechanism

**Decision**: Two new integers in `biweeklybudget/settings.py`, added to the existing
`_INT_VARS` list so they can also be overridden by environment variables, and mirrored
into `biweeklybudget/settings_example.py`.

**Rationale**: This is exactly the pattern `DEFAULT_ACCOUNT_ID` and `FUEL_BUDGET_ID`
already follow. Both new settings have module-level defaults and are absent from
`_REQUIRED_VARS`, so an existing installation that upgrades without touching its settings
module gets the documented defaults and nothing fails (FR-002, User Story 3 scenario 3).

**Reaching the template**: `biweeklybudget/flaskapp/context_processors.py` already injects
every settings global into the Jinja context as `settings`. `index.html` can therefore emit
the default directly as a JavaScript variable, following the existing
`var CURRENCY_SYMBOL = "{{ CURRENCY_SYM }}";` precedent in `base.html`. No view change is
needed to plumb it through.

**Documentation**: `docs/source/biweeklybudget.settings.rst` is autodoc over
`settings.py`, so `#:` comments on the new constants are the documentation. An
`app_usage.rst` section covers the user-facing behaviour.

## R8: Testing approach

**Decision**: Three layers.

1. **Unit tests, no database** (`biweeklybudget/tests/unit/flaskapp/views/test_index.py`,
   new file). The sampling and parameter-parsing logic is extracted into small module-level
   helper functions so it can be tested directly, following the precedent set by
   `test_formhandlerview.py` which instantiates a view subclass and calls one method. This
   is where the interesting cases live: stride arithmetic, the ≤ `max_points` guarantee,
   the pinned-last-point rule, fewer-points-than-the-limit being untouched, empty input,
   and every `days` fallback case.
2. **Acceptance tests** (`biweeklybudget/tests/acceptance/flaskapp/views/test_index.py`,
   extended). Chart renders on page load; the range button group is present with the
   default marked active; clicking a range redraws without navigation; the endpoint
   honours `days` and returns a bounded point count. These run against the existing sample
   data via the `refreshdb` fixture.
3. **A large-data test.** The existing sample data has only a handful of balances, so it
   cannot demonstrate the bound. A test that seeds a few thousand synthetic
   `AccountBalance` rows and asserts the response stays at or below `max_points` is what
   actually pins SC-002 and SC-003.

**Rationale**: The constitution's Test Gate requires new code be "covered by valid tests,
not tests written to pass". The bound is the whole point of the feature, so a test that
only ever sees small data would be exactly such a hollow test.

## R9: Documentation surface

**Decision**: `docs/source/app_usage.rst` gains an "Account Balances Chart" section;
`settings.py` / `settings_example.py` carry the `#:` docs; `CHANGES.rst` gains a 1.10.0
entry; `biweeklybudget/version.py` goes `1.9.0` → `1.10.0`.

**Rationale**: Constitution IV (documentation is part of the change) and VI (versioned,
changelogged releases). MINOR is the right bump: new user-visible capability, new
settings, no removal and no incompatible change to the existing endpoint's response shape.

**Also affected**: adding named, JSDoc-commented functions to `static/js/index.js` will
cause `tox -e jsdoc` to generate a new `docs/source/jsdoc.index.rst` and add it to
`jsdoc.rst`. That is generated output that belongs in the commit, per the release
checklist's "docs regenerated … and committed".
