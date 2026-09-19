# Quickstart: Verifying the Credit Payment Panel Window

**Feature**: Credit Payment Panel Window
**Spec**: [spec.md](./spec.md) · **Contract**: [contracts/credit-payment-info.md](./contracts/credit-payment-info.md)

How to prove this works, from the cheapest check to the one that looks at the real panel.

## Prerequisites

Per `CLAUDE.md` and the project memory:

```bash
source venv/bin/activate          # the MAIN checkout's venv; worktrees have none
export TOXINIDIR=$(pwd)
export BIWEEKLYBUDGET_LOG_FILE=/tmp/bwb-test.log && touch "$BIWEEKLYBUDGET_LOG_FILE"
```

Acceptance tests need the test MariaDB container from `CLAUDE.md` ("Test Database Setup
for Development") and drop/reload the database — **never point them at a real one**.

## 1. Unit tests — the pure pieces

```bash
pytest biweeklybudget/tests/unit/test_credit_payment.py -v
```

Covers `_consume()` (unchanged, oldest-first) and the rollup split: that at most six
periods survive individually, that the summary carries the right count, date range and
both sums, and that nothing is collapsed at exactly six.

## 2. Acceptance tests — the window against a real database

```bash
tox -e acceptance -- -k "TestCreditPaymentAttribution" \
  2>&1 > /tmp/claude-scratch/credit-payment.txt
```

Redirect to a file rather than piping to `tail`; the full output is needed when something
fails.

What must hold:

- **Derived bound** — with one payment designated toward a card in the period
  2017-04-07 .. 2017-04-20, the window starts 2017-04-21 and charges before it are gone.
- **No double-count** — that anchoring payment is *not* also subtracted as a prior
  payment (spec FR-005a). This is the invariant the whole boundary design exists for.
- **The floor wins** — a configured begin date later than the derived bound is used.
- **No anchor** — a card with no designated payment behaves exactly as it does today.
- **Back-dating** — a payment dated before every designated payment gets the configured
  begin date.
- **Empty window** — a second payment inside the anchor's own period yields no periods,
  zero unpaid, and the whole amount as excess.

## 3. Acceptance tests — the rendered panel

```bash
tox -e acceptance -- -k "TestTransCreditPaymentPanel" \
  2>&1 > /tmp/claude-scratch/credit-panel.txt
```

Drives the Add New Transaction modal in a browser: enter an amount, pick the card under
**Credit Card Payment For**, and read the panel. Asserts the table holds at most six
period rows, that `#credit_payment_rollup` appears only when periods were collapsed, that
it states the count and date range, and that the rendered amounts sum to
`#credit_payment_totals`.

## 4. By hand, against the real application

```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

Open http://127.0.0.1:5000/transactions, click **Add Transaction**, enter an amount, and
choose a credit card under **Credit Card Payment For**.

Expected, on a database with history:

- Before any payment has been designated toward that card: the panel counts from the
  configured begin date — the old, noisy behaviour, once.
- Save that payment, then start another for the same card: the panel now counts from the
  period after the first payment's, the table is a handful of rows, and the unpaid total
  resembles the card's balance rather than a decade of spending.
- The panel states the date it is counting from.

## 5. The gates

```bash
tox -e py314          # unit
tox -e acceptance     # full acceptance suite
tox -e docs           # must build clean; M3 touches app_usage.rst
tox -e migrations     # unaffected — no schema change — run as a regression check
```

A suite that times out has not passed (Constitution II): raise the timeout and re-run.

Known-flaky tests per project memory — reconcile drag/unignore, fuel log search, Plaid
"Uncheck All" — are unrelated to this change; re-run them in isolation before attributing
a failure here.
