# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

biweeklybudget is a responsive Flask/SQLAlchemy personal finance application designed for biweekly (fortnightly) budgeting. It supports automatic transaction downloading via OFX Direct Connect or Plaid, scheduled transactions, fuel logging, project cost tracking, and credit card payoff calculations.

**License:** GNU Affero General Public License v3+

## Development Commands

### Testing

Run the full test suite with tox:
```bash
tox
```

Run specific test environments:
```bash
# Unit tests (Python 3.10)
tox -e py310

# Acceptance tests (requires Chrome driver)
tox -e acceptance

# Documentation build
tox -e docs

# Database migration tests
tox -e migrations

# Plaid integration tests (requires Plaid credentials)
tox -e plaid

# Docker build tests
tox -e docker
```

Run a single test file or test:
```bash
# Activate virtualenv first
source venv/bin/activate

# Run specific test file
pytest biweeklybudget/tests/unit/test_file.py

# Run specific test
pytest biweeklybudget/tests/unit/test_file.py::TestClass::test_method

# Run with coverage
pytest --cov=biweeklybudget --cov-report=html
```

### Database Setup

#### Quick Setup (Production/Local Development)
Initialize the database:
```bash
initdb
```

The database schema is managed with Alembic migrations in `biweeklybudget/alembic/versions/`.

#### Test Database Setup for Development

**IMPORTANT**: When developing features that require database changes, you must set up a test database BEFORE making model changes if you want to use Alembic's autogenerate feature.

1. **Start Docker test database container:**
```bash
docker run -d --name budgettest -p 13306:3306 \
  --env MYSQL_ROOT_PASSWORD=dbroot \
  --env MYSQL_ROOT_HOST='%' \
  mariadb:10.4.7
```

2. **Set environment variables for test database:**
```bash
export DB_CONNSTRING='mysql+pymysql://root:dbroot@127.0.0.1:13306/budgettest?charset=utf8mb4'
export SETTINGS_MODULE='biweeklybudget.tests.fixtures.test_settings'
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=13306
export MYSQL_USER=root
export MYSQL_PASS=dbroot
export MYSQL_DBNAME=budgettest
export MYSQL_DBNAME_LEFT=alembicLeft
export MYSQL_DBNAME_RIGHT=alembicRight
```

3. **Create the test databases:**
```bash
source venv/bin/activate
python dev/setup_test_db.py
```

4. **Initialize the database to current schema:**
```bash
initdb
```

5. **Cleanup when done:**
```bash
docker stop budgettest && docker rm budgettest
```

#### Creating Database Migrations

There are two workflows for creating Alembic migrations:

**Option A: Autogenerate (Preferred)**
1. Set up test database and run `initdb` BEFORE making any model changes
2. Make your model changes in `biweeklybudget/models/`
3. Generate migration: `alembic -c biweeklybudget/alembic/alembic.ini revision --autogenerate -m "description"`
4. Review and edit the generated migration file in `biweeklybudget/alembic/versions/`
5. Test the migration: `alembic -c biweeklybudget/alembic/alembic.ini upgrade head`

