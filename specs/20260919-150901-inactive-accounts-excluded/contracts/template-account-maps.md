# Contract: Which Page Gets Which Account Map

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-19

This is the UI contract for the change: the two JavaScript globals a page may define, the
rule that decides which one a select reads, and the resulting per-page and per-select
assignment. Derived in [../research.md](../research.md) R1–R2.

## The two globals

| Global | Contents | Read by |
|---|---|---|
| `acct_names_to_id` | `{name: id}` for **all** Accounts | Selects that **filter a table of existing rows** |
| `active_acct_names_to_id` | `{name: id}` for **active** Accounts | Selects that **choose an Account for a record** |

`credit_acct_names_to_id` (active credit Accounts) is unchanged by this feature.

**The rule**: a select that decides where a *record* goes lists active Accounts only; a
select that narrows a view of *history* lists every Account. This is the same rule the
Budget selects already follow — `budget_names_to_id` on the Transactions page filter,
`active_budget_names_to_id` in the Transaction entry form.

A page defines only the global(s) its scripts read. A page that defines neither is not
part of this contract.

## Per-page assignment

| Page / template | `acct_names_to_id` | `active_acct_names_to_id` | Why |
|---|---|---|---|
| `index.html` | — | ✓ | Account Transfer modal only |
| `accounts.html` | — | ✓ | Account Transfer modal only |
| `budgets.html` | — | ✓ | Budget Transfer modal only |
| `fuel.html` | — | ✓ | Fuel Fill modal only |
| `scheduled.html` | — | ✓ | Scheduled Transaction modal only |
| `payperiod.html` | — | ✓ | Transaction, Scheduled Transaction, skip-scheduled and Budget Transfer modals |
| `reconcile.html` | ✓ | ✓ | Hosts both the downloaded-transactions filter and the Transaction/Scheduled modals |
| `transactions.html` | ✓ | ✓ | Hosts both the Transactions table filter and the Transaction modal |
| `ofx.html` | ✓ | — | Downloaded-transactions filter only |

A `—` in the first column means the template **stops** emitting `acct_names_to_id` and the
view **stops** passing `accts`: nothing on that page reads it any more, and leaving it
would be dead code (R2).

## Per-select assignment

### Reads `active_acct_names_to_id` (FR-005 to FR-010)

| Select | Element id | File |
|---|---|---|
| Account Transfer — From Account | `acct_txfr_frm_from_account` | `account_transfer_modal.js` |
| Account Transfer — To Account | `acct_txfr_frm_to_account` | `account_transfer_modal.js` |
| Budget Transfer — Account | `budg_txfr_frm_account` | `budget_transfer_modal.js` |
| Add/Edit Transaction — Account | `trans_frm_account` | `transactions_modal.js` |
| Add/Edit Scheduled Transaction — Account | `sched_frm_account` | `scheduled_modal.js` |
| Skip Scheduled Transaction — Account | `skipschedtrans_frm_account` | `payperiod_modal.js` |
| Add Fuel Fill — Account | `fuel_frm_account` | `fuel.js` |

### Reads `acct_names_to_id` (FR-014, unchanged)

| Select | Element id | File |
|---|---|---|
| Transactions table — Account filter | `account_filter` | `transactions.js` |
| Downloaded transactions table — Account filter | `account_filter` | `ofx.js` |

## The re-add rule (FR-011, FR-012)

Three selects open on an **existing record** and must show that record's Account even
when it has since been deactivated:

| Select | Fill function | Name source |
|---|---|---|
| `trans_frm_account` | `transModalDivFillAndShow(msg)` | `msg['account_name']` |
| `sched_frm_account` | `schedModalDivFillAndShow(msg)` | `msg['account_name']` |
| `skipschedtrans_frm_account` | `skipSchedTransModalDivFillAndShow(msg)` | `msg['account_name']` |

Each, before selecting `msg['account_id']`:

> If the select has no option with that value, append one — value `msg['account_id']`,
> text `msg['account_name']` — then select it.

Both AJAX endpoints already return `account_name`: `/ajax/transactions/<id>`
(`views/transactions.py:265`) and `/ajax/scheduled/<id>` (`views/scheduled.py:206`). No
endpoint changes.

This is byte-for-byte the move `transModalDivFillAndShow()` already makes for a
deactivated credit-payment account (`transactions_modal.js:100-110`).

**Scope of the re-add**: the appended option exists only on that one opened form, for that
one record. Opening the same form for a record with an active Account, or for a new
record, shows only active Accounts (FR-012).

**Why it must exist**: `serializeForm()` (`forms.js:266-299`) reads every `select` in the
form, *including disabled ones*, via `$(this).find(':selected').val()`. Without the
re-add, an edit form for a record on a deactivated Account would post a different account
id — or `None` — on a save the user never intended to retarget. The skip-scheduled form
makes this sharpest: its Account field is disabled and is submitted anyway.

## Invariants

- **INV-1**: No page defines a global it does not read.
- **INV-2**: `acct_names_to_id`, wherever defined, means *all Accounts* — never a page-specific subset.
- **INV-3**: No select is populated from `active_acct_names_to_id` and then filtered further client-side; the server decides the list.
- **INV-4**: No option is labelled or styled to indicate inactivity. A re-added option looks like any other.
- **INV-5**: No client-side enforcement is added or removed. The Account Transfer handler's server-side rejection of inactive Accounts (`views/accounts.py:338`, `:355`) remains the authority (FR-015).
