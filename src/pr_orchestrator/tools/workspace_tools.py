"""Workspace tool implementations.

This module exposes operations for creating, destroying and executing commands
within workspaces.  Workspaces are backed by the E2B code sandbox in a real
implementation; this stub provides limited functionality and enforces TTL
and command allowlists based on safe/expert modes.
"""

from __future__ import annotations

import logging

from ..state import WORKSPACES

logger = logging.getLogger(__name__)


def workspace_create(mode: str = "code", ttl_minutes: int = 60) -> dict[str, object]:
    """Create a new workspace and return its identifier.

    The ``ttl_minutes`` is clamped to the maximum allowed TTL from configuration.
    Returns workspace info including expiration time.
    """
    ws = WORKSPACES.create(mode=mode, ttl_minutes=ttl_minutes)
    created_at = ws.impl.created_at
    ttl_seconds = ws.impl.ttl_minutes * 60
    expires_at = created_at + ttl_seconds

    return {
        "workspace_id": ws.id,
        "mode": ws.impl.mode,
        "created_at": created_at,
        "expires_at": expires_at,
        "ttl_minutes": ws.impl.ttl_minutes,
    }


def workspace_destroy(workspace_id: str) -> dict[str, bool]:
    """Destroy a workspace by ID."""
    destroyed = WORKSPACES.destroy(workspace_id)
    return {"destroyed": destroyed}


def run_command(
    workspace_id: str,
    command: str,
    cwd: str = ".",
    timeout_s: int = 300,
    mode: str = "safe",
) -> dict[str, object]:
    """Execute a command inside a workspace.

    The ``mode`` argument controls the command allowlist.  Supported values:

    * ``safe`` (default): Only allow a restricted set of commands (git, uv, pip install,
      pytest/unittest, ruff, mypy).  This prevents dangerous operations.
    * ``expert``: Allows the same commands plus additional dev tools (not implemented here).

    Commands that violate the allowlist will raise a ``PermissionError``.
    """
    return WORKSPACES.run_command(workspace_id=workspace_id, command=command, cwd=cwd, timeout_s=timeout_s, mode=mode)
