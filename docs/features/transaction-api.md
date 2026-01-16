# Transaction API

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

Creation of Transactions in this application was intended to be done only via the UI, but we now have a need to allow creation of transactions via a HTTP API usable by separate tooling (such as `curl`). The appropriate endpoints may or may not already exist, for use by the frontend. Our goal is to ensure that an API endpoint exists for creation of Transactions via external tooling, and to add a proof-of-concept Python script/entrypoint to this project that creates Transactions via this API. The script should accept inputs similar to the Add Transaction form. For Accounts and Budgets, either the name or ID should be accepted.
