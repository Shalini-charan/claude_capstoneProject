# Design Review: CLAUDE-3 `--dry-run` for `src/sync_docs.py`

Reviewed: `docs/claude3/architecture.md` against `docs/claude3/requirements.md`, `src/sync_docs.py` (current, pre-change), `tests/test_sync_docs.py` and `hooks/pre-push.template`.

Status vocabulary: OPEN (needs action), ACCEPTED (deliberate trade-off, rationale given), FIXED (resolved). "Resolved" in the review request means ACCEPTED or FIXED.

## Summary

| Severity | Count | Open |
|----------|-------|------|
| HIGH | 2 | 0 (RISK-01 FIXED, RISK-02 FIXED) |
| MEDIUM | 1 | 0 (RISK-03 ACCEPTED, waiver recorded) |
| LOW | 5 | 0 (RISK-07 FIXED; RISK-04, 05, 06, 08 ACCEPTED) |

Re-run after user-approved decisions were folded into `architecture.md` and `requirements.md`. No CRITICAL, HIGH or MEDIUM risks remain open; no open risks of any severity remain.

Verified non-risks:
- The pre-push hook runs `"$PYTHON_CMD" "$SCRIPT"` with no arguments, so adding argparse does not break the hook (FR-11 holds for the hook path).
- `SystemExit` is not an `Exception`, so deliberate `sys.exit` calls inside the `try` in `main` pass through the existing handler as the architecture states.
- Not constructing `GitCommitter` in dry-run does keep all subprocess calls out of that path (FR-4, FR-5, FR-16, NFR-8).

---

### RISK-01: Windows stdout encoding makes the preview fail or differ from the written README (KL-6 is under-rated)
**Severity:** HIGH
**Component:** `main` dry-run branch (`sys.stdout.write(manager.render_section(...))`), DD-3, KL-6
**Scenario:** The development platform is Windows (PowerShell). Python's stdout uses the console or locale code page (for example cp1252), not UTF-8.
1. A docstring contains a character the code page cannot encode (an arrow, a CJK character, an emoji). `sys.stdout.write` raises `UnicodeEncodeError`. The generic `except Exception` turns this into `sync_docs: unexpected error` with exit 1, so the preview feature fails on exactly the input where a user most wants to inspect output.
2. `DocstringExtractor` reads with `errors="replace"`, so a non-UTF-8 source file yields U+FFFD in docstrings. U+FFFD is not encodable in cp1252, so the FR-15 scenario (non-UTF-8 file plus dry-run) fails with exit 1 instead of printing a preview and a warning.
3. Characters that are encodable (for example an accented letter) are written as cp1252 bytes to stdout but as UTF-8 to README.md by `write_text(encoding="utf-8")`. `sync_docs.py --dry-run > preview.md` then differs byte-wise from what a real run writes, which violates NFR-2. PowerShell 5.1 `>` adds its own re-encoding on top.
The architecture defers this as "not mitigated to stay within scope", but the fix is inside `src/sync_docs.py` (C-1) and is a few lines. It also conflicts with NFR-5 (Windows is a stated platform) and NFR-2.
**Mitigation:** In the dry-run branch, emit UTF-8 explicitly and independent of the console code page. Either call `sys.stdout.reconfigure(encoding="utf-8")` (available since 3.7, so safe for the 3.8+ floor) guarded with `hasattr`, or write bytes: `sys.stdout.buffer.write(text.encode("utf-8"))` followed by `flush()`. Do this only in dry-run so real-run behaviour is unchanged (FR-11). Update DD-3 and delete the "not mitigated" wording in KL-6. Add tests: (a) a docstring containing `→` and a CJK character, run under `PYTHONIOENCODING=cp1252` in a subprocess, expects exit 0 and UTF-8 bytes on stdout; (b) a non-UTF-8 source file in dry-run expects exit 0, the warning on stderr, and a preview on stdout.
**Status:** FIXED (mitigation adopted in architecture: DD-3 forces UTF-8 in dry-run only, KL-6 rewritten, both tests added to section 5)

### RISK-02: `main(argv=None)` makes argparse read `sys.argv`, which breaks existing tests that call `main()`
**Severity:** HIGH
**Component:** `parse_args`, `main`, DD-1, Testing Strategy (section 5)
**Scenario:** `tests/test_sync_docs.py` already exists and its `TestIntegration` cases call `main()` with no arguments (for example `test_first_run_creates_api_reference_section`). After DD-1, `main()` calls `parse_args(None)`, and argparse parses `sys.argv[1:]`. Under `pytest -q tests/test_sync_docs.py`, `python -m unittest tests.test_sync_docs -v`, or the repo's `.claude/hooks/run_tests_hook.py`, `sys.argv` holds runner arguments. argparse then prints "unrecognized arguments" and exits 2. Those tests fail with an unexpected exit code and CLAUDE-1 regression coverage is lost. Separately, the architecture says the test file is "new", but it exists; writing it as new would overwrite the existing T-09 to T-13 suites.
**Mitigation:** Update every existing `main()` call in `tests/test_sync_docs.py` to `main([])` as part of this change (tests are allowed by C-1). Keep `main(argv=None)` and `parse_args(argv=None)` so the script and hook still read the real command line. Change section 5 to say "extend the existing `tests/test_sync_docs.py` (add a `TestDryRun` class); do not recreate it". Add a test that `main([])` behaves identically to the old `main()` (FR-11). Run the full existing suite before and after as a gate.
**Status:** FIXED (mitigation adopted in architecture: DD-1 requires `main([])` in existing tests, section 5 extends the existing file with `TestDryRun`, adds the `main([])` equivalence test, and makes the existing suite a gate)

