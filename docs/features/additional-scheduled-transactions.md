# Additional Scheduled Transactions

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

Right now, this application supports three types of scheduled transactions: Monthly (day number each month), Per Period (N of these in every pay period), or specific date (one specific YYYYMMDD date). Our goal is to add two more recurring scheduled transaction types: Day of Week (transaction recurs every week on the specified day of week, such as every Monday) and Annual (transactions recurs on a specified month and day of month every year, such as every April 4th). This must be supported end-to-end, i.e. in the database, the backend code, and the frontend. You must add acceptance tests to verify that each of the new scheduled transaction types can be added and edited by a user via the modal dialog, display correctly in the scheduled transaction table, and are properly included in the appropriate pay periods (and not in pay periods where they should not exist).

---

## Implementation Plan

### Design Decisions

1. **Day of Week Values**: Store as integers 0-6 where 0=Monday, 1=Tuesday, ..., 6=Sunday (Python's `datetime.weekday()` convention).

2. **Annual Date Handling**: Store month (1-12) and day (1-31) separately. Validate that the day is valid for the given month (e.g., reject February 30). For February 29th, simply skip in non-leap years (no special handling - if the date doesn't exist that year, the transaction isn't considered for that year).

3. **Pay Period Behavior**:
   - **Weekly (Day of Week)**: A 14-day biweekly pay period will contain exactly 2 occurrences of each weekday. Both dates will be calculated and included in the pay period.
   - **Annual**: Check if the annual date falls within the pay period's date range. Include it if so.

4. **Database Columns**: Add three new nullable columns to `scheduled_transactions`:
   - `day_of_week` (SmallInteger) - for weekly type
   - `annual_month` (SmallInteger) - for annual type
   - `annual_day` (SmallInteger) - for annual type

5. **Schedule Type Detection**: Update the `schedule_type` hybrid property to check the new fields:
   - If `day_of_week` is not None → `'weekly'`
   - If `annual_month` is not None → `'annual'`

---

### Milestone 1: Database & Model Changes (AST-1.x)

**Prefix:** `AST-1`

#### Task 1.1: Create Database Migration
- Create Alembic migration to add three columns:
  - `day_of_week` (SmallInteger, nullable)
  - `annual_month` (SmallInteger, nullable)
  - `annual_day` (SmallInteger, nullable)

#### Task 1.2: Update ScheduledTransaction Model
- Add the three new columns to the model
- Add validators for:
  - `day_of_week`: 0-6
  - `annual_month`: 1-12
  - `annual_day`: 1-31 (with cross-validation against month for valid dates)
- Update `schedule_type` hybrid property to include `'weekly'` and `'annual'`
- Update `schedule_type.expression` for SQL-side type detection
- Update `recurrence_str` hybrid property:
  - Weekly: "Every {Weekday}" (e.g., "Every Monday")
  - Annual: "{Month} {Day}" (e.g., "Apr 4th")
- Update `recurrence_str.expression` for SQL-side string generation

#### Task 1.3: Add Unit Tests for Model Changes
- Test schedule_type returns 'weekly' when day_of_week is set
- Test schedule_type returns 'annual' when annual_month/annual_day are set
- Test recurrence_str formats correctly for new types
- Test validators reject invalid values

#### Task 1.4: Run Tests and Verify
- Run unit tests: `tox -e py314`
- Run migration tests: `tox -e migrations`
- Update CLAUDE.md if needed

---

### Milestone 2: Backend View Changes (AST-2.x)

**Prefix:** `AST-2`

#### Task 2.1: Update SchedTransFormHandler
- Modify `submit()` to handle new types:
  - `'weekly'`: set `day_of_week` from form data
  - `'annual'`: set `annual_month` and `annual_day` from form data
- Clear other schedule fields when type changes (e.g., when switching from monthly to weekly, clear day_of_month)
- Add validation in `validate()` for the new fields

#### Task 2.2: Update OneScheduledAjax
- Ensure the `as_dict` response includes the new fields for populating the edit modal

#### Task 2.3: Update ScheduledAjax (DataTable)
- Add the new schedule types to the type filter dropdown options

#### Task 2.4: Run Tests and Verify
- Run existing unit tests to ensure no regressions

---

### Milestone 3: Frontend Changes (AST-3.x)

**Prefix:** `AST-3`

#### Task 3.1: Update scheduled_modal.js
- Add radio buttons for 'weekly' and 'annual' types
- Add input fields:
  - Weekly: dropdown for day of week selection (Monday-Sunday)
  - Annual: dropdown for month (January-December) + input for day (1-31)
- Update `schedModalDivHandleType()` to show/hide the new fields
- Update `schedModalDivFillAndShow()` to populate the new fields when editing

#### Task 3.2: Update scheduled.js
- Add 'weekly' and 'annual' to the type filter dropdown

#### Task 3.3: Verify UI manually
- Test creating/editing weekly and annual scheduled transactions
- Test type filter works correctly

---

### Milestone 4: Pay Period Logic (AST-4.x)

**Prefix:** `AST-4`

#### Task 4.1: Add Query Methods for New Types
- Add `_scheduled_transactions_weekly()`: Return all active weekly ScheduledTransactions (these always apply to every pay period)
- Add `_scheduled_transactions_annual()`: Return active annual ScheduledTransactions where the annual date falls within the pay period

#### Task 4.2: Update _data Property
- Add `st_weekly` and `st_annual` to the data cache

#### Task 4.3: Update _make_combined_transactions
- Include weekly transactions (each occurrence for the 2 dates in the pay period)
- Include annual transactions if their date falls in the period

#### Task 4.4: Update _dict_for_sched_trans
- Handle 'weekly' type: Calculate the actual dates in the pay period for the given weekday
- Handle 'annual' type: Calculate the annual date and include it

#### Task 4.5: Add Unit Tests for Pay Period Logic
- Test weekly transactions appear twice in each pay period
- Test annual transactions appear only in the correct pay period
- Test annual transactions do NOT appear in other pay periods
- Test edge cases (pay periods spanning year boundaries for annual)

---

### Milestone 5: Acceptance Tests (AST-5.x)

**Prefix:** `AST-5`

#### Task 5.1: Add Acceptance Tests for Weekly Scheduled Transactions
- Test creating a weekly scheduled transaction via modal
- Test editing an existing weekly scheduled transaction
- Test weekly transactions display correctly in the scheduled transactions table
- Test type filter includes weekly transactions

#### Task 5.2: Add Acceptance Tests for Annual Scheduled Transactions
- Test creating an annual scheduled transaction via modal
- Test editing an existing annual scheduled transaction
- Test annual transactions display correctly in the scheduled transactions table
- Test type filter includes annual transactions

#### Task 5.3: Add Test Fixtures
- Add sample weekly and annual scheduled transactions to test fixtures

#### Task 5.4: Run Full Test Suite
- Run all unit tests: `tox -e py314`
- Run all acceptance tests: `tox -e acceptance`
- Run docker tests: `tox -e docker`
- Run migration tests: `tox -e migrations`

---

### Milestone 6: Documentation & Cleanup (AST-6.x)

**Prefix:** `AST-6`

#### Task 6.1: Update Documentation
- Update any relevant documentation in `docs/source/`
- Update CLAUDE.md if any patterns or conventions changed

#### Task 6.2: Final Verification
- Run complete test suite
- Manual verification of all new functionality
- Review all changes for code quality

#### Task 6.3: Create PR
- Move feature document to `complete/` directory
- Push changes and create detailed PR

---

## Progress

- [x] Milestone 1: Database & Model Changes (completed 2026-01-19)
  - AST-1.1: Created Alembic migration `bbb39e1d7c5d`
  - AST-1.2: Updated ScheduledTransaction model with new fields and properties
  - AST-1.3: Added 44 unit tests for model changes
  - AST-1.4: All unit tests passing (91 tests)
- [x] Milestone 2: Backend View Changes (completed 2026-01-19)
  - AST-2.1: Updated SchedTransFormHandler.submit() for weekly and annual
  - AST-2.2: OneScheduledAjax already includes new fields via as_dict
  - AST-2.3: Updated scheduled.js type filter dropdown
- [x] Milestone 3: Frontend Changes (completed 2026-01-19)
  - AST-3.1: Updated scheduled_modal.js with weekly/annual radio buttons and inputs
  - AST-3.2: Type filter already updated in Milestone 2
- [x] Milestone 4: Pay Period Logic (completed 2026-01-19)
  - AST-4.1: Added _scheduled_transactions_weekly() and _scheduled_transactions_annual()
  - AST-4.2: Updated _data property with st_weekly and st_annual
  - AST-4.3: Updated _make_combined_transactions() for weekly (twice) and annual
  - AST-4.4: Updated _dict_for_sched_trans() with weekly_occurrence parameter
  - AST-4.5: Added 20+ unit tests for pay period logic (103 tests passing)
- [ ] Milestone 5: Acceptance Tests
- [ ] Milestone 6: Documentation & Cleanup

