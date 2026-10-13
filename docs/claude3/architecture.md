# Architecture: CLAUDE-3 Add --dry-run flag to sync_docs.py

Source requirements: `docs/claude3/requirements.md` (approved; A1-A5 and Q1-Q6 defaults accepted; FR-9 waived under C-7 and deferred to CLAUDE-2; Q4 resolved as deferred). Design-review mitigations RISK-01, RISK-02, RISK-07 are folded in below.
Scope: `src/sync_docs.py` only (C-1), standard library only (C-4), Python 3.8+ (NFR-5).

## 1. Component Overview

The script stays a single file. Existing components are unchanged except where noted. The change adds one function (`parse_args`), one small method (`ReadmeManager.render_section`), and a branch in `main`.

| Component | Status | Responsibility | Public interface | Requirements |
|-----------|--------|----------------|------------------|--------------|
| `parse_args` | NEW | Define the CLI and turn `argv` into a `Namespace`. Sole owner of flag definitions and `--help` text. | `parse_args(argv: Optional[list] = None) -> argparse.Namespace` with `.dry_run: bool` | FR-1, FR-10, NFR-7 |
| `main` | CHANGED | Orchestrate: scan, extract, format, detect change, then either preview (dry-run) or write+commit (real). Owns exit codes and stdout/stderr routing. | `main(argv: Optional[list] = None) -> None` (exits via `sys.exit`) | FR-2..8, FR-11..FR-18, NFR-3 |
| `DocstringExtractor` | unchanged | Parse one file and return `DocEntry` list; emits parse-error and non-UTF-8 warnings to stderr. | `extract(file_path) -> list[DocEntry]` | FR-15 |
| `_format_entries` | unchanged | Render entries to the Markdown section body. | `_format_entries(entries) -> str` | NFR-2, NFR-3 |
| `ReadmeManager` | CHANGED (one method added) | Read the existing section, render the full section text, and write it. `render_section` is the single source of the text that is either previewed or written. | `read_section(path) -> str`; NEW `render_section(content) -> str`; `write_section(path, content) -> None` (now calls `render_section`) | FR-2, FR-12, FR-13, NFR-2 |
| `ChangeDetector` | unchanged | Compare old and new section content. | `has_changed(old, new) -> bool` | FR-6, FR-8, NFR-3 |
| `GitCommitter` | unchanged | `git rev-parse`, `git add`, `git commit`, with rollback. Never constructed in dry-run. | `get_short_hash()`, `stage_and_commit(path, original, message)` | FR-4, FR-5, FR-16 |

### Component notes

- `render_section(content)` returns `f"{_HEADING}\n{content}"`. `write_section` uses it for the new section, so the previewed text is by construction what the real run writes (NFR-2). The heading is included in the preview (A3/Q1 default).
- `main` is the only place that knows about `dry_run`. No other component receives the flag (NFR-3).

## 2. Data Flow

Shared path (identical in both modes):

1. `main(argv)` calls `parse_args(argv)`. On `--help` argparse prints help and exits 0; on an unknown flag argparse exits 2 (see KL-3).
2. `main` resolves `readme_path = Path("README.md")` and `source_dir = Path(".")` (see DD-6), then globs `*.py` in `source_dir`.
3. If no files: print the existing warning to stderr and `sys.exit(0)`. No git or file operations occur in either mode (FR-14).
4. For each file, `DocstringExtractor.extract` runs. Parse-error and non-UTF-8 warnings go to stderr in both modes (FR-15).
5. `_format_entries` produces `new_content`.
6. `ReadmeManager.read_section` returns `old_content`. It returns `""` for a missing README or missing section (FR-12, FR-13).
7. `ChangeDetector.has_changed(old_content, new_content)` decides.

Unchanged branch (step 7 is False):

- Real run: print "sync_docs: no docstring changes detected" to stderr, exit 0 (FR-11, A2).
- Dry run: print "README.md is up to date" to stdout, exit 0 (FR-6, FR-7, A1/Q2).

Changed branch (step 7 is True):

- Dry run (FR-2, FR-3, FR-4, FR-5, FR-8, FR-16, FR-17):
  8d. `sys.stdout.write(manager.render_section(new_content))`.
  9d. `sys.exit(0)`. No README read-for-rollback, no `write_section`, no `GitCommitter`.
- Real run (unchanged behaviour, FR-11):
  8r. Read `original_readme`, `write_section`, then `GitCommitter.get_short_hash`, `stage_and_commit`, print the success message to stderr, exit 0.

