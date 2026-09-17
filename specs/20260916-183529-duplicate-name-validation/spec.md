# Feature Specification: Duplicate Name Validation on Account and Budget Forms

**Feature Branch**: `robot-army/issue-275-silent-failure-on-duplicate-account-name`

**Created**: 2026-09-16

**Status**: Implemented (all milestones complete; see tasks.md)

**Input**: GitHub issue [#275](https://github.com/jantman/biweeklybudget/issues/275) — "Silent failure on duplicate account name" (labels: bug, robot-army). Originally reported against 1.1.1 in a comment on issue #270 as "if you name an account with identical then fails silently"; re-checked against master at 1.6.0, where the failure is no longer silent but still surfaces a raw database error string to the user instead of a field-level validation message.

## Problem

Account names and Budget names are required by the database to be unique. Nothing in either form checks that before saving, so the uniqueness rule is only discovered when the database rejects the save. The user is then shown the database's own error text, which names internal tables, columns and constraints and does not tell them which field is at fault or what to do about it. The original report described the save failing with no feedback at all; whether that older behaviour still reproduces has not been confirmed and must be checked before it is assumed fixed.

## Observed behaviour before the fix

*Recorded at milestone M1 on 2026-09-16, satisfying FR-009 and User Story 4. Observed
in Chrome against the application running at `flask run` on the acceptance fixture
data, submitting the name `BankOne` — already held by account ID 1 — through the
**Add Account** modal.*

**The original "silent failure" does not reproduce.** The submission fails loudly. The
issue's 2026-09-05 re-check was correct, and the 1.1.1 report is not the behaviour of
current code. The gate in User Story 4 is therefore cleared and the scope in this
spec stands.

What the user actually sees is a single red `Server Error:` banner at the top of the
still-open modal, containing — verbatim, and in full:

- the driver exception and MySQL error code: `(pymysql.err.IntegrityError) (1062,
  "Duplicate entry 'BankOne' for key 'ix_accounts_name'")`
- the **entire `INSERT` statement**, naming the `accounts` table and all eighteen of
  its columns
- the **complete set of bound parameters**, including every value the user typed
- a link to the SQLAlchemy error documentation

That is roughly 1,100 characters of internal detail where a sentence belongs, and it
is materially worse than the issue described: the issue anticipated "a raw
SQLAlchemy/pymysql `IntegrityError` string", but the SQL statement and the parameter
dump come with it.

Three further details were recorded, each of which the fix should change or preserve
deliberately:

1. **Nothing marks the Name field.** The message renders through the `error_message`
   branch, not the `errors` branch, so the Name input has no error styling and no
   message beneath it. A user reading the banner has to find `'name': 'BankOne'`
   inside the parameter dump to learn which field was at fault.
2. **No account is created**, and the other values the user entered remain in the
   open modal. FR-006 therefore describes behaviour that must be *preserved*, not
   introduced.
3. **The session is not left broken.** Correcting the name in the same modal and
   re-submitting succeeds immediately, with no page reload. The issue's suggestion
   that the change "avoids leaving the session in a broken post-`IntegrityError`
   state" is not a defect that reproduces — the scoped session recovers on its own.
   The one lasting trace is that the failed `INSERT` consumes an `AUTO_INCREMENT`
   value: after the rejected `BankOne` attempt, the corrected save was assigned ID 8
   rather than 7. Validating before the write avoids that, but it is a tidiness point,
   not the reason for the change.

Server side, `FormHandlerView.post()` logs the submission at `WARNING` with a full
traceback — correct for a genuine failure, noisy for a user typo, and another small
argument for catching this in `validate()`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Naming a new account the same as an existing one (Priority: P1)

A user opens the Add Account modal, fills it in, and unknowingly types a name that another account already uses. Instead of a database error banner, the name field itself is flagged with a plain-language message saying that name is already taken. The user corrects the name in place — the rest of what they typed is still there — and saves successfully.

**Why this priority**: This is the reported defect, and account creation is the entry point to everything else in the application. A confusing failure here blocks a user from getting started.

**Independent Test**: Open the Add Account modal in a browser, enter the name of an existing account, submit, and confirm a message appears beneath the Name field rather than as a server-error banner; then change the name and confirm the save succeeds.

**Acceptance Scenarios**:

1. **Given** an account named "BankOne" exists, **When** the user submits the Add Account form with the name "BankOne", **Then** a validation message is shown against the Name field stating the name is already in use, no new account is created, and the values the user entered in the other fields are preserved in the still-open form.
2. **Given** an account named "BankOne" exists, **When** the user submits the Add Account form with the name "BankOne", **Then** no raw database or server error text is shown anywhere in the form.
3. **Given** the user has just seen the duplicate-name message, **When** they change the name to one not in use and submit again, **Then** the account is created and the usual success confirmation is shown.

---

### User Story 2 - Renaming an existing account onto another account's name (Priority: P1)

A user edits an existing account and changes its name to one that a different account already uses. The same field-level message appears. Re-saving an account without changing its name — so its name still matches its own record — saves normally.

**Why this priority**: Same defect, reached through the edit path, which is the more common day-to-day operation. Getting this wrong in the other direction (rejecting an account's own name) would break every account edit, so it must be covered alongside the create path.

**Independent Test**: Edit an existing account, set its name to another account's name, submit, and confirm the field-level message; separately, edit an account and save it with its name unchanged and confirm it saves.

**Acceptance Scenarios**:

1. **Given** accounts "BankOne" and "BankTwo" exist, **When** the user edits "BankTwo" and submits it with the name "BankOne", **Then** a validation message is shown against the Name field and neither account is changed.
2. **Given** an account "BankOne" exists, **When** the user edits it and submits it with the name still "BankOne" and some other field changed, **Then** the account saves successfully with no duplicate-name message.

---

### User Story 3 - Duplicate budget names (Priority: P2)

The same protection applies to the Budget form: naming a new budget after an existing one, or renaming a budget onto another budget's name, produces a message against the Name field rather than a database error.

**Why this priority**: The same defect exists on the only other form in the application backed by a uniquely-named record. It is lower priority than the account forms only because it was not the reported case, but leaving it unfixed would mean the application handles the identical mistake two different ways.

**Independent Test**: Open the Add Budget modal, enter the name of an existing budget, submit, and confirm the field-level message; then edit an existing budget and save with its name unchanged to confirm it still saves.

**Acceptance Scenarios**:

1. **Given** a budget named "Periodic1" exists, **When** the user submits the Add Budget form with the name "Periodic1", **Then** a validation message is shown against the Name field, no new budget is created, and no raw database error text appears.
2. **Given** budgets "Periodic1" and "Periodic2" exist, **When** the user edits "Periodic2" and submits it with the name "Periodic1", **Then** a validation message is shown against the Name field and neither budget is changed.
3. **Given** a budget "Periodic1" exists, **When** the user edits it and saves with its name unchanged, **Then** the budget saves successfully.

---

### User Story 4 - Confirming the historical "silent failure" report (Priority: P3)

Before the fix is written, the behaviour described in the original report is reproduced in a real browser against the current code so that the record says what actually happens today, rather than what reading the code suggests happens.

**Why this priority**: It does not change what a user gets, so it cannot be P1 or P2. It matters because the original report is unexplained: if a submission really can fail with no feedback at all, the validation message added by the other stories would never be seen either, and the fix would be aimed at the wrong thing.

**Independent Test**: Drive the running application in a browser, submit a duplicate account name, and record what the user sees.

**Acceptance Scenarios**:

1. **Given** the application running against a populated database, **When** a duplicate account name is submitted through the Add Account modal in a browser, **Then** the observed outcome is recorded in this specification — either the "Server Error" banner described in the issue, or genuinely no feedback.
2. **Given** that observation shows the submission fails with no feedback at all, **Then** that finding is recorded as a departure requiring the scope to be revisited before the fix is written, per the constitution's rule on escalating instead of guessing.

---

### Edge Cases

- **Names differing only by surrounding whitespace**: the form already trims the name before saving, so " BankOne " and "BankOne" become the same stored name. The duplicate check must compare the trimmed name, or a user could slip a colliding name past validation and hit the database error the fix is meant to remove.
- **Names differing only by letter case**: the database's own comparison decides whether "bankone" and "BankOne" collide. The check must reach the same verdict the database would, so that validation never passes something the save then rejects.
- **Empty name**: already rejected by an existing "Name cannot be empty" message; the duplicate check must not add a second, confusing message on top of it.
- **Two other errors at once**: a submission with both a duplicate name and another invalid field shows a message against each field, not just the first.
- **A concurrent save creating the same name between validation and write**: the database constraint remains the final guard, so such a submission still fails with the generic server error. This is accepted; the change reduces how often an ordinary user meets that error, it does not remove the constraint.
- **Records with unique names but no form**: reconcile rules have uniquely-named records but no form in the application, so there is nothing for a user to submit and nothing to validate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Account form MUST reject a submission whose name is already used by a different account, and MUST report it as a validation message attached to the Name field.
- **FR-002**: The Account form MUST accept a submission whose name matches only the account being edited, so that re-saving an account without renaming it succeeds.
- **FR-003**: The Budget form MUST reject a submission whose name is already used by a different budget, and MUST report it as a validation message attached to the Name field.
- **FR-004**: The Budget form MUST accept a submission whose name matches only the budget being edited.
- **FR-005**: The duplicate-name messages MUST name the conflict in plain language and MUST NOT contain database error text, table or column names, constraint names, or stack traces.
- **FR-006**: A rejected submission MUST leave the record store unchanged and MUST leave the user's form open with their entered values intact, so the name can be corrected and resubmitted without re-entering anything.
- **FR-007**: The duplicate check MUST compare names the same way the stored record does — after the same trimming the save applies, and reaching the same verdict on letter case that the record store would — so that a submission that passes validation is not then rejected by the store.
- **FR-008**: Where a submission has a duplicate name and other invalid fields, the response MUST report all of them together, one message per offending field.
- **FR-009**: The behaviour of a duplicate account-name submission on the current code MUST be observed in a real browser and recorded in this specification before the fix is implemented.
- **FR-010**: Automated acceptance coverage MUST exist for a duplicate account name and a duplicate budget name, on both the create and the rename path, and for the case where a record is re-saved under its own name.

### Key Entities

- **Account**: a financial account the user tracks. Has a name that must be unique across all accounts, and which the user sets through the account form.
- **Budget**: a budget category. Has a name that must be unique across all budgets, and which the user sets through the budget form.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user who submits a duplicate account or budget name sees a message identifying the Name field as the problem, in 100% of such submissions, with zero occurrences of database error text.
- **SC-002**: A user who hits a duplicate-name message can correct the name and save successfully without re-entering any other field.
- **SC-003**: Re-saving an existing account or budget without renaming it succeeds in 100% of cases — the new check introduces no regression to ordinary edits.
- **SC-004**: The complete unit and acceptance suites pass, with new acceptance coverage exercising every path named in FR-010.
- **SC-005**: The behaviour observed in the pre-fix browser check is written into this specification, so the original report is either explained or explicitly recorded as not reproducing.

## Assumptions

- The uniqueness rule itself is correct and stays as it is; this change is about how a violation is reported, not about allowing duplicate names.
- The database constraint remains the final guard. Validation is a better-behaved first line of defence, not a replacement for it, and the rare race between the two is out of scope.
- Both forms already return per-field validation messages for other problems, and the duplicate-name message uses that same existing mechanism, so no new user-interface pattern is introduced.
- Reconcile rules are out of scope: their names are unique in the store but no form in the application creates or edits them, so a user cannot submit a duplicate.
- No change to stored data or its structure is needed, so no data migration is involved.
- Existing accounts or budgets with names that already collide cannot exist, because the store has always enforced uniqueness; the change needs no clean-up of historical data.
