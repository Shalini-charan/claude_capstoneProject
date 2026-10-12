# Design Review

**Document reviewed:** docs/architecture.md  
**Reviewer role:** Senior Engineer (conducted by Claude Code)  
**Review date:** 2026-09-30  
**Verdict:** PASS WITH CONDITIONS — 4 issues must be resolved before implementation  

---

## 1. Executive Summary

The architecture is fundamentally sound: a single-file Python stdlib script invoked from a Git hook is the right shape for this problem. The component decomposition (Extractor → Manager → Detector → Committer) is clean and testable. However, four issues were found that would cause silent data loss or broken behaviour in production, plus three low-severity gaps that should be documented or clarified. All are fixable without redesign.

---

## 2. Risk Register

### RISK-01 — Sync commit is NOT included in the triggering push (HIGH)

| Field | Detail |
|---|---|
| **Location** | architecture.md §3 Data Flow, §2.1 Pre-push Hook |
| **Root cause** | When `git push` fires, Git determines the set of refs to send *before* the pre-push hook runs. Any commit the hook makes is therefore NOT part of the current push. |
| **Failure scenario** | Developer runs `git push`. Hook creates sync commit B on top of their commit A. Push sends only A. Remote is one commit behind local `main`. Developer never realises and the sync commit silently never reaches the remote. |
| **Severity** | High — the primary value of the feature (synced docs on remote) fails silently. |
| **Decision** | **Accept + Document.** The user chose pre-push hook (FR-4). Changing to `post-commit` would violate the requirement. Document as **KL-1** in architecture. Developer will see "1 ahead" and must push again. |

---

### RISK-02 — Partial failure leaves README.md permanently dirty (MEDIUM)

| Field | Detail |
|---|---|
| **Location** | architecture.md §7 Error Handling — `git commit` fails scenario |
| **Root cause** | `ReadmeManager.write_section()` writes to disk before `git commit` is attempted. If `git commit` fails, README.md is modified but not staged or committed. On the next run `ChangeDetector` compares new-README vs new-README — finds no diff — makes no commit. The sync is silently lost forever. |
| **Failure scenario** | Git identity not configured → `git commit` exits 1 → README updated on disk but uncommitted → next push does nothing → docs drift despite hook running. |
| **Severity** | Medium — silent data loss path. |
| **Decision** | **Fix.** `GitCommitter` must save the original README content before writing. If `git commit` fails, it restores the original README before exiting 1. Add explicit rollback step. |

---

### RISK-03 — File encoding not specified; non-UTF-8 .py files crash the script (MEDIUM)

| Field | Detail |
|---|---|
| **Location** | architecture.md §2.3.1 `DocstringExtractor` |
| **Root cause** | Architecture says `ast.parse(source)` but does not specify how `.py` files are opened. On Windows, files written with a non-UTF-8 locale (e.g. Windows-1252) will raise `UnicodeDecodeError`, causing the entire push to be aborted (exit 1). |
| **Failure scenario** | Developer has a `.py` file saved in Latin-1 → `open(path)` uses system locale → `UnicodeDecodeError` → hook exits 1 → push blocked. |
| **Severity** | Medium — can block all pushes on affected machines. |
| **Decision** | **Fix.** Specify `encoding='utf-8', errors='replace'` when opening `.py` files. Log a warning to stderr for any file that contained replacement characters. |

---

### RISK-04 — `python` command not portable on Windows (MEDIUM)

| Field | Detail |
|---|---|
| **Location** | architecture.md §2.1 Pre-push Hook, §5 Technology Decisions |
| **Root cause** | The hook calls `python src/sync_docs.py`. On Windows, the Python executable may be `py` (Python Launcher) or `python3`. Git Bash on Windows does not always add `python` to PATH. |
| **Failure scenario** | Developer installs Python for Windows with only `py` on PATH → hook `python src/sync_docs.py` → `command not found` → exit 1 → every push is blocked. |
| **Severity** | Medium — blocks all pushes on common Windows setups. |
| **Decision** | **Fix.** Hook must detect the Python executable: try `python`, then `python3`, then `py`. Fail with a clear error message if none resolves. |

---

### RISK-05 — Writing an empty `## API Reference` section when no .py files exist (LOW)

