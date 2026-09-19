# Phase 0 Research: Credit Payment Panel Window

**Feature**: Credit Payment Panel Window
**Spec**: [spec.md](./spec.md)
**Date**: 2026-09-19

Everything this change touches already exists; there is no new technology to evaluate.
What follows records the decisions taken about *how* to change it, and the alternatives
rejected.

---

## D-1: Where the per-account bound is computed

**Decision**: inside `CreditPaymentAttribution`, in a new `_effective_begin_date()`
helper called from `__init__` before `_calculate()`. `self.begin_date` becomes the
effective date; the configured setting is kept separately as
`self.configured_begin_date`.

**Rationale**: every existing consumer of the window — `_charges_by_period()`,
`_prior_payments()` — already reads `self.begin_date`. Assigning the effective date to
that attribute makes the whole calculation consistent with FR-008 without touching either
query. `as_dict` already publishes `begin_date`, so the panel gets the effective date for
free (FR-016), and the view layer needs no change at all.

**Alternatives considered**:

- *Compute it in the view and pass it in.* Rejected: it would have to be recomputed by
  every other caller, and the class is the thing that owns the window's definition.
- *Add a separate `effective_begin_date` attribute and leave `begin_date` as the
  setting.* Rejected: `_charges_by_period()` and `_prior_payments()` would each need
  changing to read the new attribute, and any future query added to the class would
  silently use the wrong one. Making the single existing attribute correct is safer.
  The configured value is still exposed, under a name that says what it is.

---

## D-2: The derivation query

**Decision**:

```python
q = self._db.query(func.min(Transaction.date)).filter(
    Transaction.credit_payment_acct_id.__eq__(self.account.id),
    Transaction.date.__le__(self.payment_date)
)
```

`exclude_txn_id` is deliberately **not** applied (FR-005). If the result is `None`, the
configured begin date stands (FR-004). Otherwise the effective begin date is
`max(configured, BiweeklyPayPeriod.period_for_date(first, db).next.start_date)`.

**Rationale**:

- `func.min` over the indexed date column does the work in the database; the alternative
  (`order_by(...).first()`) materialises a `Transaction` for no reason.
- Bounding by `payment_date` mirrors how every other query in the class is bounded, and
  is what makes the back-dating edge case (FR-003, Example E) fall out for free rather
  than needing a special case.
- Not applying `exclude_txn_id` keeps the panel identical between entering a payment and
  reopening it (FR-005). The excluded transaction is still excluded from
  `_prior_payments()`, which is the only place double-counting could occur.
- `BiweeklyPayPeriod.period_for_date(...).next.start_date` is the existing API for
  "the period after this one"; `.next` is an existing property, so no pay-period
  arithmetic is reimplemented.

**Alternatives considered**:

- *Anchor at the start of the period containing the first payment.* Rejected during
  planning and recorded as spec D-1a: it leaves the anchoring payment inside the window,
  where `_prior_payments()` subtracts it a second time and the surplus spills forward
  through `_consume()`, understating unpaid charges on every subsequent payment.
- *Anchor at the day after the first payment's date.* Correct arithmetically, and it was
  put to the maintainer, who chose period alignment. It would make the oldest row a
  partial pay period, which the table's "Pay Period" column does not admit of.
- *Anchor at the most recent designated payment rather than the earliest.* Rejected: it
  would discard genuinely unpaid older charges every time, which is a different bug.

---

## D-3: Where the rollup is computed

**Decision**: server-side, in `CreditPaymentAttribution._calculate()`. `as_dict` gains a
`rollup` key holding either `None` or a dict with `count`, `start_date`, `end_date`,
`outstanding` and `attributed`. `periods` holds only the periods rendered individually.

**Rationale**:

- The amounts are `Decimal`. Summing them server-side keeps the arithmetic exact; summing
  them in JavaScript would run them through IEEE-754 doubles, and FR-014 requires the
  rows to add up to the totals line exactly. This is the kind of arithmetic the
  constitution's *Financial correctness* constraint is about.
- It makes the cap unit-testable in Python against pinned numbers, rather than only
  through Selenium.
- `jsonify` already serialises `Decimal` and `date` through `MagicJSONEncoder`, so the
  new key needs no serialisation work.

**Alternatives considered**:

- *Slice and sum in `transModalCreditPaymentInfoHtml()`.* Rejected for the float
  arithmetic above, and because it would leave the JSON payload as large as it is today —
  a 200-element array serialised on every keystroke of the amount field.
- *Paginate the endpoint.* Rejected as far more machinery than a modal panel warrants.

---

## D-4: The cap constant

**Decision**: `CREDIT_PAYMENT_MAX_PERIODS = 6`, a module-level constant in
`biweeklybudget/credit_payment.py`. Not a setting.

**Rationale**: six biweekly periods is about three months — enough to show a card carried
across a few cycles, few enough to fit a modal. FR-010 requires a single named constant.
Making it a setting would add a configuration surface, documentation, and a test matrix
for something no one has asked to tune; the constitution's guidance is against that.
If it ever needs to be configurable, promoting a module constant to a setting is a small
change.

---

## D-5: Impact on the existing test suite

