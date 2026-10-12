# Implementation Plan

**Source:** docs/architecture.md (post design-review)  
**Project:** claudeCapStone (Agentic SDLC Capstone)  
**Date:** 2026-09-30  

---

## 1. Dependency Graph

```
T-01 (scaffold)
   │
   ├─────────────────────┬────────────────────┐
   ▼                     ▼                    ▼
T-02                   T-03                 T-04
DocstringExtractor     ReadmeManager        ChangeDetector
   │                     │                    │
   │                     ▼                    │
   │                   T-05                   │
   │                 GitCommitter             │
   │                     │                    │
   └──────────┬──────────┘                    │
              ▼                               │
            T-06 ◀─────────────────────────── ┘
           main()
              │
        ┌─────┴──────┐
        ▼            ▼
      T-07          T-09..T-13
   hook template      tests
        │
        ▼
      T-08
  install_hook.sh
        │
        ▼
      T-14
  smoke test
```

---

## 2. Task List (dependency order)

### Phase 0 — Scaffolding

#### T-01 · Create project directory structure
| Field | Detail |
|---|---|
| **File(s)** | `src/` dir, `tests/` dir, `README.md` |
| **Depends on** | — |
| **Blocks** | T-02, T-03, T-04, T-05 |
| **Description** | Create `src/` and `tests/` directories. Create a minimal `README.md` with a title and one placeholder paragraph. No `## API Reference` section yet — the tool will create it on first run. |
| **Done when** | `src/` and `tests/` dirs exist; `README.md` is committed with no `## API Reference` section. |

---

### Phase 1 — Core Components (T-02, T-03, T-04 can be built in parallel)

#### T-02 · Implement `DocEntry` namedtuple + `DocstringExtractor`
| Field | Detail |
|---|---|
| **File(s)** | `src/sync_docs.py` (partial) |
| **Depends on** | T-01 |
| **Blocks** | T-06, T-09 |
| **Imports** | `ast`, `textwrap`, `pathlib`, `sys`, `collections.namedtuple` |
| **Description** | Define `DocEntry = namedtuple('DocEntry', ['name', 'signature', 'docstring'])`. Implement `DocstringExtractor.extract(file_path: Path) -> list[DocEntry]`. Open file with `encoding='utf-8', errors='replace'`; warn to `stderr` if replacement chars present. Call `ast.parse()`. Walk tree for top-level `FunctionDef`, `AsyncFunctionDef`, `ClassDef` nodes. For each: extract `node.name`, build `signature` from `node.args` as param-list-only string (e.g. `a: int, b: int`), extract first `ast.Constant` child string as docstring, apply `textwrap.dedent`. Skip nodes with no docstring. |
| **Done when** | `DocstringExtractor().extract(Path('example.py'))` returns a correct list of `DocEntry` for a Google-style docstrings file. |

---

#### T-03 · Implement `ReadmeManager`
| Field | Detail |
|---|---|
| **File(s)** | `src/sync_docs.py` (partial) |
| **Depends on** | T-01 |
| **Blocks** | T-05, T-06, T-10 |
| **Imports** | `pathlib`, `re` |
| **Description** | Implement `ReadmeManager` with two methods. `read_section(readme_path)`: read README.md; use regex `r'## API Reference\n(.*?)(?=\n## |\Z)'` with `re.DOTALL` to extract section body; return `""` if section absent or README missing. `write_section(readme_path, content)`: if `## API Reference` heading found, replace everything from heading to next `##` or EOF with new content; if not found, append `\n## API Reference\n` + content to the file. Write with `encoding='utf-8'`. |
| **Done when** | `read_section` returns `""` on a README with no section and the correct body on one with it; `write_section` correctly overwrites or appends. |

---

#### T-04 · Implement `ChangeDetector`
| Field | Detail |
|---|---|
| **File(s)** | `src/sync_docs.py` (partial) |
| **Depends on** | T-01 |
| **Blocks** | T-06, T-11 |
| **Imports** | — (pure function, no imports needed) |
| **Description** | Implement `ChangeDetector.has_changed(old: str, new: str) -> bool`. Compare `old.strip() != new.strip()`. Return `True` if they differ, `False` if identical. |
| **Done when** | `has_changed("foo\n", "foo")` returns `False`; `has_changed("foo", "bar")` returns `True`. |

---

### Phase 2 — Git Integration

