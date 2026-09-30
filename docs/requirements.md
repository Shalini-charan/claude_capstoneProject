# Requirements

**Source:** CLAUDE-1 — Auto-sync README.md when Python docstrings change on push to main  
**Project:** claudeCapStone (Agentic SDLC Capstone)  
**Captured:** 2026-09-30  

---

## 1. Overview

Developers frequently update Python function docstrings but forget to update `README.md`, causing documentation drift. This feature introduces an automated sync tool that detects Google-style docstring changes in Python files and writes the updated content into a dedicated `README.md` section — triggered automatically by a Git pre-push hook, with no manual steps required.

---

## 2. Functional Requirements

### FR-1 — Docstring Extraction
- The tool MUST parse all `.py` files located in the **repository root** (non-recursive).
- The tool MUST extract **Google-style docstrings** from every top-level function and class using Python's `ast` module (stdlib only, no third-party dependencies).
- A Google-style docstring is defined as a triple-quoted string immediately following a `def` or `class` statement, optionally containing `Args:`, `Returns:`, `Raises:`, and `Attributes:` sections.

### FR-2 — README Section Update
- The tool MUST write extracted docstrings into a **dedicated section** of `README.md`, identified by the heading `## API Reference`.
- If the `## API Reference` section does not exist in `README.md`, the tool MUST **create it automatically** by appending it to the end of the file.
- If the section already exists, the tool MUST **overwrite** its content entirely with the latest extracted docstrings.
- Each function/class entry in the section MUST follow this format:
  ```
  ### `function_name(signature)`
  <docstring body>
  ```

### FR-3 — Change Detection
- The tool MUST compare the newly extracted docstring content against the current `## API Reference` section in `README.md`.
- If the content is **identical**, the tool MUST exit cleanly with exit code `0` and make **no commit**.
- If the content has **changed**, the tool MUST overwrite the section and create a Git commit with the message:  
  `docs: auto-sync from <short-commit-hash>`

### FR-4 — Git Pre-Push Hook Integration
- The sync script MUST be installed as a **Git pre-push hook** (`./git/hooks/pre-push`).
- The hook MUST run the sync script automatically before every `git push`.
- If the sync script exits with a non-zero code, the push MUST be aborted.
- The hook MUST be a standard shell script that invokes `python sync_docs.py`.

### FR-5 — Exit Behaviour
- Exit code `0`: no docstring changes detected, or sync committed successfully.
- Exit code `1`: any unhandled error (missing Python, unreadable file, git command failure).

---

## 3. Non-Functional Requirements

### NFR-1 — Runtime
- The tool MUST run on **Python 3.8+** using the **standard library only** (`ast`, `re`, `subprocess`, `pathlib`, `sys`). No `pip install` required.

### NFR-2 — Performance
- The tool MUST complete within **5 seconds** for a repository with up to 20 `.py` files.

### NFR-3 — Idempotency
- Running the tool twice on an unchanged codebase MUST produce no new commits and exit `0` both times.

### NFR-4 — Readability
- The generated `## API Reference` section MUST be valid GitHub-Flavored Markdown, readable in any Markdown renderer.

### NFR-5 — Error Messages
- All error output MUST be written to `stderr`.
- Error messages MUST be human-readable and identify the failing file or git command.

---

## 4. Constraints & Assumptions

| # | Constraint / Assumption |
|---|---|
| C-1 | The repository is a local Git repo with `git` available on `PATH`. |
| C-2 | `README.md` exists in the repository root. If it does not exist, the tool creates it. |
| C-3 | Only top-level functions and classes (not nested) are extracted in this version. |
| C-4 | The tool runs in the context of the pre-push hook — it has access to the working tree. |
| C-5 | Only the `main` branch is in scope; pushes to other branches still trigger the hook but changes only apply when pushing to `main`. |

---

## 5. Out of Scope

- Nested functions or methods inside classes (deferred to a future version).
- Docstrings in files outside the repo root (sub-directories not scanned).
- NumPy-style or reStructuredText docstrings.
- GitHub Actions / CI-based triggering.
- Confluence, Sphinx, or any external documentation system.
- Docstring linting or validation.

---

## 6. Acceptance Criteria (from CLAUDE-1)

| # | Criterion |
|---|---|
| AC-1 | On every push to `main`, the script scans `.py` files in the repo root for docstring changes. |
| AC-2 | Changed docstrings are extracted and written into the `## API Reference` section of `README.md`. |
| AC-3 | The script commits the updated README with message `docs: auto-sync from <commit-hash>`. |
| AC-4 | If no docstrings changed, no commit is made and the script exits cleanly (exit code 0). |
