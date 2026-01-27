"""GitHub tool implementations.

Wraps GitHub API interactions for retrieving issues, searching PRs and opening
pull requests.  Delegates to the ``github.api`` module which handles
authentication and HTTP calls.

All tools enforce the repository allowlist - operations are only permitted on
allowed repositories.
"""

from __future__ import annotations

import re

from ..github import api as github_api
from ..policy.allowlist import upstream_allowed
from ..state import CONFIG


def _enforce_repo_allowed(repo_slug: str) -> None:
    """Raise PermissionError if repo_slug is not in the allowlist."""
    if not upstream_allowed(repo_slug, CONFIG.allowed_repos):
        raise PermissionError(f"Repository '{repo_slug}' is not in the allowlist")


def github_ensure_fork(repo_slug: str) -> dict[str, object]:
    """Ensure a fork exists for the given upstream repository.

    Creates a fork under the authenticated user's account if it does not already
    exist.  Returns the fork slug, clone URL, upstream clone URL, and whether
    the fork was newly created.

    The upstream repository must be in the allowlist.
    """
    # Import ensure_fork from repo_tools (it has its own allowlist check)
    from .repo_tools import ensure_fork

    # Get fork info from ensure_fork
    result = ensure_fork(repo_slug)

    # Build upstream clone URL
    upstream_clone_url = f"https://github.com/{repo_slug}.git"

    return {
        "fork_repo_slug": result["fork_slug"],
        "fork_clone_url": result["fork_url"],
        "upstream_clone_url": upstream_clone_url,
        "created": result["created"],
    }


def github_get_issue(repo_slug: str, issue_number: int) -> dict[str, object]:
    """Get issue details from GitHub.
    
    The repository must be in the allowlist.
    """
    _enforce_repo_allowed(repo_slug)
    return github_api.get_issue(CONFIG, repo_slug, issue_number)


def github_find_prs_for_issue(repo_slug: str, issue_number: int) -> dict[str, object]:
    """Find PRs linked to an issue.
    
    The repository must be in the allowlist.
    """
    _enforce_repo_allowed(repo_slug)
    return github_api.find_prs_for_issue(CONFIG, repo_slug, issue_number)


def github_open_pr(
    upstream_repo_slug: str,
    base_branch: str,
    fork_repo_slug: str,
    head_branch: str,
    title: str,
    body: str,
    draft: bool = True,
    approval_id: str | None = None,
) -> dict[str, object]:
    """Open a pull request on GitHub.

    Requires a valid ``approval_id``, which is consumed prior to performing
    the API call.  Raises ``PermissionError`` if the approval ID is missing or
    invalid.  Delegates to the underlying GitHub API implementation.
    
    Validates that:
    1. The upstream repository is in the allowlist
    2. The fork owner matches the configured GitHub username
    3. The PR body does not contain auto-close keywords (closes, fixes, resolves)
    """
    from .approval_tools import consume_approval

    # Enforce allowlist on upstream repo
    _enforce_repo_allowed(upstream_repo_slug)

    if not approval_id or not consume_approval(approval_id, "open_pr"):
        raise PermissionError("A valid approval_id is required to open a pull request")

    # B4: Validate fork owner equals configured username
    try:
        fork_owner = fork_repo_slug.split("/")[0]
    except (IndexError, AttributeError):
        raise ValueError(f"Invalid fork_repo_slug format: {fork_repo_slug}")

    if fork_owner != CONFIG.github_username:
        raise PermissionError(
            f"Fork owner '{fork_owner}' does not match configured GitHub username '{CONFIG.github_username}'. "
            "PRs can only be opened from your own fork."
        )

    # S2: Enforce no auto-close keywords in PR body
    auto_close_pattern = r"\b(closes|fixes|resolves)\s+#\d+"
    if re.search(auto_close_pattern, body, re.IGNORECASE):
        raise ValueError(
            "PR body contains auto-close keywords (closes/fixes/resolves #N). "
            "Use 'Related to #N' instead to avoid auto-closing issues."
        )

    return github_api.open_pr(
        CONFIG,
        upstream_repo_slug=upstream_repo_slug,
        base_branch=base_branch,
        fork_repo_slug=fork_repo_slug,
        head_branch=head_branch,
        title=title,
        body=body,
        draft=draft,
    )