**Option B: Manual Migration (When autogenerate won't work)**
1. Make your model changes in `biweeklybudget/models/`
2. Generate empty migration: `alembic -c biweeklybudget/alembic/alembic.ini revision -m "description"`
3. Manually write the `upgrade()` and `downgrade()` functions following existing migration patterns
4. Test the migration: `alembic -c biweeklybudget/alembic/alembic.ini upgrade head`

**Common Migration Commands:**
```bash
# See current DB version
alembic -c biweeklybudget/alembic/alembic.ini current

# See migration history
alembic -c biweeklybudget/alembic/alembic.ini history

# Upgrade to latest
alembic -c biweeklybudget/alembic/alembic.ini upgrade head

# Downgrade one revision
alembic -c biweeklybudget/alembic/alembic.ini downgrade -1
```

**Migration Patterns:**
- Adding a column: See `d01774fa3ae3_add_transaction_field_to_store_sales_.py` for sales_tax on Transaction
- Column should match model definition: `sa.Column('field_name', sa.Type(...), nullable=...)`
- Always provide both `upgrade()` and `downgrade()` functions
- Test both upgrade and downgrade paths

### Running the Flask App

For development with auto-reload:
```bash
export FLASK_APP=biweeklybudget.flaskapp.app:app
flask rundev
```

This custom `rundev` command (defined in `biweeklybudget/flaskapp/cli_commands.py`) provides:
- Template auto-reloading
- Request timing in logs
- Debug mode enabled by default

For production, use standard Flask commands or Docker.

### Console Scripts

The package provides several entry points (defined in `setup.py`):
- `loaddata` - Load data into database
- `ofxgetter` - Download OFX statements (requires Vault)
- `ofxbackfiller` - Backfill OFX statements
- `initdb` - Initialize database
- `wishlist2project` - Sync Amazon wishlists to projects
- `ofxclient` - Vendored OFX client CLI

## Architecture

### Core Components

**Database Layer (`biweeklybudget/db.py`)**
- SQLAlchemy engine and session management
- Database connection configured via `DB_CONNSTRING` in settings
- Uses MySQL/MariaDB with specific SQL modes for data integrity
- Scoped sessions with `db_session`

**Models (`biweeklybudget/models/`)**
Core database models:
- `Account` - Financial accounts (bank, credit, investment)
- `Transaction` - Manual or reconciled transactions
- `OFXTransaction` - Downloaded transactions (OFX or Plaid)
- `ScheduledTransaction` - Recurring or scheduled transactions
- `Budget` - Budget categories (periodic or standing)
- `BudgetTransaction` - Links transactions to budgets (supports splits)
- `TxnReconcile` - Reconciliation mapping between OFX and manual transactions
- `BiweeklyPayPeriod` - Pay period date calculations and aggregations
- `FuelFill` and `Vehicle` - Fuel logging
- `Project` and `BoMItem` - Project cost tracking
- `PlaidItem` and `PlaidAccount` - Plaid integration

**Pay Period Logic (`biweeklybudget/biweeklypayperiod.py`)**
- `BiweeklyPayPeriod` class handles all pay period date calculations
- Start date configured in `settings.PAY_PERIOD_START_DATE`
- Provides methods to find pay periods for dates, iterate periods, and aggregate financial data

**Flask Application (`biweeklybudget/flaskapp/`)**
- `app.py` - Application factory, initializes DB and registers views
- `views/` - Route handlers organized by feature (accounts, budgets, transactions, reconcile, etc.)
- `templates/` - Jinja2 templates
- `static/` - Frontend assets (Bootstrap, jQuery, custom JS)
- `filters.py` - Jinja2 template filters
- `context_processors.py` - Template context processors
- `jsonencoder.py` - Custom JSON encoder for SQLAlchemy models

**Transaction Sources**
- **OFX Direct Connect**: Uses `ofxgetter.py` with Hashicorp Vault for credentials
- **Plaid**: Uses `plaid_updater.py` with Plaid API
- **Manual Entry**: Through web interface

**Settings (`biweeklybudget/settings.py`)**
- Loads from `biweeklybudget/settings_example.py` or environment
- Key settings: `DB_CONNSTRING`, `PAY_PERIOD_START_DATE`, `VAULT_ADDR`, Plaid credentials
- Settings module specified via `SETTINGS_MODULE` environment variable

### Key Patterns

**Database Sessions**
- Use `biweeklybudget.db.db_session` for all database operations
- Session is scoped and automatically cleaned up via `@app.teardown_appcontext`
- Models extend `biweeklybudget.models.base.ModelAsDict` which provides `as_dict()` method

**Testing**
- Unit tests in `biweeklybudget/tests/unit/`
- Acceptance tests in `biweeklybudget/tests/acceptance/` (use Selenium)
- Migration tests in `biweeklybudget/tests/migrations/`
- Test settings in `biweeklybudget/tests/fixtures/test_settings.py`
- Tests use pytest with markers: `@pytest.mark.acceptance`, `@pytest.mark.integration`, `@pytest.mark.migrations`, `@pytest.mark.plaid`

**Views Pattern**
- Most views inherit from `FormHandlerView` or `SearchableAjaxView`
- AJAX endpoints return JSON using the custom `MagicJSONEncoder`
- Many views are AJAX-driven with datatables on the frontend

**Database Migrations**
- Alembic migrations in `biweeklybudget/alembic/versions/`
- Migration tests verify upgrade/downgrade paths
- Use `alembic-verify` package to ensure migrations match models

**Copyright Headers**
All Python files include a standard copyright header with AGPL v3 license text. When creating new files, include the header found in existing files.

## Important Notes

- **Python Version**: Currently targets Python 3.10 (configurable in tox.ini)
- **Database**: MySQL/MariaDB required (uses MySQL-specific features)
- **Frontend**: jQuery + Bootstrap 3 + DataTables
- **Security**: Application not designed for public access - intended for localhost use only
- **Currency**: US-centric but configurable via locale settings
- **Pay Periods**: All budgeting logic revolves around biweekly pay periods calculated from `PAY_PERIOD_START_DATE`

## Development Environment Setup

```bash
# Create virtualenv
python3.10 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e .

# Set up database (requires MySQL running)
# Edit settings.py or set DB_CONNSTRING environment variable
initdb
```

## Environment Variables

- `DB_CONNSTRING` - Database connection string (overrides settings.py)
- `SETTINGS_MODULE` - Python module path for settings (default: `biweeklybudget.settings`)
- `SQL_ECHO` - Set to 'true' to enable SQLAlchemy query logging
- `FLASK_APP` - Set to `biweeklybudget.flaskapp.app:app` for Flask CLI
- `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV`, `PLAID_COUNTRY_CODES` - Plaid integration
- `BIWEEKLYBUDGET_LOG_FILE` - Optional log file path (used in tests)

## Project Structure

```
biweeklybudget/
├── alembic/              # Database migrations
├── flaskapp/             # Flask web application
│   ├── static/          # Frontend assets
│   ├── templates/       # Jinja2 templates
│   └── views/           # Route handlers
├── models/               # SQLAlchemy models
├── tests/                # Test suite
│   ├── unit/            # Unit tests
│   ├── acceptance/      # Acceptance tests
│   └── migrations/      # Migration tests
├── vendored/             # Vendored dependencies (ofxclient)
└── *.py                  # CLI scripts and utilities
```
