# Implementation Plan: CLAUDE-3 `--dry-run` for `src/sync_docs.py`

Inputs: `docs/claude3/architecture.md`, `docs/claude3/design-review.md` (gate PASS, no open HIGH risks). FR-9 / `--src-dir` deferred to CLAUDE-2 (RISK-03 ACCEPTED, skipped placeholder test only).

Files touched: `src/sync_docs.py`, `tests/test_sync_docs.py` (extend, never recreate). Nothing else.

FIXED-risk coverage: RISK-02 -> T-01, T-08; RISK-01 -> T-05, T-12, T-13; RISK-07 -> T-11.

## Phase 0: Baseline

| ID | Phase | Task | Depends On | Notes |
|----|-------|------|------------|-------|
| T-01 | Baseline | In `tests/test_sync_docs.py`, change every `main()` call to `main([])` (7 call sites in 5 `TestIntegration` tests, lines ~426, 443, 447, 456, 465, 480, 492). Run the full suite before the edit and record the baseline. | none | RISK-02. Current `main()` takes no argument, so `main([])` only passes once T-03 lands: commit T-01 together with T-03. Acceptance: no bare `main()` call remains in tests; baseline result noted; suite green after T-03. |

## Phase 1: Core (`src/sync_docs.py`)

| ID | Phase | Task | Depends On | Notes |
|----|-------|------|------------|-------|
| T-02 | Core | Add `import argparse` and `Optional`; add `parse_args(argv=None) -> Namespace` with `--dry-run` (`store_true`, help <= 100 chars, e.g. "Preview the README API Reference update without writing or committing."). Optional epilog: scan is CWD-relative and non-recursive; dry-run does not validate git (RISK-06, RISK-08). | none | Acceptance: `parse_args([]).dry_run is False`; `parse_args(["--dry-run"]).dry_run is True`; `--help` exits 0 and lists `--dry-run`; unknown flag exits 2. |
| T-03 | Core | Change to `main(argv=None)`; call `args = parse_args(argv)` first inside `try`. Introduce local `source_dir = Path(".")` and glob from it (DD-6). No other behaviour change. `__main__` guard keeps calling `main()`. | T-02 | Acceptance: with T-01 applied, all pre-existing tests pass; `python src/sync_docs.py` with no args behaves as before. |
| T-04 | Core | Add `ReadmeManager.render_section(content)` returning `f"{_HEADING}\n{content}"`; make `write_section` use it for `new_section`. | none | Acceptance: existing `TestReadmeManager` tests pass unchanged; `render_section("x\n") == "## API Reference\nx\n"`. |
| T-05 | Core | Dry-run branch in `main`, after `has_changed`. Unchanged: print `README.md is up to date` to stdout, exit 0 (real run keeps stderr message). Changed: force UTF-8 on stdout (`sys.stdout.reconfigure(encoding="utf-8")` guarded by `hasattr`, else write encoded bytes to `sys.stdout.buffer` and flush), then `sys.stdout.write(manager.render_section(new_content))`, exit 0. Exit before reading `original_readme`, `write_section`, or constructing `GitCommitter`. UTF-8 handling in dry-run only. | T-03, T-04 | RISK-01, DD-2/3/4. Acceptance: `python src/sync_docs.py --dry-run` in a temp dir prints the section, README unchanged, no git invoked; real-run output unchanged. |

## Phase 2: Tests (new `TestDryRun` class in `tests/test_sync_docs.py`)

Style follows the existing unittest file: temp dir plus `os.chdir` in setUp/tearDown, `redirect_stdout`/`redirect_stderr`, `patch("sync_docs.subprocess.run")`, `assertRaises(SystemExit)`.