Error path: any `Exception` in steps 2-8 is caught by the existing handler, which prints to stderr and exits 1. Because dry-run performs no write, README.md is unchanged (FR-18). `SystemExit` is not an `Exception`, so deliberate exits pass through unaffected.

## 3. Key Data Structures

No new types cross component boundaries.

- `DocEntry(name, signature, docstring)` (existing namedtuple): extractor to formatter.
- `argparse.Namespace` with a single boolean `dry_run` (default `False`): `parse_args` to `main`.
- Plain `str` for section content (`old_content`, `new_content`) and the rendered section (`render_section` output).

Process contract (not a data type):

| Mode | stdout | stderr | Exit |
|------|--------|--------|------|
| dry-run, changed | full section incl. `## API Reference` heading, exactly as written by a real run | warnings only | 0 |
| dry-run, up to date | `README.md is up to date` | warnings only | 0 |
| dry-run, no files | nothing | no-files warning | 0 |
| dry-run, unexpected error | nothing | `sync_docs: unexpected error: ...` | 1 |
| real run | nothing (unchanged) | unchanged messages | unchanged |

## 4. Architecture Decision Records

### DD-1: Introduce argparse via `parse_args(argv)` and `main(argv=None)`
**Context:** The script has no CLI parsing and `main()` takes no arguments, so it cannot be tested with different flags without patching `sys.argv`. FR-1 and FR-10 need a flag and help text.
**Decision:** Add `parse_args(argv=None)` that builds an `argparse.ArgumentParser` and returns the namespace. `main(argv=None)` calls it first. The flag is `--dry-run` with `action="store_true"` and a one-line help (<= 100 chars), for example "Preview the README API Reference update without writing or committing."
**Rationale:** argparse is stdlib (C-4), gives `--help` for free (FR-10), and passing `argv` explicitly lets tests call `main(["--dry-run"])` directly. Keeping `sys.exit` inside `main` preserves existing exit semantics (C-6); tests use `pytest.raises(SystemExit)` and inspect `.code`.
**Consequence:** `main` gains an optional parameter; the `__main__` guard and the pre-push hook invocation (`python src/sync_docs.py`, no args) behave as before (FR-11). Invalid flags now exit 2 (argparse default), which is new but only affects previously meaningless input.
**Existing tests (RISK-02):** `main(argv=None)` makes argparse read `sys.argv`, which holds runner arguments under pytest/unittest and would exit 2. Therefore every existing `main()` call in `tests/test_sync_docs.py` (e.g. `TestIntegration`) is changed to `main([])` as part of this change. The script and hook keep calling `main()` so they read the real command line.

### DD-2: Gate only write and commit on the flag
**Context:** NFR-3 requires the preview to be the same content a real run writes, and NFR-4 forbids extra scans.
**Decision:** The extract, format, read-section and change-detect steps run unconditionally. `dry_run` is checked once, after change detection, to choose between "print and exit" and "write and commit". `GitCommitter` is not instantiated in dry-run.
**Rationale:** A single branch point makes drift between preview and real behaviour structurally impossible and keeps the diff small. Not constructing `GitCommitter` guarantees no git subprocess runs (FR-4, FR-5, FR-16, NFR-8), including the read-only `git rev-parse`, which is unnecessary for a preview (Q6: works outside a repo).
**Consequence:** The test that mocks `subprocess.run` and asserts it is never called (NFR-6) is a direct check of this boundary.

### DD-3: Preview to stdout, diagnostics to stderr, via `render_section`
**Context:** FR-17 separates preview from diagnostics so output can be piped (`sync_docs.py --dry-run > preview.md`). NFR-2 requires preview text to equal written text.
**Decision:** Extract `ReadmeManager.render_section(content)` and have both `write_section` and the dry-run print use it. Emit the preview with `sys.stdout.write(...)` (not `print`) so no extra trailing newline is added. No banner or header (Q3 default). **UTF-8 output (RISK-01, dry-run only):** before writing the preview, call `sys.stdout.reconfigure(encoding="utf-8")` guarded with `hasattr(sys.stdout, "reconfigure")` (available since 3.7, safe for the 3.8+ floor); if unavailable, write `render_section(...).encode("utf-8")` to `sys.stdout.buffer` and flush. This is done only in the dry-run branch, so real-run behaviour is unchanged (FR-11).
**Rationale:** One function producing the text is simpler and more reliable than two code paths that must be kept equal. `sys.stdout.write` avoids the `print` newline discrepancy. Forcing UTF-8 makes the preview independent of the Windows console code page, so non-encodable characters (arrows, CJK, U+FFFD from non-UTF-8 sources) do not raise `UnicodeEncodeError` and the preview bytes match the UTF-8 that `write_text(encoding="utf-8")` writes (NFR-2, NFR-5).
**Consequence:** Existing warnings stay on stderr untouched. The heading is part of the preview (A3). Dry-run changes the stdout encoding of the process, which is acceptable as the process exits right after.

