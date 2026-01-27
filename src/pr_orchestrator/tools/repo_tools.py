"""Repository and git tool implementations.

This module wraps repository lifecycle operations: ensuring a fork exists,
cloning a repo, managing remotes, creating and checking out branches, diffing
changes, committing and pushing.  It enforces repository allowlists and uses
git commands via the workspace's command runner instead of GitPython.

IMPORTANT: All operations execute INSIDE the E2B sandbox. No host filesystem
access is used.
"""

from __future__ import annotations

import logging

from ..policy.allowlist import fork_owner_allowed, upstream_allowed
from ..state import CONFIG, WORKSPACES

logger = logging.getLogger(__name__)


def ensure_fork(upstream_repo_slug: str) -> dict[str, object]:
    """Ensure a fork exists for the given ``upstream_repo_slug``.

    The upstream repository must be allowed according to the configured
    allowlist (via ``upstream_allowed``).  A fork will be created under the
    authenticated user's account if it does not already exist.  The function
    returns the fork slug (``username/repo``), the HTTPS clone URL, and
    whether a new fork was created.
    """
    # Validate upstream repo is allowed
    if not upstream_allowed(upstream_repo_slug, CONFIG.allowed_repos):
        raise PermissionError(f"Upstream repository '{upstream_repo_slug}' is not in the allowlist")

    # Parse owner/repo
    try:
        upstream_owner, repo_name = upstream_repo_slug.split("/", 1)
    except ValueError as exc:
        raise ValueError(f"Invalid repository slug '{upstream_repo_slug}'") from exc

    # Determine fork slug under our account
    username = CONFIG.github_username
    fork_slug = f"{username}/{repo_name}"

    # Check if fork is allowed for the user
    if not fork_owner_allowed(fork_slug, username, CONFIG.allowed_repos):
        raise PermissionError(f"Fork slug '{fork_slug}' is not permitted for user '{username}'")

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {CONFIG.github_token}",
    }
    import httpx
    import time as _time

    # Check if fork exists
    created = False
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"https://api.github.com/repos/{fork_slug}", headers=headers)
            if resp.status_code == 200:
                created = False
            elif resp.status_code == 404:
                # Create the fork
                create_url = f"https://api.github.com/repos/{upstream_owner}/{repo_name}/forks"
                create_resp = client.post(create_url, headers=headers)
                if create_resp.status_code not in {202, 201, 200}:
                    raise RuntimeError(
                        f"Failed to create fork: {create_resp.status_code} {create_resp.text}"
                    )
                created = True
                # Poll until fork exists (bounded retries)
                for _ in range(10):
                    poll = client.get(f"https://api.github.com/repos/{fork_slug}", headers=headers)
                    if poll.status_code == 200:
                        break
                    _time.sleep(1)
            else:
                raise RuntimeError(
                    f"Unexpected status checking fork existence: {resp.status_code} {resp.text}"
                )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Failed to ensure fork '{fork_slug}': {exc}") from exc

    fork_url = f"https://github.com/{fork_slug}.git"
    return {"fork_slug": fork_slug, "fork_url": fork_url, "created": created}


def _extract_repo_slug_from_url(repo_url: str) -> str | None:
    """Extract owner/repo from a GitHub URL."""
    import re
    # Match https://github.com/owner/repo.git or https://github.com/owner/repo
    match = re.match(r"https?://github\.com/([^/]+/[^/]+?)(?:\.git)?$", repo_url)
    if match:
        return match.group(1)
    return None


