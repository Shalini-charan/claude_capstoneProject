---
title: Architecture - slugify utility (CLAUDE-4)
ticket: CLAUDE-4
created: 2026-10-13T16:09:00+05:30
updated: 2026-10-13T16:12:00+05:30
created_by: architecture-agent
hitl_status: not-required
approved_by: null
approved_on: null
revision: 2
---

# Architecture

Source: `docs/claude4/requirements.md` (approved). Scope is one pure function plus its tests (C-5).

## 1. Component Overview

| Component | Location | Responsibility | Public interface | Requirements |
|-----------|----------|----------------|------------------|--------------|
| Slug converter | `src/slugify.py` (new) | Convert a title string into a URL-safe slug. Pure, stdlib-only (`re`). | `slugify(text: str) -> str`; raises `TypeError` if `text` is not a `str` | FR-1 to FR-13, NFR-1, NFR-2, NFR-3, NFR-6, NFR-7 |
| Slug converter tests | `tests/test_slugify.py` (new) | `unittest.TestCase` covering AC 1 to 6 and the assumption edge cases. | Run via `python -m unittest discover -s tests -v` | FR-14, NFR-4, NFR-5 |

No change to `src/sync_docs.py` or `tests/test_sync_docs.py`. Delivery through a PR (FR-15) is a pipeline step, not a component.

Module-level contents of `src/slugify.py`: two precompiled patterns and the function.

```python
_INVALID = re.compile(r"[^A-Za-z0-9 \t\n\r\f\v-]")
_SEPARATORS = re.compile(r"[ \t\n\r\f\v-]+")
```

The docstring must state behaviour and the `TypeError` condition (NFR-6).

Import path: tests must import the module the same way `tests/test_sync_docs.py` imports `sync_docs` (the implementation agent should mirror that existing convention, for example a `sys.path` insert of `src`), so that discovery from the repo root works on Windows and POSIX (NFR-7).

## 2. Data Flow

1. Caller passes `text` to `slugify`.
2. If `not isinstance(text, str)`, raise `TypeError` (FR-12). Nothing else runs.
3. Remove every character matching `_INVALID` (anything outside ASCII letters, digits, the six ASCII whitespace characters and hyphen). Covers punctuation, underscores, non-ASCII letters, and non-ASCII whitespace (FR-5, FR-6, C-8, A-3).
4. Replace each run matching `_SEPARATORS` (any mix of whitespace and hyphens) with a single `-` (FR-7, FR-8, FR-9, C-10).
5. Strip leading and trailing `-`. This also performs the whitespace trim (FR-3, FR-13, C-7).
6. Lowercase the result with `str.lower()` (FR-4). The string is pure ASCII at this point.
7. Return the string. Empty or all-invalid input naturally yields `""` (FR-10, FR-11).

Worked examples: `"Hello, World!"` -> `"Hello World"` -> `"Hello-World"` -> `"hello-world"`. `"  --A_b\t\nC-- "` -> `"  --Ab\t\nC-- "` -> `"-Ab-C-"` -> `"Ab-C"` -> `"ab-c"`.

## 3. Key Data Structures

None cross component boundaries beyond `str` in and `str` out. No classes, namedtuples or schemas are introduced.

## 4. Architecture Decision Records

### DD-01: New module `src/slugify.py`, not an addition to `sync_docs.py`
**Context:** C-9 leaves the location to this stage. `sync_docs.py` serves an unrelated purpose.
**Decision:** Create `src/slugify.py` and `tests/test_slugify.py`.
**Rationale:** One responsibility per module; satisfies NFR-5 (new test file, existing tests untouched); avoids touching unrelated code (C-5).
**Consequence:** Two new files; the existing files are unchanged.

