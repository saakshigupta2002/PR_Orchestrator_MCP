# PR Orchestrator MCP

The **PR Orchestrator MCP** is a tools-only [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that provides a safe and deterministic interface for automating the creation of pull requests against GitHub repositories. The server exposes a set of high-level operations—such as workspace management, repository cloning, branch management, test and lint execution, and GitHub API interactions—through the standardized MCP tool protocol.

A client language model (such as Claude in Cursor or other MCP-compatible clients) orchestrates calls to these tools to perform complex repair workflows on Python repositories. **The server is intentionally "dumb"—it provides tools but does no autonomous reasoning.** All decision-making is delegated to the client.

## Architecture

```
┌─────────────────────┐          stdio (MCP)          ┌──────────────────────┐
│   Orchestrator LLM  │ ◄──────────────────────────► │  PR Orchestrator MCP │
│  (Claude/Cursor)    │    tool calls + responses    │       Server         │
└─────────────────────┘                               └──────────┬───────────┘
                                                                 │
                                                                 ▼
                                                      ┌──────────────────────┐
                                                      │    E2B Sandbox       │
                                                      │  (isolated execution)│
                                                      └──────────────────────┘
```

The server communicates over **stdio using the MCP protocol**. It registers tools that the client can discover and invoke. Each tool performs a specific operation and returns structured results.

## Motivation

Maintaining large codebases often involves applying fixes across many repositories. The PR Orchestrator MCP codifies common tasks into a reusable server so that clients (for example, an orchestrating LLM) can focus on reasoning while the server ensures a consistent and safe execution environment. It enforces strict safety policies, implements a branch strategy to avoid collisions, and produces verifiable evidence before opening a draft PR for review.

## Features

* **MCP Protocol**: Implements the standard Model Context Protocol for seamless integration with MCP-compatible clients like Claude Desktop and Cursor.
* **Workspace lifecycle:** Create, manage and destroy isolated workspaces using the [E2B](https://e2b.dev/) code sandbox. Each workspace is time-limited and is used to perform all actions on the repository.
* **Repository operations:** Clone the fork of an allowed repository, add an upstream remote, fetch branches and create or reuse topic branches. Enforce limits on the number of modified files and diff lines.
* **Editing tools:** Read and write files, search through the repository and apply unified diffs. Patches are validated and redacted before being applied.
* **Quality assurance:** Detect the project type, install dependencies, run tests, linting, type checking and formatting. Only the necessary commands are run and results are returned in structured JSON.
* **GitHub integration:** Authenticate using a personal access token from `.env`, ensure the fork exists, push changes and open a draft pull request with the required sections in the body. **No auto-close keywords are allowed.**
* **Approval gate:** Before pushing and opening a PR, the server exposes an approval tool which returns `approved: bool` and optional notes. The client must call this tool after reviewing the diff and evidence. Approval IDs are multi-use: they can authorize both push and PR creation.
* **Fork-only workflow:** Pushes are restricted to the user's fork (`origin`). Direct pushes to `upstream` are blocked.

## Getting Started

This repository is intended to be consumed as a Python package and run via `uv` or `python`:

```bash
git clone https://github.com/your-fork/pr-orchestrator-mcp.git
cd pr-orchestrator-mcp
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
# Edit .env with your credentials
uv run pr-orchestrator-mcp  # or python -m pr_orchestrator.server
```

### Environment Variables

Create a `.env` file with the following required variables:

```bash
GITHUB_TOKEN=ghp_your_token_here
GITHUB_USERNAME=your_github_username
ALLOWED_REPOS=owner/repo1,owner/repo2
E2B_API_KEY=your_e2b_api_key

# Optional
E2B_TEMPLATE=base  # E2B template with restricted network
LOG_LEVEL=INFO
E2B_ALLOW_LOCAL_FALLBACK=false  # Set to true only for local testing
```

### Using with Cursor/Claude

Add the server to your MCP configuration:

```json
{
  "mcpServers": {
    "pr-orchestrator": {
      "command": "uv",
      "args": ["run", "pr-orchestrator-mcp"],
      "cwd": "/path/to/pr-orchestrator-mcp"
    }
  }
}
```

## Tools Overview

The server exposes the following tool categories:

### Workspace Tools
- `workspace_create` - Create a sandboxed workspace
- `workspace_destroy` - Destroy a workspace
- `run_command` - Execute allowed commands in a workspace

### Repository Tools
- `ensure_fork` - Ensure a fork exists for an upstream repo
- `repo_clone` - Clone a repository into workspace
- `repo_setup_remotes` - Clone fork and configure upstream remote
- `repo_checkout`, `repo_create_branch`, `repo_fetch`
- `repo_diff`, `repo_commit`, `repo_push` (requires approval)

### Editing Tools
- `read_file`, `write_file` - File operations
- `search_repo` - Search repository contents
- `apply_patch` - Apply unified diff patches

### QA Tools
- `detect_project` - Detect project type and commands
- `install_deps` - Install dependencies
- `run_tests`, `run_lint`, `run_typecheck`, `run_format`
- `run_precommit` - Run pre-commit hooks

### GitHub Tools
- `github_get_issue` - Retrieve issue details
- `github_find_prs_for_issue` - Find related PRs
- `github_open_pr` - Open a pull request (requires approval)

### Approval Tool
- `request_approval` - Request approval for irreversible actions

### Artifact Tool
- `bundle_artifacts` - Create a redacted artifact bundle (returns base64)

See `docs/tool-spec.md` for detailed specifications of each tool.

## Safety Features

- **Command allowlist**: Only approved commands can be executed
- **Fork-only pushes**: Cannot push to upstream, only to your fork
- **Approval gating**: Push and PR creation require explicit approval
- **No auto-close**: PR bodies cannot contain `closes/fixes/resolves #N`
- **Secret redaction**: Tokens are redacted from all outputs
- **E2B sandbox**: Execution happens in isolated containers
- **Repository allowlist**: Only configured repos can be accessed

## Repository Layout

```
pr-orchestrator-mcp/
├── README.md               # This file
├── LICENSE                 # MIT license
├── CHANGELOG.md            # Project changelog
├── CODE_OF_CONDUCT.md      # Contributor Covenant code of conduct
├── CONTRIBUTING.md         # Contribution guidelines
├── SECURITY.md             # Security policies and reporting
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Lockfile for uv/pip
├── Makefile                # Development tasks
├── docs/                   # Documentation
│   ├── architecture.md     # High-level architecture description
│   ├── threat-model.md     # Threat modelling and safety considerations
│   ├── tool-spec.md        # Detailed specification of each tool
│   └── demo.md             # Walkthrough of a typical run
├── src/
│   └── pr_orchestrator/    # Source code package
│       ├── __init__.py
│       ├── server.py       # MCP stdio server entrypoint
│       ├── state.py        # Shared state (config, workspaces, runs)
│       ├── config.py       # Configuration loading from environment
│       ├── constants.py    # Hard-coded constants from the spec
│       ├── policy/         # Safety policies and allowlists
│       ├── sandbox/        # Workspace and E2B sandbox abstraction
│       ├── git/            # Git operations and branch strategy
│       ├── qa/             # Quality assurance helpers
│       ├── github/         # GitHub API interactions
│       ├── tools/          # Public tool interfaces
│       ├── artifacts/      # Artifact bundling and report generation
│       └── telemetry/      # Logging and run store implementation
├── tests/                  # Unit and integration tests
│   ├── unit/
│   └── integration/
└── scripts/
    ├── smoke_test.sh       # Quick smoke test for the server
    └── run_server.sh       # Helper script to start the MCP server
```

## Contributing

Contributions are welcome! Please read `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` before opening an issue or pull request. All changes must include unit tests and be accompanied by an entry in `CHANGELOG.md`.

## License

This project is licensed under the terms of the MIT license. See `LICENSE` for details.
