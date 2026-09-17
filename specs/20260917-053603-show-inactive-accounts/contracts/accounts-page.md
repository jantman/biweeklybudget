# Contract: The Accounts Page

**Feature**: [../spec.md](../spec.md) | **Date**: 2026-09-17

The interface this feature changes is a rendered HTML page, not an API. This document is the
contract the acceptance tests assert against. No HTTP route, request parameter, response shape,
or JSON payload changes anywhere in this feature.

## Routes

| Route | Handler | Change |
|-------|---------|--------|
| `GET /accounts` | `AccountsView.get()` | Response body only: all accounts now listed, `Active?` column added |
| `GET /accounts/<int:acct_id>` | `OneAccountView.get()` | Same, plus its existing behaviour of auto-opening the modal — which now works for an inactive account too |
| `GET /ajax/account/<int:account_id>` | `AccountAjax.get()` | **None.** Already returns `is_active` in `acct.as_dict` for any account |
| `POST /forms/account` | `AccountFormHandler` | **None.** Already writes `is_active` in both directions |

## Table structure

Each of the three panels gains **`Active?` as its new first column**, matching
`templates/budgets.html`. Columns after it are unchanged, in order.

| Panel (`id`) | Table `id` | Columns |
|---|---|---|
| `panel-bank-accounts` | `table-accounts-bank` | `Active?`, `Account`, `Balance`, `Unreconciled`, `Difference` |
| `panel-credit-cards` | — | `Active?`, `Account`, `Balance`, `Credit Limit`, `Available`, `Unreconciled`, `Difference` |
| `panel-investment` | `table-accounts-investment` | `Active?`, `Account`, `Value` |

Panel and table `id` attributes are unchanged; tests and the transfer flow locate tables by
them.

## Row contract

For every `Account` of the panel's `acct_type` — **active and inactive alike** (FR-001) —
ordered by `name` ascending with the two interleaved (FR-008):

### Row element

| Account state | Markup |
|---|---|
| active | `<tr>` |
| inactive | `<tr class="inactive">` |

`tr.inactive` is the existing rule in `static/css/custom.css:7`
(`background-color: #d9d9d9 !important`), shared with Budgets, Scheduled Transactions and
Projects. **No new CSS.** (FR-003)

### `Active?` cell

| Account state | Markup | Rendered text |
|---|---|---|
| active | `<td>yes</td>` | `yes` |
| inactive | `<td style="color: #a94442;">NO</td>` | `NO` |

Character-for-character the same as `templates/budgets.html:81,110`. (FR-002)

### `Account` cell

Unchanged for every account, active or inactive (FR-004):

```html
<td><a href="javascript:accountModal({{ acct.id }}, null)">{{ acct.name }}</a></td>
```

An inactive account's link is a normal link — not disabled, not styled differently beyond the
row's grey. Clicking it opens the Edit Account modal with `Active?` unchecked, and saving with
it checked re-activates the account.

### Balance age span

```html
<span class="data_age{{ ' text-danger' if acct.is_active and acct.is_stale }}">({{ ... }})</span>
```

The age is always shown. The red `text-danger` is applied only when the account is **both**
stale **and active** — one added condition (FR-007, research R4). For active accounts this is
exactly today's behaviour.

### Value cells when data is absent (FR-006)

| Condition | Contract |
|---|---|
| `acct.balance is None` | `Balance` / `Value`, and any cell derived from it (`Difference`, `Available`), render empty. The row still renders; the page still returns 200 |
| `acct.credit_limit is None` (credit) | `Credit Limit`, and the derived `Available` and `Difference`, render empty. The row still renders; the page still returns 200 |
| both present | Today's behaviour, unchanged, to the cent |

The page must never return a 500 because one account is missing a figure.

## Invariants (asserted by tests that this feature must not change)

- **`GET /` (dashboard)**: its `panel-bank-accounts`, `panel-credit-cards` and
  `panel-investment` share element `id`s with this page but are rendered from `index.html` by
  `views/index.py`. They continue to list **active accounts only**, with no `Active?` column.
  `test_index.py:91-143` must pass **unmodified**. (FR-009)
- **`/accounts/credit-payoff`, `/cash-position`, pay period pages, the account balance chart**:
  unchanged, to the cent. (FR-009, SC-005)
- **`POST /forms/account/transfer`**: an inactive account is still rejected with
  `From Account must be active` / `To Account must be active`. The dropdown continues to list
  every account, as it already does. (FR-009, research R6)
