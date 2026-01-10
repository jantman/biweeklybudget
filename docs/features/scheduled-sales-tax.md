# Scheduled Transaction Sales Tax

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

This application supports Scheduled Transactions which are displayed in the appropriate pay periods and can be converted to Transactions when they occur. Scheduled Transactions currently just have an Amount field, but Transactions have both an Amount and a Sales Tax. Our task is to add a Sales Tax field to Scheduled Transactions (in the database and in the add/edit form in the UI) and ensure that when a Transaction is made from a Scheduled Transaction (`schedToTransModal()` javascript in the UI) the sales tax is included if it was set to a non-zero amount. We will need to update all tests (both unit and acceptance) to validate this new functionality.
