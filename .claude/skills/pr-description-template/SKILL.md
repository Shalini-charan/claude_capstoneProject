---
name: pr-description-template
description: Structure and rules for writing a pull request description from SDLC documents and git log. Use when drafting or creating a PR.
---

# PR Description Template

## Inputs to read

- `docs/requirements.md` — acceptance criteria
- `docs/architecture.md` — component design and known limitations
- `docs/design-review.md` — risks and their resolutions
- `docs/impl-plan.md` — task list
- `git log --oneline` — commit history

## Format

```markdown
## Summary
<!-- 2-4 bullet points: what this PR does and why -->

## Changes Made
| File | Change |
|------|--------|
| src/... | ... |

## How to Test
1. Install hook: `sh install_hook.sh`
2. ...

## Test Evidence
```
Ran N tests in X.XXXs
OK
```

## Known Limitations
<!-- Reference KL-N items from architecture.md with their accepted rationale -->

## Reviewer Checklist
- [ ] Requirements FR-1 through FR-N are satisfied
- [ ] All CRITICAL and HIGH risks from design-review.md are resolved
- [ ] Tests pass locally
- [ ] README.md updated
```

## Rules

- The Summary must answer: what does this PR do, and why does it exist?
- Every Known Limitation must reference its KL-N id and explain why it was accepted.
- The Reviewer Checklist must include one item per functional requirement.
- Do not include implementation details that belong in commit messages.
- Write the description to `pr-description.md` in the ticket's docs directory (default `docs/`) and print it to the terminal.
- End the PR body with: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
