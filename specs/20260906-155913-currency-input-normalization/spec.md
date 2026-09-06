# Feature Specification: Currency Value Input Normalization

**Feature Branch**: `robot-army/issue-323-currency-value-input-normalization`

**Created**: 2026-09-06

**Status**: Draft

**Input**: GitHub issue [jantman/biweeklybudget#323](https://github.com/jantman/biweeklybudget/issues/323) — "Currency Value Input Normalization"

> Right now, inputting a currency value in the UI (such as the Amount and Sales Tax
> fields in the new transaction form) results in a 500 Internal Server Error if the
> value includes commas as separators, such as `1,234.56`.
>
> Also, many of the currency value inputs in the UI do not accept bare integers without
> an error; i.e. they don't accept `123` but rather require `123.0`.
>
> All currency inputs need to be normalized so that they accept common formatting (i.e.
> bare integers, commas as separators, spaces as separators). This must also take form
> validation into account, and will need actual browser tests to ensure it is
> functional. At this time only US currency formatting is in-scope, but normalization
> should be performed in as few places as possible using specific reused
> functions/methods, so that it can be extended for i18n in the future if needed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entering a thousands-separated amount does not break the application (Priority: P1)

A user adding a transaction types the amount the way it is printed on their receipt —
`1,234.56` — into the Amount field and saves the form. The transaction is created with
the amount 1234.56.

**Why this priority**: This is the reported defect. Today the same action produces a 500
Internal Server Error page with no saved record and no explanation, which is both data
loss (the typed form is gone) and the worst possible failure mode for a financially
sensitive application. Nothing else in this feature matters if this still crashes.

**Independent Test**: Open the Add Transaction modal in a browser, type `1,234.56` into
Amount, save, and confirm the transaction is persisted with amount 1234.56 and no error
is shown. Delivers the entire user-visible value of the issue on its own.

**Acceptance Scenarios**:

1. **Given** the Add Transaction modal is open, **When** the user enters `1,234.56` as
   the Amount and otherwise-valid values for the remaining fields and saves, **Then**
   the transaction is saved with an amount of 1234.56 and the modal reports success.
2. **Given** the Add Transaction modal is open, **When** the user enters `1,234.56` as
   the Amount, **Then** no server error page is produced under any circumstances —
   input that cannot be interpreted produces a field-level validation message, never an
   Internal Server Error.
3. **Given** any currency input in the application, **When** the user enters a value
   containing thousands separators, **Then** the value is interpreted with the
   separators removed.

---

### User Story 2 - Entering a bare integer amount is accepted (Priority: P1)

A user enters a whole-dollar amount as `123` rather than `123.0` and the form accepts
it.

**Why this priority**: Second half of the reported defect, and the far more common daily
annoyance — whole-dollar amounts are typical. It is independently valuable and
independently testable, and shares the same normalization machinery as Story 1.

**Independent Test**: In a browser, enter `123` into each affected currency field and
confirm the value saves rather than producing "Invalid float value" / "Invalid Decimal
value" style validation errors.

**Acceptance Scenarios**:

1. **Given** the Add/Edit Fuel Fill form, **When** the user enters `123` for Total Cost,
   **Then** the value is accepted and stored as 123.00 without a validation error.
2. **Given** the BoM Item form, **When** the user enters `40` for Unit Cost, **Then** the
   value is accepted and stored as 40.00.
3. **Given** any currency input in the application, **When** the user enters a value with
   no decimal point, **Then** it is accepted and interpreted as a whole-unit amount.

---

### User Story 3 - Common incidental formatting is tolerated across every currency input (Priority: P2)

A user pastes or types a currency value that carries the incidental formatting people
actually produce — a leading currency symbol, surrounding or embedded spaces, a leading
`+`, parentheses for a negative — and the application interprets it rather than
rejecting it.

**Why this priority**: This generalizes the fix from the two reported symptoms to the
class of problem, which is what the issue asks for ("accept common formatting"). It is
lower priority than P1 because these forms are less common than the two named ones, but
it is what makes the fix feel finished rather than spot-patched.

**Independent Test**: Feed a table of formatted inputs through a single currency form and
confirm each is interpreted as the expected numeric value.

**Acceptance Scenarios**:

1. **Given** any currency input, **When** the user enters `$1,234.56`, **Then** it is
   interpreted as 1234.56.
2. **Given** any currency input, **When** the user enters ` 1 234.56 ` (spaces as
   separators, surrounding whitespace), **Then** it is interpreted as 1234.56.
3. **Given** any currency input, **When** the user enters `-1,234.56`, **Then** it is
   interpreted as -1234.56.
4. **Given** any currency input, **When** the user enters `(1,234.56)`, **Then** it is
   interpreted as -1234.56.

---

### User Story 4 - Malformed input is rejected clearly, not silently mangled (Priority: P1)

A user enters something that is not a currency value — `abc`, `1.2.3`, `1,23.456,7`, or
an empty string in a required field — and receives a specific, field-level validation
message telling them the value is not a valid amount. No value is guessed at and no
record is saved.

**Why this priority**: Equal in priority to the acceptance stories. A normalization
routine that is too permissive is worse than the current bug: this application computes
the author's real finances, and silently reading `1.2.3` as `1.2` would corrupt records
in a way no error message would ever surface. Rejection behavior must ship with
acceptance behavior.

**Independent Test**: Enter each malformed value into a currency field, save, and confirm
a field-level error is displayed, the record is not saved, and no server error occurs.

**Acceptance Scenarios**:

1. **Given** the Add Transaction modal, **When** the user enters `abc` as the Amount and
   saves, **Then** a validation error is shown against the Amount field and no
   transaction is created.
2. **Given** the Add Transaction modal, **When** the user enters `1.2.3` as the Amount and
   saves, **Then** a validation error is shown against the Amount field and no
   transaction is created.
3. **Given** any currency input, **When** the user enters a value the system cannot
   interpret, **Then** the response is a validation message naming the field, never a
   500 Internal Server Error and never a silently altered amount.

---

### User Story 5 - Client-side feedback agrees with what the server will accept (Priority: P2)

A user entering a split transaction sees the running "sum of budget allocations must
equal transaction amount" check treat `1,234.56` and `1234.56` identically, so the Save
button is not disabled for a value the server would have accepted.

**Why this priority**: Without this, the P1 fixes are unreachable in the split-transaction
flow — in-browser validation blocks submission before the server ever sees the value. It
is P2 rather than P1 only because it affects one flow rather than every form.

**Independent Test**: In a browser, open the Add Transaction modal, check "Budget Split?",
enter `1,234.56` as the Amount and matching separator-formatted allocations, and confirm
the Save button stays enabled and the transaction saves.

**Acceptance Scenarios**:

1. **Given** a split transaction with Amount `1,234.56` and a single allocation of
   `1,234.56`, **When** the allocation field loses focus, **Then** no mismatch error is
   shown and Save remains enabled.
2. **Given** a split transaction with Amount `1,234.56`, **When** a budget row's amount
   is auto-filled with the remainder, **Then** the auto-filled figure reflects the
   normalized amount rather than a truncated one.

---

### Edge Cases

- **Empty and whitespace-only values**: A currency field that is optional (for example
  Sales Tax) and left blank continues to behave as it does today — treated as zero or
  omitted, per the existing behavior of that field. A required currency field left blank
  produces its existing "cannot be empty" style error, not a parse error.
- **Value that is only a currency symbol** (`$`, `$ `): rejected as not a valid amount.
- **Separators in impossible positions** (`1,23,4.56`, `,123`, `1,234,`): the system must
  decide deterministically and document the decision; the safe default is rejection,
  since a user who typed this cannot be assumed to have meant any particular number.
- **More than two decimal places** (`1.23456`): accepted at the precision the underlying
  field already supports; normalization does not add rounding behavior that does not
  exist today.
- **Very large values**: values beyond the precision the storage supports fail with a
  validation error rather than being silently truncated.
- **Negative zero and `-0.00`**: treated as zero, so "amount cannot be zero" checks still
  fire.
- **Values arriving from a non-browser client**: the API endpoints accept the same
  formatted values as the browser forms, because normalization happens where the value is
  validated, not in the browser alone.
- **Fields that are numeric but not currency** (fuel gallons, reported MPG): these share
  the same validation helper as currency fields and today reject bare integers for the
  same reason. They must not regress, and it is acceptable for them to gain the same
  tolerance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a single, reusable normalization routine on the
  server that converts a user-supplied currency string into an exact decimal value, and
  every server-side currency field MUST obtain its value through that routine rather than
  converting the raw string itself.
- **FR-002**: The system MUST provide a corresponding single, reusable normalization
  routine in the browser, and every in-browser currency check MUST use it, so that
  client-side and server-side interpretation of a given string cannot diverge.
- **FR-003**: Normalization MUST accept, for US formatting: bare integers (`123`),
  decimal values (`123.45`), comma thousands separators (`1,234.56`), space thousands
  separators (`1 234.56`), a leading or trailing currency symbol, leading and trailing
  whitespace, an explicit leading `+` or `-` sign, and parentheses denoting a negative
  value.
- **FR-004**: Normalization MUST reject any value it cannot interpret unambiguously, and
  MUST signal rejection to its caller distinguishably from a successfully parsed value —
  it MUST NOT return a guessed number, a zero, or a partially-parsed prefix.
- **FR-005**: Every currency form field in the application MUST validate its input before
  any conversion is attempted, such that a malformed value produces a field-level
  validation error in the form response and never an unhandled server error.
- **FR-006**: Validation MUST NOT reject a value merely because its textual form differs
  from the canonical rendering of its numeric value; in particular a whole-number entry
  MUST be accepted.
- **FR-007**: Normalized values MUST be carried through to storage as exact decimal
  amounts, with no loss of cents and no binary-floating-point rounding introduced by the
  normalization step itself.
- **FR-008**: The normalization behavior MUST be defined in terms of a single, replaceable
  set of locale conventions (decimal separator, grouping separators, currency symbol,
  negative forms), so that support for a second locale is a matter of supplying different
  conventions rather than changing every call site.
- **FR-009**: The following currency inputs MUST all accept normalized input: Transaction
  amount and sales tax; per-budget split allocation amounts on a transaction; Scheduled
  Transaction amount and sales tax; the pay-period "scheduled to transaction" amount and
  sales tax; the pay-period "skip scheduled transaction" amount; Budget starting balance
  and current balance; Budget transfer amount; Account credit limit, APR and prime rate
  margin; Account transfer amount; Fuel Fill cost per unit and total cost; BoM Item unit
  cost; Credit payoff interest charge; and credit payoff payment-increase and one-time
  payment amounts.
- **FR-010**: Existing accepted input forms MUST continue to be accepted — this feature
  only widens what is accepted; no value that is valid today may become invalid.
- **FR-011**: Behavior MUST be verified by automated browser tests that drive real form
  submissions for the accepting cases and the rejecting cases, in addition to unit tests
  of the normalization routines themselves.
- **FR-012**: User-facing validation messages for a rejected currency value MUST identify
  the offending field and state that the value is not a valid amount, in place of the
  current type-implementation-flavored wording.

### Key Entities

- **Currency input value**: A user-supplied string intended to denote a monetary amount.
  Has a raw form (what was typed) and a normalized form (an exact decimal). May be
  invalid, in which case it has no normalized form.
- **Locale conventions**: The set of rules that determine how a raw form maps to a
  normalized form — decimal separator, grouping separator(s), currency symbol, and the
  accepted ways of writing a negative. Exactly one set (US) is in scope; the structure
  must permit others.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Entering `1,234.56` into any currency field in the application and
  submitting produces either a saved record with the value 1234.56 or a field-level
  validation message — in zero cases an Internal Server Error.
- **SC-002**: Entering a bare whole number into any currency field in the application and
  submitting saves that amount; zero currency fields require a trailing `.0`.
- **SC-003**: 100% of the currency inputs enumerated in FR-009 are covered by an
  automated test that submits a separator-formatted value and asserts the persisted
  result.
- **SC-004**: Every malformed input in the project's agreed rejection set produces a
  field-level validation message and leaves the database unchanged, in 100% of cases.
- **SC-005**: A reviewer can enumerate every place currency strings are converted to
  numbers by finding the callers of one server routine and one browser routine.
- **SC-006**: Adding a second locale's conventions requires no change to any form,
  validator, or view — only the addition of a conventions definition.
- **SC-007**: The full unit and acceptance suites pass with the change in place.

## Assumptions

- Only US English currency conventions are in scope: `.` as the decimal separator, `,`
  and space as grouping separators, `$` as the currency symbol. The existing
  `CURRENCY_SYM` / locale settings remain the source of the displayed symbol.
- The set of currency inputs in FR-009 is the set discoverable in the current UI; if
  implementation reveals additional ones, they are in scope and the list is extended.
- The application's existing per-field semantics are unchanged — which fields are
  required, which default to zero when blank, and which reject zero or negative values
  all stay exactly as they are. This feature changes only how a supplied string is turned
  into a number.
- Fuel Fill gallons and reported MPG are not currency, but they share the numeric
  validation helper whose strictness causes the bare-integer defect; they are treated as
  in scope for the bare-integer fix and must not regress.
- Browser tests use the project's existing Selenium-based acceptance test infrastructure
  and the existing test database fixtures; no new test framework is introduced.
- Values are normalized at validation time on the server, so any non-browser client of
  the form endpoints benefits from the same tolerance without a separate change.
