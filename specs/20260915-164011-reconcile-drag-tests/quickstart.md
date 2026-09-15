# Quickstart: Validate the Restored Reconcile Drag-and-Drop Tests

## Prerequisites

- A throwaway MariaDB container. Never point acceptance tests at a real database.

  ```bash
  docker run -d --name budgettest -p 13306:3306 \
    --env MYSQL_ROOT_PASSWORD=dbroot --env MYSQL_ROOT_HOST='%' mariadb:10.4.7
  ```

- The database environment variables from `CLAUDE.md` ("Test Database Setup for
  Development"), then `python dev/setup_test_db.py`.
- Chrome/Chromium with a matching ChromeDriver on `PATH`.
- A fresh `acceptance` tox env needs its log file:
  `touch .tox/acceptance/liveserver.log`.

## 1. The two classes run and pass (US1, FR-001, FR-002, SC-001)

```bash
tox -e acceptance -- biweeklybudget/tests/acceptance/flaskapp/views/test_reconcile.py \
  -k "TestDragAndDropReconcile or TestUIReconcileMulti" > out.txt 2>&1
```

Expected: `18 passed` (12 fixture-loading steps plus the 6 real tests), nothing skipped
and `acceptance: OK`. Before this change the same command reported both classes as
skipped.

## 2. They are stable (SC-002)

Repeat step 1 five times in a row. Every run must report `18 passed`.

## 3. Cleanup is complete (US2, FR-004, FR-005)

```bash
grep -n "pytest.mark.skip\|2022-10-22\|# DEBUG" \
  biweeklybudget/tests/acceptance/flaskapp/views/test_reconcile.py
```

Expected: no output. `ReconcileHelper.drag_ofx_to_trans` documents why each drag uses a
new action chain.

## 4. Nothing else regressed (SC-003, constitution Principle II)

```bash
tox -e py314      > unit.txt 2>&1        # unit suite + pycodestyle + pyflakes
tox -e acceptance > acceptance.txt 2>&1  # whole acceptance suite (~17 min)
```

Expected: both environments report `OK`. The acceptance summary shows 18 fewer
skipped and 18 more passed than on `master`: a class-level skip marks all 9 tests in
each class, fixture steps included.