| Field | Detail |
|---|---|
| **Location** | architecture.md §7 Error Handling — "No .py files found" row |
| **Root cause** | Architecture says "write empty section; exit 0". This creates `## API Reference\n\n` in README.md on first run if there are no .py files, leaving a confusing empty section and making a commit with no real content. |
| **Failure scenario** | Fresh repo with only docs/ files → hook runs → empty `## API Reference` section committed → unnecessary commit noise. |
| **Severity** | Low — noise, not data loss. |
| **Decision** | **Fix.** When no `.py` files are found, skip the README update entirely, write a warning to stderr, and exit 0. No commit made. |

---

### RISK-06 — `DocEntry.signature` field not precisely defined (LOW)

| Field | Detail |
|---|---|
| **Location** | architecture.md §6 Key Interfaces |
| **Root cause** | `DocEntry: {name, signature, docstring}` — "signature" is ambiguous. Does it include the function name? Return annotation? `self` parameter? |
| **Failure scenario** | Implementer renders `### \`name(signature)\`` — if `signature` includes the name, the output becomes `add(add(a, b))`. |
| **Severity** | Low — cosmetic but causes malformed Markdown output. |
| **Decision** | **Clarify.** Define `signature` as the parameter list only (excluding the function name), e.g. `a: int, b: int` for `def add(a: int, b: int) -> int`. The Markdown template then renders as `### \`add(a: int, b: int)\``. |

---

### RISK-07 — `## API Reference` heading match is exact; typos cause silent misses (LOW)

| Field | Detail |
|---|---|
| **Location** | architecture.md §2.3.2 `ReadmeManager` |
| **Root cause** | Section boundary detection uses exact string match on `## API Reference`. If a developer writes `## API References` or `## Api Reference`, the section is never found and a duplicate is appended on every push. |
| **Failure scenario** | README has `## API References` (plural) → `ReadmeManager` never finds it → appends a new `## API Reference` section on every push → README accumulates duplicate sections. |
| **Severity** | Low — user-error scenario but produces highly visible corruption. |
| **Decision** | **Document.** Add a constraint note to `ReadmeManager` spec: the heading must be exactly `## API Reference` (case-sensitive). Document this in the tool's `--help` output and README. |

---

## 3. Agreed Design Decisions

| ID | Decision | Applies to |
|---|---|---|
| DD-01 | Accept KL-1 (second push needed); add Known Limitations section to architecture.md | architecture.md §new |
| DD-02 | Add rollback to `GitCommitter`: save original README content, restore on `git commit` failure | architecture.md §2.3.4, §7 |
| DD-03 | Specify `encoding='utf-8', errors='replace'` in `DocstringExtractor.extract()` | architecture.md §2.3.1 |
| DD-04 | Hook detects Python executable (`python` → `python3` → `py`); fails with clear message | architecture.md §2.1 |
| DD-05 | Skip README update (and commit) when no `.py` files found | architecture.md §7 |
| DD-06 | Define `DocEntry.signature` as parameter list only (no function name) | architecture.md §6 |
| DD-07 | Document exact heading requirement for `## API Reference` | architecture.md §2.3.2 |

---

## 4. Items Confirmed as Correct

- **Component decomposition** — 4-class single-file design is appropriate for the scope.
- **`ast.parse` for extraction** — correct choice; avoids code execution risk.
- **Section boundary regex** — ending at next `## ` heading correctly allows `###` subheadings inside the API Reference section.
- **`pre-push` not `pre-commit`** — correct; pre-commit would run on every commit including the sync commit itself, causing infinite recursion.
- **Idempotency** — ChangeDetector stripped-equality comparison is the right approach.
- **Exit code strategy** — 0 for success/no-op, 1 for all errors is correct for Git hooks.
- **`src/sync_docs.py` in `src/` not root** — prevents the script from scanning itself.

---

## 5. Required Changes to architecture.md

The following sections must be updated before implementation starts (Step 5):

| Section | Change |
|---|---|
| §2.1 Pre-push Hook | Add Python executable detection logic (DD-04) |
| §2.3.1 DocstringExtractor | Add encoding specification (DD-03); clarify DocEntry.signature (DD-06) |
| §2.3.2 ReadmeManager | Add heading exactness constraint note (DD-07) |
| §2.3.4 GitCommitter | Add rollback on commit failure (DD-02) |
| §6 Key Interfaces | Clarify DocEntry fields (DD-06) |
| §7 Error Handling | Fix "No .py files" row (DD-05); add rollback row (DD-02) |
| §new §8 Known Limitations | Add KL-1: second push required after sync commit (DD-01) |
