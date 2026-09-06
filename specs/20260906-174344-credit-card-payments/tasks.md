---

description: "Task list for Special Handling of Credit Card Payments"
---

# Tasks: Special Handling of Credit Card Payments

**Input**: Design documents from `specs/20260906-174344-credit-card-payments/`

**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/http-api.md](./contracts/http-api.md), [quickstart.md](./quickstart.md)

**Tests**: Included and mandatory. Issue #210's own scope calls for "unit and acceptance test coverage", and constitution Principle II (NON-NEGOTIABLE) makes a green suite a condition of completion. Constraint: changes to pay-period arithmetic must ship with tests that pin the expected numbers, so every arithmetic test below states the numbers it pins.

## Format: `[ID] [P?] [Story] Description`

- **[ID]**: `M.T` — milestone and task. Commit messages use `Credit Card Payments - M.T` per the constitution's Development Workflow.
- **[P]**: Can run in parallel — different files, no dependency on an incomplete task.
- **[Story]**: `[US1]` no-budget-impact designation, `[US2]` credit card payment, `[US3]` attribution and warnings. Infrastructure and polish tasks carry no story label.

## Path Conventions

Single Python package at the repository root: `biweeklybudget/`, with the Flask application
nested at `biweeklybudget/flaskapp/` and tests at `biweeklybudget/tests/`. All paths below
are repository-relative.

---

## Milestone 1: Schema, Model, and Settings Foundation

**Purpose**: The two columns, the derived property, the migration, and the setting. Blocks
every other milestone.

**⚠️ ORDER IS LOAD-BEARING**: M1.1 must complete before M1.3. Editing the model before the
test database is at the current head makes Alembic autogenerate see no difference and
silently emit an empty migration (CLAUDE.md, research.md D-11).

- [X] M1.1 Stand up the MariaDB test container and bring the database to the current Alembic head **before any model edit**: run the `docker run --name budgettest` command and export the environment block from [quickstart.md](./quickstart.md), then `python dev/setup_test_db.py` and `initdb`. Confirm `alembic -c biweeklybudget/alembic/alembic.ini current` reports `a1b2c3d4e5f6`. No repository files change. *(Prerequisite for M1.3; research.md D-11)*

- [X] M1.2 [P] Add the `CREDIT_PAYMENT_BEGIN_DATE` setting in `biweeklybudget/settings.py`: declare it as `None` beside `RECONCILE_BEGIN_DATE` with a docstring comment in the file's existing `#:` style, add it to `_DATE_VARS` (not `_REQUIRED_VARS`), and after the `_REQUIRED_VARS` check resolve `None` to `RECONCILE_BEGIN_DATE`. *(FR-023; research.md D-8)*

- [X] M1.3 Add the two columns to `Transaction` in `biweeklybudget/models/transaction.py`: `no_budget_impact = Column(Boolean, default=False, nullable=False)` and `credit_payment_acct_id = Column(Integer, ForeignKey('accounts.id'))`, with `#:`-style docstring comments matching the file's convention. Import `Boolean` and `or_` from `sqlalchemy`. *(FR-001, FR-009; data-model.md)*

- [X] M1.4 **Disambiguate the account relationships** in `biweeklybudget/models/transaction.py`: add `foreign_keys=[account_id]` to the existing `account` relationship and add the new `credit_payment_acct` relationship with `foreign_keys=[credit_payment_acct_id]` and `backref="credit_payments"`. `transactions` now holds two foreign keys to `accounts.id`; without this, mapper configuration raises `AmbiguousForeignKeysError` on import and every code path in the application fails. *(research.md D-2 — the single highest-risk change in the feature)*

- [X] M1.5 Add the `is_excluded_from_budget` hybrid property and its `.expression` to `biweeklybudget/models/transaction.py`, returning `no_budget_impact or credit_payment_acct_id is not None` / `or_(cls.no_budget_impact.is_(True), cls.credit_payment_acct_id.isnot(None))`, and add `'is_excluded_from_budget'` to `_dict_properties`. Follow the existing `actual_amount` hybrid for the pattern. *(FR-011, FR-014; research.md D-3)*

