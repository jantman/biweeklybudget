# Phase 0 Research: Duplicate Name Validation

**Feature**: `specs/20260916-183529-duplicate-name-validation`
**Date**: 2026-09-16

The spec left four things unresolved that the design depends on. Each is settled
below from the existing code, not from assumption.

---

## R1: Where the duplicate check belongs

**Decision**: Add one helper, `FormHandlerView._validate_unique_name()`, in
`biweeklybudget/flaskapp/views/formhandlerview.py`, and call it from both
`AccountFormHandler.validate()` and `BudgetFormHandler.validate()`.

**Rationale**: `FormHandlerView.post()` (`formhandlerview.py`) already runs
`validate()` before `submit()` and returns whatever `validate()` gives it as
`{'success': False, 'errors': {...}}`. The per-field message the spec asks for is
exactly what that branch produces, so the check has to live in `validate()` —
nowhere else in the request has both the submitted name and the ability to stop the
save. `Account` and `Budget` need identical logic (unique `name`, optional `id` in
the form data meaning "this is an edit"), and the issue notes the same treatment
applies to any further uniquely-named model reached from a form. Putting it in the
base class means the third such form is one line, and the case/trim rules settled in
R2 are decided once rather than re-derived per handler.

**Alternatives considered**:

- *Duplicate the query inline in each handler*, mirroring the existing
  duplicate-Plaid-account block in `AccountFormHandler.validate()`, as the issue
  suggests. Rejected: that block is inline because it is genuinely
  account-specific — it matches on two Plaid columns and its message names the Plaid
  relationship. A unique-name check has no per-model content beyond the model class
  and the noun in the message, so copying it twice would put the case-sensitivity
  decision in two places that could later drift apart.
- *Catch `IntegrityError` in `submit()` and translate it*. Rejected: it reads the
  constraint name out of a driver error string to work out which field failed, and
  it leaves the session needing a rollback — the spec's FR-006 (store unchanged, form
  intact) is free when the save never starts.

---

## R2: Case and whitespace semantics of the check (FR-007)

**Decision**: Compare `func.lower(cls.name) == submitted_name.strip().lower()`, i.e.
compare the *trimmed* submitted name, case-insensitively, in the database.

**Rationale**, in two parts:

*Trimming* is not a choice. Both `submit()` methods store `data['name'].strip()`
(`accounts.py`, `budgets.py`). Validating the untrimmed string would let `" BankOne "`
pass a check against a stored `"BankOne"` and then be stored as `"BankOne"` — the
exact database error this change exists to prevent.

*Case-insensitivity* is the right verdict under either collation, which is why it can
be decided without pinning the server's collation down:

- Under the case-insensitive collation MariaDB uses by default for `utf8mb4` (the
  charset in `DB_CONNSTRING`), the unique index itself already treats `"bankone"` and
  `"BankOne"` as the same name. A case-sensitive check would pass a name the database
  then rejects — validation that does not match the constraint behind it.
- Were the collation case-sensitive, a case-insensitive check would be *stricter*
  than the database: it would reject `"bankone"` alongside an existing `"BankOne"`.
  That is still correct behaviour here, because
  `biweeklybudget/models/utils.py::_resolve_reference` — which the HTTP API uses to
  look up accounts and budgets by name — matches names with `func.lower()` and
  `.one_or_none()`. Two names differing only in case would make that call raise
  `MultipleResultsFound`, breaking API lookups for both records. So the two records
  must not coexist regardless of what the index permits.

Using `func.lower()` explicitly, rather than leaning on the collation, follows the
precedent already set and documented in `_resolve_reference`: *"``func.lower()`` is
used explicitly rather than relying on the database's collation being
case-insensitive, so that the behavior is a property of this code and is pinned by a
test."* The same reasoning and the same mechanism apply here.

**Measured, not assumed** (task T011, 2026-09-16): against MariaDB 10.4.7 with the
schema `initdb` creates, `information_schema.COLUMNS` reports `accounts.name`,
`budgets.name` and `reconcile_rules.name` as `utf8mb4` / **`utf8mb4_general_ci`**, and
inserting `caseprobe` alongside an existing `CaseProbe` is rejected with
`(1062, "Duplicate entry 'caseprobe' for key 'ix_accounts_name'")`. So the first bullet
above is the case that actually applies: the index *is* case-insensitive, and a
case-sensitive check would pass names the database then rejects. The second bullet
stands as the reason the decision does not depend on that measurement holding on every
deployment.

**Alternatives considered**: exact `cls.name == name` equality. Rejected on both
counts above — it is looser than the default collation's index and looser than the
name resolution the API depends on.

---

## R3: Telling "create" from "edit"

**Decision**: Exclude the record being edited with `cls.id != record_id`, where
`record_id` is `int(data['id'])` when `data` has a non-blank `'id'`, and `0`
otherwise.

**Rationale**: This is precisely how the existing duplicate-Plaid-account check in
`AccountFormHandler.validate()` decides the same question, and how both `submit()`
methods decide whether they are creating or updating. `0` is safe as the
"no record yet" sentinel because these are MySQL `AUTO_INCREMENT` primary keys, which
start at 1. Reusing the established idiom keeps one answer to "which record am I?" in
the file rather than introducing a second.

**Alternatives considered**: comparing against the stored name of the record being
edited rather than excluding it by ID. Rejected: it needs an extra query and gets the
three-way case of renaming A onto B's name wrong unless it also does the exclusion.

---

## R4: Front end

**Decision**: No JavaScript, template, or CSS change.

**Rationale**: `handleFormSubmitted()` in `biweeklybudget/flaskapp/static/js/forms.js`
already handles the `errors` key by finding `[name=<field>]` in the form, appending a
`<p class="text-danger formfeedback">` with each message and adding `has-error` to the
field's parent. Both modals render their name input as `name="name"`, so a
`errors['name']` entry lands under the Name field with no front-end work. This is the
same path the existing "Name cannot be empty" message takes, so the duplicate-name
message inherits an appearance the user has already seen.

**Consequence for testing**: acceptance tests can assert on the rendered
`formfeedback` element, which is how `test_04_no_date_error` in
`tests/acceptance/flaskapp/views/test_accounts.py` already asserts a validation
message, and can assert on the JSON via a direct `requests.post`, which is how
`test_05_no_date_error_requests` and its neighbours do it. Both patterns are already
in the file being extended.

---

## R5: Schema impact

**Decision**: No model change, therefore no Alembic migration, and the `migrations`
tox environment is not in scope for this feature.

**Rationale**: Confirmed rather than assumed — `grep -rn "unique=True"
biweeklybudget/models/` returns exactly three lines (`account.py:109`,
`budget_model.py:70`, `reconcile_rule.py:53`) and this change adds a check *in front
of* those existing constraints. Nothing under `biweeklybudget/models/` is touched, so
Constitution Principle III (schema changes ship with reversible migrations) has
nothing to bite on. The `migrations` suite compares head against the models; with the
models unchanged it cannot newly fail, and running it is not a gate here.

**Note on `ReconcileRule`**: its `name` is unique, but a search of
`biweeklybudget/flaskapp/views/` finds no view or form that creates or edits one — it
is populated by `loaddata`/fixtures only. There is no user submission to validate, so
it stays out of scope, as recorded in the spec's assumptions.
