# /review-code

Invoke the **code-review-agent** to review all source files before merge.

## Usage

```
/review-code
```

Reviews every file under `src/` against the implementation plan and design documents.

## What it does

1. Reads `docs/impl-plan.md` to know which files were implemented.
2. Reads each source file and checks it against the review checklist:
   - **Correctness** — boundary inputs, error paths, rollback completeness
   - **Security** — subprocess injection, path traversal, credential handling
   - **Reliability** — return-code checks, encoding guards, partial-failure recovery
   - **Clarity** — naming, dead code, unnecessary comments
3. Reports each finding with file path, line number, severity, and a concrete fix.
4. Ends with a summary: `N findings (C critical, H high, M medium, L low)`.

## Severity Levels

| Severity | Action Required |
|----------|----------------|
| CRITICAL | Must fix before merge — data loss or security risk |
| HIGH | Must fix before merge — wrong output on documented input |
| MEDIUM | Should fix — wrong output on edge case |
| LOW | Advisory — clarity or minor inefficiency |

## Next Step

Apply all CRITICAL and HIGH fixes, then re-run `/review-code` to confirm they are resolved before creating the PR.
