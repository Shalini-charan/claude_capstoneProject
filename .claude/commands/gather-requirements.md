# /gather-requirements

Invoke the **requirements-agent** to capture and structure requirements for a new feature.

## Usage

```
/gather-requirements <feature description>
```

## What it does

1. Reads any existing `docs/requirements.md` to avoid duplicating requirements.
2. Asks one clarifying question at a time if the description is ambiguous.
3. Produces a structured table of Functional Requirements (FR-N), Non-Functional Requirements (NFR-N), and Constraints (C-N).
4. Writes the final document to `docs/requirements.md` after your confirmation.

## Example

```
/gather-requirements Automatically sync README.md API Reference section
from Python docstrings whenever code is pushed
```

## Next Step

After requirements are approved, run `/design-arch` to produce the architecture document.