| ID | Phase | Task | Depends On | Notes |
|----|-------|------|------------|-------|
| T-06 | Tests | `TestDryRun` scaffold: setUp/tearDown, fixture `sample.py` from `GOOGLE_STYLE_PY`, helper `_run(argv)` returning `(code, stdout, stderr)`. Tests: `--help` lists `--dry-run` and its help line <= 100 chars; unknown flag exits 2. | T-01, T-05 | FR-10, NFR-7, KL-3. |
| T-07 | Tests | Changed-section: stdout equals `ReadmeManager().render_section(expected)`, exit 0; README bytes and mtime unchanged; `subprocess.run` mock `assert_not_called()`. | T-06 | FR-1..5, 8, 16, 17; NFR-1, 6, 8. |
| T-08 | Tests | Regression: `main([])` real run with mocked subprocess writes README, calls `git rev-parse`, `git add`, `git commit` in order, stderr messages unchanged; matches old `main()` behaviour. | T-06 | FR-11, RISK-02. |
| T-09 | Tests | Up-to-date and missing inputs: README current -> stdout has `README.md is up to date`, exit 0, stderr lacks it; README missing -> section on stdout, file not created; README without section -> section on stdout, bytes unchanged; no `.py` files -> stderr warning, empty stdout, no subprocess, exit 0. | T-06 | FR-6, 7, 12, 13, 14; DD-4. |
| T-10 | Tests | Warnings/errors: syntax-error file plus non-UTF-8 file -> warnings on stderr, only preview on stdout; `DocstringExtractor.extract` patched to raise -> exit 1, `unexpected error` on stderr, README unchanged. Pin RISK-04 cases: no docstrings + missing README, no docstrings + section-less README, docstrings removed -> empty heading. | T-06 | FR-15, 17, 18; KL-4. |
| T-11 | Tests | Preview equals real run: capture dry-run stdout; real run (mocked subprocess success) on an identical fixture; `read_text(encoding="utf-8")` README, `ReadmeManager.read_section`, compare with stdout minus heading after `.replace("\r\n", "\n")`. | T-06 | NFR-2, RISK-07. Must pass on Windows. |
| T-12 | Tests | UTF-8 subprocess test: docstring with `→` and a CJK character; run `sys.executable <abs path>/src/sync_docs.py --dry-run` with `cwd=tmp` and `PYTHONIOENCODING=cp1252`; expect exit 0 and stdout bytes decoding as UTF-8 to the expected section. | T-06 | RISK-01a. Env var is overridden by `reconfigure`, which is the point. |
| T-13 | Tests | Non-UTF-8 source under cp1252 stdout: file with `\xff\xfe` plus a docstring; expect exit 0, `non-UTF-8` warning on stderr, preview on stdout. | T-06 | RISK-01b, FR-15. Share the T-12 subprocess helper (same author, or serialize after T-12). |
| T-14 | Tests | `@unittest.skip("FR-9: needs CLAUDE-2")` placeholder `test_dry_run_with_src_dir`, docstring pointing at DD-6 notes. | T-06 | KL-1, RISK-03. Test output must show 1 skipped. |
| T-15 | Tests | Optional integration: temp `git init` repo (`_init_git_repo`), `git status --porcelain` and README hash identical before and after dry-run. | T-06 | NFR-1. |

## Phase 3: Docs and hardening

| ID | Phase | Task | Depends On | Notes |
|----|-------|------|------------|-------|
| T-16 | Docs | README mention of `--dry-run`: SKIPPED by your condition. `README.md` has only an intro paragraph and the hook-managed `## API Reference`; there is no Usage section. Do not edit the API Reference section. | none | Revisit if a Usage section is added. `--help` (T-02) is the user-facing doc. |
| T-17 | Hardening | Release gate: `python -m unittest tests.test_sync_docs -v` and `pytest tests/test_sync_docs.py` on Windows; all pre-existing CLAUDE-1 tests pass, new tests pass, 1 skipped. Manual: `python src/sync_docs.py --dry-run > preview.md` gives UTF-8 bytes; `git status` clean afterwards; hook path (`python src/sync_docs.py`, no args) works; `git diff --stat` shows only the two files. | T-07..T-15 | |

## Dependency Order

(T-02 -> T-03, with T-01 committed alongside) and T-04 -> T-05 -> T-06 -> T-07..T-15 -> T-17.

## Parallel Groups

- T-02, T-04 can run in parallel (independent edits: `parse_args` vs `render_section`); T-01 can be prepared alongside but is committed with T-03 so the suite is never red.
- T-07, T-08, T-09, T-10, T-11, T-12, T-13, T-14, T-15 can run in parallel once T-06 is done (independent test methods in one class; serialize merges since they share one file; T-13 reuses T-12's helper).
- T-16 (skipped) is independent of everything.
- T-17 is strictly last.
