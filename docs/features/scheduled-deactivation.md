# Scheduled Transaction Automatic Deactivation

**IMPORTANT:** You MUST read and understand the instructions in the `README.md` document in this directory, and MUST ALWAYS follow those requirements during feature implementation.

## Overview

This application supports scheduled transactions using a variety of schedule types (per period or date of month for repeating transactions, etc.) including specific dates for single-time scheduled transactions. Right now, these specific date scheduled transactions remain "active" even long after the date has passed. Our goal is to add some functionality such that specific date scheduled transactions more than one month in the past are automatically deactivated.
