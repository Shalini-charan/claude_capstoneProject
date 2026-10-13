---
title: Design Review - slugify utility (CLAUDE-4)
ticket: CLAUDE-4
created: 2026-10-13T16:11:00+05:30
created_by: design-review-agent
hitl_status: approved
approved_by: Shalini Srinivasan
approved_on: 2026-10-13T16:11:19+05:30
revision: 1
---

# Design Review

Reviewed: `docs/claude4/architecture.md` against `docs/claude4/requirements.md` (approved). Scope is one pure function plus tests, so the review is kept proportionate.

## Open HIGH/CRITICAL risks

**None.** There are no open HIGH or CRITICAL risks, so Stage 4 (implementation plan) is not blocked by this review. Stage 3 still needs developer approval.

## Import convention check

The architecture says tests must import `slugify` "the same way `tests/test_sync_docs.py` imports `sync_docs`", for example with a `sys.path` insert of `src`. Verified against the repo:

- `tests/test_sync_docs.py` line 17 has `sys.path.insert(0, str(Path(__file__).parent.parent / "src"))`, followed by `from sync_docs import (...)`.
- `src/` and `tests/` have no `__init__.py`, so a package-style import (`from src.slugify import ...`) would not match the convention.
- The claim is **accurate**. The test should use the same `sys.path.insert` followed by `from slugify import slugify`. This works from the repo root on Windows and POSIX because the path is built from `__file__`, not the current directory.
- The architecture leaves the exact line as an example ("for example"). RISK-02 asks for it to be made explicit.

## Checklist summary

- Correctness: empty input, all-invalid input, non-str input and edge hyphens are all defined. The worked examples and DD-02 ordering are consistent (see RISK-04 for one typo).
- Reliability: a pure function with no I/O or state, so there is no partial-update risk.
- Portability: the explicit ASCII whitespace class avoids Unicode `\s` differences (DD-03). No executables or OS assumptions.
- Security: no shell, file or path handling. Regexes are linear, with no catastrophic backtracking.
- Completeness: FR-1 to FR-14 and NFR-1 to NFR-7 map to the two components. FR-15 is a pipeline step. No requirement is left uncovered, but see RISK-03.

## Risk Register

### RISK-01: Behaviour assumptions A-1 to A-4 are still marked open
**Severity:** MEDIUM
**Component:** `src/slugify.py` (regex classes, `strip`)
**Scenario:** The requirements were approved, but A-1 to A-4 (hyphens kept, edge hyphens stripped, underscores removed, non-ASCII removed) are still labelled "open / pending confirmation". The architecture encodes them. If the developer later disagrees, for example wants `"snake_case"` to give `"snake-case"` rather than `"snakecase"`, the code and tests need rework.
**Mitigation:** The developer confirms A-1 to A-4 when approving this review. The implementation plan lists them as the only behaviours that change if rejected (DD-05 already isolates this to the regexes and the `strip` call). The tests should name each assumption in its test method.
**Status:** OPEN (not HIGH: the change would be a few lines and does not block implementation planning)

### RISK-02: Test import line is described by example only
**Severity:** LOW
**Component:** `tests/test_slugify.py`
**Scenario:** The architecture says "for example a `sys.path` insert". An implementer could instead use `from src.slugify import slugify`. That fails under `python -m unittest discover -s tests` because `src` is not a package and the repo root is not on `sys.path`, so NFR-4 fails.
**Mitigation:** The implementation plan specifies the exact lines, mirroring `tests/test_sync_docs.py`: `sys.path.insert(0, str(Path(__file__).parent.parent / "src"))` then `from slugify import slugify`.
**Status:** OPEN (resolved once the plan states the exact lines)

### RISK-03: No performance test for NFR-2, and AC mapping is implicit
**Severity:** LOW
**Component:** `tests/test_slugify.py`
**Scenario:** NFR-2 (10,000 characters under 50 ms) has no named verification. FR-14 refers to AC 1 to 6, but the ACs are not reproduced in the requirements, so coverage cannot be checked from the docs alone.
**Mitigation:** Add one test that slugifies a 10,000-character string and asserts completion in under 50 ms, with a generous margin or a documented tolerance to avoid flakiness on slow CI. Add a short AC-to-test table to the implementation plan.
**Status:** OPEN

### RISK-04: Typo in DD-02 worked example
**Severity:** LOW
**Component:** `docs/claude4/architecture.md` DD-02
**Scenario:** `"a - ! - b"` after removing `!` is `"a -  - b"` (one space before the first hyphen), but the document shows `"a  -  - b"`. The final result `"a-b"` is correct, but a test author copying the intermediate value could write a wrong expectation.
**Mitigation:** Correct the intermediate string in the architecture, or tell the implementer to assert only the final output.
**Status:** OPEN

### RISK-05: Module name `slugify` may shadow a third-party package
**Severity:** LOW
**Component:** `src/slugify.py`
**Scenario:** If `python-slugify` (import name `slugify`) is installed, the `sys.path.insert(0, ...)` makes the local module win inside the tests, which is the intended result. Other code that imports `slugify` without that path insert would get the third-party one.
**Mitigation:** None needed for this ticket. NFR-3 forbids third-party dependencies, so no such package is expected.
**Status:** ACCEPTED. Rationale: the repo has no third-party dependencies, `src/` is not a package, and the existing convention puts `src` first on the path, so the local module takes priority.

### RISK-06: Known limitations KL-1 to KL-4
**Severity:** LOW
**Component:** `src/slugify.py`
**Scenario:** Non-ASCII titles lose letters (`"Café"` gives `"caf"`), fully non-ASCII titles give `""`, and different titles can produce the same slug. Callers using the slug as a file name or URL key could get empty or colliding values.
**Mitigation:** None in this ticket. Callers must handle an empty result.
**Status:** ACCEPTED. Rationale: transliteration (C-3), maximum length and uniqueness (C-4) are explicitly out of scope, and C-5 limits the ticket to the single function.

## Status summary

| Risk | Severity | Status |
|------|----------|--------|
| RISK-01 | MEDIUM | OPEN |
| RISK-02 | LOW | OPEN |
| RISK-03 | LOW | OPEN |
| RISK-04 | LOW | OPEN |
| RISK-05 | LOW | ACCEPTED |
| RISK-06 | LOW | ACCEPTED |

No risk is marked FIXED or mitigated in the documents yet. The open items are all addressable in the implementation plan. Open HIGH/CRITICAL count: 0.
