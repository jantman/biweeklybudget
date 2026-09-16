# Phase 1 Data Model: Duplicate Name Validation

**Feature**: `specs/20260916-183529-duplicate-name-validation`
**Date**: 2026-09-16

## Schema changes

**None.** No table, column, index or constraint is added, altered or removed, and no
Alembic revision is created. See [research.md](./research.md) R5, and the Principle III
section of [plan.md](./plan.md), for why that is a verified claim rather than an
assumption.

## Entities involved (all pre-existing, all unmodified)

### Account — `biweeklybudget/models/account.py`

| Column | Definition | Relevance |
|--------|-----------|-----------|
| `id` | `Integer, primary_key=True` | Identifies the record being edited, so it can be excluded from the duplicate lookup |
| `name` | `String(50), unique=True, index=True` (line 109) | The constraint being validated in front of. The index makes the new lookup cheap |

### Budget — `biweeklybudget/models/budget_model.py`

| Column | Definition | Relevance |
|--------|-----------|-----------|
| `id` | `Integer, primary_key=True` | As above |
| `name` | `String(50), unique=True, index=True` (line 70) | As above |

### ReconcileRule — `biweeklybudget/models/reconcile_rule.py`

`name` is `String(50), unique=True` (line 53), but no view under
`biweeklybudget/flaskapp/` references the class — it is populated by fixtures and
`loaddata` only. With no form, there is no user submission to validate. Listed here
so that the third unique-name model is accounted for rather than overlooked; it is out
of scope, as the spec's assumptions record.

## The validation rule

For a submission to a form backed by model class `C`:

```text
submitted  := data['name'].strip()
record_id  := int(data['id']) if data has a non-blank 'id' else 0
conflict   := first C where lower(C.name) == lower(submitted) and C.id != record_id
```

A non-null `conflict` appends one message to `errors['name']` and the submission is
rejected before `submit()` runs.

Each element of that rule is forced by something, not chosen for taste:

| Element | Why |
|---------|-----|
| `.strip()` on the submitted name | Both `submit()` methods store `data['name'].strip()`. Comparing the untrimmed value would let `" BankOne "` pass and then be stored as a duplicate `"BankOne"` |
| `lower()` on both sides | Matches the default `utf8mb4` collation's own verdict, and matches `models/utils.py::_resolve_reference`, which resolves API names with `func.lower()` and `.one_or_none()` — two names differing only in case would break that lookup for both records. See [research.md](./research.md) R2 |
| `C.id != record_id` | Lets a record keep its own name on edit. `0` is a safe sentinel for "not yet created" because these keys are `AUTO_INCREMENT` and start at 1. Same idiom as the existing duplicate-Plaid-account check |
| Rejected before `submit()` | Nothing is written, so the record store is unchanged (FR-006) and the session needs no post-`IntegrityError` rollback |

## State transitions

None. No entity gains a state, and no record changes state as a result of this
feature — a rejected submission leaves every record exactly as it was.
