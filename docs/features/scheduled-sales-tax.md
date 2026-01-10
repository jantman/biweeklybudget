# Scheduled Transaction Sales Tax

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

This application supports Scheduled Transactions which are displayed in the appropriate pay periods and can be converted to Transactions when they occur. Scheduled Transactions currently just have an Amount field, but Transactions have both an Amount and a Sales Tax. Our task is to add a Sales Tax field to Scheduled Transactions (in the database and in the add/edit form in the UI) and ensure that when a Transaction is made from a Scheduled Transaction (`schedToTransModal()` javascript in the UI) the sales tax is included if it was set to a non-zero amount. We will need to update all tests (both unit and acceptance) to validate this new functionality.

## Implementation Plan

### Background

- **ScheduledTransaction Model**: Located in `biweeklybudget/models/scheduled_transaction.py`
  - Currently has fields: id, amount, description, notes, account_id, budget_id, is_active, date, day_of_month, num_per_period
  - NO sales_tax field currently

- **Transaction Model**: Located in `biweeklybudget/models/transaction.py`
  - Already has `sales_tax = Column(Numeric(precision=10, scale=4), nullable=False, default=0.0)`
  - Added via migration `d01774fa3ae3_add_transaction_field_to_store_sales_.py`

- **Conversion Process**:
  - JavaScript: `schedToTransModal()` in `biweeklybudget/flaskapp/static/js/payperiod_modal.js` (lines 78-97)
  - Backend: `SchedToTransFormHandler` in `biweeklybudget/flaskapp/views/payperiods.py` (lines 206-269)
  - Currently transfers: date, amount, description, notes, account, budget reference
  - Does NOT transfer sales_tax (doesn't exist on ScheduledTransaction yet)

### Critical Files

#### Backend
- `biweeklybudget/models/scheduled_transaction.py` - Add sales_tax column
- `biweeklybudget/flaskapp/views/scheduled.py` - Update SchedTransFormHandler
- `biweeklybudget/flaskapp/views/payperiods.py` - Update SchedToTransFormHandler
- `biweeklybudget/alembic/versions/` - New migration file

#### Frontend
- `biweeklybudget/flaskapp/static/js/scheduled_modal.js` - Add sales_tax field to add/edit form
- `biweeklybudget/flaskapp/static/js/payperiod_modal.js` - Add sales_tax to conversion modal

#### Tests
- `biweeklybudget/tests/fixtures/sampledata.py` - Add sales_tax to sample scheduled transactions
- `biweeklybudget/tests/acceptance/flaskapp/views/test_scheduled.py` - Test sales_tax in CRUD operations
- `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py` - Test sales_tax transfer in conversion
- `biweeklybudget/tests/migrations/` - New migration test file
- Any other unit tests that create ScheduledTransaction objects

### Milestones

#### Milestone 1: Database Schema and Backend Model
**Prefix: SchedTax - 1.x**

1.1. Add `sales_tax` column to ScheduledTransaction model
   - Column type: `Numeric(precision=10, scale=4)`
   - Constraints: `nullable=False, default=0.0`
   - Follow same pattern as Transaction.sales_tax

1.2. Create Alembic migration
   - Generate new migration file
   - Upgrade: Add sales_tax column to scheduled_transactions table
   - Downgrade: Drop sales_tax column
   - Follow pattern from `d01774fa3ae3` migration

1.3. Update ScheduledAjax view to include sales_tax in DataTable response
   - File: `biweeklybudget/flaskapp/views/scheduled.py`
   - Add sales_tax column to AJAX response (similar to amount)

1.4. Update OneScheduledAjax to include sales_tax
   - File: `biweeklybudget/flaskapp/views/scheduled.py`
   - Include in JSON response for single scheduled transaction

1.5. Update SchedTransFormHandler to handle sales_tax
   - File: `biweeklybudget/flaskapp/views/scheduled.py`
   - Add to validate() if needed
   - Add to submit() - read from form, convert to Decimal, default to 0.0

#### Milestone 2: Frontend Forms
**Prefix: SchedTax - 2.x**

2.1. Add sales_tax field to scheduled transaction add/edit modal
   - File: `biweeklybudget/flaskapp/static/js/scheduled_modal.js`
   - Add field in `schedModalDivForm()` function (after amount field)
   - Type: currency input
   - Help text: "Sales tax for this transaction (default 0.0)."
   - Populate in `schedModalDivFillAndShow()` when editing

2.2. Add sales_tax to scheduled→transaction conversion modal
   - File: `biweeklybudget/flaskapp/static/js/payperiod_modal.js`
   - Add field in `schedToTransModalDivForm()` (after amount field)
   - Type: currency input
   - Populate in `schedToTransModalDivFillAndShow()` from scheduled transaction data

2.3. Update SchedToTransFormHandler to transfer sales_tax
   - File: `biweeklybudget/flaskapp/views/payperiods.py`
   - Read sales_tax from form data
   - Set on new Transaction object
   - Default to 0.0 if not provided

#### Milestone 3: Test Data and Unit Tests
**Prefix: SchedTax - 3.x**

3.1. Update sample data fixtures
   - File: `biweeklybudget/tests/fixtures/sampledata.py`
   - Add sales_tax values to existing ScheduledTransaction objects
   - Use mix of 0.0 and non-zero values (e.g., 1.23, 4.56)

3.2. Create migration test
   - File: `biweeklybudget/tests/migrations/test_migration_XXXXXX.py` (use actual revision)
   - Test that sales_tax column exists after upgrade
   - Test that sales_tax column doesn't exist after downgrade
   - Follow pattern from `test_migration_d01774fa3ae3.py`

3.3. Review and update any unit tests that create ScheduledTransaction objects
   - Ensure they either set sales_tax or work with default 0.0

#### Milestone 4: Acceptance Tests
**Prefix: SchedTax - 4.x**

4.1. Add sales_tax tests to scheduled transaction CRUD
   - File: `biweeklybudget/tests/acceptance/flaskapp/views/test_scheduled.py`
   - Test adding scheduled transaction with sales_tax
   - Test editing scheduled transaction to change sales_tax
   - Verify sales_tax appears in table (if displayed)
   - Verify sales_tax saved to database

4.2. Add sales_tax transfer test to conversion
   - File: `biweeklybudget/tests/acceptance/flaskapp/views/test_payperiods.py`
   - Modify `test_05_modal_schedtrans_to_trans()` or create new test
   - Set sales_tax on scheduled transaction
   - Convert to transaction
   - Verify sales_tax is transferred to new transaction
   - Test both zero and non-zero sales_tax values

4.3. Run full acceptance test suite
   - Ensure all existing tests still pass
   - Fix any broken tests due to schema changes

#### Milestone 5: Final Testing and Documentation
**Prefix: SchedTax - 5.x**

5.1. Run complete test suites
   - `tox -e py310` - Unit tests
   - `tox -e acceptance` - Acceptance tests (increase timeout if needed)
   - `tox -e migrations` - Migration tests
   - `tox -e docker` - Docker build tests
   - Fix any failures

5.2. Update documentation
   - Review and update `CLAUDE.md` if needed
   - Review and update any relevant docs in `docs/source/`
   - Update `README.md` if needed

5.3. Update feature document
   - Mark feature as complete
   - Document any decisions or deviations

## Implementation Progress

### Milestone 1: Database Schema and Backend Model - COMPLETE

**Completed Tasks:**
- ✅ 1.1: Added sales_tax column to ScheduledTransaction model (Numeric(10,4), nullable=False, default=0.0)
- ✅ 1.2: Created Alembic migration 1bb9e6a1c07c_add_scheduledtransaction_sales_tax_field
- ✅ 1.3: Updated ScheduledAjax view to include sales_tax in DataTable response
- ✅ 1.4: OneScheduledAjax automatically includes sales_tax via ModelAsDict.as_dict()
- ✅ 1.5: Updated SchedTransFormHandler.submit() to handle sales_tax from form data

**Commit:** 7de0502 - "SchedTax - 1.x: Database Schema and Backend Model complete"

### Milestone 2: Frontend Forms - COMPLETE

**Completed Tasks:**
- ✅ 2.1: Added sales_tax currency field to scheduled transaction add/edit modal (scheduled_modal.js)
- ✅ 2.2: Added sales_tax currency field to scheduled→transaction conversion modal (payperiod_modal.js)
- ✅ 2.3: Updated SchedToTransFormHandler.submit() to read and transfer sales_tax to new Transaction

**Commit:** 222f9a7 - "SchedTax - 2.x: Frontend Forms complete"

### Milestone 3: Test Data and Unit Tests - COMPLETE

**Completed Tasks:**
- ✅ 3.1: Updated sample data with sales_tax values for all 6 ScheduledTransaction objects
- ✅ 3.2: Created migration test test_migration_1bb9e6a1c07c.py
- ✅ 3.3: Reviewed unit tests - no changes needed (default value 0.0 handles existing code)

**Commit:** 214a22f - "SchedTax - 3.x: Test Data and Unit Tests complete"

### Milestone 4: Acceptance Tests - NOT STARTED

### Milestone 5: Final Testing and Documentation - NOT STARTED
