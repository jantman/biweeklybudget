# Standing Budget Plans (Link Projects to Standing Budgets)

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

Projects in biweeklybudget track costs via BoMItems (Bill of Materials), but there is currently no link between a Project and the Standing Budget that funds it. This feature adds an optional one-to-one relationship from Project to Standing Budget (`is_periodic=False`), allowing users to associate a project with the standing budget used to pay for its items. This is implemented as an optional foreign key on the `projects` table pointing to `budgets`, with a dropdown in the project creation/edit UI to select an active standing budget.

## Implementation Plan

### Design Decisions

1. **One budget per project**: Each project can optionally be linked to exactly one standing budget. The relationship is optional (nullable FK).
2. **FK on Project**: Add `standing_budget_id` column to `projects` table as a nullable foreign key to `budgets.id`.
3. **No constraint on budget type at DB level**: The UI will only offer standing budgets (`is_periodic=False`) in the dropdown, but the FK itself just references `budgets.id`. This keeps the schema simple.
4. **Dropdown on project form**: Add a standing budget dropdown to the inline project add form on `/projects` and also allow editing via a new project edit modal (currently projects only have an inline add form with no edit capability, so we will add an edit modal similar to the BoMItem modal pattern).
5. **Display in table**: Show the linked standing budget name in the projects DataTable.

### Background

- **Project Model** (`biweeklybudget/models/projects.py`): Fields: `id`, `name` (String 40), `notes` (String 254), `is_active` (Boolean). Properties: `total_cost`, `remaining_cost`. No existing relationship to Budget.
- **Budget Model** (`biweeklybudget/models/budget_model.py`): Standing budgets have `is_periodic=False` and use `current_balance`. Fields include: `id`, `is_periodic`, `name`, `description`, `starting_balance`, `current_balance`, `is_active`, `is_income`, `omit_from_graphs`.
- **Projects View** (`biweeklybudget/flaskapp/views/projects.py`): `ProjectsView` (GET /projects), `ProjectsAjax` (GET /ajax/projects), `ProjectsFormHandler` (POST /forms/projects with actions: add, activate, deactivate), `ProjectAjax` (GET /ajax/projects/<id>), plus BoMItem views.
- **Projects Template** (`biweeklybudget/flaskapp/templates/projects.html`): Inline form with fields: name, notes. No modal. JavaScript in `static/js/projects.js`.
- **FormBuilder** (`biweeklybudget/flaskapp/static/js/formBuilder.js`): Provides `addLabelToValueSelect()` for dropdown selects, `addText()`, `addHidden()`, `addCheckbox()`, etc. Used by BoMItem and Budget modals.

### Critical Files

#### Backend
- `biweeklybudget/models/projects.py` - Add `standing_budget_id` FK column and relationship
- `biweeklybudget/flaskapp/views/projects.py` - Update `ProjectsFormHandler`, `ProjectsAjax`, `ProjectAjax`; add edit action
- `biweeklybudget/flaskapp/views/projects.py` - Pass standing budgets to template context in `ProjectsView`
- `biweeklybudget/alembic/versions/` - New migration file for FK column

#### Frontend
- `biweeklybudget/flaskapp/templates/projects.html` - Add standing budget dropdown to inline form; add modal include; pass standing budget data to JS
- `biweeklybudget/flaskapp/static/js/projects.js` - Add standing budget to inline form handling; add project edit modal functions

#### Tests
- `biweeklybudget/tests/fixtures/sampledata.py` - Link some sample projects to standing budgets
- `biweeklybudget/tests/acceptance/flaskapp/views/test_projects.py` - Test standing budget dropdown in add/edit, display in table
- `biweeklybudget/tests/migrations/` - New migration test file

---

### Milestone 1: Database Schema and Backend Model
**Prefix: SBP - 1.x**

#### Task 1.1: Add `standing_budget_id` column to Project model
- File: `biweeklybudget/models/projects.py`
- Add column: `standing_budget_id = Column(Integer, ForeignKey('budgets.id'), nullable=True)`
- Add relationship: `standing_budget = relationship('Budget', uselist=False)`
- Import Budget if needed for relationship