- [X] M1.6 Verify the mapper configures before going further: run `python -c "import biweeklybudget.models"` and a short unit-test subset. If this fails, M1.4 is wrong — fix it here, not later. *(Guards research.md D-2)*

- [X] M1.7 Generate the Alembic migration with `alembic -c biweeklybudget/alembic/alembic.ini revision --autogenerate -m "add Transaction no_budget_impact and credit_payment_acct_id"`, then hand-finish the generated file in `biweeklybudget/alembic/versions/`: confirm `down_revision = 'a1b2c3d4e5f6'`, confirm the column definitions match the model exactly, and make `downgrade()` **drop the foreign key constraint `fk_transactions_credit_payment_acct_id_accounts` before dropping `credit_payment_acct_id`** — MySQL refuses to drop a column a constraint still references. *(FR-024, SC-007; research.md D-11)*

- [X] M1.8 Test the migration in both directions by hand: `upgrade head`, `downgrade -1`, `upgrade head`. Both directions must complete without error. *(SC-007)*

- [X] M1.9 [P] Add `biweeklybudget/tests/migrations/test_migration_<rev>.py` following the `test_migration_d01774fa3ae3.py` pattern: `verify_before` asserts `no_budget_impact` and `credit_payment_acct_id` are absent from the `transactions` columns, `verify_after` asserts both are present. The harness exercises the reverse migration back through `verify_before`. *(FR-024, SC-007)*

- [X] M1.10 [P] Add `CREDIT_PAYMENT_BEGIN_DATE` to `biweeklybudget/settings_example.py` beside `RECONCILE_BEGIN_DATE`, documented, and to `biweeklybudget/tests/fixtures/test_settings.py` as `date(2017, 1, 1)` to match its `RECONCILE_BEGIN_DATE`. *(FR-023)*

- [X] M1.11 [P] Add unit tests in `biweeklybudget/tests/unit/models/` for `is_excluded_from_budget`: false when neither field is set; true when `no_budget_impact` is true; true when `credit_payment_acct_id` is set and `no_budget_impact` is false; still true when both are set; and false again once `credit_payment_acct_id` is cleared while `no_budget_impact` remains false. That last case is FR-014 and is the reason the property is derived rather than stored. *(FR-011, FR-014)*

- [X] M1.12 **Gate**: run `tox -e py314` and `tox -e migrations` to completion, plus the pycodestyle/pyflakes run. Redirect output to a scratchpad file rather than piping to `tail`. A timed-out suite has not passed — raise both the pytest timeout and the invoking timeout and re-run. *(Constitution II, III)*

- [X] M1.13 Commit as `Credit Card Payments - M1.x`, covering M1.2 through M1.11.

**Checkpoint**: schema and model are in place; nothing reads the new fields yet, and every existing total is unchanged (SC-006).

---

## Milestone 2: Exclusion From Budget Arithmetic

**Purpose**: Make the designations mean something. This milestone alone delivers User
Story 1 end to end at the data layer, and makes User Story 2's arithmetic correct.

**Depends on**: M1 complete.

- [X] M2.1 [US1] Carry the flag into the pay period transaction dicts in `biweeklybudget/biweeklypayperiod.py`: add `'no_budget_impact': t.is_excluded_from_budget` to the dict built by `_dict_for_trans()`, and `'no_budget_impact': False` in `_dict_for_sched_trans()`. Update both methods' docstrings, which enumerate the dict's keys. *(FR-002, FR-007; research.md D-4)*

- [X] M2.2 [US1] Skip excluded transactions in `_make_budget_sums()` in `biweeklybudget/biweeklypayperiod.py`, before any `allocated` / `spent` / `trans_total` accumulation and after the `ScheduledTransaction` branch. Do **not** filter `_transactions()`: `transactions_list` also renders the pay period page, and FR-005 requires excluded transactions to stay visible there. *(FR-002, FR-003; research.md D-4)*

- [X] M2.3 [US1] Exclude them from `Account.unreconciled_sum` in `biweeklybudget/models/account.py` by skipping transactions where `is_excluded_from_budget` is true. Leave the `unreconciled` query property and `Transaction.unreconciled()` untouched, so the reconcile view still offers them. Add a comment pointing at the trade-off recorded in research.md D-5. *(FR-004, FR-005; research.md D-5)*

