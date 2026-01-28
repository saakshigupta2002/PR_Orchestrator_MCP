"""MCP stdio server entrypoint for the PR Orchestrator.

The server runs over standard input/output using the Model Context Protocol.
It registers tool functions that clients can invoke to perform repository
operations, editing, QA checks, and GitHub interactions.

This is an MCP-only server - no JSON fallback protocol is supported.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from typing import Any

from .constants import DEFAULT_LOG_LEVEL
from .tools import (
    approval_tools,
    artifact_tools,
    edit_tools,
    github_tools,
    qa_tools,
    repo_tools,
    workspace_tools,
)

# Import MCP SDK - required, no fallback
try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    print(
        "ERROR: MCP SDK is required but not installed.\n"
        "Install with: pip install mcp\n"
        f"Import error: {exc}",
        file=sys.stderr
    )
    sys.exit(1)


def build_tools_dispatch() -> dict[str, Callable[..., dict[str, Any]]]:
    """Return a mapping from tool names to callables.

    Each callable accepts keyword arguments as specified in docs/tool-spec.md and
    returns a JSON-serializable dictionary.
    """
    return {
        # Workspace
        "workspace_create": workspace_tools.workspace_create,
        "workspace_destroy": workspace_tools.workspace_destroy,
        "run_command": workspace_tools.run_command,
        # Repo / Git
        "ensure_fork": repo_tools.ensure_fork,
        "repo_clone": repo_tools.repo_clone,
        "repo_setup_remotes": repo_tools.repo_setup_remotes,
        "repo_add_remote": repo_tools.repo_add_remote,
        "repo_fetch": repo_tools.repo_fetch,
        "repo_checkout": repo_tools.repo_checkout,
        "repo_create_branch": repo_tools.repo_create_branch,
        "repo_diff": repo_tools.repo_diff,
        "repo_commit": repo_tools.repo_commit,
        "repo_push": repo_tools.repo_push,
        "repo_list_branches": repo_tools.repo_list_branches,
        "repo_find_existing_branches": repo_tools.repo_find_existing_branches,
        "repo_read_pr_template": repo_tools.repo_read_pr_template,
        # Editing
        "read_file": edit_tools.read_file,
        "search_repo": edit_tools.search_repo,
        "apply_patch": edit_tools.apply_patch,
        "write_file": edit_tools.write_file,
        # QA
        "detect_project": qa_tools.detect_project,
        "install_deps": qa_tools.install_deps,
        "run_tests": qa_tools.run_tests,
        "run_lint": qa_tools.run_lint,
        "run_typecheck": qa_tools.run_typecheck,
        "run_format": qa_tools.run_format,
        "run_precommit": qa_tools.run_precommit,
        # GitHub
        "github_ensure_fork": github_tools.github_ensure_fork,
        "github_get_issue": github_tools.github_get_issue,
        "github_find_prs_for_issue": github_tools.github_find_prs_for_issue,
        "github_open_pr": github_tools.github_open_pr,
        # Approval
        "request_approval": approval_tools.request_approval,
        # Artifact bundling
        "bundle_artifacts": artifact_tools.bundle_artifacts_tool,
    }


def main() -> None:
    """Entrypoint for the PR Orchestrator MCP server.
    
    This starts an MCP stdio server. The MCP SDK is required.
    """
    # Configure logging to stderr (stdout is used for MCP protocol)
    logging.basicConfig(
        level=getattr(logging, DEFAULT_LOG_LEVEL, logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting PR Orchestrator MCP server")

    # Create MCP server
    mcp = FastMCP("pr-orchestrator-mcp")

    # Register all tools using add_tool
    dispatch = build_tools_dispatch()
    for name, func in dispatch.items():
        mcp.add_tool(func, name=name)

    logger.info("Registered %d tools", len(dispatch))

    # Run the MCP server over stdio (blocking)
    # This call handles the MCP protocol and keeps server alive
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
