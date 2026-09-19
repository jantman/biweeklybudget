# Phase 1 Data Model: Credit Payment Panel Window

**Feature**: Credit Payment Panel Window
**Spec**: [spec.md](./spec.md)
**Date**: 2026-09-19

**No persisted data changes.** No model under `biweeklybudget/models/` is touched, no
column is added, and no Alembic migration is required. What follows describes the
in-memory objects and the serialized shape the panel consumes.

## Columns read (existing, unchanged)

| Column | Used for |
|--------|----------|
| `transactions.account_id` | charges recorded against the credit account |
| `transactions.date` | window bounds, pay-period grouping, and the `MIN(date)` anchor |
| `transactions.credit_payment_acct_id` | identifies a transaction as a payment toward a credit account; added in 2.0.0 by migration `f9df90273cdd` |
| `transactions.id` | `exclude_txn_id` |

## `CreditPaymentAttribution` attributes

| Attribute | Type | Status | Meaning |
|-----------|------|--------|---------|
| `account` | `Account` | unchanged | the credit account being paid |
| `amount` | `Decimal` | unchanged | the candidate payment amount |
| `payment_date` | `date` | unchanged | the date of the payment; the window's upper bound |
| `exclude_txn_id` | `int` or `None` | unchanged | the transaction being edited, excluded from `_prior_payments()` only |
| `payer_account_id` | `int` or `None` | unchanged | used only for the self-payment check |
| `configured_begin_date` | `date` | **new** | `settings.CREDIT_PAYMENT_BEGIN_DATE` verbatim — the operator's floor |
| `begin_date` | `date` | **meaning changed** | the *effective* window start: `max(configured_begin_date, derived)`, or `configured_begin_date` when nothing anchors it |
| `periods` | `list` of period dicts | **meaning changed** | now at most `CREDIT_PAYMENT_MAX_PERIODS` entries — the most recent ones |
| `rollup` | dict or `None` | **new** | the collapsed older periods, or `None` when nothing was collapsed |
| `total_unpaid` | `Decimal` | unchanged | unpaid charges in the window after prior payments; **covers the collapsed periods too** |
| `total_attributed` | `Decimal` | unchanged | how much of `amount` settles recorded charges |
| `excess` | `Decimal` | unchanged | the unapplied remainder |
| `pays_itself` | `bool` | unchanged | |
| `warnings` | `list` of `str` | unchanged | |

`total_unpaid`, `total_attributed` and `excess` are computed over the **whole** window,
before the cap is applied. The cap is a display concern; it must never change an amount.

## Period dict

Unchanged. One per pay period rendered individually, oldest first.

| Key | Type | Meaning |
|-----|------|---------|
| `start_date` | `date` | the pay period's start |
| `end_date` | `date` | the pay period's end |
| `is_closed` | `bool` | the period ended before the current one began |
| `outstanding` | `Decimal` | unpaid charges in the period, including what this payment covers |
| `attributed` | `Decimal` | how much of this payment this period absorbs |

## Rollup dict (new)

Present when the window holds more than `CREDIT_PAYMENT_MAX_PERIODS` periods with a
non-zero total; `None` otherwise.

| Key | Type | Meaning |
|-----|------|---------|
| `count` | `int` | how many periods were collapsed; always ≥ 1 |
| `start_date` | `date` | start of the oldest collapsed period |
| `end_date` | `date` | end of the newest collapsed period |
| `outstanding` | `Decimal` | sum of the collapsed periods' `outstanding` |
| `attributed` | `Decimal` | sum of the collapsed periods' `attributed` |

## Invariants

These hold for every result and are what the tests pin:

1. `sum(p['outstanding'] for p in periods) + rollup['outstanding'] == total_unpaid`.
   Each period's `outstanding` is restored to its pre-attribution value
   (`outstanding + attributed`), and `total_unpaid` is likewise measured after prior
   payments but before this one, so the two sides describe the same quantity.
2. `sum(p['attributed'] for p in periods) + rollup['attributed'] == total_attributed`.
3. `total_attributed + excess == amount`.
4. `len(periods) <= CREDIT_PAYMENT_MAX_PERIODS`, always.
5. `rollup is None` if and only if nothing was collapsed.
6. `begin_date >= configured_begin_date`, always. The floor is never undercut.
7. The transaction anchoring `begin_date` is dated strictly before `begin_date`, so it is
   never also counted by `_prior_payments()`.

## Module constant

`CREDIT_PAYMENT_MAX_PERIODS = 6` in `biweeklybudget/credit_payment.py`. Six biweekly
periods ≈ three months. Not a setting; see research.md D-4.
