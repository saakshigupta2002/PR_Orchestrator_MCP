"""GitHub REST API wrapper."""

from __future__ import annotations

import logging

import httpx

from ..config import Config
from .auth import get_github_client

logger = logging.getLogger(__name__)


def _github_request(
    config: Config,
    method: str,
    url: str,
    *,
    params: dict[str, object] | None = None,
    json: dict[str, object] | None = None,
    allow_404: bool = False,
) -> object | None:
    """Perform an HTTP request against the GitHub API.

    This helper wraps ``httpx`` to provide a default timeout, GitHub client
    headers and basic error handling.  If the request returns a non-2xx
    response (other than 404 when ``allow_404=True``), an error is raised.

    All requests go only to https://api.github.com/...
    """
    # Ensure we only talk to GitHub API
    if not url.startswith("https://api.github.com/"):
        raise ValueError(f"Invalid GitHub API URL: {url}")

    try:
        with get_github_client(config) as client:
            resp = client.request(method, url, params=params, json=json)
    except httpx.HTTPError as exc:
        logger.error("GitHub API request failed: %s", exc)
        raise RuntimeError(f"GitHub API request failed: {exc}") from exc

    # Allow explicit 404 responses when requested
    if allow_404 and resp.status_code == 404:
        return None

    # Check for success codes
    if 200 <= resp.status_code < 300:
        try:
            return resp.json()
        except Exception:
            return resp.text

    logger.error("GitHub API error %s: %s", resp.status_code, resp.text)
    raise RuntimeError(f"GitHub API error {resp.status_code}: {resp.text}")


def get_issue(config: Config, repo_slug: str, issue_number: int) -> dict[str, object]:
    """Retrieve a GitHub issue.  Returns a dict with `title`, `body`, `url` or `{missing: True}`."""
    url = f"https://api.github.com/repos/{repo_slug}/issues/{issue_number}"
    data = _github_request(config, "GET", url, allow_404=True)
    if data is None:
        return {"missing": True}
    return {"title": data.get("title"), "body": data.get("body"), "url": data.get("html_url")}


def find_prs_for_issue(config: Config, repo_slug: str, issue_number: int) -> dict[str, list[dict[str, object]]]:
    """Find pull requests linked to an issue.

    This implementation searches the repository's pull requests and filters by issue number in the PR body.
    It returns a list of PR descriptors.
    """
    prs: list[dict[str, object]] = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{repo_slug}/pulls"
        params = {"state": "all", "per_page": 100, "page": page}
        items = _github_request(config, "GET", url, params=params)
        if not items:
            break
        issue_ref = f"#{issue_number}"
        issue_url = f"https://github.com/{repo_slug}/issues/{issue_number}"
        for pr in items:
            title = pr.get("title", "") or ""
            body = pr.get("body", "") or ""
            search_text = f"{title}\n{body}".lower()
            if issue_ref.lower() in search_text or issue_url.lower() in search_text:
                prs.append(
                    {
                        "number": pr["number"],
                        "url": pr["html_url"],
                        "head_branch": pr["head"]["ref"],
                        "head_repo": pr["head"]["repo"]["full_name"],
                        "author_login": pr["user"]["login"],
                        "state": pr["state"],
                    }
                )
        page += 1
    return {"prs": prs}


def open_pr(
    config: Config,
    upstream_repo_slug: str,
    base_branch: str,
    fork_repo_slug: str,
    head_branch: str,
    title: str,
    body: str,
    draft: bool = True,
) -> dict[str, object]:
    """Open a pull request on the upstream repository.

    Returns the PR URL and number.
    
    The head format is: fork_owner:head_branch
    """
    url = f"https://api.github.com/repos/{upstream_repo_slug}/pulls"

    # Correctly compute PR head: fork_owner:branch
    # fork_repo_slug is "owner/repo", so split on "/" and take first part
    fork_owner = fork_repo_slug.split("/", 1)[0]
    head = f"{fork_owner}:{head_branch}"

    payload = {
        "title": title,
        "body": body,
        "head": head,
        "base": base_branch,
        "draft": draft,
    }

    data = _github_request(config, "POST", url, json=payload)
    return {"pr_url": data["html_url"], "pr_number": data["number"]}
