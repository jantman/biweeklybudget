# Phase 1 Data Model: Special Handling of Credit Card Payments

**Feature**: `specs/20260906-174344-credit-card-payments/`
**Date**: 2026-09-06

---

## Modified entity: `Transaction` (`biweeklybudget/models/transaction.py`)

### New columns

```python
#: Whether this Transaction is excluded from all budget and pay period
#: arithmetic. Set for transactions that exist only to be reconciled against a
#: real bank or card transaction -- statement credits, cash-back redemptions
#: applied as a statement credit, and manual balance-reconcile adjustments.
#: See also :py:attr:`~.credit_payment_acct_id`, which implies this.
no_budget_impact = Column(Boolean, default=False, nullable=False)

#: ID of the credit :py:class:`~.Account` that this Transaction is a payment
#: toward, or None if it is not a credit card payment. Setting this makes the
#: Transaction excluded from budget arithmetic; see
#: :py:attr:`~.is_excluded_from_budget`.
credit_payment_acct_id = Column(Integer, ForeignKey('accounts.id'))
```

| Column | Type | Nullable | Default | Notes |
|--------|------|----------|---------|-------|
| `no_budget_impact` | `Boolean` | No | `False` | User's explicit choice only |
| `credit_payment_acct_id` | `Integer` FK → `accounts.id` | Yes | `NULL` | Must name an account of type `Credit` |

### New relationship

```python
#: Relationship - the credit :py:class:`~.Account` this Transaction is a
#: payment toward, if any.
credit_payment_acct = relationship(
    "Account", backref="credit_payments", uselist=False,
    foreign_keys=[credit_payment_acct_id]
)
```

### Required change to an existing relationship

`transactions` now holds two foreign keys to `accounts.id`, so the existing relationship
must state which one it joins on. Without this, mapper configuration raises
`AmbiguousForeignKeysError` on import and every code path in the application fails:

```python
account = relationship(
    "Account", backref="transactions", uselist=False,
    foreign_keys=[account_id]          # <-- added
)
```

### New derived property

```python
@hybrid_property
def is_excluded_from_budget(self):
    """
    Whether this Transaction is excluded from all budget and pay period
    arithmetic, either because it was explicitly marked as having no budget
    impact or because it is a payment toward a credit account.
    """
    return self.no_budget_impact or self.credit_payment_acct_id is not None

@is_excluded_from_budget.expression
def is_excluded_from_budget(cls):
    return or_(
        cls.no_budget_impact.is_(True),
        cls.credit_payment_acct_id.isnot(None)
    )
```

This is the value every consumer reads. `no_budget_impact` is never read directly for
arithmetic; reading it alone would miss credit payments, and writing to it from the credit
path would make FR-014 unimplementable (see research.md D-3).

### Serialization

`ModelAsDict.as_dict` iterates instance `vars()`, so both columns appear in
`/ajax/transactions/<id>` automatically once they are set. `_dict_properties` gains
`'is_excluded_from_budget'` so the derived value is available to the modal without the
client recomputing it.

### Validation rules

| Rule | Enforced where | Requirement |
|------|----------------|-------------|
| `credit_payment_acct_id` must name an existing account | `TransactionFormHandler.validate()` | FR-015 |
| That account must have `acct_type == AcctType.Credit` | `TransactionFormHandler.validate()` | FR-015 |
| The select offers only active credit accounts | `TransactionsView` / `OneTransactionView` | FR-010 |
| An existing payment toward a now-inactive account still displays that account | `transModalDivFillAndShow` appends the option if absent | Edge case |
| Paying an account from itself is warned, not blocked | `credit_payment.py`, surfaced in the modal | FR-022 |
| Transaction still needs ≥1 budget summing to its amount | unchanged existing validation | FR-006 |

State transitions are unconstrained: both fields may be set or cleared on any unreconciled
transaction, and the existing prohibition on editing a reconciled transaction is unchanged.

---

## Unchanged entities, changed behaviour

### `Account` (`biweeklybudget/models/account.py`)

No schema change. Gains the `credit_payments` backref from the relationship above.

`unreconciled_sum` skips transactions where `is_excluded_from_budget` is true (FR-004).
`unreconciled` — the query property — is **not** filtered, so the reconcile view continues
to offer excluded transactions for reconciliation (FR-005). See research.md D-5 for the
recorded trade-off.

### `BiweeklyPayPeriod` (`biweeklybudget/biweeklypayperiod.py`)

No schema. The transaction dict produced by `_dict_for_trans()` gains one key:

* `no_budget_impact` (**bool**) — whether this transaction is excluded from the pay
  period's budget arithmetic. Always `False` for ScheduledTransactions.

`_make_budget_sums()` skips entries whose `no_budget_impact` is true, before any of its
`allocated` / `spent` / `trans_total` accumulation. `_make_overall_sums()` needs no change:
it reads only `self._data_cache['budget_sums']`.

---

## New non-persisted entity: credit payment attribution

Lives in the new module `biweeklybudget/credit_payment.py`. Computed on demand; nothing is
stored.

```text
CreditPaymentAttribution(db, account, amount, payment_date, exclude_txn_id=None)
```

| Attribute | Type | Meaning |
|-----------|------|---------|
| `periods` | list of dicts, oldest first | One entry per pay period holding outstanding charges |
| `periods[i]['start_date']` | `date` | Pay period start |
| `periods[i]['is_closed']` | `bool` | Whether the period has ended |
| `periods[i]['outstanding']` | `Decimal` | Charges in that period not settled by prior payments |
| `periods[i]['attributed']` | `Decimal` | How much of this payment settles them |
| `total_unpaid` | `Decimal` | Sum of `outstanding` across all periods |
| `total_attributed` | `Decimal` | Sum of `attributed` |
| `excess` | `Decimal` | `amount - total_attributed`; positive triggers the over-payment warning |
| `pays_itself` | `bool` | Transaction is recorded against the same account it pays (FR-022) |
| `warnings` | list of str | Human-readable advisory messages |

The algorithm, with its window and ordering, is specified in research.md D-7.