**Decision**: keep every existing assertion in
`biweeklybudget/tests/acceptance/test_credit_payment.py` exactly as it is, and make them
valid again by adding one transaction to the fixture: an *anchor* payment dated
2017-04-10, in the first pay period (2017-04-07 .. 2017-04-20), added in the same step
that already adds the 2017-05-06 payment.

**Working**. Pay periods start 2017-04-07, so they run 04-07, 04-21, 05-05, 05-19. The
fixture's charges are 400.00 on 2017-04-25 and 150.00 on 2017-05-08.

| Test | Anchor | Derived begin | Effect |
|------|--------|---------------|--------|
| `test_03` .. `test_05` | none yet — these run before any payment exists | falls back to the configured 2017-01-01 (FR-004) | unchanged |
| `test_06_prior_payment_reduces_unpaid` | 2017-04-10 | 2017-04-21 | both charges still inside the window; the 2017-05-06 payment is still inside it and still settles the closed period. Unpaid 150.00 — unchanged |
| `test_07_editing_excludes_self` | 2017-04-10 (the edited transaction is the 05-06 one, not the anchor) | 2017-04-21 | unpaid 550.00 — unchanged |
| `test_09_charges_after_payment_date_not_attributed` | 2017-04-10, on or before the 2017-05-07 evaluation date | 2017-04-21 | only the 400.00 charge is on or before 2017-05-07. Unpaid 400.00, excess 150.00 — unchanged |
| `test_10_charges_before_begin_date_not_counted` | 2017-04-10 | `max(2017-05-01, 2017-04-21)` = 2017-05-01 | the configured floor wins, as it must (FR-007). Unpaid 150.00 — unchanged |

Without the anchor the derived bound would be 2017-05-19 — the period after the one
holding the 2017-05-06 payment — which is past the end of the fixture's data, and tests
06, 07, 09 and 10 would all collapse to asserting zeroes. That would be a much weaker
suite, and `test_10` in particular would stop testing anything about the floor.

**Rationale**: the existing tests pin behaviour the spec does not change — oldest-first
attribution, the floor, `exclude_txn_id`, the payment-date upper bound. Their numbers are
still the right answers; what changed is that the window now needs an anchor before it
behaves as those tests assume. Adding the anchor keeps them honest instead of rewriting
them to whatever the new code happens to emit, and `test_10` gains a second meaning for
free: it is now also the test that the configured floor beats a derived bound.

**Additional coverage required** (new, not adaptations):

- The derived bound with no configured floor in the way — the Example A shape.
- No designated payment at all: the configured begin date stands (FR-004).
- The anchoring payment is not also counted as a prior payment (FR-005a) — the
  double-count this design exists to avoid.
- `exclude_txn_id` naming the anchor: it still anchors (FR-005).
- Back-dating: a payment dated before every designated payment gets the configured
  begin date (FR-003).
- Derived bound later than the payment date — a second payment inside the anchor's own
  period. The window is empty, the panel reports no unpaid charges, and the payment is
  entirely excess. This is a real consequence of period-aligning the bound and is pinned
  rather than papered over.
- The cap: the rollup row's count, date range, and both summed amounts, and that
  individual rows plus rollup equal the totals (FR-014).

**Alternatives considered**: patching `CREDIT_PAYMENT_BEGIN_DATE` per test so the old
numbers survive. Rejected — it would test a window the feature no longer produces, and
the constitution forbids tests written to pass.

---

## D-6: Rendering the summary row

**Decision**: one `<tr>` prepended to the table body, carrying a `text-muted` class, with
the period cell reading `N older periods (YYYY-MM-DD – YYYY-MM-DD)` and the status cell
reading `rolled up`. When its attributed amount is non-zero the row also carries
`font-weight: 700` so the covered figure stands out (FR-015). Row id
`credit_payment_rollup` for the acceptance tests to find.

**Rationale**: follows the existing jQuery-built table in
`transModalCreditPaymentInfoHtml()` exactly — same construction style, same Bootstrap 3
classes, no new frontend machinery, which is what the constitution's *Stack* constraint
requires. The existing rows already carry no ids, so the table id plus a row id is enough
for Selenium.

**Alternatives considered**: a `<tfoot>` (wrong — the summary stands for the *oldest*
periods, so chronological order puts it first); an expand/collapse control (more
machinery, and the summary already states everything the rows would).

---

## D-7: Documentation surfaces

**Decision**: four places, per FR-018 to FR-020.

1. `docs/source/app_usage.rst`, the *What the payment panel tells you* section — the
   upgrade consequence and the self-healing window, in prose.
2. `biweeklybudget/settings.py`, the `CREDIT_PAYMENT_BEGIN_DATE` docstring — its new role
   as a floor beneath a derived bound.
3. `biweeklybudget/credit_payment.py`, the `CreditPaymentAttribution` class docstring —
   the algorithm's step 1 is now wrong as written and must describe the derivation.
4. `CHANGES.rst`, under `Unreleased` — one bullet, concise, per constitution Principle VI.

**Note**: per the project memory, a `CHANGES.rst` link to a docs anchor added in the same
change breaks `tox -e docs` linkcheck. The changelog entry names the documentation
section in prose rather than linking to it.
