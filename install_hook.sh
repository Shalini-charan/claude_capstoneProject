#!/bin/sh
# One-time setup: installs the pre-push hook into .git/hooks/
# Run from the repository root: sh install_hook.sh

TEMPLATE="hooks/pre-push.template"
DEST=".git/hooks/pre-push"

if [ ! -d ".git" ]; then
    echo "install_hook.sh: error: .git directory not found." >&2
    echo "Run this script from the root of a Git repository." >&2
    exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
    echo "install_hook.sh: error: hook template not found at $TEMPLATE" >&2
    exit 1
fi

cp "$TEMPLATE" "$DEST"
chmod +x "$DEST"
echo "Hook installed at $DEST"
echo "Every 'git push' will now auto-sync README.md from Python docstrings."
