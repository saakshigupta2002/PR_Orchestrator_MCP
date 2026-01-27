"""E2B desktop mode workspace implementation.

Desktop workspaces are NOT SUPPORTED in v1 of PR Orchestrator.
This module exists only to provide a clear error message.
"""

from __future__ import annotations


class E2BDesktopWorkspace:
    """Desktop workspace - NOT SUPPORTED in v1.
    
    Per spec: Only code mode workspaces are supported in v1.
    Desktop workspaces require additional infrastructure and are planned
    for future versions.
    """

    def __init__(self, ttl_minutes: int = 60) -> None:
        raise NotImplementedError(
            "Desktop workspace is not supported in v1. "
            "Use code mode only: workspace_create(mode='code')"
        )

    def destroy(self) -> None:
        pass

    def expired(self) -> bool:
        return True
