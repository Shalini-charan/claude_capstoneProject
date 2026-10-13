"""PreToolUse hook: block risky tool calls before they run.

Claude Code passes the pending tool call as JSON on stdin. Exit code 2 blocks the
call and sends stderr back to Claude; exit code 0 lets it proceed.
"""
import json
import re
import sys
from pathlib import Path

FORCE_PUSH = re.compile(r"\bgit\s+push\b.*(--force\b|--force-with-lease\b|\s-f\b)")


def block_reason(tool_name: str, tool_input: dict) -> str | None:
    if tool_name in ("Write", "Edit"):
        name = Path(tool_input.get("file_path", "")).name
        if name == ".env" or name.startswith(".env."):
            return f"{name} holds secrets; edit it manually instead."
    if tool_name == "Bash" and FORCE_PUSH.search(tool_input.get("command", "")):
        return "Force-push is blocked; use a regular push or ask the user."
    return None


def main() -> int:
    payload = json.load(sys.stdin)
    reason = block_reason(payload.get("tool_name", ""), payload.get("tool_input", {}))
    if reason:
        print(f"Blocked by guard hook: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
