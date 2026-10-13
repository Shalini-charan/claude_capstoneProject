---
title: Implementation Plan - slugify utility (CLAUDE-4)
ticket: CLAUDE-4
created: 2026-10-13T16:12:00+05:30
created_by: impl-plan-agent
hitl_status: approved
approved_by: Shalini Srinivasan
approved_on: 2026-10-13T16:16:10+05:30
revision: 1
---

# Implementation Plan

Inputs: `docs/claude4/architecture.md`, `docs/claude4/design-review.md` (approved, 0 open HIGH/CRITICAL), `docs/claude4/requirements.md` (approved). Scope is one pure function plus its tests (C-5), so the plan is kept small.

## Branch and files

- Feature branch: `feature/claude-4-slugify`, based on the branch the work starts from (currently `main`). Stage files by name only. `docs/claude4/` is currently untracked; the docs are committed on this branch alongside the code with `docs:` commits (the developer decides whether to include them in the PR).
- Files touched by implementation and verification (only these two):
  - `src/slugify.py` (new, implementation agent)
  - `tests/test_slugify.py` (new, verify agent)
- Not touched: `src/sync_docs.py`, `tests/test_sync_docs.py` (NFR-5).

## Exact test import lines (RISK-02)

Mirrors `tests/test_sync_docs.py` line 17. Do not use `from src.slugify import ...` (`src` is not a package).

```python
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from slugify import slugify
```

## Risk disposition

The design review marks no risk as FIXED. Open risks are addressed as follows so each has a task.

| Risk | Handling | Task |
|------|----------|------|
| RISK-01 (A-1 to A-4 open, MEDIUM) | Each assumption gets a named test method. If the developer rejects one, only the regexes and `strip` call in `src/slugify.py` and the matching tests change. Confirmation is requested at approval of this plan. | T-03, T-05, T-07 |
| RISK-02 (import line) | Exact lines stated above and used in the test scaffold. | T-04 |
| RISK-03 (NFR-2 test, AC mapping) | AC-to-test table below; timing test included (not waived). | T-08 |
| RISK-04 (DD-02 typo) | Tests assert final outputs only, never the intermediate string. Correct intermediate is `"a -  - b"`. | T-06 |
| RISK-05, RISK-06 | ACCEPTED, no task. | - |

## Tasks

| ID | Phase | Task | Owner | Depends On | Notes |
|----|-------|------|-------|------------|-------|
| T-01 | Scaffold | Create branch `feature/claude-4-slugify` from the starting branch; confirm working tree has no unrelated changes (ask first if it does). | orchestrator | - | Git rules: name, base branch. |
| T-02 | Core | Create `src/slugify.py`: `_INVALID` and `_SEPARATORS` precompiled regexes, `slugify(text: str) -> str` with `isinstance` guard raising `TypeError` naming the received type, pipeline in order remove-invalid, collapse separators to `-`, `strip("-")`, `lower()`. Docstring states behaviour and the `TypeError` condition. Stdlib `re` only. | implementation agent | T-01 | FR-1 to FR-13, NFR-1, 3, 6, 7; DD-02 to DD-06. Never commits. |
| T-03 | Core | Smoke check of T-02 against the worked examples (`"Hello, World!"` gives `"hello-world"`; `"  --A_b\t\nC-- "` gives `"ab-c"`). Run by hand, no file output. | implementation agent | T-02 | Quick sanity before tests are written. |
| T-04 | Tests | Create `tests/test_slugify.py` scaffold: the exact import lines above and `class TestSlugify(unittest.TestCase)` plus `if __name__ == "__main__": unittest.main()`. | verify agent | T-02 | RISK-02. Must pass discovery from repo root. |
| T-05 | Tests | Add AC 1-4 tests (basic conversion, trim and lowercase, punctuation removal, space and hyphen run collapse) and hyphen edge cases. | verify agent | T-04 | See mapping table. |
| T-06 | Tests | Add AC 5-6 tests (empty and all-invalid input, `TypeError` for `None`, int, list, bytes), idempotency, mixed separator removal case `"a - ! - b"` (final output only). | verify agent | T-04 | RISK-04. |
| T-07 | Tests | Add whitespace and character-class tests: tabs and newlines, underscores, non-ASCII letters, non-ASCII whitespace, Kelvin sign. Each method name cites its assumption (A-1 to A-4). | verify agent | T-04 | RISK-01, DD-03, DD-04, DD-05. |
| T-08 | Tests | Add the 10,000-character timing test (NFR-2). | verify agent | T-04 | See NFR-2 below. |
| T-09 | Verify | Run `python -m unittest discover -s tests -v`; report run, passed, failed, skipped exactly as observed. Confirm `tests/test_sync_docs.py` still passes unchanged. Source bugs go back to the implementation agent, never fixed by editing source in the verify stage. | verify agent | T-05, T-06, T-07, T-08 | NFR-4, NFR-5. |
| T-10 | Hardening | Check the diff: only `src/slugify.py` and `tests/test_slugify.py` (plus docs) changed; no token-like strings; no `.mcp.json` staged. | orchestrator | T-09 | Security and pipeline rules. |
| T-11 | Delivery | Commit by file name (`feat: add slugify utility (CLAUDE-4)`, `test: add slugify tests (CLAUDE-4)`), push, open PR against the starting branch, print URL, confirm with `gh pr view`. | orchestrator / PR agent | T-10 | FR-15. |

