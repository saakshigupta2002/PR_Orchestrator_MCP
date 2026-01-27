"""Git repository operations (deprecated).

This module previously used GitPython to perform repository operations.  The
project has since migrated to executing git CLI commands via the
``workspace_store.run_command`` mechanism.  These functions are retained
for backwards compatibility but raise ``NotImplementedError`` to signal
that they should no longer be used.
"""

from __future__ import annotations

import logging
from pathlib import Path


class Repo:  # type: ignore[override]
    """Placeholder Repo type.  Do not instantiate."""
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "repo_ops functions have been deprecated; use repo_tools via the CLI instead."
        )

class Remote:  # type: ignore[override]
    """Placeholder Remote type."""
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "repo_ops functions have been deprecated; use repo_tools via the CLI instead."
        )

logger = logging.getLogger(__name__)


def clone_repo(work_dir: Path, repo_url: str) -> tuple[Repo, str, str]:
    """Deprecated.  Use ``repo_tools.repo_clone`` instead.  This function will raise."""
    raise NotImplementedError("clone_repo is deprecated; use repo_tools.repo_clone")


def add_remote(repo: Repo, name: str, url: str) -> bool:
    """Deprecated.  Use ``repo_tools.repo_add_remote`` instead."""
    raise NotImplementedError("add_remote is deprecated; use repo_tools.repo_add_remote")


def fetch(repo: Repo, remote_name: str = "upstream") -> bool:
    """Deprecated.  Use ``repo_tools.repo_fetch`` instead."""
    raise NotImplementedError("fetch is deprecated; use repo_tools.repo_fetch")


def checkout(repo: Repo, ref: str) -> str:
    """Deprecated.  Use ``repo_tools.repo_checkout`` instead."""
    raise NotImplementedError("checkout is deprecated; use repo_tools.repo_checkout")


def create_branch(repo: Repo, branch_name: str, from_ref: str) -> bool:
    """Deprecated.  Use ``repo_tools.repo_create_branch`` instead."""
    raise NotImplementedError("create_branch is deprecated; use repo_tools.repo_create_branch")


def diff(repo: Repo) -> tuple[str, int, int, int]:
    """Deprecated.  Use ``repo_tools.repo_diff`` instead."""
    raise NotImplementedError("diff is deprecated; use repo_tools.repo_diff")


def commit(repo: Repo, message: str) -> str:
    """Deprecated.  Use ``repo_tools.repo_commit`` instead."""
    raise NotImplementedError("commit is deprecated; use repo_tools.repo_commit")


def push(repo: Repo, remote_name: str, branch_name: str) -> tuple[bool, str]:
    """Deprecated.  Use ``repo_tools.repo_push`` instead."""
    raise NotImplementedError("push is deprecated; use repo_tools.repo_push")
