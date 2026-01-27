"""In‑memory run store for tracking MCP state."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RunEntry:
    """Record representing a single run."""

    run_id: str
    workspace_id: str
    metadata: dict[str, object] = field(default_factory=dict)


class RunStore:
    """Simple in‑memory store for runs.  Not persisted between server restarts."""

    def __init__(self) -> None:
        self._runs: dict[str, RunEntry] = {}

    def add(self, run_id: str, workspace_id: str, metadata: dict[str, object] | None = None) -> None:
        self._runs[run_id] = RunEntry(run_id=run_id, workspace_id=workspace_id, metadata=metadata or {})

    def get(self, run_id: str) -> RunEntry | None:
        return self._runs.get(run_id)

    def remove(self, run_id: str) -> None:
        self._runs.pop(run_id, None)
