"""Branch naming strategy as defined in the specification."""

from __future__ import annotations


# GitPython is no longer used by the project.  Repo is defined as a
# placeholder to satisfy type signatures.
class Repo:  # type: ignore[override]
    pass


def decide_branch_name(issue_number: int, repo: Repo, prefix: str = "issue") -> str:
    """Determine a branch name for a given issue number.

    This helper now uses a simple deterministic naming scheme of
    ``{prefix}/{issue_number}``.  Because GitPython is no longer used,
    this function cannot inspect existing branch names.  Callers must
    handle collisions externally if needed.
    """
    return f"{prefix}/{issue_number}"
