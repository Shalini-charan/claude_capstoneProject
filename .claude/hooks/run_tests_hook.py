"""PostToolUse hook: run the unit tests after Claude edits a Python file in src/ or tests/.

Claude Code passes the tool call as JSON on stdin. Exit code 2 sends stderr back to
Claude so it can fix the failure; exit code 0 stays silent.
"""
import json
import subprocess
import sys
from pathlib import Path


def edited_path(payload: dict) -> Path | None:
    raw = payload.get("tool_input", {}).get("file_path")
    return Path(raw) if raw else None


def main() -> int:
    path = edited_path(json.load(sys.stdin))
    if path is None or path.suffix != ".py" or not {"src", "tests"} & set(path.parts):
        return 0

    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Tests failed after editing {path.name}:\n{result.stderr}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
