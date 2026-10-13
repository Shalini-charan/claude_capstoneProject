# Architecture

**Source:** docs/requirements.md (CLAUDE-1)  
**Project:** claudeCapStone (Agentic SDLC Capstone)  
**Date:** 2026-09-30  

---

## 1. System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        Developer Machine                     │
│                                                             │
│   git push                                                  │
│      │                                                      │
│      ▼                                                      │
│  ┌────────────────┐    invokes    ┌──────────────────────┐  │
│  │  Git Engine    │ ────────────▶ │  pre-push hook       │  │
│  │  (git CLI)     │               │  (.git/hooks/pre-push│  │
│  └────────────────┘               └──────────┬───────────┘  │
│                                              │ python        │
│                                              ▼               │
│                                  ┌──────────────────────┐   │
│                                  │    sync_docs.py       │   │
│                                  │   (Main Orchestrator) │   │
│                                  └──────────┬───────────┘   │
│                                             │                │
│               ┌─────────────────────────────┤                │
│               │             │               │                │
│               ▼             ▼               ▼                │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│   │  Docstring   │ │    README    │ │    Git       │        │
│   │  Extractor   │ │   Manager   │ │  Committer   │        │
│   └──────┬───────┘ └──────┬───────┘ └──────┬───────┘        │
│          │                │                │                 │
│          ▼                ▼                ▼                 │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│   │  *.py files  │ │  README.md   │ │  git CLI     │        │
│   │  (repo root) │ │  (repo root) │ │  (subprocess)│        │
│   └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Components

### 2.1 Pre-push Hook — `.git/hooks/pre-push`

| Attribute | Detail |
|---|---|
| **Type** | POSIX shell script |
| **Installed by** | `install_hook.sh` (one-time setup) |
| **Responsibility** | Entry point: receives Git push signal, invokes `sync_docs.py`, propagates exit code |
| **On exit 0** | Push proceeds normally |
| **On exit 1** | Push is aborted by Git |
| **Python detection** | Hook tries `python`, then `python3`, then `py` in order; exits 1 with a clear error if none is found on PATH (DD-04) |

### 2.2 Hook Installer — `install_hook.sh`

| Attribute | Detail |
|---|---|
| **Type** | Shell script (run once by developer) |
| **Responsibility** | Copies hook template into `.git/hooks/pre-push` and sets executable bit |
| **Idempotent** | Safe to run multiple times; overwrites existing hook |

### 2.3 Sync Script — `src/sync_docs.py`

The main orchestrator. Contains four internal modules (classes/functions within a single file to satisfy NFR-1 stdlib-only constraint).

#### 2.3.1 `DocstringExtractor`

| Attribute | Detail |
|---|---|
| **Input** | Path to a `.py` file |
| **Output** | List of `DocEntry` namedtuples: `{name, signature, docstring}` |
| **Library** | `ast` (parse tree), `inspect.cleandoc` equivalent via `textwrap.dedent` |
| **Scope** | Top-level `FunctionDef`, `AsyncFunctionDef`, `ClassDef` only (C-3) |
| **Format handled** | Google-style docstrings (FR-1) |
| **File encoding** | Files opened with `encoding='utf-8', errors='replace'`; files with replacement characters emit a warning to stderr (DD-03) |
| **DocEntry.signature** | Parameter list only, excluding the function name — e.g. `a: int, b: int` for `def add(a: int, b: int) -> int`. Rendered as `` ### `add(a: int, b: int)` `` (DD-06) |

#### 2.3.2 `ReadmeManager`

| Attribute | Detail |
|---|---|
| **Input** | Path to `README.md` |
| **Output** | Current `## API Reference` section content as string; writes updated content |
| **Create-if-missing** | Appends `## API Reference\n` + content if heading absent (FR-2, AC-4) |
| **Section boundary** | Section starts at `## API Reference`, ends at next `## ` heading or EOF |
| **Library** | `pathlib`, `re` |
| **Heading constraint** | The heading must be exactly `## API Reference` (case-sensitive, no trailing space or plural). Any variation causes a new duplicate section to be appended (DD-07) |

#### 2.3.3 `ChangeDetector`

| Attribute | Detail |
|---|---|
| **Input** | Old section string, new section string |
| **Output** | `bool` — `True` if content differs |
| **Comparison** | Stripped string equality (handles trailing whitespace/newline drift) |

#### 2.3.4 `GitCommitter`

| Attribute | Detail |
|---|---|
| **Responsibility** | Stage `README.md` and create a commit |
| **Commit message** | `docs: auto-sync from <short-hash>` |
| **Short hash** | `git rev-parse --short HEAD` via `subprocess.run` |
| **Library** | `subprocess`, `sys` |
| **Rollback** | Saves original README content before writing. If `git commit` fails, restores the original content before exiting 1 — prevents permanently dirty working tree (DD-02) |
| **On git failure** | Restores README, writes error to `stderr`, exits 1 → push aborted (FR-5) |

---

## 3. Data Flow

```
git push
   │
   ▼
[pre-push hook]
   │
   ├─ python src/sync_docs.py
   │       │
   │       ▼
   │  1. Discover all *.py in repo root  (pathlib.Path('.').glob('*.py'))
   │       │
   │       ▼
   │  2. For each .py file:
   │       ast.parse(source)
   │       Walk tree → FunctionDef / ClassDef nodes
   │       Extract name + signature + first string expr (docstring)
   │       Append to DocEntry list
   │       │
   │       ▼
   │  3. Format DocEntry list → Markdown string
   │       ### `name(signature)`
   │       <docstring body>
   │       │
   │       ▼
   │  4. ReadmeManager.read_section()
   │       Read README.md
   │       Locate ## API Reference heading
   │       Extract section text → old_content
   │       │
   │       ▼
   │  5. ChangeDetector.has_changed(old_content, new_content)
   │       │
   │       ├─ False → print "No docstring changes" to stderr
   │       │          exit(0)  ──────────────────────────────────▶ push proceeds
   │       │
   │       └─ True  → ReadmeManager.write_section(new_content)
   │                  GitCommitter.get_short_hash()
   │                  git add README.md
   │                  git commit -m "docs: auto-sync from <hash>"
   │                  exit(0)  ──────────────────────────────────▶ push proceeds
   │
   └─ exit(1) on any exception ────────────────────────────────▶ push ABORTED
```

---

## 4. File Structure

```
claude_capStone/
├── .git/
│   └── hooks/
│       └── pre-push              # installed by install_hook.sh
├── docs/
│   ├── requirements.md
│   ├── architecture.md
│   ├── design-review.md          # (Step 3)
│   └── impl-plan.md              # (Step 4)
├── src/
│   └── sync_docs.py              # main sync script (all 4 modules)
├── tests/
│   └── test_sync_docs.py         # unit + integration tests (Step 7)
├── install_hook.sh               # one-time developer setup
└── README.md                     # target document for auto-sync
```

---

## 5. Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.8+ | Required by NFR-1; universal on developer machines |
| Dependencies | stdlib only | NFR-1 — no `pip install`; `ast`, `re`, `pathlib`, `subprocess`, `sys`, `textwrap` |
| AST parser | `ast.parse` | Most reliable way to extract docstrings without running code |
| Git integration | `subprocess.run` | Stdlib; avoids GitPython dependency |
| Hook type | `pre-push` | Fires before push, has access to working tree; can abort push on failure |
| Hook language | POSIX `sh` | Compatible across macOS, Linux, Git Bash on Windows |
| Markdown format | GitHub-Flavored Markdown | NFR-4 — renders correctly on GitHub and most renderers |
| Single file | `src/sync_docs.py` (all classes in one file) | Simplifies hook invocation; no package install needed |

---

## 6. Key Interfaces

```
DocEntry = namedtuple('DocEntry', ['name', 'signature', 'docstring'])
  # name      : str  — function or class name, e.g. "add"
  # signature : str  — parameter list only, e.g. "a: int, b: int"
  # docstring : str  — dedented docstring body

DocstringExtractor
  extract(file_path: Path) -> list[DocEntry]

ReadmeManager
  read_section(readme_path: Path) -> str        # returns "" if section absent
  write_section(readme_path: Path, content: str) -> None

ChangeDetector
  has_changed(old: str, new: str) -> bool

GitCommitter
  get_short_hash() -> str
  stage_and_commit(file_path: Path, message: str) -> None
  # saves original content before writing; restores on commit failure (DD-02)

main() -> None   # orchestrates all four; called by pre-push hook
```

---

## 7. Error Handling Strategy

| Scenario | Behaviour |
|---|---|
| No `.py` files found | Write warning to `stderr`; **skip README update entirely**; exit 0 — no commit (DD-05) |
| `README.md` missing | Create `README.md` with `## API Reference` section; exit 0 |
| `ast.parse` fails on a file | Log file path to `stderr`; skip file; continue with remaining files |
| Non-UTF-8 `.py` file | Open with `errors='replace'`; write warning to `stderr`; continue (DD-03) |
| `git` not on `PATH` | Write error to `stderr`; exit 1 → push aborted |
| `git commit` fails | Restore original `README.md` content; write error to `stderr`; exit 1 → push aborted (DD-02) |
| Python not on `PATH` | Hook writes clear error ("python/python3/py not found"); exit 1 → push aborted (DD-04) |
| Any uncaught exception | Top-level `try/except`; write to `stderr`; exit 1 |

---

## 8. Known Limitations

### KL-1 — Sync commit is not included in the triggering push

When `git push` is invoked, Git determines the set of refs to transmit **before** the pre-push hook runs. If `sync_docs.py` creates a new commit during the hook, that commit is not included in the current push.

**Consequence:** After a successful push that triggered a sync, local `main` will be one commit ahead of the remote. The developer must run `git push` a second time to send the sync commit.

**Accepted trade-off:** The alternative (post-commit hook) would trigger on every commit including the sync commit itself, risking re-entrancy. Pre-push was the explicitly chosen trigger (FR-4). This limitation is acceptable for the capstone scope.

**User guidance:** If the terminal shows "docs: auto-sync from …" during a push, run `git push` once more to send the sync commit to the remote.
