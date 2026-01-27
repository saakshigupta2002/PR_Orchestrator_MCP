"""Authentication helpers for GitHub API."""

from __future__ import annotations

import httpx

from ..config import Config


def get_github_client(config: Config) -> httpx.Client:
    """Return a configured GitHub httpx client with the Authorization header set."""
    return httpx.Client(
        headers={
            "Authorization": f"token {config.github_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": f"pr-orchestrator-mcp/{config.github_username}",
        },
        timeout=10.0,
    )
