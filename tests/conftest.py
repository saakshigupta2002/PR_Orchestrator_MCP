"""Pytest configuration and fixtures for PR Orchestrator tests.

This module provides a FakeBackend that can be used for testing without
requiring actual E2B sandbox access.

IMPORTANT: Environment variables must be set BEFORE importing pr_orchestrator
modules, as the state module lazily loads configuration on first access.
"""

from __future__ import annotations

import os

# Set environment variables BEFORE any pr_orchestrator imports
# This must happen at module load time, before pytest fixtures run
os.environ.setdefault("GITHUB_TOKEN", "test-github-token")
os.environ.setdefault("E2B_API_KEY", "test-e2b-key")
os.environ.setdefault("GITHUB_USERNAME", "test-user")
os.environ.setdefault("ALLOWED_REPOS", "test/*,owner/*,saakshigupta2002/*")

import shutil
import subprocess
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

import pytest


class FakeBackend:
    """A fake backend for testing that executes locally in a temp directory.
    
    This is ONLY for testing - not used in production.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self._files: dict[str, str] = {}

    def run(self, argv: Sequence[str], cwd: str, timeout_s: int) -> dict[str, object]:
        """Run a command locally in the test directory."""
        # Build working directory
        if cwd == "." or cwd == "":
            workdir = self.root
        elif cwd.startswith("/"):
            workdir = Path(cwd)
        else:
            workdir = self.root / cwd

        # Ensure directory exists
        workdir.mkdir(parents=True, exist_ok=True)

        timed_out = False
        start_ns = time.time_ns()

        try:
            proc = subprocess.run(
                list(argv),
                cwd=str(workdir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                timeout=timeout_s,
                text=True,
                env={
                    **os.environ,
                    "GIT_TERMINAL_PROMPT": "0",
                    "GIT_AUTHOR_NAME": "Test",
                    "GIT_AUTHOR_EMAIL": "test@test.com",
                    "GIT_COMMITTER_NAME": "Test",
                    "GIT_COMMITTER_EMAIL": "test@test.com",
                },
            )
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            exit_code = proc.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            stdout = ""
            stderr = "Command timed out"
            exit_code = 124
        except Exception as exc:
            stdout = ""
            stderr = str(exc)
            exit_code = 1

        duration_ms = int((time.time_ns() - start_ns) / 1_000_000)

        return {
            "run_id": os.urandom(16).hex(),
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms,
            "timed_out": timed_out,
        }

    def read_text(self, path: str) -> str:
        """Read a file from the test directory."""
        if path.startswith("/"):
            full_path = Path(path)
        else:
            full_path = self.root / path

        with open(full_path, encoding="utf-8") as f:
            return f.read()

    def write_text(self, path: str, content: str) -> None:
        """Write a file to the test directory."""
        if path.startswith("/"):
            full_path = Path(path)
        else:
            full_path = self.root / path

        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)

    def destroy(self) -> None:
        """Clean up the test directory."""
        try:
            shutil.rmtree(self.root)
        except Exception:
            pass


class FakeWorkspaceImpl:
    """Fake workspace implementation for testing."""

    def __init__(self, path: Path, backend: FakeBackend) -> None:
        self.path = path
        self.mode = "code"
        self.created_at = time.time()
        self.backend = backend
        self._ttl_minutes = 60

    def expired(self) -> bool:
        return False

    def destroy(self) -> None:
        self.backend.destroy()


@pytest.fixture
def fake_workspace(monkeypatch):
    """Create a fake workspace for testing.
    
    This fixture patches the state module to use a fake backend instead of
    requiring E2B.
    """
    # Create temp directory
    tmpdir = Path(tempfile.mkdtemp(prefix="test_ws_"))
    backend = FakeBackend(tmpdir)

    # Create fake workspace
    from dataclasses import dataclass

    @dataclass
    class FakeWorkspace:
        id: str
        impl: FakeWorkspaceImpl
        backend: FakeBackend

    impl = FakeWorkspaceImpl(tmpdir, backend)
    ws = FakeWorkspace(id="test-workspace-id", impl=impl, backend=backend)

    # Patch the state module
    class FakeWorkspaceStore:
        def __init__(self):
            self._store = {ws.id: ws}
            self._run_active = False
            self.config = type('Config', (), {
                'github_token': 'test-token',
                'e2b_api_key': 'test-e2b-key',
                'github_username': 'test-user',
                'allowed_repos': ['test/*'],
            })()

        def get(self, workspace_id: str):
            if workspace_id not in self._store:
                raise KeyError(f"Unknown workspace: {workspace_id}")
            return self._store[workspace_id]

        def create(self, mode: str = "code", ttl_minutes: int = 60):
            return ws

        def destroy(self, workspace_id: str) -> bool:
            if workspace_id in self._store:
                del self._store[workspace_id]
                return True
            return False

    fake_store = FakeWorkspaceStore()

    # Patch state module
    import pr_orchestrator.state as state_module
    monkeypatch.setattr(state_module, "WORKSPACES", fake_store)
    monkeypatch.setattr(state_module, "CONFIG", fake_store.config)

    yield ws

    # Cleanup
    backend.destroy()


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up basic test environment."""
    # Set required env vars for any code that checks them
    monkeypatch.setenv("GITHUB_TOKEN", "test-github-token")
    monkeypatch.setenv("E2B_API_KEY", "test-e2b-key")
    monkeypatch.setenv("GITHUB_USERNAME", "test-user")
    monkeypatch.setenv("ALLOWED_REPOS", "test/*,owner/*")
