# Tool Specification

This document enumerates all tools exposed by the **PR Orchestrator MCP** server. The server implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) and communicates over stdio.

## Protocol Overview

The server uses the standard MCP protocol for tool registration and invocation. When started, it registers all available tools with their schemas. Clients can then:

1. Discover available tools via MCP's tool listing
2. Invoke tools with JSON arguments
3. Receive structured JSON responses

### Example Tool Invocation (MCP Protocol)

Tools are invoked through the MCP protocol. The client sends a tool call request, and the server responds with the result. All responses are JSON objects containing tool-specific return values.

## Workspace Tools

### workspace_create

Create a new sandboxed workspace backed by E2B.

*Arguments*

| Name         | Type     | Default | Description                                   |
|--------------|----------|---------|-----------------------------------------------|
| `mode`       | string   | `code`  | Workspace mode: `code` or `desktop`.          |
| `ttl_minutes`| integer  | `60`    | Time-to-live in minutes for the workspace.     |

*Returns*

| Name          | Type   | Description                                          |
|---------------|--------|------------------------------------------------------|
| `workspace_id`| string | Unique identifier for the workspace.                |
| `mode`        | string | The mode used to create the workspace.              |
| `created_at`  | float  | Unix timestamp when the workspace was created.      |

### workspace_destroy

Destroy an existing workspace.

*Arguments*

| Name           | Type   | Description                           |
|----------------|--------|---------------------------------------|
| `workspace_id` | string | Identifier of the workspace to destroy|

*Returns*

| Name       | Type | Description              |
|------------|------|--------------------------|
| `destroyed`| bool | Whether the workspace was destroyed |

### run_command

Execute a command in a workspace with an optional working directory and timeout.

**Note:** This tool enforces a strict command allowlist. Commands like `git clone`, `git push`, and `git apply` are blocked and must be performed through their respective tools (`repo_clone`, `repo_push`, `apply_patch`).

*Arguments*

| Name        | Type    | Default | Description                                                   |
|-------------|---------|---------|---------------------------------------------------------------|
| `workspace_id`| string |         | Identifier of the workspace.                                 |
| `command`   | string  |         | Shell command to run. Only allowed commands may be executed. |
| `cwd`       | string  | `.`     | Working directory relative to the repository root.           |
| `timeout_s` | integer | `300`   | Timeout in seconds. Exceeding the timeout kills the command. |
| `mode`      | string  | `safe`  | Execution mode: `safe` or `expert`.                          |

*Returns*

| Name        | Type   | Description                                  |
|-------------|--------|----------------------------------------------|
| `run_id`    | string | Identifier for this command execution.       |
| `exit_code` | int    | Exit code of the command.                    |
| `stdout`    | string | Standard output (redacted) of the command.   |
| `stderr`    | string | Standard error (redacted) of the command.    |
| `duration_ms`| int   | Execution duration in milliseconds.          |
| `timed_out` | bool   | Whether the command timed out.               |

## Repo/Git Tools

### ensure_fork

Ensure that a fork of the upstream repository exists under the configured GitHub username, creating it if necessary.

*Arguments*

| Name                 | Type   | Description                                             |
|----------------------|--------|---------------------------------------------------------|
| `upstream_repo_slug` | string | The `owner/repo` of the upstream repository.            |

*Returns*

| Name        | Type    | Description                                      |
|-------------|---------|--------------------------------------------------|
| `fork_slug` | string  | The `owner/repo` of the fork.                   |
| `fork_url`  | string  | Clone URL of the fork.                          |
| `created`   | bool    | Whether a new fork was created.                 |

### repo_clone

Clone a repository into the workspace. This tool uses an internal git runner that bypasses the `run_command` allowlist.

*Arguments*

| Name           | Type   | Description                           |
|----------------|--------|---------------------------------------|
| `workspace_id` | string | Identifier of the workspace.          |
| `repo_url`     | string | The HTTPS clone URL of the repository.|

