# Threat Model

This document outlines the threat model for the **PR Orchestrator MCP** and the mitigations implemented in the server to reduce risk.  While the MCP server runs untrusted code, it enforces strict controls to prevent privilege escalation, secret leakage and accidental damage to repositories.

## Assets

* **Secrets:** GitHub personal access token (PAT) and E2B API key stored in `.env`.
* **Code:** Source code of the target repository and of this project itself.
* **Data:** Test logs, lint/typecheck outputs and artifact archives.
* **GitHub Repositories:** The upstream repository and the user’s fork.

## Threats

1. **Secret Leakage:** An attacker may attempt to exfiltrate the PAT or API key by reading environment variables or writing them into logs, diffs or commit messages.
2. **Destructive Commands:** A malicious diff could include commands that delete files, compromise the system or spawn remote shells.
3. **Privilege Escalation:** Running untrusted project code during tests could exploit vulnerabilities in the test harness or underlying tools.
4. **Branch Hijacking:** Creating branches with names that collide with existing PRs or forcing pushes to the upstream repository without approval.
5. **Out‑of‑Scope Repositories:** Accessing repositories not listed in `ALLOWED_REPOS`.

## Mitigations

* **Environment Isolation:** Workspaces are provisioned in isolated containers via the E2B API.  Each workspace has a time‑to‑live and is destroyed after use.
* **Redaction:** The `policy/redaction.py` module automatically redacts any occurrence of tokens or keys from logs, diffs, commit messages and artifact archives.
* **Allowlist and Limits:** The server enforces a strict allowlist of commands (e.g. `git`, `pytest`, `ruff`, `mypy`) and limits the number of changed files and diff lines.  Dangerous commands such as `rm -rf /` are never passed through.
* **Branch Strategy:** The branch strategy module avoids collisions by reusing existing branches for the same issue and suffixing names when necessary.  Only branches under the user’s fork are pushed.
* **Approval Gate:** Before any external side‑effects (push or PR open) occur, a human must approve the changes.  This prevents unintended or malicious modifications from being merged.
* **Allowed Repositories:** A list of repositories the server may operate on is provided via `ALLOWED_REPOS`.  Requests for other repositories are rejected.

## Assumptions

* The orchestrating client (LLM) is trusted to follow the workflow contract and use the tools responsibly.
* The PAT has the minimum required scopes (`repo` and `workflow` as necessary) and is not overly permissive.
* The E2B sandbox infrastructure is secure and isolates executions between workspaces.

Mitigations and assumptions should be revisited regularly as the threat landscape evolves.