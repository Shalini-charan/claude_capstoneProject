#!/bin/sh
# Source this script BEFORE starting Claude Code:
#   source scripts/setup-mcp-env.sh
#
# These environment variables are read by the MCP servers configured in
# .claude/settings.json.  Replace the placeholder values with your real tokens.

# ── Atlassian API token ───────────────────────────────────────────────────────
# Create at: https://id.atlassian.com/manage-profile/security/api-tokens
export ATLASSIAN_API_TOKEN="<your-atlassian-api-token>"

# ── GitHub Personal Access Token ─────────────────────────────────────────────
# Create at: GitHub → Settings → Developer settings → Personal access tokens
# Required scopes: repo, read:org, read:user
export GITHUB_TOKEN="<your-github-personal-access-token>"

echo "MCP environment variables set for this session."
