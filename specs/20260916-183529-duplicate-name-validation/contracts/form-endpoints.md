# Contract: Account and Budget form endpoints

**Feature**: `specs/20260916-183529-duplicate-name-validation`

No endpoint is added, removed or renamed. Two existing endpoints gain one new
rejection case each. Both already return the response shape used below; this change
only adds a new reason for the `errors` branch to be taken.

## `POST /forms/account` — `AccountFormHandler`

### Request

Unchanged. JSON or form-encoded. Relevant fields:

| Field | Meaning |
|-------|---------|
| `name` | The account name. Trimmed before comparison and before storage |
| `id` | Present and non-blank when editing an existing account; absent or blank when creating |

### New response case

When `name`, trimmed and compared case-insensitively, matches an account whose `id`
differs from the submitted `id`:

```json
{
  "success": false,
  "errors": {
    "name": ["An Account named \"BankOne\" already exists (ID 1); Account names must be unique."],
    "...": []
  }
}
```

- HTTP status stays `200` — this endpoint signals failure in the body, as it already
  does for every other validation error.
- `errors` carries one key per submitted field, each an array, most of them empty.
  That is the existing shape produced by `errors = {k: [] for k in data.keys()}` in
  `validate()`; the acceptance tests that assert on the whole dict depend on it.
- No account is created or modified.

### Unchanged response cases

- Valid submission → `{"success": true, "success_message": "Successfully saved Account N in database."}`
- Submission whose name matches only the account being edited → treated as valid; the
  account saves. This is a *requirement* (FR-002), not an accident of the query.
- Blank name → the existing single `"Name cannot be empty"` message, with no
  duplicate-name message stacked on top of it.
- Genuine server failure → the existing `error_message` banner. The database
  constraint remains the last line of defence for the race between validation and
  write, so this case does not disappear; it just stops being how an ordinary user
  first learns that names are unique.

## `POST /forms/budget` — `BudgetFormHandler`

Identical in every respect, against `Budget` rather than `Account`, with "Budget" in
place of "Account" in the message.

## Consumers

`handleFormSubmitted()` in `biweeklybudget/flaskapp/static/js/forms.js` is the only
consumer of the `errors` branch. It finds `[name=name]` in the form, appends a
`<p class="text-danger formfeedback">` carrying each message, and adds `has-error` to
the field's parent. Both modals build their name input via
`.addText('..._frm_name', 'name', 'Name')`, so the input's `name` attribute is `name`
and the message lands under the Name field with no front-end change.