- [X] M2.4 [P] [US1] Add unit tests in `biweeklybudget/tests/unit/test_biweeklypayperiod.py` pinning the exclusion: a period whose "Groceries" budget shows **$100** spent still shows **$100** after a **$40** excluded transaction against Groceries is added to the same period, and `overall_sums` `allocated` / `spent` / `remaining` are byte-identical to the pre-insertion values. Assert separately that the excluded transaction **is** present in `transactions_list` with `no_budget_impact` true. *(US1 scenario 1; FR-002, FR-003, FR-005)*

- [X] M2.5 [P] [US1] Add unit tests for split and budgeted-amount cases in `biweeklybudget/tests/unit/test_biweeklypayperiod.py`: an excluded transaction split across three budgets contributes to none of them; an excluded transaction carrying a non-None `budgeted_amount` and a `planned_budget_id` contributes neither `spent` nor `allocated`. *(Edge cases; FR-002)*

- [X] M2.6 [P] [US2] Add the **cross-period payoff** unit test in `biweeklybudget/tests/unit/test_biweeklypayperiod.py`, pinning the numbers from US2 scenario 1: charges of **$500** on credit account CreditOne in period N; charges of **$300** on CreditOne in period N+1; a **$500** payment recorded on a bank account dated in N+1 with `credit_payment_acct_id` set to CreditOne. Assert period N+1's spent total reflects **$300**, not **$800**; assert period N is unchanged at **$500**. This is the defect the whole feature exists to fix. *(US2 scenario 1; FR-012, FR-013, SC-001)*

- [X] M2.7 [P] [US2] Add the **same-period payoff** unit test in `biweeklybudget/tests/unit/test_biweeklypayperiod.py`: a **$200** charge on CreditOne and a **$200** payment toward CreditOne in the same pay period; assert the period's spent total counts **$200** once, not **$400**. *(US2 scenario 2; FR-012, SC-002)*

- [X] M2.8 [P] [US2] Add a unit test asserting the rejected netting behaviour is absent: with charges `C(n+1) = $300` in period N+1 and a payment `P = $500` in N+1, the period total must be **$300** and must **not** be `$500` (which is what netting would produce). Name the test so the intent survives — this is a regression guard against reintroducing the approach the spec rejects. *(FR-013)*

- [X] M2.9 [P] [US1] Add unit tests for `Account.unreconciled_sum` in `biweeklybudget/tests/unit/models/`: an account whose unreconciled sum is **$250** still reports **$250** after a **$40** excluded transaction is added, while `Transaction.unreconciled()` still returns that transaction. *(US1 scenarios 2, 3; FR-004, FR-005)*

- [X] M2.10 **Gate**: run `tox -e py314` to completion plus lint, output to a scratchpad file. *(Constitution II)*

- [X] M2.11 Commit as `Credit Card Payments - M2.x`.

**Checkpoint**: SC-001 and SC-002 hold at the data layer. User Story 1 is testable end to end via the model; nothing is exposed in the UI yet.

---

## Milestone 3: Transaction Form and Transaction Lists

**Purpose**: Expose both designations in the UI, persist them, and mark excluded
transactions where transactions are listed. Completes User Stories 1 and 2.

**Depends on**: M2 complete.

- [X] M3.1 [US2] Build the credit-account list in `biweeklybudget/flaskapp/views/transactions.py`: in both `TransactionsView.get()` and `OneTransactionView.get()`, add `credit_accts = {a.name: a.id for a in ...}` filtered to `AcctType.Credit` and `is_active`, passed to `render_template`. Restricting server-side is what makes FR-010 and FR-015 true by construction. *(FR-010)*

- [X] M3.2 [US2] Render `credit_acct_names_to_id` as a JavaScript variable in `biweeklybudget/flaskapp/templates/transactions.html`, alongside the existing `acct_names_to_id`. *(FR-010)*

