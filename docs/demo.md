# Demo Walkthrough

This document provides a high‑level walkthrough of how a client might interact with the **PR Orchestrator MCP** to fix a bug in a Python repository.  The client here is assumed to be an orchestrating language model that follows the workflow contract defined in the specification.

## Scenario

Suppose there is an open issue `#123` on the repository `saakshigupta2002/repo1` titled "Fix division by zero in calculator".  The model must reproduce the failure, apply a fix and open a pull request.

### 1. Create a Workspace

```json
{"tool": "workspace_create", "args": {"mode": "code", "ttl_minutes": 60}}
```

The server provisions a new E2B container and returns a `workspace_id`.  All subsequent operations reference this workspace.

### 2. Ensure Fork and Clone Repository

```json
{"tool": "ensure_fork", "args": {"repo_slug": "saakshigupta2002/repo1"}}
```

If the fork doesn’t exist, the server creates one.  It returns the `fork_slug` and `fork_url`.  Then clone the repository:

```json
{"tool": "repo_clone", "args": {"workspace_id": "...", "repo_url": "https://github.com/saakshigupta2002/repo1.git"}}
```

The client now has the code checked out and can run tests.

### 3. Baseline Tests

To capture the current failures on the base branch, check out `main` and run tests:

```json
{"tool": "repo_checkout", "args": {"workspace_id": "...", "ref": "main"}}
```

```json
{"tool": "run_tests", "args": {"workspace_id": "..."}}
```

The server returns a list of failing tests (if any).  Save this as `before_failures.json`.

### 4. Branch and Fix Loop

Use the branch strategy to create a new branch `issue/123-calculator` from `main`:

```json
{"tool": "repo_create_branch", "args": {"workspace_id": "...", "branch_name": "issue/123-calculator", "from_ref": "main"}}
```

Checkout the branch and reproduce the failure to confirm it matches the baseline:

```json
{"tool": "repo_checkout", "args": {"workspace_id": "...", "ref": "issue/123-calculator"}}
```
```json
{"tool": "run_tests", "args": {"workspace_id": "...", "command": "pytest tests/test_calculator.py -q"}}
```

Next, search for the bug:

```json
{"tool": "search_repo", "args": {"workspace_id": "...", "query": "division by zero"}}
```

Modify the file to handle the zero divisor and apply the patch:

```json
{"tool": "apply_patch", "args": {"workspace_id": "...", "unified_diff": "@@ -10,6 +10,8 @@ def divide(a, b):\n     if b == 0:\n-        return a / b\n+        # Avoid division by zero\n+        return 0\n     return a / b\n"}}
```

Run the targeted test again to verify the fix:

```json
{"tool": "run_tests", "args": {"workspace_id": "...", "command": "pytest tests/test_calculator.py -q"}}
```

If the test passes and no new failures are introduced, proceed to verification.

### 5. Verification

Run the linter, type checker and formatter:

```json
{"tool": "run_lint", "args": {"workspace_id": "..."}}
```
```json
{"tool": "run_typecheck", "args": {"workspace_id": "..."}}
```
```json
{"tool": "run_format", "args": {"workspace_id": "..."}}
```

Collect the unified diff:

```json
{"tool": "repo_diff", "args": {"workspace_id": "..."}}
```

Commit the changes:

```json
{"tool": "repo_commit", "args": {"workspace_id": "...", "message": "Handle division by zero in calculator"}}
```

### 6. Approval Gate

Construct a summary and call the approval tool:

```json
{
  "tool": "request_approval",
  "args": {
    "summary": "Fix division by zero in calculator module",
    "unified_diff": "...",
    "checks": {"tests": {"passed": true}, "lint": {"passed": true}, "typecheck": {"passed": true}},
    "pr_draft": true,
    "branch_plan": {"name": "issue/123-calculator", "created": true}
  }
}
```

If the reviewer approves, push the branch and open the PR:

```json
{"tool": "repo_push", "args": {"workspace_id": "...", "remote": "origin", "branch_name": "issue/123-calculator"}}
```

```json
{
  "tool": "github_open_pr",
  "args": {
    "upstream_repo_slug": "saakshigupta2002/repo1",
    "base_branch": "main",
    "fork_repo_slug": "your-username/repo1",
    "head_branch": "issue/123-calculator",
    "title": "Fix division by zero in calculator",
    "body": "Summary\n\nThis PR fixes a division by zero bug...",
    "draft": true
  }
}
```

The server returns the URL and number of the newly created draft pull request.  At this point the run is complete and the reviewer can take over.