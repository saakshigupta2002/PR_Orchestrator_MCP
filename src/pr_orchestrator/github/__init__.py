"""GitHub API integration."""

from .api import (
    find_prs_for_issue,
    get_issue,
    open_pr,
)
from .auth import get_github_client
from .templates import generate_pr_body

__all__ = [
    "get_github_client",
    "get_issue",
    "find_prs_for_issue",
    "open_pr",
    "generate_pr_body",
]