- [X] M3.3 [US1] [US2] Accept and persist both fields in `TransactionFormHandler` in `biweeklybudget/flaskapp/views/transactions.py`: read `no_budget_impact` (checkbox, absent means false) and `credit_payment_acct` (`"None"` means not a payment) in `submit()`, writing `trans.no_budget_impact` and `trans.credit_payment_acct_id`. Clearing the select to `"None"` must write `None`, which is what makes FR-014 work. *(FR-008, FR-009, FR-014; contracts/http-api.md)*

- [X] M3.4 [US2] Add the blocking validations in `TransactionFormHandler.validate()` in `biweeklybudget/flaskapp/views/transactions.py`: `credit_payment_acct` must name an existing account, and that account's `acct_type` must be `AcctType.Credit`. Messages per contracts/http-api.md. The form is a reachable endpoint, so this cannot rely on the select being restricted. *(FR-015)*

- [X] M3.5 [P] [US1] [US2] Add the new fields to `TransactionsAjax.get()`'s `table.add_data()` call in `biweeklybudget/flaskapp/views/transactions.py`: `no_budget_impact` (the derived `is_excluded_from_budget`), `credit_payment_acct_id`, and `credit_payment_acct_name`. *(FR-007; contracts/http-api.md)*

- [X] M3.6 [P] [US1] [US2] Add `credit_payment_acct_name` and confirm `no_budget_impact`, `credit_payment_acct_id`, and `is_excluded_from_budget` are present in `OneTransactionAjax.get()`'s response in `biweeklybudget/flaskapp/views/transactions.py`. The checkbox binds to the **raw** `no_budget_impact` so it reflects the user's own choice, not the derived value. *(FR-008; contracts/http-api.md)*

- [X] M3.7 [US1] [US2] Add the two form controls to `transModalDivForm()` in `biweeklybudget/flaskapp/static/js/transactions_modal.js`: `.addCheckbox('trans_frm_no_budget_impact', 'no_budget_impact', 'No Budget Impact?', false)` and `.addLabelToValueSelect('trans_frm_credit_payment_acct', 'credit_payment_acct', 'Credit Card Payment For', credit_acct_names_to_id, 'None', true)`. `addNone=true` supplies the explicit default choice FR-010 requires. *(FR-008, FR-010; research.md D-9)*

- [X] M3.8 [US1] [US2] Populate both controls on edit in `transModalDivFillAndShow()` in `biweeklybudget/flaskapp/static/js/transactions_modal.js`, appending the option for a credit account that is no longer active so an existing payment still displays the account it points at. *(FR-008; edge case)*

- [X] M3.9 [P] [US1] Mark excluded transactions in the `/transactions` DataTable in `biweeklybudget/flaskapp/static/js/transactions.js`, rendering a marker on the description column from the row's `no_budget_impact`, and naming the credit account when there is one. Follow the table's existing `<em>`-parenthetical convention. *(FR-007)*

- [X] M3.10 [P] [US1] Mark excluded transactions in the pay period transaction table in `biweeklybudget/flaskapp/templates/payperiod.html`, using `t['no_budget_impact']` from the dict M2.1 populates, in the same style as the existing `<em>(sched)</em>` marker. *(FR-007)*

- [X] M3.11 [P] [US1] [US2] Add acceptance tests in `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` for the modal: both controls present with correct defaults; the select offers credit accounts only and no others; creating a transaction with the checkbox set persists `no_budget_impact` true; creating one with a credit account set persists `credit_payment_acct_id` and leaves `no_budget_impact` false while `is_excluded_from_budget` is true; reopening shows both values; clearing the select restores ordinary budget impact. Build test data in a `test_00_*` method via `testdb`, following `TestTransModalDoesNotShowInactiveBudgets`. Do **not** add rows to `sampledata.py`. *(US1 scenario 4, US2 scenarios 3-5; FR-008, FR-010, FR-014; research.md D-10)*

- [X] M3.12 [P] [US2] Add an acceptance test in `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` posting `credit_payment_acct` naming a **non-credit** account directly to `/forms/transaction`, asserting the blocking validation error. *(FR-015)*

- [X] M3.13 [P] [US1] Add an acceptance test in `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` asserting an excluded transaction appears in the pay period's transaction table, is marked, and does not move any total on the page. *(US1 scenarios 1, 3; FR-005, FR-007)*

