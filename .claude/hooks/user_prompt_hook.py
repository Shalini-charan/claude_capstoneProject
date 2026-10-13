"""UserPromptSubmit hook: refuse prompts that ask for destructive commands.

Claude Code passes the submitted prompt as JSON on stdin. Exit code 2 blocks the
prompt and shows stderr to the user; exit code 0 lets it proceed.
"""
import json
import re
import sys

DESTRUCTIVE = [
    (r"\brm\s+(-\w*[rf]\w*\s+)+(/|~|\*|\.\.?)(\s|$)", "recursive delete of a root, home or wildcard path"),
    (r"\bRemove-Item\b.*-Recurse\b.*-Force\b|\bRemove-Item\b.*-Force\b.*-Recurse\b", "Remove-Item -Recurse -Force"),
    (r"\b(del|rmdir|rd)\s+/s\b", "recursive delete on Windows"),
    (r"\bformat\s+[a-z]:", "disk format"),
    (r"\bgit\s+reset\s+--hard\b", "git reset --hard"),
    (r"\bgit\s+clean\s+-\w*f", "git clean -f"),
    (r"\bgit\s+push\b.*(--force\b|--force-with-lease\b|\s-f\b)", "git force-push"),
    (r"\bgit\s+branch\s+-D\b", "git branch -D"),
    (r"\bgit\s+checkout\s+(--\s+)?\.(\s|$)|\bgit\s+restore\s+\.(\s|$)", "discarding all working-tree changes"),
    (r"\bdrop\s+(table|database|schema)\b", "SQL DROP"),
    (r"\btruncate\s+table\b", "SQL TRUNCATE"),
    (r"\bdelete\s+from\s+\w+\s*(;|$)", "SQL DELETE without WHERE"),
    (r"\bgh\s+repo\s+delete\b", "deleting a GitHub repository"),
    (r"--no-verify\b", "skipping git hooks"),
]


def find_destructive(prompt: str) -> str | None:
    for pattern, label in DESTRUCTIVE:
        if re.search(pattern, prompt, re.IGNORECASE):
            return label
    return None


def main() -> int:
    payload = json.load(sys.stdin)
    label = find_destructive(payload.get("prompt", ""))
    if label:
        print(
            f"Blocked by user prompt hook: your prompt asks for a destructive command ({label}). "
            "Run it yourself with the ! prefix if you really mean it, or reword the request.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
