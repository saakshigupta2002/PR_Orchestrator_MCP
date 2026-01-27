"""Allowlist enforcement for repositories and commands.

The specification restricts the server to operate only on a set of
whitelisted repositories provided via the `ALLOWED_REPOS` environment variable.
This module centralises logic for checking whether a repository is allowed.
"""

from __future__ import annotations

from collections.abc import Iterable


def is_repo_allowed(repo_slug: str, allowed: Iterable[str], owner_prefix: str = "saakshigupta2002") -> bool:
    """Return ``True`` if ``repo_slug`` is explicitly permitted.

    This helper retains backward compatibility with the original allowlist
    semantics: a repository must begin with ``owner_prefix`` and must be
    present in ``allowed`` (or match a wildcard ``owner_prefix/*``).  It is
    retained for legacy checks.  Newer logic should use ``upstream_allowed``
    and ``fork_owner_allowed`` for finer control over upstream and fork
    repositories.
    """
    normalized = repo_slug.lower().strip()
    allowed_normalized = {r.lower().strip() for r in allowed}
    # Must begin with owner_prefix
    if not normalized.startswith(f"{owner_prefix.lower()}/"):
        return False
    if f"{owner_prefix.lower()}/*" in allowed_normalized:
        return True
    return normalized in allowed_normalized


def upstream_allowed(repo_slug: str, allowed: Iterable[str]) -> bool:
    """Check whether an upstream repository is allowed.

    A repository is allowed if its full slug (case‑insensitive) appears in the
    allowlist or if a wildcard ``*`` entry is present.  No owner prefix is
    required.  A trailing ``/*`` wildcard indicates all repos for a given
    owner are permitted.  An entry of ``*/*`` or ``*`` allows any upstream.
    """
    normalized = repo_slug.lower().strip()
    allowed_normalized = {r.lower().strip() for r in allowed}
    if "*" in allowed_normalized or "*/*" in allowed_normalized:
        return True
    if normalized in allowed_normalized:
        return True
    # Check owner wildcard e.g. "org/*"
    try:
        owner, _repo = normalized.split("/", 1)
    except ValueError:
        return False
    if f"{owner}/*" in allowed_normalized:
        return True
    return False


def fork_owner_allowed(repo_slug: str, username: str, allowed: Iterable[str]) -> bool:
    """Check whether a forked repository slug is allowed under the given username.

    The fork must reside under ``username``, and the downstream project name
    must appear in the allowlist (with optional wildcards).  For example, if
    ``allowed`` contains ``org/repo``, then a fork ``username/repo`` is
    permitted.  If the allowlist contains ``org/*``, then any fork of an
    upstream project under ``username`` is allowed.  Global wildcards
    ``*``/``*/*`` also permit all forks.
    """
    normalized = repo_slug.lower().strip()
    # Must begin with the username
    if not normalized.startswith(f"{username.lower()}/"):
        return False
    try:
        _owner_prefix, repo_name = normalized.split("/", 1)
    except ValueError:
        return False
    allowed_normalized = {r.lower().strip() for r in allowed}
    # Global wildcard
    if "*" in allowed_normalized or "*/*" in allowed_normalized:
        return True
    # Match on repo name from any owner
    for entry in allowed_normalized:
        if entry.endswith("/*"):
            # owner wildcard
            # e.g. "org/*" allows any project under org
            continue
    # Check direct match: if upstream 'owner/repo' is allowed, then fork is allowed
    for entry in allowed_normalized:
        # skip wildcard entries
        if entry.endswith("/*"):
            # extract owner
            continue
        try:
            _allowed_owner, allowed_repo = entry.split("/", 1)
        except ValueError:
            continue
        if allowed_repo == repo_name:
            return True
    # Check owner wildcard: e.g. "org/*" means any repo of org is allowed
    # In this case, the fork owner must match username and repo name from that org
    for entry in allowed_normalized:
        if entry.endswith("/*"):
            # entry form: "owner/*"
            owner_prefix = entry[:-2]
            # if upstream owner wildcard matches, any repo with that name is allowed
            # Accept the fork because upstream check will have validated earlier
            return True
    return False
