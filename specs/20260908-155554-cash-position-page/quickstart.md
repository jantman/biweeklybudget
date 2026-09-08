# Quickstart / Validation: Cash Position Page

**Feature**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

How to bring the feature up locally and prove it works. Commands are run from
the repository root with the virtualenv active.

```bash
source venv/bin/activate
```

---

## 1. Test database

Per `CLAUDE.md`. **Order matters**: `initdb` must run against the *current*
head before any model change, or Alembic autogenerate sees no diff and
silently writes an empty migration (constitution III).

```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' \
  mariadb:10.4.7

export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1 MYSQL_PORT=13306
export MYSQL_USER=root MYSQL_PASS=dbroot MYSQL_DBNAME=budgettest
export MYSQL_DBNAME_LEFT=alembicLeft MYSQL_DBNAME_RIGHT=alembicRight

python dev/setup_test_db.py
initdb    # <- before touching biweeklybudget/models/
```

Teardown: `docker stop budgettest && docker rm budgettest`

## 2. Migration round trip (M1)

```bash
alembic -c biweeklybudget/alembic/alembic.ini current      # expect f9df90273cdd
alembic -c biweeklybudget/alembic/alembic.ini revision --autogenerate \
    -m "add budget_accounts table"
alembic -c biweeklybudget/alembic/alembic.ini upgrade head
alembic -c biweeklybudget/alembic/alembic.ini downgrade -1
alembic -c biweeklybudget/alembic/alembic.ini upgrade head
```

**Expected**: the generated migration creates `budget_accounts` with a
composite primary key and two cascading foreign keys; both directions run
clean; `alembic current` returns to the new head.

```bash
tox -e migrations 2>&1 > /tmp/claude-1000/.../migrations.txt
```

**Expected**: green, including `alembic-verify` confirming head matches the
models — which it only does if `models/__init__.py` imports the new module.

## 3. The calculation (M2)

```bash
pytest biweeklybudget/tests/unit/test_cashposition.py -v
pytest biweeklybudget/tests/unit/flaskapp/test_notifications.py -v
```

**Expected**: new tests pass, and the pre-existing notification tests pass
**unchanged** — that is the parity check that the refactor preserved
behaviour.

The one assertion that matters most (FR-004):

```python
assert cp.uncommitted == (
    (cp.budget_account_ledger + cp.credit_balance)
    - (cp.standing_total + cp.pay_period_allocated_unspent + cp.unreconciled)
)
```

Scenarios that must be covered, because each is a way a plausible
implementation goes wrong:

| Scenario | Expectation |
|---|---|
| Credit account with a **positive** balance | raises `net_liquid` |
| Standing budget with a negative balance | raises `uncommitted` |
| Account with `balance is None` | contributes 0, `counted is False`, no exception |
| Account with `balance.ledger is None` | same |
| Empty database | every term `Decimal('0')`, no exception |
| Pay period with nothing in it | term 5 is 0, still present |

## 4. The page (M3)

```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

Open <http://127.0.0.1:5000/cash-position>.

**Expected**:

- Five terms and two subtotals in the order given in
  [contracts/cash-position-page.md](./contracts/cash-position-page.md).
- Each budget-funding account listed with ledger, unreconciled and projected
  balance, plus its as-of date.
- Each itemized table's total equals the waterfall term above it.
- Every aggregate line links to `/accounts`, `/reconcile`, `/budgets` or
  `/pay_period_for`.
- **The number at the bottom equals the discrepancy the banner reports.**
  Compare against the banner on `/` directly; this is the whole point of the
  page.
- "Cash Position" appears in the sidebar directly under "Home".

```bash
tox -e acceptance -- -k "cash_position or base_template" \
    2>&1 > /tmp/claude-1000/.../acceptance-m3.txt
```

## 5. Diagnostics and link editing (M4)

On `/budgets`, open a **standing** budget. **Expected**: a checkbox per active
budget-funding account, absent when the type is switched to Periodic. Tick
one, save, reopen — it is still ticked.

Back on `/cash-position`:

- The account you linked appears in a coverage group with that budget, showing
  both totals and the delta.
- A budget-funding account you linked to nothing is named under unlinked
  accounts, with the explanation that its balance sits in the uncommitted
  total.
- With no links configured at all, every budget-funding account is listed as
  unlinked and the waterfall is unaffected.
- With nothing to report, the all-clear message appears rather than an empty
  panel.

## 6. The full gate (M5)

Constitution II — every suite runs **to completion**. A timeout is not a pass;
raise the timeout and re-run.

```bash
tox 2>&1 > /tmp/claude-1000/.../full-suite.txt
```

Covers `py314`, `docs`, `jsdoc`, `screenshots`, `acceptance`, `docker`,
`migrations`, `plaid`. Redirect to a file rather than piping to `tail` so the
whole output can be examined (`CLAUDE.md`).

**Also verify**:

- `biweeklybudget/version.py` reads `1.12.0`.
- `CHANGES.rst` has the 1.12.0 entry.
- `docs/source/app_usage.rst` has the Cash Position section, cross-linked from
  the unallocated-funds section.
- Every new Python file carries the AGPL v3 header.
