"""Configuration loading for PR Orchestrator MCP.

This module loads environment variables from a `.env` file using
`python-dotenv` and populates a `Config` object.

Required variables:
- GITHUB_TOKEN
- E2B_API_KEY

Optional variables with defaults:
- GITHUB_USERNAME (default: from GITHUB_TOKEN user info, or 'saakshigupta2002')
- ALLOWED_REPOS (default: '<username>/*')
- LOG_LEVEL (default: 'INFO')
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):  # type: ignore[override]
        return False


@dataclass
class Config:
    """Configuration values loaded from the environment."""

    github_token: str
    github_username: str
    allowed_repos: list[str]
    e2b_api_key: str
    log_level: str

    @classmethod
    def load_from_env(cls) -> Config:
        """Load configuration from environment variables.

        The `.env` file is loaded if present.  Raises `RuntimeError` if
        required variables are missing.
        """
        load_dotenv()
        missing = []

        # Required: GITHUB_TOKEN
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            missing.append("GITHUB_TOKEN")

        # Required: E2B_API_KEY
        e2b_api_key = os.getenv("E2B_API_KEY")
        if not e2b_api_key:
            missing.append("E2B_API_KEY")

        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        # Optional: GITHUB_USERNAME with default
        github_username = os.getenv("GITHUB_USERNAME")
        if not github_username:
            # Try to get from token (would require API call), or use default
            github_username = "saakshigupta2002"

        # Optional: ALLOWED_REPOS with default
        allowed_repos_str = os.getenv("ALLOWED_REPOS")
        if allowed_repos_str:
            allowed_repos = [repo.strip() for repo in allowed_repos_str.split(",") if repo.strip()]
        else:
            # Default: allow all repos under the configured username
            allowed_repos = [f"{github_username}/*"]

        # Optional: LOG_LEVEL with default
        log_level = os.getenv("LOG_LEVEL", "INFO")

        return cls(
            github_token=github_token,
            github_username=github_username,
            allowed_repos=allowed_repos,
            e2b_api_key=e2b_api_key,
            log_level=log_level,
        )