### DD-4: Up-to-date message goes to stdout in dry-run, stderr message unchanged in real run
**Context:** The AC requires "README.md is up to date"; the existing message is on stderr. A1/Q2 default: dry-run uses stdout; FR-11/A2 require real-run behaviour to be unchanged.
**Decision:** In the unchanged branch, if `dry_run` print `README.md is up to date` to stdout, else keep the existing stderr message. Exit 0 in both.
**Rationale:** In dry-run the message is the primary result the user asked for, so it belongs on stdout. Unifying would change real-run output, violating FR-11.
**Consequence:** Two messages exist for the same condition, accepted (KL-2).

### DD-5: Missing README or missing section needs no special handling
**Context:** FR-12 and FR-13 require dry-run to print the new section and not create or modify README.md when the file or section is absent.
**Decision:** Rely on `read_section` already returning `""` for both cases, so `has_changed("", new_content)` is True whenever there is non-empty content. Dry-run then prints the rendered section and exits without calling `write_section`, which is the only code that creates or edits the file.
**Rationale:** No new branches, and the real run follows the same path (it appends the section or creates the file), so the preview matches what would be written.
**Consequence:** Edge case: if there are no docstrings at all (`new_content == ""`) and README or section is missing, `has_changed` is False and the up-to-date message is printed. This is existing change-detection behaviour and is preserved (KL-4).

### DD-6: `--src-dir` (CLAUDE-2) is not implemented here; FR-9 deferred
**Context:** C-7: `--src-dir` does not exist in the code. FR-9 depends on it. Q4 (merge order) is unanswered. The code currently hardcodes `Path(".")` in `main`.
**Decision (minimal, user-approved option (a)):** CLAUDE-3 does not add `--src-dir`. FR-9 and its AC are explicitly waived under C-7 in requirements.md and deferred to CLAUDE-2 (owner); Q4 is resolved as deferred. To make that later change trivial, `main` holds the scan directory in a single local `source_dir = Path(".")` and globs from it; no behaviour changes. If CLAUDE-2 merges first, it adds one argparse argument in `parse_args` and sets `source_dir` from it; dry-run composes with it with no further work because the scan precedes the flag branch (DD-2). If CLAUDE-3 merges first, CLAUDE-2 does the same on top.
**Rationale:** Implementing `--src-dir` here would exceed the ticket scope (C-1, C-5), risk conflicting with CLAUDE-2's own semantics (relative vs absolute, recursion, README location), and invent requirements. A stub flag that does nothing would be misleading.
**Consequence:** FR-9 is untestable until CLAUDE-2 lands. A placeholder `@unittest.skip("FR-9: needs CLAUDE-2")` test is added so the gap is visible in test output; CLAUDE-2 replaces it with a real test. Passing `--src-dir` now fails with argparse exit 2.
**Notes for CLAUDE-2:** resolve `--src-dir` with `Path.resolve()`; require it to be an existing directory (error otherwise); decide explicitly whether paths outside the repo root are allowed; set `source_dir` from it in `main` (dry-run then composes with no further work, DD-2).

### DD-7: Keep everything in `src/sync_docs.py`; no new module or dependency
**Context:** C-1 and the design principle of minimal moving parts.
**Decision:** All changes are in the single existing file; tests go in a separate test file.
**Rationale:** The change is about 20 lines. Splitting would add structure with no benefit.
**Consequence:** None beyond the file growing slightly.

## 5. Testing Strategy

Framework: `pytest` (or `unittest`) with `tmp_path`, `monkeypatch.chdir(tmp_path)` (the script uses the CWD), `capsys`, and `unittest.mock.patch("subprocess.run")`. Tests call `main([...])` directly and catch `SystemExit`. Test file: the existing `tests/test_sync_docs.py` is extended with a new `TestDryRun` class; it must not be recreated (existing T-09 to T-13 suites are kept). Existing `main()` calls are changed to `main([])` (DD-1, RISK-02). The full existing suite is run before and after the change and is a gate. No other scripts are modified.

