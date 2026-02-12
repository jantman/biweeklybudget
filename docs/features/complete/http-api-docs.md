# HTTP API Docs

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

Add a new `HTTP API` page to the Sphinx-built documentation. This should include complete documentation (including request and response data shapes) for Flask views that can be used for driving the application via HTTP, including:

* creating/updating transactions via `POST /forms/transaction`
* creating a transaction from a scheduled transaction via `POST /forms/sched_to_trans`
* listing scheduled transactions in the current payperiod
* updating Plaid items via `/plaid-update`

and any other endpoints that would be useful for external scripts and tools

## Implementation Plan

Create a single new RST file (`docs/source/http_api.rst`) documenting all scriptable HTTP endpoints with request/response data shapes and curl examples. Add it to the Sphinx toctree. Follow existing RST style from `plaid.rst`.

### Milestones

1. **Core document structure and all endpoints** - Create `http_api.rst` with intro, common patterns, and complete endpoint documentation for: transactions, scheduled transactions, accounts, budgets, reconciliation, OFX, fuel, Plaid (cross-ref), and utility endpoints. Add to `index.rst` toctree.
2. **Final review, tests, and feature completion** - Run all test suites, move feature doc to `complete/`, bump version, push and open PR.

## Progress

### Milestone 1: Complete - Core document and all endpoints
- [x] Created feature branch `http-api-docs`
- [x] Created `docs/source/http_api.rst` with all endpoint documentation
- [x] Added `HTTP API <http_api>` to `index.rst` toctree after "Flask App"
- [x] Documented: transactions (create/update, get, sched_to_trans, skip_sched)
- [x] Documented: scheduled transactions (create/update, get)
- [x] Documented: accounts (create/update, get, transfer)
- [x] Documented: budgets (create/update, get, transfer)
- [x] Documented: reconciliation (submit, unreconciled OFX, unreconciled trans)
- [x] Documented: OFX (upload statement, list accounts)
- [x] Documented: fuel (log fill, create/update vehicle)
- [x] Documented: Plaid (cross-reference to plaid.rst)
- [x] Documented: utility (pay_period_for)
- [x] Updated feature doc with progress

### Milestone 2: Complete - Final review, tests, and feature completion
- [x] Run `tox -e docs` to verify build
- [x] Run full test suites
- [x] Move feature doc to `complete/`
- [x] Bump version to 1.5.1
- [x] Add CHANGES.rst entry
- [x] Push and open PR