*Returns*

| Name           | Type   | Description                                             |
|----------------|--------|---------------------------------------------------------|
| `repo_path`    | string | Absolute path to the cloned repository in the workspace.|
| `default_branch`| string| Default branch name (e.g. `main`).                     |
| `head_sha`      | string| SHA of the cloned head commit.                          |

### repo_setup_remotes

Clone the user's fork and configure the upstream remote in one operation. This is the recommended way to set up a fork-based workflow.

*Arguments*

| Name           | Type   | Default | Description                                      |
|----------------|--------|---------|--------------------------------------------------|
| `workspace_id` | string |         | Identifier of the workspace.                     |
| `fork_url`     | string |         | HTTPS clone URL of the user's fork.              |
| `upstream_url` | string |         | HTTPS clone URL of the upstream repository.      |
| `base_branch`  | string | `main`  | Branch name on upstream to track.                |

*Returns*

| Name           | Type   | Description                           |
|----------------|--------|---------------------------------------|
| `repo_path`    | string | Path to the cloned repository.        |
| `default_branch`| string| The configured base branch.           |

### repo_add_remote

Add a new remote to the repository.

*Arguments*

| Name           | Type   | Description                           |
|----------------|--------|---------------------------------------|
| `workspace_id` | string | Identifier of the workspace.          |
| `name`         | string | Name of the remote (e.g. `upstream`).  |
| `url`          | string | HTTPS URL of the remote.              |

*Returns*

| Name    | Type | Description                        |
|---------|------|------------------------------------|
| `added` | bool | Whether the remote was successfully added |

### repo_fetch

Fetch updates from a remote.

*Arguments*

| Name           | Type   | Default   | Description                                      |
|----------------|--------|-----------|--------------------------------------------------|
| `workspace_id` | string |           | Identifier of the workspace.                     |
| `remote`       | string | `upstream`| Name of the remote to fetch from.                |

*Returns*

| Name | Type | Description          |
|------|------|----------------------|
| `ok` | bool | Whether the fetch succeeded |

### repo_checkout

Checkout a branch, tag or commit in the repository.

*Arguments*

| Name           | Type   | Description                                |
|----------------|--------|--------------------------------------------|
| `workspace_id` | string | Identifier of the workspace.               |
| `ref`          | string | The Git reference (e.g. `main`, `HEAD~1`). |

*Returns*

| Name            | Type   | Description                                  |
|-----------------|--------|----------------------------------------------|
| `checked_out`   | string | The reference that was checked out.          |

### repo_create_branch

Create a new branch from a given reference. If the branch already exists, the tool returns `created: false`.

*Arguments*

| Name           | Type   | Description                               |
|----------------|--------|-------------------------------------------|
| `workspace_id` | string | Identifier of the workspace.              |
| `branch_name`  | string | Name of the branch to create.             |
| `from_ref`     | string | The base reference (e.g. `main`).         |

*Returns*

| Name        | Type | Description                                             |
|-------------|------|---------------------------------------------------------|
| `created`   | bool | Whether the branch was created (false if it already exists) |

### repo_diff

Get the unified diff of all changes in the working directory relative to the current HEAD.

*Arguments*

| Name           | Type   | Description                               |
|----------------|--------|-------------------------------------------|
| `workspace_id` | string | Identifier of the workspace.              |

*Returns*

| Name           | Type   | Description                                          |
|----------------|--------|------------------------------------------------------|
| `unified_diff` | string | Unified diff of all changes.                         |
| `files_changed`| int    | Number of files changed.                              |
| `insertions`   | int    | Total insertions.                                    |
| `deletions`    | int    | Total deletions.                                     |

### repo_commit

Commit staged changes with a commit message.

*Arguments*

| Name           | Type   | Description                               |
|----------------|--------|-------------------------------------------|
| `workspace_id` | string | Identifier of the workspace.              |
| `message`      | string | Commit message. Secrets are redacted.    |

*Returns*

