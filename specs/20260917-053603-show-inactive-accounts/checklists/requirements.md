# Specification Quality Checklist: Show Inactive Accounts So They Can Be Re-Activated

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-17
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`.
- **Validation pass 1** found two issues, both fixed before this checklist was marked
  complete:
  - FR-003 originally named the CSS class `tr.inactive` directly (implementation detail).
    Rewritten to name the application's existing inactive-row styling by behaviour; the
    class name is retained only in Assumptions, where it records how the issue's phrase
    "the way inactive scheduled transactions are handled" was interpreted.
  - The Scope assumption originally said only "the Accounts page", which left the reader
    to guess whether the dashboard was included. It now states the exclusions explicitly
    and is backed by FR-009.
- **Scope decision (confirmed with the maintainer, 2026-09-17)**: the issue says inactive
  accounts should "still be shown in the UI". This was put to the maintainer as a choice
  between the Accounts page alone and the Accounts page plus the dashboard. The maintainer
  chose **the Accounts page only**; every other financial surface keeps excluding inactive
  accounts, as FR-009 requires. Scope is settled; no open questions remain.
