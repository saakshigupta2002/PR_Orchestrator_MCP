"""Abstract workspace backends.

This module defines the backend abstraction used by ``WorkspaceStore`` to run
commands, read and write files and destroy workspaces.  A backend hides the
details of remote execution in an E2B sandbox.

In production, only E2BBackend is used.  For testing, a FakeBackend is available
in tests/conftest.py.
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence
from typing import Protocol

from ..config import Config
from ..policy.redaction import redact_secrets


class WorkspaceBackend(Protocol):
    """Interface for a workspace backend.

    Implementations must provide methods to run commands, read and write text
    files and destroy the underlying workspace.  Results of ``run`` must
    include exit_code, stdout, stderr, duration_ms and timed_out fields.
    """

    def run(self, argv: Sequence[str], cwd: str, timeout_s: int) -> dict[str, object]:
        ...

    def read_text(self, path: str) -> str:
        ...

    def write_text(self, path: str, content: str) -> None:
        ...

    def destroy(self) -> None:
        ...


class E2BBackend:
    """Backend that executes commands in an E2B sandbox.

    This backend wraps the E2B Python SDK.  It uses ``sandbox.commands.run()``
    for command execution and ``sandbox.files.read/write()`` for file operations.
    
    All git operations have proper authentication environment configured.
    """

    def __init__(self, sandbox: object, config: Config) -> None:
        """Initialize E2B backend.
        
        Args:
            sandbox: An E2B Sandbox instance from the e2b SDK
            config: Configuration containing tokens and settings
        """
        self.sandbox = sandbox
        self.config = config

    def _prepare_env(self) -> dict[str, str]:
        """Prepare environment variables for E2B command execution."""
        env = {}

        # Provide the GitHub token
        if self.config.github_token:
            env["GITHUB_TOKEN"] = self.config.github_token

        # Set GIT_ASKPASS to the askpass script path in the sandbox
        env["GIT_ASKPASS"] = "/home/user/git-askpass.sh"

        # Disable git terminal prompts - prevents hangs if auth fails
        env["GIT_TERMINAL_PROMPT"] = "0"

        # Set git user info
        env["GIT_AUTHOR_NAME"] = "PR Orchestrator"
        env["GIT_AUTHOR_EMAIL"] = "pr-orchestrator@localhost"
        env["GIT_COMMITTER_NAME"] = "PR Orchestrator"
        env["GIT_COMMITTER_EMAIL"] = "pr-orchestrator@localhost"

        return env

    def run(self, argv: Sequence[str], cwd: str, timeout_s: int) -> dict[str, object]:
        """Run a command in the E2B sandbox."""
        import shlex
        command = shlex.join(argv)

        timed_out = False
        start_ns = time.time_ns()

        # Build full path - E2B sandbox home is /home/user
        if cwd == "." or cwd == "":
            full_cwd = "/home/user"
        elif cwd.startswith("/"):
            full_cwd = cwd
        else:
            full_cwd = f"/home/user/{cwd}"

        try:
            # Use the E2B SDK's commands.run() method
            result = self.sandbox.commands.run(
                command,
                cwd=full_cwd,
                timeout=timeout_s,
                envs=self._prepare_env(),
            )

            stdout = result.stdout if hasattr(result, 'stdout') else ""
            stderr = result.stderr if hasattr(result, 'stderr') else ""
            exit_code = result.exit_code if hasattr(result, 'exit_code') else 0

        except TimeoutError:
            timed_out = True
            stdout = ""
            stderr = "Command timed out"
            exit_code = 124
        except Exception as exc:
            stdout = ""
            stderr = str(exc)
            exit_code = 1

        duration_ms = int((time.time_ns() - start_ns) / 1_000_000)

        # Redact secrets
        secrets = [self.config.github_token, self.config.e2b_api_key]
        stdout = redact_secrets(str(stdout), secrets)
        stderr = redact_secrets(str(stderr), secrets)

        return {
            "run_id": os.urandom(16).hex(),
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": duration_ms,
            "timed_out": timed_out,
        }

    def read_text(self, path: str) -> str:
        """Read a file from the E2B sandbox."""
        if path.startswith("/"):
            full_path = path
        else:
            full_path = f"/home/user/{path}"
        return self.sandbox.files.read(full_path)

    def write_text(self, path: str, content: str) -> None:
        """Write a file to the E2B sandbox."""
        if path.startswith("/"):
            full_path = path
        else:
            full_path = f"/home/user/{path}"
        self.sandbox.files.write(full_path, content)

    def destroy(self) -> None:
        """Kill the E2B sandbox."""
        try:
            self.sandbox.kill()
        except Exception:
            pass