### DD-02: Two-regex pipeline with remove-then-collapse order
**Context:** The rules (remove invalid, collapse separators, strip hyphens, lowercase) interact. Removing characters can make separators adjacent (for example `"a - ! - b"` or `"a_ b"`).
**Decision:** Remove invalid characters first, then collapse separator runs, then strip, then lowercase, as in section 2.
**Rationale:** Collapsing after removal guarantees a single hyphen between words even when removed characters sat between separators (`"a - ! - b"` -> `"a -  - b"` -> `"a-b"`). Collapsing before removal would leave `"a--b"`. Precompiled regexes are linear time, so a 10,000-character input is far below 50 ms (NFR-2), and they need only `re` (NFR-3).
**Consequence:** Output is deterministic and idempotent: `slugify(slugify(x)) == slugify(x)`. A test should assert this.

### DD-03: Whitespace is the explicit ASCII set, treated like a space
**Context:** C-10 extends whitespace to tab and newline. Python's `\s` on `str` also matches Unicode whitespace (for example NBSP, U+2003), which conflicts with C-8 and platform consistency.
**Decision:** Use the explicit class ` \t\n\r\f\v` instead of `\s`. Each whitespace character, including tab and newline, behaves as a space: it is a separator that becomes a hyphen. Non-ASCII whitespace is an invalid character and is removed, not converted.
**Rationale:** Predictable and locale/platform independent (NFR-7); consistent with the ASCII-only definition of letters.
**Consequence:** `"a\tb"` and `"a\nb"` give `"a-b"`; `"a b"` gives `"ab"` (see KL-2).

### DD-04: Filter before lowercasing, with an ASCII-only allow-list
**Context:** `str.lower()` on some non-ASCII characters yields ASCII (KELVIN SIGN U+212A lowers to `k`; `İ` lowers to `i` plus a combining dot). Lowercasing first would let these slip past the filter.
**Decision:** Filter with the allow-list `[A-Za-z0-9 \t\n\r\f\v-]` on the original text, then lowercase. Do not use `re.IGNORECASE` or `str.isalnum()` (the latter accepts Unicode letters and digits).
**Rationale:** Enforces C-8 strictly: non-ASCII letters are always removed, and the output is always `[a-z0-9-]*`.
**Consequence:** `"Café"` gives `"caf"`; Kelvin sign input is removed.

### DD-05: Hyphen and underscore handling (assumptions A-1, A-2, A-3)
**Context:** The requirements assume hyphens are kept and collapsed (C-6), edge hyphens are stripped (C-7), and underscores are removed (A-3).
**Decision:** Hyphen belongs to the separator class. Underscore is not in the allow-list, so it is removed (not converted to a hyphen). Edge hyphens are removed with `strip("-")`.
**Rationale:** Matches the approved requirement text literally and needs no special cases.
**Consequence:** `"snake_case"` gives `"snakecase"`; `"-Hello-"` gives `"hello"`; `"---"` gives `""`. If the developer later rejects A-1 to A-3, only the regex classes and `strip` call change.

### DD-06: Strict type check with `isinstance(text, str)`
**Context:** FR-12 requires `TypeError` for non-strings.
**Decision:** Explicit `isinstance` check at the top that raises `TypeError` with a message naming the received type. Subclasses of `str` are accepted. `bytes` is rejected.
**Rationale:** Without it, `re.sub` raises `TypeError` for `None`, int and list anyway, but with an unclear message and, for `bytes`, a different failure. An explicit guard gives a clear and stable contract.
**Consequence:** Input is validated before any processing; no coercion via `str()` is ever done.

## 5. Known Limitations

- **KL-1:** No transliteration. Non-ASCII letters are dropped, so a title such as `"Café"` becomes `"caf"` and a fully non-ASCII title becomes `""` (C-3, C-8).
- **KL-2:** Non-ASCII whitespace (NBSP, em space) is removed rather than treated as a word separator, so `"a b"` becomes `"ab"`. Accepted for consistency with C-8.
- **KL-3:** Underscores are removed, which merges words in `snake_case` input (A-3).
- **KL-4:** No maximum length and no uniqueness handling (C-4). Distinct inputs can map to the same slug.
- **KL-5:** Assumptions A-1 to A-4 were approved with the requirements but are encoded as assumed behaviour; changing any means editing the regexes (DD-05).