#### T-05 · Implement `GitCommitter`
| Field | Detail |
|---|---|
| **File(s)** | `src/sync_docs.py` (partial) |
| **Depends on** | T-03 (rollback reads README via same path) |
| **Blocks** | T-06, T-12 |
| **Imports** | `subprocess`, `sys`, `pathlib` |
| **Description** | Implement `GitCommitter` with two methods. `get_short_hash() -> str`: run `git rev-parse --short HEAD` via `subprocess.run(capture_output=True)`; return stdout stripped. `stage_and_commit(readme_path, message)`: (1) read and save `original_content = readme_path.read_text(encoding='utf-8')`; (2) run `git add <readme_path>`; (3) run `git commit -m <message>`; if either git command fails (returncode != 0), write stderr to `sys.stderr`, call `readme_path.write_text(original_content, encoding='utf-8')` (rollback), then `sys.exit(1)`. |
| **Done when** | Method creates a commit with correct message; restores README and exits 1 if commit fails. |

---

### Phase 3 — Orchestrator

#### T-06 · Implement `main()` function
| Field | Detail |
|---|---|
| **File(s)** | `src/sync_docs.py` (completes the file) |
| **Depends on** | T-02, T-03, T-04, T-05 |
| **Blocks** | T-07, T-13 |
| **Imports** | `pathlib`, `sys` (already present) |
| **Description** | Implement `main()` wrapped in top-level `try/except Exception`. Steps: (1) Discover `list(Path('.').glob('*.py'))`. If empty: print warning to stderr, `sys.exit(0)`. (2) Instantiate `DocstringExtractor`; call `extract()` for each file; collect all `DocEntry` items. (3) Format entries as Markdown: for each entry, render `### \`name(signature)\`\n\n<docstring>\n\n`. Join all entries into `new_content`. (4) Instantiate `ReadmeManager`; call `read_section(Path('README.md'))` → `old_content`. (5) Instantiate `ChangeDetector`; call `has_changed(old_content, new_content)`. If `False`: print "sync_docs: no docstring changes detected" to stderr; `sys.exit(0)`. (6) Call `ReadmeManager.write_section(Path('README.md'), new_content)`. (7) Instantiate `GitCommitter`; call `get_short_hash()` → `hash`; call `stage_and_commit(Path('README.md'), f"docs: auto-sync from {hash}")`. (8) Print "sync_docs: README.md updated and committed" to stderr; `sys.exit(0)`. Add `if __name__ == '__main__': main()` at bottom. |
| **Done when** | Running `python src/sync_docs.py` from a repo with .py files updates README.md and creates a commit; running it again with no changes exits 0 with no commit. |

---

### Phase 4 — Hook Infrastructure

#### T-07 · Write pre-push hook template
| Field | Detail |
|---|---|
| **File(s)** | `hooks/pre-push.template` (source-controlled template) |
| **Depends on** | T-06 |
| **Blocks** | T-08 |
| **Description** | Write a POSIX `sh` script. Shebang: `#!/bin/sh`. Python detection block: try `python --version`, else `python3 --version`, else `py --version`; if none found print error to stderr and `exit 1`. Run `$PYTHON_CMD src/sync_docs.py`; propagate exit code with `exit $?`. Store as `hooks/pre-push.template` (tracked in git; copied to `.git/hooks/pre-push` by installer). |
| **Done when** | Script detects Python correctly on the current machine; invokes `sync_docs.py`; exits with its return code. |

---

#### T-08 · Write `install_hook.sh`
| Field | Detail |
|---|---|
| **File(s)** | `install_hook.sh` |
| **Depends on** | T-07 |
| **Blocks** | T-14 |
| **Description** | Write a POSIX `sh` script that: (1) copies `hooks/pre-push.template` to `.git/hooks/pre-push`; (2) sets executable bit with `chmod +x .git/hooks/pre-push`; (3) prints "Hook installed at .git/hooks/pre-push". Include a guard: if `.git/` is not found in the current directory, print an error and exit 1. |
| **Done when** | Running `sh install_hook.sh` produces a working hook at `.git/hooks/pre-push`. |

---

### Phase 5 — Tests

