# Data Model: Plaid Screenshots

No schema changes. The screenshots use existing sample data
(`biweeklybudget/tests/fixtures/sampledata.py`), unchanged.

## Sample data used

| Entity | Records | Used by |
|--------|---------|---------|
| PlaidItem | `PlaidItem1` (Inst1), `PlaidItem2` (Inst2) | Plaid Update page (both tables), result page rows |
| PlaidAccount | `PlaidAcct1`, `PlaidAcct2`, `PlaidAcct4` on Item 1; `PlaidAcct3` on Item 2 | Plaid Update page account lists; Plaid Account selector options |
| Account | `BankOne` (id 1) linked to `PlaidItem1` / `PlaidAcct1` | Edit Account modal, selector pre-selected |

## Stub update results (screenshot run only, never stored)

`PlaidUpdateResult(item, success, updated, added, exc, stmt_ids)` values returned by the
stub (research R1), one per requested Item, in the order given:

| Position | success | updated | added | exc | stmt_ids |
|----------|---------|---------|-------|-----|----------|
| first | True | 23 | 4 | None | a list of statement IDs |
| each other | False | 0 | 0 | `ITEM_LOGIN_REQUIRED` sample error | None |

With the two sample Items this gives one success, one failure, and a total row reading
"1 Failed".
