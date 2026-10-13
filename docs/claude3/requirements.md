# Requirements: CLAUDE-3 Add --dry-run flag to sync_docs.py

Source: Jira CLAUDE-3 (Task, Low, labels: cli, sync-docs). Related: CLAUDE-1 (README sync), CLAUDE-2 (--src-dir).

User story: As a developer, I want to run `sync_docs.py --dry-run` to see what would change in README.md, so I can preview the docstring sync before it edits files or creates a commit.

## Functional Requirements
| ID | Requirement |
|----|-------------|
| FR-1 | The script shall accept a `--dry-run` command-line flag. |
| FR-2 | When `--dry-run` is given and the README `## API Reference` section would change, the script shall print the complete new section content to stdout. |
| FR-3 | When `--dry-run` is given and the section would change, the script shall leave README.md byte-for-byte unchanged (no write, no rewrite, no timestamp-affecting save). |
| FR-4 | When `--dry-run` is given, the script shall not run `git add`. |
| FR-5 | When `--dry-run` is given, the script shall not run `git commit`. |
| FR-6 | When `--dry-run` is given and README.md is already up to date, the script shall print "README.md is up to date" to stdout. |
| FR-7 | When `--dry-run` is given and README.md is already up to date, the script shall exit with code 0. |
| FR-8 | When `--dry-run` is given and the section would change, the script shall exit with code 0. |
| FR-9 | **WAIVED (C-7), deferred to CLAUDE-2.** When `--dry-run` is combined with `--src-dir <dir>`, the script shall scan `<dir>` for source files instead of the default location. Not delivered or tested by CLAUDE-3. |
| FR-10 | When `--help` is given, the script shall list `--dry-run` with a one-line description. |
| FR-11 | When `--dry-run` is not given, the script shall behave identically to current behaviour (extract docstrings, rewrite README section, `git add`, `git commit`). |
| FR-12 | When `--dry-run` is given and README.md does not exist, the script shall print the new section to stdout and shall not create README.md. |
| FR-13 | When `--dry-run` is given and README.md has no `## API Reference` section, the script shall print the new section to stdout and leave README.md unchanged. |
| FR-14 | When `--dry-run` is given and no source files are found, the script shall print the existing no-files warning to stderr, change no files, run no git commands, and exit 0. |
| FR-15 | When `--dry-run` is given, the script shall still emit existing parse-error and non-UTF-8 warnings to stderr for scanned files. |
| FR-16 | When `--dry-run` is given, the script shall not invoke any git subprocess that modifies the repository or index. |
| FR-17 | When `--dry-run` is given, the script shall write the preview only to stdout and diagnostics only to stderr. |
| FR-18 | If an unexpected error occurs during a dry run, the script shall print the error to stderr and exit with code 1, with README.md unchanged. |

## Non-Functional Requirements
| ID | Requirement |
|----|-------------|
| NFR-1 | Reliability: after any `--dry-run` invocation, `git status --porcelain` and the README.md content hash shall be identical to their pre-run values (verified by automated test). |
| NFR-2 | Reliability: the dry-run preview shall be exactly the section text that a real run would write, so a real run immediately after produces the same content (verified by comparing output to written section). |
| NFR-3 | Maintainability: dry-run and real-run shall share the same extraction, formatting and change-detection code paths; only the write and commit steps shall be gated by the flag. |
| NFR-4 | Performance: a dry run shall complete in no more than the duration of a real run minus the write and git steps, on the same inputs (no additional scans). |
| NFR-5 | Portability: the flag shall work on Windows, macOS and Linux with the same Python versions the script already supports (3.8+ per existing compatibility code). |
| NFR-6 | Maintainability: unit tests shall cover each acceptance criterion (AC1-AC6 except the AC waived under C-7 (FR-9)), including a mock asserting `subprocess.run` is not called in dry-run mode. |
| NFR-7 | Usability: the `--help` text for `--dry-run` shall be a single line of 100 characters or fewer. |
| NFR-8 | Security: dry-run shall introduce no new external inputs beyond the CLI flag and shall not execute any new subprocess. |

## Constraints
| ID | Constraint | Type |
|----|------------|------|
| C-1 | The change is limited to `src/sync_docs.py` (plus tests and docs); no other scripts are modified. | FIXED |
| C-2 | Diff-style output is out of scope; the preview is the full new section. | FIXED |
| C-3 | Changes to the pre-push hook are out of scope. | FIXED |
| C-4 | Implementation language is Python using the standard library only (argparse for flag parsing). | ASSUMED |
| C-5 | Ticket labels `cli` and `sync-docs` confine the work to the command-line interface of the sync-docs script. | FIXED |
| C-6 | Existing exit-code semantics (0 success/no change, 1 error) are preserved. | ASSUMED |
| C-7 | `--src-dir` (CLAUDE-2) is not present in `src/sync_docs.py`. **Explicit waiver (user-approved):** FR-9 and the acceptance criterion "dry-run combined with `--src-dir`" are waived for CLAUDE-3 and deferred to CLAUDE-2, which is the owner of that requirement and its test. | FIXED (waiver) |
| C-8 | Priority is Low; no delivery deadline stated. | FIXED |

## Current Code Observations
- `src/sync_docs.py` has no argparse and does not read `sys.argv`; `main()` takes no arguments.
- `main()` globs `*.py` in the current working directory (`Path(".")`), not in `src/`. It extracts docstrings, rewrites README `## API Reference`, then runs `git add` and `git commit` via `GitCommitter`.
- The `--src-dir` option from CLAUDE-2 does not exist in the code (checked). Only `docs/claude1` exists under `docs/`; no CLAUDE-2 artefacts were found.
- The existing "no changes" message is "sync_docs: no docstring changes detected" on stderr with exit 0. The AC requires "README.md is up to date" (stdout is assumed) in dry-run mode.

## Assumptions
- A1: "Prints" in the ACs means stdout; the up-to-date message is printed to stdout in dry-run mode.
- A2: In real (non-dry-run) mode, the existing stderr message is left unchanged (FR-11).
- A3: The preview prints only the new section body (as would be written under `## API Reference`), including the heading line.
- A4: Dry-run exit code is 0 on success regardless of whether changes are pending.
- A5: Acceptance criteria are numbered AC1-AC6 in ticket order for NFR-6.

## Open Questions
- Q1: Should dry-run include the `## API Reference` heading in the printed output, or only the body? (A3 assumes heading included.)
- Q2: Should the up-to-date message in dry-run go to stdout while the non-dry-run message stays on stderr, or should both be unified?
- Q3: Should dry-run print anything extra (e.g. a header such as "Would update README.md") to separate preview from content? The ticket does not say; none is assumed.
- Q4: RESOLVED (user-approved): deferred. FR-9 is waived for CLAUDE-3 under C-7 and owned by CLAUDE-2.
- Q5: Should a missing README.md in dry-run be treated as "would change" (assumed in FR-12)?
- Q6: Should `--dry-run` run when git is unavailable or the directory is not a repo? Assumed yes, since no git calls are made (FR-16).