## Acceptance-criterion-to-test mapping

The requirements do not reproduce the Jira ACs. The mapping below is inferred from FR-2 to FR-14 and A-1 (which cites AC 3 as "remove non letters, digits, spaces" and AC 4 as "collapse hyphen runs"). Confirm the numbering against the CLAUDE-4 ticket during plan approval.

| AC / topic | Requirement | Test method (in `TestSlugify`) | Input to expected output | Task |
|------------|-------------|--------------------------------|--------------------------|------|
| AC1 basic | FR-2 | `test_ac1_basic_conversion` | `"Hello World"` to `"hello-world"` | T-05 |
| AC2 trim, lowercase | FR-3, FR-4 | `test_ac2_trims_and_lowercases` | `"  Hello World  "` to `"hello-world"`; `"ABC"` to `"abc"` | T-05 |
| AC3 remove invalid | FR-5, FR-6 | `test_ac3_removes_special_characters` | `"Hello, World!"` to `"hello-world"`; `"a@b#c"` to `"abc"` | T-05 |
| AC4 collapse | FR-7, FR-8, FR-9 | `test_ac4_collapses_space_and_hyphen_runs` | `"a   b"` to `"a-b"`; `"a---b"` to `"a-b"`; `"a - - b"` to `"a-b"` | T-05 |
| AC5 empty | FR-10, FR-11 | `test_ac5_empty_input`, `test_ac5_all_invalid_input` | `""` to `""`; `"!!!"` to `""`; `"   "` to `""`; `"---"` to `""` | T-06 |
| AC6 type error | FR-12 | `test_ac6_non_string_raises_type_error` | `None`, `123`, `["a"]`, `b"a"` each raise `TypeError` (use `subTest`) | T-06 |
| Hyphen edges (A-1, A-2; RISK-03) | FR-13, C-6, C-7 | `test_a1_a2_hyphen_edges_stripped`, `test_a1_hyphen_kept_inside` | `"-Hello-"` and `"--Hello--"` to `"hello"`; `"well-known"` to `"well-known"`; `"-"` to `""`; `"a-"` to `"a"` | T-05 |
| Idempotency | DD-02 | `test_idempotent` | `slugify(slugify(x)) == slugify(x)` over a list of mixed inputs, including `"  --A_b\t\nC-- "` | T-06 |
| Remove-then-collapse | DD-02 | `test_removal_then_collapse` | `"a - ! - b"` to `"a-b"` (final output only) | T-06 |
| Tabs and newlines | C-10, DD-03 | `test_c10_tab_and_newline_are_separators` | `"a\tb"` to `"a-b"`; `"a\nb"` to `"a-b"`; `"\t a \n"` to `"a"` | T-07 |
| Underscores (A-3) | DD-05 | `test_a3_underscores_removed` | `"snake_case"` to `"snakecase"`; `"a_ b"` to `"a-b"` | T-07 |
| Non-ASCII (A-4) | C-8, DD-04, KL-1, KL-2 | `test_a4_non_ascii_letters_removed`, `test_non_ascii_whitespace_removed`, `test_kelvin_sign_removed` | `"Café"` to `"caf"`; `"日本語"` to `""`; `"a b"` to `"ab"`; `"K"` to `""` | T-07 |
| Output charset | NFR-1, DD-04 | `test_output_matches_charset` | result of mixed inputs matches `^[a-z0-9-]*$` | T-07 |
| NFR-2 timing | NFR-2 | `test_nfr2_10000_chars_under_50ms` | see below | T-08 |

Unicode inputs in tests use `\u` escapes so the file stays ASCII and platform independent.

## NFR-2 timing test (included, not waived)

`test_nfr2_10000_chars_under_50ms` builds a 10,000-character string mixing letters, spaces, hyphens and punctuation, runs `slugify` three times with `time.perf_counter`, and asserts the best of the three is under 0.050 s (best-of-3 reduces CI noise; the algorithm is linear, so the real cost is far below the limit). If it proves flaky on a slow machine, the verify agent reports it rather than loosening it silently; any change to the threshold needs developer approval and a recorded waiver per the pipeline rules.

## Parallel Groups

- T-05, T-06, T-07, T-08 can run in parallel (independent groups of test methods in the same file, all after T-04). Because they edit one file, the verify agent should add them in one session or merge sequentially; they have no logical dependency on each other.
- T-02 and the T-01 branch creation are sequential. T-03 must follow T-02. T-04 can start as soon as T-02 exists (it only needs the module to import), so T-03 and T-04 can run in parallel.
- T-09 onward is strictly sequential: T-09 then T-10 then T-11.

Critical path: T-01, T-02, T-04, (T-05..T-08), T-09, T-10, T-11.

## Definition of done

- `python -m unittest discover -s tests -v` shows zero failures and zero errors, with counts reported as observed and `tests/test_sync_docs.py` unchanged.
- Only the two listed files are added.
- PR URL printed and `gh pr view` confirms it is open.
