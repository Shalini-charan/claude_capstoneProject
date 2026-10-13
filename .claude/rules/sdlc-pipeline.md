# SDLC pipeline

- Each stage is done by its specialist agent: requirements, architecture, design review, implementation plan, implementation, code review, verify and PR. The orchestrator coordinates and does not write the source code or tests itself.
- Store a ticket's documents in `docs/<ticket-id-lowercase-no-dash>/` (e.g. `docs/claude3/`).
- Pause for developer approval after Stage 1 (requirements), Stage 3 (design review) and Stage 4 (implementation plan). Open HIGH or CRITICAL risks block Stage 4.
- The implementation agent edits only the files the plan lists and never commits. The verify agent writes tests and never edits source to make a test pass; source bugs go back to the implementation agent.
- Extend existing test files. Never recreate or weaken existing tests.
- Report test results exactly as observed (run, passed, failed, skipped). Never report a pass that was not run.
- Record a deferred acceptance criterion as a waiver in the docs, with an owner ticket and a skipped placeholder test.
- Do not stage `.mcp.json` or other files unrelated to the ticket.