- [X] M3.14 **Gate**: run `tox -e py314` and `tox -e acceptance` to completion plus lint, output to scratchpad files. *(Constitution II)*

- [X] M3.15 Commit as `Credit Card Payments - M3.x`.

**Checkpoint**: User Stories 1 and 2 are complete and usable. SC-003 holds — recording a payment takes one entry and creates no offsetting transaction.

---

## Milestone 4: Payment Attribution and Warnings

**Purpose**: User Story 3 — the part that prevents mistakes rather than merely making them
representable.

**Depends on**: M3 complete.

- [X] M4.1 [US3] Create `biweeklybudget/credit_payment.py` with the AGPL v3 header copied from an existing module, holding `CreditPaymentAttribution(db, account, amount, payment_date, exclude_txn_id=None, payer_account_id=None)`. Implement the algorithm exactly as specified in research.md D-7: window bounded below by `settings.CREDIT_PAYMENT_BEGIN_DATE` and above by the payment date; charges grouped by pay period oldest first; prior payments toward the account consumed against those charges oldest first, excluding `exclude_txn_id`; then the candidate amount attributed against the remainders; excess is what is left. All arithmetic in `Decimal`. Expose the attributes listed in data-model.md. *(FR-016, FR-017, FR-018, FR-019, FR-020, FR-022, FR-023)*

- [X] M4.2 [US3] Add `CreditPaymentInfoAjax` to `biweeklybudget/flaskapp/views/transactions.py` serving `GET /ajax/credit-payment-info`, with the parameters, response shape, and 400 conditions in contracts/http-api.md. Read-only, no side effects, safe to call on every keystroke — so it must read the account's transactions once rather than per pay period. *(contracts/http-api.md; FR-016, FR-020)*

- [X] M4.3 [US3] Add the info panel to the modal in `biweeklybudget/flaskapp/static/js/transactions_modal.js`: an `.addHTML('<div id="trans_frm_credit_payment_info"></div>')` element, hidden while no credit account is selected, refreshed from the endpoint when the credit account select, the amount input, or the date input changes. It renders the per-period breakdown and any warnings and **must never disable the Save button**. *(FR-016, FR-021; research.md D-9)*

- [X] M4.4 [P] [US3] Add unit tests for the attribution arithmetic in `biweeklybudget/tests/unit/test_credit_payment.py`, pinning US3's numbers: with **$400** unpaid in a closed period and **$150** in the currently-open period, a payment of **$400** attributes $400 closed / $0 open with no warning; **$500** attributes $400 closed / $100 open with no warning; **$600** attributes $550 total and warns of a **$50.00** excess against **$550** unpaid. *(US3 scenarios 1-3; FR-016, FR-017, FR-020, SC-004, SC-005)*

- [X] M4.5 [P] [US3] Add unit tests in `biweeklybudget/tests/unit/test_credit_payment.py` for multi-period attribution: unpaid charges spanning three closed pay periods, a payment covering all three, asserting the per-period attributed amounts are correct and ordered oldest first. *(US3 scenario 4; FR-017, SC-005)*

- [X] M4.6 [P] [US3] Add unit tests in `biweeklybudget/tests/unit/test_credit_payment.py` for the boundaries: charges dated before `CREDIT_PAYMENT_BEGIN_DATE` are not counted as unpaid; charges dated after the payment date are not attributed to it; prior payments are subtracted from the unpaid total; and when `exclude_txn_id` names the payment being edited, that payment is **not** counted against itself. *(FR-018, FR-019; edge case "charges predating the tracked window")*

- [X] M4.7 [P] [US3] Add unit tests in `biweeklybudget/tests/unit/test_credit_payment.py` for the remaining warning and edge cases: a card with no recorded charges at all warns and attributes zero; `pays_itself` is true when `payer_account_id` equals the paid account; a negative payment amount (a refund flowing back from the card) is handled with its sign. *(FR-022; edge cases)*