#### Task 1.2: Create Alembic migration
- Generate migration: `alembic -c biweeklybudget/alembic/alembic.ini revision -m "add standing_budget_id to projects"`
- Upgrade: Add `standing_budget_id` column (Integer, nullable) and foreign key constraint to `budgets.id`
- Downgrade: Drop foreign key constraint, then drop column
- Follow pattern from existing migrations (e.g., `d01774fa3ae3`)

#### Task 1.3: Update ProjectsAjax to include standing budget in DataTable response
- File: `biweeklybudget/flaskapp/views/projects.py`
- Add `standing_budget_name` (or null) to each row's JSON response
- Query should eager-load or join the budget relationship to avoid N+1 queries

#### Task 1.4: Update ProjectAjax to include standing budget info
- File: `biweeklybudget/flaskapp/views/projects.py`
- Include `standing_budget_id` and `standing_budget_name` in single-project JSON response

#### Task 1.5: Update ProjectsFormHandler to handle standing_budget_id
- File: `biweeklybudget/flaskapp/views/projects.py`
- In `add` action: read `standing_budget_id` from form, set on new Project (convert "None"/empty to None)
- Add `edit` action: allow updating name, notes, and standing_budget_id for an existing project
- Validate that if a standing_budget_id is provided, it references a valid standing budget

#### Task 1.6: Update ProjectsView to pass standing budgets to template
- File: `biweeklybudget/flaskapp/views/projects.py`
- Query active standing budgets: `Budget.query.filter(Budget.is_periodic==False, Budget.is_active==True).order_by(Budget.name).all()`
- Pass as dict `{name: id}` to template context (following pattern from budgets/payperiod views)

#### Task 1.7: Run unit tests and verify no regressions

---

### Milestone 2: Frontend Changes
**Prefix: SBP - 2.x**

#### Task 2.1: Update projects.html template
- Add `{% include 'modal.html' %}` for the edit modal
- Add JavaScript variable for standing budget name→id mapping (following `budget_names_to_id` pattern):
  ```html
  var standing_budget_names_to_id = {};
  {% for name in standing_budgets.keys()|sort %}
  standing_budget_names_to_id["{{ name }}"] = {{ standing_budgets[name] }};
  {% endfor %}
  ```
- Add standing budget dropdown (`<select>`) to the inline add form, with a "None" option and all active standing budgets as options

#### Task 2.2: Update projects.js - inline form and DataTable
- Update DataTable columns to include standing budget name column
- Update inline form submission to include `standing_budget_id`
- Add `projectModal(id)` function for editing projects (following `bomItemModal` pattern):
  - Fetch project data via `/ajax/projects/<id>`
  - Build form with FormBuilder: name, notes, standing_budget_id dropdown, is_active checkbox
  - Submit to `/forms/projects` with action "edit"
- Add click handler on project name or edit link in table to open modal

#### Task 2.3: Update DataTable rendering
- Add standing budget name as a column in the projects table
- Render as link to budget page or just text
- Handle null (no linked budget) gracefully

#### Task 2.4: Manual verification of UI
- Test adding project with and without standing budget
- Test editing project to add/change/remove standing budget
- Verify table displays budget name correctly

---

### Milestone 3: Test Data and Migration Tests
**Prefix: SBP - 3.x**

#### Task 3.1: Update sample data fixtures
- File: `biweeklybudget/tests/fixtures/sampledata.py`
- Link P1 to Standing1 budget (`standing_budget_id` set)
- Leave P2 with no standing budget (null)
- Leave P3Inactive with no standing budget (null)

#### Task 3.2: Create migration test
- File: `biweeklybudget/tests/migrations/test_migration_XXXXXX.py` (use actual revision)
- Test that `standing_budget_id` column exists after upgrade
- Test that foreign key constraint exists after upgrade
- Test that column and constraint are removed after downgrade
- Follow pattern from existing migration tests

