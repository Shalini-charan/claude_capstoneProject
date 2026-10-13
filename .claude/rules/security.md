# Security

- Never hardcode tokens, API keys or passwords in any file, including scripts, docs and commented-out config. Read them from environment variables (e.g. `${ATLASSIAN_API_TOKEN}`, `${GITHUB_TOKEN}`).
- Scripts that set credentials contain placeholders only (`<your-github-pat>`), never real values.
- Do not print, log or echo secret values. When showing config that may contain secrets, redact them first.
- Before committing, check the diff for strings that look like tokens (`ghp_`, `ATATT`, `AKIA`, `-----BEGIN`). GitHub secret scanning rejects pushes that contain them.
- If a secret was ever written to disk or committed, treat it as exposed and rotate it.
- Do not read credential or settings files just to look for secrets unless the developer asked for that.
