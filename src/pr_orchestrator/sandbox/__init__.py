"""Workspace and filesystem abstractions for the MCP server."""

from .workspace_store import Workspace, WorkspaceStore

__all__ = ["WorkspaceStore", "Workspace"]