| Name        | Type   | Description                         |
|-------------|--------|-------------------------------------|
| `commit_sha`| string | The SHA of the created commit.      |

### repo_push

Push the current branch to a remote repository.

**Important:** 
- Requires a valid `approval_id` from `request_approval`
- Only allows pushing to `origin` (the fork). Pushing to `upstream` or other remotes is blocked.

*Arguments*

| Name           | Type   | Default   | Description                                 |
|----------------|--------|-----------|---------------------------------------------|
| `workspace_id` | string |           | Identifier of the workspace.                |
| `remote`       | string | `origin`  | Remote name (must be `origin`).             |
| `branch_name`  | string |           | Branch name to push.                        |
| `approval_id`  | string |           | Approval ID from `request_approval`.        |

*Returns*

| Name            | Type   | Description                                    |
|-----------------|--------|------------------------------------------------|
| `pushed`        | bool   | Whether the push succeeded.                   |
| `remote_branch` | string | Full ref of the branch on the remote.        |

## Editing Tools

### read_file

Read the contents of a file in the repository.

*Arguments*

| Name           | Type   | Description                                  |
|----------------|--------|----------------------------------------------|
| `workspace_id` | string | Identifier of the workspace.                 |
| `path`         | string | Path to the file relative to the repository root. |

*Returns*

| Name    | Type   | Description                       |
|---------|--------|-----------------------------------|
| `content`| string | Contents of the file (redacted). |

### search_repo

Search for a string in the repository.

*Arguments*

| Name           | Type    | Default | Description                                                      |
|----------------|---------|---------|------------------------------------------------------------------|
| `workspace_id` | string  |         | Identifier of the workspace.                                     |
| `query`        | string  |         | Text to search for.                                              |
| `globs`        | array   | `null`  | Optional list of glob patterns to restrict the search scope.      |

*Returns*

| Name     | Type    | Description                                |
|----------|---------|--------------------------------------------|
| `matches`| array   | List of objects with `path`, `line`, `snippet` where matches were found. |

### apply_patch

Apply a unified diff patch to the working tree. The patch is validated and rejected if it modifies more files or lines than permitted by the configuration.

*Arguments*

| Name           | Type   | Description                                   |
|----------------|--------|-----------------------------------------------|
| `workspace_id` | string | Identifier of the workspace.                  |
| `unified_diff` | string | Unified diff to apply.                        |

*Returns*

| Name            | Type | Description                                       |
|-----------------|------|---------------------------------------------------|
| `applied`       | bool | Whether the patch was applied successfully.       |
| `files_modified`| array| List of files modified by the patch.             |
| `diff_lines`    | int  | Number of diff lines.                            |

### write_file

Write content to a file in the repository.

*Arguments*

| Name           | Type   | Description                                   |
|----------------|--------|-----------------------------------------------|
| `workspace_id` | string | Identifier of the workspace.                  |
| `path`         | string | Path to the file relative to repository root. |
| `content`      | string | Content to write to the file.                 |

*Returns*

| Name     | Type | Description                            |
|----------|------|----------------------------------------|
| `written`| bool | Whether the file was written successfully |

## QA Tools

### detect_project

Detect the project type (currently only Python is supported) and provide default commands for testing, linting, type checking and formatting.

*Arguments*

| Name           | Type   | Description                    |
|----------------|--------|--------------------------------|
| `workspace_id` | string | Identifier of the workspace.   |

*Returns*

| Name                | Type    | Description                                              |
|---------------------|---------|----------------------------------------------------------|
| `type`              | string  | Project type (e.g. `python`).                           |
| `test_command`      | string  | Suggested command to run tests (e.g. `pytest -q`).      |
| `lint_command`      | string  | Suggested command to run linter (e.g. `ruff check .`).  |
| `typecheck_command` | string  | Suggested command to run type checker (e.g. `mypy .`).  |
| `format_command`    | string  | Suggested command to format code (e.g. `ruff format .`).|

