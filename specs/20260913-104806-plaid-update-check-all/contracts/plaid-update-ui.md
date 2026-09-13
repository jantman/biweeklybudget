# UI Contract: Plaid Update page item selection

Page: `GET /plaid-update` (template `plaid_form.html`), panel `#panel-plaid-update`.

## Elements

| Element | Selector | Text |
|---------|----------|------|
| Check All link | `a#plaid_check_all` | `Check All` |
| Uncheck All link | `a#plaid_uncheck_all` | `Uncheck All` |
| Item checkboxes (unchanged) | `#table-update-plaid input.account-checkbox`, id and name `item_<item_id>`, value `1` | — |

Both links are inside `#panel-plaid-update`, above `#table-update-plaid`.

## Behaviour

| Action | Result |
|--------|--------|
| Page load | Every item checkbox checked (unchanged). |
| Click `#plaid_check_all` | Every item checkbox checked. |
| Click `#plaid_uncheck_all` | Every item checkbox unchecked. |
| Either click | No form submission, no navigation, URL unchanged, no other control changes. |
| Submit ("Update Transactions") | Posts `item_<item_id>=1` for each checked box only (unchanged). |

## Unchanged

The `/plaid-update` endpoint, its parameters and response formats, and the "Plaid Items"
panel.
