---
title: Requirements - slugify utility (CLAUDE-4)
ticket: CLAUDE-4
created: 2026-10-13T16:05:00+05:30
created_by: requirements-agent
hitl_status: approved
approved_by: Shalini Srinivasan
approved_on: 2026-10-13T16:08:38+05:30
revision: 1
---

# Requirements

Ticket: CLAUDE-4 (Task, Medium, label: orchestrator-validation). Story: as a developer, I want a `slugify(text)` utility that converts a string into a URL-safe slug, so that I can build clean URLs and file names from titles.

## Functional Requirements
| ID | Requirement |
|----|-------------|
| FR-1 | The system shall provide a function `slugify(text)` that accepts a string and returns a string. |
| FR-2 | `slugify("Hello World")` shall return `"hello-world"`. |
| FR-3 | `slugify` shall remove leading and trailing whitespace from the input. |
| FR-4 | `slugify` shall convert all letters in the result to lowercase. |
| FR-5 | `slugify` shall remove every character that is not a letter, digit, space or hyphen. |
| FR-6 | `slugify("Hello, World!")` shall return `"hello-world"`. |
| FR-7 | `slugify` shall replace each run of one or more spaces with a single hyphen. |
| FR-8 | `slugify` shall collapse each run of consecutive hyphens into a single hyphen. |
| FR-9 | `slugify` shall collapse a mixed run of spaces and hyphens into a single hyphen. |
| FR-10 | `slugify` shall return an empty string when the input is an empty string. |
| FR-11 | `slugify` shall return an empty string when the input contains no valid characters (for example `"!!!"`). |
| FR-12 | `slugify` shall raise a `TypeError` when the input is not a string (for example `None`, an integer or a list). |
| FR-13 | `slugify` shall remove leading and trailing hyphens from the result. |
| FR-14 | The repository shall include unit tests that cover every acceptance criterion (AC 1 to 6) of CLAUDE-4. |
| FR-15 | The change shall be delivered through an opened pull request. |

## Non-Functional Requirements
| ID | Requirement |
|----|-------------|
| NFR-1 | `slugify` shall be a pure function: the same input shall always give the same output, with no side effects and no I/O. |
| NFR-2 | `slugify` shall process a 10,000-character input in under 50 ms on a standard developer machine. |
| NFR-3 | `slugify` shall depend only on the Python standard library. |
| NFR-4 | The unit tests shall run with `python -m unittest discover -s tests -v` and all shall pass with zero failures and zero errors. |
| NFR-5 | New unit tests shall be added in a new test file and shall not modify, remove or weaken the existing tests in `tests/test_sync_docs.py`. |
| NFR-6 | The function shall include a docstring that states its behaviour and the `TypeError` condition. |
| NFR-7 | The function shall run unchanged on Windows and POSIX platforms. |

## Constraints
| ID | Constraint | Type |
|----|------------|------|
| C-1 | The implementation language is Python, consistent with the existing repository (`src/sync_docs.py`). | FIXED |
| C-2 | Tests use the `unittest` framework and run via `python -m unittest discover -s tests -v`. | FIXED |
| C-3 | Unicode transliteration (for example e-acute to e) is out of scope. | FIXED |
| C-4 | A maximum slug length is out of scope. | FIXED |
| C-5 | The ticket exists to validate the SDLC orchestrator end to end, so the scope stays limited to the `slugify` utility. | FIXED |
| C-6 | Hyphen is a permitted character, because AC 4 requires hyphen runs to collapse rather than be removed. (A-1 below) | ASSUMED |
| C-7 | Leading and trailing hyphens in the final result are stripped (for example `"-Hello-"` gives `"hello"`). | ASSUMED |
| C-8 | "Letters" means ASCII letters `a-z` and `A-Z`, since transliteration is out of scope. Non-ASCII letters are treated as invalid characters and removed. | ASSUMED |
| C-9 | The function lives in a new module under `src/` (for example `src/slugify.py`) with tests under `tests/`; the exact location is decided at the architecture stage. | ASSUMED |
| C-10 | "Whitespace" for trimming and collapsing covers space, tab and newline characters; AC 3 names only spaces. | ASSUMED |

## Assumptions and Open Questions

- A-1 (open): AC 3 says characters other than letters, digits and spaces are removed, which read literally would also remove hyphens. AC 4 collapses runs of hyphens, which implies hyphens are kept. This document assumes hyphens are kept (C-6). Please confirm.
- A-2 (open): Should leading and trailing hyphens be stripped from the result (for example `"--Hello--"` gives `"hello"`)? This document assumes yes (C-7). The earlier conflict with FR-13 is resolved in this draft: FR-13 now reads "slugify shall remove leading and trailing hyphens from the result". This remains pending developer confirmation of C-7.
- A-3 (open): Should underscores be kept or removed? Per AC 3 they are not letters, digits or spaces, so they are removed.
- A-4 (open): Should non-ASCII letters (for example accented letters) be removed or kept? This document assumes removed (C-8), consistent with the out-of-scope transliteration.