### install_deps

Install project dependencies using `uv` (or fallback to `pip`). Timeouts and retries are applied.

*Arguments*

| Name           | Type   | Description                    |
|----------------|--------|--------------------------------|
| `workspace_id` | string | Identifier of the workspace.   |

*Returns*

| Name      | Type | Description                                |
|-----------|------|--------------------------------------------|
| `success` | bool | Whether dependencies were installed.        |
| `logs`    | string | Installation logs (redacted).             |

### run_tests

Run the test suite. If a command is provided it overrides the default test command from `detect_project`.

*Arguments*

| Name           | Type    | Default | Description                           |
|----------------|---------|---------|---------------------------------------|
| `workspace_id` | string  |         | Identifier of the workspace.          |
| `command`      | string  | `null`  | Test command to run.                  |

*Returns*

| Name           | Type    | Description                                         |
|----------------|---------|-----------------------------------------------------|
| `passed`       | bool    | Whether all tests passed.                           |
| `exit_code`    | int     | Exit code of the test command.                     |
| `failing_tests`| array   | List of failing test names (if any).               |
| `logs`         | string  | Test logs (redacted).                              |

### run_lint

Run the linter.

*Arguments*

| Name           | Type    | Default | Description                           |
|----------------|---------|---------|---------------------------------------|
| `workspace_id` | string  |         | Identifier of the workspace.          |
| `command`      | string  | `null`  | Lint command to run.                  |

*Returns*

| Name    | Type | Description                     |
|---------|------|---------------------------------|
| `passed`| bool | Whether the linter passed.      |
| `logs`  | string | Lint logs (redacted).         |

### run_typecheck

Run the type checker.

*Arguments*

| Name           | Type    | Default | Description                           |
|----------------|---------|---------|---------------------------------------|
| `workspace_id` | string  |         | Identifier of the workspace.          |
| `command`      | string  | `null`  | Type check command to run.            |

*Returns*

| Name    | Type | Description                             |
|---------|------|-----------------------------------------|
| `passed`| bool | Whether the type checker passed.         |
| `logs`  | string | Type check logs (redacted).            |

### run_format

Run the formatter. This tool may return `ran: false` if the project does not define a formatting command.

*Arguments*

| Name           | Type    | Default | Description                           |
|----------------|---------|---------|---------------------------------------|
| `workspace_id` | string  |         | Identifier of the workspace.          |
| `command`      | string  | `null`  | Formatting command to run.            |

*Returns*

| Name    | Type | Description                                      |
|---------|------|--------------------------------------------------|
| `ran`   | bool | Whether formatting ran.                          |
| `logs`  | string | Formatter logs (redacted).                     |

### run_precommit

Run the pre-commit hooks configured in `.pre-commit-config.yaml`. This may take a long time, so timeouts and retries are applied.

*Arguments*

| Name           | Type    | Description                           |
|----------------|---------|---------------------------------------|
| `workspace_id` | string  | Identifier of the workspace.          |

*Returns*

| Name    | Type | Description                         |
|---------|------|-------------------------------------|
| `ran`   | bool | Whether pre-commit hooks were run.  |
| `passed`| bool | Whether all hooks passed.           |
| `logs`  | string | Hook logs (redacted).             |

## GitHub Tools

### github_get_issue

Retrieve an issue from GitHub.

*Arguments*

| Name          | Type   | Description                        |
|---------------|--------|------------------------------------|
| `repo_slug`   | string | The `owner/repo` of the repository. |
| `issue_number`| int    | Issue number.                       |

*Returns*

Either an object with `title`, `body` and `url`, or `{ "missing": true }` if the issue does not exist.

### github_find_prs_for_issue

Find pull requests associated with a particular issue.

*Arguments*

| Name          | Type   | Description                        |
|---------------|--------|------------------------------------|
| `repo_slug`   | string | The `owner/repo` of the repository. |
| `issue_number`| int    | Issue number.                       |

*Returns*