#### Task 3.3: Run migration tests
- `tox -e migrations`

---

### Milestone 4: Acceptance Tests
**Prefix: SBP - 4.x**

#### Task 4.1: Update existing project acceptance tests
- File: `biweeklybudget/tests/acceptance/flaskapp/views/test_projects.py`
- Update `test_00_verify_db` to check standing_budget_id values on sample projects
- Update `test_01_table` to verify standing budget column in table
- Update `test_03_add` to include selecting a standing budget in the add form

#### Task 4.2: Add new acceptance tests for standing budget dropdown
- Test adding a project with a standing budget selected
- Test adding a project with no standing budget (None selected)
- Verify the standing budget name appears in the table after add
- Verify the standing budget is saved to the database

#### Task 4.3: Add acceptance tests for project edit modal
- Test opening edit modal populates fields correctly (including standing budget dropdown)
- Test editing a project to change its standing budget
- Test editing a project to remove its standing budget (set to None)
- Verify changes are persisted to database

#### Task 4.4: Run full acceptance test suite
- `tox -e acceptance` with appropriate timeout
- Fix any broken tests

---

### Milestone 5: Final Testing and Documentation
**Prefix: SBP - 5.x**

#### Task 5.1: Run complete test suites
- `tox -e py314` - Unit tests
- `tox -e acceptance` - Acceptance tests (increase timeout if needed)
- `tox -e migrations` - Migration tests
- `tox -e docker` - Docker build tests
- Fix any failures

#### Task 5.2: Update documentation
- Review and update `CLAUDE.md` if needed (e.g., Project model description)
- Review and update relevant docs in `docs/source/` (e.g., `biweeklybudget.models.projects.rst`)
- Update feature document with completion status

#### Task 5.3: Final commit and PR preparation
- Move feature document to `complete/` directory
- Increment version in `biweeklybudget/version.py` (minor version bump)
- Add changelog entry to `CHANGES.rst`
- Push to origin and create PR

---

## Progress

### Milestone 1: Database Schema and Backend Model - COMPLETE
- Task 1.1: Added `standing_budget_id` FK column and `standing_budget` relationship to Project model
- Task 1.2: Created Alembic migration `a1b2c3d4e5f6`
- Task 1.3: Updated ProjectsAjax with outerjoin and `standing_budget_name` in DataTable response
- Task 1.4: Updated ProjectAjax to include `standing_budget_name` in single-project JSON
- Task 1.5: Updated ProjectsFormHandler with `standing_budget_id` handling in `add`, new `edit` action
- Task 1.6: Updated ProjectsView to query and pass active standing budgets to template
- Task 1.7: Unit tests pass (488/488, 2 expected collection errors for MySQL-dependent tests)

### Milestone 2: Frontend Changes - COMPLETE
- Task 2.1: Updated projects.html with Standing Budget column, dropdown in add form, modal include, JS variable
- Task 2.2: Updated projects.js with standing_budget_name column, edit modal (projectModal), form handling

### Milestone 3: Test Data and Migration Tests - COMPLETE
- Task 3.1: Updated sampledata.py to link P1 to Standing1 budget
- Task 3.2: Created migration test test_migration_a1b2c3d4e5f6.py

### Milestone 4: Acceptance Tests - COMPLETE
- Task 4.1-4.3: Updated and expanded acceptance tests for standing budget feature
  - Updated test_00_verify_db, test_01_table, test_02_search with standing budget column
  - Added test_03_add_with_standing_budget and test_05_add_without_standing_budget
  - Added tests 11-16 for project edit modal (populate, change budget, remove budget, verify)

### Milestone 5: Final Testing and Documentation - COMPLETE
- Task 5.1: All test suites pass
  - Unit tests (py314): 511 passed
  - Migration tests: 6 passed (including schema comparison)
  - Acceptance tests: 513 passed
  - Fixed migration down_revision, FK naming convention, DT_RowData access, duplicate form IDs
