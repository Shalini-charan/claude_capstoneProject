# Pull Request — Automated Documentation Sync

**Title:** feat: automated README.md sync from Python docstrings via pre-push hook  
**Branch:** `main`  
**Jira:** [CLAUDE-1](https://shalini-srinivasan.atlassian.net/jira/core/projects/CLAUDE/boards) — Auto-sync README.md when Python docstrings change on push  
**Date:** 2026-09-30  

---

## Summary

- Implements a Git pre-push hook that automatically extracts Google-style docstrings from all top-level Python functions and classes in the repo root and writes them into a dedicated `## API Reference` section in `README.md`.
- Detects content changes before writing — no commit is made if docstrings have not changed since the last sync, keeping history clean.
- Covers the full Agentic SDLC cycle: Requirements → Architecture → Design Review → Implementation Plan → Implementation → Code Review (×2 rounds) → Tests → PR.
- Demonstrates the GitHub Copilot → Claude Code capability mapping: Agents (`.claude/agents/`), Slash Commands (`.claude/commands/`), Hooks (`.claude/settings.json`).

---

## Changes Made

| File | Change |
|------|--------|
| `docs/requirements.md` | FR/NFR/Constraints for CLAUDE-1 (FR-1–FR-5, NFR-1–NFR-5, C-1–C-5, AC-1–AC-4) |
| `docs/architecture.md` | 4-component design: DocstringExtractor, ReadmeManager, ChangeDetector, GitCommitter + ADRs DD-01–DD-07 + KL-1 |
| `docs/design-review.md` | Risk register RISK-01–RISK-07; 4 FIXED, 1 ACCEPTED (KL-1), 2 DOCUMENTED |
| `docs/impl-plan.md` | 14 tasks T-01–T-14 across 6 phases; parallel groups A (T-02/T-03/T-04) and B (T-09/T-10/T-11) |
| `src/sync_docs.py` | Complete implementation — single file, stdlib-only, Python 3.8+ |
| `hooks/pre-push.template` | POSIX sh hook; detects `python`/`python3`/`py`; propagates exit code |
| `install_hook.sh` | One-time developer setup script; copies template, sets `chmod +x` |
| `README.md` | Project readme; `## API Reference` section auto-populated by the tool |
| `example.py` | Smoke-test artifact demonstrating live hook output |
| `tests/test_sync_docs.py` | 42 tests: T-09–T-13 unit + integration; `_build_signature` edge cases |
| `.claude/agents/*.md` | 6 SDLC agent definitions (requirements, architecture, design-review, impl-plan, code-review, pr) |
| `.claude/commands/*.md` | 3 slash commands (`/gather-requirements`, `/design-arch`, `/review-code`) |
| `.claude/settings.json` | PostToolUse hook → `python src/sync_docs.py` after every Write/Edit |
| `.gitignore` | `src/__pycache__/` |

---

## Implementation Notes

### Core design
`src/sync_docs.py` is a single-file, zero-dependency Python module containing four classes orchestrated by `main()`:

```
DocstringExtractor  →  list[DocEntry]
                              ↓
                    _format_entries()  →  new_content: str
                              ↓
ReadmeManager.read_section()  →  old_content: str
                              ↓
ChangeDetector.has_changed()  →  bool
                              ↓  (True only)
ReadmeManager.write_section() + GitCommitter.stage_and_commit()
```

### Key fixes applied during code review (2 rounds)
| Round | Fix |
|-------|-----|
| Manual | Critical rollback bug: `original_readme` captured **before** `write_section()` |
| Manual | DRY: `_run_git()` helper eliminates duplicated error-handling |
| Agent  | `git restore --staged` added on `git commit` failure to clean index |
| Agent  | `self`/`cls` strip compares `arg.arg` (bare name), not the assembled annotation string |
| Agent  | Positional-only `/` separator inserted correctly after `posonlyargs` |
| Agent  | `_unparse_node`: `ast.unparse` returns `''` for unknown nodes — handled with `if result:` guard |

---

## How to Test

### Unit + Integration tests
```bash
python -m unittest tests/test_sync_docs.py -v
```

### Smoke test (live hook)
```bash
# 1. Install the hook (one-time)
sh install_hook.sh

# 2. Confirm hook is in place
cat .git/hooks/pre-push

# 3. Push to any remote — hook fires automatically
git push origin main
# Expected output on stderr: "sync_docs: README.md updated and committed"
#   or: "sync_docs: no docstring changes detected"
```

---

## Test Evidence

```
test_annotated_params ... ok
test_annotated_self_stripped ... ok
test_class_node_returns_empty_string ... ok
test_cls_stripped ... ok
test_default_value ... ok
test_no_params_returns_empty ... ok
test_plain_self_stripped ... ok
test_positional_only_separator_present ... ok
test_simple_params ... ok
test_star_args_and_kwargs ... ok
test_both_empty_no_change ... ok
test_different_content_is_changed ... ok
test_empty_vs_content_is_changed ... ok
test_identical_content_no_change ... ok
test_leading_and_trailing_whitespace_ignored ... ok
test_trailing_newline_ignored ... ok
test_whitespace_only_vs_empty_no_change ... ok
test_async_function_extracted ... ok
test_class_extracted_but_nested_method_is_not ... ok
test_class_with_docstring ... ok
test_empty_file_returns_empty ... ok
test_function_with_google_docstring ... ok
test_no_docstrings_returns_empty ... ok
test_non_utf8_chars_emit_warning ... ok
test_syntax_error_skips_file_with_warning ... ok
test_get_short_hash_non_empty ... ok
test_rollback_on_commit_failure_restores_file ... ok
test_rollback_on_commit_failure_unstages_file ... ok
test_stage_and_commit_creates_commit ... ok
test_creates_readme_when_missing ... ok
test_first_run_creates_api_reference_section ... ok
test_no_py_files_exits_0_no_commit ... ok
test_second_run_no_change_makes_no_commit ... ok
test_updated_docstring_triggers_new_sync_commit ... ok
test_read_section_absent_returns_empty ... ok
test_read_section_missing_file_returns_empty ... ok
test_read_section_returns_body ... ok
test_read_section_stops_at_next_heading ... ok
test_write_section_appends_new_heading ... ok
test_write_section_creates_missing_readme ... ok
test_write_section_no_duplicate_on_repeat ... ok
test_write_section_overwrites_existing ... ok

----------------------------------------------------------------------
Ran 42 tests in 6.053s

OK
```

### T-14 Smoke test evidence (live hook)
```
$ git push smoke_test master
sync_docs: README.md updated and committed
To .../capstone_bare_q2qy
 * [new branch]      master -> master

$ git log --oneline -3
457338b docs: auto-sync from a3f6a00   ← auto-created by hook
a3f6a00 feat: add example.py for T-14 smoke test
6d725ed test: add verification suite T-09 through T-13
```

---

## Known Limitations

### KL-1 — Sync commit is not included in the triggering push

**Root cause:** Git determines which refs to transmit *before* the pre-push hook runs. Any commit created by the hook is not included in the current push.

**Consequence:** After a push that triggers a sync, local `main` will be one commit ahead of the remote. A second `git push` is required to send the sync commit.

**Why accepted:** The alternative (post-commit hook) would trigger on every commit including the sync commit itself, risking recursion. `pre-push` was the requirement (FR-4). The user sees the `docs: auto-sync from …` message in the terminal and knows to push again.

**Mitigation (future):** A CI-based approach (GitHub Actions on `push`) would avoid this entirely.

---

## Reviewer Checklist

### Functional Requirements
- [ ] **FR-1** — Tool parses all `.py` files in repo root using `ast` (no execution, no third-party deps)
- [ ] **FR-2** — Docstrings written into `## API Reference` section; section created if absent; overwritten if present
- [ ] **FR-3** — Change detection prevents empty commits; changed content produces `docs: auto-sync from <hash>`
- [ ] **FR-4** — `install_hook.sh` installs a working `pre-push` hook; hook aborts push on exit 1
- [ ] **FR-5** — Exit 0 on success/no-op; exit 1 on any error

### Non-Functional Requirements
- [ ] **NFR-1** — Runs on Python 3.8+ stdlib only; no `pip install`
- [ ] **NFR-2** — Completes in < 5 seconds for ≤ 20 `.py` files
- [ ] **NFR-3** — Second run with no changes makes no commit (idempotent)
- [ ] **NFR-4** — Generated Markdown renders correctly on GitHub
- [ ] **NFR-5** — All errors written to `stderr` with human-readable messages

### Design & Risk
- [ ] All RISK items from `docs/design-review.md` are resolved (RISK-02–RISK-07 FIXED/DOCUMENTED; RISK-01 ACCEPTED + documented as KL-1)
- [ ] Rollback restores `README.md` **and** unstages the index on `git commit` failure
- [ ] `self`/`cls` correctly stripped from instance/class method signatures
- [ ] No subprocess injection risk (all git args are controlled strings, not user input)

### Tests & Evidence
- [ ] 42 unit + integration tests pass (`python -m unittest tests/test_sync_docs.py -v`)
- [ ] T-14 smoke test passed (live push triggered hook, README updated, sync commit created)
- [ ] No test uses `unittest.mock` to bypass real git operations in the integration suite

### Agentic SDLC Pipeline
- [ ] `.claude/agents/` contains 6 agent definitions covering all SDLC phases
- [ ] `.claude/commands/` contains 3 slash commands
- [ ] `.claude/settings.json` PostToolUse hook mirrors the git pre-push automation pattern

---

## Commit History

```
ce6b673 feat: add .claude agents, commands, and hook configuration
457338b docs: auto-sync from a3f6a00
a3f6a00 feat: add example.py for T-14 smoke test
6d725ed test: add verification suite T-09 through T-13
61c4ecf fix: apply agent code-review findings to sync_docs.py
9920802 fix: apply code review fixes to sync_docs.py
691df22 feat: implement auto-doc-sync tool (T-01 through T-08)
791b78b docs: add impl-plan.md
2a45e58 docs: add design-review.md and update architecture.md
ec5679c docs: add architecture.md
f2e3bb9 docs: add requirements.md (root commit)
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
