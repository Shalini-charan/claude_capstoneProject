---
name: code-review-checklist
description: Review checklist, severity definitions, and finding format for pre-merge code reviews. Use when reviewing source files for correctness, security, reliability, and clarity.
---

# Code Review Checklist

## Finding Format

```
### FIND-NN: <Title>
**File:** src/foo.py:42
**Severity:** CRITICAL | HIGH | MEDIUM | LOW
**Category:** correctness | security | reliability | performance | clarity
**Issue:** One sentence describing the defect.
**Scenario:** Concrete input or state that triggers the wrong behaviour.
**Fix:** Exact code change or pattern to apply.
```

## Checklist

**Correctness**
- Does every code path produce the expected output for boundary inputs?
- Are off-by-one errors possible in loops or index arithmetic?
- Do error paths restore all state that was modified before the failure?

**Security**
- Is user-controlled input ever passed to `subprocess`, `eval`, or `exec` without sanitisation?
- Can file paths escape the intended directory?
- Are credentials or secrets handled correctly (not logged, not hard-coded)?

**Reliability**
- Are all `subprocess.run` calls checked for non-zero return codes?
- Are file operations wrapped for encoding errors?
- Is rollback complete — both in-memory state and filesystem state?

**Clarity**
- Are identifiers named after what they represent, not how they are implemented?
- Would removing a comment lose information not already in the code?
- Is there dead code, commented-out blocks, or TODO items that should be resolved?

## Severity Definitions

| Severity | Meaning | Action |
|----------|---------|--------|
| CRITICAL | Data loss, silent corruption, or security breach in normal use | Blocks merge |
| HIGH | Wrong output or crash on a documented input | Blocks merge |
| MEDIUM | Wrong output on an edge case; partial data loss | Advisory |
| LOW | Clarity, naming, or minor inefficiency | Advisory |

## Rules

- Only report findings you can reproduce with a concrete scenario — no speculative risks.
- Do not request stylistic changes that are not covered by the checklist.
- End with a summary line: `N findings (C critical, H high, M medium, L low)`.
