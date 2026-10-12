## Summary
- Adds a `--dry-run` flag to `src/sync_docs.py` (CLAUDE-3) so a developer can preview the README `## API Reference` update without editing files or creating a commit.
- In dry-run, a changed section is printed in full to stdout; an unchanged README prints `README.md is up to date`. README.md is not written and no git command runs. Exit code is 0 in both cases.
- Dry-run and real run share the same extraction, formatting and change-detection code. Only the write and commit steps are gated by the flag, so the preview is exactly what a real run would write.
- Behaviour without `--dry-run` is unchanged, including the pre-push hook, which calls the script with no arguments.
- Scope waiver: the "dry-run combined with `--src-dir`" acceptance criterion (FR-9) is deferred to CLAUDE-2 under waiver C-7. `--src-dir` does not exist in the code, and the waiver was approved by the user.

Base: `feature/capstone-auto-doc-sync`. Head: `feature/claude-3-dry-run`.

## Changes Made
| File | Change |
|------|--------|
| src/sync_docs.py | Add `parse_args(argv=None)` with the `--dry-run` flag and a one-line help. `main` becomes `main(argv=None)`. |
| src/sync_docs.py | Add `ReadmeManager.render_section(content)`. `write_section` now uses it, so the preview equals the written text. |
| src/sync_docs.py | Add the dry-run branch in `main` after change detection. It prints the preview to stdout, or `README.md is up to date`, and exits 0 without writing or constructing `GitCommitter`. |
| src/sync_docs.py | Force UTF-8 on stdout in dry-run only, so a non-UTF-8 Windows console code page cannot raise `UnicodeEncodeError` (RISK-01). |
| tests/test_sync_docs.py | Add the `TestDryRun` class. It covers each requirement except FR-9, including a `subprocess.run` mock asserting no git calls. |
| tests/test_sync_docs.py | Existing `main()` calls changed to `main([])` so argparse does not read runner arguments from `sys.argv` (RISK-02). |
| docs/claude3/ | Requirements, architecture, design review, implementation plan and this PR description. |

## How to Test
1. Run the full suite: `python -m unittest tests.test_sync_docs -v` (or `pytest tests/test_sync_docs.py`).
2. Preview with changes pending: in a directory containing a documented `.py` file, run `python src/sync_docs.py --dry-run`. The new section is printed to stdout. Then check that `README.md` and `git status` are unchanged.
3. Preview with nothing pending: run the same command again after a real run. It prints `README.md is up to date`.
4. Check redirection: `python src/sync_docs.py --dry-run > preview.md` produces UTF-8 bytes.
5. Check help: `python src/sync_docs.py --help` lists `--dry-run`.
6. Check there is no regression: `python src/sync_docs.py` with no arguments (the pre-push hook path) behaves as before.

## Test Evidence
```
Ran 64 tests
OK (skipped=1)
```
64 tests pass and 1 is skipped. The skipped test is the FR-9 placeholder (`@unittest.skip("FR-9: needs CLAUDE-2")`), which makes the waived gap visible in test output. The timing line is omitted because this description was written without re-running the suite.

Code review: 0 critical, 0 high, 0 medium, 2 low. Both low findings were fixed.

## Known Limitations
- **KL-1:** FR-9 (`--dry-run` with `--src-dir`) is waived under C-7 and not delivered here. `--src-dir` belongs to CLAUDE-2, which owns the requirement and its test. Until then only the skipped placeholder covers it, and passing `--src-dir` exits 2 from argparse. Accepted because implementing it here would exceed the ticket scope (C-1, C-5) and could conflict with CLAUDE-2 (RISK-03).
- **KL-2:** "No changes" is reported on stdout in dry-run and on stderr in a real run. Accepted because the message is the primary result of a dry-run, while real-run output must stay unchanged (FR-11).
- **KL-3:** Unknown arguments make argparse exit 2, which extends the 0/1 exit codes for malformed invocations only. Accepted as the argparse default, affecting previously meaningless input.
- **KL-4:** With no docstrings and a missing README or section, dry-run reports "up to date" instead of previewing an empty section. Accepted because it mirrors existing change detection, and changing it would alter real-run behaviour (RISK-04).
- **KL-5:** Dry-run does not check that git works or that a commit would succeed (identity, hooks). Accepted because running any git command contradicts FR-16 and NFR-8. A real-run failure is rolled back by the existing logic (RISK-08).
- **KL-6:** Dry-run forces UTF-8 on stdout (mitigated, RISK-01). The terminal may still display such characters wrongly, and PowerShell 5.1 `>` may re-encode the output. The bytes the script emits are UTF-8. Real-run stdout is unchanged.
- **KL-7:** The preview is the full section, not a diff, because diff output is out of scope (C-2).
- Pre-existing behaviours made visible by dry-run, accepted as out of scope: the section regex stops at the next `\n## ` line (RISK-05), and the scan is non-recursive and relative to the current directory (RISK-06).

## Reviewer Checklist
- [ ] FR-1: the script accepts `--dry-run`.
- [ ] FR-2: on a pending change, the full new section is printed to stdout.
- [ ] FR-3: README.md is left byte-for-byte unchanged on a dry-run.
- [ ] FR-4: no `git add` runs in dry-run.
- [ ] FR-5: no `git commit` runs in dry-run.
- [ ] FR-6: an up-to-date README prints `README.md is up to date` to stdout.
- [ ] FR-7: exit code is 0 when up to date.
- [ ] FR-8: exit code is 0 when the section would change.
- [ ] FR-9: WAIVED (C-7, user-approved), deferred to CLAUDE-2. Confirm the waiver is acceptable.
- [ ] FR-10: `--help` lists `--dry-run` with a one-line description.
- [ ] FR-11: behaviour without the flag is unchanged.
- [ ] FR-12: a missing README.md is not created, and the section is printed.
- [ ] FR-13: a README without the section is unchanged, and the section is printed.
- [ ] FR-14: with no source files, the warning goes to stderr, nothing changes, and the exit code is 0.
- [ ] FR-15: parse-error and non-UTF-8 warnings still go to stderr.
- [ ] FR-16: no repository-modifying git subprocess runs.
- [ ] FR-17: the preview goes to stdout and diagnostics to stderr.
- [ ] FR-18: an unexpected error prints to stderr, exits 1, and leaves README.md unchanged.
- [ ] All HIGH risks from design-review.md are resolved: RISK-01 and RISK-02 FIXED, RISK-03 ACCEPTED with the waiver recorded. No CRITICAL risks exist.
- [ ] Tests pass locally (63 passed, 1 skipped).
- [ ] README.md update: intentionally skipped. README.md has no Usage section, and `--help` is the user-facing documentation (T-16).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