Fixture: a tmp dir with a small `.py` file containing a documented function, plus an optional README.md.

| Test | Covers |
|------|--------|
| `--help` output lists `--dry-run`; its help line is <= 100 chars | FR-10, NFR-7 |
| Dry-run, section differs: stdout equals `render_section(expected)`; exit code 0 | FR-1, FR-2, FR-8, FR-17 |
| Dry-run, section differs: README bytes and mtime unchanged | FR-3, NFR-1 |
| Dry-run: `subprocess.run` mock `assert_not_called()` | FR-4, FR-5, FR-16, NFR-6, NFR-8 |
| Dry-run, README already current: stdout contains `README.md is up to date`, exit 0, stderr empty of that text | FR-6, FR-7, DD-4 |
| Dry-run with README missing: section on stdout; README.md not created | FR-12 |
| Dry-run with README lacking the section: section on stdout; bytes unchanged | FR-13 |
| Dry-run with no `.py` files: no-files warning on stderr, stdout empty, no subprocess, exit 0 | FR-14 |
| Dry-run with a syntax-error file and a non-UTF-8 file: warnings on stderr, stdout carries only the preview | FR-15, FR-17 |
| Dry-run with `DocstringExtractor.extract` patched to raise: stderr message, exit 1, README unchanged | FR-18 |
| Preview equals real run: run dry-run and capture stdout; run real run with `subprocess.run` mocked to return success; read README.md with `read_text(encoding="utf-8")`, extract the section via `ReadmeManager.read_section`, and compare with the stdout text after `.replace("\r\n", "\n")` (Windows newline translation, RISK-07). Run on Windows as well as CI | NFR-2 |
| Real run (no flag) with mocked subprocess: README written, `git add` then `git commit` called, stderr messages unchanged | FR-11 |
| `main([])` behaves identically to the old `main()` (same README result, git calls and messages) | FR-11, RISK-02 |
| UTF-8 stdout (RISK-01a): docstring containing `→` and a CJK character, run in a subprocess with `PYTHONIOENCODING=cp1252`; expects exit 0 and UTF-8 bytes on stdout | FR-2, FR-18, NFR-2, NFR-5 |
| UTF-8 stdout (RISK-01b): non-UTF-8 source file in dry-run; expects exit 0, warning on stderr, preview on stdout | FR-15, FR-17 |
| Existing `TestIntegration` and other CLAUDE-1 tests, with calls changed to `main([])`, still pass (gate) | FR-11, RISK-02 |
| `@unittest.skip("FR-9: needs CLAUDE-2")` placeholder: dry-run with `--src-dir` | FR-9 (waived under C-7) |
| Integration (optional, marked): in a temp `git init` repo, `git status --porcelain` and README hash identical before and after a dry run | NFR-1 |

NFR-4 (no extra scans) is satisfied by construction (DD-2) and needs no timing test. NFR-5 is covered by running the suite on Windows and Linux in CI if available; no platform-specific code is added.

## 6. Known Limitations

- **KL-1:** FR-9 (`--dry-run` with `--src-dir`) is waived under C-7, not delivered by CLAUDE-3, owned by CLAUDE-2, and covered only by a skipped placeholder test until then (DD-6).
- **KL-2:** The "no changes" condition is reported on stdout in dry-run and on stderr in real run, by design (DD-4).
- **KL-3:** Invalid or unknown arguments cause argparse to exit with code 2, which extends the 0/1 exit-code set of C-6 for malformed invocations only.
- **KL-4:** When there are no docstrings and README or section is missing, dry-run reports "up to date" rather than previewing an empty section, mirroring existing change detection (DD-5).
- **KL-5:** Dry-run does not verify that git is usable or that a commit would succeed (hooks, identity, nothing staged), because no git commands are run (Q6, FR-16). A real run can still fail where a dry run succeeded.
- **KL-6:** (Mitigated, RISK-01) Dry-run forces UTF-8 on stdout (DD-3), so a non-UTF-8 console code page no longer causes `UnicodeEncodeError`. Residual: the terminal itself may still display such characters incorrectly, and PowerShell 5.1 `>` redirection may re-encode the output; the bytes emitted by the script are UTF-8. Real-run stdout is unchanged.
- **KL-7:** The preview is the full section, not a diff (C-2).
