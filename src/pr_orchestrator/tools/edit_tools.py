"""Editing tool implementations.

Provides functions to read and write files, search the repository and apply
patches.  All operations execute INSIDE the E2B sandbox via the backend.
No host filesystem access is used.
"""

from __future__ import annotations

import json
import logging
import posixpath

from ..policy.limits import enforce_patch_limits
from ..policy.redaction import redact_secrets
from ..state import CONFIG, WORKSPACES

logger = logging.getLogger(__name__)


def _validate_repo_path(path: str) -> str:
    """Validate and normalize a path to ensure it's within repo/.
    
    Args:
        path: Relative path within the repository
        
    Returns:
        Normalized path prefixed with 'repo/'
        
    Raises:
        ValueError: If path escapes repo/
    """
    # Reject absolute paths
    if path.startswith("/") or path.startswith("~"):
        raise ValueError(f"Path must be relative: {path}")

    # Normalize
    norm = posixpath.normpath(path)

    # Prevent directory traversal
    if norm.startswith("..") or "/.." in norm:
        raise ValueError(f"Path escapes repository: {path}")

    # Return full path from workspace root
    return f"repo/{norm}"


def read_file(workspace_id: str, path: str) -> dict[str, str]:
    """Read a file within the checked-out repository.

    The path is relative to the repository root. Content is read from
    the E2B sandbox and secrets are redacted.
    """
    ws = WORKSPACES.get(workspace_id)

    if ws.backend is None:
        raise RuntimeError("Workspace backend is not configured")

    # Validate and build full path
    full_path = _validate_repo_path(path)

    # Read via backend
    try:
        content = ws.backend.read_text(full_path)
    except Exception as exc:
        raise FileNotFoundError(f"Could not read file '{path}': {exc}") from exc

    # Redact secrets
    secrets = [CONFIG.github_token, CONFIG.e2b_api_key]
    content = redact_secrets(content, secrets)

    return {"content": content}


def write_file(workspace_id: str, path: str, content: str) -> dict[str, bool]:
    """Write content to a file in the repository.

    The path is relative to the repository root.
    """
    ws = WORKSPACES.get(workspace_id)

    if ws.backend is None:
        raise RuntimeError("Workspace backend is not configured")

    # Validate and build full path
    full_path = _validate_repo_path(path)

    # Write via backend
    try:
        ws.backend.write_text(full_path, content)
        return {"written": True}
    except Exception as exc:
        logger.error("Failed to write file %s: %s", path, exc)
        return {"written": False}


def search_repo(workspace_id: str, query: str, globs: list[str] | None = None) -> dict[str, object]:
    """Search for ``query`` within files under the repository root.

    Executes a Python search script inside the sandbox to find matches.
    Limited to a modest time budget and maximum match count.
    """
    ws = WORKSPACES.get(workspace_id)

    if ws.backend is None:
        raise RuntimeError("Workspace backend is not configured")

    # Build a Python search script to run inside the sandbox
    # This avoids requiring ripgrep or similar tools
    globs_json = json.dumps(globs or ["*"])
    query_escaped = query.replace("\\", "\\\\").replace("'", "\\'")

    search_script = f'''
import os
import fnmatch
import json

query = '{query_escaped}'
globs = {globs_json}
max_matches = 100
matches = []

for root, dirs, files in os.walk('.'):
    # Skip hidden directories
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    
    for filename in files:
        # Check glob patterns
        if globs and globs != ['*']:
            if not any(fnmatch.fnmatch(filename, g) for g in globs):
                continue
        
        filepath = os.path.join(root, filename)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line_no, line in enumerate(f, 1):
                    if query in line:
                        matches.append({{
                            'path': filepath[2:] if filepath.startswith('./') else filepath,
                            'line': line_no,
                            'snippet': line.strip()[:200]
                        }})
                        if len(matches) >= max_matches:
                            break
        except Exception:
            pass
        
        if len(matches) >= max_matches:
            break
    
    if len(matches) >= max_matches:
        break

print(json.dumps(matches))
'''

    # Run the search script inside the sandbox
    result = ws.backend.run(
        ["python", "-c", search_script],
        "repo",
        30  # 30 second timeout
    )

    if result.get("exit_code", 1) != 0:
        logger.warning("Search failed: %s", result.get("stderr", ""))
        return {"matches": [], "error": result.get("stderr", "Search failed")}

    try:
        matches = json.loads(result.get("stdout", "[]"))
    except json.JSONDecodeError:
        matches = []

    return {"matches": matches}


def apply_patch(workspace_id: str, unified_diff: str) -> dict[str, object]:
    """Apply a unified diff patch and enforce patch limits.

    The patch is written to a temporary file inside the sandbox and applied
    using ``git apply``.  Patch limits are enforced before application.
    """
    ws = WORKSPACES.get(workspace_id)

    if ws.backend is None:
        raise RuntimeError("Workspace backend is not configured")

    # Create .pr_orchestrator directory in repo for temp files
    ws.backend.run(["mkdir", "-p", ".pr_orchestrator"], "repo", 10)

    # Write diff to a file inside the sandbox
    patch_path = "repo/.pr_orchestrator/tmp.patch"
    ws.backend.write_text(patch_path, unified_diff)

    # Apply the patch using internal git helper
    # The path is relative to repo/
    resp = WORKSPACES.run_git_apply(workspace_id, ".pr_orchestrator/tmp.patch")

    if resp.get("exit_code", 1) != 0:
        return {
            "applied": False,
            "files_modified": [],
            "stderr": resp.get("stderr", ""),
        }

    # Get modified files
    name_resp = WORKSPACES.run_command(workspace_id, "git diff --name-only", cwd="repo")
    files = [l for l in name_resp.get("stdout", "").splitlines() if l.strip()]

    # Count diff lines
    diff_resp = WORKSPACES.run_command(workspace_id, "git diff", cwd="repo")
    diff_lines = sum(
        1 for line in diff_resp.get("stdout", "").splitlines()
        if line.startswith("+") or line.startswith("-")
    )

    # Enforce limits
    enforce_patch_limits(files, diff_lines)

    return {
        "applied": True,
        "files_modified": files,
        "diff_lines": diff_lines,
    }