| Name    | Type  | Description                                                           |
|---------|-------|-----------------------------------------------------------------------|
| `prs`   | array | List of objects containing `number`, `url`, `head_branch`, `head_repo`, `author_login`, `state` |

### github_open_pr

Open a pull request on the upstream repository using the head branch from the fork. The PR is opened as a draft by default.

**Important:**
- Requires a valid `approval_id` from `request_approval`
- The `fork_repo_slug` owner must match the configured `GITHUB_USERNAME`
- The `body` must NOT contain auto-close keywords (`closes #N`, `fixes #N`, `resolves #N`)

*Arguments*

| Name                | Type   | Description                                                      |
|---------------------|--------|------------------------------------------------------------------|
| `upstream_repo_slug`| string | The `owner/repo` of the upstream repository.                     |
| `base_branch`       | string | The branch to merge into (e.g. `main`).                          |
| `fork_repo_slug`    | string | The `owner/repo` of the user's fork.                             |
| `head_branch`       | string | The branch on the fork to use as the PR head.                   |
| `title`             | string | The PR title.                                                    |
| `body`              | string | The PR body (must not contain auto-close keywords).             |
| `draft`             | bool   | Whether the PR should be opened as a draft (`true` by default). |
| `approval_id`       | string | Approval ID from `request_approval`.                            |

*Returns*

| Name      | Type  | Description                               |
|-----------|-------|-------------------------------------------|
| `pr_url`  | string| URL of the created pull request.          |
| `pr_number`| int  | Number of the created pull request.        |

## Approval Tool

### request_approval

Present the diff and evidence to a human reviewer (or automated policy) and ask for approval. This tool returns an approval ID that can be used for **both** `repo_push` and `github_open_pr` operations.

*Arguments*

| Name         | Type   | Description                                                         |
|--------------|--------|---------------------------------------------------------------------|
| `summary`    | string | High-level summary of the changes.                                  |
| `unified_diff`| string| Unified diff of the changes.                                        |
| `checks`     | object | Results of QA checks (`tests`, `lint`, `typecheck`, `format`).      |
| `pr_draft`   | bool   | Whether the PR will be opened as a draft.                           |
| `branch_plan`| object | Details about branch creation or reuse.                              |
| `approved`   | bool   | Whether the changes are approved.                                   |
| `notes`      | string | Optional notes from the reviewer.                                   |
| `pr_title`   | string | Optional PR title for metadata.                                     |
| `pr_body`    | string | Optional PR body for metadata.                                      |
| `issue_url`  | string | Optional URL of the related issue.                                  |

*Returns*

| Name        | Type   | Description                                                      |
|-------------|--------|------------------------------------------------------------------|
| `approved`  | bool   | Whether the reviewer approved the changes.                       |
| `approval_id`| string| Unique ID to use for push/PR operations (only if approved).     |
| `notes`     | string | Optional notes from the reviewer.                                |

## Artifact Tool

### bundle_artifacts

Bundle run artifacts into a redacted zip file. Returns the zip as base64-encoded data for direct retrieval through MCP.

*Arguments*

| Name            | Type   | Description                                                |
|-----------------|--------|------------------------------------------------------------|
| `diff_text`     | string | The unified diff to include.                               |
| `metadata`      | object | Metadata dictionary to include.                            |
| `before_failures`| object| Test/lint failures before changes.                        |
| `after_failures` | object| Test/lint failures after changes.                         |
| `logs`          | object | Dictionary of log name to log content.                     |
| `secrets`       | array  | List of secrets to redact from artifacts.                  |

*Returns*

| Name          | Type   | Description                                      |
|---------------|--------|--------------------------------------------------|
| `artifact_path`| string| Local filesystem path to the zip (for debugging).|
| `zip_filename` | string| The filename of the zip archive.                 |
| `zip_base64`   | string| Base64-encoded contents of the zip file.         |
| `size_bytes`   | int   | Size of the zip file in bytes.                   |