def repo_clone(workspace_id: str, repo_url: str) -> dict[str, object]:
    """Clone a repository into the workspace.

    The repository is cloned into the ``repo`` subdirectory within the sandbox.
    All operations happen inside E2B - no host filesystem access.
    
    The repository must be in the allowlist.
    """
    # Enforce allowlist
    repo_slug = _extract_repo_slug_from_url(repo_url)
    if repo_slug and not upstream_allowed(repo_slug, CONFIG.allowed_repos):
        raise PermissionError(f"Repository '{repo_slug}' is not in the allowlist")

    ws = WORKSPACES.get(workspace_id)

    # Clone into repo/ directory from workspace root
    # The clone command runs from workspace root (.) and creates repo/
    clone_cmd = ["git", "clone", repo_url, "repo"]
    result = WORKSPACES.run_internal_git(workspace_id, clone_cmd, cwd=".")

    if result.get("exit_code", 1) != 0:
        raise RuntimeError(f"Failed to clone repository: {result.get('stderr', '')}")

    # Detect default branch by inspecting HEAD
    default_branch = "main"
    branch_resp = WORKSPACES.run_internal_git(
        workspace_id,
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd="repo"
    )
    if branch_resp.get("exit_code", 1) == 0:
        detected = branch_resp.get("stdout", "").strip()
        if detected:
            default_branch = detected

    # Get head SHA
    sha_resp = WORKSPACES.run_internal_git(
        workspace_id,
        ["git", "rev-parse", "HEAD"],
        cwd="repo"
    )
    head_sha = sha_resp.get("stdout", "").strip()

    return {
        "repo_path": "repo",
        "default_branch": default_branch,
        "head_sha": head_sha,
    }


def repo_setup_remotes(
    workspace_id: str,
    fork_url: str,
    upstream_url: str,
    base_branch: str = "main",
) -> dict[str, object]:
    """Clone the user's fork and add the upstream remote.

    This helper encapsulates the recommended cloning workflow for a fork-based
    contribution flow:
    1. Clone the fork into repo/
    2. Add upstream remote
    3. Fetch upstream
    4. Checkout base branch tracking upstream
    
    All operations happen inside E2B sandbox.
    Both fork and upstream URLs must be in the allowlist.
    """
    # Enforce allowlist on both URLs
    fork_slug = _extract_repo_slug_from_url(fork_url)
    upstream_slug = _extract_repo_slug_from_url(upstream_url)

    if upstream_slug and not upstream_allowed(upstream_slug, CONFIG.allowed_repos):
        raise PermissionError(f"Upstream repository '{upstream_slug}' is not in the allowlist")

    # Fork must be under our username
    if fork_slug and not fork_owner_allowed(fork_slug, CONFIG.github_username, CONFIG.allowed_repos):
        raise PermissionError(f"Fork '{fork_slug}' is not permitted for user '{CONFIG.github_username}'")

    ws = WORKSPACES.get(workspace_id)

    # Step 1: clone the fork into repo/
    clone_cmd = ["git", "clone", fork_url, "repo"]
    clone_result = WORKSPACES.run_internal_git(workspace_id, clone_cmd, cwd=".")
    if clone_result.get("exit_code", 1) != 0:
        raise RuntimeError(f"Failed to clone fork: {clone_result.get('stderr', '')}")

    # Step 2: add upstream remote
    add_remote_cmd = ["git", "remote", "add", "upstream", upstream_url]
    WORKSPACES.run_internal_git(workspace_id, add_remote_cmd, cwd="repo")

    # Step 3: fetch upstream
    fetch_cmd = ["git", "fetch", "upstream"]
    WORKSPACES.run_internal_git(workspace_id, fetch_cmd, cwd="repo")

    # Step 4: checkout base branch tracking upstream
    checkout_cmd = ["git", "checkout", "-B", base_branch, f"upstream/{base_branch}"]
    WORKSPACES.run_internal_git(workspace_id, checkout_cmd, cwd="repo")

    return {"repo_path": "repo", "default_branch": base_branch}


def repo_list_branches(workspace_id: str, remote: str = "origin", all: bool = True) -> dict[str, object]:
    """List branches in the repository."""
    cmd = ["git", "branch", "-a"] if all else ["git", "branch"]
    resp = WORKSPACES.run_internal_git(workspace_id, cmd, cwd="repo")

    branches: list[str] = []
    for line in resp.get("stdout", "").splitlines():
        name = line.strip().lstrip("*").strip()
        if name:
            branches.append(name)
    return {"branches": branches}


def repo_find_existing_branches(workspace_id: str, patterns: list[str]) -> dict[str, object]:
    """Find branches matching any of the provided patterns."""
    all_branches = repo_list_branches(workspace_id, all=True).get("branches", [])
    matches: list[str] = []
    for pat in patterns:
        for branch in all_branches:
            if pat in branch and branch not in matches:
                matches.append(branch)
    return {"matches": matches}


