# Phase 1 Data Model: Exclude Inactive Accounts From Dropdowns And The Balances Chart

**Feature**: [spec.md](./spec.md) | **Date**: 2026-09-19

**No structural change.** No table, column, relationship, index or constraint is added,
altered or removed, and no Alembic migration is required (FR-016, Constitution III).
What follows records which existing entities this feature reads, and the one behavioural
rule it attaches to each.

## Account (`biweeklybudget/models/account.py`)

| Field | Role in this feature |
|---|---|
| `id` | The value of every option in every account select; the key of the chart's `accounts` map. |
| `name` | The label of every option; the series name (`keys` entry) on the chart. |
| `is_active` | **The rule.** Existing `Boolean`, unchanged. Its value now decides whether the Account is *offered* and *charted*. |

**Added behaviour** — one static query method, no state:

```
Account.active_accounts(db) -> Query   # Account.is_active == True, ordered by name
```

It mirrors the existing `Account.active_credit_accounts(db)` (`account.py:264`) in name,
signature, docstring shape and return type: a `Query`, not a list, so callers choose
`.all()` or compose further. It is the single definition of "an Account that may be
chosen", replacing the eleven copies of an unfiltered query.

**Not changed**: `is_active` semantics, how it is set (the Edit Account modal), and the
fact that deactivation is reversible and non-destructive. An Account made active again
reappears in every select and on the chart with its full history, on the next page load.

## AccountBalance (`biweeklybudget/models/account_balance.py`)

Read-only here, and **retained in full** for inactive Accounts (FR-004). Rows whose
`account_id` is not an active Account are skipped while assembling the chart response;
they are never filtered out of the query (R4 — doing so would drop dates from the
response), and never deleted.

## Transaction / ScheduledTransaction / FuelFill

Each holds an `account_id` that may point at an Account that has since been deactivated.

**The invariant this feature must not break**: a stored `account_id` is never changed by
this feature, and opening and saving one of these records without touching its Account
field leaves `account_id` exactly as it was (FR-011). This is what forbids both a blanket
server-side rejection of inactive accounts on save (R5) and a bare narrowing of the
select without re-adding the record's own value.

`ScheduledTransaction` carries the same invariant through the "skip scheduled
transaction" flow: the Transaction created to skip it is created against the scheduled
transaction's own Account, inactive or not.

## Derived structures (not persisted)

These are the actual subject of the change — per-request maps handed to templates:

| Name | Shape | Contents after this change |
|---|---|---|
| `accts` / `acct_names_to_id` | `{name: id}` | **All** Accounts. Survives only where a table filter reads it. |
| `active_accts` / `active_acct_names_to_id` | `{name: id}` | **Active** Accounts. New; read by every account picker. |
| `credit_accts` / `credit_acct_names_to_id` | `{name: id}` | Active credit Accounts. Unchanged. |
| `accounts` (chart) | `{id: name}` | **Active** Accounts. Was all Accounts. |

Which page receives which is specified in
[contracts/template-account-maps.md](./contracts/template-account-maps.md).
