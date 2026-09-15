# Data Model: Restore Skipped Reconcile Drag-and-Drop Acceptance Tests

This feature adds or changes no models, tables, columns or page-side data. This file
lists the existing entities the restored tests check, so each assertion can be traced
to what it verifies.

## Reconcile page state (`reconciled`, JavaScript, `reconcile.js`)

- Mapping of Transaction ID to `[account_id, fitid]`, or to a note string for "no OFX"
  reconciles.
- **Set** by a successful drop (`reconcileTransactions()`), one key per dropped pair.
- **Cleared** after a successful submit. **Kept** after a failed submit, e.g. an
  invalid Transaction ID returning HTTP 400.
- Tests read it through `ReconcileHelper.get_reconciled()`.

## Reconcile record (`TxnReconcile`, table `txn_reconciles`)

- Links one Transaction to one OFX transaction (`ofx_account_id`, `ofx_fitid`), or holds
  a note. Unique on `txn_id`.
- Created by `POST /ajax/reconcile` on submit.
- The fixtures start with one record (Transaction 7 ↔ `(2, 'OFX8')`), which each
  class's `test_06_verify_db` checks.

## Fixture pairs used by the drags (from `ReconcileHelper.test_03`/`test_04`)

| OFX element | Account | Amount | Transaction div |
|-------------|---------|--------|-----------------|
| `ofx-2-OFX3` | 2 | 600 | `trans-3` |
| `ofx-1-OFX1` | 1 | -100 | `trans-1` |
| `ofx-1-OFX2` | 1 | 250 | `trans-2` |
| `ofx-2-OFXT6` | 2 | 25 | `trans-5` |
| `ofx-2-OFXT7` | 2 | 25 | `trans-6` |

A drop is accepted only when the account and amount match and the Transaction's drop
target is empty (`reconcileTransDroppableAccept()`).
