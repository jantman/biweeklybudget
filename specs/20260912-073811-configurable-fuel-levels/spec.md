# Feature Specification: Configurable Fuel Levels

**Feature Branch**: `robot-army/issue-208-fuel-log-configurable-fuel-levels`

**Created**: 2026-09-12

**Status**: Complete

**Input**: GitHub issue [#208](https://github.com/jantman/biweeklybudget/issues/208) — "Fuel Log - Configurable fuel levels"

## Context

When a fuel fill is logged, the Add Fuel Fill form asks for the starting and ending fuel
level. Both are chosen from a fixed list of eleven options, `0/10` through `10/10`. Each
option stands for a percentage of a full tank (0, 10, 20 … 100), and that percentage is
what gets recorded for the fill.

Most fuel gauges are not marked in tenths. Common markings are eighths (E, 1/8, 1/4 …
F), quarters, or a bar display with some other number of segments. The owner of such a
car has to convert the gauge reading to the nearest tenth every time they log a fill, and
the result is inaccurate. The issue asks for the list of levels to be configurable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Log a fill using my own gauge's markings (Priority: P1)

The operator's car has a gauge marked E, 1/4, 1/2, 3/4, F. They configure the application
with those five levels, each paired with the percentage of a full tank it represents. When
they next open Add Fuel Fill, both fuel level selects show exactly those five choices, in
the configured order. The starting level defaults to the emptiest level and the ending
level defaults to the fullest. They pick what the gauge showed and save. The fill is
recorded with the percentage paired with each chosen label.

**Why this priority**: This is the whole of the issue.

**Independent Test**: Configure a non-default list of levels, open Add Fuel Fill, check
the options and defaults in both selects, then save a fill and check the recorded levels.

**Acceptance Scenarios**:

1. **Given** the levels are configured as E=0, 1/4=25, 1/2=50, 3/4=75, F=100, **When** the
   Add Fuel Fill form opens, **Then** both the starting and ending level selects list
   exactly E, 1/4, 1/2, 3/4, F in that order, and no other options.
2. **Given** the same configuration, **When** the form opens, **Then** the starting level
   is preselected as E (the lowest percentage) and the ending level as F (the highest
   percentage).
3. **Given** the same configuration, **When** the operator chooses starting level 1/4 and
   ending level F and saves, **Then** the fill is recorded with a starting level of 25 and
   an ending level of 100.

---

### User Story 2 - Nothing changes for an operator who configures nothing (Priority: P1)

The operator upgrades and does not configure fuel levels. The Add Fuel Fill form behaves
exactly as it did before: eleven options `0/10` to `10/10` meaning 0 to 100 percent,
starting level preselected as `0/10`, ending level preselected as `10/10`.

**Why this priority**: Equally essential. An upgrade must not change the form, or the
meaning of what it records, for anyone who has not asked for a change.

**Independent Test**: With no fuel level configuration, open Add Fuel Fill and compare
the options, their recorded values and the defaults with the current behaviour.

**Acceptance Scenarios**:

1. **Given** no fuel level configuration, **When** the form opens, **Then** both selects
   list `0/10`, `1/10` … `10/10`, recording 0, 10 … 100, with `0/10` preselected for the
   starting level and `10/10` for the ending level.

---

### User Story 3 - A mistake in the configuration is reported, not silently used (Priority: P2)

The operator sets the levels through an environment variable and makes a typo, such as a
missing percentage or a percentage of 150. The application refuses to start and prints a
message naming the fuel level setting and what is wrong with it. It does not start with a
broken or partial list.

**Why this priority**: A malformed list would otherwise produce a form that records wrong
numbers into the fuel log, or no usable form at all. Failing at startup is how the other
settings already behave, and it is cheaper to notice.

**Independent Test**: Start the application with each kind of invalid value and confirm it
exits with an error naming the setting.

**Acceptance Scenarios**:

1. **Given** a fuel level list with a percentage outside 0–100, a non-integer percentage,
   an empty label, a duplicated label, a duplicated percentage, or fewer than two levels,
   **When** the application starts, **Then** it exits with an error message that names
   the fuel level setting and describes the problem.

### Edge Cases

- **Fractions that are not whole percentages**, such as 1/8 (12.5%): percentages are
  whole numbers, so the operator chooses the rounding (for example 1/8=13). The fuel log
  has always stored whole percentages, so this loses nothing that was stored before.
- **Levels configured out of order**: they are shown in the order configured. The defaults
  still use the lowest and highest percentages, wherever those appear in the list.
- **Existing fills logged before the list was changed**: they keep their recorded
  percentages, and the fuel log table and charts keep showing them as percentages. Nothing
  is converted.
- **Labels containing characters with meaning in a web page** (such as `<` or `&`): they
  are displayed as the literal text configured.
- **Fills submitted directly to the HTTP API**: unchanged. The API still accepts integer
  levels, and does not require them to be one of the configured values, as today.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The operator MUST be able to configure the fuel levels offered on the Add
  Fuel Fill form as an ordered list, each entry pairing a display label with the whole
  percentage of a full tank (0–100) it represents.
- **FR-002**: The list MUST be configurable in the settings module and through an
  environment variable, like the other Fuel Log settings.
- **FR-003**: When no list is configured, the default MUST reproduce the current options
  exactly: labels `0/10` through `10/10` for 0, 10 … 100 percent.
- **FR-004**: The starting and ending fuel level selects MUST both offer exactly the
  configured levels, in the configured order.
- **FR-005**: The starting level MUST default to the configured level with the lowest
  percentage, and the ending level to the level with the highest percentage.
- **FR-006**: Saving a fill MUST record, for each of the starting and ending levels, the
  percentage paired with the chosen label. The stored meaning of a level (a percentage of
  a full tank) MUST NOT change.
- **FR-007**: The application MUST refuse to start, with an error naming the fuel level
  setting, if the configured list has fewer than two levels, an empty or duplicated label,
  a duplicated percentage, or a percentage that is not a whole number from 0 to 100.
- **FR-008**: The new setting MUST be documented where the other Fuel Log settings are
  documented, including the environment variable format and an example for a gauge that
  is not marked in tenths.

### Key Entities

- **Fuel level option**: a label as marked on the operator's gauge (for example `1/4` or
  `E`), paired with the whole percentage of a full tank that the label represents. The
  configured list of these is a setting. Only the percentage is stored with a fill, as
  today, so no stored data changes shape.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator whose gauge is marked in eighths, quarters or any other division
  can log a fill by picking the label that matches the gauge, with no mental conversion to
  tenths.
- **SC-002**: With no configuration, 100% of the Add Fuel Fill form's level options,
  recorded values and defaults are identical to those before the change.
- **SC-003**: 100% of the invalid configurations listed in FR-007 are rejected at startup
  with a message that names the setting; none produce a form.
- **SC-004**: Every fill logged before the change still shows the same levels in the fuel
  log afterwards.

## Assumptions

- **One list for the whole application, not per vehicle.** The issue asks for "a
  configurable list of values", and the other Fuel Log settings (units and abbreviations)
  are global. A household whose vehicles have differently marked gauges would want a list
  per vehicle, but that needs a schema change and a vehicle-editing UI change. It is out
  of scope here and can be added later without undoing this work.
- **Levels stay stored as percentages.** Keeping the stored value a percentage of a full
  tank means existing data, the fuel log table and the charts keep their meaning, and no
  migration is needed. The alternative of storing the label would make fills logged under
  different lists incomparable.
- **The fuel log table keeps showing percentages.** The issue is about input. Showing
  labels in the table would make old fills, logged under a different list, display
  differently from new ones.
- **The HTTP API is unchanged.** It already accepts any integer level. Restricting it to
  the configured list would break existing API callers and is not asked for.