#### T-09 · Unit tests — `DocstringExtractor`
| Field | Detail |
|---|---|
| **File(s)** | `tests/test_sync_docs.py` |
| **Depends on** | T-02 |
| **Blocks** | T-13 |
| **Test cases** | (a) Happy path: file with two Google-style functions → correct DocEntry list. (b) File with no docstrings → empty list. (c) Empty `.py` file → empty list. (d) File with only a class docstring → one DocEntry. (e) `ast.parse` failure (invalid Python) → empty list, warning on stderr. |

---

#### T-10 · Unit tests — `ReadmeManager`
| Field | Detail |
|---|---|
| **File(s)** | `tests/test_sync_docs.py` |
| **Depends on** | T-03 |
| **Blocks** | T-13 |
| **Test cases** | (a) `read_section` on README with `## API Reference` section → returns body. (b) `read_section` on README with no section → returns `""`. (c) `read_section` on missing README → returns `""`. (d) `write_section` on README with existing section → overwrites only that section. (e) `write_section` on README with no section → appends heading + content. (f) `write_section` on missing README → creates file. |

---

#### T-11 · Unit tests — `ChangeDetector`
| Field | Detail |
|---|---|
| **File(s)** | `tests/test_sync_docs.py` |
| **Depends on** | T-04 |
| **Blocks** | T-13 |
| **Test cases** | (a) Identical strings → `False`. (b) Trailing newline difference → `False` (strip). (c) Different content → `True`. (d) Both empty strings → `False`. |

---

#### T-12 · Unit tests — `GitCommitter`
| Field | Detail |
|---|---|
| **File(s)** | `tests/test_sync_docs.py` |
| **Depends on** | T-05 |
| **Blocks** | T-13 |
| **Test cases** | (a) `get_short_hash()` returns a non-empty string in a git repo. (b) `stage_and_commit` on a modified file creates a new commit. (c) `stage_and_commit` with simulated `git commit` failure → README restored to original content, exits 1. |

---

#### T-13 · Integration test — end-to-end
| Field | Detail |
|---|---|
| **File(s)** | `tests/test_sync_docs.py` |
| **Depends on** | T-09, T-10, T-11, T-12, T-06 |
| **Blocks** | T-14 |
| **Test cases** | (a) Fresh temp repo + one `.py` with Google-style docstrings → `main()` runs → `README.md` now has `## API Reference` section → one new commit exists. (b) Running `main()` again with no changes → no new commit → exit 0. (c) Update docstring → run `main()` → README section updated → new commit. |

---

### Phase 6 — Smoke Test

#### T-14 · Install hook and manual smoke test
| Field | Detail |
|---|---|
| **File(s)** | `.git/hooks/pre-push` (installed) |
| **Depends on** | T-08, T-13 (all tests passing) |
| **Blocks** | — (final task) |
| **Description** | Run `sh install_hook.sh`. Add a `.py` file with a Google-style docstring to the repo root. Commit it. Run `git push`. Verify: (a) hook ran without error; (b) `README.md` contains `## API Reference` with the function's docstring; (c) a sync commit appears in `git log`. |
| **Done when** | All three verification points pass. |

---

## 3. Blocked Tasks Summary

| Task | Blocked until | Reason |
|---|---|---|
| T-05 | T-03 complete | Rollback in `GitCommitter` saves/restores README content — needs `ReadmeManager` path to be settled |
| T-06 | T-02 + T-03 + T-04 + T-05 all complete | `main()` orchestrates all four components |
| T-07 | T-06 complete | Hook invocation path (`src/sync_docs.py`) must be confirmed working |
| T-08 | T-07 complete | Installer copies the template file — template must exist first |
| T-09–T-12 | Respective component (T-02–T-05) | Cannot test what hasn't been written |
| T-13 | T-09 + T-10 + T-11 + T-12 complete | Integration test assumes all units pass |
| T-14 | T-08 + T-13 complete | Smoke test requires installer and green test suite |

---

## 4. Parallel Work Opportunities

| Group | Tasks | Can run in parallel because |
|---|---|---|
| A | T-02, T-03, T-04 | Independent components; no shared state |
| B | T-09, T-10, T-11 | Unit tests for independent components |

---

## 5. Implementation Order (sequential execution)

```
T-01 → T-02 + T-03 + T-04 (parallel)
     → T-05
     → T-06
     → T-07 + T-09 + T-10 + T-11 (parallel)
     → T-08 + T-12
     → T-13
     → T-14
```

Total tasks: **14**  
Estimated implementation phases: **6**