- [X] M4.8 [P] [US3] Add acceptance tests in `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py`: entering **400**, **500**, and **600** against a card with $400 closed / $150 open produces the three panel states above, and the Save button stays enabled while the $50.00 excess warning is showing; saving with the warning showing succeeds. Data built via `testdb` in a `test_00_*` method. *(US3 scenarios 1-3, 5; FR-021, SC-004)*

- [X] M4.9 [P] [US3] Add an acceptance test in `biweeklybudget/tests/acceptance/flaskapp/views/test_transactions.py` reopening a saved payment for editing and asserting the panel does not count that payment against itself. *(US3 scenario 6; FR-019)*

- [X] M4.10 **Gate**: run `tox -e py314` and `tox -e acceptance` to completion plus lint, output to scratchpad files. *(Constitution II)*

- [X] M4.11 Commit as `Credit Card Payments - M4.x`.

**Checkpoint**: all three user stories complete. SC-004 and SC-005 hold.

---

## Milestone 5: Documentation, Version, Changelog, and the Full Gate

**Purpose**: Finish the change as the constitution defines finished.

**Depends on**: M4 complete.

- [X] M5.1 [P] Document the credit card payment workflow in `docs/source/app_usage.rst`: designate the payment toward the card, enter nothing else, zero budget impact in every pay period, and what the attribution panel and the over-payment warning mean. Document the general no-budget-impact designation and when to use it — statement credits, cash-back redemptions applied as a statement credit, manual balance-reconcile adjustments. A search of `docs/` and `README.rst` found no existing description of the pseudo-transaction workaround, so FR-025's "replace" reduces to writing the new workflow; state that finding in the commit message rather than leaving it implicit. *(FR-025)*

- [X] M5.2 [P] Document `CREDIT_PAYMENT_BEGIN_DATE` where the other settings are documented, covering what the window is for and why moving it forward is the operator's lever once historical payments have been designated. *(FR-023, FR-025)*

- [X] M5.3 [P] Add `docs/source/biweeklybudget.credit_payment.rst` following the existing per-module autodoc pages, and add it to the toctree in `docs/source/biweeklybudget.rst`. *(Constitution IV)*

- [X] M5.4 [P] Add the `CHANGES.rst` entry for 1.8.0 in the existing format, referencing issues #210 and #319, and stating plainly that the netting approach in #210's original proposal was rejected and why. *(Constitution VI)*

- [X] M5.5 [P] Bump `VERSION` in `biweeklybudget/version.py` from `1.7.0` to `1.8.0` — backwards-compatible new functionality. *(Constitution VI)*

- [X] M5.6 **Full gate**: run `tox -e py314`, `tox -e acceptance`, `tox -e migrations`, and `tox -e docs` to completion, plus lint. Redirect each to its own scratchpad file. All four must pass. A suite that times out has not passed: raise the pytest timeout and the invoking timeout and run it again. Narrowing to a passing subset, marking failures expected, or reporting a timed-out run as green all violate Principle II. *(Constitution II, III, IV; SC-008)*

- [X] M5.7 Walk the [quickstart.md](./quickstart.md) scenarios against a running application to confirm the delivered behaviour matches the spec's acceptance scenarios, not just the tests. *(SC-001 through SC-005)*

- [ ] M5.8 Commit as `Credit Card Payments - M5.x`, push the branch to `origin`, and open a pull request describing the change, the rejected netting approach, the Constitution Check result, and the `Account.unreconciled_sum` trade-off recorded in research.md D-5 so it is visible to review.

- [ ] M5.9 Tear down the test container: `docker stop budgettest && docker rm budgettest`.

---

## Dependencies & Execution Order

### Milestone dependencies

```text
M1 (schema, model, settings)      -- blocks everything
     |
M2 (exclusion arithmetic)         -- delivers US1 at the data layer, makes US2 correct
     |
M3 (form, AJAX, lists)            -- completes US1 and US2
     |
M4 (attribution, warnings)        -- delivers US3
     |
M5 (docs, version, full gate)
```

The milestones are strictly sequential. This differs from the template's parallel-story
model for a concrete reason: all three user stories are layers on one `Transaction` model
and one pay period calculation, so they share files rather than dividing along them. US2's
correctness is produced by M2, which is also US1's implementation; US3 reads the same data
M3 persists.

