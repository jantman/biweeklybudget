# Additional Scheduled Transactions

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

Right now, this application supports three types of scheduled transactions: Monthly (day number each month), Per Period (N of these in every pay period), or specific date (one specific YYYYMMDD date). Our goal is to add two more recurring scheduled transaction types: Day of Week (transaction recurs every week on the specified day of week, such as every Monday) and Annual (transactions recurs on a specified month and day of month every year, such as every April 4th). This must be supported end-to-end, i.e. in the database, the backend code, and the frontend. You must add acceptance tests to verify that each of the new scheduled transaction types can be added and edited by a user via the modal dialog, display correctly in the scheduled transaction table, and are properly included in the appropriate pay periods (and not in pay periods where they should not exist).

