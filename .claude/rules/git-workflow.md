# Git workflow

- Base each feature branch and its PR on the branch you started from, not blindly on `main`, because `main` may not contain the code the ticket builds on.
- Name feature branches `feature/<ticket-id>-<slug>` (e.g. `feature/claude-3-dry-run`).
- Stage files by name. Never use `git add -A` or `git add .`.
- Keep other tickets' uncommitted changes out of a PR. If the working tree has unrelated changes, ask before branching.
- Commit messages follow `<type>: <summary> (<TICKET_ID>)` where `<type>` is `feat`, `fix`, `chore`, `docs` or `test`.
- Do not amend or force-push commits that are already on the remote. Amending a local, unpushed commit is fine.
- If a PR targets a feature branch rather than `main`, remember it still needs its own PR to `main` once the parent branch merges.
- A PR is not done until its URL has been printed and `gh pr view` confirms it is open.
