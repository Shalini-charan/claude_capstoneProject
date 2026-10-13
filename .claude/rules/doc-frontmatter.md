# Document front matter

Every document generated for the SDLC (requirements, architecture, design review, implementation plan, PR description, and any other generated doc) must start with this YAML front matter:

```yaml
---
title: <document title>
ticket: <ticket ID, e.g. CLAUDE-3>
created: <ISO 8601 date and time, e.g. 2026-10-13T11:42:00+05:30>
created_by: <name of the agent that generated it, e.g. requirements-agent>
hitl_status: <pending-review | approved | revision-requested | not-required>
approved_by: <name of the human who approved, or null>
approved_on: <ISO 8601 date and time of approval, or null>
revision: <number, starting at 1>
---
```

## Rules

- `created_by` is the agent that wrote the document, not the orchestrator that invoked it. If a human wrote or edited it, say so (e.g. `created_by: human (Shalini Srinivasan)`).
- `hitl_status` is the human-in-the-loop state:
  - `pending-review`: written and waiting at an approval gate.
  - `approved`: a human approved it. Set `approved_by` and `approved_on`.
  - `revision-requested`: a human asked for changes. Increase `revision` when the revised version is written, and set the status back to `pending-review`.
  - `not-required`: the document has no approval gate (e.g. an architecture draft before its review).
- New documents start as `pending-review`, or `not-required` if they have no gate.
- Update `hitl_status`, `approved_by` and `approved_on` only after the human has actually approved. Never mark a document `approved` on the strength of an agent's report or an automated notification.
- When a document is revised, keep `created` as the original date and add `updated: <ISO 8601 date and time>`.
- Use the real current date and time, not a placeholder.