### RISK-03: FR-9 / `--src-dir` deferral leaves an acceptance criterion undeliverable and untested
**Severity:** MEDIUM (escalate to HIGH if the Jira acceptance criteria literally list dry-run plus `--src-dir` and no waiver is recorded)
**Component:** DD-6, KL-1, Testing Strategy, requirements C-7 and Q4
**Scenario:**
- The requirements list FR-9 as a functional requirement, and NFR-6 says unit tests "shall cover each acceptance criterion (AC1-AC6)". The architecture ships no FR-9 test and states FR-9 "is not part of CLAUDE-3 acceptance". Both cannot hold: either FR-9 maps to an AC (then NFR-6 and the ticket's acceptance fail) or it does not (then the requirements document should say so).
- The architecture header says "Q1-Q6 defaults accepted", but Q4 (is CLAUDE-2 merged first?) has no default and the requirements note no CLAUDE-2 artefacts exist. The deferral decision therefore rests on an unanswered question.
- `main --dry-run --src-dir x` exits 2 with an argparse error, which looks like a bug to someone following the ticket text.
- `source_dir = Path(".")` is a refactor with no consumer and no test. Whichever ticket merges second owns the FR-9 test, with no tracking item to enforce it, so the test can be forgotten.
- When CLAUDE-2 lands, `--src-dir` is a user-controlled path. It must be resolved and handled deliberately (absolute or relative, symlinks, scope outside the repo), which the dry-run design does not discuss.
**Mitigation:**
1. Get an explicit decision from the ticket owner on Q4 and record it in `requirements.md`. Either remove FR-9 from the CLAUDE-3 requirement set and mark the matching AC as waived or moved to CLAUDE-2, or implement a minimal `--src-dir` here.
2. If deferred, create a Jira link or sub-task "add FR-9 dry-run + `--src-dir` test" blocked by CLAUDE-2, and add a `@unittest.skip("FR-9: needs CLAUDE-2")` placeholder test so the gap is visible in test output rather than silent.
3. Update NFR-6 to read "AC1-AC6 except the one waived under C-7".
4. Note for CLAUDE-2: resolve `--src-dir` with `Path.resolve()`, require it to be an existing directory, and decide explicitly whether paths outside the repo root are allowed.
**Status:** ACCEPTED. Rationale: user approved option (a), defer `--src-dir`. The waiver is recorded in `requirements.md` (FR-9, C-7, NFR-6 reworded to "AC1-AC6 except the AC waived under C-7 (FR-9)", Q4 resolved as deferred), CLAUDE-2 is the named owner, `architecture.md` adds a `@unittest.skip("FR-9: needs CLAUDE-2")` placeholder test and CLAUDE-2 notes (`Path.resolve()`, must be an existing directory). With the waiver recorded the severity does not escalate to HIGH.

### RISK-04: KL-4 empty-section edge case gives a misleading result
**Severity:** LOW
**Component:** `ChangeDetector.has_changed`, DD-5, KL-4
**Scenario:** Three related inputs, all from existing change detection (`old.strip() != new.strip()`):
1. No docstrings found and the README is missing: `has_changed("", "")` is False, so dry-run prints "README.md is up to date" even though README.md does not exist. This is literally false for FR-6 and conflicts with the FR-12 intent that a missing README is "would change".
2. No docstrings and the README has no `## API Reference` section: also "up to date". Correct, because a real run would also do nothing.
3. No docstrings but the README section has content (all docstrings removed): `new_content == ""`, so dry-run prints only `## API Reference\n`, an empty heading. This is accurate (a real run would write exactly that) but can look like a bug.
The architecture documents case 2 and mirrors real-run behaviour. It does not mention cases 1 and 3.
**Mitigation:** Keep the logic unchanged (NFR-3 requires shared change detection). Add three tests that pin the behaviour so it cannot drift: missing README with no docstrings, section-less README with no docstrings, and section removed because docstrings were deleted. Add cases 1 and 3 to KL-4 so the message wording is a known quirk. Optionally, if the owner prefers, change the dry-run message for case 1 only to "no docstrings found; README.md unchanged", which is a small `if not readme_path.exists()` branch in the dry-run path only.
**Status:** ACCEPTED. Rationale: preview and real run behave identically, so the preview is faithful (NFR-2, NFR-3). The wording is a cosmetic quirk on a Low-priority ticket (C-8), and changing change detection would alter real-run behaviour (FR-11).

### RISK-05: Section regex is not round-trip stable, so the preview can claim "would change" forever
**Severity:** LOW
**Component:** `ReadmeManager._SECTION_RE`, NFR-2
**Scenario:** `_SECTION_RE` ends at the next `\n## `. If a docstring contains a line starting with `## ` (a markdown heading in a docstring), the written section is cut short when re-read. `has_changed` stays True on every run, so dry-run always shows a pending change and a real run commits on every push. Also, a README whose last line is `## API Reference` with no trailing newline does not match, so a real run appends a second heading and the preview shows a section that is a duplicate once written. Both are existing CLAUDE-1 behaviours that dry-run only makes visible.
**Mitigation:** Out of scope for CLAUDE-3 (C-1, C-5). Record as a known limitation. If addressed later, anchor the regex to `^## API Reference\s*$` with `re.MULTILINE` and escape or indent leading `## ` in docstring bodies.
**Status:** ACCEPTED. Rationale: pre-existing behaviour, triggered only by unusual docstrings or hand-edited READMEs, and fixing it changes real-run output, which FR-11 forbids in this ticket.

### RISK-06: Dry-run scans only the current directory root and prints nothing on stdout when no files are found
**Severity:** LOW
**Component:** `main` (`Path(".").glob("*.py")`), DD-6, FR-14
**Scenario:** The scan is non-recursive and relative to the CWD. A user runs `python src/sync_docs.py --dry-run` from the repo root, or from a subdirectory. Only root-level `*.py` files are scanned. With none, the result is a stderr warning, empty stdout and exit 0, which a script consuming stdout cannot tell apart from "nothing to do". In a subdirectory the preview silently describes the wrong tree.
**Mitigation:** None in this ticket. Document in `--help` epilog or the README that the scan is CWD-relative and non-recursive (one line in `parse_args`, within NFR-7 since that limit applies to the `--dry-run` line only). The proper fix belongs with CLAUDE-2.
**Status:** ACCEPTED. Rationale: existing behaviour that C-5 and C-6 keep unchanged. The no-files path is explicitly specified by FR-14 (warning on stderr, exit 0).

### RISK-07: Preview-equals-write test is fragile on Windows newline translation
**Severity:** LOW
**Component:** Testing Strategy, the "Preview equals real run" row (NFR-2)
**Scenario:** `write_text` on Windows translates `\n` to `\r\n` in README.md, whereas `capsys` captures stdout without translation. A byte-for-byte comparison of captured stdout with the file fails on Windows only, and the natural "fix" of loosening the assertion hides real mismatches. `read_text` normalises newlines, so the comparison must be made on normalised text.
**Mitigation:** Specify in section 5 that the test reads README.md with `read_text(encoding="utf-8")`, extracts the section via `ReadmeManager.read_section`, and compares it with the stdout text after `.replace("\r\n", "\n")`. Run the suite on Windows (the author's platform) as well as in CI.
**Status:** FIXED (mitigation adopted in architecture section 5: normalised comparison via `read_section`)

### RISK-08: Dry-run success gives false assurance that the commit will succeed (KL-5)
**Severity:** LOW
**Component:** `main` dry-run branch, DD-2, KL-5
**Scenario:** Dry-run never runs git, so a missing git identity, a failing commit hook, or a detached or absent repository is not detected. A developer sees a clean preview and exit 0, then the real push-time run fails at `git commit` (rollback restores the file, exit 1).
**Mitigation:** Mention in the `--help` text or README that dry-run does not validate git. Do not add a git check, because FR-16 and Q6 deliberately keep dry-run subprocess-free.
**Status:** ACCEPTED. Rationale: running git, even read-only, contradicts NFR-8 and the decision that dry-run works outside a repo (Q6). The failure surfaces safely at real-run time via the existing rollback.

---

## Checklist coverage

- **Correctness:** empty input (RISK-04), missing file (FR-12, FR-13, DD-5, covered by tests), concurrent writes (not realistic for a single-user pre-push script, so not listed). Error path: dry-run performs no write, so there is nothing to roll back (FR-18); the one new failure mode is RISK-01.
- **Reliability:** no partial-update path exists in dry-run. The real-run rollback is unchanged. RISK-02 is the main reliability hazard (existing tests break).
- **Portability:** RISK-01 (Windows stdout encoding), RISK-07 (newline translation). The hook already discovers `python`, `python3` or `py` at runtime; no executable names are hard-coded in the new code.
- **Security:** no new user-controlled input beyond a boolean flag (NFR-8). The `--src-dir` path-handling concern is deferred and noted in RISK-03. No shell invocation is added (`subprocess.run` is called with lists).
- **Completeness:** FR-1 to FR-8 and FR-10 to FR-18 map to `parse_args`, `main` and `render_section`. FR-9 has no component by design (RISK-03). NFR-6 is satisfied for AC1-AC6 except the AC waived under C-7 (FR-9).

## Release gate

Open CRITICAL/HIGH risks: none. RISK-01 and RISK-02 are FIXED (mitigations adopted in `architecture.md`), RISK-03 is ACCEPTED with the waiver recorded in `requirements.md`, RISK-07 is FIXED. Gate: PASS. The design may proceed to implementation, with the existing test suite (using `main([])`) as a gate.