### Within a milestone

- M1.1 strictly before M1.3 (autogenerate needs the database at head first).
- M1.3 → M1.4 → M1.5 → M1.6 → M1.7 in order; each depends on the previous.
- M2.1 before M2.2 (the filter reads the key the dict task adds).
- M3.1 before M3.2 before M3.7 (view builds the list, template exposes it, JS consumes it).
- M4.1 before M4.2 before M4.3 (module, then endpoint, then panel).
- All `[P]` test tasks within a milestone touch different files and may run together.

### Parallel opportunities

- **M1**: M1.2, M1.9, M1.10, M1.11 are independent of one another.
- **M2**: M2.4 through M2.9 are all independent once M2.1–M2.3 land.
- **M3**: M3.5, M3.6, M3.9, M3.10 are independent; M3.11–M3.13 are independent test files.
- **M4**: M4.4 through M4.9 are independent once M4.1–M4.3 land.
- **M5**: M5.1 through M5.5 are all independent.

---

## Story coverage

| Story | Delivered by | Independently testable at |
|-------|--------------|---------------------------|
| US1 — no budget impact (P1) | M1, M2.1–M2.5, M2.9, M3.3, M3.7–M3.11, M3.13 | End of M2 at the data layer; end of M3 through the UI |
| US2 — credit card payment (P1) | M1, M2.6–M2.8, M3.1–M3.8, M3.11, M3.12 | End of M2 at the data layer; end of M3 through the UI |
| US3 — attribution and warnings (P2) | M4 in full | End of M4 |

### Requirement coverage

| Requirement | Tasks |
|-------------|-------|
| FR-001, FR-009 | M1.3 |
| FR-002, FR-003 | M2.1, M2.2, M2.4, M2.5 |
| FR-004 | M2.3, M2.9 |
| FR-005 | M2.2, M2.3, M2.4, M2.9, M3.13 |
| FR-006 | unchanged existing validation; asserted in M3.11 |
| FR-007 | M2.1, M3.5, M3.9, M3.10, M3.13 |
| FR-008 | M3.3, M3.6, M3.7, M3.8, M3.11 |
| FR-010 | M3.1, M3.2, M3.7, M3.11 |
| FR-011 | M1.5, M1.11 |
| FR-012 | M2.6, M2.7 |
| FR-013 | M2.2, M2.8 |
| FR-014 | M1.5, M1.11, M3.3, M3.11 |
| FR-015 | M3.1, M3.4, M3.12 |
| FR-016, FR-017 | M4.1, M4.3, M4.4, M4.5, M4.8 |
| FR-018 | M4.1, M4.6 |
| FR-019 | M4.1, M4.6, M4.9 |
| FR-020 | M4.1, M4.4, M4.8 |
| FR-021 | M4.3, M4.8 |
| FR-022 | M4.1, M4.7 |
| FR-023 | M1.2, M1.10, M4.1, M5.2 |
| FR-024 | M1.7, M1.9 |
| FR-025 | M5.1, M5.2 |
| SC-001 | M2.6 |
| SC-002 | M2.7 |
| SC-003 | M3.3, M3.11 |
| SC-004 | M4.4, M4.8 |
| SC-005 | M4.4, M4.5 |
| SC-006 | M1.7, M1.8 |
| SC-007 | M1.7, M1.8, M1.9 |
| SC-008 | M5.6 |

---

## Notes

- `[P]` tasks touch different files and have no dependency on an incomplete task.
- Commit messages use `Credit Card Payments - M.T` per constitution Development Workflow step 4.
- Redirect test output to a scratchpad file rather than piping to `tail`, `head`, or `grep`, per CLAUDE.md, so the full output stays available for examination.
- Never point the acceptance suite at a real database; it drops and reloads (constitution, Test data safety).
- Do not extend `biweeklybudget/tests/fixtures/sampledata.py`; the acceptance suite addresses its rows by hard-coded id and asserts on totals derived from the whole fixture set (research.md D-10).
- The netting approach from #210's original proposal is not to be implemented under any circumstance; M2.8 is the regression guard.
