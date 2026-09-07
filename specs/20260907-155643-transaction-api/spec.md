# Feature Specification: Transaction API — Name-or-ID Lookup and Console Script

**Feature Branch**: `robot-army/issue-322-implement-the-transaction-http-api-and`

**Created**: 2026-09-07

**Status**: Draft

**Input**: GitHub issue #322, "Implement the Transaction HTTP API and use it to automate credit card payment entry", plus `docs/features/transaction-api.md`.

## Overview

External tooling needs to create Transactions in biweeklybudget without going through the
web UI. The concrete driver is the biweekly credit card payment workflow: an external
script already computes, per credit account, the charges in a pay period; today the user
then hand-enters the payment transaction and its negating offset, and mis-typed offsets
are the most common source of error in the whole workflow.

The HTTP endpoint for creating a Transaction already exists (`POST /forms/transaction`)
and is already documented for scripting. Two things stop an external script from using
it:

1. It identifies Accounts and Budgets **only by numeric database ID**. A script that
   knows "CHASE" and "Groceries" cannot address them without first scraping IDs out of
   the application.
2. There is no in-project example of driving it, so every consumer starts from scratch.

This feature closes both gaps: the Transaction-creation endpoint accepts Accounts and
Budgets by **either name or ID**, and the project ships a console script that creates a
Transaction through that endpoint, taking inputs similar to the Add Transaction form.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a Transaction by Account and Budget name (Priority: P1)

An external script author knows their accounts and budgets by the names they see in the
web UI ("CHASE", "Groceries"). They post a Transaction to the application's
Transaction-creation endpoint using those names, and the Transaction is created against
the right Account and Budget without the script ever having to look up a numeric ID.

**Why this priority**: Without this, the endpoint is unusable from external tooling that
does not already have database access; this is the blocking gap named in issue #322.

**Independent Test**: Post a Transaction whose `account` field is an account name and
whose budget key is a budget name; confirm the created Transaction is linked to the
Account and Budget bearing those names. Delivers the whole "usable from a script" value
on its own, even with no console script present.

**Acceptance Scenarios**:

1. **Given** an Account named "CHASE" and an active Budget named "Groceries", **When** a
   Transaction is submitted with account "CHASE" and budgets `{"Groceries": "12.34"}`,
   **Then** a Transaction is created linked to that Account with a budget allocation
   against that Budget, and the success response reports the new Transaction's ID.
2. **Given** the same Account and Budget, **When** a Transaction is submitted using their
   numeric IDs exactly as the web UI does today, **Then** it is created identically —
   existing ID-based callers, including the web UI, are unaffected.
3. **Given** a Transaction submitted with account name "No Such Account", **When** it is
   validated, **Then** it is rejected with a field-level error naming the unresolvable
   account, and no Transaction is created.
4. **Given** a Transaction submitted with budget name "No Such Budget", **When** it is
   validated, **Then** it is rejected with a field-level error naming the unresolvable
   budget, and no Transaction is created.
5. **Given** an inactive Budget named "Old Budget", **When** a new Transaction is
   submitted against it by name, **Then** it is rejected for the same reason it would be
   rejected by ID — resolving by name does not weaken any existing validation.
6. **Given** a credit Account named "CHASE", **When** a Transaction is submitted with
   the credit-payment-account field set to "CHASE" by name, **Then** the Transaction is
   recorded as a payment for that credit account; and a non-credit account supplied by
   name is rejected exactly as a non-credit account ID is today.

---

### User Story 2 - Create a Transaction from the command line (Priority: P2)

A user or an automation script runs a console command shipped with the project, giving it
a date, amount, description, account, and one or more budget allocations, and the command
creates the Transaction through the HTTP API and reports the new Transaction's ID.

**Why this priority**: This is the proof of concept that shows the endpoint is genuinely
usable from outside, and the reusable building block for the credit card payment
automation the issue is motivated by. It depends on Story 1 for name support but is
independently valuable once the endpoint exists.

**Independent Test**: With the application running, invoke the console command with
account and budget names and confirm a Transaction appears with the expected values, and
that the command prints the new Transaction ID and exits successfully.

**Acceptance Scenarios**:

1. **Given** a running application, **When** the console command is invoked with a date,
   amount, description, account name, and a single budget name, **Then** a Transaction is
   created and the command reports success with the new Transaction's ID and exits zero.
2. **Given** a running application, **When** the command is invoked with multiple budget
   allocations, **Then** the created Transaction carries one allocation per budget with
   the given amounts.
3. **Given** an input the application rejects (e.g. an unknown budget, or budget amounts
   that do not sum to the transaction amount), **When** the command is invoked, **Then**
   it prints the validation errors the application returned, in a form that identifies
   which field failed, and exits non-zero.
4. **Given** the application is not reachable at the configured address, **When** the
   command is invoked, **Then** it reports the connection failure clearly and exits
   non-zero rather than raising an unhandled traceback.
5. **Given** no explicit address is supplied, **When** the command is invoked, **Then** it
   targets a documented default address, overridable by both a command-line option and an
   environment variable.

---

### Edge Cases

- **A name that looks like a number.** If a Budget or Account is named "123", a value of
  `123` is ambiguous between "ID 123" and "the record named 123". The rule must be
  deterministic and documented.
- **Names differing only by case or surrounding whitespace.** Account and Budget names are
  unique in the database, but a caller may send `"chase"` or `" CHASE "`. Whether these
  resolve must be defined, not accidental.
- **Income budget display suffix.** The web UI shows income budgets as "Name (income)".
  A caller reading names off the UI may send that suffixed form; it is not the stored name.
- **Mixed identification within one request.** An account given by ID and budgets given by
  name (or the reverse) in the same request must work.
