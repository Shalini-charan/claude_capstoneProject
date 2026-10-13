---
title: PR Description - slugify utility (CLAUDE-4)
ticket: CLAUDE-4
created: 2026-10-13T16:19:00+05:30
created_by: pr-agent
hitl_status: not-required
approved_by: null
approved_on: null
revision: 1
---

# feat: add slugify utility (CLAUDE-4)

Base: `main`. Head: `feature/claude-4-slugify`. Jira: https://shalini-srinivasan.atlassian.net/browse/CLAUDE-4

## Summary
- Adds `slugify(text)`, a pure, stdlib-only function that turns a title into a URL-safe slug (for example `"Hello, World!"` becomes `"hello-world"`), so clean URLs and file names can be built from titles.
- Adds `tests/test_slugify.py` covering acceptance criteria AC 1 to 6 plus the approved assumption edge cases. The AC numbering was confirmed against the Jira ticket.
- Assumptions A-1 to A-4 (hyphens kept, edge hyphens stripped, underscores removed, non-ASCII letters removed) and C-10 (tab and newline count as whitespace) were approved by the developer.
- Existing files (`src/sync_docs.py`, `tests/test_sync_docs.py`) are not touched. The ticket exists to validate the SDLC orchestrator end to end, so scope is limited to this one function.

## Changes Made
| File | Change |
|------|--------|
| src/slugify.py | New module with `slugify(text: str) -> str`. Raises `TypeError` for non-string input. |
| tests/test_slugify.py | New test file, 20 tests. |
| docs/claude4/ | SDLC documents for CLAUDE-4 (requirements, architecture, design review, implementation plan, this description). |

## How to Test
1. Check out the branch: `git checkout feature/claude-4-slugify`
2. Run the full suite from the repo root: `python -m unittest discover -s tests -v`
3. Run only the new tests: `python -m unittest tests.test_slugify -v` (or `python tests/test_slugify.py`)
4. Try it by hand: `python -c "import sys; sys.path.insert(0, 'src'); from slugify import slugify; print(slugify('  Hello, -- World! '))"` prints `hello-world`.

## Test Evidence
Results observed by the developer, reported as run:

```
Full suite (python -m unittest discover -s tests -v):
  run: 84   passed: 83   failed: 0   skipped: 1
  The skip is the pre-existing CLAUDE-2 skip in tests/test_sync_docs.py.

tests/test_slugify.py:
  run: 20   passed: 20   failed: 0   skipped: 0
```

Code review: 0 findings.

## Known Limitations
- **KL-1 (no transliteration):** non-ASCII letters are dropped, so `"Cafe"` with an accent becomes `"caf"` and a fully non-ASCII title becomes `""`. Accepted because transliteration is out of scope (C-3, C-8). Callers must handle an empty result.
- **KL-2 (non-ASCII whitespace):** NBSP and em space are removed, not treated as separators, so two words joined by NBSP become one. Accepted for consistency with the ASCII-only rule (C-8) and platform-independent behaviour.
- **KL-3 (underscores removed):** `"snake_case"` becomes `"snakecase"`. Accepted under assumption A-3, approved by the developer.
- **KL-4 (no length limit or uniqueness):** distinct inputs can map to the same slug. Accepted because maximum length and uniqueness are out of scope (C-4, C-5).
- **KL-5 (assumed behaviour):** A-1 to A-4 are encoded as approved assumptions. Changing one means editing the regex classes or the `strip` call only (DD-05).

## Reviewer Checklist
- [ ] FR-1: `slugify(text)` exists, takes a string and returns a string
- [ ] FR-2: `slugify("Hello World")` returns `"hello-world"`
- [ ] FR-3: leading and trailing whitespace is removed
- [ ] FR-4: result is lowercase
- [ ] FR-5: characters other than letters, digits, spaces and hyphens are removed
- [ ] FR-6: `slugify("Hello, World!")` returns `"hello-world"`
- [ ] FR-7: each run of spaces becomes a single hyphen
- [ ] FR-8: consecutive hyphens collapse to one
- [ ] FR-9: mixed runs of spaces and hyphens collapse to one hyphen
- [ ] FR-10: empty string input returns `""`
- [ ] FR-11: input with no valid characters (for example `"!!!"`) returns `""`
- [ ] FR-12: non-string input (`None`, int, list) raises `TypeError`
- [ ] FR-13: leading and trailing hyphens are removed from the result
- [ ] FR-14: unit tests cover AC 1 to 6
- [ ] FR-15: change delivered through this pull request
- [ ] NFR-5: `tests/test_sync_docs.py` is unchanged
- [ ] No open HIGH or CRITICAL risks in design-review.md (none were raised; RISK-01 assumptions approved by the developer)
- [ ] Tests pass locally
- [ ] README.md: no change made in this PR; confirm none is needed

🤖 Generated with [Claude Code](https://claude.com/claude-code)
