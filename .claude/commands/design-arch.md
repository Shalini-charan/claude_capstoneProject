# /design-arch

Invoke the **architecture-agent** to design the system architecture from approved requirements.

## Usage

```
/design-arch
```

Reads `docs/requirements.md` automatically — no arguments needed.

## What it does

1. Reads `docs/requirements.md` to understand what must be built.
2. Identifies the minimal set of components needed to satisfy every functional requirement.
3. Defines public interfaces and key data structures.
4. Records each non-obvious design choice as an Architecture Decision Record (DD-NN).
5. Explicitly notes accepted trade-offs as Known Limitations (KL-N).
6. Writes the final document to `docs/architecture.md` after your confirmation.

## Prerequisites

`docs/requirements.md` must exist and be approved before running this command.

## Next Step

After architecture is approved, run `/review-code` (after implementation) or ask the design-review-agent to audit the architecture for risks.