- **Multiple budgets, one unresolvable.** The whole request must be rejected — no partial
  Transaction, no partial budget allocation.
- **Updating an existing Transaction by name.** The endpoint also serves updates; name
  resolution must behave the same there, including the existing rule about inactive
  budgets already attached to the transaction.
- **Empty or omitted credit-payment-account.** Must continue to mean "not a credit card
  payment", not "resolve the empty string as a name".

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Transaction-creation endpoint MUST accept the Account either as a
  numeric Account ID or as an Account name.
- **FR-002**: The Transaction-creation endpoint MUST accept each Budget in the budget
  allocation mapping either as a numeric Budget ID or as a Budget name.
- **FR-003**: The Transaction-creation endpoint MUST accept the credit-payment Account
  either as a numeric Account ID or as an Account name.
- **FR-004**: Resolution MUST be deterministic: a value consisting only of digits is
  treated as a record ID; any other value is treated as a name. When a digits-only value
  matches no record by ID, the endpoint MUST then attempt to resolve it as a name before
  reporting failure, so that a record whose name is numeric remains reachable.
- **FR-005**: Name matching MUST be exact against the stored name after stripping leading
  and trailing whitespace, and MUST be case-insensitive. Account and Budget names are
  unique, so at most one record can match.
- **FR-006**: A value that resolves to no Account or Budget MUST produce a field-level
  validation error that quotes the unresolvable value, and MUST NOT create or modify any
  Transaction.
- **FR-007**: All validation that exists today MUST continue to apply unchanged once a
  name has been resolved — inactive-budget rules, the requirement that budget amounts sum
  to the transaction amount, the credit-account-only rule for the credit-payment account,
  the non-empty description, the non-zero amount, and the date format.
- **FR-008**: Requests that identify Accounts and Budgets by numeric ID MUST behave
  exactly as they do today, including every request the web UI makes. Callers MUST be able
  to mix IDs and names within a single request.
- **FR-009**: The project MUST ship a console script, installed as a console entry point,
  that creates a Transaction by calling the application's HTTP API — not by writing to the
  database directly.
- **FR-010**: The console script MUST accept the inputs of the Add Transaction form: date,
  amount, description, account, one or more budget allocations, and optionally notes and
  sales tax; and it MUST accept the credit-payment account. Accounts and Budgets MUST be
  accepted by either name or ID.
- **FR-011**: The console script MUST determine the application's address from a
  command-line option, falling back to an environment variable, falling back to a
  documented default.
- **FR-012**: On success the console script MUST report the created Transaction's ID and
  exit with status zero.
- **FR-013**: On validation failure the console script MUST print the per-field errors
  returned by the application and exit with a non-zero status.
- **FR-014**: On a transport or unexpected-response failure the console script MUST print
  a comprehensible error and exit with a non-zero status, without an unhandled traceback.
- **FR-015**: The console script MUST support a verbose/debug output option consistent
  with the project's other console scripts.
- **FR-016**: Documentation MUST be updated in the same change: the HTTP API reference
  MUST describe name-or-ID acceptance and the resolution rule for every affected field,
  and the new console script MUST be documented alongside the project's other scripts.
- **FR-017**: Fields the HTTP API reference already documents as optional MUST actually
  be optional. *(Added during implementation. `notes` and `sales_tax` were documented as
  optional but returned a 500 when genuinely omitted — the reference said so of `notes`
  in as many words. The console script hit this immediately, and no external caller has
  reason to send an empty string for a field it does not use. Sending either value
  behaves exactly as before.)*

### Key Entities

- **Account**: A financial account. Has a unique name and a numeric ID; either may now
  identify it in a Transaction-creation request. Only credit accounts may be named as the
  target of a credit card payment.
- **Budget**: A budget category. Has a unique name, a numeric ID, and an active/inactive
  state. Either name or ID may now identify it in a Transaction's budget allocations.
- **Transaction**: The record being created, carrying a date, amount, description, notes,
  sales tax, an Account, one or more Budget allocations summing to its amount, and
  optionally the credit Account it pays.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Transaction can be created from a single command-line invocation that
  mentions no numeric database IDs at all.
- **SC-002**: Every field that today accepts an Account or Budget ID on the
  Transaction-creation endpoint also accepts the corresponding name — three fields,
  covered by tests.
- **SC-003**: Every existing automated test that exercises Transaction creation by ID —
  unit and acceptance, including the web UI's own form submissions — passes unchanged.
- **SC-004**: An unresolvable Account or Budget name produces an error message that names
  the offending value, and leaves the database unchanged; verified by test.
- **SC-005**: An operator can go from a fresh checkout to a created Transaction using only
  the published documentation, with no reading of source code required.

## Assumptions

- Account names and Budget names are unique in the database (enforced by unique indexes),
  so a name identifies at most one record.
- Case-insensitive, whitespace-stripped exact matching is the right default: it is
  forgiving of how a name is typed at a shell prompt without introducing the ambiguity of
  partial or fuzzy matching. Fuzzy or prefix matching is out of scope.
- The income-budget display suffix "(income)" is a presentation detail of the web UI and
  is **not** part of a Budget's name; callers must use the stored name. This is documented
  rather than special-cased.
- Extending the existing `POST /forms/transaction` handler is preferable to adding a
  parallel endpoint: the issue permits either, and one endpoint means one set of
  validation rules to keep correct. The existing endpoint's request and response shapes
  are already documented and must remain backward compatible.
- The application has no authentication (it is documented as localhost-only), so the
  console script needs no credential handling.
- No database schema change is required; this feature adds no models and no migration.
- The follow-on described in issue #322 — detecting a closed pay period whose credit card
  charges have no corresponding payment — is explicitly **out of scope** for this feature,
  as is any change to how the negating offset transaction (#210) is calculated. This
  feature delivers the building block those will use.
