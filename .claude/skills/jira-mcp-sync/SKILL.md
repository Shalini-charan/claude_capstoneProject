---
name: jira-mcp-sync
description: Jira MCP calls for the SDLC pipeline — pulling a ticket into requirements, posting stage-completion comments, and transitioning the ticket. Use whenever a stage needs to read from or report to Jira.
---

# Jira MCP Sync

Applies only when the `atlassian` MCP server (configured in `.mcp.json`) is connected. If it is not, skip these calls and fall back to local-only behaviour (ask the user for the description, print status to the terminal).

## Pull a ticket (Stage 1)

```
mcp__atlassian__jira_get_issue(issue_key="<TICKET_ID>")
```

Extract `summary`, `description`, `customfield_10016` (acceptance criteria), `labels`, `priority`, and map them:

- Description paragraphs → Functional Requirements
- Acceptance criteria bullets → FR rows with testable conditions
- Labels / components → Constraints

Ask the user only for gaps the ticket does not cover.

## Post a stage-completion comment

```
mcp__atlassian__jira_add_comment(
  issue_key="<TICKET_ID>",
  comment="Stage <N> complete — <one-line result>."
)
```

Examples:
- Stage 1: `requirements captured in docs/requirements.md.`
- Stage 6: `code review findings: <N CRITICAL, N HIGH, N MEDIUM, N LOW>. All CRITICAL/HIGH resolved.`
- Stage 8: `PR created: <PR_URL>.`

## Transition after PR creation (Stage 8)

```
mcp__atlassian__jira_transition_issue(issue_key="<TICKET_ID>", transition="In Review")
```
