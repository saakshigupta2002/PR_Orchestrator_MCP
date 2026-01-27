"""Shared state module for PR Orchestrator MCP.

This module provides a single shared instance of configuration, workspace store,
and run store that is used across all tool modules. This ensures that workspace
IDs created in one tool module are accessible from other tool modules.

All tool modules should import CONFIG, WORKSPACES, and RUNS from this module
instead of creating their own instances.
"""

from __future__ import annotations

from .config import Config
from .sandbox.workspace_store import WorkspaceStore
from .telemetry.run_store import RunStore

# Single shared configuration loaded once at import time
CONFIG: Config = Config.load_from_env()

# Single shared workspace store - all workspace operations go through this
WORKSPACES: WorkspaceStore = WorkspaceStore(CONFIG)

# Single shared run store for tracking command executions
RUNS: RunStore = RunStore()
