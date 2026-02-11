# HTTP API Docs

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

Add a new `HTTP API` page to the Sphinx-built documentation. This should include complete documentation (including request and response data shapes) for Flask views that can be used for driving the application via HTTP, including:

* creating/updating transactions via `POST /forms/transaction`
* creating a transaction from a scheduled transaction via `POST /forms/sched_to_trans`
* listing scheduled transactions in the current payperiod
* updating Plaid items via `/plaid-update`

and any other endpoints that would be useful for external scripts and tools
