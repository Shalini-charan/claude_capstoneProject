# Run this script in your PowerShell session BEFORE starting Claude Code:
#   . scripts/setup-mcp-env.ps1
#
# These environment variables are read by the MCP servers configured in
# .claude/settings.json.  Replace the placeholder values with your real tokens.

# ── Atlassian API token ───────────────────────────────────────────────────────
# Create at: https://id.atlassian.com/manage-profile/security/api-tokens
$env:ATLASSIAN_API_TOKEN = "<your-atlassian-api-token>"

# ── GitHub Personal Access Token ─────────────────────────────────────────────
# Create at: GitHub → Settings → Developer settings → Personal access tokens
# Required scopes: repo, read:org, read:user
$env:GITHUB_TOKEN = "<your-github-personal-access-token>"

Write-Host "MCP environment variables set for this session." -ForegroundColor Green
Write-Host "  ATLASSIAN_API_TOKEN : $($env:ATLASSIAN_API_TOKEN.Substring(0,8))..." -ForegroundColor Cyan
Write-Host "  GITHUB_TOKEN        : $($env:GITHUB_TOKEN.Substring(0,8))..." -ForegroundColor Cyan