def repo_read_pr_template(workspace_id: str) -> dict[str, object]:
    """Read the repository's pull request template.

    Reads `.github/pull_request_template.md` from inside the sandbox.
    """
    ws = WORKSPACES.get(workspace_id)

    if ws.backend is None:
        return {"exists": False, "template": ""}

    try:
        content = ws.backend.read_text("repo/.github/pull_request_template.md")
        return {"exists": True, "template": content}
    except Exception:
        return {"exists": False, "template": ""}


def repo_add_remote(workspace_id: str, name: str, url: str) -> dict[str, bool]:
    """Add a new remote to the repository."""
    cmd = ["git", "remote", "add", name, url]
    try:
        WORKSPACES.run_internal_git(workspace_id, cmd, cwd="repo")
        return {"added": True}
    except Exception:
        return {"added": False}


def repo_fetch(workspace_id: str, remote: str = "upstream") -> dict[str, bool]:
    """Fetch updates from a remote."""
    cmd = ["git", "fetch", remote]
    resp = WORKSPACES.run_internal_git(workspace_id, cmd, cwd="repo")
    return {"ok": resp.get("exit_code", 1) == 0}


def repo_checkout(workspace_id: str, ref: str) -> dict[str, str]:
    """Checkout a branch, tag or commit."""
    cmd = ["git", "checkout", ref]
    WORKSPACES.run_internal_git(workspace_id, cmd, cwd="repo")
    return {"checked_out": ref}


def repo_create_branch(workspace_id: str, branch_name: str, from_ref: str) -> dict[str, bool]:
    """Create a new branch from a given reference."""
    # Check if branch exists
    branches = WORKSPACES.run_internal_git(workspace_id, ["git", "branch", "--list"], cwd="repo")
    if branch_name in (branches.get("stdout", "")):
        return {"created": False}

    # Checkout from_ref and create new branch
    WORKSPACES.run_internal_git(workspace_id, ["git", "checkout", from_ref], cwd="repo")
    WORKSPACES.run_internal_git(workspace_id, ["git", "checkout", "-b", branch_name], cwd="repo")
    return {"created": True}


def repo_diff(workspace_id: str) -> dict[str, object]:
    """Get the unified diff of all changes in the working directory."""
    diff_resp = WORKSPACES.run_internal_git(workspace_id, ["git", "diff", "-U3"], cwd="repo")
    diff_text = diff_resp.get("stdout", "")

    # Count insertions and deletions
    insertions = sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---"))

    # Number of changed files
    name_resp = WORKSPACES.run_internal_git(workspace_id, ["git", "diff", "--name-only"], cwd="repo")
    files_changed = len([l for l in name_resp.get("stdout", "").splitlines() if l.strip()])

    return {
        "unified_diff": diff_text,
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
    }


def repo_commit(workspace_id: str, message: str) -> dict[str, str]:
    """Commit staged changes with a commit message."""
    WORKSPACES.run_internal_git(workspace_id, ["git", "add", "-A"], cwd="repo")
    cmd = ["git", "commit", "-m", message]
    WORKSPACES.run_internal_git(workspace_id, cmd, cwd="repo")
    sha_resp = WORKSPACES.run_internal_git(workspace_id, ["git", "rev-parse", "HEAD"], cwd="repo")
    return {"commit_sha": sha_resp.get("stdout", "").strip()}


def repo_push(
    workspace_id: str,
    remote: str = "origin",
    branch_name: str = "",
    approval_id: str | None = None,
) -> dict[str, object]:
    """Push the current HEAD to the specified remote/branch.

    A valid ``approval_id`` must be provided.
    Only pushing to 'origin' (the fork) is allowed.
    The fork must be under the configured GitHub username.
    """
    from .approval_tools import consume_approval

    # Enforce fork-only push
    if remote != "origin":
        raise PermissionError(f"Only pushing to 'origin' (fork) is allowed. Attempted to push to '{remote}'.")

    # Note: The fork URL was validated during repo_setup_remotes or repo_clone
    # Additional validation at push time would require reading the remote URL from git config

    if not approval_id or not consume_approval(approval_id, "push"):
        raise PermissionError("A valid approval_id is required to push changes")

    refspec = f"HEAD:{branch_name}" if branch_name else "HEAD"
    resp = WORKSPACES.run_git_push(workspace_id, remote, refspec)

    return {
        "pushed": resp.get("exit_code", 1) == 0,
        "remote_branch": f"{remote}/{branch_name or 'HEAD'}",
    }
